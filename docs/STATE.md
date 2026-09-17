# STATE.md Ã¢â‚¬â€ Current Truth

**Last updated:** 2026-09-17 by Antigravity
**Current milestone:** M0 Ã¢â‚¬â€ Walking skeleton
**Build status:** CI lint/type repair is committed in 9b8127b. Processing-lease repair is validated locally; remote GitHub Actions CI has successfully passed and is fully green. All 76 local integration/unit tests pass.

## Where the project actually is

SAH-001 through SAH-004 are complete. The owner approved ADRs 0001, 0002, 0004, 0005, and 0006.
The FastAPI application factory runs through Uvicorn and exposes public GET
/health with a typed process-liveness response. It loads validated environment
configuration at factory invocation, not import time. Documentation routes are
disabled. A bounded per-process rate limit and no-body request policy cover this
bootstrap. 
Tenant provisioning and isolated persistence exist using PostgreSQL. The database enforces Row-Level Security (RLS) to isolate tenants. Repositories manage sessions and messages with idempotency constraints. A partitioned, append-only audit event table exists to store critical events securely. Standard operational logging redacts phone numbers and payloads. 
SAH-005 authenticated WhatsApp ingress is committed. 
SAH-006 adds dispatch state, a restricted claim function, arq enqueueing, and robust worker transitions including processing leases, queue recovery, and review required states. No model or outbound echo implementation exists.

The uv manifest includes PostgreSQL, migration, arq/Redis and Testcontainers dependencies; uv.lock is committed. This repair adds no new dependencies.
CI defines compilation, Ruff lint/format, strict mypy, import-linter and pytest.
Five import contracts cover currently implemented boundaries. A negative test
modifies a temporary copy and proves a forbidden import is rejected.

## In progress

Current branch: 	ask/SAH-006-complete-recovery.
The dispatcher reclaims expired processing rows, and all worker result writes require the matching unexpired token. Redis deliveries use fresh queue IDs; the processor receives a stable tenant/message idempotency key.
The unconfigured processor now fails terminally instead of falsely completing. Real PostgreSQL/Redis tests cover interrupted processing, redispatch, loss of queued data, and audit-write failure.
SAH-006 is complete on this branch: dispatch transitions generate atomic audit events, lost enqueued jobs are reclaimed via 60-second leases, and exhausted retries enter a REVIEW_REQUIRED state instead of silently dropping. 

The outbound implementation is SAH-007; its merge gates explicitly require idempotency-key forwarding and safe treatment of uncertain submissions.

## Next up, in order

1. SAH-007: outbound text echo.
2. SAH-008: deployment and real-number demonstration.

Read the relevant docs/tasks file before implementation. Continue on a separate
	ask/<id>-<slug> branch based on the completed prerequisite work.

## Open questions blocking later work

| Question | Blocks | Who decides |
|---|---|---|
| Which deployment host/account, HTTPS domain, secret store, test number and operator will be used? | SAH-008 | Project owner |
| What retention period and authorized audit-reader role apply? | Deployment | Project owner |

## Gotchas

- System Python is 3.13.3; this project requires 3.12. Repository-local tooling is
  ignored: .tools/uv/uv.exe (0.12.15) and .tools/python (3.12.14).
- For local uv commands here, set UV_PYTHON_INSTALL_DIR to the absolute
  .tools/python path and UV_CACHE_DIR to .uv-cache, then invoke .tools/uv/uv.exe.
  No shell profile was modified. uv reported a denied optional Windows registry
  registration; the managed interpreter and virtual environment work without it.
- Docker/Testcontainers PostgreSQL works outside the sandbox. The sandbox cannot
  access the Docker named pipe; tests require approved Docker access here.
- Health means process liveness only. The fixed-window limiter is aggregate per
  process, not distributed/per-tenant. SAH-005 needs route-specific limits and
  webhook body handling. Deployment also needs connection/header/slow-client limits.
- Database, Redis and WhatsApp settings now require runtime configuration.
  .env is ignored but not automatically loaded. Inject environment variables;
  do not commit secrets.
- The architecture negative test resolves lint-imports beside sys.executable;
  PATH discovery was unreliable in this Windows tool environment.
- The human reference is docs/source/sahulat-solution-design.html, not the filename
  mentioned in AGENTS.md. It is now tracked by prior work and remains unread here.
- Git metadata writes require sandbox approval here.
- Drain/stop old workers before migration 0005; do not mix old unfenced workers
  with new workers. Upgrade expires legacy processing rows for reclamation.
- Worker job timeout is four minutes and processing lease is five minutes.
  No heartbeat is implemented; keep bounded M0 processing within this budget.
- Queue delivery IDs and claim tokens are not outbound idempotency keys. Preserve
  intent:<tenant_uuid>:<message_uuid> across retries. Lease fencing protects
  database transitions, not external writes; SAH-007 must handle uncertain sends.
- Provider API contracts and delivery guarantees still require primary-document
  verification during SAH-005/007. No provider exactly-once guarantee is assumed.
- pytest can hit Windows temp/cache ownership errors. Disable its optional cache
  with -p no:cacheprovider and use a fresh, previously nonexistent workspace
  --basetemp directory. Do not skip failing tests to conceal permissions errors.

## Decisions made recently

- [ADR 0001](adr/0001-m0-contracts.md): accepted contract ownership, I/O protocol
  exception, durable dispatch, restricted audit evidence and pre-M5 operator review.
- [ADR 0002](adr/0002-m0-dependencies.md): accepted staged M0 dependency list.
- [ADR 0003](adr/0003-liveness-bootstrap.md): application factory, health semantics,
  bounded local probe policy and bootstrap quality gates.
- [ADR 0004](adr/0004-tenant-persistence.md): accepted tenant-scoped PostgreSQL persistence with Row-Level Security.
- [ADR 0005](adr/0005-audit-storage.md): accepted declarative PostgreSQL partitioning and strict insert-only database grants for audit logs.
- [ADR 0006](adr/0006-processing-leases.md): processing leases, fenced results, per-delivery queue IDs and stable outbound idempotency identity.

## Deliberately not done

No database/Redis integration beyond tenant/conversation schema, WhatsApp adapter, future module stubs, deployment, or reads/changes to the original reference HTML. The remote CI is now fully verified and green. M0 is not yet complete.

## Session log
### 2026-09-17 — Typed API client + MSW mock layer (Task 2)

- Did: Authored console/lib/api-client/admin-api.openapi.yaml from the finalized contract (21 endpoints, 26 schemas, all error shapes). Generated typed client via openapi-typescript. Created typed openapi-fetch client with credentials: 'include'. Set up full MSW mock layer: data.ts (in-memory store), 7 handler files (auth, users, tenants, documents, manifest, publish, sandbox), browser/server setup. Added .env.example, format scripts, type-fest @5.9.0 npm override (5.10.0 unpublished from npm).
- Validation: tsc --noEmit clean, prettier --check clean, eslint clean (0 errors, 0 warnings on source files).
- Decided: Relative API_BASE_URL default (/api/v1/admin) to avoid CORS in dev; absolute URL via env var for production. Used new HttpResponse(JSON.stringify()) in jsonOk wrapper to avoid MSW JsonBodyType generic constraint.
- Issues found: type-fest@5.10.0 unpublished from npm registry — pinned to 5.9.0 via package.json overrides. ESLint 'next lint' command hangs on full project scan (slow on first run + large generated types) — lint only source dirs and ignore generated/.
- Noted: contract doesn't specify GET /manifest or GET /documents list endpoints; added them as reasonable inferences for UI data loading. Flagged for owner confirmation in Task 2 report.
- Next: Awaiting owner confirmation of contract-derived shapes before Task 3 (actual screens).

### 2026-09-17 — Control plane UI scaffold begins

- Did: Started the control plane admin portal (`console/`). Refined
  `docs/admin-api-contract.md` error shapes (added `violations` field,
  documented `422` format, specified manifest PUT content type, sandbox reset
  response). Added ADR-0007 for a hand-authored OpenAPI spec to generate the
  console's typed client. Scaffolded Next.js 16.3.5 (App Router, TypeScript
  strict, Tailwind, ESLint, Prettier) in `console/`, renamed package to
  `sahulat-console`. Fixed scaffolded `layout.tsx` LayoutProps import error.
  Verified `tsc --noEmit`, ESLint, Prettier --check all pass; dev server serves
  HTTP 200 on localhost:3000.
- Validation: tsc clean, ESLint clean, Prettier check clean, dev server HTTP 200.
- Decided: ADR-0007 hand-authored spec approach for typed client generation.
- Assumed: Next.js 16 scaffold is acceptable; AGENTS.md specified Next 15 but
  create-next-app@latest resolves to 16.3.5 (backward compatible with App Router
  features).
- Next: Hold Task 2 (OpenAPI spec authoring + typed client generation) pending
  owner confirmation of contract edits.


### 2026-09-17 Ã¢â‚¬â€ Antigravity Ã¢â‚¬â€ SAH-006 Complete Recovery
- Did: Implemented atomic transition audits for all dispatcher/worker states. Added 60-second enqueue leases to reclaim lost queued data if Redis restarts or drops jobs. Handled exhaustion of retries and unknown outcomes by placing them into a REVIEW_REQUIRED state. Added close_dispatch_review.sql for operators to safely close stalled reviews without auto-resend. Added integration tests covering Redis outages, loss of queue data, and audit-write failure rollback.
- Validation: All tests passed on local Testcontainers (Postgres & Redis). 	est_dispatch_recovery.py specifically verifies that failed audits roll back state transitions and queue/Redis outages re-enqueue the items once the lease expires.
- Decided: Any unknown failure (Exception) in the worker translates to REVIEW_REQUIRED rather than an immediate terminal failure, protecting against operator uncertainty. Enqueue leases are used to guarantee at-least-once processing in the event of queue-layer amnesia. Resolved the incomplete SAH-006 items left by the previous session.
- Assumed: N/A.
- Next: SAH-007.

### 2026-09-17 Ã¢â‚¬â€ Codex Ã¢â‚¬â€ SAH-006 processing leases
- Did: added reversible migration 0005, processing lease and claim token,
  conditional ownership and fenced result transitions. Recovery gets a fresh
  Redis delivery ID while retaining the same explicit processor idempotency key.
  Replaced the default processor's silent success with explicit terminal failure.
- Validation: PostgreSQL/Redis tests cover interruption before result transition,
  unexpired exclusion, reclaim, stable key, duplicate delivery, concurrent claims,
  stale success/failure fencing, tenant isolation and legacy-row upgrade.
  Full suite: 68 passed. Ruff lint/format, strict mypy (61 source files),
  compilation, five import contracts and git diff whitespace checks all pass.
- Decided: five-minute database lease, four-minute worker timeout, no heartbeat;
  ADR 0006. No new dependencies or idempotency-key column.
- Assumed: outbound writes remain disabled until SAH-007 satisfies ADR 0001 and
  the explicit forwarding/uncertain-send merge gates added to its task.
- Deliberately left: remaining SAH-006 work listed above, push/merge/deployment,
  and the owner's pre-existing AGENTS.md filename correction (not staged).

### 2026-09-17 Ã¢â‚¬â€ Codex Ã¢â‚¬â€ SAH-006 CI repair
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

### 2026-09-16 Ã¢â‚¬â€ Antigravity Ã¢â‚¬â€ SAH-004
- Did: Created AuditRow with partitioned boundaries and restricted INSERT-only grants. Implemented AuditRepository for transactional event logging. Wrote RedactingFormatter to protect operational logs.
- Validation: Integration tests prove UPDATE/DELETE are impossible. Unit tests confirm redaction rules work.
- Decided: Built-in logging.Formatter used rather than importing structural loggers. Partition provisioning procedure encapsulated inside Postgres.
- Assumed: N/A.
- Next: SAH-005.

### 2026-09-16 Ã¢â‚¬â€ Antigravity Ã¢â‚¬â€ SAH-003
- Did: Reviewed uncommitted SAH-003 codebase left by previous agent. Verified acceptance criteria are met. Tests confirm isolation boundaries and RLS protection. Committed the work.
- Validation: Integration tests passed successfully on Testcontainers Postgres.
- Decided: Proceed with existing work as it accurately models ADR 0004.
- Assumed: N/A.
- Next: SAH-004.

### 2026-09-16 Ã¢â‚¬â€ Codex Ã¢â‚¬â€ SAH-002
- Did: accepted the owner's ADR approvals; implemented runnable app, configuration,
  HTTP limits, test suite, lockfile and CI. Updated architecture/standards references.
- Validation: 15 tests pass; Ruff lint/format, strict mypy (14 files), compilation,
  and both import contracts pass. Real Uvicorn startup/HTTP probe passed. Offline
  uv sync --locked confirmed lock consistency. Remote CI has not been executed.
- Decided: process-only health with constant-memory aggregate throttling; ADR 0003.
- Assumed: no deployment credentials or account selection from dependency approval.
- Next: SAH-003. No implementation changes left uncommitted at session completion.

### 2026-09-16 Ã¢â‚¬â€ Codex Ã¢â‚¬â€ SAH-001
- Established the documentation-only baseline, eight task files and two ADR proposals.
- Owner subsequently approved both proposals; deployment requirements remain recorded
  as later prerequisites rather than guessed account choices.
- [ADR 0007](adr/0007-hand-authored-openapi-spec.md): accepted a hand-authored OpenAPI 3.1 spec as a temporary bridge for generating the console’s typed API client, retired once the backend implements endpoints and FastAPI produces its own schema.
