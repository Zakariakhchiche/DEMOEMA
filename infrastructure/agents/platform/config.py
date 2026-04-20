"""Configuration agents platform DEMOEMA."""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    prompts_dir: Path = Field(default=Path("/app/prompts"), description="Dossier prompts markdown")
    docs_dir: Path = Field(default=Path("/app/docs"), description="Docs projet (pour tool read_docs)")

    ollama_base_url: str = Field(default="https://ollama.com", description="Endpoint Ollama (Cloud https://ollama.com ou self-hosted http://ollama:11434)")
    ollama_api_key: str = Field(default="", description="API key Ollama Cloud (Pro/Max plan)")
    ollama_timeout_s: int = Field(default=300, description="Timeout requête Ollama (s)")
    ollama_keep_alive: str = Field(default="24h", description="Keep-alive models (ignoré sur Cloud)")

    # DeepSeek (pour agent openclaw)
    deepseek_api_key: str = Field(default="", description="API key DeepSeek (agent openclaw)")
    deepseek_model: str = Field(default="deepseek-chat", description="Modèle DeepSeek")

    # Postgres (via réseau shared-supabase si déployé sur VPS)
    database_url: str = Field(default="", description="DSN Postgres read-only pour tools")

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


settings = Settings()
