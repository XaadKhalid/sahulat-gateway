import io
import subprocess
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

from tests.integration.conftest import Database, migrate


async def test_migration_round_trip_recreates_rls_and_grants(
    database: Database,
) -> None:
    async with database.owner.begin() as connection:
        await connection.run_sync(migrate, "base")
        assert (
            await connection.scalar(text("SELECT to_regnamespace('sahulat')")) is None
        )
        assert (
            await connection.scalar(text("SELECT to_regnamespace('sahulat_private')"))
            is None
        )
        await connection.run_sync(migrate, "head")
    async with database.sessions() as session:
        assert await session.scalar(text("SELECT count(*) FROM sahulat.messages")) == 0
        assert (
            await session.scalar(text("SELECT sahulat.resolve_tenant_route('unknown')"))
            is None
        )
        assert (
            await session.scalar(
                text("SELECT current_setting('server_version_num')::int")
            )
            // 10000
            == 16
        )


def test_migrations_can_be_reviewed_as_offline_sql() -> None:
    output = io.StringIO()
    config = Config("alembic.ini", output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "SECURITY DEFINER" in sql
    assert (
        "REVOKE ALL ON FUNCTION sahulat.resolve_tenant_route(text) FROM PUBLIC" in sql
    )


def test_operator_provisioning_is_idempotent_and_conflicts_roll_back(
    database: Database, postgres: PostgresContainer
) -> None:
    script = Path("scripts/provision_tenant.sql").read_text(encoding="utf-8-sig")
    tenant_id = str(uuid4())
    container_id = postgres.get_wrapped_container().id
    assert isinstance(container_id, str)
    arguments = [
        "docker",
        "exec",
        "-i",
        container_id,
        "psql",
        "-U",
        postgres.username,
        "-d",
        postgres.dbname,
        "-v",
        "tenant_id=" + tenant_id,
        "-v",
        "tenant_name=Provisioned retailer",
        "-v",
        "route_key=provisioned-route",
    ]
    for _ in range(2):
        result = subprocess.run(
            arguments,
            input=script,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    arguments[-1] = "route_key=conflicting-route"
    result = subprocess.run(
        arguments, input=script, text=True, capture_output=True, timeout=30, check=False
    )
    assert result.returncode != 0
    assert "Registration conflicts" in result.stderr

    arguments[-1] = "route_key=provisioned-route"
    arguments[-5] = "tenant_id=" + str(uuid4())
    result = subprocess.run(
        arguments, input=script, text=True, capture_output=True, timeout=30, check=False
    )
    assert result.returncode != 0
    result = subprocess.run(
        [*arguments, "-At"],
        input="SELECT count(*) FROM sahulat.tenants WHERE id = :'tenant_id'::uuid;",
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0"
