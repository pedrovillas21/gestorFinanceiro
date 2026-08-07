from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.v1.transactions import _as_utc
from app.models.transaction import Transaction
from app.schemas.transaction import CategorySummary, FinancialSummary


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=FinancialSummary)
def financial_summary(
    current_user: CurrentUser,
    db: DatabaseSession,
    start: datetime | None = None,
    end: datetime | None = None,
) -> FinancialSummary:
    conditions = [Transaction.user_id == current_user.id]
    if start:
        conditions.append(Transaction.occurred_at >= _as_utc(start))
    if end:
        conditions.append(Transaction.occurred_at < _as_utc(end))

    totals = dict(
        db.execute(
            select(Transaction.type, func.sum(Transaction.amount))
            .where(*conditions)
            .group_by(Transaction.type)
        ).all()
    )
    income = totals.get("income", Decimal("0.00"))
    expense = totals.get("expense", Decimal("0.00"))
    categories = [
        CategorySummary(category=category or "Sem categoria", amount=amount)
        for category, amount in db.execute(
            select(Transaction.category, func.sum(Transaction.amount))
            .where(*conditions, Transaction.type == "expense")
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
        ).all()
    ]
    return FinancialSummary(
        income=income,
        expense=expense,
        balance=income - expense,
        by_category=categories,
        start=_as_utc(start) if start else None,
        end=_as_utc(end) if end else None,
    )
