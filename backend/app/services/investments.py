"""Cálculos financeiros da carteira usando Decimal em toda a cadeia."""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Iterable, Protocol


ZERO = Decimal("0")
SIX_PLACES = Decimal("0.000001")
EIGHT_PLACES = Decimal("0.00000001")


class MovementLike(Protocol):
    movement_type: str
    occurred_at: datetime
    quantity: Decimal | None
    unit_price: Decimal | None
    costs: Decimal
    gross_amount: Decimal | None
    net_amount: Decimal | None
    factor: Decimal | None


class SnapshotLike(Protocol):
    total_value: Decimal
    net_cash_flow: Decimal
    captured_at: datetime


class InvestmentCalculationError(ValueError):
    pass


@dataclass(slots=True)
class CalculatedPosition:
    quantity: Decimal = ZERO
    average_price: Decimal | None = None
    invested_cost: Decimal = ZERO
    realized_gain: Decimal = ZERO
    dividends_gross: Decimal = ZERO
    dividends_net: Decimal = ZERO
    sales_proceeds: Decimal = ZERO
    contributions: Decimal = ZERO
    market_value: Decimal | None = None
    unrealized_gain: Decimal | None = None
    return_on_cost: Decimal | None = None


def _q(value: Decimal, quantum: Decimal = SIX_PLACES) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def calculate_position(
    movements: Iterable[MovementLike], current_price: Decimal | None = None
) -> CalculatedPosition:
    quantity = ZERO
    total_cost = ZERO
    realized = ZERO
    dividends_gross = ZERO
    dividends_net = ZERO
    sales_proceeds = ZERO
    contributions = ZERO

    with localcontext() as context:
        context.prec = 34
        for movement in sorted(movements, key=lambda item: item.occurred_at):
            kind = movement.movement_type
            costs = movement.costs or ZERO
            if kind in {"purchase", "subscription"}:
                qty = movement.quantity or ZERO
                price = movement.unit_price or ZERO
                acquisition = qty * price + costs
                quantity += qty
                total_cost += acquisition
                contributions += acquisition
            elif kind == "sale":
                qty = movement.quantity or ZERO
                if qty > quantity:
                    raise InvestmentCalculationError("venda excede a quantidade em custódia")
                average = total_cost / quantity if quantity else ZERO
                proceeds = qty * (movement.unit_price or ZERO) - costs
                realized += proceeds - qty * average
                sales_proceeds += proceeds
                total_cost -= qty * average
                quantity -= qty
                if quantity == ZERO:
                    total_cost = ZERO
            elif kind in {"dividend", "jcp", "fii_income"}:
                gross = movement.gross_amount or movement.net_amount or ZERO
                net = movement.net_amount if movement.net_amount is not None else gross - costs
                dividends_gross += gross
                dividends_net += net
            elif kind in {"split", "reverse_split"}:
                factor = movement.factor or ZERO
                if factor <= ZERO:
                    raise InvestmentCalculationError("fator de evento corporativo deve ser positivo")
                quantity *= factor
            elif kind == "bonus":
                qty = movement.quantity or ZERO
                quantity += qty
                total_cost += qty * (movement.unit_price or ZERO) + costs
            elif kind in {"spinoff", "merger"}:
                # O plano exige lançamento manual assistido: guardamos o evento,
                # mas não inventamos uma regra fiscal de rateio de custo.
                continue

        average_price = total_cost / quantity if quantity > ZERO else None
        market_value = quantity * current_price if current_price is not None else None
        unrealized = (
            market_value - total_cost if market_value is not None else None
        )
        simple_return = None
        if market_value is not None and contributions > ZERO:
            simple_return = (
                market_value + sales_proceeds + dividends_net - contributions
            ) / contributions

    return CalculatedPosition(
        quantity=_q(quantity, EIGHT_PLACES),
        average_price=_q(average_price) if average_price is not None else None,
        invested_cost=_q(total_cost),
        realized_gain=_q(realized),
        dividends_gross=_q(dividends_gross),
        dividends_net=_q(dividends_net),
        sales_proceeds=_q(sales_proceeds),
        contributions=_q(contributions),
        market_value=_q(market_value) if market_value is not None else None,
        unrealized_gain=_q(unrealized) if unrealized is not None else None,
        return_on_cost=_q(simple_return) if simple_return is not None else None,
    )


def movement_cash_flow(movement: MovementLike) -> Decimal:
    """Fluxo externo sob a ótica da carteira: aporte positivo, retirada negativa."""
    costs = movement.costs or ZERO
    if movement.movement_type in {"purchase", "subscription"}:
        return (movement.quantity or ZERO) * (movement.unit_price or ZERO) + costs
    if movement.movement_type == "sale":
        return -((movement.quantity or ZERO) * (movement.unit_price or ZERO) - costs)
    if movement.movement_type in {"dividend", "jcp", "fii_income"}:
        received = movement.net_amount
        if received is None:
            received = (movement.gross_amount or ZERO) - costs
        return -received
    return ZERO


def calculate_twr(
    snapshots: Iterable[SnapshotLike],
) -> tuple[Decimal | None, Decimal | None]:
    ordered = sorted(snapshots, key=lambda item: item.captured_at)
    while ordered and ordered[0].total_value <= ZERO:
        ordered.pop(0)
    if len(ordered) < 2:
        return None, None
    result = Decimal("1")
    with localcontext() as context:
        context.prec = 34
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.total_value <= ZERO:
                return None, None
            factor = (current.total_value - current.net_cash_flow) / previous.total_value
            if factor <= ZERO:
                return None, None
            result *= factor
        twr = result - Decimal("1")
        days = (ordered[-1].captured_at.date() - ordered[0].captured_at.date()).days
        annualized = None
        if days >= 30:
            annualized = (Decimal("1") + twr) ** (Decimal(365) / Decimal(days)) - Decimal("1")
    return _q(twr), _q(annualized) if annualized is not None else None


def calculate_xirr(
    cash_flows: Iterable[tuple[datetime, Decimal]],
) -> Decimal | None:
    flows = sorted(cash_flows, key=lambda item: item[0])
    if len(flows) < 2 or not any(value < ZERO for _, value in flows) or not any(
        value > ZERO for _, value in flows
    ):
        return None
    if (flows[-1][0].date() - flows[0][0].date()).days < 30:
        return None
    origin = flows[0][0].date()

    def xnpv(rate: Decimal) -> Decimal:
        base = Decimal("1") + rate
        if base <= ZERO:
            raise ArithmeticError
        return sum(
            value / (base ** (Decimal((when.date() - origin).days) / Decimal(365)))
            for when, value in flows
        )

    with localcontext() as context:
        context.prec = 34
        low = Decimal("-0.9999")
        high = Decimal("1000")
        try:
            low_value = xnpv(low)
            high_value = xnpv(high)
        except ArithmeticError:
            return None
        if low_value == ZERO:
            return _q(low)
        if high_value == ZERO:
            return _q(high)
        if (low_value > ZERO) == (high_value > ZERO):
            return None
        for _ in range(240):
            middle = (low + high) / Decimal("2")
            value = xnpv(middle)
            if abs(value) < Decimal("0.00000001"):
                return _q(middle)
            if (value > ZERO) == (low_value > ZERO):
                low, low_value = middle, value
            else:
                high = middle
        result = (low + high) / Decimal("2")
        return _q(result) if abs(xnpv(result)) < Decimal("0.0001") else None


def calculate_compound_interest(
    *,
    initial_amount: Decimal,
    monthly_contribution: Decimal,
    rate: Decimal,
    rate_period: str,
    months: int,
) -> tuple[Decimal, list[tuple[int, Decimal, Decimal, Decimal]]]:
    """Aporte mensal é realizado ao fim de cada mês."""
    with localcontext() as context:
        context.prec = 34
        monthly_rate = (
            (Decimal("1") + rate) ** (Decimal("1") / Decimal("12")) - Decimal("1")
            if rate_period == "annual"
            else rate
        )
        balance = initial_amount
        invested = initial_amount
        schedule: list[tuple[int, Decimal, Decimal, Decimal]] = []
        for month in range(1, months + 1):
            balance = balance * (Decimal("1") + monthly_rate) + monthly_contribution
            invested += monthly_contribution
            schedule.append(
                (
                    month,
                    _q(invested, Decimal("0.01")),
                    _q(balance - invested, Decimal("0.01")),
                    _q(balance, Decimal("0.01")),
                )
            )
    return _q(monthly_rate), schedule
