from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class RetryableError(Exception):
    """Exception indicating the processing failed but should be retried."""


class TerminalError(Exception):
    """Exception indicating the processing failed fatally."""


class IntentProcessorService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def process(self, tenant_id: UUID, message_id: UUID) -> None:
        """Process the intent framework-free. For now, it's a stub."""
        # The real implementation will invoke the TurnLoop.
        pass
