"""Tests régression SCRUM-157 — purge Pappers system prompt LLM.

TDD : ces tests sont écrits AVANT le patch.
- Tests "should fail" : prouvent le bug actuel (mention 'pappers' dans prompts)
- Tests "should pass after patch" : valideront le patch Phase 1
"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

PAPPERS_RE = re.compile(r"\bpappers\b", re.IGNORECASE)


# ────────────────────────────────────────────────────────────────────
# Niveau 2 — System prompts LLM
# ────────────────────────────────────────────────────────────────────
def test_system_prompt_full_no_pappers_mention():
    """_SYSTEM_PROMPT_FULL ne doit PAS mentionner 'pappers'."""
    from clients.deepseek import _SYSTEM_PROMPT_FULL
    assert not PAPPERS_RE.search(_SYSTEM_PROMPT_FULL), \
        f"Pappers leak dans _SYSTEM_PROMPT_FULL : ...{_SYSTEM_PROMPT_FULL[:200]}..."


def test_system_prompt_stream_no_pappers_mention():
    """_SYSTEM_PROMPT_STREAM ne doit PAS mentionner 'pappers'."""
    from clients.deepseek import _SYSTEM_PROMPT_STREAM
    assert not PAPPERS_RE.search(_SYSTEM_PROMPT_STREAM), \
        f"Pappers leak dans _SYSTEM_PROMPT_STREAM"


def test_system_prompt_tools_no_pappers_mention():
    """_SYSTEM_PROMPT_TOOLS ne doit PAS mentionner 'pappers'."""
    from clients.deepseek import _SYSTEM_PROMPT_TOOLS
    assert not PAPPERS_RE.search(_SYSTEM_PROMPT_TOOLS), \
        f"Pappers leak dans _SYSTEM_PROMPT_TOOLS"


# ────────────────────────────────────────────────────────────────────
# Niveau 3 — Tools function-calling exposés au LLM
# ────────────────────────────────────────────────────────────────────
def test_copilot_tools_no_pappers_in_names():
    """Aucun tool name ne doit contenir 'pappers'."""
    from clients.deepseek import COPILOT_TOOLS
    for tool in COPILOT_TOOLS:
        name = tool.get("function", {}).get("name", "")
        assert "pappers" not in name.lower(), f"Tool name leak Pappers : {name}"


def test_copilot_tools_no_pappers_in_descriptions():
    """Aucune description de tool ne doit mentionner 'pappers'."""
    from clients.deepseek import COPILOT_TOOLS
    for tool in COPILOT_TOOLS:
        desc = tool.get("function", {}).get("description", "")
        assert not PAPPERS_RE.search(desc), \
            f"Tool description leak Pappers : {tool.get('function',{}).get('name')}"


def test_copilot_tools_full_json_no_pappers():
    """Le JSON complet des tools (params, enum, etc.) ne mentionne pas 'pappers'."""
    from clients.deepseek import COPILOT_TOOLS
    blob = json.dumps(COPILOT_TOOLS, ensure_ascii=False).lower()
    assert "pappers" not in blob, "Pappers leak dans COPILOT_TOOLS JSON"


# ────────────────────────────────────────────────────────────────────
# Niveau 1 — Strings user-facing dans les responses copilot_query
# ────────────────────────────────────────────────────────────────────
def test_main_module_no_pappers_in_response_strings():
    """main.py copilot_query ne doit pas contenir des strings 'Pappers MCP'
    renvoyées au user via le runtime LLM.

    Scope : le bloc `async def copilot_query` (chat /api/copilot/query).
    Les routes legacy /api/pappers/* (Phase 2) sont exclues car elles
    exposent volontairement la source 'pappers-mcp' (URL = source).
    """
    main_py = Path(__file__).resolve().parents[1] / "main.py"
    src = main_py.read_text(encoding="utf-8")
    # Isoler le bloc copilot_query (entre la def et la prochaine top-level def/route)
    m = re.search(
        r"async def copilot_query\([^)]*\).*?(?=\n@app\.|\n@router\.|\nasync def |\ndef [a-z])",
        src,
        re.DOTALL,
    )
    assert m, "Impossible de localiser copilot_query dans main.py"
    block = m.group(0)
    forbidden = [
        '"Source : Pappers MCP',
        "'Source : Pappers MCP",
        '"source": "pappers-mcp"',
        "'source': 'pappers-mcp'",
        '"source": "deepseek-ai+pappers"',
        "**Recherche Pappers**",
    ]
    leaks = [s for s in forbidden if s in block]
    assert not leaks, f"Strings user-facing Pappers dans copilot_query : {leaks}"


def test_main_module_pappers_context_renamed():
    """La variable `pappers_context` doit être renommée en `datalake_context`."""
    main_py = Path(__file__).resolve().parents[1] / "main.py"
    src = main_py.read_text(encoding="utf-8")
    # Contexte injecté au LLM ne doit plus s'appeler pappers_context
    assert "pappers_context" not in src, \
        "Variable `pappers_context` encore utilisée dans main.py"


# ────────────────────────────────────────────────────────────────────
# Niveau 0 — Comportement préservé (pas de régression fonctionnelle)
# ────────────────────────────────────────────────────────────────────
def test_copilot_tools_count_preserved():
    """Le nombre de tools doit rester >= 20 (23 actuellement)."""
    from clients.deepseek import COPILOT_TOOLS
    assert len(COPILOT_TOOLS) >= 20, \
        f"Régression : {len(COPILOT_TOOLS)} tools (attendu >= 20)"


def test_copilot_tools_essential_names_present():
    """Les tool names essentiels doivent rester présents."""
    from clients.deepseek import COPILOT_TOOLS
    essential = {
        "search_cibles", "get_fiche_entreprise", "search_entreprise_by_name",
        "get_dirigeant", "get_scoring_detail", "search_signaux_bodacc",
    }
    names = {t.get("function", {}).get("name", "") for t in COPILOT_TOOLS}
    missing = essential - names
    assert not missing, f"Tools essentiels disparus : {missing}"


def test_system_prompt_full_keeps_edrcf_mention():
    """Le system prompt doit toujours mentionner EdRCF (sémantique préservée)."""
    from clients.deepseek import _SYSTEM_PROMPT_FULL
    assert "EdRCF" in _SYSTEM_PROMPT_FULL, "Sémantique EdRCF perdue"
    assert "M&A" in _SYSTEM_PROMPT_FULL or "M&amp;A" in _SYSTEM_PROMPT_FULL, "Sémantique M&A perdue"


def test_system_prompt_full_mentions_silver_or_inpi():
    """Le system prompt doit mentionner silver/INPI/SIRENE comme nouvelle source."""
    from clients.deepseek import _SYSTEM_PROMPT_FULL
    src_lower = _SYSTEM_PROMPT_FULL.lower()
    assert any(x in src_lower for x in ("silver", "inpi", "sirene", "datalake")), \
        "Aucune mention des nouvelles sources canoniques"
