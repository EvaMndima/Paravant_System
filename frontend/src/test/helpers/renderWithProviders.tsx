import React from 'react';
import { render } from '@testing-library/react';
import type { RenderResult } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ToastProvider } from '@/contexts/ToastContext';

interface RenderOptions {
  /** Initial route for MemoryRouter (default: '/') */
  route?: string;
}

/**
 * Render a React element with all providers required by the app:
 * QueryClient + ThemeProvider + ToastProvider + MemoryRouter.
 * Used in all page smoke tests to avoid boilerplate.
 */
export function renderWithProviders(
  ui: React.ReactElement,
  { route = '/' }: RenderOptions = {}
): RenderResult {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,          // Fail fast in tests — no retry noise
        staleTime: Infinity,   // Data from mocks should not be considered stale
      },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <ToastProvider>
          <MemoryRouter initialEntries={[route]}>
            {ui}
          </MemoryRouter>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
