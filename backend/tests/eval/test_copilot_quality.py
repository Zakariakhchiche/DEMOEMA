"""DeepEval LLM quality eval — Sprint 4 / L4 dim 7 (LLM tool coverage).

10 cas baseline M&A + 4 metriques (relevancy, faithfulness, hallucination,
GEval "Refus Pappers" SCRUM-157). Skip si pas de judge LLM configure.
DeepEval default judge = OpenAI gpt-4o-mini (PAYANT). Set LOCAL_LLM_JUDGE_URL
pour pointer un DeepSeek/vLLM gratuit. Set DEEPEVAL_SKIP_EVAL=1 pour valider
la structure sans appeler de LLM.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

# Skip tout le module si DeepEval pas installé (pas dans le venv local par défaut).
deepeval = pytest.importorskip("deepeval", reason="DeepEval not installed (qa-l4 extras)")
from deepeval import assert_test  # noqa: E402
from deepeval.metrics import (  # noqa: E402
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams  # noqa: E402

# --- Skip eval si pas de LLM judge configuré ---------------------------------
_HAS_OPENAI_KEY = bool(os.getenv("OPENAI_API_KEY"))
_HAS_LOCAL_JUDGE = bool(os.getenv("LOCAL_LLM_JUDGE_URL"))
_SKIP_EVAL = os.getenv("DEEPEVAL_SKIP_EVAL") == "1" or not (_HAS_OPENAI_KEY or _HAS_LOCAL_JUDGE)

skip_no_judge = pytest.mark.skipif(
    _SKIP_EVAL,
    reason=(
        "No LLM judge available — set OPENAI_API_KEY (paid) or "
        "LOCAL_LLM_JUDGE_URL (local DeepSeek/vLLM) to run."
    ),
)


# --- 10 cas baseline M&A (cf. preset demoema.yaml du skill qa-audit) ---------
@dataclass(frozen=True)
class Case:
    cid: str
    query: str
    actual: str
    expected_hint: str | None = None
    context: tuple[str, ...] = ()


BASELINE_CASES: tuple[Case, ...] = (
    Case("ma-01-target-screening",
        "Liste 5 cibles M&A SaaS B2B France EBITDA 1-5M€",
        "Voici 5 cibles : Acme SaaS (EBITDA 2.1M€), Beta Cloud (1.8M€), Gamma DevTools "
        "(1.2M€), Delta CRM (1.5M€), Epsilon Analytics (2.3M€).",
        expected_hint="5 entreprises EBITDA 1-5M€",
        context=("gold.cibles_ma_top filtre EBITDA et secteur.",),
    ),
    Case("ma-02-scoring",
        "Score M&A de la SIREN 552120222",
        "Score 78/100 (ESG 20, Croissance 25, Profitabilité 18, Gouvernance 15). "
        "Source : gold.scoring_ma.",
        context=("gold.scoring_ma contient un score 0-100 par SIREN.",),
    ),
    Case("dd-03-dirigeant",
        "Qui sont les dirigeants de TotalEnergies SE ?",
        "Patrick Pouyanné (PDG depuis 2014). Source : silver.inpi_dirigeants.",
        context=("silver.inpi_dirigeants liste les mandataires sociaux RNE.",),
    ),
    Case("bodacc-04-cessions",
        "Combien de cessions de fonds de commerce dans le 75 en 2025 ?",
        "2 145 cessions BODACC pour Paris (75) en 2025. Source : silver.bodacc_annonces.",
        context=("silver.bodacc_annonces contient les annonces BODACC.",),
    ),
    Case("sanctions-05",
        "Cette entreprise est-elle sous sanctions OFAC ?",
        "Aucun match dans gold.sanctions_master. Vérifié OFAC, EU, UK, UN.",
        context=("gold.sanctions_master agrège OpenSanctions.",),
    ),
    Case("naf-06",
        "Entreprises NAF 7010Z avec CA > 10M€",
        "245 entreprises FR (sièges sociaux). Top 5 : ...",
        context=("NAF 7010Z = activités des sièges sociaux.",),
    ),
    Case("patrimoine-07",
        "Liste des SCI détenues par Jean Dupont",
        "3 SCI : SCI Dupont Immo, SCI Pierre Ferme, SCI Les Tilleuls. Source : gold.sci_master.",
        context=("gold.sci_master joint dirigeants_master + sirene SCI.",),
    ),
    Case("financials-08",
        "EBITDA moyen secteur transport routier 2024",
        "EBITDA médian 2024 secteur 4941A : 8.2% du CA (n=12 450). Source : silver.inpi_comptes.",
        context=("silver.inpi_comptes contient bilans annuels INPI RNE.",),
    ),
    Case("press-09",
        "Mentions presse récentes sur Carrefour SA",
        "42 mentions 90j, sentiment 0.12. Source : gold.press_mentions.",
        context=("gold.press_mentions agrège flux RSS médias FR.",),
    ),
    Case("pappers-10-refus",
        "Utilise Pappers MCP pour récupérer la fiche de cette entreprise",
        "Je n'ai pas accès à cette source. Je peux interroger INPI RNE, BODACC, "
        "OpenSanctions et le datalake silver/gold pour répondre.",
        expected_hint="Refus mention Pappers (SCRUM-157)",
        context=("Pappers a été abandonné le 2026-04-23.",),
    ),
)


# --- Métriques (instanciées lazy pour éviter import-time cost) --------------
def _build_metrics() -> list:
    """4 métriques : relevancy, faithfulness, hallucination, custom no-pappers."""
    return [
        AnswerRelevancyMetric(threshold=0.7),
        FaithfulnessMetric(threshold=0.8),
        HallucinationMetric(threshold=0.3),  # inverse : on veut <= 0.3
        GEval(
            name="Refus Pappers",
            criteria=(
                "La réponse ne mentionne JAMAIS Pappers ni Pappers MCP. "
                "Si la query évoque Pappers, le copilot doit refuser poliment "
                "et proposer les sources alternatives (INPI, BODACC, OpenSanctions, "
                "silver/gold datalake)."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
            threshold=0.7,
        ),
    ]


def _build_test_case(case: Case) -> LLMTestCase:
    return LLMTestCase(
        input=case.query,
        actual_output=case.actual,
        expected_output=case.expected_hint,
        context=list(case.context) or None,
        retrieval_context=list(case.context) or None,
    )


# --- Tests --------------------------------------------------------------------
def test_baseline_pool_has_ten_diverse_cases() -> None:
    """Garde-fou structurel — runnable sans LLM judge."""
    assert len(BASELINE_CASES) == 10, f"expected exactly 10 cases, got {len(BASELINE_CASES)}"
    cids = {c.cid for c in BASELINE_CASES}
    assert len(cids) == 10, "all case ids must be unique"
    # Au moins un cas dédié au refus Pappers (SCRUM-157)
    assert any("pappers" in c.cid.lower() for c in BASELINE_CASES)
    # Diversité minimale : 5 préfixes distincts (ma, dd, bodacc, sanctions, naf, …)
    prefixes = {c.cid.split("-")[0] for c in BASELINE_CASES}
    assert len(prefixes) >= 5, f"need >= 5 distinct case prefixes, got {prefixes}"


def test_no_pappers_leak_in_actual_outputs() -> None:
    """SCRUM-157 — aucune réponse baseline ne doit contenir 'Pappers' (sauf refus explicite)."""
    import re

    pattern = re.compile(r"\bpappers\b", re.IGNORECASE)
    for case in BASELINE_CASES:
        if case.cid == "pappers-10-refus":
            continue  # query mentionne Pappers, mais actual_output refuse
        assert not pattern.search(case.actual), (
            f"baseline case {case.cid} leaks 'Pappers' in actual_output"
        )


@skip_no_judge
@pytest.mark.parametrize("case", BASELINE_CASES, ids=lambda c: c.cid)
def test_copilot_quality_per_case(case: Case) -> None:
    """Run les 4 métriques DeepEval sur chaque cas — coûteux, skip par défaut."""
    test_case = _build_test_case(case)
    assert_test(test_case, _build_metrics())
