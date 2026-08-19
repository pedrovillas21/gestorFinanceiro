import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RefreshToken(Base):
    """Sessão de longa duração, revogável, de um usuário.

    O valor entregue ao cliente é opaco (32 bytes aleatórios) e **não** é
    guardado aqui — a coluna `token_hash` guarda o SHA-256 dele. Um vazamento do
    banco não devolve tokens utilizáveis, e a busca continua sendo um índice
    único em vez de uma varredura com comparação de hash lento.

    Por que SHA-256 e não bcrypt: bcrypt existe para segredos de baixa entropia
    (senhas), onde o custo alto é a defesa. Aqui o segredo tem 256 bits de
    entropia — não há o que adivinhar — e bcrypt impediria a busca por índice.

    Ciclo de vida:
    1. Login/registro cria a linha.
    2. `POST /auth/refresh` marca a linha atual como revogada, aponta
       `replaced_by_id` para a nova e devolve o token novo (rotação).
    3. Logout, troca de senha ou reapresentação de um token já rotacionado
       preenchem `revoked_at`.

    Reapresentar um token já rotacionado é o sinal clássico de token vazado (o
    legítimo e o atacante usam a mesma linha). A resposta é derrubar todas as
    sessões do usuário — ver `app/services/sessions.py`.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        # A limpeza de expirados e a revogação em massa varrem por usuário.
        Index("ix_refresh_tokens_user_expires", "user_id", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Preenchido só na rotação; distingue "trocado por um novo" de "revogado".
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    # Rótulo do dispositivo, só para o usuário reconhecer a sessão na lista.
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
