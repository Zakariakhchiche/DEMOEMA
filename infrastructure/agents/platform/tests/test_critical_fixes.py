"""Tests qui verrouillent les fixes critiques de la session resilience.

Les bugs fixés ici ont produit en prod des comportements observables :
- WHERE OR/AND precedence → feedback cross-silver pollué
- person_uid instable → doublons Neo4j silencieux

Ces tests évitent une régression future si quelqu'un retouche les regex /
hash signatures.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# WHERE precedence bug — silver_engine.py:319 — bug C1
# ─────────────────────────────────────────────────────────────────────────────

def test_silver_engine_feedback_query_has_parens_around_or():
    """La query SELECT du feedback codegen DOIT parenthéser le `OR applied=false`
    sinon le SELECT renvoie des rows d'AUTRES silvers (precedence AND > OR).

    Bug observé en prod : silver A regen avec le feedback d'erreur de silver B.
    """
    silver_engine = Path(__file__).parent.parent / "ingestion" / "silver_engine.py"
    src = silver_engine.read_text(encoding="utf-8")

    # On cherche la query sur audit.silver_specs_versions
    block = re.search(
        r"FROM audit\.silver_specs_versions.*?ORDER BY generated_at DESC LIMIT 1",
        src, re.DOTALL,
    )
    assert block, "feedback query introuvable dans silver_engine.py"
    query = block.group(0)
    # Le WHERE doit avoir le OR parenthésé
    assert "(validation_status != 'ok' OR applied = false)" in query, (
        "Le WHERE doit parenthéser le OR : `WHERE silver_name = %s AND "
        "(validation_status != 'ok' OR applied = false)`. Sans parenthèses, "
        "AND lie plus fort que OR → renvoie des rows d'autres silvers."
    )


# ─────────────────────────────────────────────────────────────────────────────
# _person_uid stability — neo4j_sync.py — bug MISSING-2
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def person_uid():
    """Import _person_uid depuis le module sans tirer dans psycopg/neo4j driver."""
    import sys
    import types
    # Stub psycopg et neo4j si nécessaire (on ne touche pas le module import-level)
    for stub in ("psycopg",):
        if stub not in sys.modules:
            sys.modules[stub] = types.ModuleType(stub)
    from ingestion.neo4j_sync import _person_uid as fn
    return fn


def test_person_uid_invariant_to_prenom_order(person_uid):
    """Le UID DOIT être identique quel que soit l'ordre des prénoms upstream.

    Bug observé : INPI dump avec prenoms=['Jean','Marie'] puis dump suivant
    avec prenoms=['Marie','Jean'] → 2 nodes Person au lieu d'1.
    """
    uid_1 = person_uid("DUPONT", ["Jean", "Marie"], "1970-01-01")
    uid_2 = person_uid("DUPONT", ["Marie", "Jean"], "1970-01-01")
    assert uid_1 == uid_2, (
        f"UID dépend de l'ordre des prénoms : {uid_1} ≠ {uid_2}. "
        "Doit hasher sur la liste TRIÉE pour être stable."
    )


def test_person_uid_distincts_pour_prenoms_differents(person_uid):
    """Sanity : si les prénoms sont VRAIMENT différents (pas juste réordonnés),
    les UID DOIVENT diverger."""
    uid_1 = person_uid("DUPONT", ["Jean"], "1970-01-01")
    uid_2 = person_uid("DUPONT", ["Pierre"], "1970-01-01")
    assert uid_1 != uid_2


def test_person_uid_str_legacy_compat(person_uid):
    """Compat : ancien caller passait un str unique. Nouveau accepte str | list.
    Le str doit produire le même hash que la liste à 1 élément équivalent."""
    uid_str = person_uid("DUPONT", "Jean", "1970-01-01")
    uid_list = person_uid("DUPONT", ["Jean"], "1970-01-01")
    assert uid_str == uid_list


def test_person_uid_handles_none(person_uid):
    """Robustesse : prenoms=None ne plante pas, retourne un hash calculable."""
    uid = person_uid("DUPONT", None, "1970-01-01")
    assert isinstance(uid, str) and len(uid) == 40


def test_person_uid_normalisation_accents(person_uid):
    """Les accents et chars spéciaux sont normalisés ASCII pour stabiliser
    le hash entre dumps avec encoding différent."""
    uid_1 = person_uid("DUPONT", ["Jérôme"], "1970-01-01")
    uid_2 = person_uid("DUPONT", ["Jerome"], "1970-01-01")
    assert uid_1 == uid_2
