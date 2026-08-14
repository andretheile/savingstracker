"""FastAPI router for KPI management and evaluation."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser, require_same_household
from src.core.dependencies import get_db
from src.kpis.engine import kpi_engine
from src.kpis.models import KPIDefinition
from src.kpis.service import evaluate_and_save_kpis_for_user

router = APIRouter(prefix="/kpis", tags=["kpis"])


class KPICreate(BaseModel):
    user_id: uuid.UUID
    name: str
    description: str = ""
    formula: str
    unit: str = "%"
    period: str = "monthly"


class KPIValidateRequest(BaseModel):
    formula: str


class KPIValidateResponse(BaseModel):
    is_valid: bool
    variables: list[str]
    errors: list[str]


class KPISnapshotResponse(BaseModel):
    kpi_id: uuid.UUID
    period_start: date
    period_end: date
    value: Decimal

    class Config:
        from_attributes = True


@router.post("/validate", response_model=KPIValidateResponse)
async def validate_formula(data: KPIValidateRequest):
    """Validate a custom KPI formula string without saving."""
    is_valid, errors = kpi_engine.validate_formula(data.formula)
    variables = kpi_engine.extract_variables(data.formula)
    return KPIValidateResponse(
        is_valid=is_valid,
        variables=variables,
        errors=errors,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_custom_kpi(
    data: KPICreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    require_same_household(data.user_id, user)
    is_valid, errors = kpi_engine.validate_formula(data.formula)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid KPI formula: {', '.join(errors)}",
        )

    variables = kpi_engine.extract_variables(data.formula)
    kpi = KPIDefinition(
        user_id=user.id,
        name=data.name,
        description=data.description,
        formula=data.formula,
        unit=data.unit,
        period=data.period,
        required_variables={"vars": variables},
    )
    db.add(kpi)
    await db.flush()
    return {"id": kpi.id, "name": kpi.name, "formula": kpi.formula}


class KPIDashboardItem(BaseModel):
    id: str
    kpi_id: str
    name: str
    formula: str
    unit: str
    value: float
    description: str = ""


@router.get("/{user_id}", response_model=list[KPIDashboardItem])
async def list_kpis_for_user(
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    require_same_household(user_id, user)
    snapshots = await evaluate_and_save_kpis_for_user(db, user_id, period_start, period_end)
    items = []
    for snap in snapshots:
        definition = snap.kpi_definition
        items.append(
            KPIDashboardItem(
                id=str(snap.id),
                kpi_id=str(snap.kpi_id),
                name=definition.name if definition else "KPI",
                formula=definition.formula if definition else "",
                unit=definition.unit if definition else "",
                value=float(snap.value),
                description=definition.description if definition else "",
            )
        )
    return items


@router.post("/evaluate/{user_id}", response_model=list[KPISnapshotResponse])
async def evaluate_kpis(
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    require_same_household(user_id, user)
    snapshots = await evaluate_and_save_kpis_for_user(db, user_id, period_start, period_end)
    return snapshots
