# 0008. Admin-console implementation checkpoint

Date: 2026-09-18
Status: recorded implementation; review pending

The owner requested committing the existing work on task/SAH-002-admin-console.
This records the current implementation, not approval to merge or deploy it.

The pending backend uses a separate PostgreSQL sahulat_admin schema for staff
accounts and cookie sessions, Argon2 hashes through passlib/argon2-cffi, and
email-validator. Tenant metadata and document records are introduced by migration
0008. The console adds shared Radix-based UI primitives, class-variance-authority,
clsx and tailwind-merge. These packages were already present in the working tree
before the checkpoint request; no additional packages were installed here.

Review must resolve the contract and startup gaps recorded in STATE.md. In
particular, source checkpointing does not establish working invitation delivery,
document ingestion, provider linking, publication or sandbox orchestration.
The shell exposes navigation beyond the three-screen scope; those links do not
establish implemented features or expand the approved product scope.

Preserve the factory-based runtime contract and add tests for real API error
shapes and console connection failures before declaring the feature complete.
Local credential-bearing launch/probe files and logs are excluded from Git.
