# 0001. M0 contracts, durable delivery, and audit boundaries
Date: 2026-09-16
Status: proposed

## Context

SAH-001 found conflicting protocol ownership and abstraction requirements, plus
unspecified recovery and audit behavior. M0 must prove a text echo without
implementing later milestones. Owner approval is required before changing
conflicting requirements or implementing the dependent behavior.

## Decision proposed

1. Put MessageEnvelope and channel-neutral payloads in app/schemas/messages.py.
   Consumer-owned outbound and repository protocols live with orchestration.
   Provider parsing stays in channels/whatsapp; orchestration never imports
   channels. Split normalization from sending according to consumer needs.
   Use ChannelAdapter consistently instead of the IChannelAdapter spelling.
2. Required I/O boundary protocols are exempt from the single-implementation ban.
   Introduce them only when consumed by implemented behavior; no empty future
   modules or speculative plugin mechanisms. Schemas may depend on Pydantic
   and the standard library, but not application services or I/O.
3. M0 echoes plain text only. A tagged content model also represents unsupported
   content as metadata, without processing media. Interactive messages and
   templates remain phase-1 work but are not M0 echo requirements. Status events
   never trigger echoes. Verify provider event and response semantics in SAH-005.
4. Persist the inbound message, initial audit event and durable dispatch record
   in one PostgreSQL transaction. Dispatch records form a small transactional
   outbox, not a generic event bus. An arq dispatcher retries enqueueing; worker
   claims and stable internal message identifiers prevent concurrent sends.
   Resolve minimal tenant routing before persistence through a narrowly scoped
   routing lookup, not arbitrary application access bypassing RLS.
5. Treat dispatch as at least once; do not claim provider exactly-once sending.
   Uncertain submissions become needs_review with durable audit evidence rather
   than automatic resend. Verify provider semantics before specifying retryable
   responses and backoff in SAH-007. Test crashes around outbound submissions.
6. Operational logs hold correlation identifiers and redacted errors, not text
   or phone numbers. Restricted tenant-isolated conversation storage holds
   reconstructable content; append-only audit links immutable message records
   and processing transitions. General log readers cannot read transcripts.
   Never persist credentials or OTP values in either stream. Retention and reader
   access require owner decisions before deployment. This clarifies full audit;
   it does not authorize omitting conversation evidence.
7. Until the M5 inbox exists, failures and uncertain work remain durably marked
   for an operator through a manual runbook. This is not a completed human
   handoff feature. Do not fabricate replies or build the inbox in M0.
8. Only send M0 echoes inside the provider's permitted reply window; hold stale
   work for review. Do not invent an approved template.

## Consequences

These choices preserve inward dependencies and constrain M0 scope. Durable
redispatch adds a narrowly scoped persistence concern. Delivery uncertainty is
visible rather than disguised as success. Restricted transcripts need access
control and retention policy. Manual operator handling requires an explicit
exception to the standards' human-handoff requirement until M5.

## Alternatives considered

- Import channels from orchestration: violates the dependency rule.
- Create every protocol now: conflicts with milestone scope.
- Persist then enqueue only once: can strand accepted messages.
- Retry uncertain sends blindly: can duplicate customer-visible responses.
- Raw transcripts in general logs: violates PII protection.
- Build the inbox now: pulls M5 into M0.
