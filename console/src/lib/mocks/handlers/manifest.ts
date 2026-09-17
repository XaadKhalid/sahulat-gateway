import { http, HttpResponse } from 'msw';
import { tenantData } from '../data';
import { notFound, requireAuth, unauthorized, validationError } from '../utils';

/**
 * Basic manifest validation for the mock layer.
 *
 * The real backend uses actions/manifest.py to validate. The mock performs a
 * structural check (looks for the required top-level YAML keys) and returns
 * 422 with field-level errors if anything is missing — matching the contract's
 * documented format.
 */
function validateManifest(yaml: string): string[] {
  const errors: string[] = [];
  if (!yaml.trim()) {
    errors.push('Manifest body is empty.');
    return errors;
  }
  if (!/^\s*openapi:\s/m.test(yaml)) {
    errors.push('Missing required field: "openapi" version.');
  }
  if (!/^\s*info:\s/m.test(yaml)) {
    errors.push('Missing required field: "info" section.');
  }
  if (!/^\s*paths:\s/m.test(yaml)) {
    errors.push('Missing required field: "paths" section.');
  }
  return errors;
}

export const manifestHandlers = [
  // PUT /tenants/:id/manifest — replace manifest (raw OpenAPI YAML)
  http.put('/api/v1/admin/tenants/:id/manifest', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    if (!tenantData.byId(id as string)) return notFound(`Tenant ${id} not found.`);

    const contentType = request.headers.get('content-type') ?? '';
    if (!contentType.includes('yaml') && !contentType.includes('text/plain')) {
      return validationError(['header', 'Content-Type'], 'Content-Type must be application/yaml');
    }

    const yamlText = await request.text();
    const errors = validateManifest(yamlText);
    if (errors.length > 0) {
      return validationError(['body'], errors.join('; '));
    }

    tenantData.upsertManifest(id as string, yamlText);
    return new HttpResponse(null, { status: 204, headers: { 'Content-Length': '0' } });
  }),

  // GET /tenants/:id/manifest — retrieve raw YAML
  http.get('/api/v1/admin/tenants/:id/manifest', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    if (!tenantData.byId(id as string)) return notFound(`Tenant ${id} not found.`);

    const manifest = tenantData.getManifest(id as string);
    if (!manifest) {
      return notFound('No manifest has been defined for this tenant.');
    }
    return new HttpResponse(manifest, {
      status: 200,
      headers: { 'Content-Type': 'application/yaml' },
    });
  }),
];
