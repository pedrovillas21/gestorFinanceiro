import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


AssetType = Literal["stock", "fii", "etf", "bdr", "crypto", "bond", "fund", "other"]
MovementType = Literal[
    "purchase",
    "sale",
    "dividend",
    "jcp",
    "fii_income",
    "split",
    "reverse_split",
    "bonus",
    "subscription",
    "spinoff",
    "merger",
]


class AssetCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    name: str | None = Field(default=None, max_length=255)
    asset_type: AssetType
    currency: str = Field(default="BRL", min_length=3, max_length=3)

    @field_validator("ticker", "currency")
    @classmethod
    def uppercase(cls, value: str) -> str:
        return value.strip().upper()


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    asset_type: AssetType | None = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticker: str
    name: str | None
    asset_type: str
    currency: str
    created_at: datetime


class MovementCreate(BaseModel):
    movement_type: MovementType
    occurred_at: datetime
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18)
    costs: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18)
    gross_amount: Decimal | None = Field(default=None, ge=0, max_digits=18)
    net_amount: Decimal | None = Field(default=None, ge=0, max_digits=18)
    factor: Decimal | None = Field(default=None, gt=0, max_digits=18)
    trade_kind: Literal["swing_trade", "day_trade"] | None = None
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=18)
    fx_rate_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "quantity",
        "unit_price",
        "costs",
        "gross_amount",
        "net_amount",
        "factor",
        "fx_rate",
        mode="before",
    )
    @classmethod
    def decimal_from_input(cls, value: object) -> Decimal | None:
        return None if value is None else Decimal(str(value))

    @model_validator(mode="after")
    def validate_movement(self) -> "MovementCreate":
        trades = {"purchase", "sale", "subscription"}
        if self.movement_type in trades and (
            self.quantity is None or self.unit_price is None or self.unit_price <= 0
        ):
            raise ValueError("compra, venda e subscrição exigem quantidade e preço unitário")
        if self.movement_type in {"purchase", "sale"} and self.trade_kind is None:
            self.trade_kind = "swing_trade"
        if self.movement_type in {"dividend", "jcp", "fii_income"} and (
            self.gross_amount is None and self.net_amount is None
        ):
            raise ValueError("provento exige valor bruto ou líquido")
        if self.movement_type in {"split", "reverse_split"} and self.factor is None:
            raise ValueError("desdobramento/grupamento exige o fator nova_quantidade/antiga")
        if self.movement_type == "bonus" and (
            self.quantity is None or self.unit_price is None
        ):
            raise ValueError("bonificação exige quantidade e custo unitário informado")
        if self.movement_type in {"spinoff", "merger"} and not (self.notes or "").strip():
            raise ValueError("cisão/incorporação exige instruções do lançamento manual")
        if (self.fx_rate is None) != (self.fx_rate_date is None):
            raise ValueError("taxa de câmbio e sua data devem ser informadas juntas")
        return self


class MovementUpdate(BaseModel):
    """Envio parcial de uma movimentação.

    Sem validação cruzada de propósito: as regras por tipo de movimento (provento
    exige valor, desdobramento exige fator, ...) dependem do estado final, não do
    que veio no corpo. O endpoint funde este envio com a linha existente e valida
    o resultado através de `MovementCreate`, para não duplicar as regras.
    """

    movement_type: MovementType | None = None
    occurred_at: datetime | None = None
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18)
    costs: Decimal | None = Field(default=None, ge=0, max_digits=18)
    gross_amount: Decimal | None = Field(default=None, ge=0, max_digits=18)
    net_amount: Decimal | None = Field(default=None, ge=0, max_digits=18)
    factor: Decimal | None = Field(default=None, gt=0, max_digits=18)
    trade_kind: Literal["swing_trade", "day_trade"] | None = None
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=18)
    fx_rate_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "quantity",
        "unit_price",
        "costs",
        "gross_amount",
        "net_amount",
        "factor",
        "fx_rate",
        mode="before",
    )
    @classmethod
    def decimal_from_input(cls, value: object) -> Decimal | None:
        return None if value is None else Decimal(str(value))


class MovementResponse(MovementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    created_at: datetime


class SnapshotResponse(BaseModel):
    """Fotografia da carteira gravada a cada atualização de cotações."""

    model_config = ConfigDict(from_attributes=True)

    total_value: Decimal
    net_cash_flow: Decimal
    captured_at: datetime


class QuoteResponse(BaseModel):
    price: Decimal
    currency: str
    provider: str
    collected_at: datetime
    stale: bool


class PositionResponse(BaseModel):
    asset: AssetResponse
    quantity: Decimal
    average_price: Decimal | None
    invested_cost: Decimal
    realized_gain: Decimal
    dividends_gross: Decimal
    dividends_net: Decimal
    sales_proceeds: Decimal
    quote: QuoteResponse | None
    market_value: Decimal | None
    unrealized_gain: Decimal | None
    return_on_cost: Decimal | None


class PortfolioResponse(BaseModel):
    positions: list[PositionResponse]
    total_market_value: Decimal | None
    total_invested_cost: Decimal
    total_realized_gain: Decimal
    total_unrealized_gain: Decimal | None
    return_on_cost: Decimal | None
    twr: Decimal | None
    twr_annualized: Decimal | None
    mwr: Decimal | None
    profitability_note: str


class QuoteRefreshResponse(BaseModel):
    updated: int
    failed_tickers: list[str]
    collected_at: datetime
