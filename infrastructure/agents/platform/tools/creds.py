"""Credentials store — fichier JSON chiffré Fernet (AES-128 CBC + HMAC).

Stockage : /root/DEMOEMA-agents/.secrets/credentials.enc
Clé de chiffrement : env var OPENCLAW_VAULT_KEY (base64 urlsafe, 44 chars).
Si absente, génère une clé aléatoire au premier run et l'écrit dans
/root/DEMOEMA-agents/.secrets/vault.key (chmod 600).

Schéma JSON :
{
  "email_accounts": {
    "demomea@proton.me": {"password": null, "purpose": "recovery", "readable_by_agent": false}
  },
  "mailtm_pool": [
    {"alias": "insee", "address": "xxx@mail.tm", "password": "...", "created_at": "..."}
  ],
  "api_credentials": {
    "insee_sirene_v3": {
      "signup_email": "xxx@mail.tm",
      "signup_password": "xxx",
      "dashboard_url": "...",
      "client_id": null, "client_secret": null,
      "status": "pending_email_validation|active|blocked",
      "notes": "...",
      "created_at": "...", "updated_at": "..."
    }
  }
}
"""
from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

log = logging.getLogger("demoema.creds")

# Path DANS le container, mappé sur host via volume docker-compose (./secrets:/app/.secrets).
# Le volume garantit que les credentials survivent aux rebuilds.
VAULT_DIR = Path(os.environ.get("OPENCLAW_VAULT_DIR", "/app/.secrets"))
VAULT_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
STORE_PATH = VAULT_DIR / "credentials.enc"
KEY_PATH = VAULT_DIR / "vault.key"

DEFAULT_STORE: dict[str, Any] = {
    "email_accounts": {},
    "mailtm_pool": [],
    "api_credentials": {},
    "meta": {"version": 1, "created_at": datetime.now(timezone.utc).isoformat()},
}


def _get_key() -> bytes:
    """Récupère la clé Fernet depuis env OU fichier. Génère si besoin."""
    env_key = os.environ.get("OPENCLAW_VAULT_KEY", "").strip()
    if env_key:
        return env_key.encode()
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes().strip()
    # Génère au premier usage
    k = Fernet.generate_key()
    KEY_PATH.write_bytes(k)
    KEY_PATH.chmod(0o600)
    log.warning("Generated new vault key at %s (persist it or set OPENCLAW_VAULT_KEY env)", KEY_PATH)
    return k


def _fernet() -> Fernet:
    return Fernet(_get_key())


def load_store() -> dict:
    if not STORE_PATH.exists():
        return dict(DEFAULT_STORE)
    try:
        enc = STORE_PATH.read_bytes()
        raw = _fernet().decrypt(enc)
        return json.loads(raw.decode())
    except Exception as e:
        log.exception("vault decrypt failed — returning empty: %s", e)
        return dict(DEFAULT_STORE)


def save_store(data: dict) -> None:
    data["meta"] = data.get("meta") or {}
    data["meta"]["updated_at"] = datetime.now(timezone.utc).isoformat()
    raw = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode()
    enc = _fernet().encrypt(raw)
    STORE_PATH.write_bytes(enc)
    STORE_PATH.chmod(0o600)


# ────────── API haut niveau ──────────

def record_mailtm_inbox(alias: str, address: str, password: str) -> None:
    s = load_store()
    s["mailtm_pool"].append({
        "alias": alias, "address": address, "password": password,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    save_store(s)


def set_api_credential(source_id: str, **fields) -> None:
    s = load_store()
    now = datetime.now(timezone.utc).isoformat()
    current = s["api_credentials"].get(source_id, {})
    current.update(fields)
    current["updated_at"] = now
    current.setdefault("created_at", now)
    s["api_credentials"][source_id] = current
    save_store(s)


def get_api_credential(source_id: str) -> dict | None:
    return load_store()["api_credentials"].get(source_id)


def export_plain() -> dict:
    """Retourne le store en clair (pour display ou backup)."""
    return load_store()


def sync_to_env(env_path: Path = Path("/root/DEMOEMA-agents/.env")) -> list[str]:
    """Écrit les credentials 'active' dans .env sous forme de variables.
    Convention : {SOURCE_ID}_CLIENT_ID, {SOURCE_ID}_CLIENT_SECRET, etc.
    Retourne la liste des variables injectées.
    """
    store = load_store()
    injected = []
    env_lines = env_path.read_text().splitlines() if env_path.exists() else []
    existing = {l.split("=", 1)[0] for l in env_lines if "=" in l and not l.startswith("#")}
    for sid, creds in (store.get("api_credentials") or {}).items():
        if creds.get("status") != "active":
            continue
        for k in ("client_id", "client_secret", "api_key", "consumer_key",
                  "consumer_secret", "access_token"):
            v = creds.get(k)
            if not v:
                continue
            env_name = f"{sid.upper()}_{k.upper()}"
            if env_name in existing:
                continue  # ne pas écraser
            env_lines.append(f"{env_name}={v}")
            injected.append(env_name)
    if injected:
        env_path.write_text("\n".join(env_lines) + "\n")
    return injected
