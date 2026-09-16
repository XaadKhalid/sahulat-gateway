# 0005. Append-only partitioned audit storage and redaction
Date: 2026-09-16
Status: accepted

## Context

SAH-004 requires a secure, tenant-isolated audit log for the platform. The application runtime role must be able to append events but under no circumstances should it be able to update or delete them. We also need to partition the audit events monthly for lifecycle management. Finally, standard logs must not leak message bodies or phone numbers.

## Decision

We use PostgreSQL declarative partitioning (`PARTITION BY RANGE (occurred_at)`) for the `sahulat.audit_events` table.
The `sahulat_runtime` role is granted `INSERT` and `SELECT` on this table, but `UPDATE` and `DELETE` are omitted, making it append-only at the database engine level.
Row-Level Security (RLS) policies enforce tenant isolation just like the message tables.

A PL/pgSQL procedure `sahulat_private.provision_audit_partitions()` creates the current and next month's partitions automatically. It is revoked from PUBLIC.

For operational logging, a `RedactingFormatter` uses regex to intercept and strip out phone numbers and common credentials/JSON body fields from the standard Python `logging` stream before they can be written to disk/stdout.

## Consequences

- The application is physically incapable of updating or deleting audit logs, meeting the strict compliance bar.
- Monthly partition rollout must be scheduled or run regularly via the provision script to prevent INSERT failures on boundary crossings.
- RLS applies transparently, keeping audit event reading (for future API access) natively fenced by tenant context.
- Operational logs are safe from accidental credential or PII spillage, though structured logging adoption in the future may require replacing the regex formatter with a structural filter.
