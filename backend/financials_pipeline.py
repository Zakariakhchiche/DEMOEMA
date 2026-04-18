"""
EdRCF 6.0 — financials_pipeline.py
Pipeline INPI RNE : enrichissement dirigeants + capital social des top PME/ETI Silver.

Architecture :
  bronze_rne   → DuckDB (MotherDuck) — dirigeants + capital par SIREN (INPI RNE)
  silver_ma    → Mise à jour ma_score avec bonus âge dirigeant + capital

Prérequis :
  pip install httpx duckdb
  Env : INPI_USER=<user>   INPI_PASSWORD=<pass>   (optionnels)
        MOTHERDUCK_TOKEN=<token>                    (hérité de bronze_pipeline)

Usage :
  python financials_pipeline.py setup       → crée la table bronze_rne
  python financials_pipeline.py load [N]    → charge top-N SIRENs depuis INPI
  python financials_pipeline.py enrich      → met à jour ma_score Silver
  python financials_pipeline.py run [N]     → setup + load + enrich
"""

import asyncio
import os
import sys
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Optionnel : duckdb peut ne pas être installé ─────────────────────────────
try:
    import duckdb as _duckdb
    _DUCKDB_OK = True
except ImportError:
    _DUCKDB_OK = False

# =============================================================================
# Configuration
# =============================================================================

INPI_USER     = os.getenv("INPI_USER", "")
INPI_PASSWORD = os.getenv("INPI_PASSWORD", "")

INPI_LOGIN_URL   = "https://registre-national-entreprises.inpi.fr/api/sso/login"
INPI_COMPANY_URL = "https://registre-national-entreprises.inpi.fr/api/companies/{siren}"

RNE_TABLE = "bronze_rne"

RNE_DDL = f"""
CREATE TABLE IF NOT EXISTS {RNE_TABLE} (
    siren            VARCHAR(9)  NOT NULL,
    nom_dirigeant    TEXT,
    qualite          TEXT,
    annee_naissance  SMALLINT,
    capital_social   BIGINT,
    enriched_at      TIMESTAMP DEFAULT current_timestamp
);
"""

# =============================================================================
# Imports depuis bronze_pipeline
# =============================================================================

def _import_bronze():
    """Importe bronze_pipeline de façon lazy pour éviter les erreurs au démarrage."""
    import bronze_pipeline as bp
    return bp


# =============================================================================
# SETUP
# =============================================================================

def setup_rne_table() -> None:
    """Crée la table bronze_rne + index sur siren (idempotent)."""
    bp = _import_bronze()
    if not _DUCKDB_OK:
        print("[RNE] duckdb non installé — setup ignoré.")
        return
    con = bp._get_connection()
    print(f"[RNE] Création table {RNE_TABLE}…")
    con.execute(RNE_DDL)
    con.execute(
        f"CREATE INDEX IF NOT EXISTS idx_rne_siren ON {RNE_TABLE} (siren)"
    )
    con.close()
    print(f"[RNE] Table {RNE_TABLE} prête.")


# =============================================================================
# INPI SSO — token JWT
# =============================================================================

async def _inpi_token() -> str | None:
    """
    Obtient un JWT INPI via POST /api/sso/login.
    Retourne le token ou None si pas de credentials ou erreur.
    """
    if not INPI_USER or not INPI_PASSWORD:
        print("[RNE] INPI_USER / INPI_PASSWORD non définis — token ignoré.")
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                INPI_LOGIN_URL,
                json={"username": INPI_USER, "password": INPI_PASSWORD},
                headers={"Content-Type": "application/json"},
            )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token") or data.get("access_token") or data.get("jwt")
            if token:
                print("[RNE] Token INPI obtenu.")
                return token
            print(f"[RNE] Token absent dans la réponse INPI : {list(data.keys())}")
        else:
            print(f"[RNE] Échec login INPI : HTTP {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"[RNE] Erreur _inpi_token : {e}")
    return None


# =============================================================================
# Parsing de la réponse INPI RNE
# =============================================================================

def _parse_annee_naissance(raw: str | None) -> int | None:
    """
    Parse une date de naissance INPI.
    Accepte '1965-03-15' (ISO) ou '1965' (année seule).
    """
    if not raw:
        return None
    raw = str(raw).strip()
    try:
        if len(raw) >= 4:
            return int(raw[:4])
    except (ValueError, TypeError):
        pass
    return None


def _parse_capital(raw) -> int | None:
    """
    Parse le champ capital INPI.
    Accepte {"montant": 50000, "devise": "EUR"} ou directement un int/float.
    """
    if raw is None:
        return None
    if isinstance(raw, dict):
        montant = raw.get("montant")
        if montant is not None:
            try:
                return int(float(montant))
            except (ValueError, TypeError):
                pass
        return None
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        return None


def _extract_dirigeant(company_data: dict) -> tuple[str | None, str | None, int | None]:
    """
    Extrait le dirigeant principal depuis la réponse INPI RNE.
    Cherche dans 'dirigeants' puis 'representants'.
    Retourne (nom_complet, qualite, annee_naissance).
    """
    for key in ("dirigeants", "representants"):
        membres = company_data.get(key)
        if isinstance(membres, list) and membres:
            # Prend le premier dirigeant actif ou le premier de la liste
            for m in membres:
                qualite = (
                    m.get("qualite")
                    or m.get("qualites")
                    or m.get("fonction")
                    or m.get("role")
                    or ""
                )
                if isinstance(qualite, list):
                    qualite = ", ".join(qualite)
                prenom = m.get("prenom") or m.get("prenoms") or ""
                nom = m.get("nom") or m.get("nomUsage") or m.get("nomNaissance") or ""
                nom_complet = f"{prenom} {nom}".strip() or None
                date_nais = m.get("dateNaissance") or m.get("dateDeNaissance")
                annee = _parse_annee_naissance(date_nais)
                if nom_complet:
                    return nom_complet, qualite or None, annee
    return None, None, None


# =============================================================================
# LOAD — chargement INPI RNE
# =============================================================================

async def load_rne_batch(top_n: int = 500) -> int:
    """
    Enrichit les top_n SIRENs Silver avec les données INPI RNE (dirigeants + capital).
    Rate limit : ~3 req/s (sleep 0.35s entre requêtes), pause 60s sur HTTP 429.
    Retourne le nombre de lignes insérées dans bronze_rne.
    """
    bp = _import_bronze()

    if not _DUCKDB_OK:
        print("[RNE] duckdb non installé — load_rne_batch ignoré.")
        return 0

    token = await _inpi_token()
    if not token:
        print("[RNE] Pas de token INPI — load_rne_batch annulé.")
        return 0

    con = bp._get_connection()

    # Récupère les top_n SIRENs depuis silver_ma
    try:
        rows = con.execute(f"""
            SELECT siren FROM {bp.SILVER_TABLE}
            ORDER BY bodacc_recent DESC, ma_score DESC
            LIMIT {top_n}
        """).fetchall()
    except Exception as e:
        print(f"[RNE] Erreur lecture silver_ma : {e}")
        con.close()
        return 0

    sirens = [r[0] for r in rows]
    print(f"[RNE] Chargement INPI RNE pour {len(sirens)} SIRENs…")

    # Purge des données existantes pour ces SIRENs
    if sirens:
        placeholders = ", ".join(f"'{s}'" for s in sirens)
        con.execute(f"DELETE FROM {RNE_TABLE} WHERE siren IN ({placeholders})")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    inserted = 0
    batch: list[tuple] = []
    BATCH_SIZE = 50

    async with httpx.AsyncClient(timeout=20) as client:
        for i, siren in enumerate(sirens):
            try:
                url = INPI_COMPANY_URL.format(siren=siren)
                resp = await client.get(url, headers=headers)

                if resp.status_code == 429:
                    print(f"[RNE] HTTP 429 — pause 60s (siren={siren})…")
                    await asyncio.sleep(60)
                    resp = await client.get(url, headers=headers)

                if resp.status_code != 200:
                    print(f"[RNE] HTTP {resp.status_code} pour SIREN {siren} — ignoré.")
                    await asyncio.sleep(0.35)
                    continue

                data = resp.json()
                # L'API peut renvoyer directement le dict ou dans data.company / data.formality
                company_data = data
                if "company" in data and isinstance(data["company"], dict):
                    company_data = data["company"]
                elif "formality" in data and isinstance(data["formality"], dict):
                    company_data = data["formality"].get("content", {}) or data["formality"]

                nom_dirigeant, qualite, annee_naissance = _extract_dirigeant(company_data)
                capital_raw = (
                    company_data.get("capital")
                    or company_data.get("capitalSocial")
                    or company_data.get("montantCapital")
                )
                capital_social = _parse_capital(capital_raw)

                batch.append((siren, nom_dirigeant, qualite, annee_naissance, capital_social))

                if len(batch) >= BATCH_SIZE:
                    con.executemany(
                        f"INSERT INTO {RNE_TABLE} "
                        f"(siren, nom_dirigeant, qualite, annee_naissance, capital_social) "
                        f"VALUES (?, ?, ?, ?, ?)",
                        batch,
                    )
                    inserted += len(batch)
                    batch = []
                    print(f"[RNE] {inserted}/{len(sirens)} SIRENs traités…")

            except Exception as e:
                print(f"[RNE] Erreur SIREN {siren} : {e}")

            await asyncio.sleep(0.35)

    # Flush du dernier batch
    if batch:
        con.executemany(
            f"INSERT INTO {RNE_TABLE} "
            f"(siren, nom_dirigeant, qualite, annee_naissance, capital_social) "
            f"VALUES (?, ?, ?, ?, ?)",
            batch,
        )
        inserted += len(batch)

    con.close()
    print(f"[RNE] Terminé — {inserted} lignes insérées dans {RNE_TABLE}.")
    return inserted


# =============================================================================
# ENRICH — bonus ma_score Silver
# =============================================================================

def enrich_silver_rne() -> int:
    """
    Met à jour ma_score dans silver_ma avec les bonus INPI RNE :
    - +10 si dirigeant âge >= 58 (annee courante - annee_naissance >= 58)
    - +8  si capital_social >= 500 000 €
    - +5  si capital_social >= 100 000 €
    Retourne le nombre de lignes mises à jour.
    """
    bp = _import_bronze()

    if not _DUCKDB_OK:
        print("[RNE] duckdb non installé — enrich_silver_rne ignoré.")
        return 0

    con = bp._get_connection()
    current_year = datetime.utcnow().year
    seuil_age = 58

    try:
        # Bonus dirigeant senior
        con.execute(f"""
            UPDATE {bp.SILVER_TABLE}
            SET ma_score = LEAST(100, ma_score + 10)
            WHERE siren IN (
                SELECT siren FROM {RNE_TABLE}
                WHERE annee_naissance IS NOT NULL
                  AND ({current_year} - annee_naissance) >= {seuil_age}
            )
        """)
        print(f"[RNE] Bonus +10 (dirigeant >= {seuil_age} ans) appliqué.")

        # Bonus capital >= 500 000
        con.execute(f"""
            UPDATE {bp.SILVER_TABLE}
            SET ma_score = LEAST(100, ma_score + 8)
            WHERE siren IN (
                SELECT siren FROM {RNE_TABLE}
                WHERE capital_social >= 500000
            )
        """)
        print("[RNE] Bonus +8 (capital >= 500k€) appliqué.")

        # Bonus capital >= 100 000 (seulement si < 500 000)
        con.execute(f"""
            UPDATE {bp.SILVER_TABLE}
            SET ma_score = LEAST(100, ma_score + 5)
            WHERE siren IN (
                SELECT siren FROM {RNE_TABLE}
                WHERE capital_social >= 100000
                  AND capital_social < 500000
            )
        """)
        print("[RNE] Bonus +5 (capital 100k–500k€) appliqué.")

        # Compte les lignes mises à jour (qui ont une entrée dans bronze_rne)
        updated = con.execute(f"""
            SELECT COUNT(*) FROM {bp.SILVER_TABLE}
            WHERE siren IN (SELECT DISTINCT siren FROM {RNE_TABLE})
        """).fetchone()[0]

        con.close()
        print(f"[RNE] {updated} entreprises Silver enrichies via INPI RNE.")
        return updated

    except Exception as e:
        print(f"[RNE] Erreur enrich_silver_rne : {e}")
        con.close()
        return 0


# =============================================================================
# API orchestrateur
# =============================================================================

async def api_load_rne(top_n: int = 500) -> dict:
    """
    Orchestre le pipeline INPI RNE complet :
    1. setup_rne_table()
    2. load_rne_batch(top_n)
    3. enrich_silver_rne()
    Retourne un dict de statistiques.
    """
    t0 = time.time()
    stats: dict = {
        "top_n_requested": top_n,
        "rows_inserted":   0,
        "rows_enriched":   0,
        "elapsed_s":       0,
        "error":           None,
    }

    try:
        setup_rne_table()
        rows_inserted = await load_rne_batch(top_n=top_n)
        stats["rows_inserted"] = rows_inserted

        rows_enriched = await asyncio.to_thread(enrich_silver_rne)
        stats["rows_enriched"] = rows_enriched

    except Exception as e:
        stats["error"] = str(e)
        print(f"[RNE] api_load_rne erreur : {e}")

    stats["elapsed_s"] = round(time.time() - t0, 1)
    return stats


# =============================================================================
# CLI
# =============================================================================

async def _cli(cmd: str, args: list[str]) -> None:
    if cmd == "setup":
        setup_rne_table()

    elif cmd == "load":
        n = int(args[0]) if args else 500
        token = await _inpi_token()
        if not token:
            print("[RNE] Impossible de charger sans token INPI.")
            return
        count = await load_rne_batch(top_n=n)
        print(f"[RNE] {count} lignes insérées.")

    elif cmd == "enrich":
        updated = enrich_silver_rne()
        print(f"[RNE] {updated} lignes mises à jour dans Silver.")

    elif cmd == "run":
        n = int(args[0]) if args else 500
        result = await api_load_rne(top_n=n)
        print(f"[RNE] Pipeline terminé : {result}")

    else:
        print(__doc__)


if __name__ == "__main__":
    cmd  = sys.argv[1] if len(sys.argv) > 1 else "help"
    args = sys.argv[2:]
    asyncio.run(_cli(cmd, args))
