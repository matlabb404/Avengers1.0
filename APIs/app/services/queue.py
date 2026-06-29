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

def enqueue_new_service_fanout_sync(target_id, vendor_id, is_big: bool,
                                    target_type: str | None = None,
                                    actor_name: str | None = None,
                                    preview: str | None = None) -> None:
    """
    Fire-and-forget enqueue from SYNC code (add_service / add_s). Opens a short-
    lived arq pool, enqueues, closes. Safe from a sync request handler. Never
    raises into the caller — a failed enqueue must not fail the create.

      target_id : the Service id (post) OR Add_Service id (offering)
      is_big    : True for a Service post (BIG_SERVICE), False for Add_Service (NEW_SERVICE)
      target_type: NotificationTarget.SERVICE or .OFFERING (None -> derived from is_big)
    """
    import asyncio
    from arq import create_pool

    async def _go():
        pool = await create_pool(redis_settings())
        try:
            await pool.enqueue_job(
                "fanout_new_service_task",
                str(target_id), str(vendor_id), bool(is_big), target_type,
                actor_name, preview,
            )
        finally:
            await pool.close()

    try:
        asyncio.run(_go())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(_go())
    except Exception as e:
        logger.warning("new-service fanout enqueue failed: %r", e)