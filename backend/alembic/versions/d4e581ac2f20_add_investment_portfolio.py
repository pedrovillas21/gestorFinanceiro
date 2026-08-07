"""add investment portfolio

Revision ID: d4e581ac2f20
Revises: c2d45a0f9e10
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e581ac2f20"
down_revision: Union[str, Sequence[str], None] = "c2d45a0f9e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investment_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(3), server_default="BRL", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "ticker", "currency", name="uq_asset_user_ticker_currency"),
    )
    op.create_index("ix_investment_assets_user_id", "investment_assets", ["user_id"])

    op.create_table(
        "investment_movements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("movement_type", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("costs", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("net_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("factor", sa.Numeric(18, 8), nullable=True),
        sa.Column("trade_kind", sa.String(16), nullable=True),
        sa.Column("fx_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("fx_rate_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["investment_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_investment_movements_user_asset_date",
        "investment_movements",
        ["user_id", "asset_id", "occurred_at"],
    )

    op.create_table(
        "market_quotes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["investment_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_quotes_asset_collected", "market_quotes", ["asset_id", "collected_at"])

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("total_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("net_cash_flow", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolio_snapshots_user_date", "portfolio_snapshots", ["user_id", "captured_at"])

    for table in (
        "investment_assets",
        "investment_movements",
        "market_quotes",
        "portfolio_snapshots",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in (
        "portfolio_snapshots",
        "market_quotes",
        "investment_movements",
        "investment_assets",
    ):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_portfolio_snapshots_user_date", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
    op.drop_index("ix_market_quotes_asset_collected", table_name="market_quotes")
    op.drop_table("market_quotes")
    op.drop_index("ix_investment_movements_user_asset_date", table_name="investment_movements")
    op.drop_table("investment_movements")
    op.drop_index("ix_investment_assets_user_id", table_name="investment_assets")
    op.drop_table("investment_assets")
