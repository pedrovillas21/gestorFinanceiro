from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.v1.transactions import TZ, _as_utc
from app.models.transaction import Transaction
from app.schemas.transaction import (
    CategorySummary,
    FinancialSummary,
    TimeseriesPoint,
    TimeseriesResponse,
)
from app.services.timeseries import Granularity, TimeseriesRangeError, build_series


router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Nome do fuso como o Postgres o conhece; usado no AT TIME ZONE da agregação.
TZ_NAME = "America/Sao_Paulo"


@router.get("/summary", response_model=FinancialSummary)
def financial_summary(
    current_user: CurrentUser,
    db: DatabaseSession,
    start: datetime | None = None,
    end: datetime | None = None,
    by_category_type: Literal["income", "expense"] = Query(default="expense", alias="type"),
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
            .where(*conditions, Transaction.type == by_category_type)
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
        ).all()
    ]
    return FinancialSummary(
        income=income,
        expense=expense,
        balance=income - expense,
        by_category=categories,
        by_category_type=by_category_type,
        start=_as_utc(start) if start else None,
        end=_as_utc(end) if end else None,
    )


@router.get("/timeseries", response_model=TimeseriesResponse)
def financial_timeseries(
    current_user: CurrentUser,
    db: DatabaseSession,
    start: datetime | None = None,
    end: datetime | None = None,
    granularity: Granularity = "month",
) -> TimeseriesResponse:
    """Receitas e despesas agregadas por dia, semana ou mês.

    A agregação usa `occurred_at AT TIME ZONE 'America/Sao_Paulo'`: agrupar pelo
    UTC cru jogaria um gasto das 22h de 31/01 (01:00 UTC de 01/02) para o mês
    seguinte. Os períodos sem lançamento vêm preenchidos com zero, para o gráfico
    não sair com buracos no eixo.
    """
    conditions = [Transaction.user_id == current_user.id]
    if start:
        conditions.append(Transaction.occurred_at >= _as_utc(start))
    if end:
        conditions.append(Transaction.occurred_at < _as_utc(end))

    # `timezone(zona, ts)` é a forma de função do `ts AT TIME ZONE zona`: converte
    # o timestamptz para o horário local antes de truncar.
    local_time = func.timezone(TZ_NAME, Transaction.occurred_at)
    bucket = func.date_trunc(granularity, local_time).label("bucket")
    rows = db.execute(
        select(bucket, Transaction.type, func.sum(Transaction.amount))
        .where(*conditions)
        .group_by(bucket, Transaction.type)
    ).all()

    totals = {
        (period.date(), transaction_type): amount
        for period, transaction_type, amount in rows
    }

    first, last = _series_bounds(start, end, totals)
    if first is None or last is None:
        points: list[TimeseriesPoint] = []
    else:
        try:
            series = build_series(totals, first, last, granularity)
        except TimeseriesRangeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        points = [
            TimeseriesPoint(
                period=point.period,
                income=point.income,
                expense=point.expense,
                balance=point.balance,
            )
            for point in series
        ]

    return TimeseriesResponse(
        granularity=granularity,
        points=points,
        start=_as_utc(start) if start else None,
        end=_as_utc(end) if end else None,
    )


def _series_bounds(
    start: datetime | None,
    end: datetime | None,
    totals: dict[tuple[date, str], Decimal],
) -> tuple[date | None, date | None]:
    """Primeira e última data local que a série deve cobrir.

    Com `start`/`end` informados, o eixo respeita o período pedido mesmo que não
    haja lançamento nas pontas — é o que faz o seletor de período do dashboard
    mostrar sempre a mesma quantidade de barras. Sem eles, o eixo se limita ao
    intervalo em que o usuário de fato tem dados.
    """
    if start is not None:
        first = _as_utc(start).astimezone(TZ).date()
    else:
        first = min((period for period, _ in totals), default=None)

    if end is not None:
        # `end` é exclusivo: o último instante coberto é o imediatamente anterior.
        # Sem o recuo, um `end` de 01/09 00:00 (seletor "mês de agosto") acabaria
        # incluindo um ponto de setembro inteiro vazio.
        last = (_as_utc(end).astimezone(TZ) - timedelta(microseconds=1)).date()
    else:
        last = max((period for period, _ in totals), default=None)

    return first, last
