from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditRow
from app.schemas.audit import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: AuditEvent) -> None:
        statement = insert(AuditRow).values(
            tenant_id=event.tenant_id,
            id=event.id,
            occurred_at=event.occurred_at,
            event_type=event.event_type,
            actor=event.actor,
            details=event.details,
        )
        await self._session.execute(statement)
