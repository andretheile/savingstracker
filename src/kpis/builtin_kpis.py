"""Built-in KPI definitions that ship with SavingsTracker."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuiltinKPI:
    """A pre-installed KPI definition."""

    name: str
    description: str
    formula: str
    unit: str
    period: str = "monthly"


BUILTIN_KPIS: list[BuiltinKPI] = [
    BuiltinKPI(
        name="Savings Rate",
        description="Percentage of income saved (not spent)",
        formula="pct(net_cashflow, total_income)",
        unit="%",
    ),
    BuiltinKPI(
        name="Expense Ratio",
        description="Percentage of income spent",
        formula="pct(total_expense, total_income)",
        unit="%",
    ),
    BuiltinKPI(
        name="Daily Burn Rate",
        description="Average daily spending",
        formula="total_expense / days_in_period",
        unit="€",
    ),
    BuiltinKPI(
        name="Groceries Share",
        description="Groceries as percentage of total expenses",
        formula="pct(category_groceries_total, total_expense)",
        unit="%",
    ),
    BuiltinKPI(
        name="Dining Out Share",
        description="Dining out as percentage of total expenses",
        formula="pct(category_dining_out_total, total_expense)",
        unit="%",
    ),
    BuiltinKPI(
        name="Subscriptions Share",
        description="Recurring subscriptions as percentage of total expenses",
        formula="pct(category_subscriptions_total, total_expense)",
        unit="%",
    ),
    BuiltinKPI(
        name="MoM Expense Change",
        description="Month-over-month percentage change in total expenses",
        formula="change(total_expense, prev_total_expense)",
        unit="%",
    ),
    BuiltinKPI(
        name="MoM Income Change",
        description="Month-over-month percentage change in total income",
        formula="change(total_income, prev_total_income)",
        unit="%",
    ),
    BuiltinKPI(
        name="Largest Expense Ratio",
        description="Largest single expense as percentage of total expenses",
        formula="pct(max_expense, total_expense)",
        unit="%",
    ),
    BuiltinKPI(
        name="Average Transaction Size",
        description="Average expense per transaction",
        formula="avg_expense",
        unit="€",
    ),
]
