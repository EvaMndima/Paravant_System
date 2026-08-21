import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ToastProvider } from '@/contexts/ToastContext'
import { DashboardProvider } from '@/contexts/DashboardContext'
import { SidebarProvider } from '@/components/layout/Sidebar'
import { MainLayout } from '@/components/layout/MainLayout'
import { LoadingState } from '@/components/ui/LoadingState'

// Lazy-loaded pages for code splitting
const CockpitPage         = lazy(() => import('@/pages/CockpitPage'))
const SystemPage          = lazy(() => import('@/pages/SystemPage'))
const StrategiesPage      = lazy(() => import('@/pages/StrategiesPage'))
const PortfolioPage       = lazy(() => import('@/pages/PortfolioPage'))
const RegimePage          = lazy(() => import('@/pages/RegimePage'))
const RiskPage            = lazy(() => import('@/pages/RiskPage'))
const AlertsPage          = lazy(() => import('@/pages/AlertsPage'))
const TradeHistoryPage    = lazy(() => import('@/pages/TradeHistoryPage'))
const SettingsPage        = lazy(() => import('@/pages/SettingsPage'))
const BacktestResultsPage = lazy(() => import('@/pages/BacktestResultsPage'))

// Component galleries used during design work, not part of the product.
//
// Vite statically replaces `import.meta.env.DEV` with `false` when building, so
// Rollup eliminates this branch entirely and never emits the chunks. Previously
// these were unconditional routes and shipped ~155 kB of gallery into the
// production bundle -- Dev2Page alone was 93.5 kB.
const devRoutes = import.meta.env.DEV
  ? [
      { path: '/dev',  Component: lazy(() => import('@/pages/DevPage')) },
      { path: '/dev2', Component: lazy(() => import('@/pages/Dev2Page')) },
      { path: '/dev3', Component: lazy(() => import('@/pages/Dev3Page')) },
    ]
  : []

function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        {/*
          The `future={{ v7_startTransition, v7_relativeSplatPath }}` opt-in was
          removed when react-router-dom went 6.30 -> 7.18 (DEC-2026-08-16-001).
          Those flags no longer exist as props because both behaviours are the
          default in v7, so deleting them changes nothing at runtime -- having
          already opted in is precisely what made the major bump a non-event.
        */}
        <BrowserRouter>
          <DashboardProvider>
            <SidebarProvider>
              <Suspense fallback={<LoadingState className="min-h-screen" />}>
                <Routes>
                  {/* Main layout with sidebar + header */}
                  <Route element={<MainLayout />}>
                    <Route path="/"              element={<CockpitPage />} />
                    <Route path="/system"        element={<SystemPage />} />
                    <Route path="/strategies"    element={<StrategiesPage />} />
                    <Route path="/portfolio"     element={<PortfolioPage />} />
                    <Route path="/regime"        element={<RegimePage />} />
                    <Route path="/risk"          element={<RiskPage />} />
                    <Route path="/alerts"        element={<AlertsPage />} />
                    <Route path="/trade-history" element={<TradeHistoryPage />} />
                    <Route path="/settings"      element={<SettingsPage />} />
                    <Route path="/backtests"     element={<BacktestResultsPage />} />
                  </Route>

                  {/* Component galleries, development builds only */}
                  {devRoutes.map(({ path, Component }) => (
                    <Route key={path} path={path} element={<Component />} />
                  ))}

                  {/* Catch-all redirect */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Suspense>
            </SidebarProvider>
          </DashboardProvider>
        </BrowserRouter>
      </ToastProvider>
    </ThemeProvider>
  )
}

export default App
