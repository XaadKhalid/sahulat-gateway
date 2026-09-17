from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.dispatch import DispatchRepository


class JobQueue(Protocol):
    async def enqueue_job(
        self, function: str, tenant_id: UUID, message_id: UUID, *, _job_id: str
    ) -> object:
        """Return a job on acceptance, None if the queue rejects the delivery."""
        ...


class DispatcherService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        redis: JobQueue,
        batch_size: int = 50,
    ) -> None:
        self._sessions = sessions
        self._redis = redis
        self._batch_size = batch_size

    async def dispatch_pending(self) -> int:
        """Commit a recoverable delivery lease before exposing work to Redis."""
        async with self._sessions() as session:
            repo = DispatchRepository(session)

            async with session.begin():
                intents = await repo.claim_pending_intents(batch_size=self._batch_size)

        for intent in intents:
            # A retained Redis result cannot suppress a recovery delivery.
            job_id = f"intent:{intent.tenant_id}:{intent.message_id}:{uuid4()}"
            job = await self._redis.enqueue_job(
                "process_intent",
                intent.tenant_id,
                intent.message_id,
                _job_id=job_id,
            )
            if job is None:
                raise RuntimeError("Queue rejected dispatch delivery")
        return len(intents)
