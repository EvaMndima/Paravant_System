import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './contexts/ThemeContext';
import { ToastProvider } from './contexts/ToastContext';
import { MainLayout } from './components/layout/MainLayout';
import { ErrorBoundary } from './components/ui/ErrorBoundary';
import { PageSkeleton } from './components/ui/PageSkeletons';

// Lazy-load all pages — each page becomes a separate chunk
const CockpitPage = lazy(() =>
  import('./pages/dashboard/Cockpit').then((m) => ({ default: m.CockpitPage })),
);
const PortfolioPage = lazy(() =>
  import('./pages/dashboard/Portfolio').then((m) => ({ default: m.PortfolioPage })),
);
const StrategiesPage = lazy(() =>
  import('./pages/dashboard/Strategies').then((m) => ({ default: m.StrategiesPage })),
);
const StrategyDetailPage = lazy(() =>
  import('./pages/dashboard/StrategyDetail').then((m) => ({ default: m.StrategyDetailPage })),
);
const RiskPage = lazy(() =>
  import('./pages/dashboard/Risk').then((m) => ({ default: m.RiskPage })),
);
const OrdersPage = lazy(() =>
  import('./pages/dashboard/Orders').then((m) => ({ default: m.OrdersPage })),
);
const AlertsPage = lazy(() =>
  import('./pages/dashboard/Alerts').then((m) => ({ default: m.AlertsPage })),
);
const AccountsPage = lazy(() =>
  import('./pages/dashboard/Accounts').then((m) => ({ default: m.AccountsPage })),
);
const SettingsPage = lazy(() =>
  import('./pages/dashboard/Settings').then((m) => ({ default: m.SettingsPage })),
);
const BacktestPage = lazy(() =>
  import('./pages/dashboard/Backtest').then((m) => ({ default: m.BacktestPage })),
);

// QueryClient configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <ToastProvider>
            <Router>
              <MainLayout>
                <Suspense fallback={<PageSkeleton />}>
                  <Routes>
                    <Route path="/" element={<CockpitPage />} />
                    <Route path="/portfolio" element={<PortfolioPage />} />
                    <Route path="/strategies" element={<StrategiesPage />} />
                    <Route path="/strategies/:id" element={<StrategyDetailPage />} />
                    <Route path="/risk" element={<RiskPage />} />
                    <Route path="/orders" element={<OrdersPage />} />
                    <Route path="/alerts" element={<AlertsPage />} />
                    <Route path="/accounts" element={<AccountsPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/backtest" element={<BacktestPage />} />
                  </Routes>
                </Suspense>
              </MainLayout>
            </Router>
          </ToastProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
