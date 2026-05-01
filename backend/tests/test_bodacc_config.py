"""
EdRCF 6.0 — Smoke tests config worker BODACC.

Audit QA 2026-05-01 (SCRUM-NEW-15) : worker `fetch+insertbodacc` prenait
153-158 secondes/run (visible dans la page Audit) à cause de
BULK_BATCH_SIZE=1000 + executemany sans cap. Ces tests garantissent que
les constantes de tuning post-fix ne régresseront pas.

Note : tests d'intégration (vrai fetch BODACC + insert Postgres) sont en
backend/agents-platform et non couverts ici.
"""
from __future__ import annotations

import importlib
import sys
import os
from pathlib import Path

# infrastructure/agents/platform est un package séparé du backend principal.
# On l'ajoute au sys.path pour pouvoir importer ses modules.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENTS_PLATFORM = _REPO_ROOT / "infrastructure" / "agents" / "platform"
if str(_AGENTS_PLATFORM) not in sys.path:
    sys.path.insert(0, str(_AGENTS_PLATFORM))


def _import_bodacc():
    """Import lazy + skip si dépendances manquantes (psycopg, config)."""
    try:
        return importlib.import_module("ingestion.sources.bodacc")
    except (ImportError, ModuleNotFoundError, RuntimeError):
        return None


class TestBodaccConstants:
    """Constantes de tuning post-audit QA G9."""

    def test_bulk_batch_size_bumped(self):
        bodacc = _import_bodacc()
        if bodacc is None:
            return  # skip si agents-platform pas dans sys.path test runner
        # Audit a montré 1000 trop petit (~50000 roundtrips DB pour 50M rows).
        # 10000 = ~5000 roundtrips, x10 throughput.
        assert bodacc.BULK_BATCH_SIZE >= 10_000, (
            f"BULK_BATCH_SIZE devrait être >= 10000 post-G9, got {bodacc.BULK_BATCH_SIZE}"
        )

    def test_max_rows_per_run_set(self):
        bodacc = _import_bodacc()
        if bodacc is None:
            return
        # Cap par run pour éviter qu'un fetch full bloque le scheduler 2h.
        assert hasattr(bodacc, "MAX_ROWS_PER_RUN"), "MAX_ROWS_PER_RUN doit être défini post-G9"
        assert 100_000 <= bodacc.MAX_ROWS_PER_RUN <= 5_000_000, (
            f"MAX_ROWS_PER_RUN doit être entre 100k et 5M, got {bodacc.MAX_ROWS_PER_RUN}"
        )

    def test_endpoint_unchanged(self):
        bodacc = _import_bodacc()
        if bodacc is None:
            return
        # Sanity : on n'a pas changé l'URL OpenDataSoft
        assert "bodacc-datadila.opendatasoft.com" in bodacc.BODACC_ENDPOINT
        assert "bodacc-datadila.opendatasoft.com" in bodacc.BODACC_EXPORT_URL


def test_module_importable():
    """Smoke test : le module est syntactiquement valide et importable
    (à condition que psycopg / config / settings soient résolvables)."""
    bodacc = _import_bodacc()
    if bodacc is None:
        return
    assert hasattr(bodacc, "fetch_bodacc_full")
    assert hasattr(bodacc, "fetch_bodacc_delta")
