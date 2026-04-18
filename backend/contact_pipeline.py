"""
EdRCF 6.0 — contact_pipeline.py
Enrichissement des fiches Silver avec données de contact :
  - Site web, téléphone (recherche-entreprises.api.gouv.fr — gratuit, sans clé)
  - Adresse structurée (déjà dans StockEtablissement)
  - URL LinkedIn devinée depuis le nom
  - Email domaine (heuristique sur site web)

Tables :
  silver_ma  → colonnes ajoutées : site_web, telephone, linkedin_url, email_domaine
"""

import asyncio
import os
import re
import sys
import time
import unicodedata

import httpx
from dotenv import load_dotenv

load_dotenv()

try:
    import duckdb as _duckdb
    _DUCKDB_OK = True
except ImportError:
    _DUCKDB_OK = False

# API Entreprise (gouvernement, gratuite, sans clé API)
_GOV_API = "https://recherche-entreprises.api.gouv.fr/search"

# Colonnes à ajouter à silver_ma si absentes
CONTACT_COLUMNS = {
    "site_web":      "TEXT",
    "telephone":     "VARCHAR(20)",
    "linkedin_url":  "TEXT",
    "email_domaine": "TEXT",
}


def _import_bronze():
    import bronze_pipeline as bp
    return bp


# =============================================================================
# Setup — ajout des colonnes contact à silver_ma
# =============================================================================

def setup_contact_columns() -> None:
    """Ajoute les colonnes de contact à silver_ma si elles n'existent pas (idempotent)."""
    bp = _import_bronze()
    if not _DUCKDB_OK:
        return
    con = bp._get_connection()
    try:
        # Inspecte les colonnes existantes
        existing = {r[0].lower() for r in con.execute(
            f"DESCRIBE {bp.SILVER_TABLE}"
        ).fetchall()}
        for col, dtype in CONTACT_COLUMNS.items():
            if col not in existing:
                con.execute(f"ALTER TABLE {bp.SILVER_TABLE} ADD COLUMN {col} {dtype}")
                print(f"[CONTACT] Colonne '{col}' ajoutée à {bp.SILVER_TABLE}.")
    except Exception as e:
        print(f"[CONTACT] setup_contact_columns: {e}")
    finally:
        con.close()


# =============================================================================
# Helpers
# =============================================================================

def _slugify(name: str) -> str:
    """Transforme un nom d'entreprise en slug LinkedIn (ex: 'Dupont & Fils SAS' → 'dupont-fils')."""
    name = name.lower()
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")  # retire accents
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\b(sas|sarl|sa|sasu|sci|sca|snc|eurl|scp|gie|scm)\b", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:60]


def _extract_domain(url: str) -> str:
    """Extrait le domaine d'une URL → 'https://www.example.com/...' → 'example.com'."""
    if not url:
        return ""
    url = re.sub(r"https?://", "", url.lower()).split("/")[0]
    url = url.replace("www.", "")
    return url[:100]


def _guess_linkedin(denomination: str) -> str:
    slug = _slugify(denomination or "")
    if slug:
        return f"https://www.linkedin.com/company/{slug}"
    return ""


# =============================================================================
# Enrichissement via recherche-entreprises.api.gouv.fr
# =============================================================================

async def _fetch_contact(siren: str, client: httpx.AsyncClient) -> dict:
    """
    Interroge l'API gouvernementale pour un SIREN.
    Retourne dict avec site_web, telephone (si disponibles).
    Rate-limit : ~100 req/s — on reste à 20 req/s pour être sage.
    """
    try:
        resp = await client.get(
            _GOV_API,
            params={"q": siren, "per_page": 1},
            timeout=10,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return {}
        r = results[0]
        siege = r.get("siege") or {}

        site_web = (
            r.get("site_internet")
            or siege.get("site_internet")
            or siege.get("site_web")
            or ""
        )
        telephone = (
            r.get("telephone")
            or siege.get("telephone")
            or ""
        )
        return {
            "site_web":  site_web[:200] if site_web else "",
            "telephone": str(telephone)[:20] if telephone else "",
        }
    except Exception:
        return {}


async def enrich_contact_batch(top_n: int = 3000) -> int:
    """
    Enrichit les top_n entreprises Silver avec site_web + téléphone + LinkedIn URL.
    Source : recherche-entreprises.api.gouv.fr (gratuit, sans clé, ~100 req/s).
    Retourne le nombre de lignes mises à jour.
    """
    bp = _import_bronze()
    if not _DUCKDB_OK:
        print("[CONTACT] DuckDB non installé — skip.")
        return 0

    setup_contact_columns()

    con = bp._get_connection()
    try:
        rows = con.execute(f"""
            SELECT siren, denomination
            FROM {bp.SILVER_TABLE}
            ORDER BY bodacc_recent DESC, ma_score DESC
            LIMIT {top_n}
        """).fetchall()
    except Exception as e:
        print(f"[CONTACT] Lecture silver_ma : {e}")
        con.close()
        return 0

    print(f"[CONTACT] Enrichissement de {len(rows)} entreprises…")
    updated = 0
    RATE = 0.06   # 17 req/s (under the ~100 req/s limit, generous)
    BATCH = 100

    async with httpx.AsyncClient(
        headers={"User-Agent": "EdRCF/6.0"},
        follow_redirects=True,
    ) as client:
        for i, (siren, denomination) in enumerate(rows):
            contact = await _fetch_contact(siren, client)

            site_web      = contact.get("site_web", "")
            telephone     = contact.get("telephone", "")
            linkedin_url  = _guess_linkedin(denomination or "")
            email_domaine = _extract_domain(site_web)

            try:
                con.execute(f"""
                    UPDATE {bp.SILVER_TABLE}
                    SET site_web      = ?,
                        telephone     = ?,
                        linkedin_url  = ?,
                        email_domaine = ?
                    WHERE siren = ?
                """, [site_web or None, telephone or None,
                      linkedin_url or None, email_domaine or None,
                      siren])
                updated += 1
            except Exception as e:
                print(f"[CONTACT] UPDATE {siren}: {e}")

            if (i + 1) % BATCH == 0:
                print(f"[CONTACT] {i+1}/{len(rows)} traités "
                      f"({sum(1 for r in rows[:i+1] if r)}/{i+1} avec données)…")

            await asyncio.sleep(RATE)

    con.close()
    print(f"[CONTACT] Terminé — {updated:,} fiches enrichies.")
    return updated


# =============================================================================
# Stats
# =============================================================================

def contact_stats() -> dict:
    """Retourne des stats sur le taux de remplissage des colonnes contact."""
    bp = _import_bronze()
    if not _DUCKDB_OK:
        return {}
    con = bp._get_connection()
    try:
        total = con.execute(f"SELECT COUNT(*) FROM {bp.SILVER_TABLE}").fetchone()[0]
        with_web = con.execute(
            f"SELECT COUNT(*) FROM {bp.SILVER_TABLE} WHERE site_web IS NOT NULL"
        ).fetchone()[0]
        with_tel = con.execute(
            f"SELECT COUNT(*) FROM {bp.SILVER_TABLE} WHERE telephone IS NOT NULL"
        ).fetchone()[0]
        with_li = con.execute(
            f"SELECT COUNT(*) FROM {bp.SILVER_TABLE} WHERE linkedin_url IS NOT NULL"
        ).fetchone()[0]
        return {
            "total_silver":   total,
            "with_site_web":  with_web,
            "with_telephone": with_tel,
            "with_linkedin":  with_li,
            "pct_web": round(with_web/total*100, 1) if total else 0,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        con.close()


# =============================================================================
# CLI
# =============================================================================

async def _cli(cmd: str, args: list[str]) -> None:
    if cmd == "setup":
        setup_contact_columns()
    elif cmd == "enrich":
        n = int(args[0]) if args else 3000
        await enrich_contact_batch(top_n=n)
    elif cmd == "stats":
        import json
        print(json.dumps(contact_stats(), indent=2))
    else:
        print(__doc__)


if __name__ == "__main__":
    cmd  = sys.argv[1] if len(sys.argv) > 1 else "help"
    args = sys.argv[2:]
    asyncio.run(_cli(cmd, args))
