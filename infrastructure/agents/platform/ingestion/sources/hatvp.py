"""HATVP — Haute Autorité pour la Transparence de la Vie Publique.

Source #95 d'ARCHITECTURE_DATA_V2.md. Données publiques sous licence Etalab 2.0.
Endpoint CSV gzippé : https://static.data.gouv.fr/resources/donnees-du-repertoire-des-representants-dinterets-au-format-csv/20250610-152044/1-informations-generales.csv.gz
Pas d'auth. RGPD : on stocke uniquement les données non sensibles (pas de données personnelles détaillées).
Pattern : rest_json_bulk via CSV décompressé (fichier unique, pas de pagination).
"""
from __future__ import annotations

import gzip
import io
import json
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

HATVP_ENDPOINT = "https://static.data.gouv.fr/resources/donnees-du-repertoire-des-representants-dinterets-au-format-csv/20250610-152044/1-informations-generales.csv.gz"
PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 100000
# FULL historique par bulk export streamé (3215+ représentants → ~100 KB décompressé)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 87600
BULK_BATCH_SIZE = 1000  # commit tous les 1000 rows


async def count_upstream() -> int | None:
    """Compteur amont HATVP via HEAD request (Content-Length → estimation)."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.head(HATVP_ENDPOINT)
            if r.status_code != 200:
                return None
            size = int(r.headers.get("Content-Length", "0"))
            # ~100 KB décompressé → ~1000 lignes → ~1000 représentants
            return size // 100 if size > 0 else None
    except Exception:
        return None


async def fetch_hatvp_delta() -> dict:
    """Récupère les représentants HATVP, dedup sur representant_id.
    1er run : backfill complet (toutes données) ; runs suivants : 48h (couvre délai mise à jour).
    Pattern : CSV gzippé → décompressé → parse ligne par ligne."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.hatvp_representants_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    async with httpx.AsyncClient(timeout=7200, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                # Fetch gzipped CSV
                r = await client.get(HATVP_ENDPOINT)
                if r.status_code != 200:
                    return {"error": f"HTTP {r.status_code}", "rows": 0}

                # Décompresser le contenu
                try:
                    content = gzip.decompress(r.content).decode("utf-8")
                except UnicodeDecodeError:
                    # Fallback : essayer latin-1 si UTF-8 échoue
                    content = gzip.decompress(r.content).decode("latin-1")

                # Parse CSV ligne par ligne
                lines = content.strip().split("\n")
                if not lines:
                    return {"error": "CSV vide", "rows": 0}

                # Extraire header
                header = [normalize_header(h) for h in lines[0].split(";")]
                lines = lines[1:]

                batch: list[tuple] = []
                for line in lines:
                    if not line.strip():
                        continue
                    total_fetched += 1
                    try:
                        values = line.split(";")
                        if len(values) < len(header):
                            values.extend([""] * (len(header) - len(values)))
                        rec = dict(zip(header, values))
                    except Exception:
                        total_errors += 1
                        continue

                    # Extraire champ clé
                    representant_id = _s(rec.get("id") or "")
                    if not representant_id:
                        total_skipped += 1
                        continue

                    # Construire payload complet
                    payload = Jsonb(rec)

                    # Extraire champs selon spec
                    try:
                        batch.append((
                            representant_id[:64],
                            _s(rec.get("denomination"))[:512],
                            _s(rec.get("siren"))[:9],
                            _s(rec.get("secteurActivite"))[:255],
                            _parse_date(rec.get("dateInscription")),
                            _s(rec.get("adresseVille"))[:255],
                            _int(rec.get("nbDeputes")),
                            _numeric(rec.get("caLobbying")),
                            payload,
                        ))
                    except Exception:
                        total_errors += 1
                        continue

                    if len(batch) >= BULK_BATCH_SIZE:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.hatvp_representants_raw
                                  (representant_id, denomination, siren, secteur_activite,
                                   date_inscription, adresse_ville, nb_deputes, chiffre_affaires_lobbying, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (representant_id) DO UPDATE SET
                                  denomination = EXCLUDED.denomination,
                                  siren = EXCLUDED.siren,
                                  secteur_activite = EXCLUDED.secteur_activite,
                                  date_inscription = EXCLUDED.date_inscription,
                                  adresse_ville = EXCLUDED.adresse_ville,
                                  nb_deputes = EXCLUDED.nb_deputes,
                                  chiffre_affaires_lobbying = EXCLUDED.chiffre_affaires_lobbying,
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                            log.info("HATVP bulk : %d inserted / %d fetched", total_inserted, total_fetched)
                        except Exception as e:
                            log.warning("Batch error: %s", e)
                            total_errors += len(batch)
                        batch.clear()

                # Flush final batch
                if batch:
                    try:
                        await cur.executemany(
                            """
                            INSERT INTO bronze.hatvp_representants_raw
                              (representant_id, denomination, siren, secteur_activite,
                               date_inscription, adresse_ville, nb_deputes, chiffre_affaires_lobbying, payload)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (representant_id) DO UPDATE SET
                              denomination = EXCLUDED.denomination,
                              siren = EXCLUDED.siren,
                              secteur_activite = EXCLUDED.secteur_activite,
                              date_inscription = EXCLUDED.date_inscription,
                              adresse_ville = EXCLUDED.adresse_ville,
                              nb_deputes = EXCLUDED.nb_deputes,
                              chiffre_affaires_lobbying = EXCLUDED.chiffre_affaires_lobbying,
                              payload = EXCLUDED.payload,
                              ingested_at = now()
                            """,
                            batch,
                        )
                        total_inserted += cur.rowcount or 0
                        await conn.commit()
                    except Exception as e:
                        log.warning("Final batch error: %s", e)

    return {
        "source": "hatvp",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped": total_skipped,
        "errors": total_errors,
        "mode": "bulk_full",
    }


def _s(value) -> str:
    """Convertit n'importe quelle valeur en str sûre pour slicing (None → '')."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _int(value) -> int | None:
    """Parse int avec fallback None."""
    try:
        return int(float(_s(value)))
    except Exception:
        return None


def _numeric(value) -> float | None:
    """Parse NUMERIC (float) avec fallback None."""
    try:
        return float(_s(value).replace(",", "."))
    except Exception:
        return None


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return None


def normalize_header(h: str) -> str:
    """Normaliser les headers CSV (ex: 'secteurActivite' → 'secteurActivite')."""
    return re.sub(r"[^a-zA-Z0-9_]", "", h)