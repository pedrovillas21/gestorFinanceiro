"""Rotas da versão 1 da API."""
from fastapi import APIRouter

from app.api.v1 import auth, calculator, dashboard, investments, telegram, transactions

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(transactions.router)
api_router.include_router(dashboard.router)
api_router.include_router(investments.router)
api_router.include_router(calculator.router)
api_router.include_router(telegram.router)

__all__ = ["api_router"]
