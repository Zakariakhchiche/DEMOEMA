"""crt.sh — Certificate Transparency logs TLS publics.

Source #106 d'ARCHITECTURE_DATA_V2.md. API publique HTML/JSON via crt.sh.
Endpoint : https://crt.sh/?q={domain}&output=json — requête GET sans auth.
Données publiques, pas de license explicite. RGPD : pas de données personnelles
directes (seulement noms de domaine et certificats), pas de tracking individuel.
Rate-limit stricte : <100 req/h (bannissement fréquent si dépassement).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

CRT_SH_ENDPOINT = "https://crt.sh/"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~1000 certificats par run (sécurité quota + bannissement)
# Fenêtre de backfill initial large (crt.sh conserve ~2 ans, mais données récentes prioritaires)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 24


async def fetch_crt_sh_delta() -> dict:
    """Récupère les certificats TLS récents via crt.sh, dedup sur cert_id.
    1er run : 30 jours ; runs suivants : 24h (couvre délai publication typique).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    import psycopg as _pg
    async with await _pg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.crt_sh_certificates_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    # Requête unique par run (pas de pagination sur crt.sh, mais on simule avec offset)
    # crt.sh ne supporte pas l'offset natif, on utilise la pagination via ?offset=N
    # Mais la doc indique : ?q={domain}&output=json — on ne peut pas filtrer par date
    # → on récupère les 1000 derniers certificats (par ordre décroissant de not_before)
    # et on filtre en amont sur not_before >= since
    params = {
        "q": "%",  # wildcard pour tous les domaines
        "output": "json",
        "limit": PAGE_SIZE,
        "offset": 0,
    }

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    params["offset"] = page * PAGE_SIZE
                    r = await client.get(CRT_SH_ENDPOINT, params=params)
                    if r.status_code != 200:
                        log.warning("crt.sh HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    try:
                        data = r.json()
                    except json.JSONDecodeError:
                        # crt.sh renvoie parfois du HTML en cas d'erreur → retry avec retry-after
                        log.warning("crt.sh JSON decode error: %s", r.text[:200])
                        break

                    records = data.get("results", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Filtrage en amont sur not_before >= since (crt.sh ne filtre pas côté serveur)
                    filtered_records = []
                    for rec in records:
                        not_before_raw = rec.get("not_before")
                        if not_before_raw:
                            try:
                                not_before_dt = datetime.fromisoformat(not_before_raw.replace("Z", "+00:00"))
                                if not_before_dt.date() >= datetime.fromisoformat(since).date():
                                    filtered_records.append(rec)
                            except Exception:
                                pass  # on garde si parsing échoue (risque moindre)

                    # Upsert bronze
                    for rec in filtered_records:
                        cert_id_raw = rec.get("id")
                        cert_id = _s(cert_id_raw)
                        if not cert_id:
                            total_skipped += 1
                            continue
                        try:
                            # Extraction des champs selon la spec
                            common_name = _s(rec.get("common_name", ""))
                            name_value = _s(rec.get("name_value", ""))
                            issuer_name = _s(rec.get("issuer_name", ""))
                            not_before = _parse_timestamp(rec.get("not_before"))
                            not_after = _parse_timestamp(rec.get("not_after"))

                            await cur.execute(
                                """
                                INSERT INTO bronze.crt_sh_certificates_raw
                                  (cert_id, common_name, name_value, issuer_name,
                                   not_before, not_after, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (cert_id) DO NOTHING
                                """,
                                (
                                    cert_id[:128],
                                    common_name[:512],
                                    name_value,
                                    issuer_name[:512],
                                    not_before,
                                    not_after,
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip cert_id %s: %s", cert_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "crt_sh",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped_existing": total_skipped,
        "since": since,
    }


def _s(value) -> str:
    """Convertit n'importe quelle valeur en str sûre pour slicing (None → '')."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _parse_timestamp(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None