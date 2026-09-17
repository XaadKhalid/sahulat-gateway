'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { client } from '@/lib/api-client/client';
import type { components } from '@/lib/api-client/generated/types';
import { StatusBadge } from '@/components/ui/status-badge';

type TenantDetail = components['schemas']['TenantDetail'];
type Document = components['schemas']['Document'];

export default function TenantDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const [tenant, setTenant] = useState<TenantDetail | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [manifest, setManifest] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [manifestSaving, setManifestSaving] = useState(false);
  const [publishError, setPublishError] = useState<string[] | null>(null);
  const [publishDone, setPublishDone] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!id) return;
    let active = true;
    Promise.all([
      client.GET('/tenants/{id}', { params: { path: { id } } }),
      client.GET('/tenants/{id}/documents', { params: { path: { id } } }),
      client.GET('/tenants/{id}/manifest', {
        params: { path: { id } },
        parseAs: 'text',
      }),
    ]).then(([{ data: t }, { data: docs }, { data: mani }]) => {
      if (!active) return;
      if (t) setTenant(t);
      if (docs) setDocuments(docs.items ?? []);
      if (typeof mani === 'string') setManifest(mani);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [id, reloadKey]);

  async function handleWhatsAppConnect() {
    if (!id) return;
    await client.POST('/tenants/{id}/whatsapp/connect', {
      params: { path: { id } },
    });
    setReloadKey(k => k + 1);
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    await fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1/admin'}/tenants/${id}/documents`,
      {
        method: 'POST',
        credentials: 'include',
        body: formData,
      },
    );
    e.target.value = '';
    setReloadKey(k => k + 1);
    setUploading(false);
  }

  async function handleSaveManifest() {
    setManifestSaving(true);
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1/admin'}/tenants/${id}/manifest`,
      {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/yaml' },
        body: manifest,
      },
    );
    setManifestSaving(false);
    if (!res.ok) {
      const err = await res.json();
      alert(`Manifest validation failed:\n${JSON.stringify(err.detail, null, 2)}`);
    }
  }

  async function handlePublish() {
    if (!id) return;
    setPublishError(null);
    setPublishDone(false);
    const res = await client.POST('/tenants/{id}/publish', {
      params: { path: { id } },
    });
    if (res.error) {
      if (res.response.status === 409 && res.error.violations) {
        setPublishError(res.error.violations);
      } else {
        const msg =
          typeof res.error.detail === 'string'
            ? res.error.detail
            : JSON.stringify(res.error.detail);
        setPublishError([msg || 'Publish failed']);
      }
    } else if (res.data) {
      setTenant(prev => (prev ? { ...prev, status: res.data.status } : null));
      setPublishDone(true);
    }
  }

  if (loading) return <div className="text-gray-400">Loading tenant…</div>;
  if (!tenant) return <div className="text-red-400">Tenant not found.</div>;

  return (
    <div className="space-y-8">
      {/* Profile */}
      <section>
        <h2 className="text-lg font-semibold text-gray-200 mb-3">Profile</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Name</span>
            <p className="text-gray-100">{tenant.name}</p>
          </div>
          <div>
            <span className="text-gray-500">Status</span>
            <StatusBadge status={tenant.status} />
          </div>
          <div>
            <span className="text-gray-500">WhatsApp</span>
            <p className="text-gray-100">
              {tenant.whatsapp_connected ? 'Connected' : 'Not connected'}
            </p>
          </div>
          <div>
            <span className="text-gray-500">Document count</span>
            <p className="text-gray-100">{tenant.document_count}</p>
          </div>
          <div>
            <span className="text-gray-500">Manifest</span>
            <p className="text-gray-100">{tenant.manifest_status}</p>
          </div>
          <div className="flex items-end">
            {!tenant.whatsapp_connected && (
              <button
                onClick={handleWhatsAppConnect}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                Connect WhatsApp
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Documents */}
      <section>
        <h2 className="text-lg font-semibold text-gray-200 mb-3">Documents</h2>
        <div className="mb-3">
          <label className="block text-sm text-gray-400 mb-1">Upload</label>
          <input
            type="file"
            accept=".pdf,.txt,.md,.csv"
            onChange={handleUpload}
            disabled={uploading}
            className="text-sm text-gray-400"
          />
          {uploading && <p className="text-xs text-gray-500 mt-1">Uploading…</p>}
        </div>
        {documents.length === 0 ? (
          <p className="text-sm text-gray-500">No documents uploaded.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="text-left py-1 text-gray-500">Filename</th>
                <th className="text-left py-1 text-gray-500">Status</th>
                <th className="text-left py-1 text-gray-500">Created</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc: Document) => (
                <tr key={doc.document_id} className="border-t border-gray-800">
                  <td className="py-1 text-gray-100">{doc.filename}</td>
                  <td className="py-1 text-gray-400">{doc.status}</td>
                  <td className="py-1 text-gray-400">
                    {new Date(doc.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Manifest */}
      <section>
        <h2 className="text-lg font-semibold text-gray-200 mb-3">Manifest</h2>
        <textarea
          value={manifest}
          onChange={e => setManifest(e.target.value)}
          placeholder="No manifest defined yet. Paste OpenAPI 3.1 YAML here…"
          className="w-full h-64 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 font-mono placeholder-gray-600 focus:border-blue-500 focus:outline-none"
        />
        <div className="mt-2 flex items-center justify-between">
          <span className={`text-xs ${manifestSaving ? 'text-yellow-400' : 'text-gray-500'}`}>
            {manifestSaving ? 'Saving…' : manifest ? 'Saved' : 'Unsaved changes'}
          </span>
          <button
            onClick={handleSaveManifest}
            disabled={manifestSaving || !manifest.trim()}
            className="rounded-md bg-gray-700 px-3 py-1.5 text-sm text-gray-100 hover:bg-gray-600 disabled:opacity-50"
          >
            Save Manifest
          </button>
        </div>
      </section>

      {/* Publish */}
      <section>
        <h2 className="text-lg font-semibold text-gray-200 mb-3">Publish</h2>
        {publishError && (
          <ul className="mb-3 list-inside list-disc text-sm text-red-400">
            {publishError.map((v: string) => (
              <li key={v}>{v}</li>
            ))}
          </ul>
        )}
        {publishDone && (
          <p className="mb-3 text-sm text-green-400">
            Tenant published! Status is now &ldquo;live&rdquo;.
          </p>
        )}
        <div className="flex items-center gap-3">
          <button
            onClick={handlePublish}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Publish Tenant
          </button>
          <Link
            href={`/tenants/${id}/sandbox`}
            className="text-sm text-gray-400 hover:text-gray-300"
          >
            → Test in sandbox
          </Link>
        </div>
      </section>
    </div>
  );
}
