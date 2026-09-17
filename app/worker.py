import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import DatabaseSettings
from app.core.config import RedisSettings as AppRedisSettings
from app.core.redis import get_redis_pool
from app.infrastructure.database import create_database_engine, tenant_transaction
from app.models.dispatch import DispatchState
from app.repositories.dispatch import DispatchRepository
from app.services.dispatcher import DispatcherService
from app.services.processor import (
    IntentProcessor,
    IntentProcessorService,
    RetryableError,
    TerminalError,
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5


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

    claim_token = uuid4()
    async with tenant_transaction(sessions, tenant_id) as session:
        repo = DispatchRepository(session)
        attempts = await repo.claim_for_processing(tenant_id, message_id, claim_token)
    if attempts is None:
        return

    try:
        await processor.process(
            tenant_id, message_id, idempotency_key=f"intent:{tenant_id}:{message_id}"
        )

        # Success
        async with tenant_transaction(sessions, tenant_id) as session:
            repo = DispatchRepository(session)
            await repo.update_intent_state(
                tenant_id,
                message_id,
                DispatchState.COMPLETED,
                claim_token=claim_token,
            )

    except RetryableError as e:
        logger.warning(f"Retryable failure for {tenant_id}/{message_id}: {e}")
        async with tenant_transaction(sessions, tenant_id) as session:
            repo = DispatchRepository(session)
            next_try = datetime.now(UTC) + timedelta(minutes=1)

            if attempts >= MAX_ATTEMPTS:
                await repo.update_intent_state(
                    tenant_id,
                    message_id,
                    DispatchState.FAILED_TERMINAL,
                    increment_attempts=True,
                    claim_token=claim_token,
                )
                logger.error(
                    "Terminal failure for %s/%s after %s attempts.",
                    tenant_id,
                    message_id,
                    attempts,
                )
            else:
                await repo.update_intent_state(
                    tenant_id,
                    message_id,
                    DispatchState.FAILED_RETRY,
                    increment_attempts=True,
                    next_attempt_at=next_try,
                    claim_token=claim_token,
                )

    except TerminalError as e:
        logger.error(f"Terminal failure for {tenant_id}/{message_id}: {e}")
        async with tenant_transaction(sessions, tenant_id) as session:
            repo = DispatchRepository(session)
            await repo.update_intent_state(
                tenant_id,
                message_id,
                DispatchState.FAILED_TERMINAL,
                increment_attempts=True,
                claim_token=claim_token,
            )

    except Exception as e:
        logger.exception(f"Unexpected failure for {tenant_id}/{message_id}: {e}")
        async with tenant_transaction(sessions, tenant_id) as session:
            repo = DispatchRepository(session)
            await repo.update_intent_state(
                tenant_id,
                message_id,
                DispatchState.FAILED_TERMINAL,
                increment_attempts=True,
                claim_token=claim_token,
            )
        raise


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
