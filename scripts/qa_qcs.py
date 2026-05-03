"""Quality Coverage Score (QCS) calculator — DEMOEMA QA L4 skill.

Module Python exécutable extrait du fence markdown de SKILL.md v2.2 (P0 Anne).
Permet : (a) tests pytest pour la formule, (b) appel programmatique depuis CI,
(c) appel depuis le skill v3.0.0 (Bash → python -m scripts.qa_qcs ...).

Cible : QCS >= 90 = L4 (production payante).

Usage :
    python -m scripts.qa_qcs --current metrics_now.json --previous baseline.json
    python -m scripts.qa_qcs --current '{"line_coverage_pct":95,...}'

Sortie JSON :
    {"qcs": 87, "base": 92, "penalty": 5, "regressions": [["mutation",15.0]],
     "level_reached": "L3", "verdict": "NO-GO L4 (QCS < 90)"}
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any

# Pondération 15 dimensions (somme = 1.0). Lue depuis docs/QA_PLAYBOOKS.md §6.
WEIGHTS: dict[str, float] = {
    "line_coverage_pct": 0.10,
    "branch_coverage_pct": 0.10,
    "path_coverage_pct": 0.05,
    "mutation_coverage_pct": 0.10,
    "api_endpoint_coverage_pct": 0.08,
    "clickable_coverage_pct": 0.10,
    "llm_tool_coverage_pct": 0.08,
    "data_quality_coverage_pct": 0.08,
    "visual_regression_coverage_pct": 0.05,
    "browser_coverage_pct": 0.05,
    "device_coverage_pct": 0.04,
    "locale_coverage_pct": 0.03,
    "persona_coverage_pct": 0.03,
    "state_coverage_pct": 0.05,
    "negative_test_coverage_pct": 0.06,
}

# Seuils niveaux rigueur (depuis header YAML doctrine).
THRESHOLDS = {"L2": 55, "L3": 80, "L4": 90, "L5": 95}

# Pénalité régression : si UNE dim baisse de > REGRESSION_THRESHOLD pp,
# pénalité absolue PENALTY_PTS sur QCS final.
REGRESSION_THRESHOLD_PP = 10
PENALTY_PTS = 5


@dataclass
class QcsResult:
    qcs: float
    base: float
    penalty: float
    regressions: list[tuple[str, float]] = field(default_factory=list)
    level_reached: str = "L1"
    verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "qcs": self.qcs,
            "base": self.base,
            "penalty": self.penalty,
            "regressions": self.regressions,
            "level_reached": self.level_reached,
            "verdict": self.verdict,
        }


def _validate_weights() -> None:
    """Vérifie que la somme des poids = 1.0 (invariant strict)."""
    total = sum(WEIGHTS.values())
    if abs(total - 1.0) > 0.001:
        raise ValueError(f"Somme poids QCS = {total} != 1.0 (incohérence formule)")


def _level_from_qcs(qcs: float) -> str:
    """Niveau atteint selon le QCS courant."""
    if qcs >= THRESHOLDS["L5"]:
        return "L5"
    if qcs >= THRESHOLDS["L4"]:
        return "L4"
    if qcs >= THRESHOLDS["L3"]:
        return "L3"
    if qcs >= THRESHOLDS["L2"]:
        return "L2"
    return "L1"


def _verdict_from_qcs(qcs: float, target: str = "L4") -> str:
    """Verdict GO/NO-GO pour atteindre `target`."""
    target_score = THRESHOLDS.get(target)
    if target_score is None:
        return f"Cible inconnue : {target}"
    if qcs >= target_score:
        return f"GO {target} (QCS {qcs} >= {target_score})"
    return f"NO-GO {target} (QCS {qcs} < {target_score})"


def compute_qcs(
    metrics_current: dict[str, float],
    metrics_previous: dict[str, float] | None = None,
    target_level: str = "L4",
) -> QcsResult:
    """Calcule le Quality Coverage Score depuis 15 dimensions.

    Args:
        metrics_current: dict {dimension_name: pct_value (0-100)}
        metrics_previous: optionnel — baseline pour détecter régressions > 10pp
        target_level: niveau cible (L2/L3/L4/L5) pour verdict

    Returns:
        QcsResult avec qcs final, base, penalty, regressions, level, verdict.

    Invariants vérifiés :
        - somme poids = 1.0
        - QCS dans [0, 100]
        - pénalité = 5 si max(prev - curr) > 10pp sur AU MOINS 1 dim
        - QCS final >= 0
    """
    _validate_weights()

    # Base QCS : moyenne pondérée des 15 dimensions (manquantes = 0)
    base_qcs = round(
        sum(WEIGHTS[k] * metrics_current.get(k, 0) for k in WEIGHTS),
        1,
    )

    # Pénalité régression
    penalty: float = 0.0
    regressions: list[tuple[str, float]] = []
    if metrics_previous:
        for dim in WEIGHTS:
            prev = metrics_previous.get(dim, 0)
            curr = metrics_current.get(dim, 0)
            delta = prev - curr
            if delta > REGRESSION_THRESHOLD_PP:
                regressions.append((dim, round(delta, 1)))
        if regressions:
            penalty = float(PENALTY_PTS)

    final_qcs = max(0.0, base_qcs - penalty)
    level = _level_from_qcs(final_qcs)
    verdict = _verdict_from_qcs(final_qcs, target_level)

    return QcsResult(
        qcs=final_qcs,
        base=base_qcs,
        penalty=penalty,
        regressions=regressions,
        level_reached=level,
        verdict=verdict,
    )


def _load_metrics(arg: str) -> dict[str, float]:
    """Charge des métriques depuis fichier JSON ou string JSON inline."""
    arg = arg.strip()
    if arg.startswith("{"):
        # Inline JSON
        return json.loads(arg)
    # Fichier
    from pathlib import Path

    path = Path(arg)
    if not path.exists():
        raise FileNotFoundError(f"Métriques introuvables : {arg}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calcule le Quality Coverage Score (QCS) DEMOEMA",
    )
    parser.add_argument(
        "--current",
        required=True,
        help="JSON inline ou path vers fichier JSON (15 dimensions, 0-100)",
    )
    parser.add_argument(
        "--previous",
        help="(Optionnel) Baseline pour détecter régressions > 10pp",
    )
    parser.add_argument(
        "--target",
        default="L4",
        choices=["L2", "L3", "L4", "L5"],
        help="Niveau cible (default L4)",
    )
    parser.add_argument(
        "--format",
        default="json",
        choices=["json", "human"],
        help="Format de sortie",
    )
    args = parser.parse_args()

    try:
        current = _load_metrics(args.current)
        previous = _load_metrics(args.previous) if args.previous else None
        result = compute_qcs(current, previous, args.target)
    except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
        print(f"ERREUR: {e}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"=== QCS DEMOEMA ===")
        print(f"QCS courant  : {result.qcs}/100")
        print(f"Base (sans pénalité) : {result.base}/100")
        if result.penalty:
            print(f"Pénalité régression : -{result.penalty} pts")
            print(f"Régressions > {REGRESSION_THRESHOLD_PP}pp détectées :")
            for dim, delta in result.regressions:
                print(f"  - {dim}: -{delta}pp")
        print(f"Niveau atteint : {result.level_reached}")
        print(f"Verdict {args.target} : {result.verdict}")

    # Exit code : 0 si verdict GO, 1 si NO-GO
    return 0 if "GO " in result.verdict and "NO-GO" not in result.verdict else 1


if __name__ == "__main__":
    sys.exit(main())
