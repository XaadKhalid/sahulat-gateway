import { http, HttpResponse } from 'msw';
import type { components } from '../../api-client/generated/types';
import { auth, SESSION_COOKIE_NAME, userData } from '../data';
import { jsonOk } from '../utils';

type LoginRequest = components['schemas']['LoginRequest'];

// Emails that can log in during development. Password check is intentionally
// lax — any password works for known emails — so operators can log in without
// remembering a mock password.
const VALID_EMAILS = new Set(userData.all().map(u => u.email));

/** Extract the session token from the request Cookie header. */
function getSessionToken(request: Request): string | null {
  const cookieHeader = request.headers.get('cookie');
  if (!cookieHeader) return null;
  const cookies = cookieHeader.split(';').map(c => c.trim());
  for (const cookie of cookies) {
    const eqIdx = cookie.indexOf('=');
    if (eqIdx === -1) continue;
    const name = cookie.slice(0, eqIdx);
    if (name === SESSION_COOKIE_NAME) return cookie.slice(eqIdx + 1);
  }
  return null;
}

export const authHandlers = [
  // POST /auth/login — sets an httpOnly session cookie
  http.post('/api/v1/admin/auth/login', async ({ request }) => {
    try {
      const body = (await request.json()) as LoginRequest;
      if (!body.email || !VALID_EMAILS.has(body.email)) {
        return jsonOk({ detail: 'Invalid email or password.', type: 'invalid_credentials' }, 401);
      }
      const user = userData.all().find(u => u.email === body.email);
      if (!user) {
        return jsonOk({ detail: 'Invalid email or password.', type: 'invalid_credentials' }, 401);
      }
      const token = auth.createSession(user);
      return HttpResponse.json(
        { id: user.id, email: user.email, role: user.role },
        {
          status: 200,
          headers: {
            'Set-Cookie': `${SESSION_COOKIE_NAME}=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400`,
            'Access-Control-Allow-Origin': 'http://localhost:3000',
            'Access-Control-Allow-Credentials': 'true',
          },
        },
      );
    } catch {
      return jsonOk({ detail: 'Invalid request body.', type: 'invalid_request' }, 422);
    }
  }),

  // POST /auth/logout — clears the session cookie
  http.post('/api/v1/admin/auth/logout', async ({ request }) => {
    const token = getSessionToken(request);
    auth.clearSession(token);
    return new HttpResponse(null, {
      status: 204,
      headers: {
        'Set-Cookie': `${SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`,
      },
    });
  }),

  // GET /auth/me — returns current session user or 401
  http.get('/api/v1/admin/auth/me', async ({ request }) => {
    const token = getSessionToken(request);
    const user = auth.getUser(token);
    if (!user) {
      return jsonOk({ detail: 'Authentication required.', type: 'auth_required' }, 401);
    }
    return jsonOk({ id: user.id, email: user.email, role: user.role });
  }),
];
