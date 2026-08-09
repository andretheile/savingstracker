"""KPI Engine — Safe formula evaluation using asteval.

This is the core differentiator of SavingsTracker. Users define KPIs as formula
strings (e.g., "pct(net_cashflow, total_income)") and the engine safely evaluates
them against computed transaction aggregates.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from asteval import Interpreter

logger = logging.getLogger(__name__)


@dataclass
class KPIComputeResult:
    """Result of evaluating a single KPI formula."""

    value: Decimal
    variable_values: dict[str, float]
    errors: list[str] = field(default_factory=list)


@dataclass
class TransactionAggregates:
    """Pre-computed transaction aggregates for a period.

    These become the variable namespace available to KPI formulas.
    """

    total_income: float = 0.0
    total_expense: float = 0.0
    net_cashflow: float = 0.0
    tx_count: int = 0
    avg_expense: float = 0.0
    max_expense: float = 0.0
    days_in_period: int = 30

    # Previous period (for month-over-month comparisons)
    prev_total_income: float = 0.0
    prev_total_expense: float = 0.0
    prev_net_cashflow: float = 0.0

    # Category-level aggregates: category_{snake_name}_total, category_{snake_name}_count
    category_totals: dict[str, float] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)


class KPIEngine:
    """Safely evaluates user-defined KPI formulas against transaction aggregates.

    Uses asteval (AST-based interpreter) instead of eval() to prevent code injection.
    """

    def __init__(self) -> None:
        self._interpreter = Interpreter(minimal=True)
        self._register_builtin_functions()

    def _register_builtin_functions(self) -> None:
        """Register safe helper functions available in formulas."""
        self._interpreter.symtable["pct"] = self._pct
        self._interpreter.symtable["change"] = self._change
        self._interpreter.symtable["abs"] = abs
        self._interpreter.symtable["min"] = min
        self._interpreter.symtable["max"] = max
        self._interpreter.symtable["round"] = round

    @staticmethod
    def _pct(part: float, whole: float) -> float:
        """Calculate percentage: (part / whole) * 100. Safe for zero division."""
        if whole == 0:
            return 0.0
        return (part / whole) * 100.0

    @staticmethod
    def _change(current: float, previous: float) -> float:
        """Calculate % change: ((current - previous) / previous) * 100."""
        if previous == 0:
            return 0.0 if current == 0 else 100.0
        return ((current - previous) / previous) * 100.0

    def validate_formula(self, formula: str) -> tuple[bool, list[str]]:
        """Validate a formula string without evaluating it.

        Returns (is_valid, errors).
        """
        # Create a test interpreter with dummy values for all possible variables
        test_interp = Interpreter(minimal=True)
        test_interp.symtable["pct"] = self._pct
        test_interp.symtable["change"] = self._change
        test_interp.symtable["abs"] = abs
        test_interp.symtable["min"] = min
        test_interp.symtable["max"] = max
        test_interp.symtable["round"] = round

        # Inject dummy values for all referenced variables
        variables = self.extract_variables(formula)
        for var in variables:
            test_interp.symtable[var] = 1.0

        result = test_interp(formula)
        errors = [str(e.get_error()) for e in test_interp.error] if test_interp.error else []

        return (result is not None and not errors), errors

    def extract_variables(self, formula: str) -> list[str]:
        """Extract variable names referenced in a formula.

        Identifies names that are not built-in functions or Python keywords.
        """
        builtin_names = {"pct", "change", "abs", "min", "max", "round", "True", "False", "None"}
        # Match Python identifiers
        identifiers = set(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", formula))
        return sorted(identifiers - builtin_names)

    def compute(
        self, formula: str, aggregates: TransactionAggregates
    ) -> KPIComputeResult:
        """Evaluate a KPI formula against transaction aggregates.

        Args:
            formula: The formula string to evaluate.
            aggregates: Pre-computed transaction data for the period.

        Returns:
            KPIComputeResult with the computed value and any errors.
        """
        # Build the variable namespace
        namespace = self._build_namespace(aggregates)

        # Fresh interpreter for each computation (thread safety)
        interp = Interpreter(minimal=True)
        interp.symtable["pct"] = self._pct
        interp.symtable["change"] = self._change
        interp.symtable["abs"] = abs
        interp.symtable["min"] = min
        interp.symtable["max"] = max
        interp.symtable["round"] = round

        # Inject variables
        for name, value in namespace.items():
            interp.symtable[name] = value

        # Evaluate
        result = interp(formula)
        errors = [str(e.get_error()) for e in interp.error] if interp.error else []

        if result is None or errors:
            logger.warning("KPI formula evaluation failed: %s — errors: %s", formula, errors)
            return KPIComputeResult(
                value=Decimal("0"),
                variable_values=namespace,
                errors=errors,
            )

        return KPIComputeResult(
            value=Decimal(str(result)).quantize(Decimal("0.0001")),
            variable_values=namespace,
            errors=[],
        )

    def _build_namespace(self, agg: TransactionAggregates) -> dict[str, Any]:
        """Convert TransactionAggregates into a flat variable namespace."""
        ns: dict[str, Any] = {
            "total_income": agg.total_income,
            "total_expense": agg.total_expense,
            "net_cashflow": agg.net_cashflow,
            "tx_count": agg.tx_count,
            "avg_expense": agg.avg_expense,
            "max_expense": agg.max_expense,
            "days_in_period": agg.days_in_period,
            "prev_total_income": agg.prev_total_income,
            "prev_total_expense": agg.prev_total_expense,
            "prev_net_cashflow": agg.prev_net_cashflow,
        }
        # Flatten category totals/counts into namespace
        for cat_name, total in agg.category_totals.items():
            ns[f"category_{cat_name}_total"] = total
        for cat_name, count in agg.category_counts.items():
            ns[f"category_{cat_name}_count"] = count
        return ns


# Module-level singleton
kpi_engine = KPIEngine()
