import asyncio
import secrets
from collections.abc import AsyncIterator, Iterator
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from arq.connections import ArqRedis, RedisSettings, create_pool
from sqlalchemy import Connection, func, select, text, update
from testcontainers.community.redis import RedisContainer

from app.infrastructure.database import tenant_transaction
from app.models.dispatch import DispatchIntentRow, DispatchState
from app.repositories.dispatch import DispatchRepository
from app.services.dispatcher import DispatcherService
from app.worker import process_intent
from tests.integration.conftest import Database
from tests.integration.test_dispatch import DummyRedis, insert_test_message


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer("redis:7.4", password=secrets.token_urlsafe(32)) as container:
        yield container


@pytest.fixture
async def queue(redis_container: RedisContainer) -> AsyncIterator[ArqRedis]:
    pool = await create_pool(
        RedisSettings(
            host=redis_container.get_container_host_ip(),
            port=int(redis_container.get_exposed_port(6379)),
            password=redis_container.password,
        )
    )
    try:
        yield pool
    finally:
        await pool.aclose()


async def pending_intent(database: Database) -> UUID:
    message_id = uuid4()
    await insert_test_message(database, message_id)
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        await DispatchRepository(session).enqueue(database.tenant_a, message_id)
    return message_id


async def read_intent(database: Database, message_id: UUID) -> DispatchIntentRow:
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        return (
            await session.scalars(
                select(DispatchIntentRow).where(
                    DispatchIntentRow.message_id == message_id,
                )
            )
        ).one()


async def expire_lease(database: Database, message_id: UUID) -> None:
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        await session.execute(
            update(DispatchIntentRow)
            .where(
                DispatchIntentRow.message_id == message_id,
            )
            .values(lease_expires_at=func.now() - timedelta(seconds=1))
        )


class InterruptedProcessor:
    def __init__(self) -> None:
        self.keys: list[str] = []

    async def process(
        self, tenant_id: UUID, message_id: UUID, *, idempotency_key: str
    ) -> None:
        self.keys.append(idempotency_key)
        if len(self.keys) == 1:
            # Cancellation bypasses normal result transitions, like worker death.
            raise asyncio.CancelledError


async def test_stuck_processing_is_reclaimed_with_same_idempotency_key(
    database: Database,
    queue: ArqRedis,
) -> None:
    message_id = await pending_intent(database)
    dispatcher = DispatcherService(database.sessions, queue)
    assert await dispatcher.dispatch_pending() == 1
    original_jobs = await queue.queued_jobs()
    processor = InterruptedProcessor()
    with pytest.raises(asyncio.CancelledError):
        await process_intent(
            {"sessions": database.sessions},
            database.tenant_a,
            message_id,
            processor=processor,
        )
    abandoned = await read_intent(database, message_id)
    assert abandoned.state == DispatchState.PROCESSING
    assert abandoned.claim_token is not None
    assert abandoned.lease_expires_at is not None
    assert await dispatcher.dispatch_pending() == 0
    await process_intent(
        {"sessions": database.sessions},
        database.tenant_a,
        message_id,
        processor=processor,
    )
    assert len(processor.keys) == 1

    await expire_lease(database, message_id)
    # A new dispatcher represents restart; retain the old Redis job deliberately.
    assert await DispatcherService(database.sessions, queue).dispatch_pending() == 1
    reclaimed = await read_intent(database, message_id)
    assert reclaimed.state == DispatchState.ENQUEUED
    assert reclaimed.claim_token is None
    jobs = await queue.queued_jobs()
    assert len(jobs) == len(original_jobs) + 1
    assert len({job.job_id for job in jobs}) == len(jobs)
    await process_intent(
        {"sessions": database.sessions},
        database.tenant_a,
        message_id,
        processor=processor,
    )
    assert processor.keys == [f"intent:{database.tenant_a}:{message_id}"] * 2
    completed = await read_intent(database, message_id)
    assert completed.state == DispatchState.COMPLETED
    assert completed.lease_expires_at is None
    assert completed.claim_token is None
    await process_intent(
        {"sessions": database.sessions},
        database.tenant_a,
        message_id,
        processor=processor,
    )
    assert len(processor.keys) == 2


@pytest.mark.parametrize(
    "late_state",
    [
        DispatchState.COMPLETED,
        DispatchState.FAILED_RETRY,
        DispatchState.FAILED_TERMINAL,
    ],
)
async def test_expired_worker_cannot_overwrite_replacement_claim(
    database: Database,
    late_state: DispatchState,
) -> None:
    message_id = await pending_intent(database)
    dispatcher = DispatcherService(database.sessions, DummyRedis())
    await dispatcher.dispatch_pending()
    old_token, new_token = uuid4(), uuid4()
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        assert (
            await DispatchRepository(session).claim_for_processing(
                database.tenant_a,
                message_id,
                old_token,
            )
            == 0
        )
    await expire_lease(database, message_id)
    # An expired owner also cannot complete before the dispatcher runs.
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        await DispatchRepository(session).update_intent_state(
            database.tenant_a,
            message_id,
            late_state,
            claim_token=old_token,
        )
    assert (await read_intent(database, message_id)).state == DispatchState.PROCESSING
    assert await dispatcher.dispatch_pending() == 1
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        repo = DispatchRepository(session)
        assert (
            await repo.claim_for_processing(
                database.tenant_a,
                message_id,
                new_token,
            )
            == 0
        )
        await repo.update_intent_state(
            database.tenant_a,
            message_id,
            late_state,
            claim_token=old_token,
            increment_attempts=True,
        )
    current = await read_intent(database, message_id)
    assert current.state == DispatchState.PROCESSING
    assert current.claim_token == new_token
    assert current.attempts == 0


async def test_concurrent_worker_claims_have_one_owner(database: Database) -> None:
    message_id = await pending_intent(database)
    await DispatcherService(database.sessions, DummyRedis()).dispatch_pending()

    async def claim() -> int | None:
        async with tenant_transaction(database.sessions, database.tenant_a) as session:
            return await DispatchRepository(session).claim_for_processing(
                database.tenant_a,
                message_id,
                uuid4(),
            )

    results = await asyncio.gather(claim(), claim())
    assert results.count(0) == 1
    assert results.count(None) == 1


async def test_unconfigured_processor_cannot_report_success(database: Database) -> None:
    message_id = await pending_intent(database)
    await DispatcherService(database.sessions, DummyRedis()).dispatch_pending()
    await process_intent({"sessions": database.sessions}, database.tenant_a, message_id)
    current = await read_intent(database, message_id)
    assert current.state == DispatchState.FAILED_TERMINAL
    assert current.lease_expires_at is None


async def test_claim_cannot_cross_tenant_boundary(database: Database) -> None:
    message_id = await pending_intent(database)
    await DispatcherService(database.sessions, DummyRedis()).dispatch_pending()
    async with tenant_transaction(database.sessions, database.tenant_b) as session:
        assert (
            await DispatchRepository(session).claim_for_processing(
                database.tenant_a,
                message_id,
                uuid4(),
            )
            is None
        )
    assert (await read_intent(database, message_id)).state == DispatchState.ENQUEUED


async def test_upgrade_makes_legacy_processing_rows_reclaimable(
    database: Database,
) -> None:
    message_id = await pending_intent(database)

    def downgrade_to_legacy(connection: Connection) -> None:
        config = Config("alembic.ini")
        config.attributes["connection"] = connection
        command.downgrade(config, "0004")

    def upgrade(connection: Connection) -> None:
        config = Config("alembic.ini")
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    async with database.owner.begin() as connection:
        await connection.run_sync(downgrade_to_legacy)
        await connection.execute(
            text(
                "UPDATE sahulat.dispatch_intents SET state = 'processing' "
                "WHERE message_id = :message_id"
            ),
            {"message_id": message_id},
        )
        await connection.run_sync(upgrade)
    assert (
        await DispatcherService(database.sessions, DummyRedis()).dispatch_pending() == 1
    )
    assert (await read_intent(database, message_id)).state == DispatchState.ENQUEUED
