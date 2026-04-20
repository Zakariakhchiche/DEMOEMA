"""mail.tm client — boîtes email jetables avec API REST.

API docs : https://docs.mail.tm
Endpoints principaux :
  POST /accounts              → créer compte  { address, password }
  POST /token                 → récupérer JWT { address, password }
  GET  /messages              → lister emails (auth JWT)
  GET  /messages/{id}         → lire contenu
  GET  /domains               → domaines disponibles

Les comptes persistent (pas temp). Gratuit. Pas de téléphone requis.
Exposé comme tools openclaw : create_inbox, check_inbox, extract_verification_link.
"""
from __future__ import annotations

import asyncio
import logging
import re
import secrets
import string
import time
from typing import Optional

import httpx

log = logging.getLogger("demoema.mailbox")

MAILTM_BASE = "https://api.mail.tm"
POLL_INTERVAL = 5       # secondes entre polls
DEFAULT_WAIT_SEC = 120  # total attente pour un email

# State global par run : on garde token et address entre tool_calls
_sessions: dict[str, dict] = {}  # {alias: {address, password, token}}


def _random_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _get_domain(client: httpx.AsyncClient) -> str:
    r = await client.get(f"{MAILTM_BASE}/domains")
    r.raise_for_status()
    data = r.json()
    # hydra:member format selon API mail.tm
    items = data.get("hydra:member") or data.get("member") or data
    for d in items if isinstance(items, list) else [items]:
        if isinstance(d, dict) and d.get("isActive"):
            return d["domain"]
    raise RuntimeError("Aucun domaine mail.tm actif")


async def _token(client: httpx.AsyncClient, address: str, password: str) -> str:
    r = await client.post(
        f"{MAILTM_BASE}/token",
        json={"address": address, "password": password},
    )
    r.raise_for_status()
    return r.json()["token"]


# ────────── TOOLS exposés à openclaw ──────────

async def create_inbox(alias: str = "default") -> str:
    """Crée une boîte mail.tm. `alias` = clé interne pour référencer cette boîte
    dans des calls suivants (ex: 'insee'). Retourne l'adresse email créée."""
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            domain = await _get_domain(c)
            local = "demomea_" + secrets.token_hex(5)
            address = f"{local}@{domain}"
            password = _random_password()
            r = await c.post(
                f"{MAILTM_BASE}/accounts",
                json={"address": address, "password": password},
            )
            if r.status_code not in (200, 201):
                return f"ERR create_inbox: HTTP {r.status_code} {r.text[:200]}"
            token = await _token(c, address, password)
            _sessions[alias] = {"address": address, "password": password, "token": token}
            log.info("[mailbox] inbox created: alias=%s address=%s", alias, address)
            return f"OK inbox alias={alias!r} address={address!r} password={password!r}"
        except Exception as e:
            return f"ERR create_inbox: {type(e).__name__}: {e}"


async def check_inbox(alias: str = "default", unread_only: bool = True) -> str:
    """Liste les messages de la boîte. Retourne texte synthétique.
    Si aucun message encore reçu, retourne '(empty)'."""
    sess = _sessions.get(alias)
    if not sess:
        return f"ERR alias {alias!r} inexistant. Appelle create_inbox d'abord."
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            r = await c.get(
                f"{MAILTM_BASE}/messages",
                headers={"Authorization": f"Bearer {sess['token']}"},
            )
            r.raise_for_status()
            items = r.json().get("hydra:member") or []
            if unread_only:
                items = [m for m in items if not m.get("seen")]
            if not items:
                return "(empty)"
            lines = []
            for m in items[:10]:
                lines.append(
                    f"id={m.get('id')} from={m.get('from',{}).get('address','?')} "
                    f"subject={m.get('subject','')!r} "
                    f"received={m.get('createdAt','?')}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"ERR check_inbox: {type(e).__name__}: {e}"


async def read_message(alias: str, message_id: str) -> str:
    """Lit le contenu texte + HTML d'un message. Tronqué à 3000 chars."""
    sess = _sessions.get(alias)
    if not sess:
        return f"ERR alias {alias!r} inexistant."
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            r = await c.get(
                f"{MAILTM_BASE}/messages/{message_id}",
                headers={"Authorization": f"Bearer {sess['token']}"},
            )
            r.raise_for_status()
            data = r.json()
            body = data.get("text") or ""
            if not body:
                html = data.get("html") or []
                if isinstance(html, list):
                    body = "\n".join(html)
                else:
                    body = str(html)
            if len(body) > 3000:
                body = body[:3000] + "\n...[truncated]"
            return f"subject={data.get('subject','')!r}\n--- body ---\n{body}"
        except Exception as e:
            return f"ERR read_message: {type(e).__name__}: {e}"


async def wait_for_link(alias: str = "default",
                        contains: str = "",
                        timeout_s: int = DEFAULT_WAIT_SEC) -> str:
    """Poll la boîte toutes les 5s jusqu'à recevoir un email avec un lien dans le body.
    Si `contains` est fourni, filtre les liens contenant cette sous-chaîne.
    Retourne le PREMIER lien trouvé, ou ERR timeout."""
    sess = _sessions.get(alias)
    if not sess:
        return f"ERR alias {alias!r} inexistant."
    t_end = time.time() + timeout_s
    url_re = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)
    while time.time() < t_end:
        async with httpx.AsyncClient(timeout=30) as c:
            try:
                r = await c.get(
                    f"{MAILTM_BASE}/messages",
                    headers={"Authorization": f"Bearer {sess['token']}"},
                )
                items = r.json().get("hydra:member") or []
                for m in items:
                    mid = m.get("id")
                    rr = await c.get(
                        f"{MAILTM_BASE}/messages/{mid}",
                        headers={"Authorization": f"Bearer {sess['token']}"},
                    )
                    data = rr.json()
                    body = data.get("text") or ""
                    if not body:
                        html = data.get("html") or []
                        body = "\n".join(html) if isinstance(html, list) else str(html)
                    for match in url_re.findall(body):
                        if contains and contains not in match:
                            continue
                        return f"OK link={match}\n(from message subject={data.get('subject','')!r})"
            except Exception:
                pass
        await asyncio.sleep(POLL_INTERVAL)
    return f"ERR timeout après {timeout_s}s — aucun lien reçu."


# ────────── TOOLS SCHEMA pour DeepSeek ──────────

MAILBOX_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "create_inbox",
            "description": "Create a new mail.tm inbox. Returns email address + password. Use this BEFORE filling a signup form that requires email verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alias": {"type": "string", "description": "Short name to reference this inbox later", "default": "default"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_inbox",
            "description": "List unread messages in inbox by alias.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alias": {"type": "string", "default": "default"},
                    "unread_only": {"type": "boolean", "default": True},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_message",
            "description": "Read full content of a specific message (call check_inbox first to get IDs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "alias": {"type": "string"},
                    "message_id": {"type": "string"},
                },
                "required": ["alias", "message_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_link",
            "description": "Poll inbox until a verification email arrives. Returns the first URL found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alias": {"type": "string", "default": "default"},
                    "contains": {"type": "string", "description": "Optional substring the URL must contain", "default": ""},
                    "timeout_s": {"type": "integer", "default": 120},
                },
            },
        },
    },
]

MAILBOX_DISPATCH = {
    "create_inbox": create_inbox,
    "check_inbox": check_inbox,
    "read_message": read_message,
    "wait_for_link": wait_for_link,
}


def get_sessions() -> dict:
    """Retourne l'état des sessions (pour le credentials store)."""
    return dict(_sessions)
