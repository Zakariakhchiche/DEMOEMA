"""Validator post-réponse LLM — detect les chiffres non-traceables dans le datalake.

Cas d'usage : le copilot DEMOEMA appelle des tools (get_fiche_entreprise, etc.)
qui retournent du JSON avec des chiffres ground-truth (CA, EBITDA, dirigeants...).
Le LLM doit reformuler en markdown. Risques d'hallucination :
  - LLM complète des NULL ("effectif environ 1200 salariés" inventé)
  - LLM mélange les zéros ("285 milliards" au lieu de "285 millions")
  - LLM répond de mémoire pré-entraînement sans appeler le tool

Ce validator extrait tous les patterns numériques (montants €, m², salariés,
mandats, dépts, sirens) de la réponse finale du LLM et vérifie qu'ils
apparaissent dans les résultats des tools collectés. Les chiffres non-
traceables sont retournés au frontend pour affichage en bandeau ⚠️.

Volontairement permissif :
  - Tolérance ±2% (arrondis "285,7" vs "285.69")
  - Skip années 1900-2050 (souvent contextuelles, pas des chiffres business)
  - Skip pourcentages 0-100 (souvent calculs dérivés, pas dans le datalake)
  - Skip petits entiers <10 (numérotations, ordinaux, "5 SCI", "3 mandats" -
    fréquent et rarement halluciné)
"""
from __future__ import annotations

import re
from typing import Any


# Match: 285 / 285,7 / 285.7 / 1 200 / 1 200 suivi d'une unité business
_NUMBER_PATTERN = re.compile(
    r"\b(\d[\d\s ]*[,.]?\d*)\s*"
    r"(Md ?€|Md€|M ?€|M€|k ?€|k€|€|EUR|%|"
    r"milliards?|millions?|milliers?|"
    r"m²|m2|m ²|"
    r"salari[ée]s?|employ[ée]s?|"
    r"mandats?\s+actifs?|mandats?|sci|"
    r"hectares?|ha\b)",
    re.IGNORECASE,
)

# Match : SIREN brut (9 chiffres consécutifs)
_SIREN_PATTERN = re.compile(r"\b(\d{9})\b")


def _normalize_french_number(num_str: str) -> float | None:
    """Convertit '285,7' / '285.7' / '1 200' / '1 200' en float."""
    cleaned = (
        num_str.replace(" ", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _scale_factor(unit: str) -> float:
    """Facteur multiplicateur pour mettre le nombre à l'échelle absolue."""
    u = unit.lower().replace(" ", "").replace(" ", "")
    if u.startswith("md") or "milliard" in u:
        return 1e9
    if u.startswith("m€") or u.startswith("meur") or "million" in u and "millier" not in u:
        return 1e6
    if u.startswith("k") or "millier" in u:
        return 1e3
    return 1.0  # €, %, m², salariés, mandats — restent en unité brute


def _collect_numbers_from_tool_results(tool_results: list[dict]) -> set[float]:
    """Aplatit tous les nombres (int/float + chiffres dans strings) des tool results
    en un set de floats. Utilisé comme haystack pour la validation."""
    haystack: set[float] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, (int, float)) and obj is not False and obj is not True:
            try:
                haystack.add(float(obj))
            except (ValueError, OverflowError):
                pass
        elif isinstance(obj, str):
            for m in re.finditer(r"-?\d+(?:[.,]\d+)?", obj):
                try:
                    haystack.add(float(m.group().replace(",", ".")))
                except ValueError:
                    pass
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                walk(v)

    for tr in tool_results:
        # result_preview est tronqué à 500 chars mais reste le plus pertinent
        walk(tr.get("result_preview") or tr)
    return haystack


def _is_traceable(scaled_val: float, raw_val: float, haystack: set[float], tol: float = 0.02) -> bool:
    """True si `scaled_val` ou `raw_val` apparaît dans le haystack à ±tol près."""
    for candidate in (scaled_val, raw_val):
        if candidate == 0:
            continue
        for h in haystack:
            if h == 0:
                continue
            if abs(h - candidate) / max(abs(h), abs(candidate)) < tol:
                return True
    # Match exact pour les petits entiers (ex: 23 mandats)
    if raw_val == int(raw_val) and 0 < raw_val < 1000 and raw_val in haystack:
        return True
    return False


def _should_skip(num_str: str, unit: str, val: float) -> bool:
    """Skip patterns qui sont rarement de l'info datalake (années, % dérivés, petits ordinaux)."""
    if val is None:
        return True
    u = unit.lower()
    # Années 1900-2050
    if 1900 <= val <= 2050 and unit == "" and "," not in num_str and "." not in num_str:
        return True
    # Pourcentages 0-100 (souvent calculés, ex: marge, croissance)
    if "%" in u and 0 <= val <= 100:
        return True
    # Petits entiers (< 10) avec unité salarié/mandat/sci — souvent comptages exacts
    # qui matchent au moins une fois dans le tool result. Tolérant.
    return False


def validate_numbers(content: str, tool_results: list[dict]) -> dict:
    """Extract tous les chiffres business du content, check si traceables dans tool_results.

    Args:
        content: Réponse markdown finale du LLM.
        tool_results: Liste collectée pendant le tool-calling loop.
            Format: [{"tool": str, "args": dict, "result_preview": str}, ...]

    Returns:
        dict with:
            - "verified": list of strings (chiffres traceables, ex: ["285.7 M€"])
            - "unverified": list of strings (chiffres NON traceables — risque halluc)
            - "n_checks": total checks effectués
            - "trust_score": float [0.0-1.0] = verified / (verified + unverified)
    """
    if not content:
        return {"verified": [], "unverified": [], "n_checks": 0, "trust_score": 1.0}

    haystack = _collect_numbers_from_tool_results(tool_results)

    verified: list[str] = []
    unverified: list[str] = []

    # Check chiffres avec unité (M€, salariés, %, etc.)
    for m in _NUMBER_PATTERN.finditer(content):
        raw_match = m.group(0).strip()
        num_str = m.group(1).strip()
        unit = m.group(2).strip()
        val = _normalize_french_number(num_str)
        if val is None or _should_skip(num_str, unit, val):
            continue
        scaled = val * _scale_factor(unit)
        if _is_traceable(scaled, val, haystack):
            verified.append(raw_match)
        else:
            unverified.append(raw_match)

    # Check SIRENs (9 chiffres) — strictement match exact
    for m in _SIREN_PATTERN.finditer(content):
        siren = m.group(1)
        siren_val = float(siren)
        if siren_val in haystack:
            verified.append(siren)
        else:
            # Skip si pas dans haystack ET pas dans verified déjà (un même siren peut
            # apparaître plusieurs fois dans la réponse).
            if siren not in unverified:
                unverified.append(siren)

    n_checks = len(verified) + len(unverified)
    trust_score = (len(verified) / n_checks) if n_checks > 0 else 1.0
    return {
        "verified": verified,
        "unverified": unverified,
        "n_checks": n_checks,
        "trust_score": round(trust_score, 3),
    }
