# 0003. Minimal liveness bootstrap
Date: 2026-09-16
Status: accepted

## Context

SAH-002 needs a runnable app before database or queue dependencies exist. Public
routes must have explicit access and request limits without adding dependencies.

## Decision

Use a FastAPI application factory with environment configuration loaded at factory
invocation. Importing app.main does not create an application or read settings.
The only endpoint is public GET /health, reporting process liveness. Disable
OpenAPI and documentation routes. No secrets are needed by this task.

Apply a constant-memory, aggregate per-process fixed-window rate limit (10 requests
per second by default, configured and bounded in Settings). Reject all request
bodies without buffering them. Use a monotonic clock; check/increment without
awaiting so concurrent tasks on the same event loop cannot race the counter.
This policy applies to every request in the bootstrap, including unknown routes.

Use a non-packaged uv application, a committed lockfile, Python 3.12, strict mypy,
Ruff, pytest, and import-linter. Add import contracts only for real packages.
CI uses pinned official checkout/setup-uv actions and uv 0.12.15.

## Consequences

The probe reveals no tenant data and does not imply dependency readiness. Rate
limits multiply with process count and can affect probes during sustained load;
production ingress must also provide connection/header/slow-client limits.
SAH-005 must replace the blanket no-body policy with explicit webhook-specific
limits. No Redis dependency or generic policy framework is introduced early.

## Alternatives considered

- Unrestricted health route: conflicts with public-route limits.
- Per-IP in-memory buckets: stores client identifiers and grows memory usage.
- Redis limiter now: adds SAH-006 infrastructure before it is needed.
- Module-level application instance: reads configuration during imports.

## References

- https://docs.astral.sh/uv/guides/integration/github/
- https://import-linter.readthedocs.io/en/v2.6/contract_types.html
- https://fastapi.tiangolo.com/deployment/manually/
