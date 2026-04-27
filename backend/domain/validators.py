"""Validators métier réutilisables — un seul endroit canonique.

Avant : `_validate_siren` dans main.py utilisé sporadiquement, dupliqué
inline dans get_company_statut, jamais sur certaines routes (audit SEC-8).
Désormais : importé partout.
"""
from __future__ import annotations

from fastapi import HTTPException


def validate_siren(siren: str) -> str:
    """Valide qu'un siren est une chaîne 9 chiffres et retourne la version normalisée.

    Lève HTTPException(400) si invalide. Permet de l'utiliser comme dépendance
    Path/Query :

        from fastapi import Path
        from domain.validators import validate_siren
        @router.get("/api/foo/{siren}")
        async def foo(siren: str = Path(..., regex=r"^\\d{9}$")):
            ...

    Ou en helper inline pour les sirens issus de payload/cache.
    """
    if not siren:
        raise HTTPException(400, "siren manquant")
    cleaned = siren.strip().replace(" ", "").replace(".", "")
    if not (len(cleaned) == 9 and cleaned.isdigit()):
        raise HTTPException(400, f"siren invalide : '{siren}' (doit être 9 chiffres)")
    return cleaned
