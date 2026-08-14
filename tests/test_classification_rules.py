"""Unit tests for classification rule engine and default category seeding."""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.accounts.models  # noqa
import src.banking.models  # noqa
import src.classification.models  # noqa
import src.transactions.models  # noqa
import src.users.models  # noqa
from src.classification.models import ClassificationRule
from src.classification.service import (
    _matches,
    classify_batch,
    classify_transaction,
    seed_default_categories,
)
from src.core.base_model import Base
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


def test_extract_ibans_and_internal_transfer():
    from src.classification.service import extract_ibans, is_internal_transfer

    assert extract_ibans("DE36120300001085715538Andre Theile") == {"DE36120300001085715538"}
    tx = Transaction(
        account_id=uuid.uuid4(),
        transaction_date=date.today(),
        amount=-496.0,
        description="Kreditkarte Dänemark",
        counterparty="DE36120300001205941121Andre Theile und Judith Theile",
    )
    own = {"DE36120300001085715538", "DE36120300001205941121"}
    assert is_internal_transfer(tx, own, "DE36120300001085715538") is True
    assert is_internal_transfer(tx, own, "DE36120300001205941121") is False

    car = Transaction(
        account_id=uuid.uuid4(),
        transaction_date=date.today(),
        amount=-7400.0,
        description="Auto",
        counterparty="DE11200411110173793100Andre Theile",
    )
    names = {"andre theile"}
    assert is_internal_transfer(car, own, "DE36120300001085715538", names) is True


@pytest.mark.asyncio
async def test_builtin_rules_transfers_and_exclude(async_session: AsyncSession):
    from src.accounts.service import create_account
    from src.balance_sheets.service import generate_balance_sheet
    from src.transactions.service import add_transaction
    from src.users.service import get_or_create_user_by_telegram_id

    user = await get_or_create_user_by_telegram_id(async_session, 424242, "Andre")
    await seed_default_categories(async_session)
    giro = await create_account(
        async_session, user.id, "Giro", iban="DE36120300001085715538"
    )
    joint = await create_account(
        async_session, user.id, "Joint", iban="DE36120300001205941121"
    )

    transfer = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=giro.id,
        tx_date=date(2026, 8, 6),
        amount=-496.0,
        description="Kreditkarte Dänemark",
        counterparty="DE36120300001205941121Andre Theile",
    )
    grocery = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=joint.id,
        tx_date=date(2026, 8, 10),
        amount=-18.26,
        description="VISA Debitkartenumsatz",
        counterparty="DE96120300009005290904REWE.Rainer.Czerlinski/Stuttgart",
    )
    car = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=giro.id,
        tx_date=date(2026, 8, 7),
        amount=-7400.0,
        description="Auto",
        counterparty="DE11200411110173793100Andre Theile",
    )
    car.exclude_from_totals = True
    await async_session.flush()

    assert transfer.exclude_from_totals is False
    assert grocery.category_id is not None
    assert car.exclude_from_totals is True

    bs = await generate_balance_sheet(
        async_session, user.id, date(2026, 8, 1), date(2026, 8, 31)
    )
    assert float(bs.total_expense) == pytest.approx(18.26)
    assert float(bs.total_income) == 0.0

    giro.include_in_household = False
    await async_session.flush()
    funded = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=joint.id,
        tx_date=date(2026, 8, 8),
        amount=3600.0,
        description="Urlaubsgeld + Miete + Leben",
        counterparty="DE36120300001085715538Andre Theile",
    )
    assert funded.category_id == transfer.category_id
    bs_hh = await generate_balance_sheet(
        async_session, user.id, date(2026, 8, 1), date(2026, 8, 31)
    )
    assert float(bs_hh.total_income) == pytest.approx(3600.0)
    assert float(bs_hh.total_expense) == pytest.approx(18.26)


@pytest.mark.asyncio
async def test_depot_transfer_category_and_cashflow(async_session: AsyncSession):
    from src.accounts.service import create_account
    from src.balance_sheets.service import generate_balance_sheet
    from src.classification.models import Category
    from src.transactions.service import add_transaction
    from src.users.service import get_or_create_user_by_telegram_id

    user = await get_or_create_user_by_telegram_id(async_session, 434343, "Andre")
    await seed_default_categories(async_session)
    giro = await create_account(
        async_session, user.id, "Joint Giro", iban="DE36120300001205941121"
    )
    depot = await create_account(
        async_session, user.id, "DKB Depot", iban="DE36120300009999999999"
    )
    depot.is_depot = True
    await create_account(
        async_session, user.id, "Personal Giro", iban="DE36120300001085715538"
    )
    await async_session.flush()

    cats = {
        c.name: c
        for c in (await async_session.execute(select(Category))).scalars().all()
    }

    to_depot = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=giro.id,
        tx_date=date(2026, 8, 9),
        amount=-500.0,
        description="Sparrate",
        counterparty="DE36120300009999999999Andre Theile",
    )
    from_depot = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=giro.id,
        tx_date=date(2026, 8, 10),
        amount=200.0,
        description="Depotauszahlung",
        counterparty="DE36120300009999999999Andre Theile",
    )
    between_giros = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=giro.id,
        tx_date=date(2026, 8, 11),
        amount=-50.0,
        description="Ausgleich",
        counterparty="DE36120300001085715538Andre Theile",
    )
    keyword = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=giro.id,
        tx_date=date(2026, 8, 12),
        amount=-80.0,
        description="Übertrag auf DKB Depot",
        counterparty="DKB AG",
    )

    assert to_depot.category_id == cats["Depot Transfer"].id
    assert from_depot.category_id == cats["Depot Transfer"].id
    assert between_giros.category_id == cats["Internal Transfer"].id
    assert keyword.category_id == cats["Depot Transfer"].id

    grocery = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=giro.id,
        tx_date=date(2026, 8, 13),
        amount=-18.26,
        description="REWE Einkauf",
        counterparty="REWE",
    )
    assert grocery.category_id == cats["Groceries"].id

    bs = await generate_balance_sheet(
        async_session, user.id, date(2026, 8, 1), date(2026, 8, 31)
    )
    assert float(bs.total_expense) == pytest.approx(18.26)
    assert float(bs.total_income) == 0.0


@pytest.mark.asyncio
async def test_depot_iban_registered_before_account_sync(async_session: AsyncSession):
    from src.accounts.service import create_account
    from src.classification.models import Category
    from src.classification.service import reclassify_user_transactions
    from src.transactions.service import add_transaction
    from src.users.service import get_or_create_user_by_telegram_id

    user = await get_or_create_user_by_telegram_id(async_session, 454545, "Andre")
    await seed_default_categories(async_session)
    giro = await create_account(
        async_session, user.id, "Joint Giro", iban="DE36120300001205941121"
    )
    depot_iban = "DE36120300008888888888"
    pending = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=giro.id,
        tx_date=date(2026, 8, 12),
        amount=-300.0,
        description="Erste Sparrate",
        counterparty=f"{depot_iban}Andre Theile",
    )
    cats = {
        c.name: c
        for c in (await async_session.execute(select(Category))).scalars().all()
    }
    assert pending.category_id != cats["Depot Transfer"].id

    await create_account(
        async_session,
        user.id,
        "DKB Depot",
        iban=depot_iban,
        is_depot=True,
    )
    await reclassify_user_transactions(async_session, user.id)
    await async_session.refresh(pending)
    assert pending.category_id == cats["Depot Transfer"].id

