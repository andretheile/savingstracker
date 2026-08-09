"""Classification engine — rule-based auto-categorisation of transactions."""

from __future__ import annotations

import logging
import re
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.classification.models import Category, ClassificationRule
from src.transactions.models import Transaction

logger = logging.getLogger(__name__)


async def classify_transaction(
    session: AsyncSession,
    tx: Transaction,
    user_id: uuid.UUID,
) -> uuid.UUID | None:
    """Classify a transaction using the user's rules, ordered by priority.

    Returns the matched category_id, or None if no rule matches (uncategorized).
    """
    if tx.is_manually_classified and tx.category_id is not None:
        return tx.category_id

    stmt = (
        select(ClassificationRule)
        .where(
            ClassificationRule.user_id == user_id,
            ClassificationRule.is_active.is_(True),
        )
        .order_by(ClassificationRule.priority.asc())
    )
    result = await session.execute(stmt)
    rules = result.scalars().all()

    for rule in rules:
        if _matches(tx, rule):
            logger.debug(
                "Transaction '%s' matched rule '%s' → category %s",
                tx.description[:50],
                rule.value,
                rule.category_id,
            )
            return rule.category_id

    return None


def _matches(tx: Transaction, rule: ClassificationRule) -> bool:
    """Check if a transaction matches a classification rule."""
    field_value = str(getattr(tx, rule.field, "") or "")

    match rule.operator:
        case "contains":
            return rule.value.lower() in field_value.lower()
        case "equals":
            return field_value.lower() == rule.value.lower()
        case "regex":
            try:
                return bool(re.search(rule.value, field_value, re.IGNORECASE))
            except re.error:
                logger.warning("Invalid regex in rule %s: %s", rule.id, rule.value)
                return False
        case "gt":
            try:
                return Decimal(str(tx.amount)) > Decimal(rule.value)
            except Exception:
                return False
        case "lt":
            try:
                return Decimal(str(tx.amount)) < Decimal(rule.value)
            except Exception:
                return False
        case _:
            logger.warning("Unknown operator: %s", rule.operator)
            return False


async def classify_batch(
    session: AsyncSession,
    transactions: list[Transaction],
    user_id: uuid.UUID,
) -> dict[uuid.UUID, uuid.UUID | None]:
    """Classify a batch of transactions. Returns {tx.id: category_id}."""
    # Pre-fetch rules once for the batch
    stmt = (
        select(ClassificationRule)
        .where(
            ClassificationRule.user_id == user_id,
            ClassificationRule.is_active.is_(True),
        )
        .order_by(ClassificationRule.priority.asc())
    )
    result = await session.execute(stmt)
    rules = list(result.scalars().all())

    results: dict[uuid.UUID, uuid.UUID | None] = {}
    for tx in transactions:
        if tx.is_manually_classified and tx.category_id is not None:
            results[tx.id] = tx.category_id
            continue

        matched = None
        for rule in rules:
            if _matches(tx, rule):
                matched = rule.category_id
                break
        results[tx.id] = matched

    return results


# ── Default category seed data ────────────────────────────

DEFAULT_CATEGORIES = [
    {"name": "Salary", "direction": "income", "icon": "💰", "sort_order": 1},
    {"name": "Freelance", "direction": "income", "icon": "💼", "sort_order": 2},
    {"name": "Other Income", "direction": "income", "icon": "💵", "sort_order": 3},
    {"name": "Rent & Housing", "direction": "expense", "icon": "🏠", "sort_order": 10},
    {"name": "Groceries", "direction": "expense", "icon": "🛒", "sort_order": 11},
    {"name": "Transport", "direction": "expense", "icon": "🚗", "sort_order": 12},
    {"name": "Dining Out", "direction": "expense", "icon": "🍽️", "sort_order": 13},
    {"name": "Entertainment", "direction": "expense", "icon": "🎬", "sort_order": 14},
    {"name": "Subscriptions", "direction": "expense", "icon": "📱", "sort_order": 15},
    {"name": "Healthcare", "direction": "expense", "icon": "🏥", "sort_order": 16},
    {"name": "Insurance", "direction": "expense", "icon": "🛡️", "sort_order": 17},
    {"name": "Utilities", "direction": "expense", "icon": "⚡", "sort_order": 18},
    {"name": "Shopping", "direction": "expense", "icon": "🛍️", "sort_order": 19},
    {"name": "Education", "direction": "expense", "icon": "📚", "sort_order": 20},
    {"name": "Other Expense", "direction": "expense", "icon": "❓", "sort_order": 99},
    {"name": "Savings & Investments", "direction": "transfer", "icon": "📈", "sort_order": 30},
    {"name": "Internal Transfer", "direction": "transfer", "icon": "🔄", "sort_order": 31},
]


async def seed_default_categories(session: AsyncSession) -> int:
    """Insert default categories if they don't exist yet (user_id=NULL = system defaults)."""
    existing = await session.execute(
        select(Category).where(Category.user_id.is_(None))
    )
    if existing.scalars().first() is not None:
        return 0  # Already seeded

    count = 0
    for cat_data in DEFAULT_CATEGORIES:
        category = Category(user_id=None, **cat_data)
        session.add(category)
        count += 1

    await session.flush()
    logger.info("Seeded %d default categories", count)
    return count
