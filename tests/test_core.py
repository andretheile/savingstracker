"""Unit tests for core functionality — security encryption, cache, and database helpers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.config import Settings
from src.core.cache import (
    cache_get,
    cache_invalidate,
    cache_set,
    close_redis,
    rate_limit_check,
)
from src.core.database import dispose_engine, get_session, get_standalone_session
from src.core.dependencies import get_db
from src.core.security import _get_fernet, decrypt_field, encrypt_field


@pytest.fixture(autouse=True)
def setup_encryption_key():
    from src.config import settings
    from src.core import security
    key = Fernet.generate_key().decode()
    settings.encryption_key = key
    security._fernet = Fernet(key.encode())


def test_config_settings():
    s = Settings(
        database_url="postgresql+asyncpg://usr:pwd@host:5432/db",
        encryption_key="testkey",
    )
    assert "postgresql+psycopg2" in s.sync_database_url
    assert s.openrouter_model


def test_persist_env_value(tmp_path, monkeypatch):
    import src.core.envfile as envfile
    from src.config import settings
    from src.core.envfile import persist_env_value

    env = tmp_path / ".env"
    env.write_text("FOO=1\n")
    monkeypatch.setattr(envfile, "_ENV_PATH", env)
    old = settings.openrouter_api_key
    try:
        persist_env_value("OPENROUTER_API_KEY", "sk-test-key")
        text = env.read_text()
        assert "OPENROUTER_API_KEY=sk-test-key" in text
        assert settings.openrouter_api_key == "sk-test-key"
        persist_env_value("OPENROUTER_API_KEY", "sk-replaced")
        assert env.read_text().count("OPENROUTER_API_KEY=") == 1
        assert "sk-replaced" in env.read_text()
    finally:
        settings.openrouter_api_key = old


def test_security_encryption_decryption():
    test_str = "secret_bank_login_123"
    encrypted = encrypt_field(test_str)
    assert encrypted != test_str
    decrypted = decrypt_field(encrypted)
    assert decrypted == test_str


def test_security_invalid_decryption():
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_field("invalid_ciphertext_base64_blob==")


def test_security_missing_key():
    from src.core import security
    old_key = security.settings.encryption_key
    old_fernet = security._fernet
    try:
        security._fernet = None
        security.settings.encryption_key = ""
        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY is not set"):
            _get_fernet()
    finally:
        security.settings.encryption_key = old_key
        security._fernet = old_fernet


@pytest.mark.asyncio
async def test_cache_helpers():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=[
        '{"foo": "bar"}',  # JSON test
        'raw_string',      # Non-JSON test
        None,               # Miss test
        '0',                # rate_limit initial
    ])

    async def mock_scan_iter(match=None):
        yield "k1"
        yield "k2"

    mock_redis.scan_iter = mock_scan_iter
    mock_redis.delete = AsyncMock(return_value=2)
    mock_redis.set = AsyncMock(return_value=True)

    mock_pipe = MagicMock()
    mock_pipe.incr = MagicMock()
    mock_pipe.expire = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[1, True])
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    with patch("src.core.cache.get_redis", return_value=mock_redis):
        # 1. JSON get
        res1 = await cache_get("key1")
        assert res1 == {"foo": "bar"}

        # 2. Non-JSON get
        res2 = await cache_get("key2")
        assert res2 == "raw_string"

        # 3. Cache miss
        res3 = await cache_get("key3")
        assert res3 is None

        # 4. Cache set
        await cache_set("key1", {"foo": "bar"}, ttl_seconds=100)

        # 5. Invalidate
        deleted = await cache_invalidate("pattern:*")
        assert deleted == 2

        # 6. Rate limit check allowed
        allowed = await rate_limit_check("limit:user1", max_calls=5, window_seconds=60)
        assert allowed is True

        # 7. Rate limit check blocked
        mock_redis.get = AsyncMock(return_value="5")
        blocked = await rate_limit_check("limit:user1", max_calls=5, window_seconds=60)
        assert blocked is False

    # Close redis test
    from src.core import cache
    cache._pool = mock_redis
    await close_redis()
    assert cache._pool is None


@pytest.mark.asyncio
async def test_database_and_dependencies():
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    class MockCM:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, *args):
            pass

    mock_factory = MagicMock(side_effect=lambda: MockCM())

    with patch("src.core.database.async_session_factory", mock_factory), \
         patch("src.core.dependencies.async_session_factory", mock_factory):
        async for session in get_session():
            assert session == mock_session

        async with get_standalone_session() as session:
            assert session == mock_session

        async for session in get_db():
            assert session == mock_session

    mock_engine = AsyncMock()
    with patch("src.core.database.engine", mock_engine):
        await dispose_engine()
        mock_engine.dispose.assert_called_once()
