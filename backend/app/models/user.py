import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Python-side default (não server_default): cadastro novo já passa pela
    # validação de complexidade do RegisterRequest, então nasce em dia — só o
    # `login` (única rota que vê senha em claro depois disso) pode ligar de
    # volta. Contas existentes antes desta coluna ganham `true` via
    # server_default na migração (alembic/versions), assumindo o pior até a
    # próxima vez que a pessoa logar.
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
