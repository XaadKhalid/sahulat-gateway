# Sahulat gateway

M0 bootstrap: Python 3.12, FastAPI, uv. Read AGENTS.md and docs/STATE.md first.

## Local development

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```shell
uv sync --locked
uv run --locked uvicorn app.main:create_app --factory --host 127.0.0.1
```

`GET /health` returns `{"status":"ok"}`. This unauthenticated endpoint reports
process liveness only, not database or queue readiness. Documentation routes are
disabled. No credentials are needed or defined in this bootstrap.

Configuration is read at application creation from environment variables with
the `SAHULAT_` prefix. `SAHULAT_HEALTH_REQUESTS_PER_SECOND` defaults to 10
(allowed range 1–1000). The fixed one-second limit is aggregate per application
process; it is not a distributed or per-tenant limit. Excess requests return 429
with `Retry-After: 1`. Every request is subject to this bootstrap limit, including
unknown routes. Request payloads are forbidden and return 413. No client IPs are
stored. Bind to loopback by default; deployment must also provide edge connection,
header-size and slow-client limits. Future webhooks need separate body/rate policy.

`.env` files are ignored by Git but are not automatically loaded. Supply environment
variables through your shell or deployment secret manager. Disable uvicorn access
logs for deployment unless a reviewed redaction policy is in place.

## Verification

```shell
uv run --locked python -m compileall -q app tests migrations
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked lint-imports --config tests/architecture/.importlinter
uv run --locked pytest
```

Architecture tests include a deliberately invalid import in a temporary copy.
Contracts cover currently implemented packages; extend them as business packages
arrive. PostgreSQL persistence and RLS are implemented; no queue, WhatsApp adapter
or deployed service exists yet. See [the persistence runbook](docs/persistence.md)
for provisioning, migration and Docker-backed integration tests.
