"""Tests anti-régression pour les fixes sécurité de la session audit backend.

Verrouille :
- SEC-2 : auth bypass admin si CRON_SECRET vide → fail-fast 503
- SEC-1 : CORS regex restreinte aux domaines DEMOEMA propres
- SEC-3 : usage de defusedxml partout (pas de xml.etree stdlib brut)
- SEC-10 : targets_cache.json dans .dockerignore

Ces tests font confiance au monkeypatch de l'env CRON_SECRET (pas de
modification permanente de l'env du process).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# SEC-2 — Admin secret fail-fast
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_secret_check_fails_when_cron_secret_unset(monkeypatch):
    """Si CRON_SECRET n'est pas configuré → 503 (admin endpoints disabled)."""
    monkeypatch.delenv("CRON_SECRET", raising=False)
    from routers.admin import _check_secret
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _check_secret("any-secret")
    assert exc.value.status_code == 503
    assert "CRON_SECRET" in str(exc.value.detail)


def test_admin_secret_check_fails_with_wrong_secret(monkeypatch):
    """Si CRON_SECRET set mais mismatch → 401."""
    monkeypatch.setenv("CRON_SECRET", "real-secret")
    from routers.admin import _check_secret
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _check_secret("wrong-secret")
    assert exc.value.status_code == 401


def test_admin_secret_check_passes_with_right_secret(monkeypatch):
    """Si CRON_SECRET set et match → no exception."""
    monkeypatch.setenv("CRON_SECRET", "real-secret")
    from routers.admin import _check_secret
    _check_secret("real-secret")  # no raise


def test_main_check_admin_secret_fail_fast(monkeypatch):
    """Le _check_admin_secret de main.py doit aussi fail-fast (3e site dupliqué)."""
    monkeypatch.delenv("CRON_SECRET", raising=False)
    from main import _check_admin_secret
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        _check_admin_secret("any")
    assert exc.value.status_code == 503


# ─────────────────────────────────────────────────────────────────────────────
# SEC-1 — CORS regex scoped to DEMOEMA only
# ─────────────────────────────────────────────────────────────────────────────

def test_cors_regex_blocks_random_vercel_subdomain():
    """La regex CORS ne doit PAS matcher https://attacker-app.vercel.app
    (avant le fix elle matchait, → leak credentials cookies)."""
    import main
    middleware = next(
        (m for m in main.app.user_middleware if "CORSMiddleware" in str(m.cls)),
        None,
    )
    assert middleware is not None, "CORS middleware introuvable"
    regex = middleware.kwargs.get("allow_origin_regex") or ""
    # Domaines random vercel/cf NE DOIVENT PAS matcher
    assert not re.match(regex, "https://attacker-app.vercel.app")
    assert not re.match(regex, "https://random-team.pages.dev")
    assert not re.match(regex, "https://evil.workers.dev")


def test_cors_regex_allows_demoema_preview():
    """Les preview Vercel/CF du projet DEMOEMA doivent passer."""
    import main
    middleware = next(m for m in main.app.user_middleware if "CORSMiddleware" in str(m.cls))
    regex = middleware.kwargs.get("allow_origin_regex") or ""
    assert re.match(regex, "https://demoema.vercel.app")
    assert re.match(regex, "https://demoema-pr-42.vercel.app")
    assert re.match(regex, "https://demoema-staging.pages.dev")


# ─────────────────────────────────────────────────────────────────────────────
# SEC-3 — defusedxml usage
# ─────────────────────────────────────────────────────────────────────────────

def test_main_uses_defusedxml_not_stdlib():
    """main.py ne doit PAS importer xml.etree.ElementTree stdlib (XXE/billion-laughs).
    Doit importer defusedxml.ElementTree."""
    src = Path(__file__).resolve().parent.parent / "main.py"
    content = src.read_text(encoding="utf-8")
    assert "from defusedxml" in content, "defusedxml manquant dans main.py"
    # Le pattern stdlib `xml.etree.ElementTree as ET` ne doit plus apparaître
    assert "import xml.etree" not in content, (
        "xml.etree stdlib encore importé dans main.py — utiliser defusedxml"
    )


def test_bronze_pipeline_uses_defusedxml_not_stdlib():
    """bronze_pipeline.py doit aussi utiliser defusedxml (BODACC DILA, SIRENE)."""
    src = Path(__file__).resolve().parent.parent / "bronze_pipeline.py"
    content = src.read_text(encoding="utf-8")
    assert "from defusedxml" in content
    assert "import xml.etree" not in content


# ─────────────────────────────────────────────────────────────────────────────
# SEC-10 — IP métier hors image Docker
# ─────────────────────────────────────────────────────────────────────────────

def test_dockerignore_excludes_targets_cache():
    """targets_cache.json (IP métier scoring) ne doit PAS être copié dans l'image."""
    dockerignore = Path(__file__).resolve().parent.parent / ".dockerignore"
    content = dockerignore.read_text(encoding="utf-8")
    assert "targets_cache.json" in content
