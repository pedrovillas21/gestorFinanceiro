"""create missing processed_telegram_updates

Revision ID: 3c7f1a9b2d84
Revises: f31c8a7d4b20
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c7f1a9b2d84"
down_revision: Union[str, Sequence[str], None] = "f31c8a7d4b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = "processed_telegram_updates"


def upgrade() -> None:
    """Cria a tabela de idempotência do webhook nos bancos onde ela não existe.

    `c2d45a0f9e10` já declara esta tabela, mas um banco carimbado com aquela
    revisão antes de o `create_table` entrar no arquivo ficou marcado como
    atualizado sem nunca receber o DDL — o Alembic registra o id da revisão, não
    o conteúdo dela, então `upgrade head` não reconcilia a diferença.

    O efeito era total: `_processar_update_async` insere aqui antes de qualquer
    outra coisa, e o `ProgrammingError` de tabela inexistente não é capturado
    pelo `except IntegrityError` que protege o caso de update repetido. Todo
    update do Telegram morria no catch-all, com a mesma mensagem genérica.

    A checagem de existência mantém a migration segura nos bancos que já
    receberam a tabela por `c2d45a0f9e10`.
    """
    if TABELA in sa.inspect(op.get_bind()).get_table_names():
        return

    op.create_table(
        TABELA,
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("update_id"),
    )


def downgrade() -> None:
    """Sem efeito: a tabela pertence a `c2d45a0f9e10`, que já a derruba.

    Esta revisão apenas reconcilia bancos que ficaram sem o DDL; dropar aqui
    removeria uma tabela que, na linha do tempo do Alembic, foi criada antes.
    """
