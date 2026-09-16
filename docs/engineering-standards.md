# Engineering Standards

Binding on all code in this repository, human- or agent-written. Code review
rejects violations regardless of whether tests pass.

Stack: Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, pytest, ruff,
mypy strict, uv for dependency management.

---

## 1. SOLID — what it means here, concretely

These are not slogans. Each has a testable definition in this codebase.

### Single Responsibility
A class or module has one reason to change. Practical test: can you describe
what it does in one sentence without using "and"? If not, split it.

Violations that will be rejected:
- A router that validates, applies business rules, and queries the database.
- A service that both fetches data and formats it for WhatsApp.
- A `helpers.py`, `utils.py` or `manager.py`. These names mean "I did not decide
  what this is." Name the responsibility or do not create the module.

### Open/Closed
Adding a new channel, a new step-up method, or a new tool source must not
require editing existing code. New behaviour arrives as a new implementation of
an existing Protocol, wired at composition root.

Concrete requirement: `ChannelAdapter`, `StepUpMethod`, `ToolSource`,
`LlmClient`, `EmbeddingClient` exist so this holds. If you are adding a branch
to an `if isinstance(...)` or a string-dispatch dict inside business logic, you
are violating this — add an implementation instead.

### Liskov Substitution
Any implementation of a Protocol must be usable wherever the Protocol is
expected, without the caller checking which one it got. An implementation that
raises `NotImplementedError` for half the Protocol means the Protocol is wrong —
split it.

### Interface Segregation
Small, role-based Protocols, defined by what the *consumer* needs, not by what
the implementation happens to offer. A Protocol with 14 methods of which a given
consumer uses two is wrong.

### Dependency Inversion
Business logic depends on abstractions it owns. `orchestration` defines
`KnowledgeRetriever`; `knowledge` implements it. The dependency arrow points
inward, toward the domain, always.

Enforcement: `import-linter` contracts in `tests/architecture/` assert the
dependency direction and fail CI. They are not advisory.

---

## 2. DRY — and its limits

**The rule of three.** Duplication is extracted on the third occurrence, not the
second. Two similar-looking pieces of code are frequently not the same concept;
they merely rhyme today. Wait for the third to see the real shape.

**Extract concepts, not character sequences.** If two blocks look alike but
change for different reasons, they are not duplication. Merging them couples two
independent things, and the next change to either one will hurt.

### Anti-over-abstraction limits (as binding as DRY)

The following are rejected on review even when they eliminate duplication:

- A generic abstraction with exactly one implementation and no concrete second
  one planned in the current milestone.
- A configuration, strategy or plugin mechanism introduced to serve two cases.
- A base class whose only purpose is to hold shared attributes.
- Inheritance used for code reuse. Prefer composition. Always.
- Parameters added to a shared function purely to make it fit a new caller,
  especially boolean flags that switch behaviour. Two behaviours means two
  functions.
- `**kwargs` passthrough that hides what a function actually accepts.
- Metaclasses, decorators or dynamic attribute tricks where a plain function
  would do.
- Indirection that makes a reader open more than two files to answer "what does
  this actually do?"

**Duplication is cheaper than the wrong abstraction.** If unsure, duplicate and
leave the decision to the third occurrence. Say in your summary that you did so
and why.

### What is always deduplicated, no waiting

- Domain rules: tier requirements, risk levels, money arithmetic, validation
  rules. These must exist exactly once.
- Constants, magic strings, config keys, error codes.
- Anything where two copies silently drifting apart is a correctness or security
  bug.

---

## 3. Layering

```
Router / channel adapter    thin: parse, validate, delegate. No logic. No DB.
        ↓
Service / turn loop         business logic. Framework-free. Fully testable.
        ↓
Repository / client         data access and external I/O behind Protocols.
        ↓
Domain models               entities and rules. Depend on nothing.
```

Nothing skips a layer. A router that touches an SQLAlchemy session directly is
rejected. Business logic that imports from `fastapi` is rejected.

---

## 4. Typing

- `mypy --strict` passes. Warnings are errors.
- Every function signature fully annotated, including return types.
- No bare `Any`. If a type is genuinely dynamic, model it as a union or a
  Pydantic model and validate at the boundary.
- `# type: ignore` requires an inline comment explaining why it is safe.
- Pydantic models for every request, response, and cross-boundary payload.
  **Never pass raw dicts into business logic** — an untyped dict crossing a
  module boundary is a defect, not a shortcut.

---

## 5. Security (hard rules, checked every review)

- No secrets in source, ever. `pydantic-settings` reading environment variables.
  No secret has a default value in `config.py`. Local development uses a
  gitignored `.env`, never a committed file.
- Validate all external input at the boundary with Pydantic, before business
  logic.
- SQLAlchemy expression language or parameterized queries only. Never f-strings
  or concatenation into SQL.
- AuthZ on every admin endpoint by default. Public routes opt out explicitly and
  visibly.
- Rate limit and size-limit everything public-facing, including the WhatsApp
  webhook.
- Verify `X-Hub-Signature-256` on every inbound webhook. Reject unverified,
  before parsing the body.
- Log auth failures and permission denials. Never log secrets, tokens, OTPs or
  full PII.
- Tenant isolation is enforced at the data layer via row-level security, not by
  remembering to add `WHERE tenant_id`. A query that can leak across tenants is
  a critical defect.

---

## 6. Async

- `async def` for all I/O-bound work: database, Redis, HTTP, object storage,
  model calls.
- **Never make a blocking call inside `async def`.** No `requests`, no `time.sleep`,
  no synchronous database driver, no blocking file I/O. Use `httpx.AsyncClient`,
  `asyncpg`, `asyncio.sleep`. Blocking the event loop is a rejection, and it is
  the single most common way an agent silently ruins a FastAPI service.
- CPU-bound work (parsing, chunking, OCR) goes to a worker or a thread pool via
  `run_in_executor`, never inline in a request path.
- Per-request database session injected as a dependency. No module-level global
  session shared across requests.
- `asyncio.TaskGroup` for concurrent work. No fire-and-forget `create_task`
  without a reference and error handling.

---

## 7. Error handling

- Custom exception classes per domain failure, registered with FastAPI exception
  handlers. Never `except Exception` that swallows and continues.
- Stack traces never reach an API response in production.
- Every database call, HTTP call, model call and file operation has explicit
  failure handling. Assume it fails.
- Failures in the conversation path degrade gracefully to a human handoff, never
  to a fabricated answer.
- Never return HTTP 200 with an error described in the body.

---

## 8. Data and correctness

- `decimal.Decimal` for all money. **Never `float`.** Pydantic fields for money
  are `Decimal` with explicit precision; database columns are `NUMERIC`.
- Write operations that can be retried are idempotent, with an explicit
  idempotency key.
- No N+1 queries. Use explicit eager loading (`selectinload`/`joinedload`) and
  assert query counts in integration tests for hot paths.
- Be explicit in queries. Do not rely on a default filter silently applying —
  state the condition you mean, especially in aggregates and counts.
- Alembic migrations are reviewed like code and are always reversible.
- Timezone-aware UTC datetimes everywhere. Never a naive datetime in the
  database or in a domain model.

---

## 9. Testing

- `pytest` with `pytest-asyncio`. Unit tests for every service and every
  policy/gating decision.
- Integration tests with `httpx.AsyncClient` against a real Postgres in
  Testcontainers. No SQLite substitute — it lies about SQL behaviour that this
  system depends on, including row-level security.
- Fakes over mocks. Because collaborators are Protocols, write a small fake
  implementation rather than patching. `unittest.mock.patch` on an import path
  is a sign the dependency should have been injected.
- **Tool-gating tests are mandatory and are the highest-value tests in the
  repo:** prove that an anonymous caller cannot reach a `verified` tool, that
  ownership checks reject another customer's record, and that a high-risk action
  without confirmation does not execute.
- Tests name the behaviour: `test_block_card_without_verified_tier_is_rejected`.
- No test depends on another test's state or on execution order.
- A bug fix ships with a test that fails without the fix.

---

## 10. Style and tooling

- `ruff format` and `ruff check` clean before commit. Ruff only — do not mix in
  black, flake8 or isort.
- Dependencies in `pyproject.toml`, managed with `uv`, lockfile committed. No
  bare `requirements.txt`, no `pip install` into the environment without adding
  it to the manifest.
- Functions short enough to read without scrolling. If it needs a scroll, it is
  doing too much.
- Names describe intent: `calculate_order_total`, not `process`.
- Module-level code does nothing but define things. No side effects on import.
- Comments explain *why*. The code already says *what*.
- No commented-out code. Git remembers it.
