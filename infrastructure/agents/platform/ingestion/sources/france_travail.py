"""France Travail API — offres d'emploi publiques.

Source #63 d'ARCHITECTURE_DATA_V2.md. API publique OAuth2.
Endpoint : https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search
Licence : Etalab 2.0 — réutilisation libre.
RGPD : pas de données sensibles (seulement offres d'emploi publiques).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

FRANCE_TRAVAIL_ENDPOINT = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
AUTH_TOKEN_URL = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=/partenaire"
AUTH_SCOPE = "api_offresdemploiv2 o2dsoffre"
PAGE_SIZE = 150
MAX_PAGES_PER_RUN = 1000
BACKFILL_DAYS_FIRST_RUN = 3650
INCREMENTAL_HOURS = 24

# Token cache global (simple, pas thread-safe mais suffisant pour scheduler monoprocess)
_token_cache = {"value": None, "expires_at": 0}


async def _get_oauth2_token() -> str:
    """Récupère un token OAuth2 via client_credentials, avec cache 50min."""
    now = datetime.now(tz=timezone.utc).timestamp()
    if _token_cache["value"] and now < _token_cache["expires_at"]:
        return _token_cache["value"]

    client_id = settings.FRANCE_TRAVAIL_CLIENT_ID
    client_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
    if not client_id or not client_secret:
        raise RuntimeError("FRANCE_TRAVAIL_CLIENT_ID ou FRANCE_TRAVAIL_CLIENT_SECRET non configuré(s)")

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            AUTH_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": AUTH_SCOPE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code != 200:
            raise RuntimeError(f"OAuth2 token error: HTTP {r.status_code} — {r.text[:200]}")
        data = r.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        _token_cache["value"] = access_token
        _token_cache["expires_at"] = now + expires_in - 600  # 10min de marge
        return access_token


async def fetch_france_travail_delta() -> dict:
    """Récupère les offres d'emploi France Travail récentes, dedup sur offre_id.
    1er run : 7 jours ; runs suivants : 24h (couvre fréquence de mise à jour API).
    """
    if not settings.database_url:
        return {"error": "DATABASE_URL non configuré", "rows": 0}

    # Check if table is empty → première ingestion = backfill
    import psycopg as _pg
    async with await _pg.AsyncConnection.connect(settings.database_url) as _conn:
        async with _conn.cursor() as _cur:
            await _cur.execute("SELECT count(*) FROM bronze.france_travail_offres_raw LIMIT 1")
            existing = (await _cur.fetchone())[0]

    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)
    since = (datetime.now(tz=timezone.utc) - window).strftime("%Y-%m-%d")
    total_fetched = 0
    total_inserted = 0
    total_skipped = 0

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for page in range(MAX_PAGES_PER_RUN):
                    offset = page * PAGE_SIZE
                    token = await _get_oauth2_token()
                    params = {
                        "offset": offset,
                        "limit": PAGE_SIZE,
                        "dateCreation": f">={since}",
                        "order": "dateCreation",
                    }
                    r = await client.get(
                        FRANCE_TRAVAIL_ENDPOINT,
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if r.status_code != 200:
                        log.warning("France Travail HTTP %s: %s", r.status_code, r.text[:200])
                        break
                    data = r.json()
                    offres = data.get("offres", [])
                    if not offres:
                        break
                    total_fetched += len(offres)

                    # Upsert bronze
                    for offre in offres:
                        offre_id_raw = offre.get("id")
                        offre_id = _s(offre_id_raw)
                        if not offre_id:
                            total_skipped += 1
                            continue
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.france_travail_offres_raw
                                  (offre_id, intitule, entreprise_nom, entreprise_siret,
                                   type_contrat, lieu_travail, date_creation, salaire_libelle, rome_code, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (offre_id) DO UPDATE SET payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    offre_id[:64],
                                    _s(offre.get("intitule"))[:512],
                                    _s(offre.get("entreprise", {}).get("nom"))[:512],
                                    _s(offre.get("entreprise", {}).get("siret"))[:14],
                                    _s(offre.get("typeContrat"))[:32],
                                    _s(offre.get("lieuTravail", {}).get("libelle"))[:255],
                                    _parse_date(offre.get("dateCreation")),
                                    _s(offre.get("salaire", {}).get("libelle"))[:255],
                                    _s(offre.get("romeCode"))[:16],
                                    Jsonb(offre),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                            else:
                                total_skipped += 1
                        except Exception as e:
                            log.warning("Skip offre %s: %s", offre_id, e)
                            total_skipped += 1

                    await conn.commit()
                    if len(offres) < PAGE_SIZE:
                        break

    return {
        "source": "france_travail",
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