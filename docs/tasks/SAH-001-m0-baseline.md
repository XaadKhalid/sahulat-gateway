# SAH-001 - Establish the baseline and resolve M0 contracts

Branch: task/SAH-001-m0-baseline
Prerequisites: Approved M0 task list

## Scope

Document actual repository state, create task files, and prepare contract and dependency decisions.

## Acceptance criteria

- [x] STATE.md describes the observed baseline without claiming a working build.
- [x] SAH-001 through SAH-008 have explicit scope and acceptance criteria.
- [x] ADRs record contract placement, protocol exception, supported M0 input, delivery recovery, audit handling, and pre-M5 failure handling.
- [x] Dependency and contract proposals are approved before dependent implementation; deployment requirements are recorded.

## Out of scope

Application code, package installation, deployment.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.
