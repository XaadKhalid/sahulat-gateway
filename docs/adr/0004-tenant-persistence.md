# 0004. Tenant-scoped PostgreSQL persistence
Date: 2026-09-16
Status: accepted

## Context

SAH-003 needs a real data-layer isolation boundary and durable identity constraints
before webhook, audit and queue work. Tenant routing must happen before the
application has a tenant context. Runtime credentials must not be migration credentials.

## Decision

Use PostgreSQL 16 with separate sahulat and sahulat_private schemas. Migrations
own tables and functions. A separately bootstrapped NOLOGIN sahulat_runtime group
gets SELECT on tenants/sessions/messages and INSERT on sessions/messages only.
An externally provisioned login inherits that group without privileged attributes
or membership in an owning/migration role. No credentials are embedded in code.

Tenant, session and message tables ENABLE and FORCE row-level security. Policies
read one transaction-local tenant UUID through sahulat.current_tenant_id(). Missing
or cleared context matches no rows; malformed context fails. Explicit query filters
remain in repositories, but unfiltered SQL is still fenced by PostgreSQL policies.
The application sets context only after trusted routing. RLS is protection against
query mistakes, not a defense against a compromised runtime credential deliberately
setting a different tenant UUID; trusted application code owns tenant selection.

The private route table contains only a route key and tenant UUID. It has no runtime
schema/table grants. A SECURITY DEFINER function with a fixed safe search_path and
fully qualified references returns only the matching UUID. PUBLIC cannot execute it.
It does not set tenant context. This is the narrow pre-tenant lookup from ADR 0001.

Session identity is unique within (tenant, customer number). Message provider IDs
are unique within a tenant. Composite tenant/session foreign keys prevent linking a
message to another tenant's session even when the inserted tenant UUID is valid.
Repositories use insert-on-conflict-do-nothing and preserve immutable records.
Reusing a provider message ID with different content, session, channel or timestamp
raises MessageIdentityConflict rather than silently replacing evidence.

Callers own transactions; repositories never commit. The tenant_transaction context
manager sets a LOCAL database setting, commits only success and rolls back failures.
A database exception becomes PersistenceFailure with a generic message; callers
must not expose its chained database exception in HTTP responses or ordinary logs.
Business conflicts propagate unchanged. This preserves the shared transaction needed
for message + audit + outbox in SAH-005. No unused repository Protocols or service
wrappers are added; consumer-owned protocols arrive with real business consumers.

Provision test tenants through the operator-only psql script, using tenant UUID as
the retry identity. Exact replay succeeds; conflicting name/route rolls back.
Migrations remove owned schemas/functions/tables on downgrade; cluster roles are
externally managed and deliberately remain outside schema migration ownership.

Use the approved sqlalchemy asyncio extra for its required greenlet adapter. Use
Testcontainers' community.postgres module, with generated test credentials and a
separate runtime login. Its psql readiness check needs no psycopg2 package.

## Consequences

No admin HTTP endpoint or migration credential reaches the runtime application.
The application factory still serves process liveness without requiring a database;
SAH-005 will wire persistence into actual requests. Provisioning is an operator
procedure, not the M5 control plane. Context selection and credential separation
remain deployment obligations, covered by direct restricted-login integration tests.
Downgrade is destructive to conversation data and is suitable only for disposable
validation or a separately planned rollback with backups.

## Alternatives considered

- ORM-only tenant filters: one omitted predicate could leak data.
- Runtime superuser/table-owner credentials: can bypass or disable isolation.
- Session-wide tenant settings: can leak tenant context through the pool.
- Global provider-message uniqueness: incorrectly couples different tenants.
- A generic repository base or premature service layer: no current consumer need.

## References

- https://www.postgresql.org/docs/16/ddl-rowsecurity.html
- https://www.postgresql.org/docs/16/sql-createfunction.html
- https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
