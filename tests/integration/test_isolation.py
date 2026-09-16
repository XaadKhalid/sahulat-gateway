from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError

from app.core.errors import PersistenceFailure
from app.infrastructure.database import tenant_transaction
from app.models.conversations import MessageRow, SessionRow
from app.models.tenants import TenantRow
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.schemas.messages import MessageEnvelope, TextContent
from app.schemas.sessions import SessionIdentity
from tests.integration.conftest import Database


async def seed_message(database: Database, tenant_id: UUID) -> MessageEnvelope:
    async with tenant_transaction(database.sessions, tenant_id) as session:
        conversation = await SessionRepository(session).get_or_create(
            SessionIdentity(tenant_id=tenant_id, customer_number="same-customer")
        )
        message = MessageEnvelope(
            tenant_id=tenant_id,
            session_id=conversation.id,
            provider_message_id="same-provider-id",
            content=TextContent(text="Tenant content"),
            occurred_at=datetime.now(UTC),
        )
        await MessageRepository(session).save(message)
        return message


async def test_unfiltered_queries_are_isolated_by_database_policy(
    database: Database,
) -> None:
    first = await seed_message(database, database.tenant_a)
    second = await seed_message(database, database.tenant_b)
    assert first.session_id != second.session_id
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        assert (await session.scalars(select(TenantRow.id))).all() == [
            database.tenant_a
        ]
        assert (await session.scalars(select(SessionRow.id))).all() == [
            first.session_id
        ]
        assert (await session.scalars(select(MessageRow.id))).all() == [first.id]
        assert (
            await MessageRepository(session).get(database.tenant_b, "same-provider-id")
            is None
        )
    async with tenant_transaction(database.sessions, database.tenant_b) as session:
        assert (await session.scalars(select(MessageRow.id))).all() == [second.id]


async def test_no_tenant_context_denies_reads_and_inserts(database: Database) -> None:
    await seed_message(database, database.tenant_a)
    async with database.sessions() as session:
        assert (await session.scalars(select(TenantRow))).all() == []
        assert (await session.scalars(select(SessionRow))).all() == []
        assert (await session.scalars(select(MessageRow))).all() == []
        with pytest.raises(DBAPIError):
            await SessionRepository(session).get_or_create(
                SessionIdentity(tenant_id=database.tenant_a, customer_number="blocked")
            )


async def test_cross_tenant_insert_is_rejected(database: Database) -> None:
    with pytest.raises(PersistenceFailure):
        async with tenant_transaction(database.sessions, database.tenant_a) as session:
            await SessionRepository(session).get_or_create(
                SessionIdentity(tenant_id=database.tenant_b, customer_number="blocked")
            )


async def test_message_cannot_reference_another_tenants_session(
    database: Database,
) -> None:
    other = await seed_message(database, database.tenant_b)
    with pytest.raises(PersistenceFailure):
        async with tenant_transaction(database.sessions, database.tenant_a) as session:
            await MessageRepository(session).save(
                other.model_copy(update={"id": uuid4(), "tenant_id": database.tenant_a})
            )


async def test_pool_reuse_clears_context_on_commit_and_rollback(
    database: Database,
) -> None:
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        process_id = await session.scalar(text("SELECT pg_backend_pid()"))
        assert (
            await session.scalar(text("SELECT sahulat.current_tenant_id()"))
            == database.tenant_a
        )
    async with database.sessions() as session:
        assert await session.scalar(text("SELECT pg_backend_pid()")) == process_id
        assert await session.scalar(text("SELECT sahulat.current_tenant_id()")) is None
    with pytest.raises(ValueError):
        async with tenant_transaction(database.sessions, database.tenant_b) as session:
            assert await session.scalar(text("SELECT pg_backend_pid()")) == process_id
            assert (
                await session.scalar(text("SELECT sahulat.current_tenant_id()"))
                == database.tenant_b
            )
            raise ValueError("rollback")
    async with database.sessions() as session:
        assert await session.scalar(text("SELECT pg_backend_pid()")) == process_id
        assert await session.scalar(text("SELECT sahulat.current_tenant_id()")) is None
        assert (await session.scalars(select(TenantRow))).all() == []


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM sahulat_private.tenant_routes",
        "ALTER TABLE sahulat.messages DISABLE ROW LEVEL SECURITY",
        "TRUNCATE sahulat.messages",
        "DELETE FROM sahulat.messages",
        "UPDATE sahulat.messages SET channel = 'whatsapp'",
        "SET ROLE migration_user",
    ],
)
async def test_runtime_role_cannot_escalate_or_modify_immutable_data(
    database: Database, statement: str
) -> None:
    async with database.sessions() as session:
        with pytest.raises(DBAPIError):
            await session.execute(text(statement))


async def test_runtime_login_has_no_privileged_attributes(database: Database) -> None:
    async with database.sessions() as session:
        row = (
            await session.execute(
                text(
                    """SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb,
                       rolreplication FROM pg_roles WHERE rolname = current_user"""
                )
            )
        ).one()
        assert tuple(row) == (False, False, False, False, False)
        assert (
            await session.scalar(
                text(
                    """SELECT count(*) FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname IN ('sahulat', 'sahulat_private')
                AND pg_has_role(current_user, c.relowner, 'MEMBER')"""
                )
            )
            == 0
        )
        assert (
            await session.scalar(
                text(
                    """SELECT count(*) FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'sahulat' AND c.relkind = 'r'
                AND c.relrowsecurity AND c.relforcerowsecurity"""
                )
            )
            == 3
        )


async def test_runtime_cannot_create_tenants(database: Database) -> None:
    async with database.sessions() as session:
        with pytest.raises(DBAPIError):
            await session.execute(insert(TenantRow).values(id=uuid4(), name="blocked"))
