# Architecture

## Stack decision — READ THIS FIRST

**Python 3.12 / FastAPI**, per the original solution design document.

One clarification to that document. It offers "Node.js (Fastify) or Go" for the
channel gateway alongside a Python FastAPI orchestrator. We use **Python for
both**. Two runtimes means two dependency toolchains, two sets of conventions,
two linters and two review standards, for a gateway that is deliberately thin
and not on any measured hot path. FastAPI handles webhook ingress comfortably.
This stays inside the document's own sanctioned stack while halving the surface
that agents can get wrong. If load ever justifies a separate Go gateway,
extracting it is a contained job because it sits behind `IChannelAdapter`.

One naming note: the document refers to an orchestration framework called
"gentic-ai". There is no such installable package. Read every reference to it as
"the agentic orchestration layer we are writing ourselves", described below.

## Shape: modular monolith

One deployable FastAPI application with enforced internal module boundaries. Not
microservices.

Microservices would add network boundaries, distributed tracing, deployment
coordination and eventual consistency to a team that is one reviewer and some
agents, for a product with no scale problem yet. The boundaries below are real
and test-enforced, so extraction later is mechanical if it is ever needed.

The design document's NATS/Kafka bus, Temporal workflows and Qdrant are all
deferred. Postgres and Redis cover phase 1 comfortably. Adding them now is the
premature-infrastructure failure this project must avoid. The document itself
names scope discipline as the largest risk; this is where that risk lands first.

## Project layout

```
app/
  main.py                      app instantiation, router registration, lifespan
  core/
    config.py                  pydantic-settings, env vars only, no secret defaults
    logging.py                 structured logging setup
    errors.py                  exception types + FastAPI handlers
  api/
    v1/
      routers/
        webhooks.py            WhatsApp inbound — thin, signature verify, enqueue
        admin.py               control plane API
  channels/
    base.py                    ChannelAdapter protocol + MessageEnvelope
    whatsapp/                  the ONLY WhatsApp-aware code in the system
  orchestration/
    turn_loop.py               the core loop, framework-free
    planner.py                 model interaction
    policy.py                  tier gating, confirmation, rate limits
    sessions.py                session + memory state
  knowledge/
    ingestion/                 parsing, chunking, embedding
    retrieval.py               hybrid search + rerank
  identity/
    resolver.py                phone -> principal + tier
    stepup/                    OTP and future methods
  actions/
    manifest.py                OpenAPI 3.1 + x-agent loading and validation
    registry.py                tools available for (tenant, tier)
    executor.py                execution, idempotency, ownership checks
  guardrails/
    domain_fence.py
    injection.py
    redaction.py
  models/                      SQLAlchemy ORM models
  schemas/                     Pydantic request/response/domain models
  repositories/                DB access, one per aggregate
  infrastructure/
    llm/                       LlmClient implementations
    embeddings/
    storage.py                 S3-compatible object storage
    redis.py
  audit/
    sink.py                    append-only audit writer
tests/
  unit/
  integration/                 testcontainers Postgres
  architecture/                import-linter contracts
console/                       control plane UI (Next.js, added at M5)
```

**Dependency rule, enforced by test:** `orchestration`, `identity`, `actions`,
`knowledge` and `guardrails` contain business logic and must not import from
`api`, `channels`, or `infrastructure`. They depend on protocols they define
themselves; concrete implementations are injected. `schemas` and domain models
depend on nothing. Enforced by `import-linter` contracts that fail CI, not by a
reviewer's memory.

## The turn loop

The core abstraction. Every inbound message goes through exactly this.

1. **Ingest** — verify `X-Hub-Signature-256`, deduplicate by message id,
   normalise to a `MessageEnvelope`, persist, enqueue. The envelope carries a
   content union so audio can be added later without changing this contract.
2. **Resolve** — tenant from the WhatsApp phone number id; session from
   (tenant, customer number); identity tier from cache or tenant lookup.
3. **Understand** — language detection, guardrail scan for injection and
   out-of-domain. Out-of-domain returns the tenant's configured refusal without
   ever calling the main model.
4. **Plan** — the model receives: system prompt (persona + fence), session
   memory, retrieved knowledge, and **only the tools permitted for this tier**.
   It returns a reply, tool calls, or an escalation.
5. **Gate** — every requested tool call is checked in code: tier sufficient?
   confirmation required and given? rate limit clear? If step-up is needed, the
   plan pauses, the OTP sub-flow runs as orchestrator state, and the plan
   resumes. The model never sees the OTP.
6. **Execute** — call the tenant API. Ownership-check every returned record
   against the session principal *before* the model sees it. Idempotency key on
   writes.
7. **Reply** — text, or interactive buttons where the next step is a choice, or
   an approved template if outside the 24-hour service window.

Every step writes to the audit log.

## Key protocols (defined by the business-logic packages, not by infrastructure)

Use `typing.Protocol`, not ABCs, so implementations stay structurally typed and
trivially fakeable in tests.

```python
class ChannelAdapter(Protocol):        # normalise inbound, send outbound
class KnowledgeRetriever(Protocol):    # (tenant, text, visible_tiers) -> chunks
class ToolSource(Protocol):            # tools available for (tenant, tier)
class ToolExecutor(Protocol):          # (tool, args, idempotency_key) -> result
class IdentityResolver(Protocol):      # phone -> principal + tier
class StepUpMethod(Protocol):          # challenge / verify
class LlmClient(Protocol):             # (messages, tools) -> reply | tool_calls
class EmbeddingClient(Protocol):
class AuditSink(Protocol):             # append(event)
```

These exist so a second channel, a second step-up method, or a self-hosted model
is a new implementation wired in `main.py` — never an edit to the turn loop.

## Dependency injection

FastAPI `Depends()` at the API edge, plain constructor injection everywhere
below it. The turn loop and every service take their collaborators as
constructor arguments and must be constructible in a unit test with no FastAPI
app, no database and no network. If a class reaches for a module-level global to
do I/O, that is a defect.

## Data

- **PostgreSQL 16** for everything: tenants, sessions, messages, manifests,
  audit, and vectors via **pgvector**. One store until there is a measured
  reason for a second. SQLAlchemy 2.0 async with `asyncpg`.
- **Redis** for session state, OTP challenges, rate limits, dedupe keys.
- **S3-compatible object storage** for uploaded documents and media.
- Tenant isolation via Postgres row-level security. Not by remembering to add a
  filter to each query.
- Audit tables are append-only and partitioned by month.

## Background work

Inbound webhooks return immediately after persisting and enqueueing; the turn
loop runs off that queue. Use **arq** (Redis-backed) for phase 1 — it is async
native, small, and adds no new infrastructure since Redis is already present.
Celery and Temporal are heavier than this project currently justifies.

## Models

Hosted frontier model behind `LlmClient` for phase 1. The protocol exists so a
self-hosted open-weight model can be swapped in for a future sovereign
deployment without touching the orchestrator. Do not build the sovereign path
now; just do not close the door on it.

Hard requirement when evaluating any model for this system: **reliable
structured tool-calling and reliable refusals**, not general chat quality. The
design document flags open-weight tool-calling reliability as an open risk; it
is decided by benchmark, not by preference.

## Architecture Decision Records

Every non-obvious decision gets a file in `docs/adr/NNNN-short-title.md`:

```markdown
# NNNN. Title
Date: YYYY-MM-DD
Status: proposed | accepted | superseded by NNNN

## Context
What forced a decision. What constraints applied.

## Decision
What we chose, stated plainly.

## Consequences
What this makes easy. What it makes hard. What we accept as a cost.

## Alternatives considered
What else was on the table and why it lost.
```

ADRs are how a new agent in month four understands why something looks the way
it does, instead of "improving" it back into a problem you already solved.
