"""add_login_attempts_throttle

`login_attempts` sustenta o bloqueio progressivo de `/auth/login`: a cada 5
falhas o escopo é bloqueado por 10 min, depois 3 h, depois 24 h.

Uma linha por escopo vigiado — o e-mail tentado e o IP de origem —, guardando
apenas o **SHA-256** de `tipo:valor`. A tabela é um contador defensivo, não uma
trilha de auditoria: com o hash ela responde "este escopo está bloqueado?" sem
que um dump vire uma lista de e-mails cadastrados.

Revision ID: b8f2c1d90a44
Revises: a91d3e5c7f60
Create Date: 2026-08-14 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b8f2c1d90a44"
down_revision: Union[str, Sequence[str], None] = "a91d3e5c7f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "login_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_kind", sa.String(length=16), nullable=False),
        # SHA-256 em hexadecimal tem exatamente 64 caracteres.
        sa.Column("scope_hash", sa.String(length=64), nullable=False),
        sa.Column("failures", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lock_level", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Único: a checagem e o incremento buscam a linha exata do escopo, e duas
    # linhas para o mesmo escopo dividiriam o contador ao meio.
    op.create_index(
        op.f("ix_login_attempts_scope_hash"), "login_attempts", ["scope_hash"], unique=True
    )
    # A limpeza varre por `locked_until`/`last_failure_at`.
    op.create_index(
        op.f("ix_login_attempts_locked_until"), "login_attempts", ["locked_until"]
    )

    # Padrão do projeto (ver b75641c60d56): RLS ligada nega acesso direto via
    # PostgREST/Supabase client. Aqui vale mesmo sem `user_id` — quem lê esta
    # tabela sabe quais contas estão sob ataque e quais estão bloqueadas.
    op.execute("ALTER TABLE login_attempts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE login_attempts FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_login_attempts_locked_until"), table_name="login_attempts")
    op.drop_index(op.f("ix_login_attempts_scope_hash"), table_name="login_attempts")
    op.drop_table("login_attempts")
