"""Test détecteur : tous les fetchers `_delta` doivent gérer le first-run
(bronze table vide → backfill avec fenêtre élargie).

Sans ce pattern, sur un VPS migré la bronze table reste à 0 ligne après
le premier tick scheduler — le `_delta` part de `now - 48h` qui ne ramène
rien sur une DB vide.

Convention DEMOEMA établie dans `bodacc.py:153` :
    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)

Ce test fait la liste des fetchers actifs et signale les trous. Pour les
nouveaux fetchers générés par le LLM, le prompt `codegen.py:130` exige
explicitement la règle #6 ("Backfill first-run").
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SOURCES_DIR = Path(__file__).resolve().parent.parent / "ingestion" / "sources"


def _list_delta_fetchers() -> list[Path]:
    """Liste les fichiers Python qui exposent un `fetch_<sid>_delta` (donc
    soumis à la convention first-run). Exclut les `_full`-only et templates."""
    fetchers: list[Path] = []
    for py in sorted(SOURCES_DIR.glob("*.py")):
        if py.name.startswith("_"):
            continue
        text = py.read_text(encoding="utf-8")
        # Cherche `async def fetch_<sid>_delta` (le sid peut contenir n'importe quoi)
        if re.search(r"async def fetch_\w+_delta\s*\(", text):
            fetchers.append(py)
    return fetchers


def _has_first_run_backfill(text: str) -> bool:
    """Détecte le pattern d'élargissement window quand bronze table est vide."""
    patterns = [
        r"if\s+existing\s*==\s*0",
        r"if\s+count\s*==\s*0",
        r"BACKFILL_DAYS_FIRST_RUN",
        r"backfill_days_first_run",
        r"if\s+\w+_count\s*==\s*0",
        r"empty.*backfill",
        r"first.*run.*backfill",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


# Liste des fetchers connus comme **légitimement** sans pattern first-run :
# - RSS = pas de backfill historique possible (flux limité)
# - Sources qui ont uniquement `_full` (déclenchées par cron, pas delta)
# Si le test failure remonte un fetcher absent de cette whitelist, il faut
# ajouter le pattern empty-check ou le justifier dans cette liste.
KNOWN_NO_BACKFILL_OK = {
    # RSS (le flux ne contient que les derniers articles)
    "google_news_rss.py",
    "cfnews_rss.py",
    "la_tribune_rss.py",
    "les_echos_rss.py",
    "press_rss.py",
    "usine_nouvelle_rss.py",
}

# TODO — fetchers identifiés comme nécessitant le pattern first-run mais
# pas encore patchés (audit migration VPS 2026-04-27). Sur un VPS migré,
# ces sources restent à 0 ligne après le premier tick. Solution :
#   - Soit patcher manuellement chaque fetcher (cf. bodacc.py:147-164)
#   - Soit déclencher leur regen par le maintainer (silver_codegen) avec
#     feedback explicit "table still empty after delta"
#   - Soit le user lance manuellement /api/admin/run-all après migration
# Cette liste sera vidée progressivement.
TODO_NEED_FIRST_RUN_PATCH = {
    "inpi_comptes_annuels.py",  # INPI dépôts comptes — bulk dump nécessaire
    "insee_sirene_v3.py",        # SIRENE 40M établissements — full sync needed
    "opensanctions.py",          # Sanctions list — has _full but pattern manquant
    "osint_companies.py",        # OSINT data — flux delta only
    "press_articles.py",         # Articles presse — pattern à clarifier
}


def test_first_run_backfill_coverage():
    """Les fetchers `_delta` non whitelistés doivent gérer le first-run.
    Sinon : sur un VPS migré, leur bronze table reste vide silencieusement.
    """
    delta_fetchers = _list_delta_fetchers()
    assert delta_fetchers, "Aucun fetcher _delta trouvé — sources/ peut-être vide ?"

    missing: list[str] = []
    for py in delta_fetchers:
        if py.name in KNOWN_NO_BACKFILL_OK or py.name in TODO_NEED_FIRST_RUN_PATCH:
            continue
        text = py.read_text(encoding="utf-8")
        if not _has_first_run_backfill(text):
            missing.append(py.name)

    if missing:
        msg = (
            f"\n{len(missing)} fetchers `_delta` sans pattern first-run backfill :\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\nSur un VPS migré, ces sources restent à 0 ligne après le premier\n"
            "tick scheduler. Ajoute le pattern (cf. bodacc.py:147-164) :\n\n"
            "    if existing == 0:\n"
            "        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)\n"
            "    else:\n"
            "        window = timedelta(hours=INCREMENTAL_HOURS)\n\n"
            "Ou ajoute le fichier à KNOWN_NO_BACKFILL_OK avec justification.\n"
        )
        pytest.fail(msg)
