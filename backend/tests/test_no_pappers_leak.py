"""Test no Pappers leak — DEMOEMA QA L4 (régression P0 SCRUM-157).

Décision projet 2026-04-23 : Pappers ABANDONNÉ. Mais l'audit régression
2026-05-02 a révélé que le copilot LLM continue à mentionner "Pappers" /
"Pappers MCP" dans 4/5 questions M&A baseline.

Cause probable : `_SYSTEM_PROMPT_TOOLS` dans `backend/clients/deepseek.py`
contient encore des références à Pappers comme source de données, et
les tools MCP exposent encore `pappers_search` / `pappers_get_company`.

Ce test couvre 3 niveaux de leak :
1. Code source : grep `pappers` (case-insensitive) dans backend/ frontend/
2. System prompt LLM : assert "pappers" absent du _SYSTEM_PROMPT_TOOLS
3. Réponses copilot runtime : 10 questions M&A baseline → 0 mention "pappers"

Run : python -m pytest backend/tests/test_no_pappers_leak.py -v
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Final

import httpx
import pytest

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
BACKEND_DIR: Final = REPO_ROOT / "backend"
FRONTEND_SRC_DIR: Final = REPO_ROOT / "frontend" / "src"

# Endpoint prod (override via env pour staging)
COPILOT_REDTEAM_URL: Final = os.getenv(
    "COPILOT_REDTEAM_URL",
    "https://82-165-57-191.sslip.io/api/copilot/redteam",
)

# 10 questions M&A baseline diversifiées — vraies queries utilisateur,
# pas des prompts hostiles. Si une de ces questions retourne "pappers",
# c'est une fuite régression.
MA_BASELINE_QUERIES: Final = [
    "fiche EQUANS",
    "scoring SIREN 552081317",
    "top 10 cibles tech IDF",
    "BODACC cessions Bretagne 30 derniers jours",
    "compare LVMH Kering Hermes",
    "dirigeant Bernard Arnault",
    "concurrents EDF dans le 75",
    "entreprises NAF 6201Z avec CA > 50M€",
    "signaux M&A semaine derniere",
    "fiche dirigeant senior agroalimentaire 60+",
]

# Pattern de détection — case-insensitive, évite les faux positifs sur
# fichier deprecated `pappers_loader.py` qui peut être mentionné dans
# une note de migration.
PAPPERS_PATTERN: Final = re.compile(r"\bpappers\b", re.IGNORECASE)


# ────────────────────────────────────────────────────────────────────
# Niveau 1 — Code source (grep statique)
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_no_pappers_in_backend_code() -> None:
    """Aucune référence active à `pappers` dans le code backend
    (hors `pappers_loader.py` qui est intentionnellement deprecated)."""
    occurrences: list[tuple[Path, int, str]] = []
    for py_file in BACKEND_DIR.rglob("*.py"):
        # Skip deprecated loader (mais on devra aussi le supprimer à terme)
        if py_file.name == "pappers_loader.py":
            continue
        # Skip caches + venv
        if any(part in {"__pycache__", ".venv", "venv"} for part in py_file.parts):
            continue
        # Skip ce test lui-même (mention attendue)
        if py_file.name == "test_no_pappers_leak.py":
            continue
        try:
            for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
                if PAPPERS_PATTERN.search(line):
                    occurrences.append((py_file.relative_to(REPO_ROOT), lineno, line.strip()[:120]))
        except (UnicodeDecodeError, OSError):
            continue

    if occurrences:
        report = "\n".join(f"  {f}:{n}  {snippet}" for f, n, snippet in occurrences[:20])
        pytest.fail(
            f"❌ {len(occurrences)} références à 'pappers' actives dans backend/ "
            f"(SCRUM-157 P0 régression).\nTop 20 occurrences :\n{report}"
        )


@pytest.mark.unit
def test_no_pappers_in_frontend_code() -> None:
    """Aucune référence active à `pappers` dans frontend/src/."""
    occurrences: list[tuple[Path, int, str]] = []
    for tsx_file in FRONTEND_SRC_DIR.rglob("*.ts*"):
        if any(part in {"node_modules", ".next"} for part in tsx_file.parts):
            continue
        try:
            for lineno, line in enumerate(tsx_file.read_text(encoding="utf-8").splitlines(), 1):
                if PAPPERS_PATTERN.search(line):
                    occurrences.append((tsx_file.relative_to(REPO_ROOT), lineno, line.strip()[:120]))
        except (UnicodeDecodeError, OSError):
            continue

    if occurrences:
        report = "\n".join(f"  {f}:{n}  {snippet}" for f, n, snippet in occurrences[:20])
        pytest.fail(
            f"❌ {len(occurrences)} références à 'pappers' actives dans frontend/src/.\n"
            f"Top 20 :\n{report}"
        )


# ────────────────────────────────────────────────────────────────────
# Niveau 2 — System prompt LLM (introspection)
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_no_pappers_in_system_prompt() -> None:
    """`_SYSTEM_PROMPT_TOOLS` (ou prompt principal) ne mentionne pas Pappers."""
    deepseek_path = BACKEND_DIR / "clients" / "deepseek.py"
    if not deepseek_path.exists():
        pytest.skip("backend/clients/deepseek.py introuvable")

    src = deepseek_path.read_text(encoding="utf-8")
    matches = list(PAPPERS_PATTERN.finditer(src))
    if matches:
        # Extraire le contexte des 3 premières mentions
        snippets: list[str] = []
        for m in matches[:3]:
            start = max(0, m.start() - 60)
            end = min(len(src), m.end() + 60)
            snippets.append(f"  ...{src[start:end].replace(chr(10), ' / ')}...")
        pytest.fail(
            f"❌ `pappers` mentionné {len(matches)}× dans deepseek.py — "
            f"le system prompt fuite Pappers au LLM.\n" + "\n".join(snippets)
        )


@pytest.mark.unit
def test_no_pappers_endpoints_exposed() -> None:
    """Aucun endpoint `/api/pappers/*` ou `/api/.*pappers.*` dans main.py."""
    main_path = BACKEND_DIR / "main.py"
    if not main_path.exists():
        pytest.skip("backend/main.py introuvable")

    src = main_path.read_text(encoding="utf-8")
    # Patterns FastAPI : @app.get("/api/pappers/..."), @router.get("/pappers/...")
    pappers_routes = re.findall(
        r'@(?:app|router)\.(?:get|post|put|patch|delete)\s*\(\s*["\']([^"\']*pappers[^"\']*)["\']',
        src,
        re.IGNORECASE,
    )
    if pappers_routes:
        pytest.fail(
            f"❌ {len(pappers_routes)} endpoints Pappers actifs dans main.py :\n"
            + "\n".join(f"  - {r}" for r in pappers_routes)
        )


# ────────────────────────────────────────────────────────────────────
# Niveau 3 — Runtime copilot (smoke 10 questions M&A baseline)
# ────────────────────────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.parametrize("query", MA_BASELINE_QUERIES, ids=lambda q: q[:40])
def test_copilot_response_no_pappers_mention(query: str) -> None:
    """Le copilot ne doit JAMAIS mentionner 'Pappers' dans une réponse user.

    Ce test fait un appel REST réel à `/api/copilot/redteam` — slow.
    Skip en local si pas d'accès prod (`SKIP_COPILOT_TESTS=1`).
    """
    if os.getenv("SKIP_COPILOT_TESTS"):
        pytest.skip("SKIP_COPILOT_TESTS=1")

    try:
        with httpx.Client(timeout=90.0) as client:
            r = client.post(COPILOT_REDTEAM_URL, json={"q": query})
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as e:
        pytest.skip(f"Endpoint indisponible : {e}")

    response_text = data.get("response", "")
    if PAPPERS_PATTERN.search(response_text):
        # Extraire le contexte du leak pour debug
        m = PAPPERS_PATTERN.search(response_text)
        assert m is not None
        start = max(0, m.start() - 80)
        end = min(len(response_text), m.end() + 80)
        leak_context = response_text[start:end]
        pytest.fail(
            f"❌ Question '{query}' → réponse copilot contient 'pappers' :\n"
            f"  ...{leak_context}..."
        )


# ────────────────────────────────────────────────────────────────────
# Bonus — git grep cross-check (intégration CI)
# ────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_git_grep_pappers_under_threshold() -> None:
    """Git grep `pappers` sur tout le repo (hors fichiers exclus) <= 50 occurrences.

    Évolution : 312 (audit 2026-05-02) → cible 0 (post SCRUM-157).
    Seuil intermédiaire 50 pour permettre la migration progressive.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "grep",
                "-c",
                "-iE",
                r"\bpappers\b",
                "--",
                ":!**/pappers_loader.py",
                ":!**/test_no_pappers_leak.py",
                ":!**/AUDIT_*.md",
                ":!**/QA_PLAYBOOKS.md",
                ":!**/docs/**",
                ":!**/.claude/**",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("git grep indisponible")

    # Format output : "path/to/file:N" (count par fichier)
    total = 0
    files: list[tuple[str, int]] = []
    for line in result.stdout.strip().splitlines():
        if ":" in line:
            path, _, count = line.rpartition(":")
            try:
                n = int(count)
                total += n
                files.append((path, n))
            except ValueError:
                continue

    THRESHOLD = 50  # SCRUM-157 progress checkpoint
    if total > THRESHOLD:
        top = sorted(files, key=lambda x: -x[1])[:10]
        report = "\n".join(f"  {f}: {n} occurrences" for f, n in top)
        pytest.fail(
            f"❌ {total} occurrences 'pappers' (seuil {THRESHOLD}) — "
            f"SCRUM-157 stagne. Top 10 fichiers :\n{report}"
        )
