import { http, HttpResponse } from 'msw';
import type { components } from '../../api-client/generated/types';
import { sandboxData, tenantData, buildMockReply } from '../data';
import { jsonOk, notFound, requireAuth, unauthorized } from '../utils';

type SandboxMessageRequest = components['schemas']['SandboxMessageRequest'];

export const sandboxHandlers = [
  // OPTIONS catch-all for CORS preflight (cross-origin dev scenarios)
  http.options('*', () => {
    return new HttpResponse(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': 'http://localhost:3000',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    });
  }),

  // POST /tenants/:id/sandbox/messages — send message through the turn loop
  http.post('/api/v1/admin/tenants/:id/sandbox/messages', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    if (!tenantData.byId(id as string)) return notFound(`Tenant ${id} not found.`);

    try {
      const body = (await request.json()) as SandboxMessageRequest;
      if (!body.text) {
        return jsonOk({ detail: 'The "text" field is required.', type: 'missing_field' }, 422);
      }

      const session = sandboxData.getOrCreate(id as string, body.session_id);
      const reply = buildMockReply(body.text, id as string);

      // The mock reply's session_id should match the session
      reply.session_id = session.id;

      return jsonOk(reply, 200);
    } catch {
      return jsonOk({ detail: 'Invalid request body.', type: 'invalid_request' }, 422);
    }
  }),

  // POST /tenants/:id/sandbox/reset — clear sandbox session state
  http.post('/api/v1/admin/tenants/:id/sandbox/reset', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    if (!tenantData.byId(id as string)) return notFound(`Tenant ${id} not found.`);

    // Parse optional session_id from body
    let sessionId: string | undefined;
    try {
      const body = await request.json();
      if (body && typeof body === 'object' && 'session_id' in body) {
        sessionId = body.session_id as string | undefined;
      }
    } catch {
      // No body — that's fine, reset clears all sessions for this tenant
    }

    sandboxData.reset(id as string, sessionId);
    return new HttpResponse(null, { status: 204, headers: { 'Content-Length': '0' } });
  }),
];
