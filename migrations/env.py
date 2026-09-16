import asyncio

from alembic import context
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import DatabaseSettings
from app.models import Base


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAHULAT_", hide_input_in_errors=True)
    migration_database_url: SecretStr


def migrate_connection(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def migrate_online() -> None:
    settings = DatabaseSettings(database_url=MigrationSettings().migration_database_url)
    engine = create_async_engine(
        settings.database_url.get_secret_value(),
        poolclass=NullPool,
        hide_parameters=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate_connection)
    finally:
        await engine.dispose()


def run_migrations() -> None:
    if context.is_offline_mode():
        context.configure(
            dialect_name="postgresql", target_metadata=Base.metadata, literal_binds=True
        )
        with context.begin_transaction():
            context.run_migrations()
    elif isinstance(
        connection := context.config.attributes.get("connection"), Connection
    ):
        migrate_connection(connection)
    else:
        asyncio.run(migrate_online())


run_migrations()
