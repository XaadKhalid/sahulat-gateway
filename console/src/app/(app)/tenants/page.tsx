'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { client } from '@/lib/api-client/client';
import type { components } from '@/lib/api-client/generated/types';
import { StatusBadge } from '@/components/ui/status-badge';

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

  if (loading) return <div className="text-gray-400">Loading tenants…</div>;
  if (err) return <div className="text-red-400">Error: {err}</div>;

  const tenants = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Tenants</h1>
        <button
          onClick={createTenant}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Create Tenant
        </button>
      </div>

      {tenants.length === 0 ? (
        <p className="text-gray-500">No tenants yet.</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th className="text-left py-2 text-gray-400">Name</th>
              <th className="text-left py-2 text-gray-400">Status</th>
              <th className="text-left py-2 text-gray-400">WhatsApp</th>
              <th className="text-left py-2 text-gray-400">Created</th>
              <th className="text-right py-2 text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((t: Tenant) => (
              <tr key={t.id} className="border-t border-gray-800">
                <td className="py-2 text-gray-100">{t.name}</td>
                <td className="py-2">
                  <StatusBadge status={t.status} />
                </td>
                <td className="py-2 text-gray-400">
                  {t.whatsapp_connected ? 'Connected' : 'Not connected'}
                </td>
                <td className="py-2 text-gray-400">
                  {new Date(t.created_at).toLocaleDateString()}
                </td>
                <td className="py-2 text-right">
                  <Link href={`/tenants/${t.id}`} className="text-blue-400 hover:text-blue-300">
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
