"""Unit tests for Bank Connection service and FinTS adapter."""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.accounts.models  # noqa
import src.banking.models  # noqa
import src.transactions.models  # noqa
import src.users.models  # noqa
from src.banking.adapters.base import AuthResult, BankAccountInfo, RawTransaction
from src.banking.adapters.fints_adapter import FinTSAdapter
from src.banking.service import (
    complete_tan_sync,
    create_bank_connection,
    import_since_date,
    sync_bank_connection,
)
from src.core.base_model import Base
from src.users.service import get_or_create_user_by_telegram_id


@pytest.fixture(autouse=True)
def setup_encryption_key():
    from src.config import settings
    from src.core import security
    key = Fernet.generate_key().decode()
    settings.encryption_key = key
    security._fernet = Fernet(key.encode())


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_import_since_date_starts_previous_month():
    assert import_since_date(date(2026, 8, 12)) == date(2026, 7, 1)
    assert import_since_date(date(2026, 1, 5)) == date(2025, 12, 1)


@pytest.mark.asyncio
async def test_create_and_sync_bank_connection(async_session: AsyncSession):
    user = await get_or_create_user_by_telegram_id(async_session, 777888999, "Bank User")
    
    conn = await create_bank_connection(
        session=async_session,
        user_id=user.id,
        bank_blz="12345678",
        bank_name="Test Bank",
        fints_url="https://fints.example.com",
        login_name="user123",
    )
    assert conn.id is not None
    assert conn.bank_blz == "12345678"

    # Test sync failure on invalid conn id
    ok, msg, auth = await sync_bank_connection(async_session, uuid.uuid4(), "1234")
    assert ok is False
    assert "not found" in msg

    # Test sync rate limit
    with patch("src.banking.service.rate_limit_check", return_value=False):
        ok_rl, msg_rl, _ = await sync_bank_connection(async_session, conn.id, "1234")
        assert ok_rl is False
        assert "Rate limit" in msg_rl

    # Test successful sync without TAN
    mock_adapter = AsyncMock()
    mock_adapter.connect.return_value = AuthResult(success=True, requires_tan=False, session_data={"client": MagicMock()})
    mock_adapter.fetch_accounts.return_value = [
        BankAccountInfo(iban="DE1234567890", account_name="Giro")
    ]
    mock_adapter.fetch_transactions.return_value = [
        RawTransaction(transaction_date=date.today(), value_date=date.today(), amount=Decimal("100.00"), description="Test deposit")
    ]

    with patch("src.banking.service.FinTSAdapter", return_value=mock_adapter), \
         patch("src.banking.service.rate_limit_check", return_value=True):
        ok_s, msg_s, _ = await sync_bank_connection(async_session, conn.id, "1234")
        assert ok_s is True

    # Test TAN flow
    mock_adapter_tan = AsyncMock()
    mock_adapter_tan.connect.return_value = AuthResult(success=True, requires_tan=True, session_data={"client": MagicMock()})
    with patch("src.banking.service.FinTSAdapter", return_value=mock_adapter_tan), \
         patch("src.banking.service.rate_limit_check", return_value=True):
        ok_t, msg_t, auth_t = await sync_bank_connection(async_session, conn.id, "1234")
        assert ok_t is True
        assert auth_t.requires_tan is True

    # Complete TAN sync
    mock_adapter_tan.handle_tan.return_value = AuthResult(success=True, session_data={"client": MagicMock()})
    mock_adapter_tan.fetch_accounts.return_value = []
    with patch("src.banking.service.FinTSAdapter", return_value=mock_adapter_tan):
        ok_tan_c, msg_tan_c = await complete_tan_sync(async_session, conn.id, {"client": MagicMock()}, "999999")
        assert ok_tan_c is True


@pytest.mark.asyncio
async def test_fints_adapter_full():
    adapter = FinTSAdapter()

    # Disconnect
    await adapter.disconnect({})
    mock_client = MagicMock()
    await adapter.disconnect({"client": mock_client})

    # Mock client for connect & fetch
    client_mock = MagicMock()
    client_mock.init_tan_response = None
    sepa_acc = MagicMock()
    sepa_acc.iban = "DE999"
    sepa_acc.accountnumber = "999"
    sepa_acc.currency = "EUR"
    client_mock.get_sepa_accounts.return_value = [sepa_acc]

    stmt_mock = MagicMock()
    stmt_mock.data.date = date.today()
    stmt_mock.data.amount = Decimal("50.00")
    stmt_mock.data.purpose = "Coffee"
    stmt_mock.data.applicant_name = "Starbucks"
    stmt_mock.data.bank_reference = "Ref 12"
    client_mock.get_tan_mechanisms.return_value = {}
    client_mock.get_transactions.return_value = [stmt_mock]

    with patch("fints.client.FinTS3PinTanClient", return_value=client_mock):
        auth_res = await adapter.connect("12345678", "http://fints", "user", "pin")
        assert auth_res.success is True
        client_mock.fetch_tan_mechanisms.assert_called()
        client_mock.__enter__.assert_called()

        accounts = await adapter.fetch_accounts({"client": client_mock})
        assert len(accounts) == 1
        assert accounts[0].iban == "DE999"
        client_mock.get_balance.assert_called()

        txs = await adapter.fetch_transactions({"client": client_mock}, "DE999", date.today())
        assert len(txs) == 1
        assert txs[0].amount == Decimal("50.00")
        client_mock.get_transactions.assert_called()

        # MT940 objects store fields on .data as a dict
        class Mt940Tx:
            def __init__(self):
                self.data = {
                    "date": date.today(),
                    "amount": Decimal("-850.00"),
                    "purpose": "Miete",
                    "applicant_name": "Vermieter GmbH",
                }

        parsed = adapter._parse_transaction(Mt940Tx(), date.today())
        assert parsed is not None
        assert parsed.amount == Decimal("-850.00")
        assert parsed.description == "Miete"

        # Handle TAN
        tan_res = await adapter.handle_tan({"client": client_mock, "tan_response": "resp"}, "123456")
        assert tan_res.success is True


def test_resolve_url_rewrites_legacy_dkb():
    adapter = FinTSAdapter()
    assert adapter._resolve_url("12030000", "") == "https://fints.dkb.de/fints"
    assert adapter._resolve_url("12030000", "https://fints.banking-dkb.de/fints/") == "https://fints.dkb.de/fints"
    assert adapter._resolve_url(
        "12030000", "https://banking-dkb.s-fints-pt-dkb.de/fints30"
    ) == "https://fints.dkb.de/fints"
    assert adapter._resolve_url("10070024", "") == "https://fints.deutsche-bank.de/fints"


def test_select_tan_mechanism_prefers_dkb_app():
    adapter = FinTSAdapter()
    tan2go = MagicMock()
    tan2go.name = "TAN2Go"
    dkb_app = MagicMock()
    dkb_app.name = "DKB App"
    assert adapter._select_tan_mechanism({"921": tan2go, "940": dkb_app}) == "940"


def test_submit_tan_polls_decoupled_until_confirmed():
    adapter = FinTSAdapter()
    client = MagicMock()

    class FakeNeedTAN:
        pass

    pending = FakeNeedTAN()
    client.send_tan.side_effect = [pending, pending, "ok"]

    with patch("fints.client.NeedTANResponse", FakeNeedTAN), \
         patch("src.banking.adapters.fints_adapter.time.sleep"):
        adapter._submit_tan(client, pending, "", True)

    assert client.send_tan.call_count == 3
    client.send_tan.assert_called_with(pending, "")
