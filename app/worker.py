import logging
from typing import Any
from uuid import UUID

from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import DatabaseSettings
from app.core.config import RedisSettings as AppRedisSettings
from app.core.redis import get_redis_pool
from app.infrastructure.database import create_database_engine
from app.services.dispatcher import DispatcherService
from app.services.intent_worker import MAX_ATTEMPTS as MAX_ATTEMPTS
from app.services.intent_worker import IntentWorker
from app.services.processor import IntentProcessor, IntentProcessorService

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    db_settings = DatabaseSettings()
    redis_settings = AppRedisSettings()

    engine = create_database_engine(db_settings)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    redis_pool = await get_redis_pool(redis_settings)

    ctx["engine"] = engine
    ctx["sessions"] = sessions
    ctx["redis"] = redis_pool


async def shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx["engine"]
    await engine.dispose()


async def dispatch_pending_cron(ctx: dict[str, Any]) -> None:
    """Cron job to poll for pending intents and enqueue them."""
    sessions = ctx["sessions"]
    redis = ctx["redis"]

    dispatcher = DispatcherService(sessions, redis)
    dispatched = await dispatcher.dispatch_pending()
    if dispatched > 0:
        logger.info(f"Dispatched {dispatched} pending intents to Arq.")


async def process_intent(
    ctx: dict[str, Any],
    tenant_id: UUID,
    message_id: UUID,
    *,
    processor: IntentProcessor | None = None,
) -> None:
    sessions = ctx["sessions"]
    if processor is None:
        processor = IntentProcessorService(sessions)

    await IntentWorker(sessions, processor).process(tenant_id, message_id)


class WorkerSettings:
    # Leave a margin before the five-minute database lease expires.
    job_timeout = 240
    functions = [process_intent]
    cron_jobs = [cron(dispatch_pending_cron, second=set(range(0, 60, 5)))]
    on_startup = startup
    on_shutdown = shutdown
    # For Arq to know where Redis is:
    redis_settings = RedisSettings.from_dsn(
        AppRedisSettings().redis_url.get_secret_value()
    )
