"""Unit tests for Classification rule matching operators."""

from decimal import Decimal
import uuid

# Ensure all SQLAlchemy models are registered
import src.accounts.models  # noqa
import src.banking.models  # noqa
import src.classification.models  # noqa
import src.kpis.models  # noqa
import src.projections.models  # noqa
import src.transactions.models  # noqa
import src.users.models  # noqa

from src.classification.models import ClassificationRule
from src.classification.service import _matches
from src.transactions.models import Transaction


def test_rule_matching_contains():
    rule = ClassificationRule(
        user_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        field="description",
        operator="contains",
        value="rewe",
    )
    tx_match = Transaction(
        account_id=uuid.uuid4(),
        transaction_date="2026-08-01",
        amount=Decimal("-45.50"),
        description="REWE Sag Danke Koeln",
    )
    tx_no_match = Transaction(
        account_id=uuid.uuid4(),
        transaction_date="2026-08-01",
        amount=Decimal("-45.50"),
        description="ALDI Sued Koeln",
    )
    assert _matches(tx_match, rule)
    assert not _matches(tx_no_match, rule)


def test_rule_matching_greater_than():
    rule = ClassificationRule(
        user_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        field="amount",
        operator="gt",
        value="1000.00",
    )
    tx_salary = Transaction(
        account_id=uuid.uuid4(),
        transaction_date="2026-08-01",
        amount=Decimal("2500.00"),
        description="Gehalt",
    )
    tx_expense = Transaction(
        account_id=uuid.uuid4(),
        transaction_date="2026-08-01",
        amount=Decimal("-50.00"),
        description="Kino",
    )
    assert _matches(tx_salary, rule)
    assert not _matches(tx_expense, rule)
