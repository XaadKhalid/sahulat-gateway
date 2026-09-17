import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database import tenant_transaction
from app.models.conversations import MessageRow, SessionRow
from app.models.dispatch import DispatchIntentRow, DispatchState
from app.repositories.dispatch import DispatchRepository
from app.services.dispatcher import DispatcherService
from app.services.processor import RetryableError, TerminalError
from app.worker import MAX_ATTEMPTS, process_intent
from tests.integration.conftest import Database


async def insert_test_message(database: Database, message_id: UUID) -> None:
    session_id = uuid4()
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        session.add(
            SessionRow(
                tenant_id=database.tenant_a,
                id=session_id,
                customer_number=f"+{str(uuid4())[:10]}",
                created_at=datetime.now(UTC),
            )
        )
        await session.flush()
        session.add(
            MessageRow(
                tenant_id=database.tenant_a,
                id=message_id,
                session_id=session_id,
                channel="whatsapp",
                provider_message_id=str(message_id),
                content={"type": "text"},
                occurred_at=datetime.now(UTC),
            )
        )


# Fake Redis pool for testing dispatcher enqueuing
class DummyRedis:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, UUID, UUID, str]] = []

    async def enqueue_job(
        self, function: str, tenant_id: UUID, message_id: UUID, *, _job_id: str
    ) -> None:
        self.enqueued.append((function, tenant_id, message_id, _job_id))


@pytest.fixture
def dummy_redis() -> DummyRedis:
    return DummyRedis()


async def test_dispatcher_claims_and_enqueues(
    database: Database, dummy_redis: DummyRedis
) -> None:
    message_id = uuid4()
    await insert_test_message(database, message_id)
    # Insert pending intent
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        repo = DispatchRepository(session)
        await repo.enqueue(database.tenant_a, message_id)

    # Run dispatcher
    dispatcher = DispatcherService(database.sessions, dummy_redis, batch_size=10)
    dispatched = await dispatcher.dispatch_pending()

    assert dispatched == 1
    assert len(dummy_redis.enqueued) == 1

    func, tenant_id, enqueued_id, job_id = dummy_redis.enqueued[0]
    assert func == "process_intent"
    assert tenant_id == database.tenant_a
    assert enqueued_id == message_id
    assert job_id == f"intent:{database.tenant_a}:{message_id}"

    # State should be enqueued
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        intent = (
            await session.scalars(
                select(DispatchIntentRow).where(
                    DispatchIntentRow.message_id == message_id
                )
            )
        ).one()
        assert intent.state == DispatchState.ENQUEUED


async def test_concurrent_dispatchers_do_not_duplicate(
    database: Database, dummy_redis: DummyRedis
) -> None:
    # Insert 10 pending intents
    message_ids = [uuid4() for _ in range(10)]
    for msg_id in message_ids:
        await insert_test_message(database, msg_id)
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        repo = DispatchRepository(session)
        for msg_id in message_ids:
            await repo.enqueue(database.tenant_a, msg_id)

    dispatcher = DispatcherService(database.sessions, dummy_redis, batch_size=5)

    # Run two dispatchers concurrently
    # The skip_locked should ensure they divide the work and don't duplicate
    res1, res2 = await asyncio.gather(
        dispatcher.dispatch_pending(), dispatcher.dispatch_pending()
    )

    assert res1 + res2 == 10
    assert len(dummy_redis.enqueued) == 10

    # Check all are unique
    enqueued_msg_ids = {message_id for _, _, message_id, _ in dummy_redis.enqueued}
    assert len(enqueued_msg_ids) == 10


async def test_worker_success(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    message_id = uuid4()
    await insert_test_message(database, message_id)
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        repo = DispatchRepository(session)
        await repo.enqueue(database.tenant_a, message_id)
        await repo.update_intent_state(
            database.tenant_a, message_id, DispatchState.ENQUEUED
        )

    # Mock processor
    class MockProcessor:
        def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
            pass

        async def process(self, tenant_id: UUID, message_id: UUID) -> None:
            pass

    monkeypatch.setattr("app.worker.IntentProcessorService", MockProcessor)

    ctx = {"sessions": database.sessions}
    await process_intent(ctx, database.tenant_a, message_id)

    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        intent = (
            await session.scalars(
                select(DispatchIntentRow).where(
                    DispatchIntentRow.message_id == message_id
                )
            )
        ).one()
        assert intent.state == DispatchState.COMPLETED


async def test_worker_retryable_failure(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    message_id = uuid4()
    await insert_test_message(database, message_id)
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        repo = DispatchRepository(session)
        await repo.enqueue(database.tenant_a, message_id)
        await repo.update_intent_state(
            database.tenant_a, message_id, DispatchState.ENQUEUED
        )

    class MockProcessor:
        def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
            pass

        async def process(self, tenant_id: UUID, message_id: UUID) -> None:
            raise RetryableError("test")

    monkeypatch.setattr("app.worker.IntentProcessorService", MockProcessor)

    ctx = {"sessions": database.sessions}
    await process_intent(ctx, database.tenant_a, message_id)

    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        intent = (
            await session.scalars(
                select(DispatchIntentRow).where(
                    DispatchIntentRow.message_id == message_id
                )
            )
        ).one()
        assert intent.state == DispatchState.FAILED_RETRY
        assert intent.attempts == 1
        assert intent.next_attempt_at is not None


async def test_worker_terminal_failure(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    message_id = uuid4()
    await insert_test_message(database, message_id)
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        repo = DispatchRepository(session)
        await repo.enqueue(database.tenant_a, message_id)
        await repo.update_intent_state(
            database.tenant_a, message_id, DispatchState.ENQUEUED
        )

    class MockProcessor:
        def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
            pass

        async def process(self, tenant_id: UUID, message_id: UUID) -> None:
            raise TerminalError("test")

    monkeypatch.setattr("app.worker.IntentProcessorService", MockProcessor)

    ctx = {"sessions": database.sessions}
    await process_intent(ctx, database.tenant_a, message_id)

    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        intent = (
            await session.scalars(
                select(DispatchIntentRow).where(
                    DispatchIntentRow.message_id == message_id
                )
            )
        ).one()
        assert intent.state == DispatchState.FAILED_TERMINAL
        assert intent.attempts == 1


async def test_worker_max_retries_exceeded(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    message_id = uuid4()
    await insert_test_message(database, message_id)
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        repo = DispatchRepository(session)
        await repo.enqueue(database.tenant_a, message_id)
        await repo.update_intent_state(
            database.tenant_a, message_id, DispatchState.FAILED_RETRY
        )
        # manually set attempts to MAX_ATTEMPTS
        await session.execute(
            update(DispatchIntentRow)
            .where(DispatchIntentRow.message_id == message_id)
            .values(attempts=MAX_ATTEMPTS)
        )

    class MockProcessor:
        def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
            pass

        async def process(self, tenant_id: UUID, message_id: UUID) -> None:
            raise RetryableError("test")

    monkeypatch.setattr("app.worker.IntentProcessorService", MockProcessor)

    ctx = {"sessions": database.sessions}
    await process_intent(ctx, database.tenant_a, message_id)

    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        intent = (
            await session.scalars(
                select(DispatchIntentRow).where(
                    DispatchIntentRow.message_id == message_id
                )
            )
        ).one()
        assert intent.state == DispatchState.FAILED_TERMINAL
        assert intent.attempts == MAX_ATTEMPTS + 1
