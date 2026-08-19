"""Agregação de transações por período para o gráfico de evolução.

A parte que o banco faz (`date_trunc` sobre o horário local) fica no endpoint; o
que está aqui é a aritmética de calendário — que períodos existem entre duas
datas e como preencher os que não têm lançamento. Sendo pura, é a única parte
desta funcionalidade que a suíte atual consegue cobrir.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal


Granularity = Literal["day", "week", "month"]

# Teto de segurança: `day` num intervalo de dez anos geraria ~3650 pontos, que
# nenhum gráfico desenha e o JSON carrega à toa. Acima disto o endpoint devolve
# 422 pedindo intervalo menor ou granularidade maior.
MAX_POINTS = 1000

ZERO = Decimal("0.00")


class TimeseriesRangeError(ValueError):
    """O intervalo pedido geraria mais pontos do que `MAX_POINTS`."""


@dataclass(frozen=True)
class SeriesPoint:
    period: date
    income: Decimal
    expense: Decimal
    balance: Decimal


def bucket_start(day: date, granularity: Granularity) -> date:
    """Início do período que contém `day`.

    A semana começa na segunda-feira, para bater com o `date_trunc('week', ...)`
    do Postgres (padrão ISO-8601) — se divergisse, o rótulo do ponto não
    corresponderia aos valores agregados pelo banco.
    """
    if granularity == "day":
        return day
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    return day.replace(day=1)


def next_bucket(start: date, granularity: Granularity) -> date:
    if granularity == "day":
        return start + timedelta(days=1)
    if granularity == "week":
        return start + timedelta(days=7)
    if start.month == 12:
        return date(start.year + 1, 1, 1)
    return date(start.year, start.month + 1, 1)


def bucket_range(first: date, last: date, granularity: Granularity) -> list[date]:
    """Todos os inícios de período entre `first` e `last`, ambos inclusivos."""
    if last < first:
        return []
    current = bucket_start(first, granularity)
    limit = bucket_start(last, granularity)
    periods: list[date] = []
    while current <= limit:
        if len(periods) >= MAX_POINTS:
            raise TimeseriesRangeError(
                f"o intervalo pedido gera mais de {MAX_POINTS} pontos; "
                "reduza o período ou use uma granularidade maior"
            )
        periods.append(current)
        current = next_bucket(current, granularity)
    return periods


def build_series(
    totals: dict[tuple[date, str], Decimal],
    first: date,
    last: date,
    granularity: Granularity,
) -> list[SeriesPoint]:
    """Monta a série completa, com zero nos períodos sem lançamento.

    `totals` vem do banco já agrupado, indexado por (início do período, tipo).
    Preencher aqui, e não no cliente, garante que o gráfico não tenha buracos —
    um mês sem gasto precisa aparecer como zero, não sumir do eixo.

    `balance` é acumulado ao longo da série (saldo corrente), não o líquido
    isolado do bucket: um período sem lançamento repete o saldo do anterior em
    vez de cair para zero, senão a linha do gráfico "zera" no meio do período
    mesmo com o saldo total do intervalo positivo/negativo. O acumulado começa
    do zero em `first` — não há visibilidade de saldo anterior a ele aqui,
    já que `totals` só cobre o intervalo pedido.
    """
    points: list[SeriesPoint] = []
    running_balance = ZERO
    for period in bucket_range(first, last, granularity):
        income = totals.get((period, "income"), ZERO)
        expense = totals.get((period, "expense"), ZERO)
        running_balance += income - expense
        points.append(
            SeriesPoint(
                period=period, income=income, expense=expense, balance=running_balance
            )
        )
    return points
