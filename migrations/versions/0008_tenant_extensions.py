"""Tenant business-profile columns, documents table, and admin RLS views (SAH-002)."""

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str = "0007"
branch_labels: str | None = None
depends_on: str | None = None

_TENANT_COLUMNS = {
    "status": ("draft", "TEXT"),
    "whatsapp_connected": (False, "BOOLEAN"),
    "manifest_status": ("pending", "TEXT"),
}


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        schema="sahulat",
    )
    op.add_column(
        "tenants",
        sa.Column(
            "whatsapp_connected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="sahulat",
    )
    op.add_column(
        "tenants",
        sa.Column(
            "manifest_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        schema="sahulat",
    )
    op.add_column(
        "tenants",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="sahulat",
    )
    op.create_table(
        "tenant_documents",
        sa.Column("tenant_id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="processing",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('processing', 'ready', 'failed')",
            name="doc_status_valid",
        ),
        sa.CheckConstraint("length(filename) > 0", name="doc_filename_not_empty"),
        sa.CheckConstraint("size_bytes > 0", name="doc_size_positive"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["sahulat.tenants.id"], name="doc_tenant_fk"
        ),
        schema="sahulat",
    )
    op.create_index(
        "tenant_documents_tenant_idx",
        "tenant_documents",
        ["tenant_id"],
        schema="sahulat",
    )
    op.add_column(
        "tenants",
        sa.Column(
            "policy",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="sahulat",
    )
    op.execute("REVOKE ALL ON SCHEMA sahulat_admin FROM PUBLIC")
    op.execute("""
        CREATE FUNCTION sahulat_admin.list_tenants(
            p_limit integer, p_cursor uuid
        ) RETURNS TABLE (
            id uuid, name text, status text,
            whatsapp_connected boolean,
            created_at timestamptz
        )
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT t.id, t.name, t.status,
                   t.whatsapp_connected, t.created_at
            FROM sahulat.tenants t
            WHERE (p_cursor IS NULL OR t.id > p_cursor)
            ORDER BY t.id
            LIMIT p_limit
        $$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION sahulat_admin.list_tenants(integer, uuid) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION sahulat_admin.list_tenants(integer, uuid) "
        "TO sahulat_runtime"
    )
    op.execute("GRANT SELECT ON sahulat.tenant_documents TO sahulat_runtime")
    op.execute("GRANT INSERT, DELETE ON sahulat.tenant_documents TO sahulat_runtime")
    op.execute("GRANT UPDATE, INSERT ON sahulat.tenants TO sahulat_runtime")
    op.execute("GRANT USAGE ON SCHEMA sahulat_admin TO sahulat_runtime")
    op.execute("""
        CREATE FUNCTION sahulat_admin.get_tenant_detail(p_tenant uuid)
        RETURNS TABLE (
            id uuid, name text, status text,
            whatsapp_connected boolean,
            created_at timestamptz,
            document_count bigint,
            manifest_status text,
            policy jsonb
        )
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT t.id, t.name, t.status,
                   t.whatsapp_connected,
                   t.created_at,
                   (SELECT count(*) FROM sahulat.tenant_documents d
                    WHERE d.tenant_id = t.id),
                   t.manifest_status,
                   t.policy
            FROM sahulat.tenants t
            WHERE t.id = p_tenant
        $$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION sahulat_admin.get_tenant_detail(uuid) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION sahulat_admin.get_tenant_detail(uuid) "
        "TO sahulat_runtime"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS sahulat_admin.get_tenant_detail(uuid)")
    op.execute("DROP FUNCTION sahulat_admin.list_tenants(integer, uuid)")
    op.execute("DROP INDEX IF EXISTS sahulat.tenant_documents_tenant_idx")
    op.drop_table("tenant_documents", schema="sahulat")
    op.drop_column("tenants", "policy", schema="sahulat")
    op.drop_column("tenants", "created_at", schema="sahulat")
    op.drop_column("tenants", "manifest_status", schema="sahulat")
    op.drop_column("tenants", "whatsapp_connected", schema="sahulat")
    op.drop_column("tenants", "status", schema="sahulat")
