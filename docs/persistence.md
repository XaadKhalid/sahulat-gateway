# PostgreSQL persistence runbook (SAH-003)

## Prerequisites and accounts

Use PostgreSQL 16. Keep a migration/schema-owner account separate from runtime.
The application login must not own application tables or inherit any owning role,
and must be NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION.
Only the trusted application decides tenant context after authenticated routing.
RLS does not protect against stolen runtime credentials deliberately changing context.

Store connection credentials in environment/secret management. No URLs or passwords
belong in tracked files. Configure local psql service entries outside the repository
(`sahulat_admin` and `sahulat_owner` in examples) and a protected password file, or
use psql's password prompt. Never put passwords in command-line arguments.

## Initialize roles and migrations

As a cluster role administrator, run once:

```shell
psql service=sahulat_admin -v ON_ERROR_STOP=1 -f scripts/bootstrap_roles.sql
```

The script deliberately fails if the group already exists rather than changing an
unknown role's privileges. Inspect existing role attributes/memberships before reuse.
The group has NOLOGIN and no credentials. Using the administrator's psql session,
create the application login and assign a password interactively:

```sql
CREATE ROLE sahulat_app LOGIN INHERIT NOSUPERUSER NOBYPASSRLS
    NOCREATEROLE NOCREATEDB NOREPLICATION;
GRANT sahulat_runtime TO sahulat_app;
\password sahulat_app
```

Use a dedicated database owner for migrations; it needs permission to create schemas
and the Alembic version table in public. Supply its async SQLAlchemy connection URL
through `SAHULAT_MIGRATION_DATABASE_URL` (postgresql+asyncpg scheme), then run:

```shell
uv run --locked alembic upgrade head
uv run --locked alembic current
```

`SAHULAT_DATABASE_URL` is the separately provisioned runtime URL, also using
postgresql+asyncpg. It has no default and is redacted by DatabaseSettings. Do not
reuse migration credentials. The health-only app does not load DatabaseSettings;
request-path database wiring arrives with SAH-005.

Review SQL without a database or credentials:

```shell
uv run --locked alembic upgrade head --sql
```

## Register a test tenant

Generate and retain a tenant UUID as the registration's idempotency identity.
The route key is the provider's actual WhatsApp phone-number ID supplied by the
operator; SAH-003 treats it as opaque and does not call the provider.
Run using the schema owner (not the runtime login):

```shell
psql service=sahulat_owner -v tenant_id=<tenant-uuid> -v tenant_name=<retailer-name> -v route_key=<phone-number-id> -f scripts/provision_tenant.sql
```

Replace placeholders with shell-quoted values appropriate to your shell. These
values are identifiers, not credentials. The script uses psql's SQL-literal quoting,
sets tenant context locally, and commits tenant plus route atomically. Exact replay
succeeds without changes; an existing ID/name/route mismatch rolls back and exits
nonzero. One route per tenant is enforced. Renaming/reassignment is deliberately
not provided by this bootstrap script.

## Runtime transaction contract

Create the async engine from DatabaseSettings at the composition root, inject an
async_sessionmaker, and use `tenant_transaction(factory, trusted_tenant_uuid)` for
one request/turn. Inject its session into the repositories. Never share sessions
between concurrent tasks, set tenant context globally, or commit inside repositories.

Routing is performed before that context through TenantRepository.resolve. It returns
only a tenant UUID or None and does not establish context. Unknown routes must be
rejected by the eventual ingress service. The runtime cannot inspect the private
routing table or insert tenants. Missing tenant context sees no rows and cannot write.

No HTTP error handler is needed yet because no database-backed route exists. Callers
must handle PersistenceFailure without logging its chained database exception or
returning SQL details. MessageIdentityConflict means a reused provider identifier
has different immutable data; do not treat it as a successful duplicate delivery.
Repositories do not commit, allowing audit/outbox to join the transaction in SAH-005.

## Tests and rollback

Run Docker Desktop with Linux containers (or Docker Engine on Linux), then:

```shell
uv run --locked pytest
```

Integration fixtures start a disposable PostgreSQL 16.15 container, generate fresh
credentials, migrate, connect through a separate restricted login, and downgrade
and remove test roles after each test. No persistent developer database is used.
Testcontainers cleans up its own containers. A missing Docker engine fails the
suite; integration tests are not silently skipped.

On this Windows Codex host, Docker access requires execution outside the sandbox.
If switching execution identities causes pytest cache access errors, run with
`-p no:cacheprovider`. This does not disable any tests or warnings.

`uv run --locked alembic downgrade base` removes all application tables, functions
and schemas and destroys their data. Use only for disposable tests or an explicitly
planned rollback with backups. The externally provisioned database/login/group roles
remain; schema migrations do not own their lifecycle.
