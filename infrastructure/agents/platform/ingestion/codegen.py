"""Codegen pipeline — l'agent lead-data-engineer génère le .py fetcher à partir d'un spec YAML.

Flow :
1. Lire spec YAML
2. Préparer prompt (spec + exemple bodacc.py + instructions strictes)
3. Appeler Ollama Cloud (agent lead-data-engineer)
4. Extraire le code Python de la réponse (fences ```python ... ```)
5. Valider avec ast.parse
6. Écrire dans sources/{source_id}.py
7. Hot-reload dynamique (importlib) + register dans engine.SOURCES

⚠️ Code généré jamais exécuté arbitrairement — whitelist strict :
- Path écriture = sources/*.py uniquement
- Syntaxe Python validée
- Imports whitelist (httpx, psycopg, datetime, json, logging, etc.)
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import json
import logging
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from loader import get_agent
from ollama_client import OllamaClient

log = logging.getLogger("demoema.codegen")

SPECS_DIR = Path(__file__).parent / "specs"
SOURCES_DIR = Path(__file__).parent / "sources"
REFERENCE_FETCHER = SOURCES_DIR / "bodacc.py"

# Références par format — chaque format pointe vers un fetcher existant à mimer.
# Si absent → fallback sur bodacc.py (REST JSON delta + bulk CSV section).
REFERENCE_BY_FORMAT = {
    "rest_json": SOURCES_DIR / "bodacc.py",              # pattern delta REST + pagination
    "csv":       SOURCES_DIR / "bodacc.py",              # pattern bodacc_full (stream CSV)
    "csv_gz":    SOURCES_DIR / "bodacc.py",              # CSV gzippé
    "zip":       SOURCES_DIR / "_zip_csv_ref.py",        # ZIP-of-CSV dédié (DVF, BAN, SIRENE stock)
    "jsonl":     SOURCES_DIR / "opensanctions.py",       # JSON Lines streaming
    "geojson":   SOURCES_DIR / "bodacc.py",              # générique (LLM adapte)
    "parquet":   SOURCES_DIR / "bodacc.py",              # LLM adapte (pyarrow)
    "xml":       SOURCES_DIR / "bodacc.py",              # LLM adapte (lxml streaming)
}

FORMAT_HINTS = {
    "rest_json": "REST API JSON paginée. Utilise le pattern bodacc.fetch_bodacc_delta : loop de pages avec offset+limit, insert par page.",
    "csv":       "CSV à streamer (dump file ou API avec format CSV). Utilise le pattern bodacc.fetch_bodacc_full : client.stream('GET', url), aiter_text(1MB chunks), csv.reader par ligne, batch 1000 → executemany.",
    "zip":       "ZIP contenant un ou plusieurs CSV/JSON. Télécharge avec streaming, utilise zipfile.ZipFile pour extraire, puis traite chaque membre comme CSV.",
    "jsonl":     "JSON Lines (1 objet JSON par ligne). Stream le fichier, split par '\\n', json.loads par ligne, batch insert.",
    "geojson":   "GeoJSON FeatureCollection. Récupère .features[], chaque feature a .properties + .geometry. Stocke payload JSONB complet + extract coords si utile.",
    "parquet":   "Parquet binary. Utilise pyarrow.parquet.ParquetFile avec iter_batches(batch_size=1000). Si grosses tables, streamer colonne-à-colonne.",
    "xml":       "XML. Utilise lxml.etree.iterparse(source) pour streaming events. Parse element par element, extraire les champs clés.",
}

ALLOWED_IMPORTS = {
    "__future__",
    "asyncio", "datetime", "json", "logging", "re", "os", "typing", "time", "hashlib", "collections",
    "csv", "io", "zipfile", "gzip", "shutil", "tempfile",
    "httpx", "psycopg", "lxml", "feedparser", "yaml",
    "pyarrow", "pyarrow.parquet",
    "config", "psycopg.types.json", "psycopg.types",
}


def load_spec(source_id: str) -> dict | None:
    path = SPECS_DIR / f"{source_id}.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def list_specs() -> list[dict]:
    specs = []
    for p in sorted(SPECS_DIR.glob("*.yaml")):
        try:
            s = yaml.safe_load(p.read_text(encoding="utf-8"))
            specs.append({
                "source_id": s.get("source_id"),
                "name": s.get("name"),
                "layer": s.get("layer"),
                "pattern": s.get("pattern"),
                "has_fetcher": (SOURCES_DIR / f"{s.get('source_id')}.py").exists(),
            })
        except Exception:
            log.exception("Spec invalide : %s", p.name)
    return specs


def _build_prompt(spec: dict, feedback: str | None = None) -> str:
    # Choix de la référence selon spec.format
    source_format = (spec.get("format") or "rest_json").lower().strip()
    ref_path = REFERENCE_BY_FORMAT.get(source_format, REFERENCE_FETCHER)
    ref_code = ref_path.read_text(encoding="utf-8") if ref_path.exists() else ""
    format_hint = FORMAT_HINTS.get(source_format, "")
    fb_block = f"\n\n## FEEDBACK ITÉRATION PRÉCÉDENTE (CORRIGE CES PROBLÈMES)\n{feedback}\n" if feedback else ""
    return f"""Tu es lead-data-engineer DEMOEMA. Ta mission : GÉNÉRER le code Python complet d'un fetcher pour une source data publique, à partir de la spec YAML fournie.

## FORMAT DE LA SOURCE : `{source_format}`
{format_hint}
{fb_block}

## SPEC YAML de la source à implémenter
```yaml
{yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)}
```

## CODE DE RÉFÉRENCE ({ref_path.name}, pattern {source_format}) — copier la structure, adapter à la spec
```python
{ref_code}
```

## EXIGENCES NON NÉGOCIABLES
1. **Une seule fonction async exposée** : `async def fetch_{spec['source_id']}_delta() -> dict` retournant `{{source, rows, fetched, ...}}`
2. **Pas d'imports hors whitelist** : httpx, psycopg, datetime, json, logging, re, lxml, feedparser, yaml, config (from)
3. **Pas de subprocess, os.system, eval, exec, open() en écriture**
4. **Conversion str() obligatoire** avant slicing (cf. bug bodacc int: `_s = lambda v: str(v) if v is not None else ''`)
5. **ON CONFLICT conforme à la spec** (voir champ `conflict_strategy`)
6. **Backfill first-run** : si bronze.TABLE empty → élargir la fenêtre (cf. spec `backfill_days_first_run`)
7. **Retry simple** : httpx timeout 30s, pas de retry complexe Y1 (laisser le scheduler gérer)
8. **Retourner `{{source: '...', rows: N, fetched: N, ...}}`** en sortie
9. **Commentaire docstring** en FR expliquant endpoint + licence + RGPD notes
10. **Pas de scoring / parsing métier** ici — JUST fetch + parse JSON + insert bronze

## AUTH SELON spec.auth
- `none` : pas d'auth
- `oauth2_client_credentials` : POST au token_url avec client_id/client_secret depuis env, cache token 50min
- `api_key` : header `Authorization: Bearer ${{{{spec.auth_env_vars.api_key}}}}` from env

## SORTIE ATTENDUE
**UNIQUEMENT du code Python** entre balises ```python ... ``` . **Aucun texte avant ou après**. Pas d'explication, pas de markdown, juste le fichier .py complet prêt à être écrit.
"""


def _extract_code_from_response(response_text: str) -> str | None:
    """Extrait le code Python des balises markdown."""
    m = re.search(r"```python\s*\n(.*?)\n```", response_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fallback : si tout est du code
    stripped = response_text.strip()
    if stripped.startswith(("from ", "import ", '"""', "'''")):
        return stripped
    return None


def _validate_code(code: str) -> tuple[bool, str]:
    """Parse Python AST + vérifie whitelist imports + pas d'appels dangereux."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"

    # Imports whitelist
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    return False, f"Import interdit : {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    return False, f"Import from interdit : {node.module}"
        # Interdits : exec, eval, open() write, subprocess
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval", "compile", "__import__"}:
                return False, f"Appel interdit : {node.func.id}"
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen", "Popen"}:
                return False, f"Appel subprocess interdit"

    return True, "OK"


TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATE_BY_FORMAT = {
    "rest_json": "rest_json_ods.py.tmpl",
    "csv":       "csv_dump.py.tmpl",
    "csv_gz":    "csv_dump.py.tmpl",   # gunzip auto-detect
    "zip":       "zip_csv.py.tmpl",
}

# Vars avec valeurs par défaut : si la spec YAML ne les fournit pas, on utilise ces defaults
TEMPLATE_DEFAULTS = {
    "title":              "",       # repris du spec.name
    "license":            "Etalab 2.0",
    "page_size":          100,
    "max_pages":          100,
    "backfill_days":      3650,
    "incremental_hours":  48,
    "batch_size":         1000,
    "max_rows":           500000,
    "max_members":        10,
    "key_field":          "record_id",
}


async def _discover_table_schema(source_id: str) -> tuple[str, str] | None:
    """Introspecte la DB pour trouver la vraie table bronze + sa clé primaire.
    Retourne (schema.table, key_column) ou None. Cherche par match de source_id."""
    if not settings.database_url:
        return None
    try:
        import psycopg as _pg
        async with await _pg.AsyncConnection.connect(settings.database_url) as conn:
            async with conn.cursor() as cur:
                # Stratégie : trouver une table bronze.* dont le nom contient source_id
                await cur.execute(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'bronze'
                      AND (tablename = %s OR tablename LIKE %s OR tablename LIKE %s)
                    ORDER BY LENGTH(tablename) ASC
                    LIMIT 1
                    """,
                    (f"{source_id}_raw", f"{source_id}\\_%\\_raw", f"{source_id}%raw"),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                tbl = row[0]

                # PK column : préférer une colonne VARCHAR qui finit par _id (ex: annonce_id, aide_id)
                await cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'bronze' AND table_name = %s
                      AND is_nullable = 'NO'
                      AND data_type IN ('character varying', 'character', 'text')
                      AND column_name NOT IN ('payload','ingested_at')
                    ORDER BY
                      CASE WHEN column_name LIKE '%%_id' THEN 0 ELSE 1 END,
                      ordinal_position
                    LIMIT 1
                    """,
                    (tbl,),
                )
                col_row = await cur.fetchone()
                key_field = col_row[0] if col_row else "id"

                return (f"bronze.{tbl}", key_field)
    except Exception as e:
        log.warning("discover_table_schema crashed for %s: %s", source_id, e)
        return None


async def _render_template(spec: dict) -> str | None:
    """Essaie de rendre un template correspondant au format de la spec.
    Async car on fait de l'introspection DB pour les variables table + key_field.
    Retourne le code Python rendu, ou None si format non supporté / vars manquantes."""
    fmt = (spec.get("format") or "").lower().strip()
    tmpl_name = TEMPLATE_BY_FORMAT.get(fmt)
    if not tmpl_name:
        return None
    tmpl_path = TEMPLATES_DIR / tmpl_name
    if not tmpl_path.exists():
        return None

    endpoint = spec.get("endpoint", "")
    if not endpoint:
        return None

    source_id = spec.get("source_id", "")

    # Variables pour substitution
    vars = dict(TEMPLATE_DEFAULTS)
    vars.update({
        "source_id": source_id,
        "endpoint": endpoint,
        "table": f"bronze.{source_id}_raw",  # fallback
        "title": spec.get("name") or source_id,
        "license": spec.get("licence") or spec.get("license") or "Etalab 2.0",
    })

    # DB introspection : override table + key_field avec les vraies valeurs du schéma
    schema_info = await _discover_table_schema(source_id)
    if schema_info:
        vars["table"], vars["key_field"] = schema_info
        log.info("[codegen schema] %s table=%s key=%s", source_id, vars["table"], vars["key_field"])

    # spec.table override explicite si présent
    if spec.get("table"):
        vars["table"] = spec["table"]
    # spec.template_vars écrase (dernier mot)
    for k, v in (spec.get("template_vars") or {}).items():
        vars[k] = v

    try:
        tmpl = tmpl_path.read_text(encoding="utf-8")
        rendered = tmpl.format(**vars)
        # Sanity check : doit contenir fetch_{source_id}_delta
        if f"fetch_{source_id}_delta" not in rendered:
            log.warning("template %s missing fetch_%s_delta", tmpl_name, source_id)
            return None
        return rendered
    except KeyError as e:
        log.warning("template %s needs var %s (not in spec + defaults)", tmpl_name, e)
        return None
    except Exception as e:
        log.exception("template render error: %s", e)
        return None


async def generate_fetcher(source_id: str, feedback: str | None = None) -> dict:
    """Pipeline génération : spec → [template render OU LLM prompt] → validate → write → register.

    Priorité au template (déterministe, rapide, gratuit). Fallback LLM si template indispo
    ou si feedback fourni (retry d'itération nécessite souvent du nuancé).
    """
    spec = load_spec(source_id)
    if not spec:
        return {"error": f"Spec introuvable : specs/{source_id}.yaml"}

    # ──────────── AUTO-DETECT FORMAT (sécurité) ────────────
    # Si spec.format absent, on détecte automatiquement depuis l'URL + HEAD + magic bytes.
    # Évite de dépendre du LLM hunter pour mettre `format:` proprement.
    if not spec.get("format") and spec.get("endpoint"):
        try:
            from tools.format_detect import detect_format
            detected = await detect_format(spec["endpoint"])
            fmt = detected.get("format")
            if fmt and fmt != "unknown":
                spec["format"] = fmt
                log.info("[codegen auto-detect] %s format=%s signal=%s",
                         source_id, fmt, detected.get("signal"))
                # Persister dans le YAML (pour run_fetcher ultérieur)
                try:
                    import re as _re
                    spec_path = SPECS_DIR / f"{source_id}.yaml"
                    src = spec_path.read_text(encoding="utf-8")
                    if _re.search(r"(?m)^format:\s*.*$", src):
                        src = _re.sub(r"(?m)^format:\s*.*$", f"format: {fmt}", src, count=1)
                    else:
                        src = src.rstrip() + f"\nformat: {fmt}\n"
                    spec_path.write_text(src, encoding="utf-8")
                except Exception:
                    log.exception("auto-detect: persist format failed")
        except Exception as e:
            log.warning("auto-detect format failed for %s: %s", source_id, e)

    # ──────────── TEMPLATE-FIRST PATH ────────────
    # Si on a un format reconnu + pas de feedback → render template déterministe, pas de LLM
    if not feedback:
        rendered = await _render_template(spec)
        if rendered is not None:
            ok, msg = _validate_code(rendered)
            if ok:
                target = SOURCES_DIR / f"{source_id}.py"
                target.write_text(rendered, encoding="utf-8")
                result = {"source_id": source_id, "file": str(target.name),
                          "bytes": len(rendered), "mode": "template",
                          "template": TEMPLATE_BY_FORMAT.get((spec.get("format") or "").lower())}
                # Hot-reload via import
                try:
                    import importlib
                    from ingestion import engine
                    importlib.invalidate_caches()
                    module_path = f"ingestion.sources.{source_id}"
                    if module_path in list(importlib.sys.modules):
                        importlib.reload(importlib.sys.modules[module_path])
                    else:
                        importlib.import_module(module_path)
                    mod = importlib.import_module(module_path)
                    fetcher = getattr(mod, f"fetch_{source_id}_delta", None) or getattr(mod, f"fetch_{source_id}_full", None)
                    if fetcher:
                        trigger = _build_trigger(spec.get("refresh_trigger", "interval_hours=24"))
                        engine.SOURCES[source_id] = {
                            "fetcher": fetcher, "trigger": trigger,
                            "sla_minutes": spec.get("sla_minutes", 1440),
                            "description": spec.get("name", source_id),
                        }
                        result["registered"] = True
                    log.info("[codegen template] %s rendered via %s (%d bytes)",
                             source_id, result["template"], len(rendered))
                except Exception as e:
                    result["warn_register"] = str(e)
                return result
            else:
                log.info("[codegen template] %s rendered but INVALID: %s → fallback LLM", source_id, msg)
        # sinon fallback LLM ci-dessous

    # ──────────── LLM PATH (fallback) ────────────
    agent = get_agent("lead-data-engineer")
    if not agent:
        return {"error": "Agent lead-data-engineer non chargé"}

    prompt = _build_prompt(spec, feedback=feedback)

    # Appel Ollama Cloud (stream=False pour avoir la réponse complète)
    client = OllamaClient()
    response = None
    try:
        try:
            response = await client.chat(
                model=agent.model,
                messages=[
                    {"role": "system", "content": agent.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                options=agent.to_ollama_options(),
                stream=False,
            )
        except Exception as e:
            log.warning("Ollama chat failed for %s: %s", source_id, e)
            return {"error": f"LLM call failed: {type(e).__name__}: {e}",
                    "source_id": source_id}
    finally:
        await client.close()

    content = response.get("message", {}).get("content", "") if isinstance(response, dict) else ""
    if not content:
        return {"error": "LLM response vide", "raw": str(response)[:500]}

    code = _extract_code_from_response(content)
    if not code:
        return {"error": "Pas de code Python extractible", "raw": content[:1000]}

    ok, msg = _validate_code(code)
    if not ok:
        return {"error": f"Validation failed: {msg}", "code_preview": code[:500]}

    # Write
    target = SOURCES_DIR / f"{source_id}.py"
    target.write_text(code, encoding="utf-8")

    # Hot reload : import + register dans engine
    result = {"source_id": source_id, "file": str(target.name), "bytes": len(code)}
    try:
        from ingestion import engine
        importlib.invalidate_caches()
        module_path = f"ingestion.sources.{source_id}"
        if module_path in list(importlib.sys.modules):
            importlib.reload(importlib.sys.modules[module_path])
        else:
            importlib.import_module(module_path)
        mod = importlib.import_module(module_path)
        fetcher_name = f"fetch_{source_id}_delta"
        fetcher = getattr(mod, fetcher_name, None) or getattr(mod, f"fetch_{source_id}_full", None)
        if fetcher is None:
            return {**result, "error": f"Fonction fetch_{source_id}_delta/full non trouvée dans le module"}

        trigger_str = spec.get("refresh_trigger", "interval_hours=24")
        trigger = _build_trigger(trigger_str)
        engine.SOURCES[source_id] = {
            "fetcher": fetcher,
            "trigger": trigger,
            "sla_minutes": spec.get("sla_minutes", 1440),
            "description": spec.get("name", source_id),
        }
        if engine.scheduler:
            engine.scheduler.add_job(
                engine.run_source,
                trigger=trigger,
                args=[source_id],
                id=f"ingest_{source_id}",
                name=f"Ingestion {source_id}",
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )
        result["registered"] = True
        result["trigger"] = str(trigger)
    except Exception as e:
        result["error_register"] = str(e)

    return result


async def discover_and_generate(source_id: str, max_iterations: int = 3) -> dict:
    """Mode C : generate + test_endpoint + retry avec feedback (max 3 iter).

    Critère de SUCCESS durci (2026-04-20) : un fetcher n'est considéré valide QUE s'il
    remonte effectivement des données (rows > 0) OU si la source est légitimement vide
    (upstream confirme 0). Un stub `manual_research_needed` est désormais classé en
    `status='degraded_no_data'` et NON success — le Maintainer pourra re-tenter.
    """
    from tools.http import test_endpoint as test_ep_func
    spec = load_spec(source_id)
    if not spec:
        return {"error": f"Spec introuvable : {source_id}.yaml"}

    history: list[dict] = []
    current_feedback: str | None = None

    for iteration in range(1, max_iterations + 1):
        log.info("[discover] %s iter %d/%d", source_id, iteration, max_iterations)

        endpoint_test = await test_ep_func(spec.get("endpoint", ""))
        log.info("[discover] %s endpoint test : works=%s status=%s",
                 source_id, endpoint_test.get("works"), endpoint_test.get("status"))

        if not endpoint_test.get("works"):
            ep_fb = (f"⚠️ L'endpoint spec {spec.get('endpoint')} retourne status "
                     f"{endpoint_test.get('status')} ({endpoint_test.get('error', 'no content')}). "
                     f"RECHERCHE une URL alternative réelle : data.gouv.fr, opendatasoft, api.gouv.fr. "
                     f"PAS DE STUB 'manual_research_needed' : il faut du code qui fetch réellement. "
                     f"Si aucune URL publique fonctionnelle, retourne un fetcher qui raise "
                     f"NotImplementedError('aucune source publique trouvée') — il sera logué proprement.")
            current_feedback = ((current_feedback or "") + "\n" + ep_fb) if current_feedback else ep_fb

        gen_result = await generate_fetcher(source_id, feedback=current_feedback)
        history.append({"iter": iteration, "endpoint_test": endpoint_test, "gen": gen_result})

        if "error" in gen_result and "file" not in gen_result:
            current_feedback = f"Génération précédente a échoué : {gen_result.get('error')}. Produis du code valide."
            continue

        try:
            mod_name = f"ingestion.sources.{source_id}"
            if mod_name in importlib.sys.modules:
                importlib.reload(importlib.sys.modules[mod_name])
            else:
                importlib.import_module(mod_name)
            mod = importlib.import_module(mod_name)
            fetcher = getattr(mod, f"fetch_{source_id}_delta", None) or getattr(mod, f"fetch_{source_id}_full", None)
            if fetcher:
                dry = await fetcher()
                history[-1]["dry_run"] = dry
                rows = dry.get("rows", 0) if isinstance(dry, dict) else 0
                skipped = (dry or {}).get("skipped", "") or (dry or {}).get("skipped_reason", "")

                # ─── Succès réel uniquement si rows > 0 ───
                if rows > 0:
                    log.info("[discover] %s SUCCESS iter %d rows=%d", source_id, iteration, rows)
                    return {"source_id": source_id, "status": "success",
                            "iterations": iteration, "rows": rows, "history": history}

                # ─── Stubs 'manual_research_needed' explicitement refusés ───
                if skipped == "manual_research_needed":
                    log.warning("[discover] %s iter %d : stub manual_research_needed refusé comme success",
                                source_id, iteration)
                    current_feedback = (
                        "❌ Ton code précédent a retourné skipped='manual_research_needed' avec rows=0. "
                        "C'est REFUSÉ. Tu dois trouver une source de données réelle publique "
                        "(data.gouv.fr, opendatasoft, dumps CSV, RSS, HTML parseable). "
                        "Explore plusieurs URL alternatives. Un fetcher qui ne fetche pas n'est pas acceptable."
                    )
                    continue

                current_feedback = (f"Fetcher généré mais retourne 0 rows (dry_run={dry}). "
                                   f"Causes possibles : endpoint filtre trop restrictif, parsing format incorrect, "
                                   f"auth requise. Examine + corrige. Objectif: rows > 0.")
        except Exception as e:
            current_feedback = f"Erreur à l'exécution : {type(e).__name__}: {e}. Fix."
            history[-1]["exec_error"] = str(e)

    # ─── Epuisement des iter sans succès réel : 'degraded_no_data' au lieu de success ───
    log.warning("[discover] %s DEGRADED_NO_DATA après %d iter", source_id, max_iterations)
    return {"source_id": source_id, "status": "degraded_no_data",
            "iterations": max_iterations, "history": history,
            "note": "Aucune iter n'a remonté de rows. À examiner manuellement ou à rééssayer après backoff."}


def _build_trigger(s: str):
    s = s.strip()
    if s.startswith("interval_hours="):
        return IntervalTrigger(hours=int(s.split("=")[1]))
    if s.startswith("interval_minutes="):
        return IntervalTrigger(minutes=int(s.split("=")[1]))
    if s.startswith("cron:"):
        # ex: "cron:hour=3 minute=30 tz=Europe/Paris"
        parts = dict(p.split("=") for p in s[5:].split())
        tz = parts.pop("tz", "Europe/Paris")
        return CronTrigger(timezone=tz, **{k: int(v) for k, v in parts.items()})
    if s.strip() == "on_demand":
        return IntervalTrigger(days=365)  # effectivement jamais auto
    return IntervalTrigger(hours=24)  # default
