# console/AGENTS.md — Control Plane UI

This file layers on top of the root `AGENTS.md`. Read that one first — the
session start/end protocol, hard rules, and workflow rules apply here
unchanged. This file only adds what's specific to building inside `console/`.

## What this is

The tenant admin portal. Not customer-facing — this is where a business owner
or your own ops staff manages the platform. Deliberately minimal per
`docs/product-scope.md`: **three screens only** for phase 1.

1. **User management** — portal operator/staff accounts and roles.
2. **Business profile management** — tenant onboarding: name, WhatsApp
   connection status, document upload, manifest registration, policy settings.
3. **Sandbox chat window** — real-time chat against the live orchestrator to
   test a tenant's configuration before it goes live.

Do not add a dashboard, an analytics view, a billing screen, or anything not
on this list without asking first. This restraint is the point, not a gap to
fill in.

## The contract-first rule (read this before writing any code)

**As of this file's creation, the backend admin API does not exist yet** —
only `/health` and internal persistence/dispatch code are implemented. This
means you cannot build against real endpoints today, and you must not invent
ones and hope the backend matches later.

Process:

1. Check `docs/admin-api-contract.md`. If it defines the endpoint you need,
   build against exactly that shape — request/response fields, error format,
   auth header, everything.
2. If the endpoint you need is not yet in that file, **stop and propose the
   addition there first** (as a diff, for the owner to approve) rather than
   guessing the shape and building UI around your guess. The contract file is
   the single source of truth both sides build against; an endpoint that
   exists only in your component's assumptions is a bug waiting to happen.
3. Until the backend implements an endpoint for real, mock it at the network
   boundary (MSW or an equivalent) using the exact contract shape — not an
   ad-hoc shape that's "close enough". When the real endpoint ships, the mock
   should need zero changes to your component code, only the mock layer
   removed.

Never call a made-up endpoint path, never invent a response field the
contract doesn't list, and never silently work around a missing contract
entry by loosening your own types.

## Stack

- **Next.js 16**, App Router, TypeScript strict. Async request APIs
  (`params`, `searchParams`, `cookies()`, `headers()`) have no synchronous
  fallback in 16 — always `await` them. Turbopack is the default bundler;
  don't reintroduce a webpack config. `middleware.ts` is `proxy.ts` in 16.
- **Tailwind CSS** + **shadcn/ui** for components — matches the original
  solution design and keeps the surface small and consistent rather than
  hand-rolling UI primitives.
- Server Components by default; `"use client"` only where interactivity
  requires it (forms, the sandbox chat window's live updates).
- Data fetching via a typed client generated from the OpenAPI schema FastAPI
  produces (`openapi-typescript` or equivalent) — not hand-written `fetch`
  calls with inferred types. If the type doesn't match the contract, that's a
  signal to fix the contract file or the generation step, not to cast around
  it.
- Forms: `react-hook-form` + `zod`, schema mirroring the contract's
  request shape.
- State: React state and server state (via the data-fetching layer) only. No
  global client state library — there's nothing in three screens that needs
  one. If you find yourself reaching for one, that's a sign scope is
  creeping.

## Project layout

```
console/
  app/
    (auth)/                  login for portal staff
    users/                   screen 1
    tenants/                 screen 2 — business profile management
    sandbox/                 screen 3 — live chat testing
    layout.tsx
  components/
    ui/                      shadcn primitives, generated not hand-edited
    <feature>/                feature-scoped components, colocated with the screen
  lib/
    api-client/               generated typed client + thin wrapper
    mocks/                     MSW handlers, one file per contract resource
  AGENTS.md                  this file
```

## Quality bar

Same spirit as the backend standards, translated:

- **SOLID still applies.** A component that fetches, transforms, and renders
  is doing three jobs — split fetching into a hook or server function,
  transformation into a plain function, rendering into a component that just
  takes props.
- **DRY by rule of three**, same as the backend. Two similar forms are not
  necessarily one generic `<Form>` component; wait for the third before
  abstracting, and never build a "flexible" form engine for three screens.
- No `any`. No `@ts-ignore` without a comment explaining why it's safe.
- ESLint + Prettier clean before commit, config matching this repo's
  `.eslintrc`/`prettier` (create if absent, don't invent a divergent style).
- Every screen has a loading state and an error state. Neither is optional.
- Accessible by default: real `<button>`/`<label>` elements, keyboard
  navigation works, forms have associated labels. shadcn/ui gives you this
  for free if you don't fight it.
- No secrets, tokens, or API keys in client-side code, ever — this is a
  server-rendered Next.js app; anything sensitive stays server-side.

## Testing

- Component tests with Vitest + Testing Library for the three screens'
  meaningful interactions (submit a form, see a validation error, see a
  sandbox reply render).
- Mock Service Worker for API interaction tests — test against the contract
  shape, not against whatever the component happens to send.
- No snapshot tests as the primary assertion; they rot silently and don't
  communicate intent.

## Session end protocol addition

In addition to the root `AGENTS.md` section 2 requirements: if you added or
changed anything in `docs/admin-api-contract.md`, say so explicitly in your
summary and flag it for backend-side review — a contract change is a
cross-cutting decision, not a UI-only one.
