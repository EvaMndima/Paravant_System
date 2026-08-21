/**
 * Global test setup, loaded before every test file.
 *
 * Three concerns, all of which cause cross-test contamination if left out.
 */
import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, vi } from 'vitest';

// React Testing Library does not unmount between tests on its own outside of
// globals mode. Without this, a component rendered in one test is still in the
// document during the next, and queries match the wrong element.
afterEach(() => {
  cleanup();
});

beforeAll(() => {
  // jsdom implements neither of these, and both are called during render by
  // code paths under test: Recharts' ResponsiveContainer observes element
  // size, and several components read a media query to decide layout.
  // Without stubs the component throws before any assertion runs.
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );

  if (!window.matchMedia) {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }));
  }
});
