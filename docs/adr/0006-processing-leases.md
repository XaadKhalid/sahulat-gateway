# 0006. Processing leases and stable outbound identity

Date: 2026-09-17
Status: accepted (owner requested lease recovery and explicit idempotency)

## Decision

- Persist a five-minute `lease_expires_at` and per-claim UUID `claim_token`.
  A conditional enqueued-to-processing update permits one current owner.
  Database time governs acquisition, expiry and result writes. Worker timeout
  is four minutes, leaving a margin before reclaim; no heartbeat is required
  for the bounded M0 work.
- The restricted dispatcher function also claims expired processing rows using
  `FOR UPDATE SKIP LOCKED`, clearing the old token. Every worker result requires
  a matching, unexpired token. A delayed old worker cannot change replacement
  state. Reversible migration 0005 expires legacy processing rows on upgrade.
- Each queue delivery gets a fresh UUID suffix. arq retains job/result keys and
  rejects enqueueing the same queue ID while those keys exist. Database claims,
  rather than Redis retention, control concurrent ownership. The tenant/message
  pair remains the stable logical identity across all deliveries.
- The processor requires keyword `idempotency_key`, always
  `intent:<tenant_uuid>:<message_uuid>`. SAH-007 must forward it unchanged to
  retryable outbound writes and prove that behavior before merge. The existing
  persisted tenant/message primary key supplies this identity; no extra
  idempotency-key column or later identity migration is required.
- Until outbound processing exists, the default processor explicitly fails
  terminally rather than pretending to complete work. Tests inject processors.

## Limits and rollout

Drain/stop old workers before migration and restart with the new code: old
workers do not fence writes. Do not run mixed worker versions.

A lease fences database state, not an already-running external side effect.
The explicit key is not a claim that WhatsApp supports provider deduplication.
Before outbound integration merges, SAH-007 must implement ADR 0001's uncertain
submission/review behavior and test crashes around sending. An expired lease
alone cannot authorize a blind resend of an uncertain external write.

This change does not recover lost enqueued jobs, change retry budgets/backoff,
or complete transition auditing. Those remain SAH-006 follow-up work.
