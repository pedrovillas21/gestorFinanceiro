"""make import jobs durable

Revision ID: f31c8a7d4b20
Revises: e6f792bd3a30
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f31c8a7d4b20"
down_revision: Union[str, Sequence[str], None] = "e6f792bd3a30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("import_jobs", sa.Column("content", sa.LargeBinary(), nullable=True))
    op.add_column(
        "import_jobs",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "import_jobs",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(
        "ix_import_jobs_status_created_at",
        "import_jobs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_import_jobs_status_created_at", table_name="import_jobs")
    op.drop_column("import_jobs", "attempt_count")
    op.drop_column("import_jobs", "processing_started_at")
    op.drop_column("import_jobs", "content")
