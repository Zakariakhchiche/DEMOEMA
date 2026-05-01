"""
EdRCF 6.0 — Tests SIREN lookup migration Pappers → silver datalake.

Audit QA 2026-05-01 (SCRUM-NEW-04, NEW-05, NEW-11) :
- Le SIREN lookup dans `/api/copilot/stream` appelait `_papperclip_get_company`
  (recherche-entreprises.api.gouv.fr live) avec une fiche pauvre (CA + dirigeants
  seuls) + side effect `_add_company_to_targets` automatique sans confirmation
  user + mention trompeuse "Entreprise ajoutée à la base EdRCF" + source SSE
  étiquetée "pappers".
- Patch G2 : fetch direct depuis gold.entreprises_master + gold.scoring_ma +
  silver.inpi_dirigeants (instantané, fiche complète avec EBITDA, NAF lib,
  score M&A, mandats, effectif), sans side effect.

Ces tests vérifient au niveau **code source** que :
1. Le nouveau pattern (datalake direct) est en place
2. Les anti-patterns (side effect, mention trompeuse, source pappers) sont retirés
3. Le fallback gov reste opérationnel mais sans side effect non plus
"""
from __future__ import annotations

import re
from pathlib import Path

_MAIN_PY = Path(__file__).resolve().parents[1] / "main.py"


def _read_main_source() -> str:
    return _MAIN_PY.read_text(encoding="utf-8")


def _stream_endpoint_source() -> str:
    """Extrait la fonction copilot_stream_endpoint et son `generate()` interne."""
    src = _read_main_source()
    start = src.find('@app.get("/api/copilot/stream")')
    assert start >= 0, "endpoint /api/copilot/stream introuvable dans main.py"
    # Cherche la fin = prochain @app.get ou fonction au top-level
    rest = src[start:]
    next_block = re.search(r"\n\n@app\.\w+\(", rest[100:])
    if next_block:
        return rest[: 100 + next_block.start()]
    return rest


class TestSirenLookupG2Migration:
    """Le SIREN lookup dans /api/copilot/stream doit utiliser silver/gold."""

    def test_pool_dl_pool_used_for_siren_lookup(self):
        """Le datalake silver/gold est interrogé via app.state.dl_pool."""
        block = _stream_endpoint_source()
        assert "siren_match" in block
        assert "app.state" in block
        assert "dl_pool" in block

    def test_query_uses_datalake_fiche_endpoint(self):
        """Le SIREN lookup interroge l'endpoint datalake interne /api/datalake/fiche/{siren}.

        Apres fix G2 part 2, on n'a plus de SQL inline (les noms de colonnes
        gold.entreprises_master differaient → exception → fallback gov en prod).
        On utilise maintenant l'endpoint existant qui fait deja le bon mapping.
        """
        block = _stream_endpoint_source()
        # Soit on appelle /api/datalake/fiche/, soit on garde la SQL gold direct
        has_endpoint_call = "/api/datalake/fiche/" in block
        has_gold_sql = "gold.entreprises_master" in block and "gold.scoring_ma" in block
        assert has_endpoint_call or has_gold_sql, (
            "Le SIREN lookup doit interroger soit /api/datalake/fiche/{siren} "
            "soit faire la query SQL gold directe"
        )

    def test_returns_enriched_fields(self):
        """La fiche retourne désormais EBITDA + NAF lib + score M&A + mandats."""
        block = _stream_endpoint_source()
        # Champs G2 nouvellement exposés (extraits du payload fiche endpoint)
        assert "ebitda" in block.lower(), "ebitda manquant — G2 fiche enrichie"
        assert "naf_libelle" in block or "naf_lib" in block, "naf libellé manquant"
        assert "deal_score" in block or "pro_ma_score" in block, "score M&A manquant"
        assert "tier" in block, "tier M&A manquant"
        assert "n_dirigeants" in block, "nombre de mandats manquant"

    def test_source_silver_not_pappers_in_done_event(self):
        """Le done event doit annoncer source silver/gold, pas 'pappers'."""
        block = _stream_endpoint_source()
        # Recherche le pattern source dans le SSE done event après le SIREN lookup
        # G2 patch : "silver.inpi_comptes ⨝ silver.inpi_dirigeants ⨝ gold.scoring_ma"
        assert "silver.inpi_comptes" in block, "Source silver doit être annoncée dans le SSE final"

    def test_no_silent_add_to_targets_in_siren_lookup(self):
        """Le SIREN lookup ne doit PAS appeler _add_company_to_targets dans le path silver primary.

        On match l'appel actif `await _add_company_to_targets(` plutôt que la
        simple mention dans un commentaire (qui peut documenter le retrait).
        """
        block = _stream_endpoint_source()
        # Trouve le bloc primary (avant fallback)
        primary_start = block.find("# SIREN direct lookup")
        primary_end = block.find("# Fallback : datalake silver/gold ne connaît pas")
        if primary_end < 0:
            primary_end = len(block)
        primary_block = block[primary_start:primary_end] if primary_start >= 0 else ""
        # Strip lignes commentées pour ne tester que le code actif
        active_lines = [
            ln for ln in primary_block.split("\n")
            if not ln.lstrip().startswith("#")
        ]
        active_code = "\n".join(active_lines)
        assert "await _add_company_to_targets(" not in active_code, (
            "Le path silver primary ne doit PAS appeler await _add_company_to_targets(...) "
            "(side effect non sollicité — audit QA SCRUM-NEW-11)"
        )

    def test_no_entreprise_ajoutee_in_silver_response(self):
        """Le markdown silver ne doit PAS mentionner 'Entreprise ajoutée à la base EdRCF'.

        On filtre les commentaires Python (qui peuvent documenter le retrait
        de cette mention) pour ne tester que les strings émises par le code actif.
        """
        block = _stream_endpoint_source()
        primary_end = block.find("# Fallback")
        primary_block = block[:primary_end] if primary_end >= 0 else block
        active_lines = [
            ln for ln in primary_block.split("\n")
            if not ln.lstrip().startswith("#")
        ]
        active_code = "\n".join(active_lines)
        assert "Entreprise ajoutée à la base EdRCF" not in active_code, (
            "Le path silver ne doit PAS afficher 'Entreprise ajoutée à la base EdRCF' "
            "dans une string émise — c'est un side effect trompeur "
            "(audit QA SCRUM-NEW-11)"
        )

    def test_targets_updated_false_in_silver_path(self):
        """Le done event silver renvoie targets_updated=False (read-only fiche)."""
        block = _stream_endpoint_source()
        # Trouve le label source silver dans le done event
        src_label = block.find('"silver.inpi_comptes')
        assert src_label > 0, "Source silver.inpi_comptes manquante"
        # Cherche dans une fenetre autour (avant + apres) — le dict est sur plusieurs lignes
        window = block[max(0, src_label - 500): src_label + 500]
        assert '"targets_updated": False' in window or \
               "'targets_updated': False" in window, (
            "Le done event silver doit annoncer targets_updated=False"
        )


class TestSirenLookupG2Fallback:
    """Si datalake silver/gold n'a pas le SIREN, fallback gov sans side effect."""

    def test_fallback_uses_papperclip_get_company(self):
        """Le fallback continue d'utiliser _papperclip_get_company."""
        block = _stream_endpoint_source()
        assert "_papperclip_get_company" in block

    def test_fallback_no_side_effect(self):
        """Le fallback gov n'appelle PAS _add_company_to_targets non plus."""
        block = _stream_endpoint_source()
        fallback_start = block.find("# Fallback : datalake silver/gold")
        if fallback_start < 0:
            return  # skip si pas de fallback dans le code lu
        fallback_block = block[fallback_start:fallback_start + 3000]
        active_lines = [
            ln for ln in fallback_block.split("\n")
            if not ln.lstrip().startswith("#")
        ]
        active_code = "\n".join(active_lines)
        assert "await _add_company_to_targets(" not in active_code, (
            "Le fallback gov ne doit PAS non plus avoir le side effect "
            "(audit SCRUM-NEW-11)"
        )

    def test_fallback_source_explicit(self):
        """Le fallback annonce explicitement annuaire-entreprises (pas pappers-mcp)."""
        block = _stream_endpoint_source()
        fallback_start = block.find("# Fallback : datalake silver/gold")
        if fallback_start < 0:
            return
        fallback_block = block[fallback_start:fallback_start + 3000]
        assert "annuaire-entreprises" in fallback_block.lower(), (
            "Le fallback doit annoncer annuaire-entreprises.data.gouv.fr "
            "(et pas le label trompeur 'pappers')"
        )


def test_module_syntactically_valid():
    """Le module main.py reste importable (syntaxe Python)."""
    import ast
    src = _read_main_source()
    ast.parse(src)
