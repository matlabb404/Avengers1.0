"""
arq queue access — a shared Redis pool for enqueuing background jobs.

Place at: app/services/queue.py
"""
import logging

from arq import create_pool
from arq.connections import RedisSettings

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_pool = None


def redis_settings() -> RedisSettings:
    """Single source of truth for Redis connection — used by enqueuers AND the worker."""
    return RedisSettings.from_dsn(settings.REDIS_URL)


async def get_pool():
    """Lazy singleton arq pool, reused across requests."""
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings())
    return _pool


async def enqueue_media_processing(asset_id) -> None:
    pool = await get_pool()
    await pool.enqueue_job("process_media", str(asset_id))