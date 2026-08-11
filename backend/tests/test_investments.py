from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
import asyncio

import pytest
from pydantic import ValidationError

from app.schemas.investment import MovementCreate
from app.services.investments import (
    InvestmentCalculationError,
    calculate_compound_interest,
    calculate_position,
    calculate_twr,
    calculate_xirr,
)
from app.services import market
from app.services import quote_refresh
from app.services.market import FetchedQuote, MarketProviderError


NOW = datetime(2025, 1, 1, tzinfo=UTC)


def movement(kind: str, day: int = 0, **values):
    defaults = {
        "movement_type": kind,
        "occurred_at": NOW + timedelta(days=day),
        "quantity": None,
        "unit_price": None,
        "costs": Decimal("0"),
        "gross_amount": None,
        "net_amount": None,
        "factor": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_weighted_average_sale_and_dividends() -> None:
    movements = [
        movement(
            "purchase", quantity=Decimal("10"), unit_price=Decimal("10"), costs=Decimal("1")
        ),
        movement(
            "purchase", day=1, quantity=Decimal("10"), unit_price=Decimal("20"), costs=Decimal("1")
        ),
        movement(
            "sale", day=2, quantity=Decimal("5"), unit_price=Decimal("30"), costs=Decimal("1")
        ),
        movement(
            "dividend", day=3, gross_amount=Decimal("10"), net_amount=Decimal("8.5")
        ),
    ]
    result = calculate_position(movements, Decimal("25"))
    assert result.quantity == Decimal("15.00000000")
    assert result.average_price == Decimal("15.100000")
    assert result.invested_cost == Decimal("226.500000")
    assert result.realized_gain == Decimal("73.500000")
    assert result.unrealized_gain == Decimal("148.500000")
    assert result.dividends_gross == Decimal("10.000000")
    assert result.dividends_net == Decimal("8.500000")


def test_sale_does_not_change_average_price_and_split_is_inverse() -> None:
    result = calculate_position(
        [
            movement("purchase", quantity=Decimal("10"), unit_price=Decimal("20")),
            movement("sale", day=1, quantity=Decimal("2"), unit_price=Decimal("30")),
            movement("split", day=2, factor=Decimal("2")),
        ]
    )
    assert result.quantity == Decimal("16.00000000")
    assert result.average_price == Decimal("10.000000")


def test_overselling_is_rejected() -> None:
    with pytest.raises(InvestmentCalculationError, match="excede"):
        calculate_position(
            [movement("sale", quantity=Decimal("1"), unit_price=Decimal("10"))]
        )


def test_twr_chains_subperiods_and_annualizes_only_after_30_days() -> None:
    short = [
        SimpleNamespace(total_value=Decimal("100"), net_cash_flow=Decimal("0"), captured_at=NOW),
        SimpleNamespace(
            total_value=Decimal("120"), net_cash_flow=Decimal("10"), captured_at=NOW + timedelta(days=10)
        ),
        SimpleNamespace(
            total_value=Decimal("132"), net_cash_flow=Decimal("0"), captured_at=NOW + timedelta(days=20)
        ),
    ]
    twr, annualized = calculate_twr(short)
    assert twr == Decimal("0.210000")
    assert annualized is None

    long = [short[0], SimpleNamespace(
        total_value=Decimal("121"), net_cash_flow=Decimal("0"), captured_at=NOW + timedelta(days=365)
    )]
    twr, annualized = calculate_twr(long)
    assert twr == Decimal("0.210000")
    assert annualized == Decimal("0.210000")


def test_xirr_converges_and_refuses_too_short_period() -> None:
    assert calculate_xirr(
        [(NOW, Decimal("-1000")), (NOW + timedelta(days=365), Decimal("1100"))]
    ) == Decimal("0.100000")
    assert calculate_xirr(
        [(NOW, Decimal("-1000")), (NOW + timedelta(days=10), Decimal("1010"))]
    ) is None


def test_annual_rate_conversion_is_compound_not_divided_by_twelve() -> None:
    monthly_rate, schedule = calculate_compound_interest(
        initial_amount=Decimal("1000"),
        monthly_contribution=Decimal("100"),
        rate=Decimal("0.12"),
        rate_period="annual",
        months=12,
    )
    assert monthly_rate == Decimal("0.009489")
    assert monthly_rate != Decimal("0.01")
    assert schedule[-1][1] == Decimal("2200.00")
    assert schedule[-1][3] > schedule[-1][1]


def test_movement_schema_requires_reconstructible_fields() -> None:
    with pytest.raises(ValidationError, match="quantidade e preço"):
        MovementCreate(movement_type="purchase", occurred_at=NOW)
    with pytest.raises(ValidationError, match="valor bruto ou líquido"):
        MovementCreate(movement_type="jcp", occurred_at=NOW)
    with pytest.raises(ValidationError, match="fator"):
        MovementCreate(movement_type="split", occurred_at=NOW)
    with pytest.raises(ValidationError, match="lançamento manual"):
        MovementCreate(movement_type="spinoff", occurred_at=NOW)


def test_brapi_v2_quote_contract(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "requestedAt": "2026-08-07T15:00:01.000Z",
                "results": [
                    {
                        "requestedSymbol": "PETR4",
                        "symbol": "PETR4",
                        "data": {
                            "regularMarketPrice": 38.5,
                            "currency": "BRL",
                            "regularMarketTime": "2026-08-07T15:00:00.000Z",
                        },
                    }
                ],
            }

    class FakeClient:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, *, params, headers):
            captured.update(url=url, params=params, headers=headers)
            return FakeResponse()

    monkeypatch.setattr(market.httpx, "AsyncClient", FakeClient)
    quotes = asyncio.run(market.fetch_brapi_quotes(["petr4"]))
    assert captured["url"] == "https://brapi.dev/api/v2/stocks/quote"
    assert captured["params"] == {"symbols": "PETR4"}
    assert captured["headers"]["Authorization"].startswith("Bearer ")
    assert quotes["PETR4"].price == Decimal("38.5")
    assert quotes["PETR4"].collected_at == datetime(2026, 8, 7, 15, tzinfo=UTC)


@pytest.mark.parametrize(
    "requested_at, market_time, price",
    [
        ("not-a-date", None, "38.5"),
        ("2026-08-07T15:00:01Z", "not-a-date", "38.5"),
        ("2026-08-07T15:00:01Z", None, "not-a-number"),
        ("2026-08-07T15:00:01Z", None, "NaN"),
    ],
)
def test_brapi_invalid_provider_values_raise_market_provider_error(
    monkeypatch, requested_at, market_time, price
) -> None:
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "requestedAt": requested_at,
                "results": [
                    {
                        "symbol": "PETR4",
                        "data": {
                            "regularMarketPrice": price,
                            "regularMarketTime": market_time,
                        },
                    }
                ],
            }

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, *, params, headers):
            return FakeResponse()

    monkeypatch.setattr(market.httpx, "AsyncClient", FakeClient)

    with pytest.raises(MarketProviderError):
        asyncio.run(market.fetch_brapi_quotes(["PETR4"]))


class QuoteRefreshDb:
    def __init__(self, asset, latest_quote=None):
        self.asset = asset
        self.latest_quote = latest_quote
        self.added = []
        self.flushes = 0
        self.commits = 0

    def scalars(self, statement):
        return SimpleNamespace(all=lambda: [self.asset])

    def scalar(self, statement):
        return self.latest_quote

    def add(self, item):
        self.added.append(item)

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1


def test_quote_refresh_normalizes_stored_ticker_before_lookup(monkeypatch) -> None:
    asset = SimpleNamespace(id="asset-id", ticker=" petr4 ")
    db = QuoteRefreshDb(asset)
    collected_at = datetime(2026, 8, 7, 15, tzinfo=UTC)

    async def fake_fetch(tickers):
        return {
            "PETR4": FetchedQuote("PETR4", Decimal("38.5"), "BRL", collected_at)
        }

    snapshots = []
    monkeypatch.setattr(quote_refresh, "fetch_brapi_quotes", fake_fetch)
    monkeypatch.setattr(
        quote_refresh,
        "_create_snapshot",
        lambda *args: snapshots.append(args),
    )

    result = quote_refresh.refresh_user_quotes(db, "user-id")

    assert result.updated == 1
    assert result.failed_tickers == []
    assert len(db.added) == 1
    assert len(snapshots) == 1


def test_quote_refresh_skips_duplicate_quote_and_snapshot(monkeypatch) -> None:
    asset = SimpleNamespace(id="asset-id", ticker="PETR4")
    collected_at = datetime(2026, 8, 7, 15, tzinfo=UTC)
    db = QuoteRefreshDb(asset, SimpleNamespace(collected_at=collected_at))

    async def fake_fetch(tickers):
        return {
            "PETR4": FetchedQuote("PETR4", Decimal("38.5"), "BRL", collected_at)
        }

    monkeypatch.setattr(quote_refresh, "fetch_brapi_quotes", fake_fetch)
    monkeypatch.setattr(
        quote_refresh,
        "_create_snapshot",
        lambda *args: pytest.fail("duplicate quote must not create a snapshot"),
    )

    result = quote_refresh.refresh_user_quotes(db, "user-id")

    assert result.updated == 0
    assert result.failed_tickers == []
    assert db.added == []
    assert db.flushes == 0
    assert db.commits == 1
