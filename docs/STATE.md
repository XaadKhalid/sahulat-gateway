# STATE.md — Current Truth

**Last updated:** 2026-09-16 by Codex
**Current milestone:** M0 — Walking skeleton
**Build status:** Not established; documentation only, no application or tests.

## Where the project actually is

The user approved the eight-task M0 plan. The repository initially had no
commits, only untracked operating/product/architecture documents and a human
reference HTML file. No implementation exists. The original STATE was an empty
template, not evidence of working software.

SAH-001 has established the task backlog and concrete decision proposals.
Read ADRs 0001 and 0002 before implementation. They are proposed, not accepted;
task-list approval did not approve package additions or resolve conflicting
engineering requirements.

## In progress

| Task | Branch | State | Next concrete step |
|---|---|---|---|
| SAH-001 | task/SAH-001-m0-baseline | Documentation prepared; decisions pending | Obtain approval of ADR proposals and deployment information |

## Next up, in order

1. SAH-002: application bootstrap and quality gates, after dependency approval.
2. SAH-003: tenant provisioning and isolated persistence.
3. SAH-004: append-only audit storage.
4. SAH-005: authenticated WhatsApp ingress.
5. SAH-006: durable queue dispatch and worker recovery.
6. SAH-007: outbound text echo.
7. SAH-008: deployment and real-number demonstration.

Detailed scope, prerequisites, and acceptance criteria are in docs/tasks/.

## Open questions blocking work

| Question | Blocks | Who decides |
|---|---|---|
| Approve packages in ADR 0002? | SAH-002 and subsequent package additions | Project owner |
| Approve contract ownership, required-protocol exception, delivery and audit proposals in ADR 0001? | SAH-003 onward | Project owner |
| Which deployment host/account, HTTPS domain, secret store, test number and operator will be used? | SAH-008 | Project owner |
| What retention period and authorized audit-reader role apply? | Deployment | Project owner |

## Gotchas

- Python on PATH is C:/Python313/python.exe; Python 3.12 availability is not yet verified.
- uv is not on PATH. Docker CLI exists; engine availability is not yet checked.
- No build, lint, type-check or test result exists. Documentation checks are not application validation.
- The human reference is docs/source/sahulat-solution-design.html, not the filename mentioned in AGENTS.md. It was not opened and is not authoritative.
- Do not implement all phase-1 protocols or modules during M0.
- No provider delivery/idempotency guarantee has been verified. Check primary WhatsApp documentation in SAH-005/007 before implementing provider behavior.
- Git metadata writes require sandbox approval in this environment.

## Decisions made recently

- Eight session-sized tasks approved by the user; no implementation yet.
- [ADR 0001](adr/0001-m0-contracts.md) contains reviewable proposals for contradictory requirements.
- [ADR 0002](adr/0002-m0-dependencies.md) contains the dependency approval request; no dependencies installed.

## Deliberately not done

No application, migrations, CI, dependency manifest, infrastructure provisioning,
remote deployment, or edits to original engineering/product requirements.
No source HTML was read or modified.

## Session log

### 2026-09-16 — Codex — SAH-001
- Did: inspected documentation-only baseline; created M0 task files and ADR proposals.
- Decided: preserve requirements until their contradictions are explicitly resolved.
- Assumed: approval covers the task list, not unspecified dependencies or deployment accounts.
- Left for next: dependency/contract approval, then SAH-002; runtime/tooling verification.
- Validation: eight task files and two ADRs passed structural checks; no application tests exist yet. The pre-existing docs/source HTML remains untracked and untouched.
