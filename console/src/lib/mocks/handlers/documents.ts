import { http, HttpResponse } from 'msw';
import type { components } from '../../api-client/generated/types';
import { documentsData, tenantData, paginate } from '../data';
import { jsonOk, notFound, requireAuth, unauthorized, validationError } from '../utils';

type Document = components['schemas']['Document'];

export const documentHandlers = [
  // GET /tenants/:id/documents — paginated list
  http.get('/api/v1/admin/tenants/:id/documents', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    if (!tenantData.byId(id as string)) return notFound(`Tenant ${id} not found.`);

    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') ?? '50', 10);
    const cursor = url.searchParams.get('cursor') ?? undefined;

    const docs = documentsData.byTenant(id as string);
    const result = paginate<Document>(docs, limit, cursor);
    return jsonOk(result);
  }),

  // POST /tenants/:id/documents — upload (multipart)
  http.post('/api/v1/admin/tenants/:id/documents', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    if (!tenantData.byId(id as string)) return notFound(`Tenant ${id} not found.`);

    try {
      const formData = await request.formData();
      const file = formData.get('file');
      if (!file) {
        return validationError(['body', 'file'], 'A file must be provided');
      }
      const filename = file instanceof File ? file.name : String(file);
      if (!filename) {
        return validationError(['body', 'file'], 'Filename is required');
      }
      const doc = documentsData.upload(id as string, filename);
      return jsonOk(doc, 201);
    } catch {
      return validationError(['body'], 'Invalid multipart form data');
    }
  }),

  // GET /tenants/:id/documents/:document_id — poll for status
  http.get('/api/v1/admin/tenants/:id/documents/:document_id', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id, document_id } = params;
    if (!tenantData.byId(id as string)) return notFound(`Tenant ${id} not found.`);

    const doc = documentsData.byId(id as string, document_id as string);
    if (!doc) return notFound(`Document ${document_id} not found.`);
    return jsonOk(doc);
  }),

  // DELETE /tenants/:id/documents/:document_id
  http.delete('/api/v1/admin/tenants/:id/documents/:document_id', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id, document_id } = params;
    if (!tenantData.byId(id as string)) return notFound(`Tenant ${id} not found.`);

    const ok = documentsData.delete(id as string, document_id as string);
    if (!ok) return notFound(`Document ${document_id} not found.`);
    return new HttpResponse(null, { status: 204, headers: { 'Content-Length': '0' } });
  }),
];
