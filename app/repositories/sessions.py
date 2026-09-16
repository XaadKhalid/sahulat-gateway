from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversations import SessionRow
from app.schemas.sessions import ConversationSession, SessionIdentity


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, identity: SessionIdentity) -> ConversationSession:
        statement = (
            insert(SessionRow)
            .values(
                id=uuid4(),
                tenant_id=identity.tenant_id,
                customer_number=identity.customer_number,
                created_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(constraint="session_customer_unique")
        )
        await self._session.execute(statement)
        row = (
            await self._session.scalars(
                select(SessionRow).where(
                    SessionRow.tenant_id == identity.tenant_id,
                    SessionRow.customer_number == identity.customer_number,
                )
            )
        ).one()
        return ConversationSession.model_validate(row)
