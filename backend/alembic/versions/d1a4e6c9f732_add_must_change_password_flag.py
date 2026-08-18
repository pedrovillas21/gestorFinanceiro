"""add_must_change_password_flag

A regra de complexidade de senha (schemas/auth.py `is_password_compliant`) só
vale para quem se cadastra ou troca de senha depois dela — não há como testar
uma senha já hasheada (bcrypt não devolve o texto original) para saber se as
contas existentes cumprem a regra nova.

`users.must_change_password` resolve isso de forma lazy: toda conta existente
nasce com `true` aqui (assume o pior até prova em contrário) e o `login`
(`app/api/v1/auth.py`) é o único ponto que ainda vê a senha em claro — a cada
autenticação bem-sucedida ele confere a senha digitada contra a regra atual e
atualiza a coluna. `POST /auth/change-password` sempre desliga o sinalizador,
porque `ChangePasswordRequest.new_password` já passa pela validação.

Cadastro novo (`POST /auth/register`) nasce com `false` — o Python-side
default do modelo, não este `server_default` — porque `RegisterRequest.password`
já é validado na hora.

Revision ID: d1a4e6c9f732
Revises: b8f2c1d90a44
Create Date: 2026-08-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1a4e6c9f732"
down_revision: Union[str, Sequence[str], None] = "b8f2c1d90a44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    # O `server_default` só existe para preencher as linhas já existentes na
    # hora do ADD COLUMN; a partir daqui o valor sempre vem explícito do
    # aplicativo (Python-side default do modelo em novos cadastros, `login` e
    # `change-password` nas trocas), então tira o default do schema para não
    # mascarar um INSERT futuro que esqueça a coluna.
    op.alter_column("users", "must_change_password", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "must_change_password")
