from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.dispatch import DispatchRepository


class DispatcherService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        redis: ArqRedis,
        batch_size: int = 50,
    ) -> None:
        self._sessions = sessions
        self._redis = redis
        self._batch_size = batch_size

    async def dispatch_pending(self) -> int:
        """Find pending intents, lock them, update to enqueued, and push to Arq."""
        dispatched_count = 0
        async with self._sessions() as session:
            repo = DispatchRepository(session)

            # Use a transaction for FOR UPDATE SKIP LOCKED
            async with session.begin():
                intents = await repo.claim_pending_intents(batch_size=self._batch_size)

                for intent in intents:
                    # Enqueue to Arq using deterministic job ID to prevent duplicates
                    job_id = f"intent:{intent.tenant_id}:{intent.message_id}"

                    # We pass tenant_id and message_id as strings or UUIDs
                    await self._redis.enqueue_job(
                        "process_intent",
                        intent.tenant_id,
                        intent.message_id,
                        _job_id=job_id,
                    )
                    dispatched_count += 1

            # Once session.begin() exits without error, the state updates are committed

        return dispatched_count
