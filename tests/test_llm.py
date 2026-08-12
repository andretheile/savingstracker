"""Tests for OpenRouter LLM tools, agent loop, and Telegram chat wiring."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.accounts.models  # noqa
import src.banking.models  # noqa
import src.classification.models  # noqa
import src.kpis.models  # noqa
import src.projections.models  # noqa
import src.transactions.models  # noqa
import src.users.models  # noqa
from src.accounts.service import create_account
from src.classification.service import seed_default_categories
from src.core.base_model import Base
from src.core.dependencies import get_db
from src.llm.agent import clear_history, run_agent
from src.llm.tools import execute_tool
from src.main import app
from src.telegram_bot.handlers.chat import chat_handler, split_telegram
from src.users.service import get_or_create_user_by_telegram_id


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
async def client(async_session: AsyncSession):
    async def _override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


def _parse(raw: str) -> dict:
    return json.loads(raw)


@pytest.mark.asyncio
async def test_llm_tools_accounts_and_transactions(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, 4242, "Andre")
    joint = await create_account(
        async_session, user.id, "Joint Giro", iban="DE36120300001205941121", initial_balance=1000
    )
    personal = await create_account(
        async_session, user.id, "Personal", iban="DE36120300001085715538", initial_balance=200
    )
    await seed_default_categories(async_session)
    await async_session.commit()

    accounts = _parse(await execute_tool(async_session, user.id, "list_accounts", {}))
    assert len(accounts) == 2

    flagged = _parse(
        await execute_tool(
            async_session,
            user.id,
            "set_household_account",
            {"account": "5538", "include": False},
        )
    )
    assert flagged["household"] is False
    assert flagged["name"] == "Personal"

    added = _parse(
        await execute_tool(
            async_session,
            user.id,
            "add_transaction",
            {
                "account": "1121",
                "date": date.today().isoformat(),
                "amount": -850,
                "description": "Rent August",
                "counterparty": "Landlord",
                "category": "Rent & Housing",
            },
        )
    )
    assert added["amount"] == -850
    assert added["category"] == "Rent & Housing"
    tx_id = added["id"]

    listed = _parse(
        await execute_tool(
            async_session,
            user.id,
            "list_transactions",
            {"search": "rent", "household_only": True},
        )
    )
    assert listed["count"] == 1

    recat = _parse(
        await execute_tool(
            async_session,
            user.id,
            "set_transaction_category",
            {"transaction_id": tx_id, "category": "Utilities"},
        )
    )
    assert recat["category"] == "Utilities"

    excluded = _parse(
        await execute_tool(
            async_session,
            user.id,
            "set_transaction_exclude",
            {"transaction_id": tx_id, "exclude": True},
        )
    )
    assert excluded["excluded"] is True

    sheet = _parse(await execute_tool(async_session, user.id, "get_balance_sheet", {}))
    assert "net_cashflow" in sheet

    unknown = _parse(await execute_tool(async_session, user.id, "nope", {}))
    assert "error" in unknown
    assert joint.id and personal.id


@pytest.mark.asyncio
async def test_llm_agent_tool_loop(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, 4343, "Andre")
    await create_account(async_session, user.id, "Joint Giro", iban="DE36120300001205941121")
    await async_session.commit()

    calls = {"n": 0}

    async def fake_completion(messages, tools=None, model=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "list_accounts", "arguments": "{}"},
                    }
                ],
            }
        return {"role": "assistant", "content": "Joint Giro is in household view."}

    clear_history(999)
    with patch("src.llm.agent.chat_completion", side_effect=fake_completion):
        reply = await run_agent(async_session, user.id, "Which accounts are household?", 999)
    assert "Joint Giro" in reply
    assert calls["n"] == 2
    clear_history(999)


@pytest.mark.asyncio
async def test_agent_emits_thinking_and_tool_events(async_session: AsyncSession):
    from src.llm.agent import iter_agent_events, major_thinking_points

    points = major_thinking_points(
        "I should look at household accounts first.\n\nThen I can answer with the giro balance."
    )
    assert len(points) >= 1

    user = await get_or_create_user_by_telegram_id(async_session, 4444, "Andre")
    await create_account(async_session, user.id, "Joint Giro", iban="DE36120300001205941121")
    await async_session.commit()

    calls = {"n": 0}

    async def fake_completion(messages, tools=None, model=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "role": "assistant",
                "content": "",
                "reasoning": "I will list accounts to see which ones are household.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "list_accounts", "arguments": "{}"},
                    }
                ],
            }
        return {"role": "assistant", "content": "Joint Giro is in household view."}

    clear_history("events-1")
    events = []
    with patch("src.llm.agent.chat_completion", side_effect=fake_completion):
        async for event in iter_agent_events(
            async_session, user.id, "Which accounts are household?", "events-1"
        ):
            events.append(event)
    types = [event["type"] for event in events]
    assert "thinking" in types
    assert "tool" in types
    assert "tool_result" in types
    assert types[-1] == "reply"
    assert "Joint Giro" in events[-1]["content"]
    clear_history("events-1")


def test_split_telegram_chunks():
    text = ("hello\n" * 900)
    chunks = split_telegram(text, limit=400)
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")


@pytest.mark.asyncio
async def test_chat_handler_requires_openrouter_key(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, 555111, "Bot User")
    assert user.telegram_id == 555111

    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 555111
    update.effective_chat = MagicMock()
    update.effective_chat.id = 555111
    update.effective_chat.type = "private"
    update.effective_message = MagicMock()
    update.effective_message.text = "How much did we spend on groceries?"
    reply = AsyncMock()
    update.effective_message.reply_text = reply

    @asynccontextmanager
    async def mock_standalone():
        yield async_session

    with (
        patch("src.telegram_bot.handlers.chat.settings.openrouter_api_key", ""),
        patch(
            "src.telegram_bot.handlers.common.get_standalone_session",
            side_effect=mock_standalone,
        ),
    ):
        await chat_handler(update, MagicMock())

    reply.assert_awaited()
    assert "OpenRouter" in reply.await_args.args[0]


def test_group_addressing_helpers():
    from src.telegram_bot.handlers.chat import bot_was_addressed, strip_bot_mention

    assert strip_bot_mention("@SavingsBot rent this month?", "SavingsBot") == "rent this month?"

    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.type = "supergroup"
    update.effective_message = MagicMock()
    update.effective_message.text = "what did we spend on groceries?"
    update.effective_message.entities = []
    update.effective_message.reply_to_message = None
    context = MagicMock()
    context.bot.username = "SavingsBot"
    context.bot.id = 42
    assert bot_was_addressed(update, context) is False

    mention = MagicMock()
    mention.type = "mention"
    mention.offset = 0
    mention.length = len("@SavingsBot")
    update.effective_message.text = "@SavingsBot what did we spend on groceries?"
    update.effective_message.entities = [mention]
    assert bot_was_addressed(update, context) is True

    update.effective_message.entities = []
    reply_from = MagicMock()
    reply_from.id = 42
    update.effective_message.reply_to_message = MagicMock()
    update.effective_message.reply_to_message.from_user = reply_from
    assert bot_was_addressed(update, context) is True


@pytest.mark.asyncio
async def test_group_chat_ignores_unaddressed_messages(async_session: AsyncSession):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 555111
    update.effective_chat = MagicMock()
    update.effective_chat.type = "supergroup"
    update.effective_message = MagicMock()
    update.effective_message.text = "what should we cook tonight?"
    update.effective_message.entities = []
    update.effective_message.reply_to_message = None
    reply = AsyncMock()
    update.effective_message.reply_text = reply
    context = MagicMock()
    context.bot.username = "SavingsBot"
    context.bot.id = 42
    await chat_handler(update, context)
    reply.assert_not_awaited()


@pytest.mark.asyncio
async def test_group_chat_replies_when_mentioned(async_session: AsyncSession):
    await get_or_create_user_by_telegram_id(async_session, 555111, "Bot User")
    mention = MagicMock()
    mention.type = "mention"
    mention.offset = 0
    mention.length = len("@SavingsBot")

    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 555111
    update.effective_user.first_name = "Andre"
    update.effective_user.username = "andre"
    update.effective_chat = MagicMock()
    update.effective_chat.id = -1001
    update.effective_chat.type = "supergroup"
    update.effective_message = MagicMock()
    update.effective_message.text = "@SavingsBot grocery spend?"
    update.effective_message.entities = [mention]
    update.effective_message.reply_to_message = None
    reply = AsyncMock()
    update.effective_message.reply_text = reply

    context = MagicMock()
    context.bot.username = "SavingsBot"
    context.bot.id = 42
    context.bot.send_chat_action = AsyncMock()

    @asynccontextmanager
    async def mock_standalone():
        yield async_session

    with (
        patch("src.telegram_bot.handlers.chat.settings.openrouter_api_key", "sk-test"),
        patch(
            "src.telegram_bot.handlers.chat.get_standalone_session",
            side_effect=mock_standalone,
        ),
        patch(
            "src.telegram_bot.handlers.common.get_standalone_session",
            side_effect=mock_standalone,
        ),
        patch(
            "src.telegram_bot.handlers.chat.run_agent",
            new_callable=AsyncMock,
            return_value="Groceries: 120",
        ),
    ):
        await chat_handler(update, context)

    reply.assert_awaited()
    assert "Groceries" in reply.await_args.args[0]


@pytest.mark.asyncio
async def test_telegram_status_includes_llm_fields(client: AsyncClient):
    res = await client.get("/api/telegram/status")
    assert res.status_code == 200
    data = res.json()
    assert "llm_configured" in data
    assert "llm_model" in data


@pytest.mark.asyncio
async def test_set_llm_config_validates_and_persists(client: AsyncClient):
    from src.config import settings

    old_key = settings.openrouter_api_key
    old_model = settings.openrouter_model
    try:
        with (
            patch("src.telegram_bot.router.validate_api_key", new_callable=AsyncMock) as validate,
            patch("src.telegram_bot.router.persist_env_value") as persist,
        ):
            res = await client.post(
                "/api/telegram/llm",
                json={
                    "api_key": "sk-or-v1-abcdefghijklmnopqrstuvwxyz",
                    "model": "openai/gpt-4o-mini",
                },
            )
            assert res.status_code == 200
            validate.assert_awaited()
            assert persist.call_count == 2
    finally:
        settings.openrouter_api_key = old_key
        settings.openrouter_model = old_model


@pytest.mark.asyncio
async def test_web_llm_chat_endpoint(client: AsyncClient, async_session: AsyncSession):
    from src.config import settings

    old_key = settings.openrouter_api_key
    try:
        settings.openrouter_api_key = ""
        status = await client.get("/api/llm/status")
        assert status.status_code == 200
        assert status.json()["configured"] is False

        blocked = await client.post("/api/llm/chat", json={"message": "hello"})
        assert blocked.status_code == 400

        settings.openrouter_api_key = "sk-test-key-not-real"

        async def fake_events(*args, **kwargs):
            yield {"type": "thinking", "content": "Checking household cashflow."}
            yield {
                "type": "tool",
                "name": "get_kpis",
                "label": "Evaluating KPIs",
                "arguments": {},
                "status": "running",
            }
            yield {
                "type": "tool_result",
                "name": "get_kpis",
                "summary": "4 items",
                "status": "done",
            }
            yield {"type": "reply", "content": "Household net is 200."}

        @asynccontextmanager
        async def mock_standalone():
            yield async_session

        with (
            patch("src.llm.router.iter_agent_events", side_effect=fake_events),
            patch("src.llm.router.get_standalone_session", side_effect=mock_standalone),
        ):
            ok = await client.post("/api/llm/chat", json={"message": "How is cashflow?"})
            assert ok.status_code == 200
            body = ok.text
            assert "Checking household cashflow." in body
            assert "get_kpis" in body
            assert "Household net is 200." in body
            assert '"type": "done"' in body

        reset = await client.post("/api/llm/reset")
        assert reset.status_code == 200
        assert reset.json()["ok"] is True
    finally:
        settings.openrouter_api_key = old_key
