"""Unit tests for Savings Projection Engine compound interest math and scenarios."""

import pytest
from src.projections.engine import compute_full_projection, project_future_value


def test_project_future_value_zero_growth():
    res = project_future_value(
        current_balance=1000.0,
        monthly_contribution=100.0,
        annual_return_pct=0.0,
        inflation_pct=0.0,
        horizon_years=10,
    )
    # 1000 + 100 * 120 = 13000
    assert float(res.nominal) == pytest.approx(13000.0, 0.01)
    assert float(res.real) == pytest.approx(13000.0, 0.01)


def test_project_future_value_with_growth():
    res = project_future_value(
        current_balance=0.0,
        monthly_contribution=1000.0,
        annual_return_pct=7.0,
        inflation_pct=2.0,
        horizon_years=20,
    )
    assert float(res.nominal) > 500000.0  # Approx ~520k nominal
    assert float(res.real) < float(res.nominal)  # Real should be inflation-adjusted lower
    assert float(res.real) > 350000.0  # Approx ~380k real


def test_compute_full_projection_scenarios():
    full_proj = compute_full_projection(
        current_balance=5000.0,
        monthly_contribution=1000.0,
        total_income=3000.0,
        annual_return_pct=7.0,
        inflation_pct=2.0,
        horizon_years=20,
    )
    assert len(full_proj.scenarios) == 5
    # Verify +5% scenario increases contribution and real FV
    sc_5pct = [s for s in full_proj.scenarios if "+5%" in s.label][0]
    assert float(sc_5pct.monthly_contribution) == pytest.approx(1150.0, 0.01)
    assert float(sc_5pct.delta_vs_baseline_real) > 0.0
