"""Agent openclaw — browser-driving agent via DeepSeek.

Boucle tool-calling classique :
  1. User task → system + user message
  2. Appel DeepSeek
  3. Si tool_calls → exécuter chaque tool (browser.*), append observation
  4. Si finish_reason='stop' + content finale → retourner transcript
  5. Cap max_steps pour éviter boucle infinie

Persistance : screenshots dans /tmp/openclaw_screenshots/ (lisibles hors container).
Transcripts : loggés dans audit.agent_actions (agent_role='openclaw').
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
from tools import browser
from tools import mailbox
import tools.creds as creds_store

log = logging.getLogger("demoema.openclaw")

DEFAULT_MAX_STEPS = 30
PROMPT_PATH = Path(os.environ.get("PROMPTS_DIR", "/app/prompts")) / "openclaw.md"


def _load_system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "Tu es openclaw, un agent qui pilote un navigateur pour créer des comptes "
        "sur des sites d'APIs publiques (INSEE, INPI, France Travail, etc.) et "
        "récupérer les credentials. Utilise les outils browser.* disponibles. "
        "Travaille étape par étape. Quand tu as fini, réponds avec un JSON final "
        "contenant les credentials ou un message clair sur ce qui bloque."
    )


async def run_openclaw(task: str, source_id: str | None = None,
                      max_steps: int = DEFAULT_MAX_STEPS) -> dict:
    """Lance l'agent sur une tâche. Retourne un résumé {final_message, steps, tool_calls}."""
    client = DeepSeekClient()  # lève si DEEPSEEK_API_KEY manquante
    task_id = str(uuid.uuid4())
    log.info("[openclaw %s] task : %s", task_id, task[:200])

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _load_system_prompt()},
        {"role": "user", "content": task},
    ]
    transcript: list[dict[str, Any]] = []
    t0 = time.time()

    # Tool registry fusionnée : browser + mailbox
    all_tools = browser.TOOLS_SCHEMA + mailbox.MAILBOX_TOOLS_SCHEMA
    all_dispatch = {**browser.TOOLS_DISPATCH, **mailbox.MAILBOX_DISPATCH}

    for step in range(1, max_steps + 1):
        try:
            resp = await client.chat(messages=messages, tools=all_tools)
        except Exception as e:
            log.exception("[openclaw %s] DeepSeek error step %d", task_id, step)
            transcript.append({"step": step, "error": f"deepseek: {e}"})
            break

        msg = resp["message"]
        tool_calls = msg.get("tool_calls") or []
        content = msg.get("content")
        finish = resp.get("finish_reason")

        transcript.append({
            "step": step,
            "finish_reason": finish,
            "content": content[:500] if isinstance(content, str) else None,
            "tool_calls": [
                {"name": tc["function"]["name"],
                 "args_preview": str(tc["function"].get("arguments", ""))[:200]}
                for tc in tool_calls
            ],
            "tokens": resp.get("usage", {}),
        })

        # Assistant message (doit être ajouté au contexte pour que DeepSeek voie ses propres calls)
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if content:
            assistant_msg["content"] = content
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        # Pas de tool_calls → le modèle a fini
        if not tool_calls:
            log.info("[openclaw %s] done step %d, finish=%s", task_id, step, finish)
            break

        # Exécuter chaque tool_call séquentiellement
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            # Dispatch browser ou mailbox selon l'identité de la tool
            fn = all_dispatch.get(fn_name)
            if fn is None:
                observation = f"ERR unknown tool: {fn_name}"
            else:
                try:
                    observation = await fn(**args)
                except TypeError as e:
                    observation = f"ERR bad args for {fn_name}: {e}"
                except Exception as e:
                    log.exception("tool %s crashed", fn_name)
                    observation = f"ERR {fn_name}: {type(e).__name__}: {e}"
            # Persiste les inboxes mail.tm créés dans le credentials store
            if fn_name == "create_inbox" and isinstance(observation, str) and observation.startswith("OK inbox"):
                try:
                    import re as _re
                    m = _re.search(r"alias=['\"]?(\S+?)['\"]?\s+address=['\"]?(\S+?)['\"]?\s+password=['\"]?(\S+?)['\"]?$",
                                   observation.strip())
                    if m:
                        creds_store.record_mailtm_inbox(m.group(1), m.group(2), m.group(3))
                except Exception:
                    log.exception("failed to persist mailtm creds")
            if len(observation) > 4000:
                observation = observation[:4000] + "...[truncated]"
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": observation,
            })
            transcript[-1].setdefault("observations", []).append({
                "tool": fn_name, "preview": observation[:300],
            })

    duration_ms = int((time.time() - t0) * 1000)

    # Toujours fermer le navigateur après un run (pas de session persistante cross-run)
    try:
        await browser.close_browser()
    except Exception:
        pass

    final_msg = messages[-1].get("content") if messages[-1].get("role") == "assistant" else None

    # Essayer d'extraire un JSON structuré du final_message et le persister dans le store
    parsed_final: dict[str, Any] | None = None
    if final_msg and source_id:
        try:
            import re as _re
            m = _re.search(r"```json\s*(\{.*?\})\s*```", final_msg, flags=_re.DOTALL)
            blob = m.group(1) if m else None
            if not blob:
                # Essayer le premier {...} standalone
                m2 = _re.search(r"(\{(?:[^{}]|\{[^{}]*\})*\})", final_msg, flags=_re.DOTALL)
                blob = m2.group(1) if m2 else None
            if blob:
                parsed_final = json.loads(blob)
        except Exception:
            parsed_final = None

    if parsed_final and source_id:
        try:
            fields = {
                "status": parsed_final.get("status") or "pending",
                "notes": parsed_final.get("next_action") or parsed_final.get("summary") or "",
            }
            for k in ("email", "password", "signup_email", "signup_password",
                      "client_id", "client_secret", "api_key",
                      "consumer_key", "consumer_secret", "dashboard_url"):
                v = (parsed_final.get("credentials") or {}).get(k) if isinstance(parsed_final.get("credentials"), dict) else None
                if v is None:
                    v = parsed_final.get(k)
                if v:
                    fields[k] = v
            creds_store.set_api_credential(source_id, **fields)
        except Exception:
            log.exception("failed to persist api_credential for %s", source_id)

    result = {
        "task_id": task_id,
        "source_id": source_id,
        "steps": len(transcript),
        "final_message": final_msg,
        "parsed_final": parsed_final,
        "duration_ms": duration_ms,
        "transcript": transcript,
    }

    # Audit log
    if settings.database_url:
        try:
            async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO audit.agent_actions
                          (agent_role, task_id, source_id, action, status, duration_ms,
                           payload_in, payload_out, llm_model)
                        VALUES ('openclaw', %s, %s, 'browser_task', %s, %s, %s, %s, 'deepseek-chat')
                        """,
                        (task_id, source_id,
                         "success" if final_msg else "degraded",
                         duration_ms,
                         psycopg.types.json.Jsonb({"task": task, "max_steps": max_steps}),
                         psycopg.types.json.Jsonb({"steps": len(transcript),
                                                   "final_message": final_msg})),
                    )
        except Exception:
            log.exception("[openclaw %s] audit log failed", task_id)

    return result
