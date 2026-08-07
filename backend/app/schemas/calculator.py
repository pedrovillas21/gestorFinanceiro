from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CompoundInterestRequest(BaseModel):
    initial_amount: Decimal = Field(ge=0, max_digits=18)
    monthly_contribution: Decimal = Field(ge=0, max_digits=18)
    interest_rate: Decimal = Field(gt=-1, max_digits=12)
    rate_period: Literal["monthly", "annual"]
    period_value: int = Field(ge=1, le=1200)
    period_unit: Literal["months", "years"]

    @field_validator("initial_amount", "monthly_contribution", "interest_rate", mode="before")
    @classmethod
    def decimal_from_input(cls, value: object) -> Decimal:
        return Decimal(str(value))

    @model_validator(mode="after")
    def limit_duration(self) -> "CompoundInterestRequest":
        months = self.period_value * (12 if self.period_unit == "years" else 1)
        if months > 1200:
            raise ValueError("período máximo de 100 anos")
        return self


class CompoundInterestPoint(BaseModel):
    month: int
    invested: Decimal
    interest: Decimal
    total: Decimal


class CompoundInterestResponse(BaseModel):
    monthly_rate: Decimal
    total_invested: Decimal
    total_interest: Decimal
    final_value: Decimal
    schedule: list[CompoundInterestPoint]
