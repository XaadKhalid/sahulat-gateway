"""Bound worker claims and reclaim abandoned processing intents."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dispatch_intents",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        schema="sahulat",
    )
    op.add_column(
        "dispatch_intents",
        sa.Column("claim_token", sa.Uuid(), nullable=True),
        schema="sahulat",
    )
    # Existing processing rows have no owner that the new worker can fence.
    op.execute("""
        UPDATE sahulat.dispatch_intents SET lease_expires_at = now()
        WHERE state = 'processing'
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION sahulat.claim_pending_intents(batch_size integer)
        RETURNS TABLE (tenant_id uuid, message_id uuid)
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp
        AS $$
            UPDATE sahulat.dispatch_intents
            SET state = 'enqueued', lease_expires_at = NULL, claim_token = NULL
            WHERE (tenant_id, message_id) IN (
                SELECT d.tenant_id, d.message_id
                FROM sahulat.dispatch_intents d
                WHERE d.state = 'pending'
                    OR (d.state = 'failed_retry' AND d.next_attempt_at <= now())
                    OR (d.state = 'processing' AND d.lease_expires_at < now())
                FOR UPDATE SKIP LOCKED
                LIMIT batch_size
            )
            RETURNING tenant_id, message_id;
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION sahulat.claim_pending_intents(batch_size integer)
        RETURNS TABLE (tenant_id uuid, message_id uuid)
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp
        AS $$
            UPDATE sahulat.dispatch_intents
            SET state = 'enqueued'
            WHERE (tenant_id, message_id) IN (
                SELECT d.tenant_id, d.message_id
                FROM sahulat.dispatch_intents d
                WHERE d.state = 'pending'
                    OR (d.state = 'failed_retry' AND d.next_attempt_at <= now())
                FOR UPDATE SKIP LOCKED
                LIMIT batch_size
            )
            RETURNING tenant_id, message_id;
        $$;
    """)
    op.drop_column("dispatch_intents", "claim_token", schema="sahulat")
    op.drop_column("dispatch_intents", "lease_expires_at", schema="sahulat")
