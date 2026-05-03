"""Property-based tests Hypothesis sur datalake.GOLD_TABLES_WHITELIST.

Invariants ciblés (dim 3 path_coverage QA L4 Sprint 1) :
- Whitelist non vide, immutable au sens "constante module"
- Toutes les keys = "<schema>.<table>" (préfixe gold. ou silver.)
- Chaque entrée contient les keys obligatoires (label, category, preview_cols)
- preview_cols est une liste non vide
- _qualified(table) accepte les whitelistées et rejette TOUT le reste avec HTTP 404

Sécurité : c'est l'unique défense contre l'injection SQL sur le segment
`{schema}.{table}` (les valeurs sont bindées via $1/$2 asyncpg, mais le
nom de table est interpolé en string — d'où le besoin de whitelist stricte).

Run :
    cd backend && pytest tests/properties/test_datalake_whitelist_invariants.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hypothesis import given, settings, strategies as st  # type: ignore
import pytest
from fastapi import HTTPException  # type: ignore

from datalake import GOLD_TABLES_WHITELIST  # type: ignore
from routers.datalake import _qualified  # type: ignore


WHITELISTED_NAMES = list(GOLD_TABLES_WHITELIST.keys())


# ────────────────────────────────────────────────────────────────────
# Sanity / structure
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
def test_whitelist_is_non_empty_dict() -> None:
    """La whitelist doit être un dict non-vide."""
    assert isinstance(GOLD_TABLES_WHITELIST, dict)
    assert len(GOLD_TABLES_WHITELIST) > 0


@pytest.mark.unit
@pytest.mark.property
def test_whitelist_keys_use_schema_prefix() -> None:
    """Toutes les keys doivent être qualifiées 'schema.table' (gold. ou silver.)."""
    for name in WHITELISTED_NAMES:
        assert "." in name, f"Table '{name}' sans schéma qualifié"
        schema, table = name.split(".", 1)
        assert schema in ("gold", "silver"), f"Schéma inattendu : {schema!r}"
        assert table, f"Nom de table vide après schéma : {name!r}"


@pytest.mark.unit
@pytest.mark.property
def test_whitelist_entries_have_required_fields() -> None:
    """Chaque entrée doit avoir label, category, preview_cols (liste non vide)."""
    required = {"label", "category", "preview_cols"}
    for name, meta in GOLD_TABLES_WHITELIST.items():
        assert isinstance(meta, dict), f"{name} meta pas un dict"
        missing = required - meta.keys()
        assert not missing, f"{name} manque les champs : {missing}"
        assert isinstance(meta["preview_cols"], list)
        assert len(meta["preview_cols"]) > 0, f"{name} preview_cols vide"


# ────────────────────────────────────────────────────────────────────
# _qualified accepte tout ce qui est whitelisté
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@given(table=st.sampled_from(WHITELISTED_NAMES))
@settings(max_examples=200, deadline=None)
def test_qualified_accepts_whitelisted(table: str) -> None:
    """Tous les noms whitelistés doivent être acceptés par _qualified."""
    assert _qualified(table) == table


# ────────────────────────────────────────────────────────────────────
# Negative : _qualified rejette TOUT le reste (sécurité)
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
@given(
    bad=st.text(min_size=0, max_size=100).filter(lambda s: s not in WHITELISTED_NAMES)
)
@settings(max_examples=300, deadline=None)
def test_qualified_rejects_non_whitelisted(bad: str) -> None:
    """N'importe quel nom hors whitelist → HTTP 404 (no leak, no SQL injection)."""
    with pytest.raises(HTTPException) as exc_info:
        _qualified(bad)
    assert exc_info.value.status_code == 404


@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
@pytest.mark.parametrize("attack", [
    "public.users",
    "pg_catalog.pg_user",
    "information_schema.tables",
    "gold.entreprises_master; DROP TABLE users;--",
    "gold.entreprises_master--",
    "' OR 1=1; --",
    "gold.cibles_ma_top UNION SELECT * FROM secrets",
    "",
    "gold",  # schema seul, pas de table
    ".master",  # table seule, pas de schéma
    "GOLD.ENTREPRISES_MASTER",  # case-sensitive (Postgres minuscules)
    "silver.unknown_table_xyz",
])
def test_qualified_blocks_known_attack_vectors(attack: str) -> None:
    """Vecteurs d'injection SQL connus → 404, jamais d'exécution."""
    with pytest.raises(HTTPException) as exc_info:
        _qualified(attack)
    assert exc_info.value.status_code == 404


# ────────────────────────────────────────────────────────────────────
# Property : ajout/suppression de char ne smuggle pas un nom hors-WL
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@pytest.mark.negative
@given(
    base=st.sampled_from(WHITELISTED_NAMES),
    suffix=st.text(min_size=1, max_size=20),
)
@settings(max_examples=100, deadline=None)
def test_qualified_rejects_smuggle_via_suffix(base: str, suffix: str) -> None:
    """Tout suffixe non-vide ajouté à un nom WL doit casser la match.

    Garantit qu'un attaquant ne peut pas exploiter une fuzzy match en
    ajoutant `; DROP TABLE` ou similaire.
    """
    smuggled = base + suffix
    if smuggled in WHITELISTED_NAMES:
        return  # collision improbable mais on skip
    with pytest.raises(HTTPException) as exc_info:
        _qualified(smuggled)
    assert exc_info.value.status_code == 404


@pytest.mark.unit
@pytest.mark.property
def test_qualified_returns_input_unchanged() -> None:
    """_qualified ne modifie pas le nom (pas de normalisation)."""
    for name in WHITELISTED_NAMES:
        assert _qualified(name) is name or _qualified(name) == name
