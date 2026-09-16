"""Tenant-isolated conversation persistence (SAH-003)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def create_tenants() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.CheckConstraint("length(name) > 0", name="tenant_name_not_empty"),
        schema="sahulat",
    )
    op.create_table(
        "tenant_routes",
        sa.Column("route_key", sa.String(256), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False, unique=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["sahulat.tenants.id"]),
        sa.CheckConstraint("length(route_key) > 0", name="route_key_not_empty"),
        schema="sahulat_private",
    )


def create_sessions() -> None:
    op.create_table(
        "sessions",
        sa.Column("tenant_id", sa.Uuid(), primary_key=True),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_number", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["sahulat.tenants.id"]),
        sa.UniqueConstraint(
            "tenant_id", "customer_number", name="session_customer_unique"
        ),
        sa.CheckConstraint(
            "length(customer_number) > 0", name="session_customer_not_empty"
        ),
        schema="sahulat",
    )


def create_messages() -> None:
    op.create_table(
        "messages",
        sa.Column("tenant_id", sa.Uuid(), primary_key=True),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("provider_message_id", sa.String(256), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "session_id"],
            ["sahulat.sessions.tenant_id", "sahulat.sessions.id"],
            name="message_session_same_tenant",
        ),
        sa.UniqueConstraint(
            "tenant_id", "provider_message_id", name="message_provider_unique"
        ),
        sa.CheckConstraint("channel = 'whatsapp'", name="message_supported_channel"),
        sa.CheckConstraint(
            "length(provider_message_id) > 0", name="message_provider_not_empty"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(content) = 'object'", name="message_content_object"
        ),
        schema="sahulat",
    )


def enable_tenant_isolation() -> None:
    op.execute("""
        CREATE FUNCTION sahulat.current_tenant_id() RETURNS uuid
        LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp
        AS $$ SELECT NULLIF(current_setting('sahulat.tenant_id', true), '')::uuid $$
    """)
    op.execute("REVOKE ALL ON FUNCTION sahulat.current_tenant_id() FROM PUBLIC")
    op.execute(
        "GRANT EXECUTE ON FUNCTION sahulat.current_tenant_id() TO sahulat_runtime"
    )
    for statement in (
        "ALTER TABLE sahulat.tenants ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE sahulat.tenants FORCE ROW LEVEL SECURITY",
        "ALTER TABLE sahulat.sessions ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE sahulat.sessions FORCE ROW LEVEL SECURITY",
        "ALTER TABLE sahulat.messages ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE sahulat.messages FORCE ROW LEVEL SECURITY",
        """CREATE POLICY tenant_isolation ON sahulat.tenants
        USING (id = sahulat.current_tenant_id())
        WITH CHECK (id = sahulat.current_tenant_id())""",
        """CREATE POLICY tenant_isolation ON sahulat.sessions
        USING (tenant_id = sahulat.current_tenant_id())
        WITH CHECK (tenant_id = sahulat.current_tenant_id())""",
        """CREATE POLICY tenant_isolation ON sahulat.messages
        USING (tenant_id = sahulat.current_tenant_id())
        WITH CHECK (tenant_id = sahulat.current_tenant_id())""",
    ):
        op.execute(statement)


def grant_runtime_access() -> None:
    op.execute("""
        CREATE FUNCTION sahulat.resolve_tenant_route(route_key text) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, pg_temp
        AS $$ SELECT route.tenant_id FROM sahulat_private.tenant_routes AS route
              WHERE route.route_key = $1 $$
    """)
    op.execute("REVOKE ALL ON FUNCTION sahulat.resolve_tenant_route(text) FROM PUBLIC")
    op.execute(
        "GRANT EXECUTE ON FUNCTION sahulat.resolve_tenant_route(text) "
        "TO sahulat_runtime"
    )
    op.execute("GRANT USAGE ON SCHEMA sahulat TO sahulat_runtime")
    op.execute(
        "GRANT SELECT ON sahulat.tenants, sahulat.sessions, sahulat.messages "
        "TO sahulat_runtime"
    )
    op.execute("GRANT INSERT ON sahulat.sessions, sahulat.messages TO sahulat_runtime")


def upgrade() -> None:
    op.execute("CREATE SCHEMA sahulat")
    op.execute("CREATE SCHEMA sahulat_private")
    op.execute("REVOKE ALL ON SCHEMA sahulat, sahulat_private FROM PUBLIC")
    create_tenants()
    create_sessions()
    create_messages()
    enable_tenant_isolation()
    grant_runtime_access()


def downgrade() -> None:
    op.execute("DROP FUNCTION sahulat.resolve_tenant_route(text)")
    op.drop_table("messages", schema="sahulat")
    op.drop_table("sessions", schema="sahulat")
    op.drop_table("tenant_routes", schema="sahulat_private")
    op.drop_table("tenants", schema="sahulat")
    op.execute("DROP FUNCTION sahulat.current_tenant_id()")
    op.execute("DROP SCHEMA sahulat_private")
    op.execute("DROP SCHEMA sahulat")
