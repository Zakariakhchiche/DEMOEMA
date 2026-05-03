"""Validate Soda Core configuration & checks YAML files (Sprint 2 — L4 dim 8).

Tourne sans connexion Postgres : se contente de vérifier la structure
des fichiers YAML pour catch toute régression (clé manquante, syntaxe
cassée, schema inattendu) AVANT que le scan quotidien CI ne tourne.

Cible :
- qa/soda/configuration.yml          — connexion + schema default
- qa/soda/checks/<table>.yml         — au moins 8 fichiers, ≥ 1 check chacun
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


# Repo root = parent of `backend/`
REPO_ROOT = Path(__file__).resolve().parents[2]
SODA_DIR = REPO_ROOT / "qa" / "soda"
CONFIG_FILE = SODA_DIR / "configuration.yml"
CHECKS_DIR = SODA_DIR / "checks"

# Toutes les tables qu'on s'attend à couvrir Sprint 2 (mission 1.2).
EXPECTED_CHECK_FILES = {
    "silver_inpi_comptes.yml",
    "silver_inpi_dirigeants.yml",
    "silver_opensanctions.yml",
    "silver_bodacc_annonces.yml",
    "silver_insee_unites_legales.yml",
    "silver_recherche_entreprises.yml",
    "gold_entreprises_master.yml",
    "gold_scoring_ma.yml",
}


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_soda_dir_layout_exists() -> None:
    assert SODA_DIR.is_dir(), f"missing {SODA_DIR}"
    assert CONFIG_FILE.is_file(), f"missing {CONFIG_FILE}"
    assert CHECKS_DIR.is_dir(), f"missing {CHECKS_DIR}"


def test_configuration_yml_parses_and_has_data_source() -> None:
    cfg = _load_yaml(CONFIG_FILE)
    assert isinstance(cfg, dict), "configuration.yml must be a YAML mapping"

    ds_keys = [k for k in cfg if k.startswith("data_source ")]
    assert ds_keys, "configuration.yml must declare at least one `data_source <name>:` block"

    # On exige le data source `demoema` (utilisé par les workflows CI).
    assert "data_source demoema" in cfg, "expected `data_source demoema:` block"

    ds = cfg["data_source demoema"]
    assert ds.get("type") == "postgres", "DEMOEMA data source must be postgres"

    conn = ds.get("connection") or {}
    for required in ("host", "port", "database", "username", "password"):
        assert required in conn, f"connection missing key: {required}"

    # Schema default `silver` exigé par le brief (mission 1.1).
    assert ds.get("schema") == "silver", "default schema must be `silver`"


def test_at_least_eight_check_files_exist() -> None:
    files = sorted(p.name for p in CHECKS_DIR.glob("*.yml"))
    assert len(files) >= 8, f"expected >= 8 Soda check files, found {len(files)}: {files}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_CHECK_FILES))
def test_expected_check_file_present(filename: str) -> None:
    assert (CHECKS_DIR / filename).is_file(), f"missing expected check file {filename}"


@pytest.mark.parametrize("path", sorted(CHECKS_DIR.glob("*.yml")), ids=lambda p: p.name)
def test_each_check_file_parses_and_targets_a_table(path: Path) -> None:
    doc = _load_yaml(path)
    assert isinstance(doc, dict), f"{path.name} must be a YAML mapping"

    check_keys = [k for k in doc if k.startswith("checks for ")]
    assert check_keys, f"{path.name} must contain at least one `checks for <table>:` block"

    for key in check_keys:
        table = key[len("checks for ") :].strip()
        # Les fichiers doivent référencer un schéma silver.* ou gold.*
        assert table.startswith(("silver.", "gold.")), (
            f"{path.name}: table `{table}` must be in silver.* or gold.* schema"
        )
        checks = doc[key]
        assert isinstance(checks, list) and checks, (
            f"{path.name}: `{key}` must hold a non-empty list of checks"
        )


def test_total_check_count_meets_minimum() -> None:
    """Sprint 2 cible >= 30 checks individuels (sanity, missing, dup, freshness, regex…)."""
    total = 0
    per_file: dict[str, int] = {}
    for path in CHECKS_DIR.glob("*.yml"):
        doc = _load_yaml(path)
        n = 0
        for key, checks in doc.items():
            if key.startswith("checks for ") and isinstance(checks, list):
                n += len(checks)
        per_file[path.name] = n
        total += n
    # 8 fichiers * ~4 checks = ~32. Garde-fou large pour autoriser tuning.
    assert total >= 30, f"expected >= 30 total Soda checks, got {total}: {per_file}"
