"""Tools pour lire et patcher les specs YAML d'ingestion.

Usage par source_hunter : une fois une URL correcte trouvée, appeler patch_endpoint
pour écrire la nouvelle URL dans le YAML. Le scheduler la rechargera au prochain restart.

Tools :
  read_spec(source_id) → YAML complet (texte)
  patch_endpoint(source_id, new_url, count_endpoint=None) → succès/échec
  run_fetcher(source_id) → exécute le fetcher + renvoie rows
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

log = logging.getLogger("demoema.specs_rw")

SPECS_DIR = Path("/app/ingestion/specs")


async def read_spec(source_id: str) -> str:
    p = SPECS_DIR / f"{source_id}.yaml"
    if not p.exists():
        return f"ERR spec {source_id}.yaml introuvable"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERR read: {e}"


async def patch_endpoint(source_id: str, new_url: str,
                         count_endpoint: str | None = None,
                         source_format: str | None = None) -> str:
    """Remplace `endpoint:` + optionnel `count_endpoint:` + optionnel `format:` du YAML.
    Backup .bak au 1er patch. format= csv|rest_json|jsonl|zip|parquet|geojson|xml — dirige codegen."""
    p = SPECS_DIR / f"{source_id}.yaml"
    if not p.exists():
        return f"ERR spec {source_id}.yaml introuvable"
    if not new_url.startswith(("http://", "https://")):
        return f"ERR invalid URL (doit commencer par http/https): {new_url!r}"
    try:
        original = p.read_text(encoding="utf-8")
        bak = p.with_suffix(".yaml.bak")
        if not bak.exists():
            bak.write_text(original, encoding="utf-8")

        new = re.sub(r"(?m)^endpoint:\s*.*$", f"endpoint: {new_url}", original, count=1)
        if new == original:
            new = new + f"\nendpoint: {new_url}\n"

        if count_endpoint:
            if re.search(r"(?m)^count_endpoint:\s*.*$", new):
                new = re.sub(r"(?m)^count_endpoint:\s*.*$",
                             f"count_endpoint: {count_endpoint}", new, count=1)
            else:
                new = new.rstrip() + f"\ncount_endpoint: {count_endpoint}\n"

        if source_format:
            if re.search(r"(?m)^format:\s*.*$", new):
                new = re.sub(r"(?m)^format:\s*.*$",
                             f"format: {source_format}", new, count=1)
            else:
                new = new.rstrip() + f"\nformat: {source_format}\n"

        try:
            yaml.safe_load(new)
        except Exception as e:
            return f"ERR invalid YAML after patch: {e}"
        p.write_text(new, encoding="utf-8")
        suffix = ""
        if count_endpoint: suffix += f" + count_endpoint → {count_endpoint}"
        if source_format:  suffix += f" + format → {source_format}"
        return f"OK patched {p.name} : endpoint → {new_url}" + suffix
    except Exception as e:
        return f"ERR patch: {type(e).__name__}: {e}"


async def regenerate_fetcher(source_id: str) -> str:
    """Régénère le code Python du fetcher à partir du spec YAML (patché par patch_endpoint).
    Nécessaire après patch_endpoint : sans régénération, le .py garde l'ancienne URL hardcodée."""
    try:
        from ingestion.codegen import generate_fetcher
    except ImportError as e:
        return f"ERR codegen indisponible: {e}"
    try:
        r = await generate_fetcher(source_id)
        if r.get("file"):
            return f"OK regen {source_id} → {r.get('bytes')} bytes ({r.get('file')})"
        return f"ERR regen {source_id}: {r.get('error', 'no file produced')}"
    except Exception as e:
        return f"ERR regen crash: {type(e).__name__}: {e}"


async def run_fetcher(source_id: str) -> str:
    """Exécute le fetcher de la source et renvoie le résultat (rows, errors)."""
    try:
        from ingestion.engine import run_source, SOURCES
        if source_id not in SOURCES:
            # Essayer hot-reload (au cas où le fetcher vient d'être régénéré)
            try:
                import importlib
                mod_name = f"ingestion.sources.{source_id}"
                if mod_name in importlib.sys.modules:
                    importlib.reload(importlib.sys.modules[mod_name])
                importlib.import_module(mod_name)
            except Exception as e:
                return f"ERR run_fetcher: source {source_id} pas dans SOURCES et hot-reload échoué ({e})"
        if source_id not in SOURCES:
            return f"ERR run_fetcher: source {source_id} toujours inconnue — redémarre le container"
        r = await run_source(source_id)
        rows = r.get("rows", 0) if isinstance(r, dict) else 0
        err = r.get("error") if isinstance(r, dict) else None
        keys = "/".join(k for k in r.keys() if k not in ("error",)) if isinstance(r, dict) else ""
        return f"OK source={source_id} rows={rows} error={err!r} keys={keys}"
    except Exception as e:
        log.exception("run_fetcher crashed")
        return f"ERR run_fetcher: {type(e).__name__}: {e}"


SPECSRW_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_spec",
            "description": "Read the YAML spec of a source (endpoint, auth, volume, etc.).",
            "parameters": {
                "type": "object",
                "properties": {"source_id": {"type": "string"}},
                "required": ["source_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patch_endpoint",
            "description": "Update spec YAML: endpoint URL + optional count_endpoint + source_format (csv|rest_json|jsonl|zip|parquet|geojson|xml). The format field drives which fetcher template codegen produces.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "new_url": {"type": "string"},
                    "count_endpoint": {"type": "string"},
                    "source_format": {"type": "string", "description": "Data format, e.g. csv, rest_json, jsonl, zip, parquet, geojson"},
                },
                "required": ["source_id", "new_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "regenerate_fetcher",
            "description": "REQUIRED after patch_endpoint. Regenerates the Python fetcher code from the updated spec YAML so it uses the new URL and proper parsing logic. Without this, the old fetcher .py still uses the hardcoded old URL.",
            "parameters": {
                "type": "object",
                "properties": {"source_id": {"type": "string"}},
                "required": ["source_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_fetcher",
            "description": "Execute the fetcher of a source to test if data loads. Call AFTER regenerate_fetcher.",
            "parameters": {
                "type": "object",
                "properties": {"source_id": {"type": "string"}},
                "required": ["source_id"],
            },
        },
    },
]

SPECSRW_DISPATCH = {
    "read_spec": read_spec,
    "patch_endpoint": patch_endpoint,
    "regenerate_fetcher": regenerate_fetcher,
    "run_fetcher": run_fetcher,
}
