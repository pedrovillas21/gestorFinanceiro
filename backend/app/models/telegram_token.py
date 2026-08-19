import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TelegramToken(Base):
    """Vincula um chat_id do Telegram a um usuário autenticado do sistema.

    Ciclo de vida da linha:
    1. A aplicação Web gera um `link_token` para o usuário (chat_id ainda nulo).
    2. O usuário abre o Deep Link `https://t.me/<bot>?start=<link_token>`.
    3. O bot recebe `/start <link_token>`, grava o `chat_id` e zera o `link_token`.
    """

    __tablename__ = "telegram_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Nulo enquanto o vínculo estiver pendente (token gerado, Deep Link não aberto ainda).
    chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    # Token de uso único do Deep Link; zerado assim que o vínculo é concluído.
    link_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    link_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Preenchido no DELETE /telegram/link. A linha sobrevive para preservar a
    # versão e a data do consentimento; sem esta coluna, um vínculo revogado
    # ficaria idêntico a um que nunca foi concluído (chat_id nulo nos dois casos).
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    privacy_consent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    privacy_consented_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
