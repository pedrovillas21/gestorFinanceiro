"""Configurações da aplicação carregadas do .env via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Banco de dados (Supabase PostgreSQL)
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Autenticação JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # IA — Cascata do Gemini (modelo recente -> fallback estável)
    GEMINI_API_KEY: str
    GEMINI_MODEL_PRIMARY: str = "gemini-flash-latest"
    GEMINI_MODEL_FALLBACK: str = "gemini-2.5-flash"

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str
    # Username do bot (sem "@"), usado para montar o Deep Link de vínculo
    TELEGRAM_BOT_USERNAME: str | None = None
    # URL pública HTTPS do backend, usada pelo script de setup no setWebhook
    TELEGRAM_WEBHOOK_URL: str | None = None
    # Validade (em minutos) do token de vínculo gerado para o Deep Link
    TELEGRAM_LINK_TOKEN_TTL_MINUTES: int = 30

    # Front-end (link enviado ao usuário ainda não vinculado)
    WEB_APP_URL: str = "http://localhost:3000"

    # Mercado financeiro
    BRAAPI_TOKEN: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
