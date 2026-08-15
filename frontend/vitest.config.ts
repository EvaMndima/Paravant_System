/**
 * Vitest configuration.
 *
 * Deliberately a separate file rather than a `test` key inside
 * `vite.config.ts`. The production build reads `vite.config.ts`, and keeping
 * test configuration out of it means no test setting can affect what ships.
 * The build config is merged in, so path aliases (`@/`) resolve identically in
 * tests and in the bundle -- a divergence there produces tests that pass
 * against modules the build never loads.
 */
import { defineConfig, mergeConfig } from 'vitest/config';

import viteConfig from './vite.config';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      // jsdom rather than happy-dom: the components under test use portals
      // (EmergencyPanel renders through createPortal) and jsdom's DOM
      // implementation is the more faithful of the two.
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      // Tailwind classes are asserted as strings, never computed, so parsing
      // CSS would cost time and buy nothing.
      css: false,
      restoreMocks: true,
      clearMocks: true,

      // Run test files sequentially. Memory, not wall time, is the binding
      // constraint: Vitest defaults to one worker per core, each with its own
      // jsdom instance, and jsdom plus React plus framer-motion plus recharts
      // is heavy enough that the workers exhausted the V8 heap. The symptom
      // was a FATAL "JavaScript heap out of memory" that killed a DIFFERENT
      // test file on each run -- 47 of 59 tests one time, 15 the next.
      //
      // It surfaced when the react-router 7 upgrade added module weight, but
      // the cause is the worker count, not the router. A non-deterministic
      // OOM in CI is indistinguishable from a real failure and would train
      // everyone to hit re-run, so this is fixed rather than tuned around.
      //
      // The whole suite runs in well under a minute sequentially. Revisit if
      // that stops being true; raising the heap with
      // NODE_OPTIONS=--max-old-space-size would be the next lever.
      fileParallelism: false,
    },
  }),
);
