"""Configurações da aplicação carregadas do .env via pydantic-settings."""
from pydantic import AliasChoices, Field
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
    # Curto de propósito: o access token é stateless e não consulta a tabela de
    # sessões, então revogar (logout, troca de senha) só tem efeito real quando
    # ele expira. 30 minutos é a janela em que um token já revogado ainda passa.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Refresh token opaco, persistido e rotacionado a cada uso: 30 dias.
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 43200

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
    PRIVACY_POLICY_VERSION: str = "2026-08-10"

    # Ligue **apenas** quando houver proxy confiável na frente (load balancer da
    # hospedagem). Ligada sem proxy, qualquer cliente forja o próprio IP no
    # X-Forwarded-For e escapa do bloqueio por IP do login — ou bloqueia o IP de
    # outra pessoa de propósito. Desligada atrás de proxy, todo mundo chega com o
    # IP do proxy e um atacante só bloquearia a base inteira.
    TRUST_PROXY_HEADERS: bool = False

    # Front-end (link enviado ao usuário ainda não vinculado)
    WEB_APP_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:3000"

    # Mercado financeiro
    BRAPI_TOKEN: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BRAPI_TOKEN", "BRAAPI_TOKEN"),
    )
    MARKET_HTTP_TIMEOUT_SECONDS: float = 10.0
    QUOTE_STALE_AFTER_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
