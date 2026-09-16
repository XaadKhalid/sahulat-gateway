"""Audit storage partitioning and isolation (SAH-004)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def create_audit_table() -> None:
    op.create_table(
        "audit_events",
        sa.Column("tenant_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), primary_key=True, nullable=False
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("length(event_type) > 0", name="audit_event_type_not_empty"),
        sa.CheckConstraint("length(actor) > 0", name="audit_actor_not_empty"),
        sa.CheckConstraint(
            "jsonb_typeof(details) = 'object'", name="audit_details_object"
        ),
        schema="sahulat",
        postgresql_partition_by="RANGE (occurred_at)",
    )


def setup_partition_provisioning() -> None:
    op.execute("""
        CREATE OR REPLACE PROCEDURE sahulat_private.provision_audit_partitions()
        LANGUAGE plpgsql
        AS $$
        DECLARE
            current_month_start DATE := date_trunc('month', current_date);
            next_month_start DATE := current_month_start + interval '1 month';
            next_next_month_start DATE := next_month_start + interval '1 month';
            current_partition text := 'audit_events_' || 
                                      to_char(current_month_start, 'YYYY_MM');
            next_partition text := 'audit_events_' || 
                                   to_char(next_month_start, 'YYYY_MM');
        BEGIN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS sahulat.%I '
                'PARTITION OF sahulat.audit_events '
                'FOR VALUES FROM (%L) TO (%L);',
                current_partition, current_month_start, next_month_start
            );
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS sahulat.%I '
                'PARTITION OF sahulat.audit_events '
                'FOR VALUES FROM (%L) TO (%L);',
                next_partition, next_month_start, next_next_month_start
            );
        END;
        $$;
    """)
    op.execute(
        "REVOKE ALL ON PROCEDURE sahulat_private.provision_audit_partitions() "
        "FROM PUBLIC"
    )
    op.execute("CALL sahulat_private.provision_audit_partitions()")


def enable_audit_isolation() -> None:
    op.execute("ALTER TABLE sahulat.audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sahulat.audit_events FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON sahulat.audit_events
        USING (tenant_id = sahulat.current_tenant_id())
        WITH CHECK (tenant_id = sahulat.current_tenant_id())
    """)


def grant_audit_access() -> None:
    op.execute("GRANT SELECT, INSERT ON sahulat.audit_events TO sahulat_runtime")


def upgrade() -> None:
    create_audit_table()
    setup_partition_provisioning()
    enable_audit_isolation()
    grant_audit_access()


def downgrade() -> None:
    op.execute("DROP PROCEDURE sahulat_private.provision_audit_partitions()")
    op.drop_table("audit_events", schema="sahulat")
