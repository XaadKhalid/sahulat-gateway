import { HttpResponse } from 'msw';
import type { components } from '../api-client/generated/types';
import { auth, SESSION_COOKIE_NAME } from './data';

type User = components['schemas']['MeResponse'];

/**
 * The Next.js app origin, used for CORS headers in cross-origin dev scenarios.
 * When NEXT_PUBLIC_API_BASE_URL is a relative path (the default), requests
 * are same-origin and CORS is not needed — but setting these headers is
 * harmless and makes the mock layer work even when an absolute backend URL
 * is configured.
 */
export const ALLOWED_ORIGIN = process.env.NODE_ENV === 'production' ? '*' : 'http://localhost:3000';

/** Headers applied to every mock response so cross-origin requests work. */
export const CORS_HEADERS: Record<string, string> = {
  'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
  'Access-Control-Allow-Credentials': 'true',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

/**
 * Wrap a response value with the standard CORS headers + status.
 *
 * Uses new HttpResponse + JSON.stringify directly (rather than
 * HttpResponse.json) to avoid the JsonBodyType generic constraint — the
 * data we return is always JSON-serializable from the contract types.
 */
export function jsonOk(data: unknown, status = 200) {
  return new HttpResponse(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}

/** Return a 401 unauthenticated error. */
export function unauthorized() {
  return jsonOk({ detail: 'Authentication required.', type: 'auth_required' }, 401);
}

/** Return a 404 not-found error. */
export function notFound(detail = 'Resource not found.') {
  return jsonOk({ detail, type: 'not_found' }, 404);
}

/**
 * Return a 422 validation error with field-level detail (FastAPI format).
 */
export function validationError(loc: string[], msg: string, type = 'value_error') {
  return jsonOk(
    {
      detail: [{ loc, msg, type }],
    },
    422,
  );
}

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

/** Extract the session token from the request Cookie header. */
export function getSessionToken(request: Request): string | null {
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

/**
 * Check if the request is authenticated. Returns the user or null.
 * Each handler that requires auth calls this and returns unauthorized() if null.
 */
export function requireAuth(request: Request): User | null {
  const token = getSessionToken(request);
  if (!token) return null;
  return auth.getUser(token);
}
