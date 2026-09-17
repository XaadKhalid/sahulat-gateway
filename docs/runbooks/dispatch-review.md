# Dispatch outage and operator review

This is the M0 manual handoff required by ADR 0001, not a customer-facing inbox.
Use an authorized database operator login; never give audit readers write grants.
Configure database credentials outside command text/source.

## Outage recovery

Run the arq worker/dispatcher after PostgreSQL and Redis recover. A dispatch claim
commits with a 60-second enqueue lease before contacting Redis. Failure, lost
Redis data or a crash before enqueue leaves recoverable work. The next poll after
expiry delivers again. Unexpired processing is not stolen. Processing has a
five-minute lease with a four-minute worker timeout. State and audit commit
together; missing audit partitions block progress rather than silently dropping
evidence. Run the existing partition-provisioning procedure before rollover.

## Review queue

Using a tenant-scoped transaction (`set_config('sahulat.tenant_id', tenant UUID,
true)`), query `sahulat.dispatch_intents WHERE state = 'review_required'`, ordered
by tenant/message ID. Inspect `state_reason` and the corresponding
`sahulat.audit_events` whose `details->>'message_id'` matches the message UUID.
Unknown processor outcomes, explicit review requests and exhausted retries are
held here. Dispatcher and worker exclude these records from automatic execution.

Reconcile any potential provider acceptance before taking action. Until SAH-007
is wired, there are no provider sends. Once sending exists, an internal
idempotency key is not proof that the provider deduplicates requests.

To close without resend, run `scripts/close_dispatch_review.sql` with psql
`-v ON_ERROR_STOP=1 -v tenant_id=<uuid> -v message_id=<uuid>`. A returned row confirms
closure; zero rows means it was absent, hidden by tenant isolation or already
resolved. The trigger records the operator login and transition atomically.
There is deliberately no automatic retry/resend button for uncertain outcomes.
Use a new customer interaction/manual handoff if further response is needed.

Check this queue and terminal failures during M0 operation. Automated alerts and
the M5 inbox are not implemented; the deployment operator owns these checks.
