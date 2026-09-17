import { authHandlers } from './handlers/auth';
import { userHandlers } from './handlers/users';
import { tenantHandlers } from './handlers/tenants';
import { documentHandlers } from './handlers/documents';
import { manifestHandlers } from './handlers/manifest';
import { publishHandlers } from './handlers/publish';
import { sandboxHandlers } from './handlers/sandbox';

/**
 * All MSW request handlers for the admin API.
 *
 * Each sub-array corresponds to a contract resource. New endpoints are added
 * by creating a handler file under handlers/ and appending it here.
 */
export const handlers = [
  ...authHandlers,
  ...userHandlers,
  ...tenantHandlers,
  ...documentHandlers,
  ...manifestHandlers,
  ...publishHandlers,
  ...sandboxHandlers,
];
