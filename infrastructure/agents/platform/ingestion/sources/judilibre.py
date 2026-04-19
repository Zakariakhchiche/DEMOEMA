"""Judilibre — Cour de Cassation + Cours d'appel + TJ + prud'hommes.

Source #34 d'ARCHITECTURE_DATA_V2.md. API publique OAuth2 via PISTE.
Endpoint : https://api.piste.gouv.fr/cassation/judilibre/v1.0/search
Licence : Open Licence 2.0 via data.gouv.fr
RGPD : Décisions anonymisées par défaut. Respecter pseudonymisation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

JUDILIBRE_ENDPOINT = "https://api.piste.gouv.fr/cassation/judilibre/v1.0/search"
PAGE_SIZE = 50
MAX_PAGES_PER_RUN = 1000  # ~1000 décisions par run (sécurité quota)
# Fenêtre de backfill initial large (JudiLibre publie avec 1-3j de délai typique)
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 48


def _get_auth_headers() -> dict:
    """Récupère le token OAuth2 (cache 50min via env)."""
    token = settings.judilibre_oauth_token
    if not token or settings.judilibre_token_expiry < datetime.now(timezone.utc):
        # Refresh token
        try:
            client_id = settings.piste_client_id
            client_secret = settings.piste_client_secret
            if not client_id or not client_secret:
                raise ValueError("PISTE_CLIENT_ID ou PISTE_CLIENT_SECRET non configuré")
            payload = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "openid",
            }
            r = httpx.post(
                "https://oauth.piste.gouv.fr/api/oauth/token",
                data=payload,
                timeout=30,
                headers={"User-Agent": "DEMOEMA-Agents/0.1"},
            )
            r.raise_for_status()
            data = r.json()
            token = data["access_token"]
            expiry = datetime.now(timezone.utc) + timedelta(minutes=50)
            # Stockage temporaire dans settings (via setter simulé)
            settings.judilibre_oauth_token = token
            settings.judilibre_token_expiry = expiry
        except Exception as e:
            log.error("Échec refresh token Judilibre: %s", e)
            raise
    return {"Authorization": f"Bearer {token}", "User-Agent": "DEMOEMA-Agents/0.1"}


async def fetch_judilibre_delta() -> dict:
    """Récupère les décisions Judilibre récentes, dedup sur decision_id.
    1er run : 7 jours ; runs suivants : 48h (couvre délai publication)."""
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM bronze.judilibre_decisions_raw LIMIT 1")
            existing = (await cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    try:
        headers = _get_auth_headers()
    except Exception as e:
        return {"error": f"Auth Judilibre échoué: {e}", "rows": 0}

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    params = {
                        "date_start": since,
                        "date_end": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "sort": "date_decision DESC",
                        "limit": PAGE_SIZE,
                        "offset": offset,
                    }
                    try:
                        r = await client.get(JUDILIBRE_ENDPOINT, params=params)
                    except httpx.TimeoutException:
                        log.warning("Judilibre timeout à la page %s", page)
                        break
                    if r.status_code != 200:
                        log.warning("Judilibre HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    records = data.get("decisions", [])
                    if not records:
                        break
                    total_fetched += len(records)

                    # Upsert bronze
                    for rec in records:
                        decision_id_raw = rec.get("id") or ""
                        decision_id = _s(decision_id_raw)[:128]
                        if not decision_id:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.judilibre_decisions_raw
                                  (decision_id, juridiction, chamber, date_decision, theme,
                                   numero_affaire, solution, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (decision_id) DO NOTHING
                                """,
                                (
                                    decision_id,
                                    _s(rec.get("jurisdiction"))[:64],
                                    _s(rec.get("chamber"))[:64],
                                    _parse_date(rec.get("decision_date")),
                                    _s(rec.get("themes", {}).get("title"))[:512],
                                    _s(rec.get("number"))[:64],
                                    _s(rec.get("solution"))[:128],
                                    Jsonb(rec),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip décision %s: %s", decision_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(records) < PAGE_SIZE:
                        break

    return {
        "source": "judilibre",
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
        import json as _json
        return _json.dumps(value, ensure_ascii=False)
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