"""Auth dependency centralisée pour les routes admin.

Avant : 3 implémentations dupliquées (`_check_secret` dans routers/admin.py,
`_check_admin_secret` dans main.py:2588, et l'inline `cron_secret = ...` dans
2 routes /api/refresh-targets et /api/admin/load-sector — audit ARCH-7).
Désormais : un seul `verify_cron_secret(secret)` réutilisable.

Comportement (audit SEC-2 CRITICAL) :
- Si `CRON_SECRET` env var n'est pas configurée → 503 (admin disabled).
  Avant le fix, l'absence laissait les endpoints publics.
- Si configurée et secret reçu mismatch → 401.
- Sinon → pass.
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Query


def verify_cron_secret(secret: str) -> None:
    """Lève HTTPException si non autorisé. À utiliser inline dans la route :

        from auth.cron_secret import verify_cron_secret

        @router.get("/admin/foo")
        async def admin_foo(secret: str = Query(default="")):
            verify_cron_secret(secret)
            ...

    Pour FastAPI Depends, voir `cron_secret_dep` ci-dessous.
    """
    cron = os.getenv("CRON_SECRET", "")
    if not cron:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoints disabled — CRON_SECRET not configured on server",
        )
    if secret != cron:
        raise HTTPException(status_code=401, detail="Unauthorized")


def cron_secret_dep(secret: str = Query(default="", description="Cron auth secret")) -> str:
    """Dependency FastAPI prête à l'emploi :

        from fastapi import Depends
        from auth.cron_secret import cron_secret_dep

        @router.get("/admin/foo", dependencies=[Depends(cron_secret_dep)])
        async def admin_foo():
            ...
    """
    verify_cron_secret(secret)
    return secret
