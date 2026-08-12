"""Unit tests for KPI Engine formula evaluation."""

import pytest

from src.kpis.engine import KPIEngine, TransactionAggregates


def test_kpi_engine_validation():
    engine = KPIEngine()

    is_valid, errors = engine.validate_formula("pct(net_cashflow, total_income)")
    assert is_valid
    assert not errors

    is_valid_syntax, syntax_errors = engine.validate_formula("pct(net_cashflow, ")
    assert not is_valid_syntax
    assert syntax_errors


def test_kpi_engine_variable_extraction():
    engine = KPIEngine()
    vars_found = engine.extract_variables(
        "pct(category_groceries_total + category_dining_out_total, total_expense)"
    )
    assert vars_found == [
        "category_dining_out_total",
        "category_groceries_total",
        "total_expense",
    ]


def test_kpi_engine_computation():
    engine = KPIEngine()
    agg = TransactionAggregates(
        total_income=3000.0,
        total_expense=1800.0,
        net_cashflow=1200.0,
        tx_count=20,
        avg_expense=90.0,
        max_expense=400.0,
        days_in_period=30,
        category_totals={"groceries": 450.0, "dining_out": 300.0},
    )

    # Test savings rate
    res_savings = engine.compute("pct(net_cashflow, total_income)", agg)
    assert float(res_savings.value) == pytest.approx(40.0, 0.01)

    # Test custom category share
    res_groc = engine.compute("pct(category_groceries_total, total_expense)", agg)
    assert float(res_groc.value) == pytest.approx(25.0, 0.01)

    # Test daily burn
    res_burn = engine.compute("total_expense / days_in_period", agg)
    assert float(res_burn.value) == pytest.approx(60.0, 0.01)
