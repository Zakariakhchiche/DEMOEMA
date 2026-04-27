"""
EdRCF 6.0 — Test Fixtures
Shared fixtures for backend test suite.
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

# Ensure backend/ is on the path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from demo_data import SIGNAL_CATALOG, DEFAULT_SCORING_WEIGHTS, SECTORS_HEAT


# ---------------------------------------------------------------------------
# Sample Pappers company data (realistic structure)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_company_info():
    """Full Pappers company_info dict with all fields present."""
    return {
        "siren": "123456789",
        "nom_entreprise": "ACME INDUSTRIES SAS",
        "siege": {
            "code_postal": "75008",
            "ville": "PARIS",
            "departement": "75",
        },
        "code_naf": "25.62A",
        "libelle_code_naf": "Mecanique industrielle",
        "date_creation": "2005-03-15",
        "forme_juridique": "SAS",
        "effectif": "150",
        "capital": 500000,
        "representants": [
            {
                "prenom": "Jean",
                "nom": "DUPONT",
                "qualite": "President",
                "age": 63,
                "date_de_naissance": "1962-05-20",
                "date_prise_de_poste": "2005-03-15",
                "autres_mandats": [{"siren": "999888777"}, {"siren": "111222333"}],
            },
            {
                "prenom": "Marie",
                "nom": "MARTIN",
                "qualite": "Directeur general",
                "age": 45,
                "date_de_naissance": "1980-11-10",
                "date_prise_de_poste": "2018-01-01",
            },
        ],
        "finances": [
            {"chiffre_affaires": 25000000, "resultat": 2000000, "annee": 2024},
            {"chiffre_affaires": 20000000, "resultat": 1500000, "annee": 2023},
        ],
        "beneficiaires_effectifs": [],
        "etablissements": [
            {"siret": "12345678900010", "ville": "PARIS", "code_postal": "75008"},
            {"siret": "12345678900020", "ville": "LYON", "code_postal": "69001"},
        ],
        "entreprise_cessee": False,
        "date_cessation": None,
        "procedure_collective_existe": False,
        "procedure_collective_en_cours": False,
        "procedures_collectives": [],
        "scoring_non_financier": None,
        "publications_bodacc": [],
    }


@pytest.fixture
def minimal_company_info():
    """Minimal Pappers data — only required fields, everything else missing."""
    return {
        "siren": "987654321",
        "nom_entreprise": "PETITE SARL",
    }


@pytest.fixture
def company_with_procedures():
    """Company with active collective procedures."""
    return {
        "siren": "555666777",
        "nom_entreprise": "DIFFICULTE SA",
        "siege": {"code_postal": "33000", "ville": "BORDEAUX"},
        "code_naf": "41.20A",
        "libelle_code_naf": "Construction de maisons individuelles",
        "representants": [
            {"prenom": "Pierre", "nom": "DURAND", "qualite": "President", "age": 67},
        ],
        "finances": [
            {"chiffre_affaires": 5000000, "resultat": -200000, "annee": 2024},
            {"chiffre_affaires": 8000000, "resultat": 500000, "annee": 2023},
        ],
        "entreprise_cessee": False,
        "procedure_collective_existe": True,
        "procedure_collective_en_cours": True,
        "procedures_collectives": [{"type": "Redressement judiciaire", "date": "2024-06-01"}],
        "etablissements": [],
        "beneficiaires_effectifs": [],
    }


@pytest.fixture
def holding_company_info():
    """Company that should be detected as a holding."""
    return {
        "siren": "111222333",
        "nom_entreprise": "HOLDING DUPONT",
        "siege": {"code_postal": "92100", "ville": "BOULOGNE"},
        "code_naf": "64.20Z",
        "libelle_code_naf": "Activités des sociétés holding",
        "representants": [
            {"prenom": "Jean", "nom": "DUPONT", "qualite": "Gerant", "age": 70},
        ],
        "finances": [],
        "entreprise_cessee": False,
        "etablissements": [],
        "beneficiaires_effectifs": [],
    }


@pytest.fixture
def sample_enriched_target(sample_company_info):
    """A fully enriched target ready for API responses."""
    from pappers_loader import build_target
    from main import enrich_target

    target = build_target(idx=1, company_info=sample_company_info, search_info={})
    return enrich_target(target)


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client(sample_enriched_target):
    """FastAPI TestClient with one pre-loaded target."""
    from main import app, enriched_targets, raw_targets
    from httpx import AsyncClient, ASGITransport

    # Inject sample data into globals
    enriched_targets.clear()
    enriched_targets.append(sample_enriched_target)

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state between tests.

    Audit QA-fix : on snapshote AUSSI scoring_config et _next_idx, sinon un
    test qui POST /api/scoring/config ou ajoute des targets contamine tous
    les tests suivants silencieusement.
    """
    import copy as _copy
    import main as _main
    original_et = _main.enriched_targets.copy()
    original_rt = _main.raw_targets.copy()
    original_scoring = _copy.deepcopy(_main.scoring_config)
    original_next_idx = _main._next_idx
    yield
    _main.enriched_targets.clear()
    _main.enriched_targets.extend(original_et)
    _main.raw_targets.clear()
    _main.raw_targets.extend(original_rt)
    # Restore scoring_config keys (mutable nested dicts)
    for k in list(_main.scoring_config.keys()):
        if k in original_scoring:
            _main.scoring_config[k] = original_scoring[k]
    _main._next_idx = original_next_idx
