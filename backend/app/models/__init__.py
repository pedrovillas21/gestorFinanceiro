"""Importa todos os models para que Base.metadata os enxergue (necessário para o autogenerate do Alembic)."""
from app.models.user import User
from app.models.transaction import Transaction
from app.models.telegram_token import TelegramToken

__all__ = ["User", "Transaction", "TelegramToken"]
