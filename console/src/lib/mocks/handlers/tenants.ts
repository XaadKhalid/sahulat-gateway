import { http } from 'msw';
import type { components } from '../../api-client/generated/types';
import { tenantData, paginate } from '../data';
import { jsonOk, notFound, requireAuth, unauthorized, validationError } from '../utils';

type CreateTenantRequest = components['schemas']['CreateTenantRequest'];
type UpdateTenantRequest = components['schemas']['UpdateTenantRequest'];

export const tenantHandlers = [
  // GET /tenants — paginated list
  http.get('/api/v1/admin/tenants', async ({ request }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') ?? '50', 10);
    const cursor = url.searchParams.get('cursor') ?? undefined;

    const result = paginate(tenantData.all(), limit, cursor);
    return jsonOk(result);
  }),

  // POST /tenants — create tenant
  http.post('/api/v1/admin/tenants', async ({ request }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    try {
      const body = (await request.json()) as CreateTenantRequest;
      if (!body.name) {
        return validationError(['body', 'name'], 'Name is required');
      }
      if (body.name.length < 2) {
        return validationError(['body', 'name'], 'Name must be at least 2 characters');
      }
      const created = tenantData.create(body.name);
      return jsonOk(created, 201);
    } catch {
      return validationError(['body'], 'Invalid JSON body');
    }
  }),

  // GET /tenants/:id — full detail
  http.get('/api/v1/admin/tenants/:id', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    const detail = tenantData.getDetail(id as string);
    if (!detail) return notFound(`Tenant ${id} not found.`);
    return jsonOk(detail);
  }),

  // PATCH /tenants/:id — partial update
  http.patch('/api/v1/admin/tenants/:id', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    try {
      const body = (await request.json()) as UpdateTenantRequest;
      const updated = tenantData.update(id as string, body);
      if (!updated) return notFound(`Tenant ${id} not found.`);
      return jsonOk(updated);
    } catch {
      return validationError(['body'], 'Invalid JSON body');
    }
  }),
];
