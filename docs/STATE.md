# STATE.md — Current Truth

**Last updated:** 2026-09-16 by Codex
**Current milestone:** M0 — Walking skeleton
**Build status:** Green locally for SAH-002 on Python 3.12.14; CI configured but not run remotely.

## Where the project actually is

SAH-001 and SAH-002 are complete. The owner approved ADRs 0001 and 0002.
The FastAPI application factory runs through Uvicorn and exposes public GET
/health with a typed process-liveness response. It loads validated environment
configuration at factory invocation, not import time. Documentation routes are
disabled. A bounded per-process rate limit and no-body request policy cover this
bootstrap. No database, queue, tenant, WhatsApp or model implementation exists.

The uv manifest contains only approved SAH-002 packages; uv.lock is committed.
CI defines compilation, Ruff lint/format, strict mypy, import-linter and pytest.
Two import contracts cover currently implemented boundaries. A negative test
modifies a temporary copy and proves a forbidden import is rejected.

## In progress

No implementation task is partially complete. Current branch:
`task/SAH-002-application-bootstrap`.

## Next up, in order

1. SAH-003: tenant provisioning and isolated persistence; dependencies already approved.
2. SAH-004: append-only audit storage.
3. SAH-005: authenticated WhatsApp ingress; replace bootstrap's blanket body policy.
4. SAH-006: durable dispatch and worker recovery.
5. SAH-007: outbound text echo.
6. SAH-008: deployment and real-number demonstration.

Read the relevant docs/tasks file before implementation. Continue on a separate
`task/<id>-<slug>` branch based on the completed prerequisite work.

## Open questions blocking later work

| Question | Blocks | Who decides |
|---|---|---|
| Which deployment host/account, HTTPS domain, secret store, test number and operator will be used? | SAH-008 | Project owner |
| What retention period and authorized audit-reader role apply? | Deployment | Project owner |

## Gotchas

- System Python is 3.13.3; this project requires 3.12. Repository-local tooling is
  ignored: `.tools/uv/uv.exe` (0.12.15) and `.tools/python` (3.12.14).
- For local uv commands here, set UV_PYTHON_INSTALL_DIR to the absolute
  `.tools/python` path and UV_CACHE_DIR to `.uv-cache`, then invoke `.tools/uv/uv.exe`.
  No shell profile was modified. uv reported a denied optional Windows registry
  registration; the managed interpreter and virtual environment work without it.
- Docker CLI exists; engine availability has not been checked. SAH-003 must verify
  real PostgreSQL/Testcontainers tests; never substitute SQLite.
- Health means process liveness only. The fixed-window limiter is aggregate per
  process, not distributed/per-tenant. SAH-005 needs route-specific limits and
  webhook body handling. Deployment also needs connection/header/slow-client limits.
- No credentials are needed or defined yet. `.env` is ignored but not automatically
  loaded. Inject environment variables; do not commit secrets.
- The architecture negative test resolves lint-imports beside sys.executable;
  PATH discovery was unreliable in this Windows tool environment.
- The human reference is docs/source/sahulat-solution-design.html, not the filename
  mentioned in AGENTS.md. It remains pre-existing, untracked and unread.
- Git metadata writes require sandbox approval here.
- Provider API contracts and delivery guarantees still require primary-document
  verification during SAH-005/007. No provider exactly-once guarantee is assumed.

## Decisions made recently

- [ADR 0001](adr/0001-m0-contracts.md): accepted contract ownership, I/O protocol
  exception, durable dispatch, restricted audit evidence and pre-M5 operator review.
- [ADR 0002](adr/0002-m0-dependencies.md): accepted staged M0 dependency list.
- [ADR 0003](adr/0003-liveness-bootstrap.md): application factory, health semantics,
  bounded local probe policy and bootstrap quality gates.

## Deliberately not done

No database/Redis integration, WhatsApp adapter, future module stubs, deployment,
remote CI execution, or reads/changes to the original reference HTML. The service
is a local bootstrap; M0 is not yet complete.

## Session log

### 2026-09-16 — Codex — SAH-002
- Did: accepted the owner's ADR approvals; implemented runnable app, configuration,
  HTTP limits, test suite, lockfile and CI. Updated architecture/standards references.
- Validation: 15 tests pass; Ruff lint/format, strict mypy (14 files), compilation,
  and both import contracts pass. Real Uvicorn startup/HTTP probe passed. Offline
  `uv sync --locked` confirmed lock consistency. Remote CI has not been executed.
- Decided: process-only health with constant-memory aggregate throttling; ADR 0003.
- Assumed: no deployment credentials or account selection from dependency approval.
- Next: SAH-003. No implementation changes left uncommitted at session completion.

### 2026-09-16 — Codex — SAH-001
- Established the documentation-only baseline, eight task files and two ADR proposals.
- Owner subsequently approved both proposals; deployment requirements remain recorded
  as later prerequisites rather than guessed account choices.
