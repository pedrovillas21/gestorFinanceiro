"""add telegram confirmation state

Revision ID: e6f792bd3a30
Revises: d4e581ac2f20
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f792bd3a30"
down_revision: Union[str, Sequence[str], None] = "d4e581ac2f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("chat_id", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("transaction_type", sa.String(20), nullable=True),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("awaiting", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pending_transactions_chat_id", "pending_transactions", ["chat_id"], unique=True)
    op.execute("ALTER TABLE pending_transactions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pending_transactions FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE pending_transactions NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pending_transactions DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_pending_transactions_chat_id", table_name="pending_transactions")
    op.drop_table("pending_transactions")
