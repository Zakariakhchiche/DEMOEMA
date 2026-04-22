"""INPI Comptes annuels — via API RNE (registre-national-entreprises).

Auth : login email/password → JWT (PAS OAuth2 client_credentials).
Endpoint : https://registre-national-entreprises.inpi.fr/api/companies/{siren}
Rate limit : ~5 req/s (pas documenté officiellement, on reste prudent).

L'API RNE retourne formality + bilans imbriqués. On extrait chaque bilan comme
une ligne de bronze.inpi_comptes_raw. Pas d'endpoint bulk — on échantillonne
depuis bronze.insee_sirene_siret_raw (cible = SIRENs les + gros, filtrable NAF).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

LOGIN_URL = "https://registre-national-entreprises.inpi.fr/api/sso/login"
COMPANY_URL = "https://registre-national-entreprises.inpi.fr/api/companies/{siren}"
RATE_DELAY = 0.25   # 4 req/s — sûr
BATCH_SIZE_SIRENS = 100   # SIRENs par run (test initial ; scale après validation)
JWT_TTL_SECONDS = 25 * 60  # cache JWT 25 min (token vaut ~30 min)

_token_cache = {"value": None, "expires_at": 0.0}


async def _login_rne() -> str:
    """POST /api/sso/login avec username/password → JWT."""
    now = datetime.now(tz=timezone.utc).timestamp()
    if _token_cache["value"] and _token_cache["expires_at"] > now:
        return _token_cache["value"]

    if not settings.inpi_username or not settings.inpi_password:
        raise RuntimeError("INPI_USERNAME et/ou INPI_PASSWORD non configurés")

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            LOGIN_URL,
            json={"username": settings.inpi_username, "password": settings.inpi_password},
            headers={"Content-Type": "application/json"},
        )
        if r.status_code != 200:
            raise RuntimeError(f"INPI login échec: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        token = data.get("token")
        if not token:
            raise RuntimeError(f"INPI login sans token: {str(data)[:200]}")
        _token_cache["value"] = token
        _token_cache["expires_at"] = now + JWT_TTL_SECONDS
        return token


async def _pick_target_sirens(limit: int) -> list[str]:
    """Échantillon de SIRENs à enrichir : depuis bronze.insee_sirene_siret_raw,
    on prend les établissements siège (etablissement_siege=true) pas déjà vus
    dans bronze.inpi_comptes_raw."""
    sql = """
        WITH sieges AS (
          SELECT DISTINCT LEFT(payload->>'siren', 9) AS siren
          FROM bronze.insee_sirene_siret_raw
          WHERE (payload->>'etablissement_siege')::bool IS TRUE
          LIMIT %s
        )
        SELECT s.siren FROM sieges s
        WHERE s.siren IS NOT NULL
          AND length(s.siren) = 9
          AND NOT EXISTS (SELECT 1 FROM bronze.inpi_comptes_raw c WHERE c.siren = s.siren)
        LIMIT %s
    """
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (limit * 10, limit))
            rows = await cur.fetchall()
    return [r[0] for r in rows if r[0]]


async def _fetch_one_siren(client: httpx.AsyncClient, siren: str, token: str) -> dict | None:
    """GET /api/companies/{siren} avec Bearer JWT. Retourne dict ou None."""
    url = COMPANY_URL.format(siren=siren)
    try:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as e:
        log.warning("inpi %s: %s", siren, e)
        return None
    if r.status_code == 404:
        return None
    if r.status_code == 401:
        # token expiré mi-session
        return {"__reauth__": True}
    if r.status_code != 200:
        log.warning("inpi %s: HTTP %s %s", siren, r.status_code, r.text[:150])
        return None
    try:
        return r.json()
    except Exception as e:
        log.warning("inpi %s: json parse %s", siren, e)
        return None


def _extract_bilans(company_data: dict, siren: str) -> list[dict]:
    """Extrait la liste des bilans depuis la réponse RNE. Structure variable
    selon le type d'entité — on tente plusieurs chemins."""
    if not isinstance(company_data, dict):
        return []
    bilans = company_data.get("bilans")
    if isinstance(bilans, list):
        return bilans
    # Fallback : certains SIRENs exposent les bilans sous formality/content
    formality = company_data.get("formality") or {}
    content = formality.get("content") if isinstance(formality, dict) else None
    if isinstance(content, dict):
        b2 = content.get("bilans")
        if isinstance(b2, list):
            return b2
    return []


def _as_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except Exception:
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
        except Exception:
            return None


def _as_num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


async def fetch_inpi_comptes_annuels_delta() -> dict:
    if not settings.database_url:
        return {"source": "inpi_comptes_annuels", "rows": 0, "error": "no DB"}

    try:
        token = await _login_rne()
    except Exception as e:
        return {"source": "inpi_comptes_annuels", "rows": 0, "error": f"login: {e}"}

    sirens = await _pick_target_sirens(BATCH_SIZE_SIRENS)
    if not sirens:
        return {"source": "inpi_comptes_annuels", "rows": 0,
                "note": "no new SIRENs to enrich (all sampled sieges already fetched)"}

    total_inserted = 0
    total_fetched = 0
    total_companies = 0
    errors = 0

    async with httpx.AsyncClient(timeout=30,
                                  headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                for siren in sirens:
                    await asyncio.sleep(RATE_DELAY)
                    data = await _fetch_one_siren(client, siren, token)
                    if data and data.get("__reauth__"):
                        token = await _login_rne()
                        data = await _fetch_one_siren(client, siren, token)
                    if not data:
                        errors += 1
                        continue
                    total_companies += 1

                    bilans = _extract_bilans(data, siren)
                    for bilan in bilans:
                        if not isinstance(bilan, dict):
                            continue
                        total_fetched += 1
                        depot_id = str(bilan.get("id") or bilan.get("depot_id") or
                                       f"{siren}_{bilan.get('dateClotureExercice','')}")[:64]
                        try:
                            await cur.execute(
                                """
                                INSERT INTO bronze.inpi_comptes_raw
                                  (depot_id, siren, exercice_debut, exercice_fin,
                                   ca, ebitda, total_bilan, capitaux_propres, payload)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (depot_id) DO UPDATE SET
                                  payload = EXCLUDED.payload,
                                  ingested_at = now()
                                """,
                                (
                                    depot_id,
                                    siren[:9],
                                    _as_date(bilan.get("dateDebutExercice") or bilan.get("exercice_debut")),
                                    _as_date(bilan.get("dateClotureExercice") or bilan.get("exercice_fin")),
                                    _as_num(bilan.get("chiffreAffairesNet") or bilan.get("ca")),
                                    _as_num(bilan.get("ebitda")),
                                    _as_num(bilan.get("totalBilan") or bilan.get("total_bilan")),
                                    _as_num(bilan.get("capitauxPropres") or bilan.get("capitaux_propres")),
                                    Jsonb(bilan),
                                ),
                            )
                            if cur.rowcount > 0:
                                total_inserted += 1
                        except Exception as e:
                            log.warning("inpi insert fail %s: %s", depot_id, e)
                            errors += 1
                            try:
                                await conn.rollback()
                            except Exception:
                                pass
                    await conn.commit()

    return {
        "source": "inpi_comptes_annuels",
        "rows": total_inserted,
        "companies_fetched": total_companies,
        "bilans_seen": total_fetched,
        "errors": errors,
        "sample_size": len(sirens),
        "mode": "rne_jwt",
    }
