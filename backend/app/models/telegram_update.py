from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProcessedTelegramUpdate(Base):
    """Chave de idempotência para impedir lançamentos duplicados por retry."""

    __tablename__ = "processed_telegram_updates"

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
