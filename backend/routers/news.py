"""Routes Google News + Infogreffe — extraites de main.py:1069-1142.

Chaque route :
- valide le siren via domain.validators (audit SEC-8)
- timeout strict pour ne pas geler
- détecte les signaux M&A à partir du contenu
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from clients.google_news import get_google_news
from clients.infogreffe import get_infogreffe_actes
from domain.validators import validate_siren

router = APIRouter(tags=["news"])


@router.get("/api/news/{siren}")
async def get_news_for_company(siren: str):
    """Fetch recent press articles from Google News RSS pour un SIREN.

    Optimisation : si la company est déjà en mémoire, on fait directement
    Google News. Sinon, lookup Pappers concurrent + fetch news, gardés
    sous 9s total via asyncio.wait_for.
    """
    siren = validate_siren(siren)

    # Lazy import pour éviter circulaire avec main (qui importe ce router).
    import main
    target = next((t for t in main.enriched_targets if t.get("siren") == siren), None)
    if target:
        company_name = target["name"]
        try:
            articles = await asyncio.wait_for(get_google_news(company_name), timeout=8)
        except asyncio.TimeoutError:
            articles = []
    else:
        async def _resolve_and_fetch():
            try:
                pappers_data = await asyncio.wait_for(
                    main.get_pappers_company(siren), timeout=6,
                )
                name = (pappers_data or {}).get("nom_entreprise") or siren
            except Exception:
                name = siren
            return name, await get_google_news(name)

        try:
            company_name, articles = await asyncio.wait_for(_resolve_and_fetch(), timeout=9)
        except asyncio.TimeoutError:
            company_name, articles = siren, []

    detected_signals: set = set()
    for a in articles:
        for sig in a.get("signals", []):
            detected_signals.add(sig)

    return {
        "data": {
            "company": company_name,
            "siren": siren,
            "articles": articles,
            "signals_detected": list(detected_signals),
        }
    }


@router.get("/api/infogreffe/{siren}")
async def get_infogreffe_endpoint(siren: str):
    """Fetch recent actes RCS from Infogreffe open data for a SIREN."""
    siren = validate_siren(siren)
    try:
        actes = await asyncio.wait_for(get_infogreffe_actes(siren), timeout=8)
    except asyncio.TimeoutError:
        actes = []

    detected_signals: set = set()
    for acte in actes:
        acte_type = (acte.get("type") or "").lower()
        if any(w in acte_type for w in ["nomination", "gerant", "president", "directeur"]):
            detected_signals.add("infogreffe_nouveau_dirigeant")
        if any(w in acte_type for w in ["capital", "augmentation", "reduction"]):
            detected_signals.add("infogreffe_capital_change")
        if any(w in acte_type for w in ["fusion", "absorption", "scission"]):
            detected_signals.add("infogreffe_fusion_absorption")
        if any(w in acte_type for w in ["transfert", "siege"]):
            detected_signals.add("infogreffe_transfert_siege")

    return {
        "data": {
            "siren": siren,
            "actes": actes,
            "signals_detected": list(detected_signals),
        }
    }
