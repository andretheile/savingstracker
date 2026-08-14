"""LLM tools that mirror frontend actions on household finance data."""

from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.models import Account
from src.accounts.service import get_account_balance, list_user_accounts
from src.balance_sheets.service import generate_balance_sheet
from src.banking.service import confirm_household_sync, start_household_sync
from src.classification.models import Category
from src.classification.service import DEFAULT_CATEGORIES, reclassify_user_transactions
from src.kpis.engine import kpi_engine
from src.kpis.models import KPIDefinition
from src.kpis.service import evaluate_and_save_kpis_for_user
from src.projections.service import generate_user_projection, get_or_create_user_projection_config
from src.transactions.models import Transaction
from src.transactions.service import add_transaction

_CATEGORY_NAMES = [c["name"] for c in DEFAULT_CATEGORIES]


def _json(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def _month_bounds(
    period_start: str | None = None,
    period_end: str | None = None,
) -> tuple[date, date]:
    if period_start and period_end:
        return date.fromisoformat(period_start), date.fromisoformat(period_end)
    today = date.today()
    start = today.replace(day=1)
    end = (start + relativedelta(months=1)) - relativedelta(days=1)
    return start, end


def _tx_dict(tx: Transaction) -> dict[str, Any]:
    account = getattr(tx, "account", None)
    category = getattr(tx, "category", None)
    return {
        "id": str(tx.id),
        "date": str(tx.transaction_date),
        "amount": float(tx.amount),
        "description": tx.description,
        "counterparty": tx.counterparty,
        "account": account.name if account else str(tx.account_id),
        "account_id": str(tx.account_id),
        "category": category.name if category else None,
        "excluded": bool(tx.exclude_from_totals),
    }


async def _find_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    account: str | None = None,
) -> Account:
    accounts = list(await list_user_accounts(session, user_id))
    needle = (account or "").strip().lower()
    if needle:
        for acc in accounts:
            iban = (acc.iban or "").replace(" ", "").lower()
            if needle == str(acc.id).lower() or needle in acc.name.lower() or iban.endswith(needle):
                return acc
    if len(accounts) == 1:
        return accounts[0]
    names = ", ".join(a.name for a in accounts) or "none"
    raise ValueError(f"Account not found. Available: {names}")


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _tool(
        "get_overview",
        "Household snapshot: accounts, this period's cashflow, and KPI values.",
        {
            "period_start": {"type": "string", "description": "YYYY-MM-DD"},
            "period_end": {"type": "string", "description": "YYYY-MM-DD"},
        },
    ),
    _tool(
        "list_accounts",
        "List bank accounts with balances, household flag, and whether the account is a depot.",
        {},
    ),
    _tool(
        "set_household_account",
        "Include or exclude an account from household KPIs and cashflow.",
        {
            "account": {
                "type": "string",
                "description": "Account name, id, or IBAN suffix (e.g. 1121)",
            },
            "include": {"type": "boolean"},
        },
        ["account", "include"],
    ),
    _tool(
        "list_transactions",
        "Search transactions. Defaults to this month. household_only=true is household view.",
        {
            "search": {
                "type": "string",
                "description": "Match description, counterparty, or category",
            },
            "account": {"type": "string"},
            "period_start": {"type": "string", "description": "YYYY-MM-DD"},
            "period_end": {"type": "string", "description": "YYYY-MM-DD"},
            "household_only": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
    ),
    _tool(
        "add_transaction",
        "Log a manual transaction. Expenses must be negative (e.g. -12.50), income positive.",
        {
            "account": {"type": "string"},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "amount": {"type": "number"},
            "description": {"type": "string"},
            "counterparty": {"type": "string"},
            "category": {"type": "string"},
        },
        ["account", "date", "amount", "description"],
    ),
    _tool(
        "set_transaction_category",
        "Set the category of a transaction by id.",
        {
            "transaction_id": {"type": "string"},
            "category": {"type": "string", "enum": _CATEGORY_NAMES},
        },
        ["transaction_id", "category"],
    ),
    _tool(
        "set_transaction_exclude",
        "Exclude or include a transaction in income/expense totals (one-offs like a car payoff).",
        {
            "transaction_id": {"type": "string"},
            "exclude": {"type": "boolean"},
        },
        ["transaction_id", "exclude"],
    ),
    _tool(
        "list_categories",
        "List available transaction categories.",
        {},
    ),
    _tool(
        "get_balance_sheet",
        "Household income vs expenses for a period (defaults to this calendar month).",
        {
            "period_start": {"type": "string"},
            "period_end": {"type": "string"},
        },
    ),
    _tool(
        "get_kpis",
        "Evaluate household KPIs for a period (defaults to this calendar month).",
        {
            "period_start": {"type": "string"},
            "period_end": {"type": "string"},
        },
    ),
    _tool(
        "create_kpi",
        "Create a custom KPI. Formulas may use total_income, total_expense, "
        "net_cashflow, days_in_period, category_<name>_total, pct(), change().",
        {
            "name": {"type": "string"},
            "formula": {"type": "string"},
            "unit": {"type": "string", "description": "% or €"},
            "description": {"type": "string"},
        },
        ["name", "formula"],
    ),
    _tool(
        "validate_kpi_formula",
        "Check a KPI formula without saving it.",
        {"formula": {"type": "string"}},
        ["formula"],
    ),
    _tool(
        "get_projection",
        "Household savings projection from current balance and this month's net cashflow.",
        {
            "period_start": {"type": "string"},
            "period_end": {"type": "string"},
        },
    ),
    _tool(
        "update_projection_config",
        "Update projection assumptions (return, inflation, horizon, monthly contribution).",
        {
            "annual_return_pct": {"type": "number"},
            "inflation_pct": {"type": "number"},
            "horizon_years": {"type": "integer"},
            "monthly_contribution": {"type": "number"},
            "use_actual_savings": {"type": "boolean"},
        },
    ),
    _tool(
        "reclassify_transactions",
        "Re-run auto-classification on uncategorized (non-manual) transactions.",
        {},
    ),
    _tool(
        "sync_bank",
        "Refresh live bank balances and transactions via FinTS using the stored encrypted PIN. "
        "If the bank needs app approval, tell the user to confirm in the DKB app, then call confirm_bank_sync. "
        "Never ask for a PIN or TAN.",
        {},
    ),
    _tool(
        "confirm_bank_sync",
        "Finish a bank refresh after the user approved the login in the DKB app. "
        "Call only after sync_bank returned needs_approval and the user said they approved it. "
        "Never ask for a PIN or TAN.",
        {},
    ),
]


async def execute_tool(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    arguments: dict[str, Any],
) -> str:
    try:
        result = await _execute(session, user_id, name, arguments or {})
        await session.commit()
        return _json(result)
    except Exception as exc:
        await session.rollback()
        return _json({"error": str(exc)})


async def _execute(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    args: dict[str, Any],
) -> Any:
    if name == "get_overview":
        accounts = await _execute(session, user_id, "list_accounts", {})
        sheet = await _execute(session, user_id, "get_balance_sheet", args)
        kpis = await _execute(session, user_id, "get_kpis", args)
        return {"accounts": accounts, "cashflow": sheet, "kpis": kpis}

    if name == "list_accounts":
        accounts = await list_user_accounts(session, user_id)
        rows = []
        for acc in accounts:
            bal = await get_account_balance(session, acc.id)
            rows.append(
                {
                    "id": str(acc.id),
                    "name": acc.name,
                    "iban": acc.iban,
                    "balance": float(bal),
                    "household": bool(acc.include_in_household),
                    "depot": bool(acc.is_depot),
                }
            )
        return rows

    if name == "set_household_account":
        acc = await _find_account(session, user_id, account=args.get("account"))
        acc.include_in_household = bool(args["include"])
        await session.flush()
        return {"id": str(acc.id), "name": acc.name, "household": acc.include_in_household}

    if name == "list_transactions":
        start, end = _month_bounds(args.get("period_start"), args.get("period_end"))
        household_only = bool(args.get("household_only", True))
        accounts = await list_user_accounts(session, user_id, household_only=household_only)
        account_ids = [a.id for a in accounts]
        if args.get("account"):
            one = await _find_account(session, user_id, account=args["account"])
            account_ids = [one.id]
        if not account_ids:
            return {"count": 0, "transactions": []}
        stmt = (
            select(Transaction)
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
            .order_by(Transaction.transaction_date.desc())
            .limit(500)
        )
        txs = list((await session.execute(stmt)).scalars().all())
        search = (args.get("search") or "").strip().lower()
        filtered = []
        for tx in txs:
            cat_name = getattr(tx.category, "name", "") or ""
            blob = f"{tx.description} {tx.counterparty} {cat_name}".lower()
            if search and search not in blob:
                continue
            filtered.append(_tx_dict(tx))
        limit = int(args.get("limit") or 40)
        return {"count": len(filtered), "transactions": filtered[:limit]}

    if name == "add_transaction":
        acc = await _find_account(session, user_id, account=args.get("account"))
        category_id = None
        if args.get("category"):
            cat = await _category_by_name(session, args["category"])
            category_id = cat.id
        tx = await add_transaction(
            session,
            user_id=user_id,
            account_id=acc.id,
            tx_date=date.fromisoformat(args["date"]),
            amount=args["amount"],
            description=args["description"],
            counterparty=args.get("counterparty") or "",
            category_id=category_id,
        )
        loaded = await session.execute(
            select(Transaction)
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
            .where(Transaction.id == tx.id)
        )
        return _tx_dict(loaded.scalar_one())

    if name == "set_transaction_category":
        tx = await _get_tx(session, user_id, args["transaction_id"])
        cat = await _category_by_name(session, args["category"])
        tx.category_id = cat.id
        tx.is_manually_classified = True
        await session.flush()
        tx.category = cat
        return _tx_dict(tx)

    if name == "set_transaction_exclude":
        tx = await _get_tx(session, user_id, args["transaction_id"])
        tx.exclude_from_totals = bool(args["exclude"])
        await session.flush()
        return _tx_dict(tx)

    if name == "list_categories":
        cats = list((await session.execute(select(Category))).scalars().all())
        if cats:
            return [{"name": c.name, "direction": c.direction} for c in cats]
        return [{"name": c["name"], "direction": c["direction"]} for c in DEFAULT_CATEGORIES]

    if name == "get_balance_sheet":
        start, end = _month_bounds(args.get("period_start"), args.get("period_end"))
        sheet = await generate_balance_sheet(session, user_id, start, end)
        return {
            "period_start": str(sheet.period_start),
            "period_end": str(sheet.period_end),
            "total_income": float(sheet.total_income),
            "total_expense": float(sheet.total_expense),
            "net_cashflow": float(sheet.net_cashflow),
            "savings_rate_pct": float(sheet.savings_rate_pct),
            "income": [
                {"category": i.category_name, "amount": float(i.amount)} for i in sheet.income_items
            ],
            "expenses": [
                {"category": i.category_name, "amount": float(i.amount)}
                for i in sheet.expense_items
            ],
            "account_balances": {k: float(v) for k, v in sheet.account_balances.items()},
        }

    if name == "get_kpis":
        start, end = _month_bounds(args.get("period_start"), args.get("period_end"))
        snaps = await evaluate_and_save_kpis_for_user(session, user_id, start, end)
        rows = []
        for snap in snaps:
            definition = getattr(snap, "kpi_definition", None)
            rows.append(
                {
                    "name": definition.name if definition else "KPI",
                    "value": float(snap.value),
                    "unit": definition.unit if definition else "",
                    "formula": definition.formula if definition else "",
                }
            )
        return rows

    if name == "create_kpi":
        formula = args["formula"]
        valid, errors = kpi_engine.validate_formula(formula)
        if not valid:
            return {"error": ", ".join(errors)}
        kpi = KPIDefinition(
            user_id=user_id,
            name=args["name"],
            description=args.get("description") or "",
            formula=formula,
            unit=args.get("unit") or "%",
            required_variables={"vars": kpi_engine.extract_variables(formula)},
        )
        session.add(kpi)
        await session.flush()
        return {"id": str(kpi.id), "name": kpi.name, "formula": kpi.formula, "unit": kpi.unit}

    if name == "validate_kpi_formula":
        valid, errors = kpi_engine.validate_formula(args["formula"])
        return {
            "is_valid": valid,
            "errors": errors,
            "variables": kpi_engine.extract_variables(args["formula"]),
        }

    if name == "get_projection":
        start, end = _month_bounds(args.get("period_start"), args.get("period_end"))
        proj, _ = await generate_user_projection(session, user_id, start, end)
        return {
            "current_balance": float(proj.current_balance),
            "monthly_contribution": float(proj.monthly_contribution),
            "annual_return_pct": float(proj.annual_return_pct),
            "horizon_years": proj.horizon_years,
            "projected_nominal": float(proj.baseline.nominal),
            "projected_real": float(proj.baseline.real),
            "scenarios": [
                {
                    "label": s.label,
                    "monthly_contribution": float(s.monthly_contribution),
                    "real": float(s.result.real),
                    "delta_vs_baseline_real": float(s.delta_vs_baseline_real),
                }
                for s in proj.scenarios
            ],
        }

    if name == "update_projection_config":
        config = await get_or_create_user_projection_config(session, user_id)
        for field in (
            "annual_return_pct",
            "inflation_pct",
            "horizon_years",
            "monthly_contribution",
            "use_actual_savings",
        ):
            if args.get(field) is not None:
                setattr(config, field, args[field])
        await session.flush()
        return {
            "annual_return_pct": float(config.annual_return_pct),
            "inflation_pct": float(config.inflation_pct),
            "horizon_years": config.horizon_years,
            "use_actual_savings": config.use_actual_savings,
            "monthly_contribution": (
                float(config.monthly_contribution)
                if config.monthly_contribution is not None
                else None
            ),
        }

    if name == "reclassify_transactions":
        updated = await reclassify_user_transactions(session, user_id)
        return {"updated": updated}

    if name == "sync_bank":
        return await start_household_sync(session, user_id)

    if name == "confirm_bank_sync":
        return await confirm_household_sync(session, user_id)

    raise ValueError(f"Unknown tool: {name}")


async def _get_tx(session: AsyncSession, user_id: uuid.UUID, tx_id: str) -> Transaction:
    try:
        parsed = uuid.UUID(tx_id)
    except ValueError as exc:
        raise ValueError("Invalid transaction id") from exc
    stmt = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .options(selectinload(Transaction.account), selectinload(Transaction.category))
        .where(Transaction.id == parsed, Account.user_id == user_id)
    )
    tx = (await session.execute(stmt)).scalar_one_or_none()
    if tx is None:
        raise ValueError("Transaction not found")
    return tx


async def _category_by_name(session: AsyncSession, name: str) -> Category:
    stmt = select(Category).where(Category.name == name).limit(1)
    cat = (await session.execute(stmt)).scalars().first()
    if cat is None:
        raise ValueError(f"Unknown category '{name}'. Use list_categories.")
    return cat
