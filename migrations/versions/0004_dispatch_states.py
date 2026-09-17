"""dispatch_states

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-17 08:54:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dispatch_state_enum = postgresql.ENUM(
        "pending",
        "enqueued",
        "processing",
        "completed",
        "failed_retry",
        "failed_terminal",
        "review_required",
        name="dispatch_state_enum",
        create_type=False,
    )
    dispatch_state_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "dispatch_intents",
        sa.Column(
            "state", dispatch_state_enum, server_default="pending", nullable=False
        ),
        schema="sahulat",
    )
    op.add_column(
        "dispatch_intents",
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        schema="sahulat",
    )
    op.add_column(
        "dispatch_intents",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        schema="sahulat",
    )
    op.execute("GRANT UPDATE ON sahulat.dispatch_intents TO sahulat_runtime")

    op.execute("""
        CREATE FUNCTION sahulat.claim_pending_intents(batch_size integer)
        RETURNS TABLE (tenant_id uuid, message_id uuid)
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp
        AS $$
            UPDATE sahulat.dispatch_intents
            SET state = 'enqueued'
            WHERE (tenant_id, message_id) IN (
                SELECT d.tenant_id, d.message_id
                FROM sahulat.dispatch_intents d
                WHERE d.state = 'pending' OR (d.state = 'failed_retry' AND d.next_attempt_at <= now())
                FOR UPDATE SKIP LOCKED
                LIMIT batch_size
            )
            RETURNING tenant_id, message_id;
        $$;
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION sahulat.claim_pending_intents(integer) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION sahulat.claim_pending_intents(integer) TO sahulat_runtime"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION sahulat.claim_pending_intents(integer)")
    op.drop_column("dispatch_intents", "next_attempt_at", schema="sahulat")
    op.drop_column("dispatch_intents", "attempts", schema="sahulat")
    op.drop_column("dispatch_intents", "state", schema="sahulat")

    dispatch_state_enum = postgresql.ENUM(
        "pending",
        "enqueued",
        "processing",
        "completed",
        "failed_retry",
        "failed_terminal",
        "review_required",
        name="dispatch_state_enum",
        create_type=False,
    )
    dispatch_state_enum.drop(op.get_bind(), checkfirst=True)
