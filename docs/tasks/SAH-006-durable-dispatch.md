# SAH-006 - Add durable dispatch and worker recovery

Branch: task/SAH-006-durable-dispatch
Prerequisites: SAH-005; queue dependencies approved

## Scope

Deliver durable dispatch records to arq with safe retries and a framework-free worker service.

## Acceptance criteria

- [ ] Persisted work survives queue outage and dispatcher restart.
- [ ] Stable job/message identifiers and database claims prevent concurrent processing.
- [ ] Crash/restart, duplicate enqueue and expired worker-claim paths are tested.
- [ ] Webhook processing does not wait for outbound completion.
- [ ] Workers persist attempts, retryable failures, terminal failures and review-required states.
- [ ] Integration tests use real PostgreSQL and Redis where queue guarantees are exercised.

## Out of scope

Generic event bus, Celery, Temporal, model orchestration.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.
