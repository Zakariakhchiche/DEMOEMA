"""Configuration agents platform DEMOEMA."""
from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    prompts_dir: Path = Field(default=Path("/app/prompts"), description="Dossier prompts markdown")
    docs_dir: Path = Field(default=Path("/app/docs"), description="Docs projet (pour tool read_docs)")

    ollama_base_url: str = Field(default="https://ollama.com", description="Endpoint Ollama (Cloud https://ollama.com ou self-hosted http://ollama:11434)")
    ollama_api_key: str = Field(default="", description="API key Ollama Cloud (Pro/Max plan)")
    ollama_timeout_s: int = Field(default=1200, description="Timeout requête Ollama (s) — codegen silver_of_silver avec 9 schémas peut dépasser 10 min côté kimi")
    ollama_keep_alive: str = Field(default="24h", description="Keep-alive models (ignoré sur Cloud)")

    # DeepSeek (pour agent openclaw)
    deepseek_api_key: str = Field(default="", description="API key DeepSeek (agent openclaw)")
    deepseek_model: str = Field(default="deepseek-chat", description="Modèle DeepSeek")

    # ─── INPI RNE (registre-national-entreprises) ─────────────────────────────
    inpi_username: str = Field(default="", description="Email du compte INPI (login RNE)")
    inpi_password: str = Field(default="", description="Password du compte INPI (login RNE)")

    # Postgres datalake. La DSN peut être fournie explicitement (DATABASE_URL),
    # ou dérivée des composantes (DATALAKE_POSTGRES_ROOT_PASSWORD + host/db
    # par défaut qui matchent docker-compose.agents.yml). Cette dérivation est
    # le filet : si l'opérateur set juste le password (le strict minimum déjà
    # nécessaire pour Postgres), tout fonctionne — pas besoin de maintenir
    # deux secrets en miroir.
    database_url: str = Field(default="", description="DSN Postgres (auto-dérivée si vide)")
    datalake_postgres_root_password: str = Field(default="", description="Password root Postgres datalake")
    datalake_host: str = Field(default="datalake-db", description="Hostname Postgres datalake (service compose)")
    datalake_port: int = Field(default=5432, description="Port Postgres datalake")
    datalake_db: str = Field(default="datalake", description="Nom de la base Postgres datalake")
    datalake_user: str = Field(default="postgres", description="Rôle Postgres pour la DSN auto-dérivée")

    # Redis (cache sessions agent)
    redis_url: str = Field(default="redis://redis:6379/0")

    # Atlassian (déjà en env)
    atlassian_api_token: str = Field(default="", description="Token API Atlassian (env)")
    atlassian_email: str = Field(default="zkhchiche@hotmail.com")
    atlassian_base_url: str = Field(default="https://demoema.atlassian.net")

    # Slack
    slack_webhook_url: str = Field(default="")

    # Auth interne agents platform (JWT simple Y1)
    platform_api_key: str = Field(default="", description="Clé API appelante agents platform (header X-API-Key)")

    # Limites
    max_concurrent_invocations: int = Field(default=3, description="Max invocations simultanées")
    max_tokens_response: int = Field(default=4096, description="Max tokens sortie agent")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def _derive_database_url(self):
        """Construire DATABASE_URL depuis le password si elle n'est pas fournie.

        Permet à un nouveau VPS de démarrer en ne configurant qu'une seule
        variable (DATALAKE_POSTGRES_ROOT_PASSWORD). Si la DSN explicite est
        définie elle gagne — utile pour pointer vers un Postgres externe.
        """
        if not self.database_url and self.datalake_postgres_root_password:
            from urllib.parse import quote
            pw = quote(self.datalake_postgres_root_password, safe="")
            self.database_url = (
                f"postgresql://{self.datalake_user}:{pw}"
                f"@{self.datalake_host}:{self.datalake_port}/{self.datalake_db}"
            )
        return self


settings = Settings()
