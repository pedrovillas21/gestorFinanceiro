import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TransactionType = Literal["income", "expense"]


class TransactionBase(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=18)
    category: str | None = Field(default=None, max_length=100)
    type: TransactionType
    payment_method: str | None = Field(default=None, max_length=50)
    occurred_at: datetime | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def decimal_from_input(cls, value: object) -> Decimal:
        return Decimal(str(value))


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=18)
    category: str | None = Field(default=None, max_length=100)
    type: TransactionType | None = None
    payment_method: str | None = Field(default=None, max_length=50)
    occurred_at: datetime | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def decimal_from_input(cls, value: object) -> Decimal | None:
        return None if value is None else Decimal(str(value))


class TransactionResponse(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    occurred_at: datetime
    created_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    limit: int
    offset: int


class CategorySummary(BaseModel):
    category: str
    amount: Decimal


class FinancialSummary(BaseModel):
    income: Decimal
    expense: Decimal
    balance: Decimal
    by_category: list[CategorySummary]
    # Qual tipo o `by_category` agrega. Continua `expense` por padrão, para o
    # contrato anterior seguir valendo sem o parâmetro.
    by_category_type: TransactionType = "expense"
    start: datetime | None
    end: datetime | None


class CategoryOption(BaseModel):
    """Categoria já usada pelo usuário, com a frequência para ordenar o filtro."""

    category: str
    count: int


class TimeseriesPoint(BaseModel):
    # Data local (America/Sao_Paulo) em que o período começa: o próprio dia, a
    # segunda-feira da semana ou o dia 1 do mês.
    period: date
    income: Decimal
    expense: Decimal
    balance: Decimal


class TimeseriesResponse(BaseModel):
    granularity: Literal["day", "week", "month"]
    points: list[TimeseriesPoint]
    start: datetime | None
    end: datetime | None
