import createClient from 'openapi-fetch';
import { API_BASE_URL } from './config';
import type { paths } from './generated/types';

/**
 * Typed API client.
 *
 * `openapi-fetch` infers request/response types from the generated `paths`
 * type, so every `client.GET`, `client.POST`, etc. is fully type-safe.
 * `credentials: 'include'` ensures the httpOnly session cookie travels on
 * every request — matching the cookie-auth contract.
 */
export const client = createClient<paths>({
  baseUrl: API_BASE_URL,
  credentials: 'include',
});

export { API_BASE_URL };
export type { paths };
