# 0007. Hand-authored OpenAPI spec for console typed client
Date: 2026-09-17
Status: accepted

## Context

The admin API contract (`docs/admin-api-contract.md`) exists only as Markdown.
The backend (`app/api/v1/routers/admin.py`) is not yet implemented — all
endpoints are marked `[ ] not implemented`. The control plane UI (`console/`)
needs a typed API client to build against, and the contract-first rule in
`console/AGENTS.md` requires that the UI build against the exact contract shape,
not hand-written `fetch` calls with inferred types.

## Decision

Create a hand-authored OpenAPI 3.1 specification at
`console/lib/api-client/admin-api.openapi.yaml` that mirrors
`docs/admin-api-contract.md` endpoint-for-endpoint. Generate the typed client
and MSW mock handlers from this spec. The spec is a faithful translation of the
contract Markdown, not an independent reinterpretation.

## Consequences

- **What's duplicated:** The hand-authored spec duplicates information that will,
  once the backend is implemented, also live in FastAPI's generated OpenAPI
  schema. This is a single, explicitly temporary duplication — a bridge, not a
  second source of truth.
- **Why:** The contract is Markdown, not machine-readable. A typed client cannot
  be generated from Markdown. The UI must have type safety from day one;
  `fetch` calls with `any`-typed responses violate both the quality bar and the
  contract-first rule.
- **Drift prevention:** Until the backend implements an endpoint, the
  hand-authored spec *is* the contract for that endpoint. Once the backend
  implements an endpoint, any mismatch between the spec and the contract Markdown
  is a bug in the spec (fix it), not an acceptable divergence.
- **Shared validation requirement:** For `PUT .../manifest`, the spec notes that
  server-side validation must use the same code path as
  `actions/manifest.py` at runtime — not a separate UI-facing validator — so the
  UI never accepts a manifest the orchestrator would reject.

## Retirement trigger

Once the backend implements an endpoint and FastAPI's generated OpenAPI schema
covers it, the console switches to consuming the generated schema (via CI
download from the running dev server or a committed export). The corresponding
section of the hand-authored file is deleted — not left in place as a second,
potentially drifting source of truth. When all endpoints have migrated,
`admin-api.openapi.yaml` is removed entirely.

## Alternatives considered

- **Build the typed client from inferred fetch responses.** Rejected — violates
  the contract-first rule and the "no `any`" quality bar; types would be
  guesses drifting from the contract.
- **Wait until the backend is implemented.** Rejected — the contract explicitly
  permits UI work against mocks while the backend is absent. The console should
  not block on SAH-005/006/007.
- **Generate from the Markdown directly.** Rejected — no tool converts
  Markdown documentation into a typed OpenAPI client with fidelity; a
  hand-authored spec is the reliable translation.
