"""add_refresh_tokens_and_telegram_unlink

Duas mudanças que andam juntas por serem ambas de ciclo de vida de acesso:

1. `refresh_tokens` — sessões de longa duração, revogáveis. Guarda o SHA-256 do
   token opaco, nunca o valor entregue ao cliente. Habilita logout de verdade e
   faz a troca de senha derrubar os outros aparelhos.

2. `telegram_tokens.unlinked_at` — `DELETE /telegram/link` preserva a linha (e
   com ela a versão e a data do consentimento) em vez de apagá-la. Sem uma
   coluna de revogação, uma linha com consentimento preenchido e `chat_id` nulo
   seria indistinguível de um vínculo que nunca chegou a ser concluído.

Revision ID: a91d3e5c7f60
Revises: 3c7f1a9b2d84
Create Date: 2026-08-12 09:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a91d3e5c7f60"
down_revision: Union[str, Sequence[str], None] = "3c7f1a9b2d84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        # SHA-256 em hexadecimal tem exatamente 64 caracteres.
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        # SET NULL, não CASCADE: apagar uma linha antiga da cadeia de rotação não
        # pode derrubar a sessão viva que ela apontava.
        sa.ForeignKeyConstraint(["replaced_by_id"], ["refresh_tokens.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True
    )
    op.create_index(
        "ix_refresh_tokens_user_expires", "refresh_tokens", ["user_id", "expires_at"]
    )

    # Padrão do projeto (ver b75641c60d56): toda tabela com dado de usuário nasce
    # com RLS ligada, negando acesso direto via PostgREST/Supabase client.
    op.execute("ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY")

    op.add_column(
        "telegram_tokens",
        sa.Column("unlinked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("telegram_tokens", "unlinked_at")
    op.drop_index("ix_refresh_tokens_user_expires", table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_token_hash"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
