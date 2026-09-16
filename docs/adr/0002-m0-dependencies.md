# 0002. Minimal M0 dependency approval
Date: 2026-09-16
Status: proposed

## Context

AGENTS.md requires asking before adding packages to pyproject.toml. No manifest
exists. The approved task list does not specify package additions.

## Decision proposed

Approve these direct dependencies, added only when their task consumes them:

| Task | Packages | Purpose |
|---|---|---|
| SAH-002 runtime | fastapi, uvicorn, pydantic, pydantic-settings | Application/server, typed boundaries, environment configuration |
| SAH-002 development | pytest, pytest-asyncio, httpx, ruff, mypy, import-linter | Behavior and async HTTP tests, lint/format, typing, import contracts |
| SAH-003 runtime | sqlalchemy, asyncpg, alembic | Async PostgreSQL persistence and migrations |
| SAH-003 development | testcontainers[postgres], psycopg2-binary | Real Postgres fixtures; synchronous bootstrap driver restricted to test tooling outside application async paths |
| SAH-005 runtime | httpx | Async provider I/O; already used by development tests |
| SAH-006 runtime | arq, redis | Background work, queue transport and rate-limit storage |

Use Python 3.12 and uv. Resolve compatible versions and commit uv.lock during
implementation; compatibility is not asserted before resolution and testing.
Start with uv non-packaged application mode, avoiding an unnecessary build backend.
Use base uvicorn without optional extras. Omit psycopg2-binary if the chosen test
setup does not need it; do not substitute another unapproved direct dependency.

No LLM SDK, document parser, vector client, frontend package or storage SDK in M0.
Tool installation and deployment access are separate from package approval.

## Consequences

Introduce packages incrementally with lockfile and test evidence. Application I/O
uses asyncpg; any synchronous bootstrap driver remains test-only. Any additional
direct package discovered during implementation requires another proposal.

## Alternatives considered

- Install the entire future stack: expands M0 without working behavior.
- SQLite tests: cannot prove PostgreSQL RLS or partition behavior.
- Omit an explicit server: leaves no supported application runner.
