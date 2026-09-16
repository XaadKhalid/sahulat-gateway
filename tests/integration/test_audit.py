from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.infrastructure.database import tenant_transaction
from app.models.audit import AuditRow
from app.repositories.audit import AuditRepository
from app.schemas.audit import AuditEvent
from tests.integration.conftest import Database


async def test_audit_append_only_isolation(database: Database) -> None:
    event_id = uuid4()
    occurred_at = datetime.now(UTC)
    event = AuditEvent(
        tenant_id=database.tenant_a,
        id=event_id,
        occurred_at=occurred_at,
        event_type="test.event",
        actor="system",
        details={"key": "value"},
    )

    # 1. Insert works in tenant_a context
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        repo = AuditRepository(session)
        await repo.append(event)

    # 2. Read works in tenant_a context
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        rows = (await session.scalars(select(AuditRow))).all()
        assert len(rows) == 1
        assert rows[0].id == event_id

    # 3. Read is isolated from tenant_b
    async with tenant_transaction(database.sessions, database.tenant_b) as session:
        rows = (await session.scalars(select(AuditRow))).all()
        assert len(rows) == 0

    # 4. Update fails
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        with pytest.raises(DBAPIError):
            await session.execute(
                update(AuditRow).where(AuditRow.id == event_id).values(actor="hacker")
            )

    # 5. Delete fails
    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        with pytest.raises(DBAPIError):
            await session.execute(delete(AuditRow).where(AuditRow.id == event_id))


async def test_audit_shares_transaction(database: Database) -> None:
    # Prove that if we fail after appending an audit event, it rolls back.
    with pytest.raises(ValueError, match="rollback"):
        async with tenant_transaction(database.sessions, database.tenant_a) as session:
            repo = AuditRepository(session)
            await repo.append(
                AuditEvent(
                    tenant_id=database.tenant_a,
                    id=uuid4(),
                    occurred_at=datetime.now(UTC),
                    event_type="test.transaction",
                    actor="system",
                    details={},
                )
            )
            raise ValueError("rollback")

    async with tenant_transaction(database.sessions, database.tenant_a) as session:
        rows = (await session.scalars(select(AuditRow))).all()
        assert len(rows) == 0
