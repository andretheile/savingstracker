"""Google household auth: isolation, invites, and bootstrap claim."""

from __future__ import annotations

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
from src.accounts.service import create_account
from src.auth.dependencies import get_current_user
from src.auth.service import create_household_invite, delete_household, resolve_google_user
from src.config import settings
from src.core.base_model import Base
from src.core.dependencies import get_db
from src.main import app
from src.users.models import User
from src.users.service import get_or_create_default_user, get_user_by_id


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_api_requires_login(async_session: AsyncSession):
    async def _override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await client.get("/api/health")
        assert health.status_code == 200
        me = await client.get("/api/users/me")
        assert me.status_code == 401
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_household_cannot_read_another_users_kpis(async_session: AsyncSession):
    alice = User(name="Alice")
    bob = User(name="Bob")
    async_session.add_all([alice, bob])
    await async_session.flush()

    async def _override_get_db():
        yield async_session

    async def _override_user():
        return alice

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        denied = await client.get(
            f"/api/kpis/{bob.id}?period_start=2026-08-01&period_end=2026-08-31"
        )
        assert denied.status_code == 403
        ok = await client.get(
            f"/api/kpis/{alice.id}?period_start=2026-08-01&period_end=2026-08-31"
        )
        assert ok.status_code == 200
        listed = await client.get("/api/banking/accounts")
        assert listed.status_code == 200
        assert listed.json() == []
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invite_joins_existing_household(async_session: AsyncSession):
    alice = await resolve_google_user(
        async_session, email="alice@example.com", name="Alice", picture=None, google_sub="a"
    )
    await create_household_invite(async_session, alice.id, "bob@example.com", "alice@example.com")
    bob = await resolve_google_user(
        async_session, email="bob@example.com", name="Bob", picture=None, google_sub="b"
    )
    assert bob.id == alice.id


@pytest.mark.asyncio
async def test_new_google_email_gets_own_household(async_session: AsyncSession):
    alice = await resolve_google_user(
        async_session, email="alice@example.com", name="Alice", picture=None, google_sub="a"
    )
    carol = await resolve_google_user(
        async_session, email="carol@example.com", name="Carol", picture=None, google_sub="c"
    )
    assert carol.id != alice.id


@pytest.mark.asyncio
async def test_first_login_claims_existing_user(async_session: AsyncSession):
    existing = await get_or_create_default_user(async_session)
    await create_account(async_session, existing.id, "Giro", initial_balance=10)
    claimed = await resolve_google_user(
        async_session, email="andre@example.com", name="Andre", picture=None, google_sub="x"
    )
    assert claimed.id == existing.id
    second = await resolve_google_user(
        async_session, email="other@example.com", name="Other", picture=None, google_sub="y"
    )
    assert second.id != existing.id


def _session_cookie(user_id, email: str, name: str = "Admin") -> str:
    import json
    from base64 import b64encode

    from itsdangerous import TimestampSigner

    secret = settings.auth_secret_key or "dev-only-change-me"
    payload = {
        "user": {
            "user_id": str(user_id),
            "email": email,
            "name": name,
            "picture": None,
        }
    }
    data = b64encode(json.dumps(payload).encode("utf-8"))
    return TimestampSigner(str(secret)).sign(data).decode("utf-8")


@pytest.mark.asyncio
async def test_admin_can_list_and_delete_other_household(async_session: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "alice@example.com")
    alice = await resolve_google_user(
        async_session, email="alice@example.com", name="Alice", picture=None, google_sub="a"
    )
    carol = await resolve_google_user(
        async_session, email="carol@example.com", name="Carol", picture=None, google_sub="c"
    )
    await create_account(async_session, carol.id, "Carol Giro", initial_balance=5)
    await async_session.flush()

    async def _override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    cookies = {"session": _session_cookie(alice.id, "alice@example.com", "Alice")}
    async with AsyncClient(transport=transport, base_url="http://testserver", cookies=cookies) as client:
        me = await client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["is_admin"] is True

        listed = await client.get("/api/admin/households")
        assert listed.status_code == 200
        rows = listed.json()
        assert {row["emails"][0] for row in rows} == {"alice@example.com", "carol@example.com"}
        carol_row = next(row for row in rows if "carol@example.com" in row["emails"])
        assert carol_row["account_count"] == 1
        assert carol_row["is_current"] is False

        denied_self = await client.delete(f"/api/admin/households/{alice.id}")
        assert denied_self.status_code == 400

        deleted = await client.delete(f"/api/admin/households/{carol.id}")
        assert deleted.status_code == 200

        remaining = await client.get("/api/admin/households")
        assert [row["emails"] for row in remaining.json()] == [["alice@example.com"]]

    leftover = await get_user_by_id(async_session, carol.id)
    assert leftover is None
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_non_admin_cannot_list_households(async_session: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "alice@example.com")
    bob = await resolve_google_user(
        async_session, email="bob@example.com", name="Bob", picture=None, google_sub="b"
    )

    async def _override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    cookies = {"session": _session_cookie(bob.id, "bob@example.com", "Bob")}
    async with AsyncClient(transport=transport, base_url="http://testserver", cookies=cookies) as client:
        me = await client.get("/api/auth/me")
        assert me.json()["is_admin"] is False
        listed = await client.get("/api/admin/households")
        assert listed.status_code == 403
        wiped = await client.delete(f"/api/admin/households/{bob.id}")
        assert wiped.status_code == 403
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_household_refuses_self(async_session: AsyncSession):
    alice = await resolve_google_user(
        async_session, email="alice@example.com", name="Alice", picture=None, google_sub="a"
    )
    with pytest.raises(ValueError, match="own household"):
        await delete_household(async_session, alice.id, acting_user_id=alice.id)
