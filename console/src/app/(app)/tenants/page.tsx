'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { client } from '@/lib/api-client/client';
import type { components } from '@/lib/api-client/generated/types';
import { StatusBadge } from '@/components/ui/status-badge';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

type Tenant = components['schemas']['Tenant'];
type TenantList = components['schemas']['TenantList'];

export default function TenantsPage() {
  const [data, setData] = useState<TenantList | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    client.GET('/tenants').then(res => {
      if (!active) return;
      if (res.data) setData(res.data);
      if (res.error) {
        const detail =
          typeof res.error.detail === 'string'
            ? res.error.detail
            : JSON.stringify(res.error.detail);
        setErr(detail || 'Failed to load tenants');
      }
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  async function createTenant() {
    const name = window.prompt('Tenant name?');
    if (!name) return;
    await client.POST('/tenants', { body: { name } });
    setLoading(true);
    const res = await client.GET('/tenants');
    if (res.data) setData(res.data);
    setLoading(false);
  }

  if (loading) return <div className="text-mute">Loading tenants…</div>;
  if (err) return <div className="text-danger">Error: {err}</div>;

  const tenants = data?.items ?? [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-green">Control plane</p>
          <h1 className="font-display text-4xl text-ink">Tenants</h1>
        </div>
        <Button onClick={createTenant}>Create tenant</Button>
      </header>

      {tenants.length === 0 ? (
        <p className="text-mute">No tenants yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="text-left py-2 text-xs font-medium uppercase tracking-wider text-mute">
                  Name
                </th>
                <th className="text-left py-2 text-xs font-medium uppercase tracking-wider text-mute">
                  Status
                </th>
                <th className="text-left py-2 text-xs font-medium uppercase tracking-wider text-mute">
                  WhatsApp
                </th>
                <th className="text-left py-2 text-xs font-medium uppercase tracking-wider text-mute">
                  Created
                </th>
                <th className="text-right py-2 text-xs font-medium uppercase tracking-wider text-mute">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t: Tenant) => (
                <tr key={t.id} className="border-t border-line">
                  <td className="py-2 text-ink">{t.name}</td>
                  <td className="py-2">
                    <StatusBadge status={t.status as Tenant['status']} />
                  </td>
                  <td className="py-2 text-ink-2">
                    {t.whatsapp_connected ? (
                      <Badge variant="default">Connected</Badge>
                    ) : (
                      <Badge variant="mute">Not connected</Badge>
                    )}
                  </td>
                  <td className="py-2 text-ink-2">{new Date(t.created_at).toLocaleDateString()}</td>
                  <td className="py-2 text-right">
                    <Link href={`/tenants/${t.id}`} className="text-sm text-green hover:underline">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
