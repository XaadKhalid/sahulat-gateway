"""Dispatch intents (SAH-005)."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispatch_intents",
        sa.Column("tenant_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("message_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "message_id"],
            ["sahulat.messages.tenant_id", "sahulat.messages.id"],
            name="dispatch_intent_message_fk",
        ),
        schema="sahulat",
    )
    op.execute("ALTER TABLE sahulat.dispatch_intents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sahulat.dispatch_intents FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON sahulat.dispatch_intents
        USING (tenant_id = sahulat.current_tenant_id())
        WITH CHECK (tenant_id = sahulat.current_tenant_id())
    """)
    op.execute("GRANT SELECT, INSERT ON sahulat.dispatch_intents TO sahulat_runtime")


def downgrade() -> None:
    op.drop_table("dispatch_intents", schema="sahulat")
