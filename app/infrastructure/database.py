from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import DatabaseSettings
from app.core.errors import PersistenceFailure


def create_database_engine(settings: DatabaseSettings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        echo=False,
        hide_parameters=True,
        pool_pre_ping=True,
        connect_args={"server_settings": {"timezone": "UTC"}},
    )


@asynccontextmanager
async def tenant_transaction(
    sessions: async_sessionmaker[AsyncSession], tenant_id: UUID
) -> AsyncIterator[AsyncSession]:
    try:
        async with sessions() as session, session.begin():
            await session.execute(
                text("SELECT set_config('sahulat.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )
            yield session
    except SQLAlchemyError as exc:
        # Never include query parameters (which may contain PII) in this message.
        raise PersistenceFailure("Database transaction failed") from exc
