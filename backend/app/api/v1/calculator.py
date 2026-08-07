from fastapi import APIRouter

from app.schemas.calculator import (
    CompoundInterestPoint,
    CompoundInterestRequest,
    CompoundInterestResponse,
)
from app.services.investments import calculate_compound_interest


router = APIRouter(prefix="/calculators", tags=["calculators"])


@router.post("/compound-interest", response_model=CompoundInterestResponse)
def compound_interest(payload: CompoundInterestRequest) -> CompoundInterestResponse:
    months = payload.period_value * (12 if payload.period_unit == "years" else 1)
    monthly_rate, values = calculate_compound_interest(
        initial_amount=payload.initial_amount,
        monthly_contribution=payload.monthly_contribution,
        rate=payload.interest_rate,
        rate_period=payload.rate_period,
        months=months,
    )
    schedule = [
        CompoundInterestPoint(month=month, invested=invested, interest=interest, total=total)
        for month, invested, interest, total in values
    ]
    last = schedule[-1]
    return CompoundInterestResponse(
        monthly_rate=monthly_rate,
        total_invested=last.invested,
        total_interest=last.interest,
        final_value=last.total,
        schedule=schedule,
    )
