"""Configuration centralisée backend DEMOEMA — Pydantic Settings.

Aligné sur le pattern utilisé par `infrastructure/agents/platform/config.py` :
toutes les clés env sont déclarées en un seul endroit, validées au boot,
et accessibles via un singleton `settings`. Plus de `os.getenv` dispersé
dans 25 sites (audit ARCH-4).

Pour utiliser :
    from config import settings
    if settings.cron_secret:
        ...
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Auth / cron
    cron_secret: str = Field(default="", description="Secret pour les routes /api/admin et cron jobs")

    # Postgres / Supabase
    database_url: str = Field(default="", description="DSN Postgres optionnelle (Hetzner/managed)")
    supabase_url: str = Field(default="", description="URL projet Supabase (sans trailing slash)")
    supabase_key: str = Field(default="", description="Clé service_role Supabase (admin)")
    supabase_anon_key: str = Field(default="", description="Clé publique anon (frontend)")

    # LLM providers
    deepseek_api_key: str = Field(default="", description="DeepSeek API key (Copilot AI)")
    deepseek_model: str = Field(default="deepseek-chat")
    ai_gateway_api_key: str = Field(default="", description="AI Gateway (fallback proxy)")
    openai_api_key: str = Field(default="", description="OpenAI key (legacy / optional)")

    # Pappers / INPI
    pappers_token: str = Field(default="", description="Token API Pappers (legacy MCP)")
    pappers_mcp_url: str = Field(default="", description="URL MCP Pappers")
    inpi_username: str = Field(default="", description="Login INPI RNE")
    inpi_password: str = Field(default="", description="Password INPI RNE")

    # MotherDuck / DuckDB
    motherduck_token: str = Field(default="", description="Token MotherDuck pour bronze pipeline")

    # CORS
    cors_origins: str = Field(default="", description="Origins comma-separated (en plus des défauts)")
    cors_origin_regex: str = Field(default="", description="Regex CORS override (vide = défaut sécurisé)")

    # HTTP client
    http_timeout_s: float = Field(default=15.0, description="Timeout par défaut httpx")
    http_max_connections: int = Field(default=200, description="Pool size max")
    http_max_keepalive: int = Field(default=50, description="Connexions keep-alive max")

    # Environnement
    env: str = Field(default="dev", description="dev/staging/prod — masque les détails d'erreur en prod")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Permettre les minuscules dans .env (DATABASE_URL, database_url tous deux acceptés)
        case_sensitive = False
        extra = "ignore"


settings = Settings()
