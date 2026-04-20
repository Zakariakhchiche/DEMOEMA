"""Signup orchestrator — lit profile.yaml + exécute flows/<source>.py pour chaque source."""
from __future__ import annotations

import asyncio
import importlib
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] signup.%(name)s: %(message)s",
)
log = logging.getLogger("main")


class Settings(BaseSettings):
    profile_path: Path = Field(default=Path("/app/profile.yaml"))
    env_signups_path: Path = Field(default=Path("/app/.env.signups"))
    audit_dir: Path = Field(default=Path("/app/audit"))
    slack_webhook_url: str = Field(default="")

    class Config:
        env_file = ".env"


settings = Settings()


class Profile(BaseModel):
    company_name: str
    company_legal_form: str = ""
    company_siren: str = ""
    company_naf: str = ""
    contact_first_name: str
    contact_last_name: str
    project_email: str
    project_email_imap_host: str = "localhost"
    project_email_imap_port: int = 143
    project_email_user: str
    project_email_password: str = ""
    company_address: str = ""
    company_city: str = "Paris"
    company_postal_code: str = "75001"
    company_country: str = "FR"
    project_phone: str = ""
    sources_to_signup: list[str] = Field(default_factory=list)
    sources_blocked_manual: list[str] = Field(default_factory=list)
    # Per-flow parameters, e.g. {"dns_ionos": {"record_params": {...}}}
    flow_params: dict[str, dict] = Field(default_factory=dict)


def load_profile() -> Profile:
    if not settings.profile_path.exists():
        raise FileNotFoundError(f"profile.yaml manquant à {settings.profile_path}")
    data = yaml.safe_load(settings.profile_path.read_text(encoding="utf-8"))
    if not data.get("project_email") or not data.get("contact_first_name"):
        raise ValueError("Profile incomplet (project_email + contact_first_name obligatoires)")
    if not data["project_email"].endswith(("demoema.fr", "demoema.com", "proton.me", "slmail.me")):
        log.warning("project_email ne semble pas être un alias dédié projet : %s", data["project_email"])
    return Profile(**data)


async def write_credential(key: str, value: str) -> None:
    """Append crédential dans .env.signups, idempotent (ne dupplique pas)."""
    path = settings.env_signups_path
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    if f"{key}=" in existing:
        # Remplace la ligne existante
        lines = existing.splitlines()
        new_lines = [f"{key}={value}" if line.startswith(f"{key}=") else line for line in lines]
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    path.chmod(0o600)
    log.info("Credential écrit : %s (value redacted)", key)


async def notify_slack(message: str, level: str = "info") -> None:
    if not settings.slack_webhook_url:
        return
    import httpx
    emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level, "")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(settings.slack_webhook_url, json={"text": f"{emoji} [signup] {message}"})
    except Exception:
        log.exception("Slack notif failed")


async def run_source_flow(source: str, profile: Profile) -> dict:
    """Import dynamique flows/<source>.py + exécute."""
    try:
        mod = importlib.import_module(f"signup_agent.flows.{source}")
    except ImportError:
        log.warning("Flow %s non implémenté, skip", source)
        return {"source": source, "status": "flow_not_implemented"}

    audit_subdir = settings.audit_dir / source / datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    audit_subdir.mkdir(parents=True, exist_ok=True)

    log.info("Démarrage flow %s (audit: %s)", source, audit_subdir)
    extra = profile.flow_params.get(source, {})
    try:
        result = await mod.run(
            profile=profile,
            audit_dir=audit_subdir,
            write_credential=write_credential,
            **extra,
        )
        await notify_slack(f"✅ {source} : {result.get('status', 'done')}")
        return {"source": source, **result}
    except Exception as e:
        log.exception("Flow %s crashed", source)
        await notify_slack(f"❌ {source} : {type(e).__name__} - {str(e)[:200]}", level="critical")
        return {"source": source, "status": "crashed", "error": str(e)}


async def main() -> int:
    log.info("DEMOEMA signup-automator démarré")
    try:
        profile = load_profile()
    except Exception as e:
        log.error("Impossible de charger profile: %s", e)
        return 1

    log.info("Sources à enroller: %s", profile.sources_to_signup)

    results = []
    for source in profile.sources_to_signup:
        if source in profile.sources_blocked_manual:
            log.info("Source %s marquée manual (ToS) — skip", source)
            continue
        result = await run_source_flow(source, profile)
        results.append(result)

    log.info("=== Rapport final ===")
    for r in results:
        log.info("  %s: %s", r.get("source"), r.get("status"))

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
