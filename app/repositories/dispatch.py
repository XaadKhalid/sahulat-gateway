from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dispatch import DispatchIntentRow


class DispatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, tenant_id: UUID, message_id: UUID) -> None:
        statement = (
            insert(DispatchIntentRow)
            .values(tenant_id=tenant_id, message_id=message_id)
            .on_conflict_do_nothing()
        )
        await self._session.execute(statement)
