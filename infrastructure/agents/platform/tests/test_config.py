"""Tests for config.Settings — verifies the resilient DSN derivation.

The whole point of the derivation: a fresh VPS only needs ONE secret
(DATALAKE_POSTGRES_ROOT_PASSWORD) to bring up the silver/bronze pipelines.
A regression here breaks migration.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def fresh_settings(monkeypatch):
    """Reload config with a clean env so each test starts from defaults.

    Settings is instantiated at import-time so we have to clear env vars
    AND reimport the module to pick up the changes.
    """
    for var in (
        "DATABASE_URL",
        "DATALAKE_POSTGRES_ROOT_PASSWORD",
        "DATALAKE_HOST",
        "DATALAKE_PORT",
        "DATALAKE_DB",
        "DATALAKE_USER",
    ):
        monkeypatch.delenv(var, raising=False)
    # Pydantic settings also reads from .env file by default; redirect to /dev/null.
    monkeypatch.setenv("PYDANTIC_SETTINGS_ENV_FILE", "/dev/null")
    import config
    return importlib.reload(config).Settings


def test_database_url_explicit_wins(fresh_settings, monkeypatch):
    """An explicit DATABASE_URL must always be used as-is, even when a password
    is also provided (relevant when pointing at a managed Postgres)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@external.db:5432/mydb")
    monkeypatch.setenv("DATALAKE_POSTGRES_ROOT_PASSWORD", "ignored")
    s = fresh_settings()
    assert s.database_url == "postgresql://u:p@external.db:5432/mydb"


def test_database_url_derived_from_password(fresh_settings, monkeypatch):
    """The migration-friendly path: only the password is set, the DSN is built."""
    monkeypatch.setenv("DATALAKE_POSTGRES_ROOT_PASSWORD", "secretpw123")
    s = fresh_settings()
    assert s.database_url == "postgresql://postgres:secretpw123@datalake-db:5432/datalake"


def test_database_url_derived_url_encodes_password(fresh_settings, monkeypatch):
    """A password with @ or : characters must not break the DSN parser."""
    monkeypatch.setenv("DATALAKE_POSTGRES_ROOT_PASSWORD", "p@ss:w/rd")
    s = fresh_settings()
    # The literals @ : / must each be percent-encoded.
    assert "p%40ss%3Aw%2Frd" in s.database_url
    assert s.database_url.startswith("postgresql://postgres:")


def test_database_url_empty_when_nothing_set(fresh_settings):
    """No password, no explicit DSN → database_url stays empty so main.py
    can log the actionable error instead of attempting a bad connection."""
    s = fresh_settings()
    assert s.database_url == ""


def test_derived_dsn_respects_host_override(fresh_settings, monkeypatch):
    """If the operator points at a different Postgres on the same network,
    they can override the host without redeclaring the full DSN."""
    monkeypatch.setenv("DATALAKE_POSTGRES_ROOT_PASSWORD", "pw")
    monkeypatch.setenv("DATALAKE_HOST", "postgres.internal")
    monkeypatch.setenv("DATALAKE_PORT", "5433")
    s = fresh_settings()
    assert s.database_url == "postgresql://postgres:pw@postgres.internal:5433/datalake"
