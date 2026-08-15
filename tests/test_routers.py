"""Integration tests for FastAPI REST API endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.accounts.models  # noqa
import src.auth.models  # noqa
import src.banking.models  # noqa
import src.classification.models  # noqa
import src.kpis.models  # noqa
import src.projections.models  # noqa
import src.transactions.models  # noqa
import src.users.models  # noqa
from src.auth.dependencies import get_current_user
from src.core.base_model import Base
from src.core.dependencies import get_db
from src.main import app
from src.users.service import get_or_create_default_user


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def household_user(async_session: AsyncSession):
    user = await get_or_create_default_user(async_session)
    await async_session.commit()
    return user


@pytest.fixture
async def client(async_session: AsyncSession, household_user):
    async def _override_get_db():
        yield async_session

    async def _override_user():
        return household_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "service": "savingstracker"}


@pytest.mark.asyncio
async def test_telegram_status_unlinked(client: AsyncClient):
    res = await client.get("/api/telegram/status")
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is False
    assert "next_digest" in data


@pytest.mark.asyncio
async def test_users_router(client: AsyncClient, household_user):
    res_me = await client.get("/api/users/me")
    assert res_me.status_code == 200
    assert res_me.json()["id"] == str(household_user.id)

    res_forbidden = await client.post("/api/users/", json={"name": "API User", "telegram_id": 99887766})
    assert res_forbidden.status_code == 403

    res_other = await client.get(f"/api/users/{uuid.uuid4()}")
    assert res_other.status_code == 403


@pytest.mark.asyncio
async def test_accounts_router(client: AsyncClient, household_user):
    user_id = str(household_user.id)

    # Create account
    res = await client.post("/api/accounts/", json={
        "user_id": str(user_id),
        "name": "Sparkasse",
        "iban": "DE12345678901234567890",
        "initial_balance": 1000.0
    })
    assert res.status_code == 201
    acc_id = res.json()["id"]

    # Get account by ID
    res_acc = await client.get(f"/api/accounts/{acc_id}")
    assert res_acc.status_code == 200
    assert float(res_acc.json()["current_balance"]) == 1000.0

    # Get non-existent account -> 404
    res_acc_404 = await client.get(f"/api/accounts/{uuid.uuid4()}")
    assert res_acc_404.status_code == 404

    # List accounts for user
    res_list = await client.get(f"/api/accounts/user/{user_id}")
    assert res_list.status_code == 200
    accounts = res_list.json()
    assert len(accounts) == 1
    assert float(accounts[0]["current_balance"]) == 1000.0


@pytest.mark.asyncio
async def test_transactions_router(client: AsyncClient, household_user):
    user_id = str(household_user.id)
    a_res = await client.post("/api/accounts/", json={"user_id": str(user_id), "name": "Main", "initial_balance": 500.0})
    acc_id = a_res.json()["id"]

    # Add transaction
    tx_payload = {
        "user_id": str(user_id),
        "account_id": str(acc_id),
        "transaction_date": "2026-08-01",
        "amount": 2500.0,
        "description": "Gehalt",
        "counterparty": "Arbeitgeber Gmbh",
        "reference": "Ref 123"
    }
    res = await client.post("/api/transactions/", json=tx_payload)
    assert res.status_code == 201
    assert res.json()["amount"] == 2500.0

    # List transactions
    res_list = await client.get(f"/api/transactions/?account_id={acc_id}")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # Duplicate tx error -> 400
    res_dup = await client.post("/api/transactions/", json=tx_payload)
    assert res_dup.status_code == 400


@pytest.mark.asyncio
async def test_kpis_and_projections_and_balance_sheets_routers(client: AsyncClient, household_user):
    user_id = str(household_user.id)
    a_res = await client.post("/api/accounts/", json={"user_id": str(user_id), "name": "Depot", "initial_balance": 10000.0})
    acc_id = a_res.json()["id"]

    await client.post("/api/transactions/", json={
        "user_id": str(user_id),
        "account_id": str(acc_id),
        "transaction_date": "2026-08-01",
        "amount": 4000.0,
        "description": "Gehalt"
    })
    await client.post("/api/transactions/", json={
        "user_id": str(user_id),
        "account_id": str(acc_id),
        "transaction_date": "2026-08-05",
        "amount": -1500.0,
        "description": "Miete"
    })

    # Validate KPI formula endpoint
    res_val = await client.post("/api/kpis/validate", json={"formula": "pct(net_cashflow, total_income)"})
    assert res_val.status_code == 200
    assert res_val.json()["is_valid"] is True

    # 1. KPIs router
    res_kpis = await client.get(f"/api/kpis/{user_id}?period_start=2026-08-01&period_end=2026-08-31")
    assert res_kpis.status_code == 200

    # Create custom KPI
    res_new_kpi = await client.post("/api/kpis/", json={
        "user_id": str(user_id),
        "name": "Custom Savings Rate",
        "formula": "net_cashflow",
        "unit": "EUR",
        "description": "Custom rate"
    })
    assert res_new_kpi.status_code == 201

    # Bad formula -> 400
    res_bad_kpi = await client.post("/api/kpis/", json={
        "user_id": str(user_id),
        "name": "Bad Formula",
        "formula": "pct(net_cashflow, [invalid_syntax",
        "unit": "%"
    })
    assert res_bad_kpi.status_code == 400

    # 2. Projections router
    res_proj = await client.post(f"/api/projections/compute/{user_id}?period_start=2026-08-01&period_end=2026-08-31")
    assert res_proj.status_code == 200
    proj_data = res_proj.json()
    assert float(proj_data["projected_real"]) > 10000.0

    # Get projection config
    res_get_cfg = await client.get(f"/api/projections/config/{user_id}")
    assert res_get_cfg.status_code == 200

    # Update projection config
    res_up_proj = await client.put(f"/api/projections/config/{user_id}", json={
        "annual_return_pct": 8.0,
        "horizon_years": 25,
        "inflation_pct": 2.5
    })
    assert res_up_proj.status_code == 200
    assert float(res_up_proj.json()["annual_return_pct"]) == 8.0

    # 3. Balance Sheets router
    res_bs = await client.get(f"/api/balance-sheets/{user_id}?period_start=2026-08-01&period_end=2026-08-31")
    assert res_bs.status_code == 200
    bs_data = res_bs.json()
    assert float(bs_data["total_income"]) == 4000.0
    assert float(bs_data["total_expense"]) == 1500.0
    assert float(bs_data["net_cashflow"]) == 2500.0


@pytest.mark.asyncio
async def test_register_depot_iban(client: AsyncClient):
    bad = await client.post("/api/banking/depot", json={"iban": "not-an-iban"})
    assert bad.status_code == 400

    res = await client.post(
        "/api/banking/depot",
        json={"name": "DKB Depot", "iban": "DE36 1203 0000 8888 8888 88"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["is_depot"] is True
    assert data["include_in_household"] is False
    assert data["iban"] == "DE36120300008888888888"
    assert data["name"] == "DKB Depot"

    again = await client.post(
        "/api/banking/depot",
        json={"name": "DKB Depot", "iban": "DE36120300008888888888"},
    )
    assert again.status_code == 201
    assert again.json()["id"] == data["id"]

    listed = await client.get("/api/banking/accounts")
    assert listed.status_code == 200
    depots = [acc for acc in listed.json() if acc["is_depot"]]
    assert len(depots) == 1


@pytest.mark.asyncio
async def test_banking_sync_endpoints(client: AsyncClient):
    start = AsyncMock(
        return_value={"status": "needs_approval", "bank": "DKB", "message": "Approve in the app"}
    )
    confirm = AsyncMock(
        return_value={"status": "synced", "bank": "DKB", "message": "Sync completed."}
    )
    with patch("src.banking.router.start_household_sync", start):
        waiting = await client.post("/api/banking/sync")
    assert waiting.status_code == 200
    assert waiting.json()["status"] == "needs_approval"
    start.assert_awaited_once()

    with patch("src.banking.router.confirm_household_sync", confirm):
        done = await client.post("/api/banking/sync/confirm")
    assert done.status_code == 200
    assert done.json()["status"] == "synced"
    confirm.assert_awaited_once()
