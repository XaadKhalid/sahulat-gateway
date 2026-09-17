/**
 * In-memory mock data store for the admin API.
 *
 * This module holds all mock state used by the MSW handlers. It is a
 * plain module with mutable arrays/Maps — simple enough for dev and test,
 * and easy to reset between tests.
 *
 * No production data ever passes through here; these mocks exist solely to
 * let the UI build against the contract shape before the backend is live.
 */
import type { components } from '../api-client/generated/types';

type User = components['schemas']['User'];
type Tenant = components['schemas']['Tenant'];
type TenantDetail = components['schemas']['TenantDetail'];
type Document = components['schemas']['Document'];
type SandboxMessageResponse = components['schemas']['SandboxMessageResponse'];
type ToolCall = components['schemas']['ToolCall'];
type RetrievedChunk = components['schemas']['RetrievedChunk'];

// ---------------------------------------------------------------------------
// Auth sessions
// ---------------------------------------------------------------------------

interface Session {
  token: string;
  user: User;
}

const sessions = new Map<string, Session>();

export const SESSION_COOKIE_NAME = 'session';

export const auth = {
  createSession(user: User): string {
    const token = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    sessions.set(token, { token, user });
    return token;
  },
  getUser(token: string | null): User | null {
    if (!token) return null;
    return sessions.get(token)?.user ?? null;
  },
  clearSession(token: string | null): void {
    if (token) sessions.delete(token);
  },
};

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

const users: User[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    email: 'admin@acme.com',
    role: 'admin',
    created_at: '2026-09-17T09:00:00.000Z',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    email: 'ops@acme.com',
    role: 'operator',
    created_at: '2026-09-17T09:30:00.000Z',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    email: 'ops2@acme.com',
    role: 'operator',
    created_at: '2026-09-18T10:00:00.000Z',
  },
];

export const userData = {
  all: () => [...users],
  byId(id: string): User | undefined {
    return users.find(u => u.id === id);
  },
  create(email: string, role: 'admin' | 'operator'): User | null {
    if (users.some(u => u.email === email)) return null;
    const user: User = {
      id: crypto.randomUUID(),
      email,
      role,
      created_at: new Date().toISOString(),
    };
    users.push(user);
    return user;
  },
  updateRole(id: string, role: 'admin' | 'operator'): User | null {
    const user = users.find(u => u.id === id);
    if (!user) return null;
    user.role = role;
    return { ...user };
  },
  deactivate(id: string): boolean {
    const idx = users.findIndex(u => u.id === id);
    if (idx === -1) return false;
    users.splice(idx, 1);
    return true;
  },
  adminCount(): number {
    return users.filter(u => u.role === 'admin').length;
  },
};

// ---------------------------------------------------------------------------
// Tenants
// ---------------------------------------------------------------------------

const tenants: Tenant[] = [
  {
    id: 'a1111111-1111-1111-1111-111111111111',
    name: 'Acme Corp',
    status: 'live',
    whatsapp_connected: true,
    created_at: '2026-09-17T09:00:00.000Z',
  },
  {
    id: 'a2222222-2222-2222-2222-222222222222',
    name: 'Beta Retail',
    status: 'draft',
    whatsapp_connected: false,
    created_at: '2026-09-17T10:00:00.000Z',
  },
  {
    id: 'a3333333-3333-3333-3333-333333333333',
    name: 'Gamma Services',
    status: 'connecting',
    whatsapp_connected: false,
    created_at: '2026-09-18T08:00:00.000Z',
  },
];

const tenantPolicies: Record<string, Record<string, unknown>> = {
  'a1111111-1111-1111-1111-111111111111': {
    auto_reply: true,
    operating_hours: { start: '09:00', end: '18:00' },
  },
  'a2222222-2222-2222-2222-222222222222': {
    auto_reply: false,
  },
  'a3333333-3333-3333-3333-333333333333': {
    auto_reply: true,
  },
};

const manifests: Record<string, string> = {
  'a1111111-1111-1111-1111-111111111111': `openapi: 3.0.0
info:
  title: Acme Corp API
  version: 1.0.0
x-agent:
  name: acme-agent
  instructions: "Answer billing questions from the knowledge base."
paths:
  /customers/{id}:
    get:
      summary: Get customer by ID
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string }
`,
};

const publishState: Record<string, { published: boolean }> = {
  'a1111111-1111-1111-1111-111111111111': { published: true },
  'a2222222-2222-2222-2222-222222222222': { published: false },
  'a3333333-3333-3333-3333-333333333333': { published: false },
};

export const tenantData = {
  all: () => [...tenants],
  byId(id: string): Tenant | undefined {
    return tenants.find(t => t.id === id);
  },
  getDetail(id: string): TenantDetail | null {
    const t = tenants.find(t => t.id === id);
    if (!t) return null;
    const docs = documentsData.byTenant(t.id);
    return {
      id: t.id,
      name: t.name,
      status: t.status,
      whatsapp_connected: t.whatsapp_connected,
      created_at: t.created_at,
      document_count: docs.length,
      manifest_status: manifests[t.id] ? 'present' : 'pending',
      policy: tenantPolicies[t.id] ?? {},
    };
  },
  create(name: string): Tenant {
    const t: Tenant = {
      id: crypto.randomUUID(),
      name,
      status: 'draft',
      whatsapp_connected: false,
      created_at: new Date().toISOString(),
    };
    tenants.push(t);
    tenantPolicies[t.id] = {};
    publishState[t.id] = { published: false };
    return t;
  },
  update(
    id: string,
    patch: Partial<{ name: string; policy: Record<string, unknown> }>,
  ): TenantDetail | null {
    const t = tenants.find(t => t.id === id);
    if (!t) return null;
    if (patch.name !== undefined) t.name = patch.name;
    if (patch.policy !== undefined) tenantPolicies[t.id] = patch.policy;
    return this.getDetail(id);
  },
  setWhatsappConnected(id: string, connected: boolean): boolean {
    const t = tenants.find(t => t.id === id);
    if (!t) return false;
    t.whatsapp_connected = connected;
    if (connected) t.status = 'connecting';
    return true;
  },
  getManifest(id: string): string | null {
    return manifests[id] ?? null;
  },
  hasManifest(id: string): boolean {
    return !!manifests[id];
  },
  upsertManifest(id: string, yaml: string): boolean {
    const t = tenants.find(t => t.id === id);
    if (!t) return false;
    manifests[id] = yaml;
    return true;
  },
  getPublishPreconditions(id: string): string[] | null {
    const t = tenants.find(t => t.id === id);
    if (!t) return null;
    const violations: string[] = [];
    if (!t.whatsapp_connected) violations.push('WhatsApp is not connected.');
    if (!manifests[id]) violations.push('No manifest has been defined.');
    if (publishState[id]?.published) violations.push('Tenant is already published.');
    return violations;
  },
  publish(id: string): Tenant | null {
    const t = tenants.find(t => t.id === id);
    if (!t) return null;
    t.status = 'live';
    publishState[id] = { published: true };
    return { ...t };
  },
};

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

const tenantDocuments: Record<string, Document[]> = {
  'a1111111-1111-1111-1111-111111111111': [
    {
      document_id: 'd1111111-1111-1111-1111-111111111111',
      filename: 'acme_billing_faq.pdf',
      status: 'ready',
      created_at: '2026-09-17T11:00:00.000Z',
    },
    {
      document_id: 'd2222222-2222-2222-2222-222222222222',
      filename: 'acme_terms.pdf',
      status: 'ready',
      created_at: '2026-09-17T12:00:00.000Z',
    },
  ],
  'a2222222-2222-2222-2222-222222222222': [
    {
      document_id: 'd3333333-3333-3333-3333-333333333333',
      filename: 'beta_product_catalog.pdf',
      status: 'processing',
      created_at: '2026-09-17T14:00:00.000Z',
    },
  ],
};

export const documentsData = {
  byTenant(tenantId: string): Document[] {
    return tenantDocuments[tenantId] ?? [];
  },
  byId(tenantId: string, documentId: string): Document | undefined {
    return tenantDocuments[tenantId]?.find(d => d.document_id === documentId);
  },
  upload(tenantId: string, filename: string): Document {
    const doc: Document = {
      document_id: crypto.randomUUID(),
      filename,
      status: 'processing',
      created_at: new Date().toISOString(),
    };
    if (!tenantDocuments[tenantId]) tenantDocuments[tenantId] = [];
    tenantDocuments[tenantId].push(doc);
    return doc;
  },
  delete(tenantId: string, documentId: string): boolean {
    const arr = tenantDocuments[tenantId];
    if (!arr) return false;
    const idx = arr.findIndex(d => d.document_id === documentId);
    if (idx === -1) return false;
    arr.splice(idx, 1);
    return true;
  },
};

// ---------------------------------------------------------------------------
// Sandbox
// ---------------------------------------------------------------------------

interface SandboxSession {
  id: string;
  messages: Array<{
    role: 'user' | 'assistant';
    text: string;
  }>;
  tier: 'anonymous' | 'known' | 'verified' | 'privileged';
}

const sandboxSessions = new Map<string, SandboxSession>();

export const sandboxData = {
  getOrCreate(tenantId: string, sessionId?: string): SandboxSession {
    const key = `${tenantId}:${sessionId ?? crypto.randomUUID()}`;
    let session = sessionId ? sandboxSessions.get(key) : undefined;
    if (!session) {
      sessionId = sessionId ?? crypto.randomUUID();
      session = {
        id: sessionId,
        messages: [],
        tier: 'anonymous',
      };
      sandboxSessions.set(key, session);
    }
    return session;
  },
  reset(tenantId: string, sessionId?: string): void {
    if (sessionId) {
      sandboxSessions.delete(`${tenantId}:${sessionId}`);
    } else {
      // Clear all sessions for this tenant
      for (const key of sandboxSessions.keys()) {
        if (key.startsWith(`${tenantId}:`)) {
          sandboxSessions.delete(key);
        }
      }
    }
  },
  addMessage(tenantId: string, sessionId: string, role: 'user' | 'assistant', text: string): void {
    const session = sandboxSessions.get(`${tenantId}:${sessionId}`);
    if (session) {
      session.messages.push({ role, text });
    }
  },
};

// A canned orchestrator response for the mock
export function buildMockReply(text: string, tenantId: string): SandboxMessageResponse {
  const doc =
    documentsData.byTenant(tenantId).find(d => d.status === 'ready') ??
    documentsData.byTenant(tenantId)[0];

  const toolCalls: ToolCall[] = doc
    ? [
        {
          name: 'customer_lookup',
          args: { query: text },
          result: {
            customer: 'Jane Doe',
            account_status: 'active',
            balance: '$0.00',
          },
        },
      ]
    : [];

  const retrievedChunks: RetrievedChunk[] = doc
    ? [
        {
          source: doc.filename,
          excerpt:
            `Regarding your inquiry: "${text.slice(0, 40)}...", ` +
            `our knowledge base indicates the billing cycle ends on the 15th ` +
            `of each month and payment is due within 30 days.`,
        },
      ]
    : [];

  return {
    session_id: crypto.randomUUID(),
    reply:
      `Based on your documents${toolCalls.length ? ' and a tool call to customer_lookup' : ''}, here is what I found: ` +
      `Your account is active. ${toolCalls.length ? `The tool returned: ${JSON.stringify(toolCalls[0].result)}` : ''}`,
    tool_calls: toolCalls,
    retrieved_chunks: retrievedChunks,
    tier: 'anonymous',
  };
}

// ---------------------------------------------------------------------------
// Pagination helper
// ---------------------------------------------------------------------------

export function paginate<T>(
  items: T[],
  limit = 50,
  cursor?: string,
): { items: T[]; next_cursor: string | null } {
  let startIdx = 0;
  if (cursor) {
    const idx = items.findIndex(item => {
      const obj = item as Record<string, unknown>;
      return typeof obj === 'object' && obj !== null && 'id' in obj && obj.id === cursor;
    });
    if (idx !== -1) startIdx = idx + 1;
  }
  const slice = items.slice(startIdx, startIdx + limit);
  const hasNext = startIdx + limit < items.length;
  const lastItem = slice[slice.length - 1] as Record<string, unknown> | undefined;
  const nextCursor = hasNext && lastItem && typeof lastItem.id === 'string' ? lastItem.id : null;
  return { items: slice, next_cursor: nextCursor };
}
