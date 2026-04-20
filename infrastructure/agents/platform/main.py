"""DEMOEMA Agents Platform — FastAPI app.

Routes :
- GET  /healthz                  Santé
- GET  /agents                   Liste des agents disponibles
- GET  /agents/{name}            Détails d'un agent
- POST /agents/{name}/invoke     Invoke avec streaming SSE
- GET  /models                   Modèles Ollama chargés
- POST /models/{name}/pull       Pull un modèle Ollama

Auth : header X-API-Key = settings.platform_api_key (si configuré).
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from config import settings
from loader import AgentSpec, get_agent, list_agents, load_agents
from ollama_client import OllamaClient
from tools import execute_tool, get_tool_schemas
from ingestion.engine import SOURCES, freshness_report, list_jobs, run_source, start_scheduler, stop_scheduler
from ingestion.codegen import discover_and_generate, generate_fetcher, list_specs, load_spec

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("demoema.agents")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_agents()
    app.state.ollama = OllamaClient()
    if settings.database_url:
        try:
            start_scheduler()
            log.info("Ingestion scheduler démarré (%d sources)", len(SOURCES))
        except Exception:
            log.exception("Scheduler start failed (non-fatal)")
    else:
        log.warning("DATABASE_URL vide — ingestion scheduler non démarré")
    log.info("Platform démarrée (%d agents)", len(list_agents()))
    yield
    stop_scheduler()
    await app.state.ollama.close()


app = FastAPI(title="DEMOEMA Agents Platform", version="0.1.0", lifespan=lifespan)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = settings.platform_api_key
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid API key")


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "agents_loaded": len(list_agents())}


@app.get("/agents", dependencies=[Depends(require_api_key)])
async def agents_list() -> list[dict]:
    return [
        {"name": a.name, "model": a.model, "description": a.description, "tools": a.tools}
        for a in list_agents()
    ]


@app.get("/agents/{name}", dependencies=[Depends(require_api_key)])
async def agent_detail(name: str) -> dict:
    spec = get_agent(name)
    if not spec:
        raise HTTPException(404, f"agent inconnu : {name}")
    return {
        "name": spec.name,
        "model": spec.model,
        "description": spec.description,
        "temperature": spec.temperature,
        "num_ctx": spec.num_ctx,
        "tools": spec.tools,
        "system_prompt_preview": spec.system_prompt[:500],
    }


@app.get("/models", dependencies=[Depends(require_api_key)])
async def models_list(request: Request) -> dict:
    ollama: OllamaClient = request.app.state.ollama
    models = await ollama.list_models()
    return {"models": [{"name": m.get("model"), "size": m.get("size")} for m in models]}


@app.post("/models/{name:path}/pull", dependencies=[Depends(require_api_key)])
async def models_pull(name: str, request: Request) -> EventSourceResponse:
    ollama: OllamaClient = request.app.state.ollama

    async def stream():
        async for chunk in ollama.pull_model(name):
            yield {"event": "progress", "data": json.dumps(chunk)}
        yield {"event": "done", "data": json.dumps({"model": name})}

    return EventSourceResponse(stream())


@app.post("/agents/{name}/invoke", dependencies=[Depends(require_api_key)])
async def agent_invoke(name: str, body: dict, request: Request) -> EventSourceResponse:
    """Invoque un agent avec streaming SSE.

    Body : {"prompt": "...", "history": [{role, content}]}
    Stream : event=token (delta), event=tool_call, event=done
    """
    spec = get_agent(name)
    if not spec:
        raise HTTPException(404, f"agent inconnu : {name}")

    prompt = body.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(422, "prompt requis")
    history: list[dict] = body.get("history", [])

    messages = [{"role": "system", "content": spec.system_prompt}, *history, {"role": "user", "content": prompt}]
    tools_schemas = get_tool_schemas(spec.tools) if spec.tools else None

    ollama: OllamaClient = request.app.state.ollama

    async def stream():
        yield {"event": "start", "data": json.dumps({"agent": spec.name, "model": spec.model})}

        # Boucle tool-calling : max 5 tours pour éviter runaway
        for turn in range(5):
            response = await ollama.chat(
                model=spec.model,
                messages=messages,
                tools=tools_schemas,
                options=spec.to_ollama_options(),
                stream=False,  # tool-calling non streamable sur Ollama actuellement
            )
            msg = response.get("message", {})
            messages.append(msg)

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                # Réponse finale : stream token par token
                content = msg.get("content", "")
                for chunk in _chunk_text(content, 40):
                    yield {"event": "token", "data": json.dumps({"delta": chunk})}
                yield {"event": "done", "data": json.dumps({"turn": turn, "stop_reason": response.get("done_reason", "stop")})}
                return

            # Tool-calling : exécuter chaque outil + re-injecter
            for tc in tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                fn_args = fn.get("arguments", {})
                yield {"event": "tool_call", "data": json.dumps({"name": fn_name, "args": fn_args})}
                tool_result = await execute_tool(fn_name, fn_args)
                yield {"event": "tool_result", "data": json.dumps({"name": fn_name, "result_preview": str(tool_result)[:500]})}
                messages.append({"role": "tool", "content": json.dumps(tool_result)})

        yield {"event": "error", "data": json.dumps({"error": "max tool-call turns atteint (5)"})}

    return EventSourceResponse(stream())


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


@app.post("/agents/reload", dependencies=[Depends(require_api_key)])
async def agents_reload() -> dict:
    agents = load_agents()
    return {"reloaded": len(agents)}


@app.get("/ingestion/sources", dependencies=[Depends(require_api_key)])
async def ingestion_sources() -> dict:
    return {
        "sources": [
            {"id": sid, "description": cfg["description"], "sla_minutes": cfg["sla_minutes"], "trigger": str(cfg["trigger"])}
            for sid, cfg in SOURCES.items()
        ],
        "jobs": list_jobs(),
    }


@app.post("/ingestion/run/{source_id}", dependencies=[Depends(require_api_key)])
async def ingestion_run(source_id: str) -> dict:
    """Trigger manuel d'une source."""
    if source_id not in SOURCES:
        raise HTTPException(404, f"source inconnue : {source_id}. Valides : {list(SOURCES.keys())}")
    return await run_source(source_id)


@app.get("/ingestion/freshness", dependencies=[Depends(require_api_key)])
async def ingestion_freshness() -> dict:
    return {"sources": await freshness_report()}


@app.get("/ingestion/specs", dependencies=[Depends(require_api_key)])
async def ingestion_specs_list() -> dict:
    """Liste des specs YAML déclarées + statut has_fetcher."""
    return {"specs": list_specs()}


@app.get("/ingestion/specs/{source_id}", dependencies=[Depends(require_api_key)])
async def ingestion_spec_detail(source_id: str) -> dict:
    spec = load_spec(source_id)
    if not spec:
        raise HTTPException(404, f"Spec introuvable : {source_id}.yaml")
    return spec


@app.post("/ingestion/generate/{source_id}", dependencies=[Depends(require_api_key)])
async def ingestion_generate_fetcher(source_id: str) -> dict:
    """Codegen one-shot."""
    result = await generate_fetcher(source_id)
    if "error" in result and "file" not in result:
        raise HTTPException(422, result["error"])
    return result


@app.post("/ingestion/discover/{source_id}", dependencies=[Depends(require_api_key)])
async def ingestion_discover(source_id: str, iterations: int = 3) -> dict:
    """Mode C : generate + test_endpoint + retry avec feedback (max N iter)."""
    return await discover_and_generate(source_id, max_iterations=iterations)


# ─── Agent openclaw : browser-driving (DeepSeek + Playwright) ────────────────

@app.post("/agents/openclaw/run", dependencies=[Depends(require_api_key)])
async def openclaw_run(payload: dict) -> dict:
    """Lance l'agent openclaw sur une tâche.

    Body JSON :
      { "task": "...", "source_id": "insee_sirene_v3" (optional), "max_steps": 30 }
    Retour : transcript, screenshots paths, credentials si extraits.
    """
    task = (payload or {}).get("task")
    if not task:
        raise HTTPException(400, "field 'task' required")
    source_id = (payload or {}).get("source_id")
    max_steps = int((payload or {}).get("max_steps") or 30)
    if max_steps < 1 or max_steps > 60:
        raise HTTPException(400, "max_steps must be in [1, 60]")
    try:
        from openclaw import run_openclaw
    except ImportError as e:
        raise HTTPException(500, f"openclaw indisponible: {e}")
    return await run_openclaw(task, source_id=source_id, max_steps=max_steps)


# ─── Agent source-hunter : trouve URL d'API via data.gouv.fr ────────────────

@app.post("/agents/source-hunter/hunt/{source_id}", dependencies=[Depends(require_api_key)])
async def source_hunter_run(source_id: str, max_steps: int = 15) -> dict:
    """Lance l'agent source-hunter pour une source.

    Cherche dans data.gouv.fr la bonne URL, patche le spec, teste.
    """
    if max_steps < 1 or max_steps > 30:
        raise HTTPException(400, "max_steps must be in [1, 30]")
    try:
        from source_hunter import hunt_source
    except ImportError as e:
        raise HTTPException(500, f"source-hunter indisponible: {e}")
    return await hunt_source(source_id, max_steps=max_steps)
