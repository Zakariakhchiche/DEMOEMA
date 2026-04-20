"""Client data.gouv.fr — catalogue ouvert de l'État français.

API docs : https://doc.data.gouv.fr/api/reference
Endpoints :
  GET  https://www.data.gouv.fr/api/1/datasets/?q={query}   (search)
  GET  https://www.data.gouv.fr/api/1/datasets/{id_or_slug}/ (details)
  GET  https://www.data.gouv.fr/api/1/organizations/{id}/datasets/

Objectif : trouver les VRAIES URL d'endpoints pour les sources dont le spec YAML
a un endpoint mort. La plupart des datasets data.gouv sont hébergés sur
OpenDataSoft, data.economie.gouv.fr, ou en fichier CSV/JSON direct.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

log = logging.getLogger("demoema.data_gouv")

DG_BASE = "https://www.data.gouv.fr/api/1"
DEFAULT_TIMEOUT = 20
MAX_RESULTS = 10


async def _get(path: str, params: dict | None = None) -> dict | None:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as c:
        try:
            r = await c.get(f"{DG_BASE}{path}", params=params or {})
            if r.status_code != 200:
                return None
            return r.json()
        except Exception as e:
            log.warning("data.gouv %s failed: %s", path, e)
            return None


# ──────────── Tools exposés au LLM ────────────

async def search_datasets(q: str, limit: int = MAX_RESULTS) -> str:
    """Recherche un dataset dans le catalogue data.gouv. Retourne un résumé texte
    des top `limit` résultats (titre, slug, organisation, nb ressources)."""
    data = await _get("/datasets/", {"q": q, "page_size": min(limit, MAX_RESULTS)})
    if not data:
        return f"ERR search: pas de réponse data.gouv pour q={q!r}"
    items = data.get("data") or []
    if not items:
        return f"(aucun résultat pour q={q!r})"
    lines = [f"FOUND {len(items)} datasets for q={q!r}:"]
    for d in items:
        orgname = (d.get("organization") or {}).get("name", "?")
        lines.append(
            f"- slug={d.get('slug')!r} title={d.get('title', '?')!r} org={orgname!r} "
            f"resources={len(d.get('resources') or [])} "
            f"url=https://www.data.gouv.fr/datasets/{d.get('slug')}"
        )
    return "\n".join(lines)


async def get_dataset(slug_or_id: str) -> str:
    """Détail d'un dataset : description, organisation, list des ressources avec URL."""
    data = await _get(f"/datasets/{slug_or_id}/")
    if not data:
        return f"ERR get_dataset: dataset {slug_or_id!r} introuvable"
    resources = data.get("resources") or []
    res_lines = []
    for i, r in enumerate(resources[:15], 1):
        res_lines.append(
            f"  [{i}] format={r.get('format','?')} type={r.get('type','?')} "
            f"size={r.get('filesize') or r.get('file_size') or '?'} "
            f"url={r.get('url')}"
        )
    desc = (data.get("description") or "")[:600]
    return (
        f"title={data.get('title')!r}\n"
        f"org={(data.get('organization') or {}).get('name', '?')!r}\n"
        f"description={desc!r}\n"
        f"homepage={data.get('page', '')}\n"
        f"resources ({len(resources)}) :\n" + "\n".join(res_lines)
    )


async def probe_url(url: str) -> str:
    """Teste une URL (GET avec limite=0 si OpenDataSoft, sinon HEAD ou GET partiel).
    Retourne status + size + JSON si applicable + premiers chars du body."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as c:
        try:
            # Si URL ressemble à OpenDataSoft : tenter ?limit=0 pour voir total_count
            if "opendatasoft" in url or "/api/explore/" in url or "/api/records/" in url:
                test_url = url
                if "?" not in test_url:
                    test_url = test_url + "?limit=0"
                else:
                    test_url = test_url + "&limit=0"
                r = await c.get(test_url)
                try:
                    j = r.json()
                    total = j.get("total_count") or j.get("nhits")
                    return (f"OK status={r.status_code} ods=True total_count={total} "
                            f"content_type={r.headers.get('content-type','?')}")
                except Exception:
                    pass
            # Fallback : HEAD
            rh = await c.head(url)
            if rh.status_code in (200, 301, 302):
                return (f"OK status={rh.status_code} content_type={rh.headers.get('content-type','?')} "
                        f"content_length={rh.headers.get('content-length','?')}")
            # Sinon GET partiel
            r = await c.get(url, headers={"Range": "bytes=0-2048"})
            body = r.text[:500]
            return (f"status={r.status_code} content_type={r.headers.get('content-type','?')} "
                    f"preview={body!r}")
        except Exception as e:
            return f"ERR probe: {type(e).__name__}: {e}"


# ──────────── Tool schemas pour DeepSeek ────────────

DATAGOUV_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "dg_search",
            "description": "Search data.gouv.fr catalog. Returns top N datasets matching query with slug, title, org, resources count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Keywords — use source name and/or producer (e.g. 'SIRENE INSEE' or 'DVF valeurs foncières')"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dg_get",
            "description": "Get full dataset details (description + resources list with URLs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug_or_id": {"type": "string"},
                },
                "required": ["slug_or_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dg_probe",
            "description": "Test if a URL is reachable and usable. For OpenDataSoft URLs, returns total_count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                },
                "required": ["url"],
            },
        },
    },
]

DATAGOUV_DISPATCH = {
    "dg_search": search_datasets,
    "dg_get": get_dataset,
    "dg_probe": probe_url,
}
