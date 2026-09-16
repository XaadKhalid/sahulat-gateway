# SAH-004 - Implement append-only audit storage

Branch: task/SAH-004-audit-storage
Prerequisites: SAH-003; approved audit boundary in ADR 0001

## Scope

Implement tenant-isolated typed audit events and monthly partitions for M0.

## Acceptance criteria

- [ ] Application role can append permitted events but cannot update/delete audit rows.
- [ ] Partition creation and rollover procedure works and is documented.
- [ ] Cross-tenant audit access is denied under the runtime role.
- [ ] Correlated immutable message references reconstruct M0 exchanges.
- [ ] Operational logging omits message bodies, phone numbers and credentials.
- [ ] Audit persistence failures propagate; message and initial audit writes can share one transaction.

## Out of scope

Audit viewer, analytics, later-milestone event implementations.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.
