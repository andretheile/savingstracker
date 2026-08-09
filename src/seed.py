"""CLI utility script to seed database with initial categories and KPI definitions."""

import asyncio
import logging

from src.classification.service import seed_default_categories
from src.core.database import get_standalone_session
from src.kpis.service import ensure_builtin_kpis_seeded

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)


async def run_seed():
    logger.info("Seeding database...")
    async with get_standalone_session() as session:
        cat_count = await seed_default_categories(session)
        logger.info("Seeded %d categories", cat_count)
        await ensure_builtin_kpis_seeded(session)
        logger.info("Seeded built-in KPIs")
    logger.info("Database seeding complete.")


if __name__ == "__main__":
    asyncio.run(run_seed())
