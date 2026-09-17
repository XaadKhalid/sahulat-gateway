import { setupServer } from 'msw/node';
import { handlers } from './handlers';

/**
 * Node-side MSW server (for Vitest tests).
 *
 * Usage in test files:
 *   import { server } from '@/lib/mocks/server';
 *   import { beforeAll, afterEach, afterAll } from 'vitest';
 *   beforeAll(() => server.listen());
 *   afterEach(() => server.resetHandlers());
 *   afterAll(() => server.close());
 *
 * Use `server.use(...)` inside individual tests to override handlers for
 * that test only.
 */
export const server = setupServer(...handlers);
