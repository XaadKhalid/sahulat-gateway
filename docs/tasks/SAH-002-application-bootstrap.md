# SAH-002 - Bootstrap application and quality gates

Branch: task/SAH-002-application-bootstrap
Prerequisites: ADR 0002 dependency approval; SAH-001 documentation

## Scope

Create the smallest runnable Python 3.12 FastAPI application and reproducible quality checks.

## Acceptance criteria

- [x] uv manifest and lock reproduce the environment on Python 3.12.
- [x] Application factory and health endpoint work; imports perform no I/O.
- [x] Typed configuration uses environment values with no secret defaults.
- [x] Public health-route exposure, limits, and access expectations are explicit.
- [x] CI runs behavior tests, Ruff check/format, strict mypy, and initial import contracts.
- [x] Negative architecture check proves a forbidden import is rejected.

## Out of scope

Database, WhatsApp integration, future milestone module stubs.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.

## Validation evidence

15 tests pass on Python 3.12.14. Compilation, Ruff lint/format, strict mypy,
and both import contracts pass. Real Uvicorn startup and HTTP health probe passed.
Offline locked sync succeeds. CI workflow is committed; remote execution awaits push.
