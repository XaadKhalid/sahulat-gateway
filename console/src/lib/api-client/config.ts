/**
 * API client configuration.
 *
 * The base URL is read from NEXT_PUBLIC_API_BASE_URL (exposed to the browser
 * by Next.js). If unset, it defaults to a *relative* path so that in
 * development the Next.js app and MSW mock layer operate same-origin — no
 * CORS configuration needed. Set an absolute URL (e.g.
 * http://localhost:8000/api/v1/admin) in production or when testing against
 * the real backend.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api/v1/admin';
