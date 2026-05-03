"""mutmut configuration — DEMOEMA mutation testing (Sprint 2 — L4 dim 4).

NOTE Windows : mutmut a un known-issue (#397) sur Windows natif (subprocess
+ sqlite3 lock). Ce fichier est conçu pour tourner UNIQUEMENT sur CI Linux
(`.github/workflows/qa-mutation-testing.yml`).

Modules ciblés (5) — choisis pour leur impact runtime + sécurité :
  1. backend/clients/deepseek.py      — system prompts + tool definitions LLM
  2. backend/domain/scoring.py        — calcul deal_score
  3. backend/domain/validators.py     — validate_siren (regex Luhn)
  4. backend/main.py                  — copilot_query handler + _PROMPT_INJECTION_PATTERNS

Cible mutation score : ≥ 80 % (échec build CI sinon).
"""
from __future__ import annotations

import os


# Modules à muter. Mutmut accepte une liste séparée par virgules via
# `--paths-to-mutate` ; on l'expose ici pour que le workflow CI lise la
# même source de vérité.
PATHS_TO_MUTATE: list[str] = [
    "backend/clients/deepseek.py",
    "backend/domain/scoring.py",
    "backend/domain/validators.py",
    "backend/main.py",
]


def pre_mutation(context):  # noqa: D401 — mutmut hook signature.
    """Hook mutmut : skip mutations hors zones critiques de main.py.

    On laisse mutmut muter `clients/deepseek.py`, `domain/*.py` entièrement,
    mais sur `main.py` on cible UNIQUEMENT :
      - la fonction `copilot_query`
      - le bloc `_PROMPT_INJECTION_PATTERNS`
    Tout le reste de main.py (boilerplate FastAPI, mounts) est skip pour
    garder le run < 30 min et rester dans le budget CI hebdo.
    """
    filename = context.filename or ""
    if not filename.endswith("main.py"):
        return  # mute everything for clients/* + domain/*

    src = context.current_source_line or ""
    line_no = context.current_line_index  # 0-based

    # Lire le fichier pour repérer les bornes des zones critiques.
    target_path = os.path.join(os.path.dirname(__file__), "main.py")
    if not os.path.isfile(target_path):
        context.skip = True
        return

    with open(target_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_critical_zone = False
    # Zone 1 : _PROMPT_INJECTION_PATTERNS (constant assignment, possibly multi-line).
    for i, raw in enumerate(lines):
        if "_PROMPT_INJECTION_PATTERNS" in raw and "=" in raw:
            # Étendre jusqu'à fermeture du bloc (ligne sans indent + qui ne continue pas).
            start = i
            end = i
            for j in range(i + 1, min(i + 200, len(lines))):
                stripped = lines[j].rstrip("\n")
                if stripped == "" or stripped.startswith(("def ", "class ", "@")):
                    end = j - 1
                    break
                end = j
            if start <= line_no <= end:
                in_critical_zone = True
                break

    # Zone 2 : def copilot_query(...) jusqu'à la prochaine `def` au même niveau.
    if not in_critical_zone:
        for i, raw in enumerate(lines):
            if raw.lstrip().startswith("def copilot_query") or raw.lstrip().startswith(
                "async def copilot_query"
            ):
                start = i
                end = len(lines) - 1
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("def ") or lines[j].startswith("async def "):
                        end = j - 1
                        break
                if start <= line_no <= end:
                    in_critical_zone = True
                    break

    if not in_critical_zone:
        context.skip = True


def init():  # noqa: D401 — mutmut hook.
    """Configuration globale mutmut."""
    return {
        "paths_to_mutate": ",".join(PATHS_TO_MUTATE),
        "tests_dir": "backend/tests/",
        # Test-runner : pytest avec opts minimales (no-cov pour vitesse).
        "runner": "python -m pytest -p no:schemathesis backend/tests/ --no-cov -x -q",
        # Budget par mutation.
        "timeout": 60,
        # Garder mutmut bavard pour debug CI.
        "use_coverage": False,
    }
