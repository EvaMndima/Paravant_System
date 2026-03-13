import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { ToastProvider } from '@/contexts/ToastContext'
import { SidebarProvider } from '@/components/layout/Sidebar'
import { MainLayout } from '@/components/layout/MainLayout'
import { LoadingState } from '@/components/ui/LoadingState'

// Lazy-loaded pages for code splitting
const CockpitPage = lazy(() => import('@/pages/CockpitPage'))
const SystemPage = lazy(() => import('@/pages/SystemPage'))
const StrategiesPage = lazy(() => import('@/pages/StrategiesPage'))
const PortfolioPage = lazy(() => import('@/pages/PortfolioPage'))
const RegimePage = lazy(() => import('@/pages/RegimePage'))
const RiskPage = lazy(() => import('@/pages/RiskPage'))
const AlertsPage = lazy(() => import('@/pages/AlertsPage'))
const TradeHistoryPage = lazy(() => import('@/pages/TradeHistoryPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))
const DevPage = lazy(() => import('@/pages/DevPage'))
const Dev2Page = lazy(() => import('@/pages/Dev2Page'))
const Dev3Page = lazy(() => import('@/pages/Dev3Page'))

function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <SidebarProvider>
            <Suspense fallback={<LoadingState className="min-h-screen" />}>
              <Routes>
                {/* Main layout with sidebar + header */}
                <Route element={<MainLayout />}>
                  <Route path="/" element={<CockpitPage />} />
                  <Route path="/system" element={<SystemPage />} />
                  <Route path="/strategies" element={<StrategiesPage />} />
                  <Route path="/portfolio" element={<PortfolioPage />} />
                  <Route path="/regime" element={<RegimePage />} />
                  <Route path="/risk" element={<RiskPage />} />
                  <Route path="/alerts" element={<AlertsPage />} />
                  <Route path="/trade-history" element={<TradeHistoryPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Route>

                {/* Dev pages outside main layout */}
                <Route path="/dev" element={<DevPage />} />
                <Route path="/dev2" element={<Dev2Page />} />
                <Route path="/dev3" element={<Dev3Page />} />

                {/* Catch-all redirect */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </SidebarProvider>
        </BrowserRouter>
      </ToastProvider>
    </ThemeProvider>
  )
}

export default App
