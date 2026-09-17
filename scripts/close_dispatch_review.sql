-- Run with an operator login and psql -v tenant_id=... -v message_id=...
-- Closing explicitly declines automatic resend; inspect evidence first.
BEGIN;
SELECT set_config('sahulat.tenant_id', :'tenant_id', true);
UPDATE sahulat.dispatch_intents
SET state = 'failed_terminal', state_reason = 'operator_closed_without_resend',
    lease_expires_at = NULL, claim_token = NULL
WHERE tenant_id = :'tenant_id'::uuid AND message_id = :'message_id'::uuid
    AND state = 'review_required'
RETURNING tenant_id, message_id, state, state_reason;
COMMIT;
