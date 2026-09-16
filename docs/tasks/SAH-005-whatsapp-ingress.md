# SAH-005 - Implement authenticated WhatsApp ingress

Branch: task/SAH-005-whatsapp-ingress
Prerequisites: SAH-003 and SAH-004; approved M0 contract

## Scope

Verify and normalize provider webhooks, then persist inbound messages and durable dispatch intent.

## Acceptance criteria

- [ ] Primary Meta documentation is checked and linked for verification, payloads and response semantics.
- [ ] Signature is verified against raw bytes before parsing; malformed or forged requests are rejected.
- [ ] Request size and rate limits apply before expensive work.
- [ ] Validated text events resolve the correct tenant/session and create typed envelopes.
- [ ] Duplicate delivery does not create duplicate messages or dispatch intent.
- [ ] Status and unsupported events never trigger text echoes.
- [ ] Persistence of message, audit and dispatch intent is atomic; failures do not falsely acknowledge acceptance.

## Out of scope

Model calls, interactive replies, audio processing, outbound sending.

## Session completion

Read AGENTS.md, STATE.md, this task and engineering-standards.md before coding.
Keep the task in one session-sized branch. Include behavior tests with implementation.
Run applicable build/test/lint/type checks; record evidence and limitations in STATE.md.
Record architectural decisions in ADRs and commit with this task ID.
Do not claim completion while any acceptance criterion is unfulfilled.
