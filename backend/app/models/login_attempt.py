import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LoginAttempt(Base):
    """Contador de falhas de login, por escopo, para o bloqueio progressivo.

    Uma linha por escopo vigiado: o e-mail tentado e o IP de origem. São dois
    ataques diferentes — insistir numa conta e varrer muitas contas do mesmo
    lugar —, e um contador só não pega os dois.

    **Não guarda o e-mail nem o IP em claro**, só o SHA-256 de `tipo:valor`. Esta
    tabela é um contador defensivo, não uma trilha de auditoria: ela precisa
    responder "este escopo está bloqueado?", e para isso o hash basta. Guardar o
    valor cru transformaria um dump da tabela numa lista de e-mails cadastrados
    (e dos que alguém tentou), que é justamente o que o login genérico de
    `/auth/login` evita revelar.

    A linha é efêmera: `clear_login_failures` apaga a do e-mail a cada login bem
    sucedido, e `scripts/purge_access_lifecycle.py` remove as que ficaram para
    trás. Ver `app/services/login_throttle.py` para a escada de bloqueio.
    """

    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # `email` ou `ip`; só para leitura humana e para a limpeza segmentada.
    scope_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    # Falhas desde o último bloqueio (ou desde a última janela ociosa).
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Quantas vezes este escopo já foi bloqueado: é o degrau da escada.
    lock_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
