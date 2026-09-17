from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class RetryableError(Exception):
    """Exception indicating the processing failed but should be retried."""


class TerminalError(Exception):
    """Exception indicating the processing failed fatally."""


class ReviewRequiredError(Exception):
    """Outcome is uncertain or requires operator intervention; never auto-retry."""


class IntentProcessor(Protocol):
    async def process(
        self, tenant_id: UUID, message_id: UUID, *, idempotency_key: str
    ) -> None: ...


class IntentProcessorService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def process(
        self, tenant_id: UUID, message_id: UUID, *, idempotency_key: str
    ) -> None:
        """SAH-007 must forward this stable key to every retryable outbound write."""
        raise TerminalError("Outbound processor is not configured")
