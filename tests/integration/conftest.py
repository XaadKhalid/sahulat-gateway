import secrets
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import URL, Connection, insert, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer

from app.core.config import DatabaseSettings
from app.infrastructure.database import create_database_engine
from app.models.admin import AdminUserRow
from app.models.tenants import TenantRow
from app.services.auth_service import hash_password


@dataclass(frozen=True)
class Database:
    owner: AsyncEngine
    runtime: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]
    tenant_a: UUID
    tenant_b: UUID
    admin_id: UUID
    operator_id: UUID


@dataclass(frozen=True)
class AdminUserCredentials:
    email: str
    password: str
    role: str


ADMIN_CREDENTIALS = AdminUserCredentials(
    email="admin@acme.com", password="password", role="admin"
)
OPERATOR_CREDENTIALS = AdminUserCredentials(
    email="ops@acme.com", password="password123", role="operator"
)


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        "postgres:16.15",
        username="migration_user",
        password=secrets.token_urlsafe(32),
        dbname="sahulat_test",
        driver="asyncpg",
    ) as container:
        yield container


@pytest.fixture
def bootstrap_sql() -> str:
    return Path("scripts/bootstrap_roles.sql").read_text(encoding="utf-8-sig")


def migrate(connection: Connection, revision: str) -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    if revision == "base":
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


async def initialize_database(
    owner: AsyncEngine, bootstrap_sql: str, password: str
) -> None:
    async with owner.begin() as connection:
        await connection.execute(text(bootstrap_sql))
        create_login = text(
            "CREATE ROLE sahulat_test_login LOGIN PASSWORD :password"
        ).bindparams(password=password)
        compiled = create_login.compile(
            dialect=connection.dialect,
            compile_kwargs={"literal_binds": True},
        )
        await connection.execute(text(str(compiled)))
        await connection.execute(text("GRANT sahulat_runtime TO sahulat_test_login"))
        await connection.run_sync(migrate, "head")


async def seed_tenants(data: Database) -> None:
    async with data.owner.begin() as connection:
        await connection.execute(
            insert(TenantRow),
            [
                {
                    "id": data.tenant_a,
                    "name": "Retailer A",
                    "policy": {
                        "persona": "You are a helpful business assistant.",
                        "languages": "en",
                        "domain_fence": "same-origin",
                        "refusal_style": "polite",
                        "business_hours": "09:00-18:00",
                        "verified_ttl_minutes": 60,
                        "handoff_rules": "escalate",
                    },
                },
                {
                    "id": data.tenant_b,
                    "name": "Retailer B",
                    "policy": {
                        "persona": "You are a helpful business assistant.",
                        "languages": "en",
                        "domain_fence": "same-origin",
                        "refusal_style": "polite",
                        "business_hours": "09:00-18:00",
                        "verified_ttl_minutes": 60,
                        "handoff_rules": "escalate",
                    },
                },
            ],
        )
        await connection.execute(
            text(
                "INSERT INTO sahulat_private.tenant_routes "
                "(route_key, tenant_id) "
                "VALUES (:route, :tenant)"
            ),
            [
                {"route": "route-a", "tenant": data.tenant_a},
                {"route": "route-b", "tenant": data.tenant_b},
            ],
        )


async def seed_admin_users(data: Database) -> None:
    from datetime import UTC, datetime

    async with data.owner.begin() as connection:
        await connection.execute(
            insert(AdminUserRow),
            [
                {
                    "id": data.admin_id,
                    "email": ADMIN_CREDENTIALS.email,
                    "password_hash": hash_password(ADMIN_CREDENTIALS.password),
                    "role": ADMIN_CREDENTIALS.role,
                    "display_name": "Acme Admin",
                    "created_at": datetime(2026, 9, 17, 9, 0, 0, tzinfo=UTC),
                },
                {
                    "id": data.operator_id,
                    "email": OPERATOR_CREDENTIALS.email,
                    "password_hash": hash_password(OPERATOR_CREDENTIALS.password),
                    "role": OPERATOR_CREDENTIALS.role,
                    "display_name": "Ops User",
                    "created_at": datetime(2026, 9, 17, 9, 30, 0, tzinfo=UTC),
                },
            ],
        )


@pytest.fixture
async def database(
    postgres: PostgresContainer, bootstrap_sql: str
) -> AsyncIterator[Database]:
    owner_url = URL.create(
        "postgresql+asyncpg",
        username=postgres.username,
        password=postgres.password,
        host=postgres.get_container_host_ip(),
        port=int(postgres.get_exposed_port(5432)),
        database=postgres.dbname,
    )
    password = secrets.token_urlsafe(32)
    owner = create_async_engine(owner_url, hide_parameters=True)
    try:
        await initialize_database(owner, bootstrap_sql, password)
        runtime_url = owner_url.set(username="sahulat_test_login", password=password)
        settings = DatabaseSettings(
            database_url=SecretStr(runtime_url.render_as_string(hide_password=False))
        )
        runtime = create_database_engine(settings)
        data = Database(
            owner,
            runtime,
            async_sessionmaker(runtime, expire_on_commit=False),
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        try:
            await seed_tenants(data)
            await seed_admin_users(data)
            yield data
        finally:
            await runtime.dispose()
            async with owner.begin() as connection:
                await connection.run_sync(migrate, "base")
                await connection.execute(text("DROP ROLE sahulat_test_login"))
                await connection.execute(text("DROP ROLE sahulat_runtime"))
    finally:
        await owner.dispose()
