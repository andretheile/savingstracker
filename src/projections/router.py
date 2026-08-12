"""FastAPI router for Savings Projections."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db
from src.projections.service import generate_user_projection, get_or_create_user_projection_config

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
    scenarios: list[ScenarioResponse]


class ProjectionConfigUpdate(BaseModel):
    annual_return_pct: float | None = None
    inflation_pct: float | None = None
    horizon_years: int | None = None
    monthly_contribution: float | None = None
    use_actual_savings: bool | None = None


class ProjectionConfigResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    annual_return_pct: float
    inflation_pct: float
    horizon_years: int
    use_actual_savings: bool

    class Config:
        from_attributes = True


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


@router.get("/config/{user_id}", response_model=ProjectionConfigResponse)
async def get_projection_config(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_or_create_user_projection_config(db, user_id)


@router.put("/config/{user_id}", response_model=ProjectionConfigResponse)
async def update_projection_config(
    user_id: uuid.UUID,
    data: ProjectionConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    config = await get_or_create_user_projection_config(db, user_id)
    if data.annual_return_pct is not None:
        config.annual_return_pct = data.annual_return_pct
    if data.inflation_pct is not None:
        config.inflation_pct = data.inflation_pct
    if data.horizon_years is not None:
        config.horizon_years = data.horizon_years
    if data.monthly_contribution is not None:
        config.monthly_contribution = data.monthly_contribution
    if data.use_actual_savings is not None:
        config.use_actual_savings = data.use_actual_savings

    await db.flush()
    return config
