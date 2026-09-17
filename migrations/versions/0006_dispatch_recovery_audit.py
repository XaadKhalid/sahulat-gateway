"""Audit every dispatch transition and lease queue deliveries (SAH-006)."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dispatch_intents",
        sa.Column(
            "state_reason", sa.String(100), nullable=False, server_default="created"
        ),
        schema="sahulat",
    )
    op.execute("""
        CREATE FUNCTION sahulat_private.audit_dispatch_transition()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp AS $$
        BEGIN
            IF TG_OP = 'INSERT' OR OLD.state IS DISTINCT FROM NEW.state
                OR OLD.lease_expires_at IS DISTINCT FROM NEW.lease_expires_at
                OR OLD.state_reason IS DISTINCT FROM NEW.state_reason THEN
                INSERT INTO sahulat.audit_events
                    (tenant_id, id, occurred_at, event_type, actor, details)
                VALUES (NEW.tenant_id, gen_random_uuid(), clock_timestamp(),
                    'dispatch.transition', session_user,
                    jsonb_build_object('message_id', NEW.message_id,
                        'from_state', CASE WHEN TG_OP = 'INSERT' THEN NULL
                                          ELSE OLD.state::text END,
                        'to_state', NEW.state, 'reason', NEW.state_reason,
                        'attempts', NEW.attempts,
                        'lease_expires_at', NEW.lease_expires_at));
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        REVOKE ALL ON FUNCTION sahulat_private.audit_dispatch_transition() FROM PUBLIC
    """)
    op.execute("""
        CREATE TRIGGER dispatch_transition_audit
            AFTER INSERT OR UPDATE ON sahulat.dispatch_intents
            FOR EACH ROW EXECUTE FUNCTION sahulat_private.audit_dispatch_transition();
    """)
    op.execute("""
        UPDATE sahulat.dispatch_intents SET lease_expires_at = now(),
            state_reason = 'legacy_enqueue_expired'
        WHERE state = 'enqueued' AND lease_expires_at IS NULL
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION sahulat.claim_pending_intents(batch_size integer)
        RETURNS TABLE (tenant_id uuid, message_id uuid)
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
            WITH candidates AS (
                SELECT d.tenant_id, d.message_id, d.state
                FROM sahulat.dispatch_intents d
                WHERE d.state = 'pending'
                    OR (d.state = 'failed_retry' AND d.next_attempt_at <= now())
                    OR (d.state IN ('processing', 'enqueued')
                        AND d.lease_expires_at < now())
                FOR UPDATE SKIP LOCKED LIMIT batch_size
            )
            UPDATE sahulat.dispatch_intents d
            SET state = 'enqueued', lease_expires_at = now() + interval '60 seconds',
                claim_token = NULL,
                state_reason = CASE c.state
                    WHEN 'enqueued' THEN 'enqueue_lease_expired'
                    WHEN 'processing' THEN 'processing_lease_expired'
                    ELSE 'queued' END
            FROM candidates c
            WHERE d.tenant_id = c.tenant_id AND d.message_id = c.message_id
            RETURNING d.tenant_id, d.message_id;
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION sahulat.claim_pending_intents(batch_size integer)
        RETURNS TABLE (tenant_id uuid, message_id uuid)
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
            UPDATE sahulat.dispatch_intents
            SET state = 'enqueued', lease_expires_at = NULL, claim_token = NULL
            WHERE (tenant_id, message_id) IN (
                SELECT d.tenant_id, d.message_id FROM sahulat.dispatch_intents d
                WHERE d.state = 'pending'
                    OR (d.state = 'failed_retry' AND d.next_attempt_at <= now())
                    OR (d.state = 'processing' AND d.lease_expires_at < now())
                FOR UPDATE SKIP LOCKED LIMIT batch_size
            ) RETURNING tenant_id, message_id;
        $$;
    """)
    op.execute("DROP TRIGGER dispatch_transition_audit ON sahulat.dispatch_intents")
    op.execute("DROP FUNCTION sahulat_private.audit_dispatch_transition()")
    op.drop_column("dispatch_intents", "state_reason", schema="sahulat")
