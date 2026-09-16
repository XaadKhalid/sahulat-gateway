# SAH-008 - Deploy and demonstrate M0

Branch: task/SAH-008-m0-deployment
Prerequisites: SAH-007; owner-supplied deployment target, test-number access, retention/access policy and operator

## Scope

Deploy the M0 service and worker, validate a real test-number exchange, and document operation.

## Acceptance criteria

- [ ] All local/CI build, lint, format, strict typing and tests pass.
- [ ] Deployment uses externally provisioned secrets, TLS and least-privilege database roles.
- [ ] Real test-number text is received, persisted, echoed and reconstructed through audit.
- [ ] Deployment records release revision and sanitized evidence without credentials or full PII.
- [ ] Migration, partition maintenance, queue recovery, uncertain-send review and rollback runbooks are usable.
- [ ] STATE.md records observed results, remaining limitations and the next milestone.

## Out of scope

Unapproved cloud provisioning/costs, production rollout, M1 features.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.
