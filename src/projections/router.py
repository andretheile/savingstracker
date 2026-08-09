"""FastAPI router for Savings Projections."""

from datetime import date
from decimal import Decimal
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.projections.service import generate_user_projection

router = APIRouter(prefix="/projections", tags=["projections"])


class ScenarioResponse(BaseModel):
    label: str
    description: str
    monthly_contribution: Decimal
    real_fv: Decimal
    nominal_fv: Decimal
    delta_vs_baseline_real: Decimal


class ProjectionResponse(BaseModel):
    current_balance: Decimal
    monthly_contribution: Decimal
    annual_return_pct: Decimal
    horizon_years: int
    projected_nominal: Decimal
    projected_real: Decimal
    total_contributed: Decimal
    total_growth: Decimal
    scenarios: List[ScenarioResponse]


@router.post("/compute/{user_id}", response_model=ProjectionResponse)
async def compute_projection(
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
    db: AsyncSession = Depends(get_db),
):
    proj_data, snapshot = await generate_user_projection(db, user_id, period_start, period_end)

    scenarios = [
        ScenarioResponse(
            label=s.label,
            description=s.description,
            monthly_contribution=s.monthly_contribution,
            real_fv=s.result.real,
            nominal_fv=s.result.nominal,
            delta_vs_baseline_real=s.delta_vs_baseline_real,
        )
        for s in proj_data.scenarios
    ]

    return ProjectionResponse(
        current_balance=proj_data.current_balance,
        monthly_contribution=proj_data.monthly_contribution,
        annual_return_pct=proj_data.annual_return_pct,
        horizon_years=proj_data.horizon_years,
        projected_nominal=proj_data.baseline.nominal,
        projected_real=proj_data.baseline.real,
        total_contributed=proj_data.baseline.total_contributed,
        total_growth=proj_data.baseline.total_growth,
        scenarios=scenarios,
    )
