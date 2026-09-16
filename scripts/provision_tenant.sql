\set ON_ERROR_STOP on
-- Supply tenant_id, tenant_name and route_key with psql -v. No credential values.
BEGIN;
SELECT set_config('sahulat.tenant_id', :'tenant_id', true);
INSERT INTO sahulat.tenants (id, name) VALUES (:'tenant_id'::uuid, :'tenant_name')
    ON CONFLICT (id) DO NOTHING;
INSERT INTO sahulat_private.tenant_routes (route_key, tenant_id)
    VALUES (:'route_key', :'tenant_id'::uuid) ON CONFLICT DO NOTHING;
SELECT EXISTS (
    SELECT 1 FROM sahulat.tenants AS tenant
    JOIN sahulat_private.tenant_routes AS route ON route.tenant_id = tenant.id
    WHERE tenant.id = :'tenant_id'::uuid AND tenant.name = :'tenant_name'
      AND route.route_key = :'route_key'
) AS registration_matches \gset
\if :registration_matches
    COMMIT;
\else
    ROLLBACK;
    DO $$ BEGIN
        RAISE EXCEPTION 'Registration conflicts with an existing tenant or route.';
    END $$;
\endif
