"""Test fixtures for the silver codegen pipeline.

Adds `infrastructure/agents/platform/` to sys.path so `ingestion.silver_codegen`
imports without any DEMOEMA backend dep. Stubs out the heavy modules
(`config`, `loader`, `ollama_client`) that the codegen module imports at top
level — they require Postgres/Ollama at import-time which we don't want for
pure unit tests.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLATFORM_DIR))


def _stub(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# Minimal `config.settings` — codegen reads `settings.database_url`. None disables DB.
_stub("config", settings=types.SimpleNamespace(database_url=None))

# `loader.get_agent` is only called when generating SQL via LLM, but importing
# the module hits the agent prompt loader. Stub to a no-op.
_stub("loader", get_agent=lambda _name: None)

# `ollama_client.OllamaClient` would attempt HTTP setup at construction. Stub a
# class that is never instantiated by validation/topo-sort tests.
class _OllamaStub:  # noqa: D401 — test stub
    def __init__(self, *_a, **_kw):
        raise RuntimeError("OllamaClient not available in unit tests")

    async def close(self):
        pass


_stub("ollama_client", OllamaClient=_OllamaStub)


# psycopg is not installed in the dev/test environment of this repo. The pure
# functions under test (validate_sql, topo_sort_specs, extract_sql) never call
# into psycopg, so a minimal stub covering `connect` lets the module import.
class _PsycopgConnStub:
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def cursor(self):
        return self

    def execute(self, *_a, **_kw):
        return self

    def fetchall(self):
        return []

    def commit(self):
        pass


_stub("psycopg", connect=lambda *_a, **_kw: _PsycopgConnStub())
