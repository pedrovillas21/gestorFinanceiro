import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Isolamento multi-tenant: toda transação pertence a um user_id
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    # Dinheiro é Decimal, nunca float (seção 4.4 do plano de arquitetura): o
    # Numeric do Postgres já chega como Decimal e é assim que ele deve circular.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # ex.: "income" | "expense"
    # ex.: "pix" | "dinheiro" | "débito" | "crédito" | "boleto" | "transferência"
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Origem do lançamento: "web" | "telegram"
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default="web")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
