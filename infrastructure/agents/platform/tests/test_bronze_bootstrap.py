"""Tests for bronze_bootstrap.list_missing_fetchers — the gap-detection
heuristic that decides what discover_and_generate gets called on.

These tests don't touch Postgres or LLMs; they only cover the spec-vs-source
filesystem walk.
"""
from __future__ import annotations

import pytest

from ingestion import bronze_bootstrap as bb


def _write_spec(specs_dir, name: str, source_id: str | None) -> None:
    body = ""
    if source_id is not None:
        body = f"source_id: {source_id}\nname: test {source_id}\n"
    (specs_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_lists_specs_without_matching_python(tmp_path, monkeypatch):
    specs = tmp_path / "specs"
    sources = tmp_path / "sources"
    specs.mkdir()
    sources.mkdir()
    _write_spec(specs, "alpha", "alpha")
    _write_spec(specs, "beta", "beta")
    (sources / "alpha.py").write_text("# placeholder", encoding="utf-8")  # exists
    # beta.py absent → missing

    monkeypatch.setattr(bb, "SPECS_DIR", specs)
    monkeypatch.setattr(bb, "SOURCES_DIR", sources)
    assert bb.list_missing_fetchers() == ["beta"]


def test_skips_specs_without_source_id(tmp_path, monkeypatch):
    specs = tmp_path / "specs"
    sources = tmp_path / "sources"
    specs.mkdir()
    sources.mkdir()
    _write_spec(specs, "no_id", None)  # no source_id → ignored
    _write_spec(specs, "good", "good")
    monkeypatch.setattr(bb, "SPECS_DIR", specs)
    monkeypatch.setattr(bb, "SOURCES_DIR", sources)
    assert bb.list_missing_fetchers() == ["good"]


def test_skips_underscore_prefixed_files(tmp_path, monkeypatch):
    specs = tmp_path / "specs"
    sources = tmp_path / "sources"
    specs.mkdir()
    sources.mkdir()
    _write_spec(specs, "_template", "template")
    _write_spec(specs, "real", "real")
    monkeypatch.setattr(bb, "SPECS_DIR", specs)
    monkeypatch.setattr(bb, "SOURCES_DIR", sources)
    assert bb.list_missing_fetchers() == ["real"]


def test_returns_empty_when_dirs_missing(tmp_path, monkeypatch):
    specs = tmp_path / "specs"
    sources = tmp_path / "sources"
    # ne pas créer les dossiers
    monkeypatch.setattr(bb, "SPECS_DIR", specs)
    monkeypatch.setattr(bb, "SOURCES_DIR", sources)
    assert bb.list_missing_fetchers() == []


def test_alphabetical_order(tmp_path, monkeypatch):
    specs = tmp_path / "specs"
    sources = tmp_path / "sources"
    specs.mkdir()
    sources.mkdir()
    for name in ("zebra", "alpha", "mango"):
        _write_spec(specs, name, name)
    monkeypatch.setattr(bb, "SPECS_DIR", specs)
    monkeypatch.setattr(bb, "SOURCES_DIR", sources)
    assert bb.list_missing_fetchers() == ["alpha", "mango", "zebra"]


def test_real_repo_specs_have_some_missing():
    """Sanity-check sur le vrai repo : au moins quelques specs orphelines.
    Si tout est couvert, ce test deviendra simplement un no-op."""
    missing = bb.list_missing_fetchers()
    assert isinstance(missing, list)
    # On ne fait pas d'assert trop strict : ce nombre va décroître au fil
    # des bootstrap ticks. Mais le typage et l'exécution doivent marcher.
