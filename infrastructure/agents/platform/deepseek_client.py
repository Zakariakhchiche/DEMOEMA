"""DeepSeek Chat client (OpenAI-compatible API).

Endpoint : https://api.deepseek.com/v1/chat/completions
Auth     : Bearer ${DEEPSEEK_API_KEY}
Models   : deepseek-chat (V3), deepseek-reasoner (R1)

Interface minimale : chat(messages, tools) → parsed response dict.
Supporte tool-calling (format OpenAI tools).
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger("demoema.deepseek")

DEFAULT_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 120


class DeepSeekClient:
    def __init__(self, api_key: str | None = None, base_url: str = DEFAULT_BASE,
                 model: str = DEFAULT_MODEL, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY manquante")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Appel /chat/completions. Retourne le premier choice['message'].

        Le message peut contenir :
        - content : str (texte) OU None si tool_calls
        - tool_calls : list[{id, type, function: {name, arguments_json_str}}]
        """
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if r.status_code != 200:
                log.warning("DeepSeek HTTP %d : %s", r.status_code, r.text[:500])
                r.raise_for_status()
            data = r.json()

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"DeepSeek réponse sans choices: {data}")
        return {
            "message": choices[0].get("message") or {},
            "finish_reason": choices[0].get("finish_reason"),
            "usage": data.get("usage") or {},
        }
