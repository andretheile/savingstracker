"""Classification engine — rule-based auto-categorisation of transactions."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.classification.models import Category, ClassificationRule
from src.transactions.models import Transaction

logger = logging.getLogger(__name__)

IBAN_RE = re.compile(r"DE[0-9]{20}", re.IGNORECASE)

TRANSFER_CATEGORY = "Internal Transfer"
DEPOT_CATEGORY = "Depot Transfer"


@dataclass(frozen=True)
class BuiltinRule:
    category_name: str
    pattern: str
    priority: int = 100


# First match wins. Patterns run against description + counterparty + reference.
BUILTIN_RULES: list[BuiltinRule] = [
    BuiltinRule("Rent & Housing", r"win-win|miete|wohnung|betriebskosten|hausgeld|kaltmiete", 10),
    BuiltinRule("Salary", r"gehalt|lohnabrechnung|\bsalary\b", 15),
    BuiltinRule(
        "Depot Transfer",
        r"wertpapierdepot|depotübertrag|dkb.?depot|\bdepotkonto\b|\bdepot\b",
        18,
    ),
    BuiltinRule("Insurance", r"huk-?24|huk-?coburg|versicherung|\badac\b", 20),
    BuiltinRule("Utilities", r"e\.on|stadtwerke|\bstrom\b|telekom|vodafone|\bo2\b", 20),
    BuiltinRule("Subscriptions", r"openai|cursor|netflix|spotify|adobe|apple\.com/bill", 20),
    BuiltinRule("Taxes & Fees", r"finanzamt|kfz.?steuer|einkommenssteuer|rundfunkbeitrag|beitragsservice", 20),
    BuiltinRule("Travel & Vacation", r"booking\.com|\bairbnb\b|\bhotel\b|ferienwohnung|ferienhaus|\bhostel\b|lufthansa|ryanair|easyjet|eurowings|air.?france|\bklm\b|swiss.?air|opodo|expedia|hotels\.com|marriott|hilton|\bibis\b|accor|reiseb[uü]ro|check24.?reise", 21),
    BuiltinRule("Sports & Fitness", r"fitness.?first|mcfit|clever.?fit|urban.?sports|sportverein|\bgym\b|decathlon", 22),
    BuiltinRule("Gifts & Donations", r"\bspende\b|unicef|\bdrk\b|sos.?kinderdorf|betterplace", 22),
    BuiltinRule("Groceries", r"rewe|aldi|lidl|edeka|penny|denn.?s|biomarkt|tchibo|kaufland|\bnetto\b", 25),
    BuiltinRule("Transport", r"db vertrieb|deutsche bahn|vw-?bank|oil\.\d|rastanlage|tankstelle|flixbus|easypark", 25),
    BuiltinRule("Healthcare", r"apotheke|arzt|zahnarzt", 25),
    BuiltinRule("Cash", r"bargeld|geldautomat|\batm\b|barauszahlung|sb-?auszahlung|cash.?withdraw", 22),
    BuiltinRule("Dining Out", r"peter\.?pane|restaurant|mission\.?coffee|eurest|\bmeny\.|circle\.?k|kala\.?bar|baecker|bäcker|sehne\.backwaren", 30),
    BuiltinRule("Shopping", r"obi\.sagt|\bzara\b|tk\.?maxx|dm\.drogerie|vinted|amazon|ikea|buchstae|\bh&m\b", 30),
    BuiltinRule("Entertainment", r"\bkino\b|cinema", 40),
]


def normalize_iban(iban: str | None) -> str:
    return re.sub(r"\s+", "", iban or "").upper()


def extract_ibans(*texts: str) -> set[str]:
    found: set[str] = set()
    for text in texts:
        found.update(m.group(0).upper() for m in IBAN_RE.finditer(text or ""))
    return found


def holder_name_after_iban(text: str | None) -> str:
    match = IBAN_RE.search(text or "")
    if not match:
        return ""
    return re.sub(r"\s+", " ", (text or "")[match.end() :]).strip()


def collect_own_holder_names(transactions: list[Transaction], own_ibans: set[str]) -> set[str]:
    """Names that appear on transfers to/from already-linked IBANs (e.g. 'Andre Theile')."""
    names: set[str] = set()
    for tx in transactions:
        mentioned = extract_ibans(tx.counterparty, tx.description, tx.reference)
        if not (mentioned & own_ibans):
            continue
        raw = holder_name_after_iban(tx.counterparty).lower()
        if not raw:
            continue
        names.add(raw)
        parts = raw.split()
        if len(parts) >= 2:
            names.add(" ".join(parts[:2]))
    return {n for n in names if len(n) >= 8}


def is_internal_transfer(
    tx: Transaction,
    own_ibans: set[str],
    source_iban: str,
    own_names: set[str] | None = None,
) -> bool:
    """True when the counterparty is another of the user's accounts (linked or same holder)."""
    mentioned = extract_ibans(tx.counterparty, tx.description, tx.reference)
    if (mentioned & own_ibans) - {source_iban}:
        return True
    if not own_names or not mentioned:
        return False
    name = holder_name_after_iban(tx.counterparty).lower()
    return bool(name) and any(token in name for token in own_names)


def is_depot_leg(
    tx: Transaction,
    depot_ibans: set[str],
    source_iban: str,
) -> bool:
    """True when this booking is to or from a marked depot account."""
    if not depot_ibans:
        return False
    if source_iban in depot_ibans:
        return True
    mentioned = extract_ibans(tx.counterparty, tx.description, tx.reference)
    return bool(mentioned & depot_ibans)


def is_cashflow_relevant(
    tx: Transaction,
    category: Category | None,
    household_ibans: set[str] | None = None,
) -> bool:
    """Whether a booking counts toward household income/expense.

    Manual excludes always drop out. Transfers between two household accounts
    are ignored so money is not counted twice. Money arriving from a personal
    (non-household) account counts as household income. Money sent back to a
    personal account is not treated as spending.
    """
    if getattr(tx, "exclude_from_totals", False):
        return False

    is_internal = category is not None and category.name == TRANSFER_CATEGORY
    if is_internal:
        mentioned = extract_ibans(tx.counterparty, tx.description, tx.reference)
        counterpart_is_household = bool(household_ibans and (mentioned & household_ibans))
        if counterpart_is_household:
            return False
        return float(tx.amount) > 0

    if category is not None and category.direction == "transfer":
        return False

    return True


def _search_text(tx: Transaction, field: str) -> str:
    if field == "any":
        return f"{tx.description} {tx.counterparty} {tx.reference}"
    return str(getattr(tx, field, "") or "")


async def classify_transaction(
    session: AsyncSession,
    tx: Transaction,
    user_id: uuid.UUID,
    *,
    own_ibans: set[str] | None = None,
    source_iban: str | None = None,
    own_names: set[str] | None = None,
    categories_by_name: dict[str, Category] | None = None,
    depot_ibans: set[str] | None = None,
) -> uuid.UUID | None:
    """Classify a transaction using transfers, user rules, then built-in merchant rules.

    Returns the matched category_id, or None if no rule matches (uncategorized).
    """
    if tx.is_manually_classified and tx.category_id is not None:
        return tx.category_id

    loaded_depot: set[str] = set()
    if own_ibans is None or source_iban is None:
        own_ibans, iban_by_account, loaded_depot = await _own_ibans(session, user_id)
        source_iban = iban_by_account.get(tx.account_id, "")
    if depot_ibans is None:
        depot_ibans = loaded_depot

    if categories_by_name is None:
        categories_by_name = await _system_categories(session)

    if is_internal_transfer(tx, own_ibans, source_iban, own_names):
        if is_depot_leg(tx, depot_ibans, source_iban):
            depot = categories_by_name.get(DEPOT_CATEGORY)
            if depot is not None:
                return depot.id
        transfer = categories_by_name.get(TRANSFER_CATEGORY)
        if transfer is not None:
            return transfer.id

    stmt = (
        select(ClassificationRule)
        .where(
            ClassificationRule.user_id == user_id,
            ClassificationRule.is_active.is_(True),
        )
        .order_by(ClassificationRule.priority.asc())
    )
    result = await session.execute(stmt)
    for rule in result.scalars().all():
        if _matches(tx, rule):
            logger.debug(
                "Transaction '%s' matched rule '%s' → category %s",
                tx.description[:50],
                rule.value,
                rule.category_id,
            )
            return rule.category_id

    blob = _search_text(tx, "any")
    for rule in BUILTIN_RULES:
        if re.search(rule.pattern, blob, re.IGNORECASE):
            cat = categories_by_name.get(rule.category_name)
            if cat is not None:
                return cat.id

    return None


def _matches(tx: Transaction, rule: ClassificationRule) -> bool:
    """Check if a transaction matches a classification rule."""
    field_value = _search_text(tx, rule.field)

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
    own_ibans, iban_by_account, depot_ibans = await _own_ibans(session, user_id)
    categories_by_name = await _system_categories(session)
    own_names = collect_own_holder_names(transactions, own_ibans)
    results: dict[uuid.UUID, uuid.UUID | None] = {}
    for tx in transactions:
        results[tx.id] = await classify_transaction(
            session,
            tx,
            user_id,
            own_ibans=own_ibans,
            source_iban=iban_by_account.get(tx.account_id, ""),
            own_names=own_names,
            categories_by_name=categories_by_name,
            depot_ibans=depot_ibans,
        )
    return results


async def reclassify_user_transactions(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Apply auto-classification to all non-manual transactions for a user."""
    own_ibans, iban_by_account, depot_ibans = await _own_ibans(session, user_id)
    if not iban_by_account:
        stmt_acc = select(Account.id).where(Account.user_id == user_id)
        account_ids = list((await session.execute(stmt_acc)).scalars().all())
    else:
        account_ids = list(iban_by_account.keys())
    if not account_ids:
        return 0

    categories_by_name = await _system_categories(session)
    all_stmt = select(Transaction).where(Transaction.account_id.in_(account_ids))
    all_txs = list((await session.execute(all_stmt)).scalars().all())
    own_names = collect_own_holder_names(all_txs, own_ibans)
    txs = [tx for tx in all_txs if not tx.is_manually_classified]
    updated = 0
    for tx in txs:
        source_iban = iban_by_account.get(tx.account_id, "")
        matched = await classify_transaction(
            session,
            tx,
            user_id,
            own_ibans=own_ibans,
            source_iban=source_iban,
            own_names=own_names,
            categories_by_name=categories_by_name,
            depot_ibans=depot_ibans,
        )
        changed = False
        if matched is not None and tx.category_id != matched:
            tx.category_id = matched
            changed = True
        if is_internal_transfer(tx, own_ibans, source_iban, own_names):
            if tx.exclude_from_totals:
                tx.exclude_from_totals = False
                changed = True
        if changed:
            updated += 1
    await session.flush()
    logger.info("Reclassified %d transactions for user %s", updated, user_id)
    return updated


async def reclassify_all_users(session: AsyncSession) -> int:
    stmt = select(Account.user_id).distinct()
    user_ids = list((await session.execute(stmt)).scalars().all())
    total = 0
    for user_id in user_ids:
        total += await reclassify_user_transactions(session, user_id)
    return total


async def _own_ibans(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[set[str], dict[uuid.UUID, str], set[str]]:
    stmt = select(Account).where(Account.user_id == user_id, Account.is_active.is_(True))
    accounts = list((await session.execute(stmt)).scalars().all())
    iban_by_account: dict[uuid.UUID, str] = {}
    own: set[str] = set()
    depot: set[str] = set()
    for acc in accounts:
        iban = normalize_iban(acc.iban)
        if iban:
            own.add(iban)
            iban_by_account[acc.id] = iban
            if acc.is_depot:
                depot.add(iban)
        else:
            iban_by_account[acc.id] = ""
    return own, iban_by_account, depot


async def _system_categories(session: AsyncSession) -> dict[str, Category]:
    cats = list((await session.execute(select(Category))).scalars().all())
    by_name: dict[str, Category] = {}
    for cat in sorted(cats, key=lambda c: c.user_id is not None):
        by_name.setdefault(cat.name, cat)
    return by_name


# ── Default category seed data ────────────────────────────

DEFAULT_CATEGORIES = [
    {"name": "Salary", "direction": "income", "icon": "💰", "sort_order": 1},
    {"name": "Freelance", "direction": "income", "icon": "💼", "sort_order": 2},
    {"name": "Other Income", "direction": "income", "icon": "💵", "sort_order": 3},
    {"name": "Rent & Housing", "direction": "expense", "icon": "🏠", "sort_order": 10},
    {"name": "Groceries", "direction": "expense", "icon": "🛒", "sort_order": 11},
    {"name": "Transport", "direction": "expense", "icon": "🚗", "sort_order": 12},
    {"name": "Dining Out", "direction": "expense", "icon": "🍽️", "sort_order": 13},
    {"name": "Travel & Vacation", "direction": "expense", "icon": "✈️", "sort_order": 14},
    {"name": "Entertainment", "direction": "expense", "icon": "🎬", "sort_order": 15},
    {"name": "Subscriptions", "direction": "expense", "icon": "📱", "sort_order": 16},
    {"name": "Sports & Fitness", "direction": "expense", "icon": "🏋️", "sort_order": 17},
    {"name": "Healthcare", "direction": "expense", "icon": "🏥", "sort_order": 18},
    {"name": "Insurance", "direction": "expense", "icon": "🛡️", "sort_order": 19},
    {"name": "Utilities", "direction": "expense", "icon": "⚡", "sort_order": 20},
    {"name": "Shopping", "direction": "expense", "icon": "🛍️", "sort_order": 21},
    {"name": "Education", "direction": "expense", "icon": "📚", "sort_order": 22},
    {"name": "Gifts & Donations", "direction": "expense", "icon": "🎁", "sort_order": 23},
    {"name": "Taxes & Fees", "direction": "expense", "icon": "🧾", "sort_order": 24},
    {"name": "Cash", "direction": "expense", "icon": "💶", "sort_order": 25},
    {"name": "Other Expense", "direction": "expense", "icon": "❓", "sort_order": 99},
    {"name": "Depot Transfer", "direction": "transfer", "icon": "🏦", "sort_order": 30},
    {"name": "Savings & Investments", "direction": "transfer", "icon": "📈", "sort_order": 31},
    {"name": "Internal Transfer", "direction": "transfer", "icon": "🔄", "sort_order": 32},
]


async def seed_default_categories(session: AsyncSession) -> int:
    """Insert missing system default categories (user_id=NULL)."""
    existing = await session.execute(
        select(Category).where(Category.user_id.is_(None))
    )
    existing_names = {c.name for c in existing.scalars().all()}

    count = 0
    for cat_data in DEFAULT_CATEGORIES:
        if cat_data["name"] in existing_names:
            continue
        session.add(Category(user_id=None, **cat_data))
        count += 1

    if count:
        await session.flush()
        logger.info("Seeded %d default categories", count)
    return count
