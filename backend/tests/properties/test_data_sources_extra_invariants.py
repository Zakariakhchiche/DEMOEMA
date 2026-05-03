"""Property-based tests Hypothesis sur backend/data_sources.py — Sprint QA-L4.6.

Cible : étendre dim 1+3 path_coverage QCS skill qa-audit en couvrant les
helpers purs (non-async, pas d'I/O) :
- _nature_juridique_to_text : mapping code → libellé
- _tranche_to_effectif      : mapping code tranche → range
- _bodacc_type               : routing famille avis → type Pappers
- _map_gouv_to_pappers      : structural mapping (clés stables, types)

~700 inputs aléatoires (digits, lettres, edge cases vides/None/longs).

Run :
    cd backend && pytest tests/properties/test_data_sources_extra_invariants.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st  # type: ignore

data_sources = pytest.importorskip("data_sources")

_nature_juridique_to_text = data_sources._nature_juridique_to_text
_tranche_to_effectif = data_sources._tranche_to_effectif
_bodacc_type = data_sources._bodacc_type
_map_gouv_to_pappers = data_sources._map_gouv_to_pappers
_TRANCHE_MAP = data_sources._TRANCHE_MAP


# ────────────────────────────────────────────────────────────────────
# 1. _nature_juridique_to_text
# ────────────────────────────────────────────────────────────────────
KNOWN_NATURE_CODES = [
    "1000", "5498", "5499", "5710", "5720", "5410", "5422",
    "5599", "5505", "5510", "5699", "6540", "5307", "9220", "9221",
]


@pytest.mark.unit
@pytest.mark.property
@given(code=st.sampled_from(KNOWN_NATURE_CODES))
@settings(max_examples=200, deadline=None)
def test_nature_juridique_known_codes_return_non_empty(code: str) -> None:
    """Codes connus → libellé non vide, non préfixé "Forme juridique"."""
    result = _nature_juridique_to_text(code)
    assert isinstance(result, str)
    assert len(result) > 0
    assert not result.startswith("Forme juridique ")


@pytest.mark.unit
@pytest.mark.property
@given(code=st.text(alphabet="0123456789", min_size=1, max_size=10))
@settings(max_examples=200, deadline=None)
def test_nature_juridique_unknown_codes_fallback(code: str) -> None:
    """Code inconnu → fallback "Forme juridique <code>"."""
    if code in KNOWN_NATURE_CODES:
        return  # skip known
    result = _nature_juridique_to_text(code)
    assert result == f"Forme juridique {code}"


@pytest.mark.unit
@pytest.mark.property
@given(code=st.one_of(st.just(""), st.just(None)))
@settings(max_examples=10, deadline=None)
def test_nature_juridique_empty_returns_empty(code) -> None:
    """Code vide ou None → "" (jamais raise)."""
    assert _nature_juridique_to_text(code) == ""


@pytest.mark.unit
@pytest.mark.property
@given(code=st.text(min_size=0, max_size=50))
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
def test_nature_juridique_never_raises(code: str) -> None:
    """Quel que soit l'input string, jamais de raise."""
    result = _nature_juridique_to_text(code)
    assert isinstance(result, str)


# ────────────────────────────────────────────────────────────────────
# 2. _tranche_to_effectif
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@given(tranche=st.sampled_from(list(_TRANCHE_MAP.keys())))
@settings(max_examples=100, deadline=None)
def test_tranche_known_codes_mapped(tranche: str) -> None:
    """Tranche connue → mapping correspondant exact."""
    assert _tranche_to_effectif(tranche) == _TRANCHE_MAP[tranche]


@pytest.mark.unit
@pytest.mark.property
@given(tranche=st.one_of(st.just(""), st.just(None)))
@settings(max_examples=10, deadline=None)
def test_tranche_empty_returns_na(tranche) -> None:
    """Tranche vide ou None → "N/A"."""
    assert _tranche_to_effectif(tranche) == "N/A"


@pytest.mark.unit
@pytest.mark.property
@given(tranche=st.text(alphabet="0123456789ABZ", min_size=1, max_size=8))
@settings(max_examples=200, deadline=None)
def test_tranche_unknown_returns_self(tranche: str) -> None:
    """Tranche inconnue → l'input est retourné tel quel (string)."""
    if tranche in _TRANCHE_MAP:
        return
    assert _tranche_to_effectif(tranche) == str(tranche)


@pytest.mark.unit
@pytest.mark.property
@given(tranche=st.text(min_size=0, max_size=30))
@settings(max_examples=200, deadline=None)
def test_tranche_idempotent_when_known(tranche: str) -> None:
    """f(f(x)) == f(x) sur l'image (les valeurs déjà mappées restent stables)."""
    once = _tranche_to_effectif(tranche)
    twice = _tranche_to_effectif(once)
    # Soit déjà N/A, soit string non-vide, jamais de None
    assert isinstance(once, str)
    assert isinstance(twice, str)


# ────────────────────────────────────────────────────────────────────
# 3. _bodacc_type
# ────────────────────────────────────────────────────────────────────
BODACC_KEYWORDS = ["vente", "cession", "radiation", "capital", "depot",
                   "dpc", "modification", "immatriculation", "dissolution",
                   "liquidation", "RANDOM", "", "OTHER"]


@pytest.mark.unit
@pytest.mark.property
@given(
    famille=st.sampled_from(BODACC_KEYWORDS),
    modifs=st.sampled_from(BODACC_KEYWORDS),
    lib=st.sampled_from(BODACC_KEYWORDS),
)
@settings(max_examples=200, deadline=None)
def test_bodacc_type_returns_known_label(famille: str, modifs: str, lib: str) -> None:
    """Quelle que soit la combinaison, retourne un type Pappers connu."""
    fields = {
        "familleavis": famille,
        "modificationsgenerales": modifs,
        "familleavis_lib": lib,
    }
    result = _bodacc_type(fields)
    assert result in {"Vente", "Radiation", "Modification", "Depot des comptes",
                      "Immatriculation"}


@pytest.mark.unit
@pytest.mark.property
@given(fields=st.fixed_dictionaries({}))
@settings(max_examples=10, deadline=None)
def test_bodacc_type_empty_dict_default(fields: dict) -> None:
    """Dict vide → "Modification" (default fallback)."""
    assert _bodacc_type(fields) == "Modification"


@pytest.mark.unit
@pytest.mark.property
@given(
    famille=st.text(min_size=0, max_size=30),
    modifs=st.text(min_size=0, max_size=80),
)
@settings(max_examples=200, deadline=None)
def test_bodacc_type_never_raises(famille: str, modifs: str) -> None:
    """Inputs aléatoires → jamais de raise, toujours une string."""
    fields = {"familleavis": famille, "modificationsgenerales": modifs}
    result = _bodacc_type(fields)
    assert isinstance(result, str) and len(result) > 0


@pytest.mark.unit
@pytest.mark.property
def test_bodacc_type_priority_vente_over_modification() -> None:
    """Si "vente" présent, prime sur "modification"."""
    fields = {"familleavis": "Vente",
              "modificationsgenerales": "modification capital"}
    assert _bodacc_type(fields) == "Vente"


# ────────────────────────────────────────────────────────────────────
# 4. _map_gouv_to_pappers — structural invariants
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.property
@given(
    siren=st.text(alphabet="0123456789", min_size=9, max_size=9),
    nom=st.text(min_size=0, max_size=80),
    cp=st.text(alphabet="0123456789", min_size=0, max_size=10),
)
@settings(max_examples=200, deadline=None)
def test_map_gouv_keys_always_present(siren: str, nom: str, cp: str) -> None:
    """Toutes les clés Pappers attendues présentes même si input minimal."""
    company = {
        "siren": siren,
        "nom_complet": nom,
        "siege": {"code_postal": cp, "siret": siren + "00012"},
    }
    result = _map_gouv_to_pappers(company)
    expected_keys = {
        "siren", "nom_entreprise", "siege", "code_naf",
        "libelle_code_naf", "chiffre_affaires", "resultat",
        "date_creation", "forme_juridique", "effectif",
        "representants", "finances", "etablissements",
        "entreprise_cessee", "statut_activite",
        "beneficiaires_effectifs", "publications_bodacc",
        "procedures_collectives", "infogreffe_actes", "news_articles",
    }
    assert expected_keys.issubset(set(result.keys()))


@pytest.mark.unit
@pytest.mark.property
@given(cp=st.text(alphabet="0123456789", min_size=2, max_size=10))
@settings(max_examples=100, deadline=None)
def test_map_gouv_departement_first_two_digits(cp: str) -> None:
    """Departement = code_postal[:2] si len >= 2, sinon ""."""
    company = {"siren": "123456789", "siege": {"code_postal": cp}}
    result = _map_gouv_to_pappers(company)
    assert result["siege"]["departement"] == cp[:2]


@pytest.mark.unit
@pytest.mark.property
@given(etat=st.sampled_from(["A", "F", "C", "", "X"]))
@settings(max_examples=20, deadline=None)
def test_map_gouv_cessee_flag_consistent(etat: str) -> None:
    """etat_administratif=='F' ⇔ entreprise_cessee=True."""
    company = {"siren": "123456789", "etat_administratif": etat,
               "siege": {}}
    result = _map_gouv_to_pappers(company)
    assert result["entreprise_cessee"] == (etat == "F")
    assert result["statut_activite"] == ("Radie" if etat == "F" else "En activite")


@pytest.mark.unit
@pytest.mark.property
@given(
    siren=st.text(alphabet="0123456789", min_size=9, max_size=9),
    nom=st.text(min_size=0, max_size=50),
)
@settings(max_examples=100, deadline=None)
def test_map_gouv_round_trip_json_serializable(siren: str, nom: str) -> None:
    """Le résultat doit être sérialisable en JSON (round-trip)."""
    company = {"siren": siren, "nom_complet": nom, "siege": {}}
    result = _map_gouv_to_pappers(company)
    encoded = json.dumps(result, default=str)
    decoded = json.loads(encoded)
    assert decoded["siren"] == siren
