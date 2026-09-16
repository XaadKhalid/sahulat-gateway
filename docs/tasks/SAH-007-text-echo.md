# SAH-007 - Implement outbound text echo

Branch: task/SAH-007-text-echo
Prerequisites: SAH-006

## Scope

Wire the text echo service to an injected async WhatsApp client.

## Acceptance criteria

- [ ] Primary provider documentation supports endpoint/version, credentials, payload and error handling.
- [ ] A persisted text message is sent to the correct sender using the correct tenant configuration.
- [ ] Provider acceptance identifiers and failures are audited; acceptance is not mislabeled as delivery.
- [ ] Definite failure, uncertain submission, worker crash and stale reply-window cases follow ADR 0001.
- [ ] Fakes verify service behavior without network; HTTP adapter tests cover provider responses.
- [ ] No blind retry can send an uncertain submission twice automatically.

## Out of scope

LLM, retrieval, customer identity lookup, templates, commerce actions.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.
