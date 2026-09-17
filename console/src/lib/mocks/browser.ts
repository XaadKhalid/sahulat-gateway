import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

/**
 * Browser-side MSW worker.
 *
 * Start this in the browser during development so that API requests made by
 * console/ are intercepted and served from mock handlers — no real backend
 * needed.
 *
 * Call `worker.start()` before the app renders (e.g. in a client component
 * loaded once at the root layout, gated on process.env.NODE_ENV === 'development').
 */
export const worker = setupWorker(...handlers);
