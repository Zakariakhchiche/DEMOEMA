"""Tools : HTTP GET + endpoint validation."""
from __future__ import annotations

import httpx


async def httpx_get(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"error": "URL invalide"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(url)
        preview = r.text[:2000] if "text" in r.headers.get("content-type", "") or "json" in r.headers.get("content-type", "") else f"<{len(r.content)} bytes binaire>"
        return {"status": r.status_code, "content_type": r.headers.get("content-type", ""), "body_preview": preview}


async def test_endpoint(url: str, method: str = "GET", params: dict | None = None) -> dict:
    """Valide qu'un endpoint existe + examine sa réponse avant codegen.
    Retourne : works, status, content_type, is_json, preview_200, sample_record_keys."""
    if not url.startswith(("http://", "https://")):
        return {"works": False, "error": "URL invalide"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                      headers={"User-Agent": "DEMOEMA-Agents/0.1 (contact@demoema.fr)"}) as c:
            r = await c.request(method.upper(), url, params=params or {})
        ct = r.headers.get("content-type", "")
        is_json = "json" in ct
        is_xml = "xml" in ct
        works = 200 <= r.status_code < 300
        result = {
            "url": url,
            "works": works,
            "status": r.status_code,
            "content_type": ct,
            "is_json": is_json,
            "is_xml": is_xml,
            "content_length": len(r.content),
            "preview_200": r.text[:400] if "text" in ct or is_json else f"<{len(r.content)} bytes>",
        }
        # Extraire les clés d'1 record si JSON (pour guider l'agent)
        if is_json and works:
            try:
                import json
                data = r.json()
                if isinstance(data, list) and data:
                    result["sample_record_keys"] = list(data[0].keys())[:20] if isinstance(data[0], dict) else None
                elif isinstance(data, dict):
                    # Chercher une liste dans le payload (ex: {"results":[...], "records":[...]})
                    result["top_keys"] = list(data.keys())[:20]
                    for k, v in data.items():
                        if isinstance(v, list) and v and isinstance(v[0], dict):
                            result["array_path"] = k
                            result["sample_record_keys"] = list(v[0].keys())[:20]
                            break
            except Exception as e:
                result["parse_error"] = str(e)[:200]
        return result
    except Exception as e:
        return {"url": url, "works": False, "error": str(e)[:300], "type": type(e).__name__}
