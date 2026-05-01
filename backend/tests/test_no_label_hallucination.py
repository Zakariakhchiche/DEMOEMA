"""
EdRCF 6.0 — Tests anti-hallucination labels DL{N}

Audit QA 2026-05-01 a montré que le copilot interprétait des labels d'identifiant
interne (DL28, DL46, DL57, DL87, DL92, DL94) comme codes département FR,
produisant des réponses faussement scopées (ex DL28 NAF 7010Z → réponse filtrée
sur Eure-et-Loir au lieu de toutes géographies).

Ces tests valident :
1. Que le system prompt contient bien la règle anti-hallucination labels.
2. Que la règle couvre les patterns observés en audit.
"""
from __future__ import annotations

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clients.deepseek import _SYSTEM_PROMPT_TOOLS  # noqa: E402


class TestSystemPromptAntiHallucination:
    """Le system prompt doit contenir la règle anti-hallucination labels."""

    def test_anti_hallucination_section_present(self):
        assert "ANTI-HALLUCINATION LABELS" in _SYSTEM_PROMPT_TOOLS

    def test_mentions_label_patterns_observed_in_audit(self):
        # Labels exacts vus dans l'audit : DL{N}, Q{N}/{T}, UI{N}, BUG-{N}, TEST-{N}
        for pattern in ["DL", "Q", "UI"]:
            assert pattern in _SYSTEM_PROMPT_TOOLS, f"label pattern {pattern!r} manquant"

    def test_explicit_examples_with_known_audit_cases(self):
        # Cas DL28 → Eure-et-Loir était LE bug le plus visible
        assert "DL28" in _SYSTEM_PROMPT_TOOLS
        assert "NAF 7010Z" in _SYSTEM_PROMPT_TOOLS

    def test_warns_against_dept_misinterpretation(self):
        # Le prompt doit explicitement dire de ne PAS interpréter comme département
        prompt_lower = _SYSTEM_PROMPT_TOOLS.lower()
        assert "département" in prompt_lower or "dept" in prompt_lower
        assert "pas" in prompt_lower  # négation explicite


class TestLabelDetectionRegex:
    """Si on ajoute un préprocessing regex côté backend dans le futur,
    ces patterns doivent être correctement détectés."""

    LABEL_PREFIX_RE = re.compile(
        r"^(?:DL\d+(?:/\d+)?|Q\d+(?:/\d+)?|UI\d+|BUG-?\d+|TEST-?\d+)\s*[-:.]?\s*",
        re.IGNORECASE,
    )

    def test_dl28_stripped(self):
        assert self.LABEL_PREFIX_RE.sub("", "DL28 NAF 7010Z").strip() == "NAF 7010Z"

    def test_dl46_stripped(self):
        assert self.LABEL_PREFIX_RE.sub("", "DL46 - BODACC cessions").strip() == "BODACC cessions"

    def test_q1_55_stripped(self):
        assert self.LABEL_PREFIX_RE.sub("", "Q1/55 - fusion vs acquisition").strip() == "fusion vs acquisition"

    def test_q1_2026_NOT_stripped_business_query(self):
        """Une query métier "T1 2026 résultats" doit rester intacte."""
        # Pas de label → pas de strip
        original = "résultats T1 2026 chez Capgemini"
        assert self.LABEL_PREFIX_RE.sub("", original).strip() == original

    def test_dept_in_middle_NOT_stripped(self):
        """Un numéro département au milieu reste."""
        assert (
            self.LABEL_PREFIX_RE.sub("", "DL57 sociétés du 57 (Moselle)").strip()
            == "sociétés du 57 (Moselle)"
        )


class TestKnownAuditHallucinationCases:
    """Documente les 6 cas d'hallucination confirmés en audit 2026-05-01.

    Format : (label, real_intent, false_positive_dept_label)
    """

    AUDIT_CASES = [
        ("DL28", "NAF 7010Z toutes régions", "Eure-et-Loir (28)"),
        ("DL46", "BODACC cessions 7 derniers jours", "Lot (46)"),
        ("DL57", "sociétés ayant doublé CA en 3 ans", "Moselle (57)"),
        ("DL87", "énergie renouvelable NAF 35", "Haute-Vienne (87)"),
        ("DL92", "défense NAF 30", "Hauts-de-Seine (92)"),
        ("DL94", "édition livres NAF 58", "Val-de-Marne (94)"),
    ]

    def test_audit_documents_6_cases(self):
        assert len(self.AUDIT_CASES) == 6

    def test_each_case_has_label_and_intent(self):
        for label, intent, false_dept in self.AUDIT_CASES:
            assert label.startswith("DL")
            assert intent
            assert false_dept

    def test_system_prompt_addresses_audit_cases(self):
        """Le system prompt doit mentionner au moins 1 des cas exacts."""
        # Au moins l'exemple DL28 NAF 7010Z doit y être (cf patch Phase G1)
        assert "DL28" in _SYSTEM_PROMPT_TOOLS
