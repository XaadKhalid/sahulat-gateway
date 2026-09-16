# SAH-003 - Add tenant provisioning and isolated persistence

Branch: task/SAH-003-tenant-persistence
Prerequisites: SAH-002; ADR 0001 and persistence dependency approval

## Scope

Implement tenants, sessions and messages with async repositories and a documented test-tenant provisioning procedure.

## Acceptance criteria

- [ ] Reversible migrations build and remove the schema on real PostgreSQL 16.
- [ ] Tenant routing is narrowly scoped and documented; unrecognized routes cannot access tenant data.
- [ ] Runtime database role cannot bypass RLS; missing tenant context fails closed.
- [ ] Tests prove read/write isolation, including pooled connection reuse across tenants.
- [ ] Repositories use injected async sessions, UTC timestamps, and typed boundaries.
- [ ] Message identity constraints support deduplication and session uniqueness.

## Out of scope

Identity lookup, OTP, admin UI, live credentials.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.
