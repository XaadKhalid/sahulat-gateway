# AGENTS.md — Sahulat Operating Manual

## 1. Session start protocol (mandatory, no exceptions)

Before writing a single line of code:

1. Read this file.
2. Read `docs/STATE.md` — the current truth of the project. It supersedes
   anything you remember, assume, or were told in a previous session.
3. Read the task file you were assigned in `docs/tasks/`.
4. Read `docs/engineering-standards.md` if you have not read it in this session.
5. Read only the source files the task touches. Do not read the whole repo.

If `docs/STATE.md` and the code disagree, **the code is the truth** — fix
`docs/STATE.md` as part of your task and say so in your summary.

## 2. Session end protocol (mandatory, no exceptions)

You are not done until all of the following are true:

- [ ] Code compiles, all tests pass, linter/formatter clean.
- [ ] New behaviour is covered by tests.
- [ ] `docs/STATE.md` updated: what changed, what is now true, what is next,
      any gotcha the next agent would otherwise rediscover the hard way.
- [ ] Any architectural decision recorded as an ADR in `docs/adr/`.
- [ ] Work committed in small, conventional commits referencing the task id.
- [ ] Your final message lists: files changed, decisions made, assumptions made,
      and anything you deliberately did not do.

**Never end a session with uncommitted work or an un-updated `STATE.md`.**
Assume you will be replaced mid-task by a different agent from a different
provider who has never seen this conversation. That is the normal case, not
the exception.

## 3. What this project is

A conversational agent gateway: one WhatsApp number per business, answering
from that business's own documents and performing real operations through that
business's own APIs, fenced strictly to that business's domain.

**Phase 1 target: e-commerce tenants. Text messages only.**
Voice, calling, and other channels are explicitly out of scope for now — but
the message envelope must not assume text. See `docs/product-scope.md`.

Full detail lives in:
- `docs/product-scope.md` — what we are building and, importantly, what we are not
- `docs/architecture.md` — target architecture, stack, module boundaries
- `docs/engineering-standards.md` — the code quality bar (non-negotiable)
- `docs/STATE.md` — where the project actually is right now
- `docs/adr/` — why things are the way they are
- `docs/source/sahulat-solution-design.html` — original vision doc, human reference only.
  **Do not load it into context.** It is aspirational and much of it is
  deliberately deferred. `docs/` is authoritative; that file is not.

## 4. Hard rules

1. **Scope discipline.** Build exactly what the task says. If you believe the
   task needs something outside its stated scope, stop and say so in your
   summary. Do not build it. Unrequested features are rejected on review.
2. **No secrets in source.** Ever. Not in `appsettings.json`, not in tests, not
   in comments, not as a "temporary" default value. Configuration and secret
   managers only.
3. **No new dependency without asking.** Adding a package to `pyproject.toml` is an
   architectural decision. Propose it, justify it, wait for approval.
4. **No TODO, no stub, no `NotImplementedException` on a merged path.** If you
   cannot finish it, do not merge it. A smaller complete thing beats a larger
   half thing.
5. **No silent failure.** Every external call can fail. Handle it explicitly or
   let it propagate to a handler that does.
6. **Tests are not optional** and are not written after the fact by someone
   else. Business logic ships with tests in the same commit.
7. **Do not invent APIs, fields, endpoints, or WhatsApp behaviours.** If you do
   not know how something works, say you do not know. A wrong confident answer
   costs more than a question.
8. **Do not reformat, rename, or "clean up" code the task did not ask you to
   touch.** It destroys reviewability. Propose it as a separate task.
9. **Audit everything in the conversation path.** Inbound message, retrieved
   chunks, tool calls with arguments and results, model prompts and outputs,
   tier changes, handoffs. This is a regulated-buyer product; the audit log is
   a feature, not logging.
10. **The model never decides policy.** Which tools exist for this user at this
    identity tier is decided in code, before the model is called. The model can
    only request tools it was given.

## 5. Code quality bar

Full rules in `docs/engineering-standards.md`. The headline:

- **SOLID**, applied as designed-in structure, not retrofitted.
- **DRY by the rule of three** — duplication is extracted on the third
  occurrence, not the second, and never into a generic abstraction that serves
  hypothetical future cases. See the anti-over-abstraction section; it is as
  binding as DRY itself.
- Routers are thin. Business logic is in services. Data access is behind
  repositories. Nothing skips a layer.
- Dependencies are injected, not imported and instantiated. Every service must
  be constructible in a test with no FastAPI app and no network.
- `async def` for all I/O. **Never a blocking call inside async** — no
  `requests`, no `time.sleep`, no sync database driver.
- `Decimal` for money. Never `float`.
- `mypy --strict` passes. Pydantic models at every boundary, never raw dicts.
- Functions short enough to read without scrolling. Names describe intent.
- Comments explain *why*. The code already says *what*.

Review rejects code that passes tests but violates these. "It works" is not the
bar.

## 6. Workflow

- One task per branch: `task/<id>-<slug>`.
- Conventional commits: `feat(orchestrator): add tier gate to tool registry (SAH-014)`.
- Small commits. A commit that touches 30 files is a review failure.
- Before starting: restate the task in your own words and list your plan. Wait
  for confirmation on anything ambiguous.
- After finishing: summary per section 2.

## 7. When you are stuck or uncertain

Say so, explicitly, and stop. Acceptable and expected:

> I cannot complete SAH-021 as specified. The task assumes the identity lookup
> returns a customer id, but `docs/architecture.md` §4 defines it as returning a
> principal object. I need a decision before proceeding.

Unacceptable: guessing, inventing an interface to keep moving, or quietly
narrowing the task and reporting success.
