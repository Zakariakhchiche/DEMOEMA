"""Multi-tenant SaaS — contexte d'authentification (Clerk) + résolution org.

Architecture :
  - Le frontend (Clerk) envoie le JWT de session dans `Authorization: Bearer`.
  - On vérifie le JWT via le JWKS public Clerk (RS256), puis on résout / upsert
    l'utilisateur et l'organisation dans le schéma `app` (cf. migrations/app_schema_001.sql).
  - `get_tenant_context` est une dépendance FastAPI à injecter sur les routes
    qui manipulent des données par-tenant (watchlist, pipeline, recherches…).

Feature flag : si `AUTH_ENABLED` n'est pas "true", on renvoie un contexte
ANONYME (org de dev) → la prod actuelle continue de fonctionner sans login
tant que l'intégration Clerk n'est pas branchée. À activer une fois les clés
Clerk fournies (CLERK_JWKS_URL + CLERK_ISSUER).

Dépendances : PyJWT[crypto] (à ajouter au requirements si absent).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx

AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "").lower() == "true"
CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL", "")      # ex https://<app>.clerk.accounts.dev/.well-known/jwks.json
CLERK_ISSUER = os.environ.get("CLERK_ISSUER", "")          # ex https://<app>.clerk.accounts.dev

# Contexte de dev quand AUTH_ENABLED=false (prod actuelle mono-tenant)
_DEV_ORG = os.environ.get("DEV_ORG_SLUG", "origin-dev")


@dataclass
class TenantContext:
    clerk_user_id: str | None
    clerk_org_id: str | None
    email: str | None
    org_slug: str            # slug résolu (dev ou Clerk)
    is_anonymous: bool


# Cache JWKS (TTL 1h) — évite de refetch les clés publiques à chaque requête.
_jwks_cache: dict = {"keys": None, "fetched_at": 0.0}


async def _get_jwks() -> dict | None:
    if not CLERK_JWKS_URL:
        return None
    if _jwks_cache["keys"] and (time.time() - _jwks_cache["fetched_at"]) < 3600:
        return _jwks_cache["keys"]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(CLERK_JWKS_URL)
            if r.status_code == 200:
                _jwks_cache["keys"] = r.json()
                _jwks_cache["fetched_at"] = time.time()
                return _jwks_cache["keys"]
    except Exception as e:  # noqa: BLE001
        print(f"[tenant] JWKS fetch error: {type(e).__name__}: {e}")
    return None


async def verify_clerk_jwt(token: str) -> dict | None:
    """Vérifie un JWT Clerk (RS256) contre le JWKS public. Retourne les claims."""
    jwks = await _get_jwks()
    if jwks is None:
        return None
    try:
        import jwt  # PyJWT
        from jwt import PyJWKClient  # noqa: F401
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key is None:
            return None
        pub = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        claims = jwt.decode(
            token, pub, algorithms=["RS256"],
            issuer=CLERK_ISSUER or None,
            options={"verify_aud": False, "verify_iss": bool(CLERK_ISSUER)},
        )
        return claims
    except Exception as e:  # noqa: BLE001
        print(f"[tenant] JWT verify failed: {type(e).__name__}: {str(e)[:120]}")
        return None


async def upsert_user_org(pool, claims: dict) -> str:
    """Upsert user + org Clerk dans le schéma app, retourne l'org_slug."""
    clerk_uid = claims.get("sub")
    clerk_org = claims.get("org_id") or claims.get("o", {}).get("id") if isinstance(claims.get("o"), dict) else claims.get("org_id")
    email = claims.get("email")
    full_name = claims.get("name")
    # Upsert org (si pas d'org active Clerk, org perso = clerk_uid)
    org_key = clerk_org or f"u_{clerk_uid}"
    org_id = await pool.fetchval(
        """INSERT INTO app.organizations (clerk_org_id, name, slug)
           VALUES ($1, $2, $1)
           ON CONFLICT (clerk_org_id) DO UPDATE SET updated_at = now()
           RETURNING id""",
        org_key, (claims.get("org_name") or email or org_key),
    )
    user_id = await pool.fetchval(
        """INSERT INTO app.users (clerk_user_id, email, full_name, last_seen_at)
           VALUES ($1, $2, $3, now())
           ON CONFLICT (clerk_user_id) DO UPDATE SET last_seen_at = now(),
             email = COALESCE(EXCLUDED.email, app.users.email)
           RETURNING id""",
        clerk_uid, email, full_name,
    )
    await pool.execute(
        """INSERT INTO app.memberships (org_id, user_id, role)
           VALUES ($1, $2, 'owner') ON CONFLICT DO NOTHING""",
        org_id, user_id,
    )
    return org_key


def anonymous_context() -> TenantContext:
    return TenantContext(clerk_user_id=None, clerk_org_id=None, email=None,
                         org_slug=_DEV_ORG, is_anonymous=True)
