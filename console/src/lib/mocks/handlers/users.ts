import { http, HttpResponse } from 'msw';
import type { components } from '../../api-client/generated/types';
import { userData, paginate } from '../data';
import { jsonOk, notFound, requireAuth, unauthorized, validationError } from '../utils';

type User = components['schemas']['User'];
type CreateUserRequest = components['schemas']['CreateUserRequest'];
type UpdateUserRoleRequest = components['schemas']['UpdateUserRoleRequest'];

export const userHandlers = [
  // GET /users — paginated list
  http.get('/api/v1/admin/users', async ({ request }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') ?? '50', 10);
    const cursor = url.searchParams.get('cursor') ?? undefined;

    const result = paginate<User>(userData.all(), limit, cursor);
    return jsonOk(result);
  }),

  // POST /users — create user
  http.post('/api/v1/admin/users', async ({ request }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    try {
      const body = (await request.json()) as CreateUserRequest;
      if (!body.email || !body.role) {
        return validationError(['body', 'email'], 'Email is required');
      }
      if (!body.email.includes('@')) {
        return validationError(['body', 'email'], 'Invalid email address');
      }
      const created = userData.create(body.email, body.role);
      if (!created) {
        return jsonOk(
          { detail: 'A user with this email already exists.', type: 'user_exists' },
          409,
        );
      }
      return jsonOk(created, 201);
    } catch {
      return validationError(['body'], 'Invalid JSON body');
    }
  }),

  // PATCH /users/:id — update role
  http.patch('/api/v1/admin/users/:id', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    try {
      const body = (await request.json()) as UpdateUserRoleRequest;
      if (!body.role) {
        return validationError(['body', 'role'], 'Role is required');
      }
      if (id === user.id && body.role === 'operator' && userData.adminCount() <= 1) {
        return jsonOk(
          {
            detail: 'Cannot remove the last admin role from yourself.',
            type: 'cannot_demote_last_admin',
            violations: [
              'You are the only remaining admin. Assign this role to another user first.',
            ],
          },
          409,
        );
      }
      const updated = userData.updateRole(id as string, body.role);
      if (!updated) return notFound(`User ${id} not found.`);
      return jsonOk(updated);
    } catch {
      return validationError(['body'], 'Invalid JSON body');
    }
  }),

  // DELETE /users/:id — deactivate user
  http.delete('/api/v1/admin/users/:id', async ({ request, params }) => {
    const user = requireAuth(request);
    if (!user) return unauthorized();

    const { id } = params;
    if (id === user.id) {
      return jsonOk(
        {
          detail: 'You cannot deactivate your own account.',
          type: 'cannot_deactivate_self',
          violations: ['You must ask another admin to deactivate your account.'],
        },
        409,
      );
    }
    const ok = userData.deactivate(id as string);
    if (!ok) return notFound(`User ${id} not found.`);
    return new HttpResponse(null, { status: 204, headers: { 'Content-Length': '0' } });
  }),
];
