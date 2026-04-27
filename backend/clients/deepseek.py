"""Client Copilot DeepSeek (avec fallback Vercel AI Gateway).

Extrait de main.py:516-622. Lit les clés via os.getenv (sera migré vers
Pydantic Settings dans une PR séparée).
"""
from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx

# Vercel AI Gateway prioritaire (single key, cost tracking, cache, multi-model
# routing) ; DeepSeek direct en fallback.
AI_GATEWAY_API_KEY = os.getenv("AI_GATEWAY_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

_SYSTEM_PROMPT_FULL = (
    "Tu es le Copilot IA d'EdRCF 6.0, plateforme d'origination M&A "
    "pour Edmond de Rothschild Corporate Finance. Reponds en francais, "
    "de maniere concise et professionnelle. Utilise le markdown pour "
    "formater tes reponses (gras, listes, tableaux).\n\n"
    "Tu as acces a deux sources de donnees:\n"
    "1. Base interne EdRCF: cibles pre-scorees avec signaux M&A\n"
    "2. Pappers (open data): donnees legales/financieres de toutes les entreprises francaises\n\n"
    "Quand le contexte contient des 'Donnees Pappers', analyse-les "
    "en croisant avec les criteres EdRCF (age dirigeant, CA, secteur en consolidation, "
    "structure holding, etc.) pour identifier les meilleures opportunites M&A.\n\n"
    "Contexte:\n{context}"
)

_SYSTEM_PROMPT_STREAM = (
    "Tu es le Copilot IA d'EdRCF 6.0, plateforme d'origination M&A. "
    "Reponds en francais, de maniere concise et professionnelle. "
    "Utilise le markdown pour formater tes reponses.\n\n"
    "Contexte:\n{context}"
)


def _resolve_endpoint() -> tuple[str, str, str] | None:
    """Retourne (api_key, base_url, model) ou None si aucune clé configurée."""
    if AI_GATEWAY_API_KEY:
        return (AI_GATEWAY_API_KEY,
                "https://ai-gateway.vercel.sh/v1/chat/completions",
                "deepseek/deepseek-chat")
    if DEEPSEEK_API_KEY:
        return (DEEPSEEK_API_KEY,
                "https://api.deepseek.com/v1/chat/completions",
                "deepseek-chat")
    return None


async def copilot_ai_query(query: str, context: str) -> str | None:
    """Non-streaming chat completion. Retourne le content ou None si fallback rule-based."""
    resolved = _resolve_endpoint()
    if resolved is None:
        return None
    api_key, base_url, model = resolved
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT_FULL.format(context=context)},
                        {"role": "user", "content": query},
                    ],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            print(f"[DeepSeek] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[DeepSeek] Error: {e}")
    return None


async def copilot_ai_query_stream(query: str, context: str) -> AsyncIterator[str]:
    """Streaming version. Yields text chunks."""
    resolved = _resolve_endpoint()
    if resolved is None:
        return
    api_key, base_url, model = resolved
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                base_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "stream": True,
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT_STREAM.format(context=context)},
                        {"role": "user", "content": query},
                    ],
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and "[DONE]" not in line:
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            pass
    except Exception as e:
        print(f"[Copilot Stream] Error: {e}")
