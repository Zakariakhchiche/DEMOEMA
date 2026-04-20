"""Agent source-hunter — trouve la bonne URL d'un dataset public via data.gouv.fr.

Pour un source_id donné :
 1. Lit le spec YAML (read_spec)
 2. Cherche le dataset dans data.gouv.fr (dg_search)
 3. Explore les résultats (dg_get) pour trouver l'URL d'API/dump qui retourne du JSON/CSV
 4. Teste l'URL candidate (dg_probe)
 5. Patch le spec (patch_endpoint) + exécute (run_fetcher)
 6. Rapporte success/failed/partial

Utilise DeepSeek comme brain, pas de navigateur nécessaire ici.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

import psycopg

from config import settings
from deepseek_client import DeepSeekClient
from tools import data_gouv, specs_rw, format_detect

log = logging.getLogger("demoema.source_hunter")

DEFAULT_MAX_STEPS = 15
PROMPT_PATH = Path(os.environ.get("PROMPTS_DIR", "/app/prompts")) / "source_hunter.md"


def _load_system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "Tu es source-hunter. Pour un source_id, trouve l'URL correcte d'un dataset "
        "public français dans data.gouv.fr, patch le spec YAML et teste le fetcher. "
        "Tools : read_spec, dg_search, dg_get, dg_probe, patch_endpoint, run_fetcher."
    )


async def hunt_source(source_id: str, max_steps: int = DEFAULT_MAX_STEPS) -> dict:
    client = DeepSeekClient()
    task_id = str(uuid.uuid4())
    log.info("[hunter %s] source=%s", task_id, source_id)

    user_task = (
        f"Trouve une URL fonctionnelle pour la source `{source_id}` (tout format : "
        f"REST JSON, CSV dump, ZIP, JSONL, Parquet, GeoJSON, XML). Procédure :\n\n"
        f"1. `read_spec({source_id!r})` — nom, description, endpoint actuel.\n"
        f"2. `dg_search` avec mots-clés pertinents (du champ name/description).\n"
        f"3. `dg_get(slug)` sur le meilleur candidat → liste des resources avec format+url+filesize.\n"
        f"4. Pour CHAQUE resource candidate (priorité : API > CSV > ZIP > Parquet) :\n"
        f"   → `detect_format(url, metadata_format=<format de resource>)` "
        f"→ le retour donne {{format, signal, size_bytes}}.\n"
        f"   → `dg_probe(url)` pour vérifier qu'elle est accessible.\n"
        f"5. Choisis la MEILLEURE resource (priorité : plus petite taille, plus récente).\n"
        f"6. `patch_endpoint({source_id!r}, new_url=..., source_format=<format_détecté>)`. "
        f"Si format=rest_json OpenDataSoft, mets aussi count_endpoint=même URL.\n"
        f"7. `regenerate_fetcher({source_id!r})` — OBLIGATOIRE, régénère le .py avec le bon "
        f"template selon format_détecté (CSV stream / ZIP-CSV / REST JSON / etc.).\n"
        f"8. `run_fetcher({source_id!r})` — valide. Si rows=0, analyse puis retry étape 2 "
        f"avec d'autres keywords OU accepte un autre format.\n\n"
        f"Réponds TOUJOURS (même en cas d'échec) avec JSON strict :\n"
        f"```json\n"
        f"{{\"status\": \"success|partial|failed\", \"source_id\": \"{source_id}\", "
        f"\"format\": \"csv|rest_json|...\", \"new_url\": \"...\", "
        f"\"rows_loaded\": N, \"reasoning\": \"1 phrase\"}}\n"
        f"```"
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _load_system_prompt()},
        {"role": "user", "content": user_task},
    ]

    all_tools = (data_gouv.DATAGOUV_TOOLS_SCHEMA
                 + specs_rw.SPECSRW_TOOLS_SCHEMA
                 + format_detect.DETECT_TOOLS_SCHEMA)
    all_dispatch = {**data_gouv.DATAGOUV_DISPATCH,
                    **specs_rw.SPECSRW_DISPATCH,
                    **format_detect.DETECT_DISPATCH}

    transcript = []
    t0 = time.time()

    for step in range(1, max_steps + 1):
        try:
            resp = await client.chat(messages=messages, tools=all_tools)
        except Exception as e:
            transcript.append({"step": step, "error": f"deepseek: {e}"})
            break

        msg = resp["message"]
        tool_calls = msg.get("tool_calls") or []
        content = msg.get("content")
        finish = resp.get("finish_reason")

        transcript.append({
            "step": step,
            "finish": finish,
            "content_preview": (content or "")[:300],
            "tool_calls": [tc["function"]["name"] for tc in tool_calls],
            "tokens": resp.get("usage", {}).get("total_tokens"),
        })

        assistant = {"role": "assistant"}
        if content:
            assistant["content"] = content
        if tool_calls:
            assistant["tool_calls"] = tool_calls
        messages.append(assistant)

        if not tool_calls:
            break

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            fn = all_dispatch.get(fn_name)
            if fn is None:
                observation = f"ERR unknown tool: {fn_name}"
            else:
                try:
                    observation = await fn(**args)
                except Exception as e:
                    observation = f"ERR {fn_name}: {type(e).__name__}: {e}"
            # Normaliser en str (certains tools retournent dict)
            if not isinstance(observation, str):
                try:
                    observation = json.dumps(observation, ensure_ascii=False, default=str)
                except Exception:
                    observation = str(observation)
            if len(observation) > 4000:
                observation = observation[:4000] + "...[truncated]"
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": observation,
            })
            transcript[-1].setdefault("observations", []).append({
                "tool": fn_name, "preview": observation[:200],
            })

    duration_ms = int((time.time() - t0) * 1000)
    final_msg = messages[-1].get("content") if messages[-1].get("role") == "assistant" else None

    # Parse JSON final
    parsed = None
    if final_msg:
        try:
            import re as _re
            m = _re.search(r"```json\s*(\{.*?\})\s*```", final_msg, flags=_re.DOTALL)
            blob = m.group(1) if m else _re.search(r"(\{(?:[^{}]|\{[^{}]*\})*\})", final_msg, flags=_re.DOTALL)
            blob = blob.group(1) if hasattr(blob, "group") else blob
            if blob:
                parsed = json.loads(blob)
        except Exception:
            parsed = None

    # Audit
    if settings.database_url:
        try:
            async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO audit.agent_actions
                          (agent_role, task_id, source_id, action, status, duration_ms,
                           payload_out, llm_model)
                        VALUES ('source_hunter', %s, %s, 'hunt_source', %s, %s, %s, 'deepseek-chat')
                        """,
                        (task_id, source_id,
                         (parsed or {}).get("status", "unknown"),
                         duration_ms,
                         psycopg.types.json.Jsonb({"steps": len(transcript),
                                                   "parsed": parsed,
                                                   "final_message": final_msg})),
                    )
        except Exception:
            log.exception("hunter audit failed")

    return {
        "task_id": task_id,
        "source_id": source_id,
        "steps": len(transcript),
        "final_message": final_msg,
        "parsed_final": parsed,
        "duration_ms": duration_ms,
        "transcript": transcript,
    }
