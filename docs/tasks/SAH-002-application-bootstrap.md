# SAH-002 - Bootstrap application and quality gates

Branch: task/SAH-002-application-bootstrap
Prerequisites: ADR 0002 dependency approval; SAH-001 documentation

## Scope

Create the smallest runnable Python 3.12 FastAPI application and reproducible quality checks.

## Acceptance criteria

- [ ] uv manifest and lock reproduce the environment on Python 3.12.
- [ ] Application factory and health endpoint work; imports perform no I/O.
- [ ] Typed configuration uses environment values with no secret defaults.
- [ ] Public health-route exposure, limits, and access expectations are explicit.
- [ ] CI runs behavior tests, Ruff check/format, strict mypy, and initial import contracts.
- [ ] Negative architecture check proves a forbidden import is rejected.

## Out of scope

Database, WhatsApp integration, future milestone module stubs.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.
