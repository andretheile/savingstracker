"""Unit tests for classification rule engine and default category seeding."""

import pytest
import uuid
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.core.base_model import Base
import src.users.models  # noqa
import src.accounts.models  # noqa
import src.transactions.models  # noqa
import src.classification.models  # noqa

from src.classification.models import Category, ClassificationRule
from src.classification.service import (
    classify_transaction,
    classify_batch,
    seed_default_categories,
    _matches,
)
from src.transactions.models import Transaction


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_matches_rule_operators():
    tx = Transaction(
        account_id=uuid.uuid4(),
        transaction_date=date.today(),
        amount=-150.50,
        description="REWE Supermarkt Einkauf",
        counterparty="REWE Sagstetter",
        reference="EC 123456",
    )

    # 1. contains
    r_contains = ClassificationRule(field="description", operator="contains", value="rewe")
    assert _matches(tx, r_contains) is True

    # 2. equals
    r_equals = ClassificationRule(field="counterparty", operator="equals", value="rewe sagstetter")
    assert _matches(tx, r_equals) is True

    # 3. regex
    r_regex = ClassificationRule(field="description", operator="regex", value=r"REWE|ALDI")
    assert _matches(tx, r_regex) is True

    # 4. invalid regex
    r_bad_regex = ClassificationRule(field="description", operator="regex", value="[invalid")
    assert _matches(tx, r_bad_regex) is False

    # 5. gt / lt (amount is -150.50)
    r_lt = ClassificationRule(field="amount", operator="lt", value="-100")
    assert _matches(tx, r_lt) is True

    r_gt = ClassificationRule(field="amount", operator="gt", value="0")
    assert _matches(tx, r_gt) is False

    # Bad numeric value
    r_bad_num = ClassificationRule(field="amount", operator="gt", value="abc")
    assert _matches(tx, r_bad_num) is False

    # 6. unknown operator
    r_unknown = ClassificationRule(field="description", operator="foo", value="bar")
    assert _matches(tx, r_unknown) is False


@pytest.mark.asyncio
async def test_classify_and_batch(async_session: AsyncSession):
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()

    rule = ClassificationRule(
        user_id=user_id,
        category_id=cat_id,
        field="description",
        operator="contains",
        value="salary",
        priority=1,
        is_active=True,
    )
    async_session.add(rule)
    await async_session.flush()

    tx1 = Transaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=date.today(),
        amount=3000.0,
        description="Monthly Salary Payment",
    )
    tx2 = Transaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=date.today(),
        amount=-50.0,
        description="Coffee Shop",
    )
    tx_manual = Transaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        transaction_date=date.today(),
        amount=100.0,
        description="Manual TX",
        category_id=cat_id,
        is_manually_classified=True,
    )

    # Classify single
    res1 = await classify_transaction(async_session, tx1, user_id)
    assert res1 == cat_id

    res2 = await classify_transaction(async_session, tx2, user_id)
    assert res2 is None

    res_manual = await classify_transaction(async_session, tx_manual, user_id)
    assert res_manual == cat_id

    # Classify batch
    batch_res = await classify_batch(async_session, [tx1, tx2, tx_manual], user_id)
    assert batch_res[tx1.id] == cat_id
    assert batch_res[tx2.id] is None
    assert batch_res[tx_manual.id] == cat_id

    # Duplicate seed test
    cnt1 = await seed_default_categories(async_session)
    assert cnt1 > 0
    cnt2 = await seed_default_categories(async_session)
    assert cnt2 == 0
