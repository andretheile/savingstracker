"""Savings Projection Engine — compound interest with what-if scenario analysis.

Projects future portfolio value based on monthly savings contributions and
a configurable benchmark return (default: MSCI World ~7% nominal annual).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class ProjectionResult:
    """Result of a single projection calculation."""

    nominal: Decimal  # Future value in nominal terms
    real: Decimal  # Future value adjusted for inflation
    total_contributed: Decimal  # Total money put in
    total_growth: Decimal  # Growth from compound returns


@dataclass
class ScenarioResult:
    """Result of a what-if scenario compared to the baseline."""

    label: str
    description: str
    monthly_contribution: Decimal
    result: ProjectionResult
    delta_vs_baseline_real: Decimal  # Difference in real FV vs. baseline


@dataclass
class FullProjection:
    """Complete projection with baseline + all scenarios."""

    baseline: ProjectionResult
    monthly_contribution: Decimal
    annual_return_pct: Decimal
    inflation_pct: Decimal
    horizon_years: int
    current_balance: Decimal
    scenarios: list[ScenarioResult] = field(default_factory=list)


def project_future_value(
    current_balance: float,
    monthly_contribution: float,
    annual_return_pct: float,
    inflation_pct: float,
    horizon_years: int,
) -> ProjectionResult:
    """Compute nominal and real (inflation-adjusted) future value.

    Uses the annuity formula:
        FV = P(1+r)^n + C × ((1+r)^n - 1) / r

    Where:
        P = current balance
        r = monthly return rate
        n = total months
        C = monthly contribution

    Args:
        current_balance: Current total savings/portfolio value.
        monthly_contribution: Amount saved per month.
        annual_return_pct: Expected annual return (e.g., 7.0 for 7%).
        inflation_pct: Expected annual inflation (e.g., 2.0 for 2%).
        horizon_years: Investment horizon in years.

    Returns:
        ProjectionResult with nominal and real future values.
    """
    n = horizon_years * 12
    total_contributed = Decimal(str(monthly_contribution * n + current_balance))

    # ── Nominal calculation ─────────────────────────────
    r_nominal = annual_return_pct / 100.0 / 12.0
    if r_nominal > 0:
        fv_nominal = (
            current_balance * (1 + r_nominal) ** n
            + monthly_contribution * ((1 + r_nominal) ** n - 1) / r_nominal
        )
    else:
        fv_nominal = current_balance + monthly_contribution * n

    # ── Real (inflation-adjusted) calculation ───────────
    r_real_annual = (1 + annual_return_pct / 100.0) / (1 + inflation_pct / 100.0) - 1
    r_real = r_real_annual / 12.0
    if r_real > 0:
        fv_real = (
            current_balance * (1 + r_real) ** n
            + monthly_contribution * ((1 + r_real) ** n - 1) / r_real
        )
    else:
        fv_real = current_balance + monthly_contribution * n

    fv_nom_dec = Decimal(str(fv_nominal)).quantize(Decimal("0.01"))
    fv_real_dec = Decimal(str(fv_real)).quantize(Decimal("0.01"))

    return ProjectionResult(
        nominal=fv_nom_dec,
        real=fv_real_dec,
        total_contributed=total_contributed.quantize(Decimal("0.01")),
        total_growth=(fv_nom_dec - total_contributed).quantize(Decimal("0.01")),
    )


def compute_full_projection(
    current_balance: float,
    monthly_contribution: float,
    total_income: float,
    annual_return_pct: float = 7.0,
    inflation_pct: float = 2.0,
    horizon_years: int = 20,
) -> FullProjection:
    """Compute a full projection with baseline + what-if scenarios.

    Scenarios show what happens if the user changes their savings rate by
    fixed percentages of income or multiplies their contribution.

    Args:
        current_balance: Current total savings/portfolio.
        monthly_contribution: Current monthly savings amount.
        total_income: Monthly income (for percentage-based scenarios).
        annual_return_pct: Expected annual return.
        inflation_pct: Expected annual inflation.
        horizon_years: Investment horizon in years.

    Returns:
        FullProjection with baseline result and scenario comparisons.
    """
    baseline = project_future_value(
        current_balance, monthly_contribution, annual_return_pct, inflation_pct, horizon_years
    )

    scenarios: list[ScenarioResult] = []

    # Define what-if scenarios
    scenario_defs = [
        (
            "+5% of income",
            "Save 5% more of your income",
            monthly_contribution + (total_income * 0.05),
        ),
        (
            "+10% of income",
            "Save 10% more of your income",
            monthly_contribution + (total_income * 0.10),
        ),
        (
            "−5% of income",
            "If spending increases by 5% of income",
            max(0, monthly_contribution - (total_income * 0.05)),
        ),
        (
            "Double savings",
            "If you double your monthly contribution",
            monthly_contribution * 2,
        ),
        (
            "Halve savings",
            "If your savings are halved",
            monthly_contribution * 0.5,
        ),
    ]

    for label, description, scenario_contribution in scenario_defs:
        scenario_result = project_future_value(
            current_balance,
            scenario_contribution,
            annual_return_pct,
            inflation_pct,
            horizon_years,
        )
        delta = scenario_result.real - baseline.real
        scenarios.append(
            ScenarioResult(
                label=label,
                description=description,
                monthly_contribution=Decimal(str(scenario_contribution)).quantize(
                    Decimal("0.01")
                ),
                result=scenario_result,
                delta_vs_baseline_real=delta.quantize(Decimal("0.01")),
            )
        )

    return FullProjection(
        baseline=baseline,
        monthly_contribution=Decimal(str(monthly_contribution)).quantize(Decimal("0.01")),
        annual_return_pct=Decimal(str(annual_return_pct)),
        inflation_pct=Decimal(str(inflation_pct)),
        horizon_years=horizon_years,
        current_balance=Decimal(str(current_balance)).quantize(Decimal("0.01")),
        scenarios=scenarios,
    )
