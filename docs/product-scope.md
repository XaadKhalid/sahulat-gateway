# Product Scope

## The product in one paragraph

A business connects a WhatsApp number, uploads its documents, and points us at
its APIs. We turn that into an agent that answers questions from the business's
own content and performs real operations through the business's own systems,
recognising the customer by phone number and verifying them when the action
requires it. Strictly inside that business's domain. The business does not build
a bot; it describes itself.

## Phase 1: e-commerce, text only

The first tenant type is an online retailer. Everything built now is validated
against that use case, without hard-coding it — the same engine must later serve
a bank with a different manifest and no code change.

### In scope

| Capability | Detail |
|---|---|
| Channel | WhatsApp Cloud API. Inbound text, interactive buttons and lists. Outbound text, buttons, approved templates, 24-hour service window handling. **Development and testing use Meta's own free test number and access token directly through the Cloud API — no BSP (Twilio/360dialog/etc.) in the loop, no cost.** See the note below the table. |
| Knowledge | Ingest PDF, DOCX, XLSX, MD, HTML and crawled web pages. Chunk by structure. Hybrid retrieval. Answers grounded in the corpus only. |
| Catalog | Product data as a first-class queryable source: search, availability, price, variants. |
| Identity | Phone number as principal. Anonymous → known → verified tiers. Lookup against tenant API. OTP step-up. |
| Actions | Tenant-supplied OpenAPI 3.1 manifest with `x-agent` annotations. Risk levels, required tier, confirmation gates, ownership checks, idempotency. |
| Commerce flows | Order status, order tracking, returns/exchange initiation, product search, place a COD order. |
| Guardrails | Domain fence, tool exposure by tier, prompt-injection defence on retrieved content and tool results, PII redaction in logs. |
| Human handoff | Escalate with full context to a human inbox; human replies in the same thread; AI resumes. |
| Audit | Complete, append-only, queryable. |
| Control plane | Minimal, multi-tenant admin portal. Deliberately few screens for phase 1: **user management** (portal operator/staff accounts and roles), **business profile management** (tenant onboarding — name, WhatsApp connection, document upload, manifest registration, policy settings), and a **sandbox chat window** for real-time conversation testing against the live orchestrator before a tenant goes live. Clean and functional over feature-rich; every additional screen is a phase 2+ decision, not a default. |

### Explicitly out of scope for phase 1

Do not build these. Do not build "hooks for" these beyond the interface
boundaries already named in `architecture.md`.

- Voice notes, ASR, TTS, WhatsApp Calling. **Deferred to a later phase.**
  The message envelope must not assume text, but no audio code is written now.
- Any channel other than WhatsApp (no web widget, SMS, Slack, Teams).
- Self-serve signup, billing, subscription management.
- Prebuilt connectors for Shopify/Zoho/Odoo/etc. Phase 1 is a generic OpenAPI
  manifest. A specific connector is proven demand, not speculation.
- MCP support.
- Vision, image understanding, document photo processing.
- Campaigns, broadcasts, proactive notification engine.
- Payments in chat beyond handing over the tenant's own payment link.
- Multi-region, sovereign/on-prem deployment work, air-gapped bundles.
- Fine-tuning anything.
- Analytics dashboards beyond raw conversation viewing.
- "AI ERP / AI CRM" framing of any kind.

If a task seems to require one of these, stop and raise it. The most likely
failure mode of this project is building phase 3 before phase 1 works.

### A note on WhatsApp testing cost

Development and testing on the real WhatsApp Cloud API do not cost money.
Direct from Meta: no monthly fee for API access, a free test phone number and
temporary access token from the Meta Developers console, and service
conversations (replies inside a customer-initiated 24-hour window) are free
and uncapped. What costs money is a paid BSP layer (Twilio, 360dialog, Wati,
etc.) added on top, and template/marketing messages sent outside that window
at scale — neither applies to phase 1 development. Build and test directly
against Meta's Cloud API, not through a BSP, for exactly this reason.

## Milestones

Each milestone is demonstrable end to end. No milestone is "infrastructure only".

**M0 — Walking skeleton.**
Inbound WhatsApp webhook, signature verified, normalised to an envelope,
persisted, echoed back to the sender. Audit log written. Deployed and running
against a real test number. Nothing intelligent. Proves the whole pipe.

**M1 — Grounded answers.**
Document ingestion and retrieval. The agent answers catalog and policy questions
from tenant content, with a fixed refusal for out-of-domain messages. No
identity, no actions. A tenant with documents only is already a shippable
product at this point.

**M2 — Identity.**
Number-to-customer lookup, tier caching, OTP step-up as orchestrator state
(never model output), tier expiry. Tier-gated retrieval: documents tagged for
`verified` are invisible to an anonymous caller.

**M3 — Actions.**
Manifest loading, tool registry filtered by tier, confirmation gates, ownership
checks, idempotent execution, full tool audit. First real actions: order status
and order tracking.

**M4 — Commerce loop.**
Product search from catalog, multi-turn field collection, place a COD order,
initiate a return. This is the milestone a retailer can actually run on.

**M5 — Operations.**
Human handoff inbox, conversation viewer, sandbox test chat, transcript replay
evals.

## Non-functional targets for phase 1

- Median response under 5 seconds for a retrieval answer, under 10 for an action.
- Correct refusal of out-of-domain requests, measured by an eval set, not vibes.
- Zero cross-tenant data access, proven by test.
- Zero action executed above the caller's tier, proven by test.
- Every conversation fully reconstructable from the audit log.