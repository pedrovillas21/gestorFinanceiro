import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
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
    MovementUpdate,
    PortfolioResponse,
    PositionResponse,
    QuoteRefreshResponse,
    QuoteResponse,
    SnapshotResponse,
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
from app.services.spreadsheets import (
    export_movements_csv,
    export_portfolio_xlsx,
    export_positions_csv,
)


router = APIRouter(prefix="/investments", tags=["investments"])
ZERO = Decimal("0")


def _decimal(value: Decimal | None, places: str) -> Decimal | None:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP) if value is not None else None


def _as_utc(value: datetime, field: str = "occurred_at") -> datetime:
    """Exige fuso explícito.

    O módulo de investimentos não assume `America/Sao_Paulo` para datas sem
    fuso, ao contrário do de transações: aqui uma data errada por três horas
    desloca uma operação para outro pregão.
    """
    if value.tzinfo is None:
        raise HTTPException(status_code=422, detail=f"{field} deve incluir fuso horário")
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


def _movement_values(payload: MovementCreate) -> dict:
    """Aplica a escala de cada coluna antes de gravar.

    As casas decimais são as do schema do banco (`Numeric(18, 8)` para quantidade
    e fator, `Numeric(18, 6)` para dinheiro). Quantizar aqui, e não deixar o
    driver truncar, mantém o mesmo arredondamento no POST e no PATCH.
    """
    values = payload.model_dump()
    values["occurred_at"] = _as_utc(payload.occurred_at)
    values["quantity"] = _decimal(payload.quantity, "0.00000001")
    values["unit_price"] = _decimal(payload.unit_price, "0.000001")
    values["costs"] = _decimal(payload.costs, "0.000001")
    values["gross_amount"] = _decimal(payload.gross_amount, "0.000001")
    values["net_amount"] = _decimal(payload.net_amount, "0.000001")
    values["factor"] = _decimal(payload.factor, "0.00000001")
    values["fx_rate"] = _decimal(payload.fx_rate, "0.00000001")
    return values


def _asset_movements(
    db: DatabaseSession, user_id: uuid.UUID, asset_id: uuid.UUID, *, excluding: uuid.UUID | None = None
) -> list[InvestmentMovement]:
    conditions = [
        InvestmentMovement.asset_id == asset_id,
        InvestmentMovement.user_id == user_id,
    ]
    if excluding is not None:
        conditions.append(InvestmentMovement.id != excluding)
    return list(db.scalars(select(InvestmentMovement).where(*conditions)).all())


@router.get("/assets", response_model=list[AssetResponse])
def list_assets(
    current_user: CurrentUser,
    db: DatabaseSession,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[InvestmentAsset]:
    """Ativos do usuário, por ticker.

    A resposta segue sendo uma lista pura, e não um envelope com `total`: o
    contrato já documentado para o front depende disso. O cliente pagina até
    receber menos itens que o `limit`.
    """
    return list(
        db.scalars(
            select(InvestmentAsset)
            .where(InvestmentAsset.user_id == current_user.id)
            .order_by(InvestmentAsset.ticker)
            .limit(limit)
            .offset(offset)
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
    asset_id: uuid.UUID,
    current_user: CurrentUser,
    db: DatabaseSession,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
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
            .limit(limit)
            .offset(offset)
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
    values = _movement_values(payload)
    movement = InvestmentMovement(
        user_id=current_user.id, asset_id=asset_id, **values
    )

    existing = _asset_movements(db, current_user.id, asset_id)
    try:
        calculate_position([*existing, movement])
    except InvestmentCalculationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@router.patch("/movements/{movement_id}", response_model=MovementResponse)
def update_movement(
    movement_id: uuid.UUID,
    payload: MovementUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> InvestmentMovement:
    """Corrige uma movimentação sem o rodeio de excluir e recriar.

    A validação por tipo de movimento depende do estado final, não do que veio no
    corpo: trocar só o `movement_type` de `purchase` para `dividend` muda quais
    campos passam a ser obrigatórios. Por isso o envio é fundido com a linha
    atual e o resultado passa inteiro pelo `MovementCreate` — as regras vivem num
    lugar só.
    """
    movement = db.scalar(
        select(InvestmentMovement).where(
            InvestmentMovement.id == movement_id,
            InvestmentMovement.user_id == current_user.id,
        )
    )
    if movement is None:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")
    # Serializa alterações de custódia do mesmo ativo até o commit, como no POST.
    asset = _owned_asset(db, current_user.id, movement.asset_id, for_update=True)

    changes = payload.model_dump(exclude_unset=True)
    merged = {field: getattr(movement, field) for field in MovementCreate.model_fields}
    merged.update(changes)
    try:
        validated = MovementCreate.model_validate(merged)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    if asset.currency != "BRL" and (
        validated.fx_rate is None or validated.fx_rate_date is None
    ):
        raise HTTPException(status_code=422, detail="Ativo estrangeiro exige câmbio e data")

    values = _movement_values(validated)
    # Candidata transitória (fora da sessão): se a custódia não fechar, a linha
    # persistida não chegou a ser tocada e não há nada para desfazer.
    candidate = InvestmentMovement(
        user_id=current_user.id, asset_id=movement.asset_id, **values
    )
    others = _asset_movements(
        db, current_user.id, movement.asset_id, excluding=movement.id
    )
    try:
        calculate_position([*others, candidate])
    except InvestmentCalculationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    for field, value in values.items():
        setattr(movement, field, value)
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
    remaining = _asset_movements(
        db, current_user.id, movement.asset_id, excluding=movement.id
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


@router.get("/snapshots", response_model=list[SnapshotResponse])
def list_snapshots(
    current_user: CurrentUser,
    db: DatabaseSession,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=365, ge=1, le=1000),
) -> list[PortfolioSnapshot]:
    """Curva do patrimônio investido, em ordem cronológica.

    A tabela é alimentada por `refresh_user_quotes` a cada atualização de
    cotações — por isso a curva só ganha pontos quando o usuário atualiza, e é a
    mesma fonte que o TWR consome.

    O `limit` corta as fotografias **mais antigas**, não as mais recentes: um
    gráfico de evolução truncado precisa terminar em hoje.
    """
    conditions = [PortfolioSnapshot.user_id == current_user.id]
    if start:
        conditions.append(PortfolioSnapshot.captured_at >= _as_utc(start, "start"))
    if end:
        conditions.append(PortfolioSnapshot.captured_at < _as_utc(end, "end"))
    recent = list(
        db.scalars(
            select(PortfolioSnapshot)
            .where(*conditions)
            .order_by(PortfolioSnapshot.captured_at.desc())
            .limit(limit)
        ).all()
    )
    return list(reversed(recent))


@router.get("/export")
def export_portfolio(
    current_user: CurrentUser,
    db: DatabaseSession,
    format: Literal["csv", "xlsx"] = "csv",
    sheet: Literal["positions", "movements"] = "positions",
) -> StreamingResponse:
    """Exporta a carteira.

    O XLSX leva as duas abas — posições consolidadas e extrato de movimentações.
    O CSV não tem abas, então o parâmetro `sheet` escolhe qual das duas sai;
    ele é ignorado no XLSX, que traz ambas de qualquer forma.
    """
    portfolio = _portfolio(current_user, db)
    positions = portfolio.positions

    if format == "xlsx":
        movements = _movements_with_ticker(db, current_user.id)
        content = export_portfolio_xlsx(positions, movements)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif sheet == "movements":
        content = export_movements_csv(_movements_with_ticker(db, current_user.id))
        media_type = "text/csv; charset=utf-8"
    else:
        content = export_positions_csv(positions)
        media_type = "text/csv; charset=utf-8"

    suffix = "movimentacoes" if format == "csv" and sheet == "movements" else "carteira"
    headers = {"Content-Disposition": f'attachment; filename="{suffix}.{format}"'}
    return StreamingResponse(BytesIO(content), media_type=media_type, headers=headers)


def _movements_with_ticker(
    db: DatabaseSession, user_id: uuid.UUID
) -> list[tuple[InvestmentMovement, str]]:
    """Movimentações do usuário já com o ticker do ativo, em ordem cronológica.

    O join evita uma consulta por ativo — a exportação percorre a carteira
    inteira, onde N+1 aparece rápido.
    """
    rows = db.execute(
        select(InvestmentMovement, InvestmentAsset.ticker)
        .join(InvestmentAsset, InvestmentAsset.id == InvestmentMovement.asset_id)
        .where(InvestmentMovement.user_id == user_id)
        .order_by(InvestmentMovement.occurred_at, InvestmentMovement.id)
    ).all()
    return [(movement, ticker) for movement, ticker in rows]


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
