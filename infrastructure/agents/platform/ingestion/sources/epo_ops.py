"""EPO OPS — Brevets européens.

Source #53 d'ARCHITECTURE_DATA_V2.md. API publique EPO via OAuth2 client_credentials.
Endpoint : https://ops.epo.org/3.2/rest-services/published-data/search
Licence : Public / Etalab 2.0 par défaut (données publiques).
RGPD : pas de données personnelles sensibles (seulement titres, applicants, dates, classifications).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from config import settings

log = logging.getLogger(__name__)

EPO_OPS_ENDPOINT = "https://ops.epo.org/3.2/rest-services/published-data/search"
EPO_OPS_TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"
PAGE_SIZE = 100
MAX_PAGES_PER_RUN = 1000  # ~10k records max par run (limit EPO)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48
BULK_BATCH_SIZE = 500  # commit tous les 500 rows
TOKEN_CACHE = {"token": None, "expires_at": 0}


def _get_oauth2_token() -> str:
    """Récupère et met en cache un token OAuth2 client_credentials (valide 60min)."""
    now = datetime.now().timestamp()
    if TOKEN_CACHE["token"] and now < TOKEN_CACHE["expires_at"]:
        return TOKEN_CACHE["token"]

    client_id = settings.epo_ops_client_id
    client_secret = settings.epo_ops_client_secret
    if not (client_id and client_secret):
        raise RuntimeError("EPO_OPS_CLIENT_ID / EPO_OPS_CLIENT_SECRET non configurés")

    payload = {"grant_type": "client_credentials"}
    auth = (client_id, client_secret)

    with httpx.Client(timeout=30) as client:
        r = client.post(EPO_OPS_TOKEN_URL, data=payload, auth=auth)
        r.raise_for_status()
        data = r.json()
        TOKEN_CACHE["token"] = data["access_token"]
        TOKEN_CACHE["expires_at"] = now + data.get("expires_in", 3600) - 600  # -10min marge
        return TOKEN_CACHE["token"]


def _s(value) -> str:
    """Convertit n'importe quelle valeur en str sûre pour slicing (None → '')."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


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


async def fetch_epo_ops_delta() -> dict:
    """Récupère les brevets EPO OPS récents, dedup sur publication_number.
    1er run : 30 jours ; runs suivants : 48h (couvre délai publication).
    Auth : OAuth2 client_credentials (token mis en cache 50min)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    import psycopg as _pg
    async with await _pg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.epo_brevets_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    # Auth token
    token = _get_oauth2_token()

    async with httpx.AsyncClient(
        timeout=30,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "DEMOEMA-Agents/0.1",
        },
    ) as client:
        async with await _pg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "q": f"publication_date>={since}",
                        "numResults": PAGE_SIZE,
                        "start": offset + 1,
                        "view": "brief",
                    }
                    try:
                        r = await client.get(EPO_OPS_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("EPO OPS timeout after 30s")
                        break
                    if r.status_code != 200:
                        log.warning("EPO OPS HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    documents = data.get("ops:world-ip", {}).get("ops:biblio-data", {}).get("ops:document-inquiry", {}).get("ops:document", [])
                    if not documents:
                        break
                    total_fetched += len(documents)

                    batch: list[tuple] = []
                    for doc in documents:
                        pub_num = _s(doc.get("publication-reference", {}).get("doc-number", ""))
                        if not pub_num:
                            continue

                        title = _s(doc.get("invention-title", {}).get("#text", ""))
                        applicants = [_s(a.get("name", "")) for a in (doc.get("applicants", []) or [])]
                        date_filed = _parse_date(doc.get("application-reference", {}).get("date", ""))
                        ipc_classes = [_s(c.get("symbol", "")) for c in (doc.get("classifications-ipcr", []) or [])]

                        payload = json.dumps({
                            "publication_number": pub_num,
                            "title": title,
                            "applicants": applicants,
                            "date_filed": date_filed.isoformat() if date_filed else None,
                            "ipc_classes": ipc_classes,
                            "raw": doc,
                        }, ensure_ascii=False)

                        batch.append((
                            pub_num[:32],
                            title,
                            applicants,
                            date_filed,
                            ipc_classes,
                            payload,
                        ))

                        if len(batch) >= BULK_BATCH_SIZE:
                            try:
                                await cur.executemany(
                                    """
                                    INSERT INTO bronze.epo_brevets_raw
                                      (publication_number, title, applicants, date_filed, ipc_classes, payload)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (publication_number) DO UPDATE SET
                                      payload = EXCLUDED.payload,
                                      ingested_at = now()
                                    """,
                                    batch,
                                )
                                total_inserted += cur.rowcount or 0
                                await conn.commit()
                                log.info("EPO OPS batch : %d inserted / %d fetched", total_inserted, total_fetched)
                            except Exception as e:
                                log.warning("Batch error: %s", e)
                            batch.clear()

                    if batch:
                        try:
                            await cur.executemany(
                                """
                                INSERT INTO bronze.epo_brevets_raw
                                  (publication_number, title, applicants, date_filed, ipc_classes, payload)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (publication_number) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                batch,
                            )
                            total_inserted += cur.rowcount or 0
                            await conn.commit()
                        except Exception as e:
                            log.warning("Final batch error: %s", e)

                    if len(documents) < PAGE_SIZE:
                        break

    return {
        "source": "epo_ops",
        "rows": total_inserted,
        "fetched": total_fetched,
        "skipped_existing": total_skipped,
        "since": since,
    }