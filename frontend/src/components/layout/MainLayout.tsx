import React from 'react';
import { useLocation } from 'react-router-dom';
import { Sidebar, SidebarProvider } from './Sidebar';
import { Header } from './Header';
import { ConnectionBanner } from '@/components/ui/ConnectionBanner';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { KeyboardShortcutsHelp } from '@/components/ui/KeyboardShortcutsHelp';
import { useEventStream } from '@/hooks';
import { useGlobalShortcuts } from '@/hooks/useGlobalShortcuts';

interface MainLayoutProps {
  children: React.ReactNode;
}

// Map routes to page titles
const routeTitles: Record<string, string> = {
  '/': 'Cockpit',
  '/portfolio': 'Portfolio',
  '/strategies': 'Strategies',
  '/risk': 'Risk',
  '/orders': 'Orders',
  '/alerts': 'Alerts',
  '/accounts': 'Accounts',
  '/settings': 'Settings',
  '/backtest': 'Backtest',
};

const MainLayoutInner: React.FC<MainLayoutProps> = ({ children }) => {
  const location = useLocation();
  const pageTitle = routeTitles[location.pathname] || 'Dashboard';

  // Establish SSE connection for real-time updates
  useEventStream();

  // Global keyboard shortcuts (G+letter nav, Ctrl+K kill switch, Ctrl+/ help)
  const { showHelp, setShowHelp, shortcuts } = useGlobalShortcuts();

  return (
    <SidebarProvider>
      {/* Connection status banner — appears at very top of viewport */}
      <ConnectionBanner />

      <div className="flex min-h-screen bg-paper-100 dark:bg-obsidian-900">
        <Sidebar />

        <div className="flex-1 flex flex-col min-w-0">
          <Header title={pageTitle} />

          <main className="flex-1 overflow-x-hidden">
            <div className="max-w-7xl mx-auto px-4 md:px-8 py-8">
              <ErrorBoundary>
                {children}
              </ErrorBoundary>
            </div>
          </main>
        </div>
      </div>

      {/* Keyboard shortcuts help overlay */}
      <KeyboardShortcutsHelp
        isOpen={showHelp}
        shortcuts={shortcuts}
        onClose={() => setShowHelp(false)}
      />
    </SidebarProvider>
  );
};

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  // Top-level ErrorBoundary catches layout crashes
  return (
    <ErrorBoundary>
      <MainLayoutInner>{children}</MainLayoutInner>
    </ErrorBoundary>
  );
};
