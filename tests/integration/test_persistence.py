from asyncio import TaskGroup
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Connection, ExecutionContext, event, select

from app.core.errors import MessageIdentityConflict
from app.infrastructure.database import tenant_transaction
from app.models.conversations import SessionRow
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.repositories.tenants import TenantRepository
from app.schemas.messages import (
    MessageEnvelope,
    MessageSaveResult,
    TextContent,
    UnsupportedContent,
)
from app.schemas.sessions import SessionIdentity
from app.schemas.tenants import RouteLookup
from tests.integration.conftest import Database


async def test_routing_exposes_only_tenant_id_without_setting_context(
    database: Database,
) -> None:
    async with database.sessions() as session:
        repository = TenantRepository(session)
        route = await repository.resolve(RouteLookup(route_key="route-a"))
        assert route is not None and route.tenant_id == database.tenant_a
        assert route.model_dump().keys() == {"tenant_id"}
        assert await repository.resolve(RouteLookup(route_key="unknown")) is None
        assert await repository.resolve(RouteLookup(route_key="' OR true --")) is None
        assert await repository.get(database.tenant_a) is None


@pytest.mark.parametrize(
    "content",
    [TextContent(text="Order question"), UnsupportedContent(provider_kind="image")],
)
async def test_message_round_trip_and_idempotency(
    database: Database, content: TextContent | UnsupportedContent
) -> None:
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        sessions = SessionRepository(session)
        identity = SessionIdentity(
            tenant_id=database.tenant_a, customer_number="test-customer"
        )
        first = await sessions.get_or_create(identity)
        assert await sessions.get_or_create(identity) == first
        assert first.created_at.tzinfo == UTC
        message = MessageEnvelope(
            tenant_id=database.tenant_a,
            session_id=first.id,
            provider_message_id="message-one",
            content=content,
            occurred_at=datetime.now(UTC),
        )
        repository = MessageRepository(session)
        saved = await repository.save(message)
        assert saved.created
        replay = await repository.save(message.model_copy(update={"id": uuid4()}))
        assert not replay.created
        assert replay.message.id == message.id
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        assert (
            await MessageRepository(session).get(database.tenant_a, "message-one")
            == message
        )


async def test_reused_message_identity_with_different_content_is_rejected(
    database: Database,
) -> None:
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        conversation = await SessionRepository(session).get_or_create(
            SessionIdentity(
                tenant_id=database.tenant_a, customer_number="test-customer"
            )
        )
        message = MessageEnvelope(
            tenant_id=database.tenant_a,
            session_id=conversation.id,
            provider_message_id="same-id",
            content=TextContent(text="Original"),
            occurred_at=datetime.now(UTC),
        )
        await MessageRepository(session).save(message)
    with pytest.raises(MessageIdentityConflict):
        async with tenant_transaction(database.sessions, database.tenant_a) as session:
            await MessageRepository(session).save(
                message.model_copy(update={"content": TextContent(text="Changed")})
            )
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        assert (
            await MessageRepository(session).get(database.tenant_a, "same-id")
            == message
        )


async def test_failed_turn_rolls_back_session_creation(database: Database) -> None:
    with pytest.raises(ValueError, match="turn failed"):
        async with tenant_transaction(database.sessions, database.tenant_a) as session:
            await SessionRepository(session).get_or_create(
                SessionIdentity(
                    tenant_id=database.tenant_a, customer_number="test-customer"
                )
            )
            raise ValueError("turn failed")
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        assert (await session.scalars(select(SessionRow))).all() == []


async def test_concurrent_duplicate_delivery_creates_one_session_and_message(
    database: Database,
) -> None:
    occurred_at = datetime.now(UTC)

    async def deliver() -> MessageSaveResult:
        async with tenant_transaction(database.sessions, database.tenant_a) as session:
            conversation = await SessionRepository(session).get_or_create(
                SessionIdentity(
                    tenant_id=database.tenant_a, customer_number="concurrent"
                )
            )
            return await MessageRepository(session).save(
                MessageEnvelope(
                    tenant_id=database.tenant_a,
                    session_id=conversation.id,
                    provider_message_id="concurrent-message",
                    content=TextContent(text="Hello"),
                    occurred_at=occurred_at,
                )
            )

    async with TaskGroup() as group:
        first = group.create_task(deliver())
        second = group.create_task(deliver())
    assert first.result().message == second.result().message
    assert sorted([first.result().created, second.result().created]) == [False, True]


async def test_new_session_and_message_use_three_queries(database: Database) -> None:
    statements: list[str] = []

    def count_query(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext | None,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        event.listen(database.runtime.sync_engine, "before_cursor_execute", count_query)
        try:
            conversation = await SessionRepository(session).get_or_create(
                SessionIdentity(
                    tenant_id=database.tenant_a, customer_number="query-budget"
                )
            )
            await MessageRepository(session).save(
                MessageEnvelope(
                    tenant_id=database.tenant_a,
                    session_id=conversation.id,
                    provider_message_id="query-budget",
                    content=TextContent(text="Hello"),
                    occurred_at=datetime.now(UTC),
                )
            )
            assert len(statements) == 3
        finally:
            event.remove(
                database.runtime.sync_engine, "before_cursor_execute", count_query
            )
