# STATE.md — Current Truth

**Last updated:** 2026-09-17 by Codex
**Current milestone:** M0 — Walking skeleton
**Build status:** SAH-006 commit a7da665 failed GitHub Quality run #14 (owner screenshots). Local Ruff and strict-mypy failures are repaired; remote logs and a remote rerun are unverified. See the latest session log for validation.

## Where the project actually is

SAH-001, SAH-002, SAH-003, and SAH-004 are complete. The owner approved ADRs 0001, 0002, 0004, and 0005.
The FastAPI application factory runs through Uvicorn and exposes public GET
/health with a typed process-liveness response. It loads validated environment
configuration at factory invocation, not import time. Documentation routes are
disabled. A bounded per-process rate limit and no-body request policy cover this
bootstrap. 
Tenant provisioning and isolated persistence exist using PostgreSQL. The database enforces Row-Level Security (RLS) to isolate tenants. Repositories manage sessions and messages with idempotency constraints. A partitioned, append-only audit event table exists to store critical events securely. Standard operational logging redacts phone numbers and payloads. SAH-005 authenticated WhatsApp ingress is committed. SAH-006 adds dispatch state, a restricted claim function, arq enqueueing and worker transitions, but is not complete. No model or outbound echo implementation exists.

The uv manifest includes PostgreSQL, migration, arq/Redis and Testcontainers dependencies; uv.lock is committed. This repair adds no dependencies.
CI defines compilation, Ruff lint/format, strict mypy, import-linter and pytest.
Five import contracts cover currently implemented boundaries. A negative test
modifies a temporary copy and proves a forbidden import is rejected.

## In progress

Current repair branch: `task/SAH-006-ci-repair`, based on a7da665.
The earlier state document lagged behind the committed SAH-005/006 code.
SAH-006 remains incomplete: the processor is a no-op that the worker can mark
completed; workers lack a conditional claim/stale-processing recovery; dispatch
transitions lack audit events. Dispatch tests use a queue fake, not real Redis.
These require follow-up within SAH-006, not a claim that passing CI completes M0.

## Next up, in order

1. Complete/review SAH-006 against its task and ADR 0001, including recovery,
   concurrency, transition audit and real-Redis verification.
2. SAH-007: outbound text echo.
3. SAH-008: deployment and real-number demonstration.

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
- Docker/Testcontainers PostgreSQL works outside the sandbox. The sandbox cannot
  access the Docker named pipe; tests require approved Docker access here.
- Health means process liveness only. The fixed-window limiter is aggregate per
  process, not distributed/per-tenant. SAH-005 needs route-specific limits and
  webhook body handling. Deployment also needs connection/header/slow-client limits.
- Database, Redis and WhatsApp settings now require runtime configuration.
  `.env` is ignored but not automatically loaded. Inject environment variables;
  do not commit secrets.
- The architecture negative test resolves lint-imports beside sys.executable;
  PATH discovery was unreliable in this Windows tool environment.
- The human reference is docs/source/sahulat-solution-design.html, not the filename
  mentioned in AGENTS.md. It is now tracked by prior work and remains unread here.
- Git metadata writes require sandbox approval here.
- Provider API contracts and delivery guarantees still require primary-document
  verification during SAH-005/007. No provider exactly-once guarantee is assumed.
- pytest can hit Windows temp/cache ownership errors. Disable its optional cache
  with `-p no:cacheprovider` and use a fresh, previously nonexistent workspace
  `--basetemp` directory. Do not skip failing tests to conceal permissions errors.

## Decisions made recently

- [ADR 0001](adr/0001-m0-contracts.md): accepted contract ownership, I/O protocol
  exception, durable dispatch, restricted audit evidence and pre-M5 operator review.
- [ADR 0002](adr/0002-m0-dependencies.md): accepted staged M0 dependency list.
- [ADR 0003](adr/0003-liveness-bootstrap.md): application factory, health semantics,
  bounded local probe policy and bootstrap quality gates.
- [ADR 0004](adr/0004-tenant-persistence.md): accepted tenant-scoped PostgreSQL persistence with Row-Level Security.
- [ADR 0005](adr/0005-audit-storage.md): accepted declarative PostgreSQL partitioning and strict insert-only database grants for audit logs.

## Deliberately not done

This CI repair does not complete dispatch recovery, implement outbound echo,
deploy, publish a branch, or change the original reference HTML. The owner
declined network escalation to read Actions logs; the remote failed step is
unknown. M0 is not yet complete.

## Session log

### 2026-09-17 — Codex — SAH-006 CI repair
- Did: repaired seven Ruff errors and sixteen strict-mypy errors reproduced on
  a7da665. Added a consumer-owned queue protocol, typed test doubles, adopted
  StrEnum and wrapped long comments/logging/SQL without changing dispatch policy.
  Corrected stale STATE claims using committed code as truth.
- Validation: 60 tests pass with Docker access and a fresh workspace basetemp;
  Ruff lint/format, strict mypy (59 source files), compilation, all five import
  contracts and git diff whitespace checks pass. An earlier run had 59 passes
  and one Windows temp-directory permission error, resolved by the fresh path.
- Decided: apply ADR 0001's existing required-I/O-protocol exception; no new
  architectural decision or dependency. Limit this task to quality-check repair.
- Assumed: local failures explain likely CI blockers, not proof of the unseen
  remote step. Screenshots expose only exit code 1; remote rerun remains unverified.
- Next: review/complete the SAH-006 gaps above before SAH-007. No push or deployment.

### 2026-09-16 — Antigravity — SAH-004
- Did: Created `AuditRow` with partitioned boundaries and restricted INSERT-only grants. Implemented `AuditRepository` for transactional event logging. Wrote `RedactingFormatter` to protect operational logs.
- Validation: Integration tests prove `UPDATE`/`DELETE` are impossible. Unit tests confirm redaction rules work.
- Decided: Built-in `logging.Formatter` used rather than importing structural loggers. Partition provisioning procedure encapsulated inside Postgres.
- Assumed: N/A.
- Next: SAH-005.

### 2026-09-16 — Antigravity — SAH-003
- Did: Reviewed uncommitted SAH-003 codebase left by previous agent. Verified acceptance criteria are met. Tests confirm isolation boundaries and RLS protection. Committed the work.
- Validation: Integration tests passed successfully on Testcontainers Postgres.
- Decided: Proceed with existing work as it accurately models ADR 0004.
- Assumed: N/A.
- Next: SAH-004.

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


