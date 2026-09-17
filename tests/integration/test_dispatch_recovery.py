import asyncio
from pathlib import Path
from uuid import UUID

import pytest
from arq.connections import ArqRedis
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from testcontainers.community.redis import RedisContainer

from app.infrastructure.database import tenant_transaction
from app.models.audit import AuditRow
from app.models.dispatch import DispatchState
from app.services.dispatcher import DispatcherService
from app.services.intent_worker import IntentWorker
from app.services.processor import RetryableError, ReviewRequiredError, TerminalError
from tests.integration.conftest import Database
from tests.integration.test_dispatch import DummyRedis
from tests.integration.test_processing_leases import (
    expire_lease,
    pending_intent,
    read_intent,
)
from tests.integration.test_processing_leases import queue as queue
from tests.integration.test_processing_leases import redis_container as redis_container


class OutcomeProcessor:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def process(
        self,
        tenant_id: UUID,
        message_id: UUID,
        *,
        idempotency_key: str,
    ) -> None:
        if self.error is not None:
            raise self.error


async def audit_details(
    database: Database, message_id: UUID
) -> list[dict[str, object]]:
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        rows = (
            await session.scalars(
                select(AuditRow)
                .where(
                    AuditRow.event_type == "dispatch.transition",
                    AuditRow.details["message_id"].astext == str(message_id),
                )
                .order_by(AuditRow.occurred_at)
            )
        ).all()
        return [row.details for row in rows]


@pytest.mark.parametrize(
    "error,state",
    [
        (None, DispatchState.COMPLETED),
        (RetryableError("private details"), DispatchState.FAILED_RETRY),
        (TerminalError("private details"), DispatchState.FAILED_TERMINAL),
        (ReviewRequiredError("private details"), DispatchState.REVIEW_REQUIRED),
        (ValueError("private details"), DispatchState.REVIEW_REQUIRED),
    ],
)
async def test_every_worker_outcome_is_audited_without_error_payload(
    database: Database,
    error: Exception | None,
    state: DispatchState,
) -> None:
    message_id = await pending_intent(database)
    await DispatcherService(database.sessions, DummyRedis()).dispatch_pending()
    worker = IntentWorker(database.sessions, OutcomeProcessor(error))
    await worker.process(database.tenant_a, message_id)
    events = await audit_details(database, message_id)
    assert [event["to_state"] for event in events] == [
        "pending",
        "enqueued",
        "processing",
        state.value,
    ]
    assert "private details" not in str(events)
    if state == DispatchState.REVIEW_REQUIRED:
        assert (
            await DispatcherService(database.sessions, DummyRedis()).dispatch_pending()
            == 0
        )
        await worker.process(database.tenant_a, message_id)
        assert await audit_details(database, message_id) == events


async def test_audit_failure_rolls_back_state_transition(database: Database) -> None:
    message_id = await pending_intent(database)
    async with database.owner.begin() as connection:
        await connection.execute(
            text(
                "ALTER TABLE sahulat.audit_events ADD CONSTRAINT test_reject_audit "
                "CHECK (false) NOT VALID"
            )
        )
    try:
        with pytest.raises(IntegrityError):
            await DispatcherService(database.sessions, DummyRedis()).dispatch_pending()
        assert (await read_intent(database, message_id)).state == DispatchState.PENDING
    finally:
        async with database.owner.begin() as connection:
            await connection.execute(
                text(
                    "ALTER TABLE sahulat.audit_events DROP CONSTRAINT test_reject_audit"
                )
            )
    assert len(await audit_details(database, message_id)) == 1


async def test_lost_redis_job_is_reclaimed_after_enqueue_lease(
    database: Database,
    queue: ArqRedis,
) -> None:
    await queue.flushdb()
    message_id = await pending_intent(database)
    dispatcher = DispatcherService(database.sessions, queue)
    assert await dispatcher.dispatch_pending() == 1
    await queue.flushdb()
    assert await dispatcher.dispatch_pending() == 0
    await expire_lease(database, message_id)
    assert await DispatcherService(database.sessions, queue).dispatch_pending() == 1
    assert len(await queue.queued_jobs()) == 1
    assert (await read_intent(database, message_id)).state == DispatchState.ENQUEUED
    assert (await audit_details(database, message_id))[-1][
        "reason"
    ] == "enqueue_lease_expired"


async def test_redis_outage_preserves_claim_and_restart_recovers(
    database: Database,
    queue: ArqRedis,
    redis_container: RedisContainer,
) -> None:
    message_id = await pending_intent(database)
    container = redis_container.get_wrapped_container()
    await asyncio.to_thread(container.pause)
    try:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(
                DispatcherService(database.sessions, queue).dispatch_pending(),
                timeout=0.5,
            )
    finally:
        await asyncio.to_thread(container.unpause)
    assert (await read_intent(database, message_id)).state == DispatchState.ENQUEUED
    await expire_lease(database, message_id)
    assert await DispatcherService(database.sessions, queue).dispatch_pending() == 1


async def test_operator_closes_review_without_resend(database: Database) -> None:
    message_id = await pending_intent(database)
    await DispatcherService(database.sessions, DummyRedis()).dispatch_pending()
    await IntentWorker(
        database.sessions, OutcomeProcessor(ReviewRequiredError())
    ).process(
        database.tenant_a,
        message_id,
    )
    script = await asyncio.to_thread(
        Path("scripts/close_dispatch_review.sql").read_text
    )
    statement = (
        script[script.index("UPDATE") : script.index("COMMIT;")]
        .replace(":'tenant_id'", ":tenant_id")
        .replace(":'message_id'", ":message_id")
        .replace(":tenant_id::uuid", "CAST(:tenant_id AS uuid)")
        .replace(":message_id::uuid", "CAST(:message_id AS uuid)")
    )
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        result = await session.execute(
            text(statement),
            {
                "tenant_id": database.tenant_a,
                "message_id": message_id,
            },
        )
        assert len(result.all()) == 1
    assert (await audit_details(database, message_id))[-1][
        "reason"
    ] == "operator_closed_without_resend"
    assert (
        await DispatcherService(database.sessions, DummyRedis()).dispatch_pending() == 0
    )
