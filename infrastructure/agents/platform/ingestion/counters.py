"""Upstream row count helpers.

Chaque source peut (optionnellement) exposer une fonction async `count_upstream()`
qui renvoie le nombre TOTAL de lignes disponibles côté source.

Retour possible :
- int >= 0 : nombre officiel (utilisé pour calculer completeness)
- None     : non supporté / non disponible → la source est exclue du check

Conventions :
- Si le module d'une source expose `count_upstream()`, l'engine l'appelle.
- Sinon, si sa spec YAML contient une clé `count_endpoint`, on essaie le pattern
  OpenDataSoft (records?limit=0 → total_count).
- Sinon, None (inconnu).

Contrat : NE JAMAIS boucler. Un seul appel HTTP, timeout court. Si ça tombe, None.
"""
from __future__ import annotations

import importlib
import logging
from typing import Optional

import httpx
import yaml
from pathlib import Path

log = logging.getLogger("demoema.counters")

SPECS_DIR = Path(__file__).parent / "specs"
COUNT_TIMEOUT = 15  # secondes — jamais plus


async def get_upstream_count(source_id: str) -> Optional[int]:
    """Retourne le count amont pour une source, ou None si indisponible.

    Ordre d'essai :
    1. Module source expose count_upstream() → on l'appelle
    2. Spec YAML contient count_endpoint → pattern OpenDataSoft
    3. None
    """
    # 1. Module-level count_upstream()
    try:
        mod = importlib.import_module(f"ingestion.sources.{source_id}")
        fn = getattr(mod, "count_upstream", None)
        if callable(fn):
            result = await fn()
            if isinstance(result, int) and result >= 0:
                return result
            return None
    except ImportError:
        pass
    except Exception as e:
        log.warning("count_upstream() raised for %s: %s", source_id, e)

    # 2. Spec-level count_endpoint (pattern OpenDataSoft)
    spec_path = SPECS_DIR / f"{source_id}.yaml"
    if spec_path.exists():
        try:
            spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
            count_url = spec.get("count_endpoint") or spec.get("endpoint")
            hint = (spec.get("count_hint") or "").lower()
            if count_url and "opendatasoft" in (count_url + hint):
                return await _count_opendatasoft(count_url)
        except Exception as e:
            log.warning("count spec fallback failed for %s: %s", source_id, e)

    return None


async def _count_opendatasoft(endpoint: str) -> Optional[int]:
    """OpenDataSoft API : GET {endpoint}?limit=0 → JSON avec total_count."""
    try:
        async with httpx.AsyncClient(timeout=COUNT_TIMEOUT) as c:
            r = await c.get(endpoint, params={"limit": 0})
            if r.status_code != 200:
                return None
            data = r.json()
            v = data.get("total_count")
            if isinstance(v, int) and v >= 0:
                return v
    except Exception:
        return None
    return None


# Helpers publics réutilisables par les fetchers
async def count_opendatasoft(endpoint: str) -> Optional[int]:
    """Helper public : un fetcher peut importer ça dans son count_upstream()."""
    return await _count_opendatasoft(endpoint)


async def count_via_header(url: str, header: str = "X-Total-Count") -> Optional[int]:
    """HEAD/GET un endpoint, lit un header de total."""
    try:
        async with httpx.AsyncClient(timeout=COUNT_TIMEOUT) as c:
            r = await c.head(url)
            if r.status_code == 405:  # HEAD not allowed
                r = await c.get(url, params={"limit": 1})
            v = r.headers.get(header)
            if v and v.isdigit():
                return int(v)
    except Exception:
        return None
    return None
