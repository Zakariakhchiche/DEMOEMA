"""Validate Bandit SAST configuration — Sprint 5 / L4 dim 6 (security_static).

Test offline (sans run reel de bandit) qui catch toute regression sur :
- backend/.bandit                 — fallback INI pour outils sans pyproject
- backend/pyproject.toml          — section [tool.bandit] source-of-truth

Garantit que les deux configs restent synchronisees, que les patterns
d'exclusion attendus sont presents, et que les modules critiques restent
inclus dans le scan.
"""
from __future__ import annotations

import configparser
from pathlib import Path

import pytest

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found, no-redef]


BACKEND_ROOT = Path(__file__).resolve().parent.parent
BANDIT_INI = BACKEND_ROOT / ".bandit"
PYPROJECT = BACKEND_ROOT / "pyproject.toml"

# Skips attendus (cf. brief Sprint 5 mission 2.1).
EXPECTED_SKIPS = {"B101", "B404", "B603"}
EXPECTED_EXCLUDES = {"tests", "migrations", "__pycache__"}

# Modules critiques qui DOIVENT rester scannes (pas dans excludes).
CRITICAL_MODULES = (
    "main.py",
    "datalake.py",
    "auth",
    "clients",
    "domain",
    "routers",
    "services",
)


def _load_bandit_ini() -> dict[str, str]:
    parser = configparser.ConfigParser()
    parser.read(BANDIT_INI, encoding="utf-8")
    assert parser.has_section("bandit"), ".bandit must contain [bandit] section"
    return dict(parser.items("bandit"))


def _load_bandit_toml() -> dict:
    with PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("bandit", {})


def test_bandit_ini_exists_and_parses() -> None:
    assert BANDIT_INI.is_file(), f"missing {BANDIT_INI}"
    cfg = _load_bandit_ini()
    assert "skips" in cfg, ".bandit must declare `skips`"
    assert "exclude_dirs" in cfg, ".bandit must declare `exclude_dirs`"


def test_pyproject_has_bandit_section() -> None:
    assert PYPROJECT.is_file(), f"missing {PYPROJECT}"
    cfg = _load_bandit_toml()
    assert cfg, "pyproject.toml must define [tool.bandit] section"
    assert "skips" in cfg, "[tool.bandit] must list `skips`"
    assert "exclude_dirs" in cfg, "[tool.bandit] must list `exclude_dirs`"


def test_skip_codes_match_expected() -> None:
    toml_cfg = _load_bandit_toml()
    skips = set(toml_cfg.get("skips", []))
    assert EXPECTED_SKIPS.issubset(skips), (
        f"missing expected skip codes: {EXPECTED_SKIPS - skips}"
    )


def test_ini_and_toml_skips_are_consistent() -> None:
    ini_cfg = _load_bandit_ini()
    toml_cfg = _load_bandit_toml()
    ini_skips = {s.strip() for s in ini_cfg["skips"].split(",") if s.strip()}
    toml_skips = set(toml_cfg.get("skips", []))
    assert ini_skips == toml_skips, (
        f".bandit and pyproject.toml skips diverge: ini={ini_skips} toml={toml_skips}"
    )


@pytest.mark.parametrize("excluded", sorted(EXPECTED_EXCLUDES))
def test_exclude_dirs_contains_expected(excluded: str) -> None:
    toml_cfg = _load_bandit_toml()
    excludes = set(toml_cfg.get("exclude_dirs", []))
    assert excluded in excludes, f"expected exclude_dir `{excluded}` missing"


@pytest.mark.parametrize("module", CRITICAL_MODULES)
def test_critical_module_present_and_not_excluded(module: str) -> None:
    """Garde-fou : on n'exclut JAMAIS un module critique du scan SAST."""
    target = BACKEND_ROOT / module
    assert target.exists(), f"critical module {module} missing in backend/"
    toml_cfg = _load_bandit_toml()
    excludes = {e.strip("/") for e in toml_cfg.get("exclude_dirs", [])}
    assert module not in excludes, f"critical module {module} must NOT be excluded"


def test_minimum_python_modules_to_scan() -> None:
    """Sanity : au moins 20 fichiers .py a scanner dans backend/ hors excludes."""
    toml_cfg = _load_bandit_toml()
    excludes = {e.strip("/") for e in toml_cfg.get("exclude_dirs", [])}
    py_files = [
        p for p in BACKEND_ROOT.rglob("*.py")
        if not any(part in excludes for part in p.relative_to(BACKEND_ROOT).parts)
    ]
    assert len(py_files) >= 20, (
        f"expected >= 20 scannable .py modules in backend/, found {len(py_files)}"
    )
