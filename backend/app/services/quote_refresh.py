import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.investment import (
    InvestmentAsset,
    InvestmentMovement,
    MarketQuote,
    PortfolioSnapshot,
)
from app.services.investments import calculate_position, movement_cash_flow
from app.services.market import fetch_brapi_quotes


ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class QuoteRefreshResult:
    updated: int
    failed_tickers: list[str]
    collected_at: datetime


def _latest_quote(db: Session, asset_id: uuid.UUID) -> MarketQuote | None:
    return db.scalar(
        select(MarketQuote)
        .where(MarketQuote.asset_id == asset_id)
        .order_by(MarketQuote.collected_at.desc())
        .limit(1)
    )


def _create_snapshot(
    db: Session,
    user_id: uuid.UUID,
    assets: list[InvestmentAsset],
    captured_at: datetime,
) -> None:
    total_value = ZERO
    for asset in assets:
        movements = list(
            db.scalars(
                select(InvestmentMovement).where(
                    InvestmentMovement.user_id == user_id,
                    InvestmentMovement.asset_id == asset.id,
                )
            ).all()
        )
        position_without_quote = calculate_position(movements)
        if position_without_quote.quantity == ZERO:
            continue
        quote = _latest_quote(db, asset.id)
        if quote is None:
            return
        position = calculate_position(movements, quote.price)
        total_value += position.market_value or ZERO

    previous = db.scalar(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user_id)
        .order_by(PortfolioSnapshot.captured_at.desc())
        .limit(1)
    )
    flow = ZERO
    if previous is not None:
        movements = db.scalars(
            select(InvestmentMovement).where(
                InvestmentMovement.user_id == user_id,
                InvestmentMovement.occurred_at > previous.captured_at,
                InvestmentMovement.occurred_at <= captured_at,
            )
        ).all()
        flow = sum((movement_cash_flow(item) for item in movements), ZERO)
    db.add(
        PortfolioSnapshot(
            user_id=user_id,
            total_value=total_value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
            net_cash_flow=flow.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
            captured_at=captured_at,
        )
    )


def refresh_user_quotes(db: Session, user_id: uuid.UUID) -> QuoteRefreshResult:
    """Roda em thread/worker: HTTP assíncrono em loop privado e persistência síncrona."""
    assets = list(
        db.scalars(
            select(InvestmentAsset).where(InvestmentAsset.user_id == user_id)
        ).all()
    )
    if not assets:
        return QuoteRefreshResult(0, [], datetime.now(UTC))
    fetched = asyncio.run(fetch_brapi_quotes([asset.ticker for asset in assets]))
    timestamps: list[datetime] = []
    failed: list[str] = []
    updated = 0
    for asset in assets:
        quote = fetched.get(asset.ticker.strip().upper())
        if quote is None:
            failed.append(asset.ticker)
            continue
        latest = _latest_quote(db, asset.id)
        if latest is not None and latest.collected_at >= quote.collected_at:
            continue
        db.add(
            MarketQuote(
                asset_id=asset.id,
                price=quote.price.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
                currency=quote.currency,
                provider="brapi",
                collected_at=quote.collected_at,
            )
        )
        timestamps.append(quote.collected_at)
        updated += 1
    collected_at = max(timestamps) if timestamps else datetime.now(UTC)
    if updated:
        db.flush()
        _create_snapshot(db, user_id, assets, datetime.now(UTC))
    db.commit()
    return QuoteRefreshResult(updated, failed, collected_at)
