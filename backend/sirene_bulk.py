"""
EdRCF 6.0 — sirene_bulk.py
Pipeline d'ingestion du fichier SIRENE INSEE (16M entités) vers Supabase sirene_index.

Deux modes :
  bulk : télécharge StockUniteLegale_utf8.csv.gz (~2.5 Go) et filtre localement
         → idéal pour VPS ou usage local, construit l'index en ~20 minutes
  api  : sweep paginé via API Recherche Entreprises (Vercel-safe)
         → plus lent mais ne nécessite pas de dl massif

CLI :
  python sirene_bulk.py rebuild           → mode bulk complet
  python sirene_bulk.py api-sweep         → mode API (20 grands depts)
  python sirene_bulk.py api-sweep 75,69   → mode API depts spécifiques
  python sirene_bulk.py stats             → affiche les stats sirene_index
  python sirene_bulk.py bodacc-hot        → marque les SIRENs avec BODACC récent
"""

import asyncio
import csv
import gzip
import io
import os
import sys
import time
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator

import httpx
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Configuration
# =============================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
TABLE = "sirene_index"

SIRENE_FALLBACK_URL = "https://files.data.gouv.fr/insee-sirene/StockUniteLegale_utf8.csv.gz"
DATAGOUV_API = "https://www.data.gouv.fr/api/1/datasets/558dbb8c88ee386afc0c7d9b/"
BODACC_API = "https://bodacc-datadila.opendatasoft.com/api/records/1.0/search/"
RECHERCHE_API = "https://recherche-entreprises.api.gouv.fr/search"

UPSERT_BATCH = 500       # lignes par batch Supabase
BODACC_LOOKBACK_DAYS = 90
RATE_LIMIT_SLEEP = 0.15  # ~7 req/s pour l'API Recherche Entreprises

# =============================================================================
# Codes NAF cibles (format SIRENE : sans point, ex "6622Z")
# Doit rester synchronisé avec _LOAD_PROFILES dans data_sources.py
# =============================================================================

SIRENE_NAF_CODES: set[str] = {
    # ── Assurance / Finance ──────────────────────────────────────────────
    "6622Z", "6629Z", "6430Z", "6630Z", "6420Z", "6419Z",
    # ── Logistique / Transport ───────────────────────────────────────────
    "4941A", "4941B", "5210B", "5229A",
    # ── BTP / Construction ───────────────────────────────────────────────
    "4120A", "4321A", "4322A", "4399C", "4110A",
    # ── Services B2B / Conseil ───────────────────────────────────────────
    "7022Z", "6920Z", "6910Z", "7810Z", "8010Z", "8121Z", "8110Z",
    # ── MedTech / Santé ──────────────────────────────────────────────────
    "3250A", "8610Z", "4773Z", "2120Z", "8690B",
    # ── Industrie / Tech ─────────────────────────────────────────────────
    "2899B", "2611Z", "2932Z", "2452Z", "2512Z", "2591Z",
    # ── IT / SaaS / Digital ──────────────────────────────────────────────
    "6201Z", "6202A", "5829C", "6312Z",
    # ── Agroalimentaire ──────────────────────────────────────────────────
    "1089Z", "1102A", "1071A", "1011Z",
    # ── Energie / CleanTech ──────────────────────────────────────────────
    "3511Z", "7112B", "3831Z", "3700Z",
    # ── Commerce de gros ─────────────────────────────────────────────────
    "4669Z", "4663Z", "4639B", "4646Z",
    # ── Tourisme / Hôtellerie ────────────────────────────────────────────
    "5530Z", "5510Z", "5610A",
    # ── Immobilier ───────────────────────────────────────────────────────
    "4110B", "6832A",
    # ── Education / Formation ────────────────────────────────────────────
    "8559B", "8542Z",
    # ── Auto / Mobility ──────────────────────────────────────────────────
    "4511Z", "4520A",
    # ── Communication / Media ────────────────────────────────────────────
    "7311Z", "5814Z",
    # ── Aéronautique / Défense ───────────────────────────────────────────
    "3030Z", "3040Z",
}

# Tranches effectif correspondant à 10+ salariés (codes INSEE)
ELIGIBLE_EFFECTIF: set[str] = {"11", "12", "21", "22", "31", "32", "41", "42", "51", "52", "53"}

# Catégories juridiques éligibles (SAS, SARL, SA, SNC)
ELIGIBLE_CJ: set[str] = {
    "5498", "5499", "5710", "5720",  # SAS, SASU
    "5410", "5422",                   # SARL, EURL
    "5599", "5505", "5510", "5699",  # SA (différents types)
    "5307",                           # SNC
}

# 20 grands départements pour le sweep API
DEFAULT_DEPTS = [
    "75", "92", "93", "94",  # Paris + petite couronne
    "69", "13", "31", "33",  # Lyon, Marseille, Toulouse, Bordeaux
    "59", "67", "44", "06",  # Lille, Strasbourg, Nantes, Nice
    "34", "76", "38", "35",  # Montpellier, Rouen, Grenoble, Rennes
    "78", "91", "77", "95",  # Grande couronne Île-de-France
]

# =============================================================================
# Helpers Supabase (cohérent avec pappers_loader.py)
# =============================================================================

def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def _is_supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


async def _upsert_batch(client: httpx.AsyncClient, rows: list[dict]) -> bool:
    """Upsert un batch de lignes dans sirene_index. Retourne True si succès."""
    if not rows or not _is_supabase_configured():
        return False
    try:
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            json=rows,
            headers={**_supabase_headers(), "Prefer": "resolution=merge-duplicates"},
            timeout=30,
        )
        if r.status_code not in (200, 201):
            print(f"[SIRENE] Supabase upsert error: HTTP {r.status_code} — {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[SIRENE] Supabase upsert exception: {e}")
        return False


async def upsert_sirene_index(rows: list[dict], client: httpx.AsyncClient | None = None) -> int:
    """Upsert des lignes dans sirene_index en batches de UPSERT_BATCH.
    Retourne le nombre de lignes envoyées avec succès."""
    if not _is_supabase_configured():
        print("[SIRENE] Supabase non configuré — dry-run mode (données non sauvegardées)")
        return len(rows)

    total = 0
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=30)

    try:
        for i in range(0, len(rows), UPSERT_BATCH):
            batch = rows[i : i + UPSERT_BATCH]
            ok = await _upsert_batch(client, batch)
            if ok:
                total += len(batch)
    finally:
        if own_client:
            await client.aclose()

    return total


# =============================================================================
# Score M&A pré-enrichissement (basé sur données SIRENE uniquement)
# =============================================================================

_CURRENT_YEAR = datetime.now().year

_EFFECTIF_SCORE: dict[str, int] = {
    "11": 15,  # 10-19 salariés
    "12": 20,  # 20-49
    "21": 25,  # 50-99    ← sweet spot M&A
    "22": 25,  # 100-199  ← sweet spot M&A
    "31": 20,  # 200-249
    "32": 18,  # 250-499
    "41": 12,  # 500-999
    "42": 8,   # 1 000-1 999
    "51": 5,   # 2 000-4 999
    "52": 3,   # 5 000-9 999
    "53": 2,   # 10 000+
}

_CJ_SCORE: dict[str, int] = {
    "5498": 15, "5499": 15, "5710": 15, "5720": 15,  # SAS/SASU
    "5410": 14, "5422": 14,                           # SARL/EURL
    "5599": 12, "5505": 12, "5510": 12, "5699": 12,  # SA
    "5307": 8,                                        # SNC
}

# NAF codes les plus actifs en M&A (bonus +5)
_HIGH_MA_NAF: set[str] = {
    "6622Z", "6629Z", "6420Z", "6430Z",  # Finance/Assurance
    "7022Z", "6920Z",                    # Conseil/Compta
    "4941A", "4941B",                    # Transport
    "4120A",                             # Construction
    "6201Z", "6202A",                    # IT
}


def compute_ma_score_estimate(row: dict) -> int:
    """Score 0-100 basé uniquement sur les données SIRENE (aucun appel API).
    Permet de prioriser les enrichissements sans coût supplémentaire."""
    score = 0

    # ── Effectif (0-25 pts) ──────────────────────────────────────────────
    tranche = row.get("effectif_tranche", "")
    score += _EFFECTIF_SCORE.get(str(tranche), 0)

    # ── Ancienneté (0-20 pts) ────────────────────────────────────────────
    date_creation = row.get("date_creation", "")
    if date_creation:
        try:
            year_creation = int(str(date_creation)[:4])
            age = _CURRENT_YEAR - year_creation
            if 3 <= age < 5:
                score += 8
            elif 5 <= age < 10:
                score += 15
            elif 10 <= age <= 25:
                score += 20   # maturité optimale pour succession
            elif age > 25:
                score += 12
        except (ValueError, IndexError):
            pass

    # ── Forme juridique (0-15 pts) ───────────────────────────────────────
    cj = row.get("categorie_juridique", "")
    score += _CJ_SCORE.get(str(cj), 0)

    # ── Catégorie entreprise (0-15 pts) ──────────────────────────────────
    cat = row.get("categorie_entreprise", "")
    if cat == "ETI":
        score += 15
    elif cat == "PME":
        score += 10

    # ── NAF à forte activité M&A (0-5 pts bonus) ─────────────────────────
    naf = row.get("naf", "")
    if naf in _HIGH_MA_NAF:
        score += 5

    return min(score, 100)


# =============================================================================
# Mode BULK — téléchargement + parsing du fichier SIRENE complet
# =============================================================================

async def get_sirene_stock_url() -> str:
    """Interroge l'API data.gouv.fr pour obtenir l'URL courante du fichier SIRENE.
    Retourne l'URL du premier fichier .gz trouvé, sinon l'URL de fallback."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(DATAGOUV_API)
            if r.status_code == 200:
                resources = r.json().get("resources", [])
                for res in resources:
                    url = res.get("url", "")
                    title = res.get("title", "").lower()
                    if "stockuniteleg" in title and url.endswith(".csv.gz"):
                        print(f"[SIRENE] URL trouvée via data.gouv.fr API: {url}")
                        return url
    except Exception as e:
        print(f"[SIRENE] data.gouv.fr API error: {e} — utilisation URL de fallback")
    return SIRENE_FALLBACK_URL


async def download_sirene_stock(dest_path: str = "/tmp/sirene_ul.csv.gz") -> str:
    """Télécharge le fichier SIRENE en streaming vers dest_path.
    Affiche la progression toutes les 50 Mo.
    Retourne le chemin du fichier téléchargé."""
    url = await get_sirene_stock_url()
    print(f"[SIRENE] Téléchargement depuis: {url}")
    print(f"[SIRENE] Destination: {dest_path}")

    downloaded_bytes = 0
    last_report = 0
    MB = 1024 * 1024
    t0 = time.time()

    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            if total:
                print(f"[SIRENE] Taille totale: {total / MB:.0f} Mo")

            with open(dest_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 256):
                    f.write(chunk)
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes - last_report >= 50 * MB:
                        elapsed = time.time() - t0
                        speed = downloaded_bytes / elapsed / MB
                        pct = f"{100 * downloaded_bytes / total:.1f}%" if total else "?"
                        print(f"[SIRENE]   {downloaded_bytes / MB:.0f} Mo ({pct}) — {speed:.1f} Mo/s")
                        last_report = downloaded_bytes

    elapsed = time.time() - t0
    print(f"[SIRENE] Téléchargement terminé: {downloaded_bytes / MB:.0f} Mo en {elapsed:.0f}s")
    return dest_path


def iter_sirene_eligible(gz_path: str) -> Generator[dict, None, None]:
    """Générateur : lit le CSV gzippé ligne par ligne et yield les entreprises M&A-éligibles.
    Streaming — n'alloue pas tout le fichier en mémoire."""
    scanned = 0
    eligible = 0

    with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            scanned += 1

            # ── Filtre 1 : entreprise active ────────────────────────────
            if row.get("etatAdministratifUniteLegale") != "A":
                continue

            # ── Filtre 2 : PME ou ETI ────────────────────────────────────
            cat = row.get("categorieEntreprise", "")
            if cat not in ("PME", "ETI"):
                continue

            # ── Filtre 3 : effectif 10+ salariés ────────────────────────
            effectif = row.get("trancheEffectifsUniteLegale", "")
            if effectif not in ELIGIBLE_EFFECTIF:
                continue

            # ── Filtre 4 : NAF cible ─────────────────────────────────────
            naf = row.get("activitePrincipaleUniteLegale", "")
            if naf not in SIRENE_NAF_CODES:
                continue

            eligible += 1

            # ── Build row dict ───────────────────────────────────────────
            siren = row.get("siren", "").strip()
            if not siren or len(siren) != 9:
                continue

            # Nom : personnes morales ont denominationUniteLegale
            denomination = (
                row.get("denominationUniteLegale")
                or row.get("sigleUniteLegale")
                or f"{row.get('prenom1UniteLegale', '')} {row.get('nomUniteLegale', '')}".strip()
            )

            date_creation = row.get("dateCreationUniteLegale", "") or None
            cj = row.get("categorieJuridiqueUniteLegale", "")

            yield {
                "siren": siren,
                "denomination": denomination[:255] if denomination else "",
                "naf": naf,
                "dept": "",        # Pas dans UniteLegale — rempli à l'enrichissement
                "effectif_tranche": effectif,
                "date_creation": date_creation,
                "categorie_juridique": cj,
                "categorie_entreprise": cat,
                "bodacc_recent": False,
                "enriched": False,
            }

            if scanned % 500_000 == 0:
                print(f"[SIRENE]   Scanné: {scanned:,} — Éligibles: {eligible:,}")


async def run_full_rebuild(progress_callback=None) -> dict:
    """Pipeline complet : télécharge SIRENE → filtre → upsert Supabase.
    Retourne les stats du rebuild."""
    t0 = time.time()
    gz_path = "/tmp/sirene_ul.csv.gz"

    print("[SIRENE] === Démarrage rebuild complet ===")

    # ── Étape 1 : Téléchargement ─────────────────────────────────────────
    try:
        await download_sirene_stock(gz_path)
    except Exception as e:
        print(f"[SIRENE] Erreur téléchargement: {e}")
        return {"error": str(e)}

    # ── Étape 2 : Parse + filtre + calcul score ──────────────────────────
    print("[SIRENE] Parsing du fichier CSV...")
    batch: list[dict] = []
    total_scanned = 0
    total_eligible = 0
    total_upserted = 0

    async with httpx.AsyncClient(timeout=30) as client:
        for row in iter_sirene_eligible(gz_path):
            total_scanned += 1  # compteur lignes éligibles ici (post-filtre)
            row["ma_score_estimate"] = compute_ma_score_estimate(row)
            batch.append(row)

            if len(batch) >= UPSERT_BATCH:
                n = await upsert_sirene_index(batch, client)
                total_upserted += n
                total_eligible += len(batch)
                batch = []

                if progress_callback:
                    progress_callback({
                        "eligible": total_eligible,
                        "upserted": total_upserted,
                        "elapsed": time.time() - t0,
                    })
                print(f"[SIRENE]   Upserted: {total_upserted:,} (batch ok)")

        # Dernier batch
        if batch:
            n = await upsert_sirene_index(batch, client)
            total_upserted += n
            total_eligible += len(batch)

    # ── Étape 3 : Nettoyage ──────────────────────────────────────────────
    try:
        os.remove(gz_path)
        print(f"[SIRENE] Fichier temporaire supprimé: {gz_path}")
    except OSError:
        pass

    elapsed = time.time() - t0
    result = {
        "total_eligible": total_eligible,
        "total_upserted": total_upserted,
        "elapsed_seconds": round(elapsed, 1),
        "elapsed_human": f"{elapsed / 60:.1f} minutes",
    }
    print(f"[SIRENE] === Rebuild terminé: {result} ===")
    return result


# =============================================================================
# Mode API — sweep paginé (Vercel-safe, sans bulk download)
# =============================================================================

async def api_mode_sweep(
    depts: list[str] | None = None,
    max_per_naf: int = 25,
) -> dict:
    """Sweep paginé via API Recherche Entreprises.
    Pour chaque (NAF × département), récupère jusqu'à max_per_naf entreprises.
    Retourne les stats du sweep."""
    from data_sources import search_companies_gouv

    dept_list = depts or DEFAULT_DEPTS
    t0 = time.time()

    print(f"[SIRENE-API] Sweep {len(SIRENE_NAF_CODES)} NAF × {len(dept_list)} depts...")

    rows_to_upsert: list[dict] = []
    seen_sirens: set[str] = set()
    total_new = 0

    async with httpx.AsyncClient(timeout=30) as supabase_client:
        for naf in SIRENE_NAF_CODES:
            for dept in dept_list:
                try:
                    results = await search_companies_gouv(
                        code_naf=naf,
                        departement=dept,
                        per_page=max_per_naf,
                    )
                    for company in results:
                        siren = company.get("siren", "")
                        if not siren or siren in seen_sirens:
                            continue
                        seen_sirens.add(siren)
                        siege = company.get("siege", {}) or {}
                        cp = siege.get("code_postal", "") or ""

                        row = {
                            "siren": siren,
                            "denomination": company.get("nom_entreprise", "")[:255],
                            "naf": naf,
                            "dept": dept,
                            "effectif_tranche": "",
                            "date_creation": company.get("date_creation") or None,
                            "categorie_juridique": "",
                            "categorie_entreprise": company.get("categorie_entreprise", ""),
                            "bodacc_recent": False,
                            "enriched": False,
                        }
                        row["ma_score_estimate"] = compute_ma_score_estimate(row)
                        rows_to_upsert.append(row)

                        if len(rows_to_upsert) >= UPSERT_BATCH:
                            n = await upsert_sirene_index(rows_to_upsert, supabase_client)
                            total_new += n
                            rows_to_upsert = []
                            print(f"[SIRENE-API] Upserted: {total_new:,}")

                except Exception as e:
                    print(f"[SIRENE-API] Erreur NAF={naf} dept={dept}: {e}")

                await asyncio.sleep(RATE_LIMIT_SLEEP)

        # Dernier batch
        if rows_to_upsert:
            n = await upsert_sirene_index(rows_to_upsert, supabase_client)
            total_new += n

    elapsed = time.time() - t0
    result = {
        "total_new": total_new,
        "depts_swept": len(dept_list),
        "naf_codes": len(SIRENE_NAF_CODES),
        "elapsed_seconds": round(elapsed, 1),
    }
    print(f"[SIRENE-API] Sweep terminé: {result}")
    return result


# =============================================================================
# BODACC hot — marque les SIRENs avec annonces récentes
# =============================================================================

async def mark_bodacc_hot(client: httpx.AsyncClient | None = None) -> int:
    """Pour les SIRENs dans sirene_index, vérifie les annonces BODACC récentes (90j).
    Met à jour bodacc_recent=true et augmente ma_score_estimate de 25.
    Retourne le nombre de SIRENs marqués."""
    if not _is_supabase_configured():
        print("[SIRENE-BODACC] Supabase non configuré — skip")
        return 0

    cutoff = (datetime.utcnow() - timedelta(days=BODACC_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    marked = 0

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=20)

    try:
        # Récupérer les SIRENs non encore marqués BODACC (par batch de 500)
        offset = 0
        while True:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/{TABLE}",
                params={
                    "bodacc_recent": "eq.false",
                    "select": "siren,ma_score_estimate",
                    "limit": 500,
                    "offset": offset,
                },
                headers=_supabase_headers(),
            )
            if r.status_code != 200 or not r.json():
                break

            sirens_batch = r.json()
            if not sirens_batch:
                break

            for item in sirens_batch:
                siren = item["siren"]
                try:
                    bodacc_r = await client.get(
                        BODACC_API,
                        params={
                            "dataset": "annonces-commerciales",
                            "q": siren,
                            "rows": 1,
                            "sort": "-dateparution",
                            "fields": "siren,dateparution,typeavis_lib",
                        },
                        timeout=10,
                    )
                    if bodacc_r.status_code == 200:
                        records = bodacc_r.json().get("records", [])
                        if records:
                            date_pub = records[0].get("fields", {}).get("dateparution", "")
                            if date_pub >= cutoff:
                                new_score = min(item["ma_score_estimate"] + 25, 100)
                                await client.patch(
                                    f"{SUPABASE_URL}/rest/v1/{TABLE}?siren=eq.{siren}",
                                    json={"bodacc_recent": True, "ma_score_estimate": new_score},
                                    headers={**_supabase_headers(), "Prefer": "resolution=merge-duplicates"},
                                )
                                marked += 1
                except Exception:
                    pass
                await asyncio.sleep(0.12)  # ~8 req/s BODACC

            offset += 500
            if len(sirens_batch) < 500:
                break

    finally:
        if own_client:
            await client.aclose()

    print(f"[SIRENE-BODACC] {marked} SIRENs marqués bodacc_recent=true")
    return marked


# =============================================================================
# Stats sirene_index
# =============================================================================

async def get_index_stats() -> dict:
    """Affiche les stats de la table sirene_index."""
    if not _is_supabase_configured():
        return {"configured": False}

    stats = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for label, params in [
            ("total", {}),
            ("enriched", {"enriched": "eq.true"}),
            ("bodacc_hot", {"bodacc_recent": "eq.true"}),
            ("high_score", {"ma_score_estimate": "gte.60"}),
        ]:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/{TABLE}",
                params={**params, "select": "count"},
                headers={**_supabase_headers(), "Prefer": "count=exact"},
            )
            count = int(r.headers.get("content-range", "0/0").split("/")[-1])
            stats[label] = count

    return stats


# =============================================================================
# CLI
# =============================================================================

async def _cli_main():
    args = sys.argv[1:]
    cmd = args[0] if args else "stats"

    if cmd == "rebuild":
        result = await run_full_rebuild()
        print(f"\n✓ Rebuild terminé: {result}")

    elif cmd == "api-sweep":
        depts = args[1].split(",") if len(args) > 1 else None
        result = await api_mode_sweep(depts)
        print(f"\n✓ Sweep API terminé: {result}")

    elif cmd == "bodacc-hot":
        marked = await mark_bodacc_hot()
        print(f"\n✓ {marked} SIRENs marqués BODACC hot")

    elif cmd == "stats":
        stats = await get_index_stats()
        if not stats.get("configured", True):
            print("⚠ Supabase non configuré (SUPABASE_URL / SUPABASE_KEY manquants)")
            return
        print("\n── sirene_index stats ──────────────────────")
        for k, v in stats.items():
            print(f"  {k:20} : {v:,}")
        print("────────────────────────────────────────────")

    else:
        print(f"Commande inconnue: {cmd}")
        print("Usage: python sirene_bulk.py [rebuild|api-sweep|bodacc-hot|stats]")


if __name__ == "__main__":
    asyncio.run(_cli_main())
