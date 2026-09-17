from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database import tenant_transaction
from app.models.dispatch import DispatchState
from app.repositories.dispatch import DispatchRepository
from app.services.processor import (
    IntentProcessor,
    RetryableError,
    ReviewRequiredError,
    TerminalError,
)

MAX_ATTEMPTS = 5


class IntentWorker:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        processor: IntentProcessor,
    ) -> None:
        self._sessions = sessions
        self._processor = processor

    async def process(self, tenant_id: UUID, message_id: UUID) -> None:
        token = uuid4()
        async with tenant_transaction(self._sessions, tenant_id) as session:
            attempts = await DispatchRepository(session).claim_for_processing(
                tenant_id,
                message_id,
                token,
            )
        if attempts is None:
            return
        state = await self._invoke(tenant_id, message_id, attempts)
        next_try = (
            datetime.now(UTC) + timedelta(minutes=1)
            if state == DispatchState.FAILED_RETRY
            else None
        )
        async with tenant_transaction(self._sessions, tenant_id) as session:
            await DispatchRepository(session).update_intent_state(
                tenant_id,
                message_id,
                state,
                claim_token=token,
                increment_attempts=True,
                next_attempt_at=next_try,
            )

    async def _invoke(
        self,
        tenant_id: UUID,
        message_id: UUID,
        attempts: int,
    ) -> DispatchState:
        try:
            await self._processor.process(
                tenant_id,
                message_id,
                idempotency_key=f"intent:{tenant_id}:{message_id}",
            )
            return DispatchState.COMPLETED
        except RetryableError:
            return (
                DispatchState.REVIEW_REQUIRED
                if attempts + 1 >= MAX_ATTEMPTS
                else DispatchState.FAILED_RETRY
            )
        except TerminalError:
            return DispatchState.FAILED_TERMINAL
        except ReviewRequiredError:
            return DispatchState.REVIEW_REQUIRED
        except Exception:
            # Unknown outcomes must be held, never guessed safe to resend.
            return DispatchState.REVIEW_REQUIRED
