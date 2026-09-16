from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import MessageIdentityConflict
from app.models.conversations import MessageRow
from app.schemas.messages import MessageEnvelope, MessageSaveResult


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, tenant_id: UUID, provider_message_id: str
    ) -> MessageEnvelope | None:
        row = await self._session.scalar(
            select(MessageRow).where(
                MessageRow.tenant_id == tenant_id,
                MessageRow.provider_message_id == provider_message_id,
            )
        )
        return None if row is None else MessageEnvelope.model_validate(row)

    async def save(self, message: MessageEnvelope) -> MessageSaveResult:
        statement = (
            insert(MessageRow)
            .values(
                id=message.id,
                tenant_id=message.tenant_id,
                session_id=message.session_id,
                channel=message.channel,
                provider_message_id=message.provider_message_id,
                content=message.content.model_dump(mode="json"),
                occurred_at=message.occurred_at,
            )
            .on_conflict_do_nothing(constraint="message_provider_unique")
            .returning(MessageRow.id)
        )
        inserted_id = await self._session.scalar(statement)
        if inserted_id is not None:
            return MessageSaveResult(message=message, created=True)
        existing = await self.get(message.tenant_id, message.provider_message_id)
        if existing is None or existing.model_dump(
            exclude={"id"}
        ) != message.model_dump(exclude={"id"}):
            raise MessageIdentityConflict("Provider message identity conflicts")
        return MessageSaveResult(message=existing, created=False)
