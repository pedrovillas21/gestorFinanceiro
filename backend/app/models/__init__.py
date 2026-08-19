"""Importa todos os models para que Base.metadata os enxergue (necessário para o autogenerate do Alembic)."""
from app.models.user import User
from app.models.transaction import Transaction
from app.models.telegram_token import TelegramToken
from app.models.import_job import ImportJob
from app.models.telegram_update import ProcessedTelegramUpdate
from app.models.investment import (
    InvestmentAsset,
    InvestmentMovement,
    MarketQuote,
    PortfolioSnapshot,
)
from app.models.pending_transaction import PendingTransaction
from app.models.refresh_token import RefreshToken
from app.models.login_attempt import LoginAttempt

__all__ = [
    "User",
    "RefreshToken",
    "LoginAttempt",
    "Transaction",
    "TelegramToken",
    "ImportJob",
    "ProcessedTelegramUpdate",
    "InvestmentAsset",
    "InvestmentMovement",
    "MarketQuote",
    "PortfolioSnapshot",
    "PendingTransaction",
]
