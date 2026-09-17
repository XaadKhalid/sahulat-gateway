from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dispatch import DispatchIntentRow, DispatchState


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

    async def claim_pending_intents(
        self, batch_size: int = 50
    ) -> Sequence[DispatchIntentRow]:
        """Claim intents for processing by calling the security definer function."""
        # The restricted function claims work across tenant boundaries.
        statement = text(
            "SELECT tenant_id, message_id FROM sahulat.claim_pending_intents(:batch)"
        )

        result = await self._session.execute(statement, {"batch": batch_size})
        # The result is rows with tenant_id and message_id
        # We can construct lightweight intent row objects for the dispatcher
        return [
            DispatchIntentRow(tenant_id=row.tenant_id, message_id=row.message_id)
            for row in result.all()
        ]

    async def claim_for_processing(
        self, tenant_id: UUID, message_id: UUID, claim_token: UUID
    ) -> int | None:
        """Only one delivery may acquire an enqueued intent; use database time."""
        statement = (
            update(DispatchIntentRow)
            .where(
                DispatchIntentRow.tenant_id == tenant_id,
                DispatchIntentRow.message_id == message_id,
                DispatchIntentRow.state == DispatchState.ENQUEUED,
            )
            .values(
                state=DispatchState.PROCESSING,
                claim_token=claim_token,
                lease_expires_at=func.now() + timedelta(minutes=5),
            )
            .returning(DispatchIntentRow.attempts)
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def update_intent_state(
        self,
        tenant_id: UUID,
        message_id: UUID,
        state: DispatchState,
        *,
        claim_token: UUID,
        increment_attempts: bool = False,
        next_attempt_at: datetime | None = None,
    ) -> None:
        statement = (
            update(DispatchIntentRow)
            .where(
                DispatchIntentRow.tenant_id == tenant_id,
                DispatchIntentRow.message_id == message_id,
                DispatchIntentRow.state == DispatchState.PROCESSING,
                DispatchIntentRow.claim_token == claim_token,
                DispatchIntentRow.lease_expires_at > func.now(),
            )
            .values(
                state=state,
                next_attempt_at=next_attempt_at,
                lease_expires_at=None,
                claim_token=None,
            )
        )

        if increment_attempts:
            statement = statement.values(attempts=DispatchIntentRow.attempts + 1)

        await self._session.execute(statement)
