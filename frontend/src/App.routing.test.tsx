/**
 * Contract test for the react-router API surface this app depends on.
 *
 * Purpose, stated plainly: this is an upgrade canary. It exercises exactly the
 * seven symbols App.tsx and the layout components import -- Routes, Route,
 * Navigate, Outlet, useLocation, useNavigate, and a Router -- so that a major
 * version bump either keeps behaving identically or fails here.
 *
 * It deliberately does NOT render App itself. App mounts four context
 * providers and ten lazily-loaded pages, several of which fetch on mount; a
 * test that rendered it would be slow, would need the whole network mocked,
 * and would fail for reasons unrelated to routing. App.tsx's own route table
 * is covered by `tsc -b` and the production build.
 *
 * The behaviours pinned are the ones whose loss would be silent rather than
 * loud: a catch-all that stops redirecting leaves a blank page on a typo'd
 * URL, and a layout Outlet that stops rendering children leaves the chrome
 * with no content.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

/** Stands in for MainLayout: chrome plus an Outlet for the routed page. */
function Layout() {
  return (
    <div>
      <span>chrome</span>
      <Outlet />
    </div>
  );
}

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="pathname">{location.pathname}</span>;
}

function NavButton({ to, label }: { to: string; label: string }) {
  const navigate = useNavigate();
  return <button onClick={() => navigate(to)}>{label}</button>;
}

function renderRoutes(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route element={<Layout />}>
          <Route
            path="/"
            element={
              <>
                <span>cockpit</span>
                <LocationProbe />
                <NavButton to="/risk" label="go to risk" />
              </>
            }
          />
          <Route
            path="/risk"
            element={
              <>
                <span>risk</span>
                <LocationProbe />
              </>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('router contract', () => {
  it('renders the index route inside the layout', () => {
    renderRoutes('/');

    expect(screen.getByText('chrome')).toBeInTheDocument();
    expect(screen.getByText('cockpit')).toBeInTheDocument();
  });

  it('renders a sibling route inside the same layout', () => {
    // Outlet nesting: the chrome must persist across routes rather than the
    // page replacing the whole tree.
    renderRoutes('/risk');

    expect(screen.getByText('chrome')).toBeInTheDocument();
    expect(screen.getByText('risk')).toBeInTheDocument();
  });

  it('redirects an unknown path to the index route', () => {
    // Without this the app renders an empty layout on any typo'd URL, which
    // looks like a broken deploy rather than a bad link.
    renderRoutes('/no-such-page');

    expect(screen.getByText('cockpit')).toBeInTheDocument();
    expect(screen.getByTestId('pathname')).toHaveTextContent('/');
  });

  it('exposes the current pathname through useLocation', () => {
    // Sidebar and MainLayout both read useLocation to mark the active nav item.
    renderRoutes('/risk');

    expect(screen.getByTestId('pathname')).toHaveTextContent('/risk');
  });

  it('navigates imperatively through useNavigate', async () => {
    // Header and Sidebar navigate this way rather than with <Link>.
    renderRoutes('/');

    await userEvent.click(screen.getByRole('button', { name: 'go to risk' }));

    expect(screen.getByText('risk')).toBeInTheDocument();
    expect(screen.getByTestId('pathname')).toHaveTextContent('/risk');
  });
});
