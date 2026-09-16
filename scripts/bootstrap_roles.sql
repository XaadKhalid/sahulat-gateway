-- Run once per PostgreSQL cluster using a role administrator, before migrations.
-- Login accounts and credentials are provisioned separately, never in migrations.
CREATE ROLE sahulat_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
