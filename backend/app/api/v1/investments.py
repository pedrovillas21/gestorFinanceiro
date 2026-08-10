import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.models.investment import (
    InvestmentAsset,
    InvestmentMovement,
    MarketQuote,
    PortfolioSnapshot,
)
from app.schemas.investment import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    MovementCreate,
    MovementResponse,
    PortfolioResponse,
    PositionResponse,
    QuoteRefreshResponse,
    QuoteResponse,
)
from app.services.investments import (
    InvestmentCalculationError,
    calculate_position,
    calculate_twr,
    calculate_xirr,
    movement_cash_flow,
)
from app.services.market import MarketProviderError
from app.services.quote_refresh import refresh_user_quotes


router = APIRouter(prefix="/investments", tags=["investments"])
ZERO = Decimal("0")


def _decimal(value: Decimal | None, places: str) -> Decimal | None:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP) if value is not None else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(status_code=422, detail="occurred_at deve incluir fuso horário")
    return value.astimezone(UTC)


def _owned_asset(
    db: DatabaseSession,
    user_id: uuid.UUID,
    asset_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> InvestmentAsset:
    statement = select(InvestmentAsset).where(
        InvestmentAsset.id == asset_id, InvestmentAsset.user_id == user_id
    )
    if for_update:
        statement = statement.with_for_update()
    asset = db.scalar(statement)
    if asset is None:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    return asset


def _latest_quote(db: DatabaseSession, asset_id: uuid.UUID) -> MarketQuote | None:
    return db.scalar(
        select(MarketQuote)
        .where(MarketQuote.asset_id == asset_id)
        .order_by(MarketQuote.collected_at.desc())
        .limit(1)
    )


@router.get("/assets", response_model=list[AssetResponse])
def list_assets(current_user: CurrentUser, db: DatabaseSession) -> list[InvestmentAsset]:
    return list(
        db.scalars(
            select(InvestmentAsset)
            .where(InvestmentAsset.user_id == current_user.id)
            .order_by(InvestmentAsset.ticker)
        ).all()
    )


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate, current_user: CurrentUser, db: DatabaseSession
) -> InvestmentAsset:
    if payload.currency != "BRL":
        raise HTTPException(
            status_code=422,
            detail="O MVP calcula a carteira em BRL; moedas estrangeiras serão habilitadas futuramente",
        )
    asset = InvestmentAsset(user_id=current_user.id, **payload.model_dump())
    db.add(asset)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ativo já cadastrado") from exc
    db.refresh(asset)
    return asset


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> InvestmentAsset:
    asset = _owned_asset(db, current_user.id, asset_id)
    changes = payload.model_dump(exclude_unset=True)
    if "asset_type" in changes and changes["asset_type"] is None:
        raise HTTPException(status_code=422, detail="asset_type não pode ser nulo")
    for field, value in changes.items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: uuid.UUID, current_user: CurrentUser, db: DatabaseSession
) -> Response:
    asset = _owned_asset(db, current_user.id, asset_id)
    db.delete(asset)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/assets/{asset_id}/movements", response_model=list[MovementResponse])
def list_movements(
    asset_id: uuid.UUID, current_user: CurrentUser, db: DatabaseSession
) -> list[InvestmentMovement]:
    _owned_asset(db, current_user.id, asset_id)
    return list(
        db.scalars(
            select(InvestmentMovement)
            .where(
                InvestmentMovement.asset_id == asset_id,
                InvestmentMovement.user_id == current_user.id,
            )
            .order_by(InvestmentMovement.occurred_at, InvestmentMovement.id)
        ).all()
    )


@router.post(
    "/assets/{asset_id}/movements",
    response_model=MovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_movement(
    asset_id: uuid.UUID,
    payload: MovementCreate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> InvestmentMovement:
    # Serializa alterações de custódia do mesmo ativo até o commit.
    asset = _owned_asset(db, current_user.id, asset_id, for_update=True)
    if asset.currency != "BRL" and (payload.fx_rate is None or payload.fx_rate_date is None):
        raise HTTPException(status_code=422, detail="Ativo estrangeiro exige câmbio e data")
    values = payload.model_dump()
    values["occurred_at"] = _as_utc(payload.occurred_at)
    values["quantity"] = _decimal(payload.quantity, "0.00000001")
    values["unit_price"] = _decimal(payload.unit_price, "0.000001")
    values["costs"] = _decimal(payload.costs, "0.000001")
    values["gross_amount"] = _decimal(payload.gross_amount, "0.000001")
    values["net_amount"] = _decimal(payload.net_amount, "0.000001")
    values["factor"] = _decimal(payload.factor, "0.00000001")
    values["fx_rate"] = _decimal(payload.fx_rate, "0.00000001")
    movement = InvestmentMovement(
        user_id=current_user.id, asset_id=asset_id, **values
    )

    existing = list(
        db.scalars(
            select(InvestmentMovement).where(
                InvestmentMovement.asset_id == asset_id,
                InvestmentMovement.user_id == current_user.id,
            )
        ).all()
    )
    try:
        calculate_position([*existing, movement])
    except InvestmentCalculationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@router.delete("/movements/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: uuid.UUID, current_user: CurrentUser, db: DatabaseSession
) -> Response:
    movement = db.scalar(
        select(InvestmentMovement).where(
            InvestmentMovement.id == movement_id,
            InvestmentMovement.user_id == current_user.id,
        )
    )
    if movement is None:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")
    _owned_asset(db, current_user.id, movement.asset_id, for_update=True)
    remaining = list(
        db.scalars(
            select(InvestmentMovement).where(
                InvestmentMovement.asset_id == movement.asset_id,
                InvestmentMovement.user_id == current_user.id,
                InvestmentMovement.id != movement.id,
            )
        ).all()
    )
    try:
        calculate_position(remaining)
    except InvestmentCalculationError as exc:
        raise HTTPException(
            status_code=409,
            detail="A exclusão deixaria vendas sem custódia suficiente",
        ) from exc
    db.delete(movement)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _portfolio(current_user: CurrentUser, db: DatabaseSession) -> PortfolioResponse:
    assets = list(
        db.scalars(
            select(InvestmentAsset).where(InvestmentAsset.user_id == current_user.id)
        ).all()
    )
    positions: list[PositionResponse] = []
    all_movements: list[InvestmentMovement] = []
    internal_positions = []
    complete_market_value = True
    for asset in assets:
        movements = list(
            db.scalars(
                select(InvestmentMovement).where(
                    InvestmentMovement.asset_id == asset.id,
                    InvestmentMovement.user_id == current_user.id,
                )
            ).all()
        )
        all_movements.extend(movements)
        without_quote = calculate_position(movements)
        quote = _latest_quote(db, asset.id)
        current_price = quote.price if quote is not None else None
        if without_quote.quantity == ZERO:
            current_price = ZERO
        calculated = calculate_position(movements, current_price)
        internal_positions.append(calculated)
        if calculated.quantity > ZERO and quote is None:
            complete_market_value = False
        quote_response = None
        if quote is not None:
            quote_response = QuoteResponse(
                price=quote.price,
                currency=quote.currency,
                provider=quote.provider,
                collected_at=quote.collected_at,
                stale=datetime.now(UTC) - quote.collected_at
                > timedelta(minutes=settings.QUOTE_STALE_AFTER_MINUTES),
            )
        positions.append(
            PositionResponse(
                asset=asset,
                quantity=calculated.quantity,
                average_price=calculated.average_price,
                invested_cost=calculated.invested_cost,
                realized_gain=calculated.realized_gain,
                dividends_gross=calculated.dividends_gross,
                dividends_net=calculated.dividends_net,
                sales_proceeds=calculated.sales_proceeds,
                quote=quote_response,
                market_value=calculated.market_value,
                unrealized_gain=calculated.unrealized_gain,
                return_on_cost=calculated.return_on_cost,
            )
        )

    invested = sum((position.invested_cost for position in internal_positions), ZERO)
    realized = sum((position.realized_gain for position in internal_positions), ZERO)
    contributions = sum((position.contributions for position in internal_positions), ZERO)
    sales = sum((position.sales_proceeds for position in internal_positions), ZERO)
    dividends = sum((position.dividends_net for position in internal_positions), ZERO)
    total_market = (
        sum((position.market_value or ZERO for position in internal_positions), ZERO)
        if complete_market_value
        else None
    )
    unrealized = (
        sum((position.unrealized_gain or ZERO for position in internal_positions), ZERO)
        if complete_market_value
        else None
    )
    simple_return = (
        (total_market + sales + dividends - contributions) / contributions
        if total_market is not None and contributions > ZERO
        else None
    )

    snapshots = list(
        db.scalars(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == current_user.id)
            .order_by(PortfolioSnapshot.captured_at)
        ).all()
    )
    twr, twr_annualized = calculate_twr(snapshots)
    mwr = None
    if total_market is not None:
        investor_flows = [
            (movement.occurred_at, -movement_cash_flow(movement))
            for movement in all_movements
            if movement_cash_flow(movement) != ZERO
        ]
        investor_flows.append((datetime.now(UTC), total_market))
        mwr = calculate_xirr(investor_flows)

    return PortfolioResponse(
        positions=positions,
        total_market_value=_decimal(total_market, "0.000001"),
        total_invested_cost=_decimal(invested, "0.000001"),
        total_realized_gain=_decimal(realized, "0.000001"),
        total_unrealized_gain=_decimal(unrealized, "0.000001"),
        return_on_cost=_decimal(simple_return, "0.000001"),
        twr=twr,
        twr_annualized=twr_annualized,
        mwr=mwr,
        profitability_note=(
            "Indicadores líquidos de custos e brutos de IR. TWR exige ao menos duas "
            "fotografias completas; MWR exige fluxos com 30 dias ou mais."
        ),
    )


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio(current_user: CurrentUser, db: DatabaseSession) -> PortfolioResponse:
    return _portfolio(current_user, db)


@router.post("/quotes/refresh", response_model=QuoteRefreshResponse)
def refresh_quotes(
    current_user: CurrentUser, db: DatabaseSession
) -> QuoteRefreshResponse:
    try:
        result = refresh_user_quotes(db, current_user.id)
    except MarketProviderError as exc:
        # O GET da carteira continua entregando o último preço persistido e seu timestamp.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Provedor indisponível; a carteira mantém as últimas cotações em cache",
        ) from exc

    return QuoteRefreshResponse(
        updated=result.updated,
        failed_tickers=result.failed_tickers,
        collected_at=result.collected_at,
    )
