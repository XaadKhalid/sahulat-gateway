# 6. Webhook Ingress and Atomic Dispatch

Date: 2026-09-16

## Status

Accepted

## Context

We need to safely receive incoming messages from WhatsApp, map them to the correct isolated tenant context, and durably record them for processing. Model calls are relatively slow and fallible, so they must not happen synchronously during the webhook request, or we risk WhatsApp timing out and redelivering the same message.

## Decision

1. **Security & Limits First:** We enforce payload size limits and a token-bucket rate limit directly in standard ASGI middleware (`GatewayRequestLimits`) before buffering bodies or entering the framework routing. We compute HMAC-SHA256 signatures immediately on the raw body before JSON parsing to reject forged requests efficiently.
2. **Atomic Ingress:** `IngressService` wraps the persistence of the session creation, the message itself, the audit log event, and a new `dispatch_intents` marker in a single PostgreSQL transaction (`tenant_transaction`).
3. **Idempotency:** The database models use `ON CONFLICT DO NOTHING` for unique message IDs. If a duplicate delivery occurs, the database safely ignores the insert, ensuring we never duplicate messages or dispatch intents.
4. **Outbox Pattern for Dispatch:** We introduced `dispatch_intents` as a simple outbox pattern. This allows the synchronous webhook to return HTTP 200 immediately after persisting the intent, deferring the actual LLM processing to an asynchronous worker.

## Consequences

*   WhatsApp webhooks remain extremely fast, minimizing retry storms.
*   We rely entirely on PostgreSQL for transactional integrity and idempotency.
*   We need a separate worker/polling mechanism in the future to consume `dispatch_intents` and trigger the agent logic.
