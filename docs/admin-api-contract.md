# Admin API Contract

The single source of truth for the control plane's admin API. Both
`console/` (consumer) and `app/api/v1/routers/admin.py` (implementer) build
against exactly this file. Neither side invents a shape the other doesn't
know about.

**Status: not yet implemented.** This file currently describes the *intended*
contract so UI work can start against mocks. As each endpoint is implemented
for real, mark it and keep this file in sync — it must never describe an
endpoint whose real shape has silently diverged.

Base path: `/api/v1/admin`. All requests require an authenticated portal-staff
session (see Auth below). All responses are JSON. Errors follow FastAPI's
`ProblemDetails`-style shape:

```json
{ "detail": "human-readable message", "type": "error_code_string", "violations": ["string"] }
```

- `422` request-validation failures (e.g. invalid manifest YAML) return
  FastAPI's standard validation format — the only shape where `detail` is an
  array rather than a string:
  ```json
  { "detail": [{ "loc": ["body"], "msg": "error message", "type": "value_error" }] }
  ```
- The `violations` array is optional and only present on errors (such as the
  409 publish precondition failure) that carry a list of specific reasons the
  client needs to surface in the UI.```

---

## Auth

`[ ] not implemented`

- `POST /api/v1/admin/auth/login` — `{ email, password }` → sets an
  httpOnly session cookie. No tokens handled client-side.
- `POST /api/v1/admin/auth/logout` — clears session.
- `GET /api/v1/admin/auth/me` → `{ id, email, role }` for the current
  session, or 401.

---

## Screen 1 — User management

`[ ] not implemented`

Portal staff accounts, not tenant customers.

- `GET /api/v1/admin/users` → paginated list
  ```json
  { "items": [{ "id": "uuid", "email": "string", "role": "admin|operator", "created_at": "iso8601" }],
    "next_cursor": "string|null" }
  ```
- `POST /api/v1/admin/users` — `{ email, role }` → creates and emails an
  invite. Does not accept a password (invite-based, not admin-set).
- `PATCH /api/v1/admin/users/{id}` — `{ role }` → role change only. No
  self-demotion if it would leave zero admins (409 if attempted).
- `DELETE /api/v1/admin/users/{id}` → deactivates, does not hard-delete
  (staff actions must remain attributable in the audit log).

---

## Screen 2 — Business profile management

`[ ] not implemented`

Tenant onboarding and configuration.

- `GET /api/v1/admin/tenants` → paginated list
  ```json
  { "items": [{ "id": "uuid", "name": "string", "status": "draft|connecting|live|suspended",
    "whatsapp_connected": "boolean", "created_at": "iso8601" }],
    "next_cursor": "string|null" }
  ```
- `POST /api/v1/admin/tenants` — `{ name }` → creates a tenant in `draft`
  status. Everything else is added incrementally via the endpoints below.
- `GET /api/v1/admin/tenants/{id}` → full detail: profile, WhatsApp
  connection status, document count, manifest status, policy summary.
- `PATCH /api/v1/admin/tenants/{id}` — `{ name?, policy? }` → partial update.
- `POST /api/v1/admin/tenants/{id}/whatsapp/connect` — starts embedded
  signup / WABA linking flow; response shape depends on Meta's embedded
  signup integration, to be defined when SAH-005's WhatsApp adapter work
  clarifies what's available server-side.
- `POST /api/v1/admin/tenants/{id}/documents` — multipart upload → 
  `{ document_id, filename, status: "processing" }`. Ingestion is async;
  poll `GET .../documents/{document_id}` for `status: "ready"|"failed"`.
- `GET /api/v1/admin/tenants/{id}/documents` → list with status per doc.
- `DELETE /api/v1/admin/tenants/{id}/documents/{document_id}`
- `PUT /api/v1/admin/tenants/{id}/manifest` — accepts `Content-Type:
  application/yaml`; the body is the raw OpenAPI 3.1 YAML document as a text
  string (including `x-agent` annotations). Validates and stores. 422 with
  field-level errors on an invalid manifest; server-side validation must use
  the same code path `actions/manifest.py` uses at runtime — not a separate
  UI-facing validator — so the UI never accepts something the orchestrator
  would reject.
- `POST /api/v1/admin/tenants/{id}/publish` — `status: draft → live`, only
  once WhatsApp is connected, at least one document is ready, and the
  manifest (if present) validates. 409 with a list of unmet preconditions
  otherwise — the UI renders this list, it does not duplicate the check.

---

## Screen 3 — Sandbox chat window

`[ ] not implemented`

Real-time testing against the live orchestrator for a given tenant, without
touching the real WhatsApp channel.

- `POST /api/v1/admin/tenants/{id}/sandbox/messages` — `{ text, session_id? }`
  → runs the message through the real turn loop (`orchestration/turn_loop.py`)
  with a synthetic `ChannelAdapter` that never touches WhatsApp, returns the
  full result:
  ```json
  { "session_id": "uuid", "reply": "string",
    "tool_calls": [{ "name": "string", "args": {}, "result": {} }],
    "retrieved_chunks": [{ "source": "string", "excerpt": "string" }],
    "tier": "anonymous|known|verified|privileged" }
  ```
  Exposing `tool_calls` and `retrieved_chunks` here is deliberate — this
  screen is a debugging tool for the tenant admin, not the polished chat
  experience the end customer gets, so showing the orchestrator's reasoning
  is a feature.
- `POST /api/v1/admin/tenants/{id}/sandbox/reset` — clears sandbox session
  state (starts a fresh identity tier at `anonymous`). Returns `204 No Content`.

This may become a WebSocket (`/api/v1/admin/tenants/{id}/sandbox/stream`)
if request/response polling feels wrong once real turn-loop latency is
visible. Decide that with an ADR when SAH-007 makes real latency
measurable, not preemptively.

---

## Changelog

Record every change here with a date and a one-line reason, so both sides can
tell at a glance whether their assumptions are stale.

- `2026-09-17` — refined error shapes: added optional `violations` array to
  409 precondition errors, documented `422` validation format, specified manifest
  PUT content type and shared validation requirement, specified sandbox reset
  response.
- `2026-09-17` — initial draft, nothing implemented yet.
