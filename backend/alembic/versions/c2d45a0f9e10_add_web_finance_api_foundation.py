"""add web finance api foundation

Revision ID: c2d45a0f9e10
Revises: b75641c60d56
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d45a0f9e10"
down_revision: Union[str, Sequence[str], None] = "b75641c60d56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE transactions SET occurred_at = created_at WHERE occurred_at IS NULL")
    op.alter_column(
        "transactions",
        "occurred_at",
        nullable=False,
        server_default=sa.text("now()"),
    )

    op.add_column(
        "telegram_tokens",
        sa.Column("privacy_consent_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "telegram_tokens",
        sa.Column("privacy_consented_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("imported_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_jobs_user_id", "import_jobs", ["user_id"])
    op.execute("ALTER TABLE import_jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE import_jobs FORCE ROW LEVEL SECURITY")

    op.create_table(
        "processed_telegram_updates",
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("update_id"),
    )

    with op.get_context().autocommit_block():
        op.create_index(
            "ix_transactions_user_id_occurred_at",
            "transactions",
            ["user_id", "occurred_at"],
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_transactions_user_id_created_at",
            table_name="transactions",
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_transactions_user_id_created_at",
            "transactions",
            ["user_id", "created_at"],
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_transactions_user_id_occurred_at",
            table_name="transactions",
            postgresql_concurrently=True,
        )

    op.drop_table("processed_telegram_updates")
    op.execute("ALTER TABLE import_jobs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE import_jobs DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_import_jobs_user_id", table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_column("telegram_tokens", "privacy_consented_at")
    op.drop_column("telegram_tokens", "privacy_consent_version")
    op.drop_column("transactions", "occurred_at")
