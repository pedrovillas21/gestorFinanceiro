"""enable_row_level_security_and_balance_query_index

Habilita Row Level Security (RLS) nas tabelas com dados de usuário e cria o
índice composto que as consultas de saldo por período (dia/semana/mês/3 meses)
precisam para filtrar `user_id` + intervalo de `created_at` com eficiência.

Por que RLS sem policies de leitura/escrita:
O backend FastAPI conecta no Postgres com o papel `postgres` (dono das tabelas),
que ignora RLS por padrão — nada muda para a API. Quem passa a ser bloqueado é
o acesso direto via PostgREST/Supabase client (papéis `anon` e `authenticated`),
que por padrão do Supabase pode ler/escrever em qualquer tabela sem policy
nenhuma assim que a API REST é exposta. Como hoje toda escrita/leitura passa
pelo backend (autenticação própria via JWT, sem Supabase Auth), a policy certa
é "negar tudo" para esses papéis — não existe policy de "cada um vê o próprio
user_id" porque não há `auth.uid()` equivalente ainda. Se o projeto adotar
Supabase Auth futuramente, revisar e adicionar policies de posse por linha.

Padrão daqui pra frente: toda tabela nova com dado de usuário entra com
`ALTER TABLE ... ENABLE/FORCE ROW LEVEL SECURITY` na mesma migration que a cria.

Revision ID: b75641c60d56
Revises: 6ca4ec8a71fb
Create Date: 2026-08-05 17:51:33.412177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b75641c60d56'
down_revision: Union[str, Sequence[str], None] = '6ca4ec8a71fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tabelas com dado de usuário — mantidas em uma lista só para não esquecer
# nenhuma quando uma tabela nova entrar no schema.
TABELAS_COM_RLS = ["users", "transactions", "telegram_tokens"]


def upgrade() -> None:
    """Upgrade schema."""
    for tabela in TABELAS_COM_RLS:
        op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")
        # FORCE garante que nem o dono da tabela escape da RLS por engano
        # (o papel `postgres` da connection string continua passando batido
        # porque é superusuário — FORCE só afeta dono não-superusuário).
        op.execute(f"ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY")

    # Consultas de saldo por período (dia/semana/mês/3 meses) filtram sempre
    # por user_id + intervalo de created_at — o índice em user_id sozinho não
    # ajuda a cortar o intervalo de datas.
    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.create_index(
        "ix_transactions_user_id_created_at",
        "transactions",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_transactions_user_id_created_at", table_name="transactions")
    op.create_index(
        op.f("ix_transactions_user_id"), "transactions", ["user_id"], unique=False
    )

    for tabela in reversed(TABELAS_COM_RLS):
        op.execute(f"ALTER TABLE {tabela} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY")
