"""Integration tests for service layer operations."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.accounts.models  # noqa
import src.banking.models  # noqa
import src.classification.models  # noqa
import src.kpis.models  # noqa
import src.projections.models  # noqa
import src.transactions.models  # noqa
import src.users.models  # noqa
from src.accounts.service import create_account, get_account_balance, list_user_accounts
from src.balance_sheets.service import generate_balance_sheet
from src.classification.service import seed_default_categories
from src.core.base_model import Base
from src.kpis.service import evaluate_and_save_kpis_for_user
from src.projections.service import generate_user_projection
from src.transactions.service import add_transaction, list_transactions
from src.users.service import get_or_create_user_by_telegram_id, get_user_by_id, list_active_users


@pytest.fixture
async def async_session():
    """Create in-memory SQLite async engine and session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_user_and_account_services(async_session: AsyncSession):
    # Test user creation
    user = await get_or_create_user_by_telegram_id(async_session, telegram_id=123456789, name="Test User")
    assert user.id is not None
    assert user.telegram_id == 123456789

    fetched = await get_user_by_id(async_session, user.id)
    assert fetched is not None
    assert fetched.name == "Test User"

    users = await list_active_users(async_session)
    assert len(users) == 1

    # Test account creation
    account = await create_account(
        async_session,
        user_id=user.id,
        name="Sparkasse Giro",
        iban="DE89370400440532013000",
        initial_balance=1000.0,
    )
    assert account.id is not None

    accounts = await list_user_accounts(async_session, user.id)
    assert len(accounts) == 1

    bal = await get_account_balance(async_session, account.id)
    assert float(bal) == 1000.0


@pytest.mark.asyncio
async def test_transaction_and_balance_sheet_services(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, telegram_id=987654321, name="Finance User")
    account = await create_account(async_session, user_id=user.id, name="Checking", initial_balance=500.0)

    # Seed default categories
    await seed_default_categories(async_session)

    # Add income transaction
    tx_in = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=account.id,
        tx_date=date(2026, 8, 1),
        amount=3000.0,
        description="Gehalt August",
    )
    assert tx_in.id is not None

    # Add expense transaction
    tx_out = await add_transaction(
        async_session,
        user_id=user.id,
        account_id=account.id,
        tx_date=date(2026, 8, 2),
        amount=-1000.0,
        description="Miete",
    )
    assert tx_out.id is not None

    # List transactions
    txs = await list_transactions(async_session, account_id=account.id)
    assert len(txs) == 2

    # Check updated balance
    new_bal = await get_account_balance(async_session, account.id)
    assert float(new_bal) == 2500.0  # 500 + 3000 - 1000

    # Generate balance sheet
    bs = await generate_balance_sheet(async_session, user.id, date(2026, 8, 1), date(2026, 8, 31))
    assert float(bs.total_income) == 3000.0
    assert float(bs.total_expense) == 1000.0
    assert float(bs.net_cashflow) == 2000.0


@pytest.mark.asyncio
async def test_kpis_and_projections_services(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, telegram_id=555555555, name="Investor User")
    account = await create_account(async_session, user_id=user.id, name="Broker", initial_balance=10000.0)

    await add_transaction(
        async_session,
        user_id=user.id,
        account_id=account.id,
        tx_date=date(2026, 8, 1),
        amount=4000.0,
        description="Salary",
    )
    await add_transaction(
        async_session,
        user_id=user.id,
        account_id=account.id,
        tx_date=date(2026, 8, 5),
        amount=-2000.0,
        description="Expenses",
    )

    # Evaluate KPIs
    snapshots = await evaluate_and_save_kpis_for_user(async_session, user.id, date(2026, 8, 1), date(2026, 8, 31))
    assert len(snapshots) > 0

    # Generate Projection
    proj_data, snap = await generate_user_projection(async_session, user.id, date(2026, 8, 1), date(2026, 8, 31))
    assert float(proj_data.baseline.real) > 100000.0
    assert len(proj_data.scenarios) == 5
