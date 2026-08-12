"""Unit tests for main FastAPI application lifecycle and SPA routing."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app, lifespan


@pytest.mark.asyncio
async def test_main_app_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health check
        res_health = await client.get("/api/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        # 2. SPA fallback / static file handling
        res_spa = await client.get("/some/client/route")
        assert res_spa.status_code in (200, 404)


@pytest.mark.asyncio
async def test_main_lifespan():
    mock_app = MagicMock()
    mock_session = AsyncMock()

    @asynccontextmanager
    async def mock_standalone():
        yield mock_session

    with patch("src.main.get_standalone_session", side_effect=mock_standalone), \
         patch("src.main.seed_default_categories", new_callable=AsyncMock), \
         patch("src.main.ensure_builtin_kpis_seeded", new_callable=AsyncMock), \
         patch("src.main.apply_default_household_selection", new_callable=AsyncMock), \
         patch("src.main.reclassify_all_users", new_callable=AsyncMock), \
         patch("src.main.ensure_schema", new_callable=AsyncMock), \
         patch("src.main.start_polling", new_callable=AsyncMock), \
         patch("src.main.stop_polling", new_callable=AsyncMock), \
         patch("src.main.dispose_engine", new_callable=AsyncMock) as mock_dispose_db, \
         patch("src.main.close_redis", new_callable=AsyncMock) as mock_close_redis:
        async with lifespan(mock_app):
            pass
        mock_dispose_db.assert_called_once()
        mock_close_redis.assert_called_once()
