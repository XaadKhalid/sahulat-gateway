import { http } from 'msw';
import { tenantData } from '../data';
import { jsonOk, notFound, requireAuth, unauthorized } from '../utils';

export const publishHandlers = [
  // POST /tenants/:id/publish — publish tenant (draft → live)
  http.post('/api/v1/admin/tenants/:id/publish', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    const tenant = tenantData.byId(id as string);
    if (!tenant) return notFound(`Tenant ${id} not found.`);

    const violations = tenantData.getPublishPreconditions(id as string);
    if (violations !== null && violations.length > 0) {
      return jsonOk(
        {
          detail: 'Cannot publish tenant — unresolved preconditions.',
          type: 'publish_preconditions_unmet',
          violations,
        },
        409,
      );
    }

    const published = tenantData.publish(id as string);
    if (!published) return notFound(`Tenant ${id} not found.`);
    return jsonOk(published, 200);
  }),
];
