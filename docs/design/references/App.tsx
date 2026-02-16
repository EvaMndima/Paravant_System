
import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import { ToastProvider } from './contexts/ToastContext';
import { SidebarProvider, Sidebar } from './components/layout/Sidebar';
import { DashboardProvider, useDashboard } from './contexts/DashboardContext';
import { Header } from './components/layout/Header';
import { motion, AnimatePresence } from 'framer-motion';

// Pages
import { CockpitPage } from './components/pages/CockpitPage';
import { StrategiesPage } from './components/pages/StrategiesPage';
import { PortfolioPage } from './components/pages/PortfolioPage';
import { RegimePage } from './components/pages/RegimePage';
import { RiskPage } from './components/pages/RiskPage';
import { TradeHistoryPage } from './components/pages/TradeHistoryPage';
import { SettingsPage } from './components/pages/SettingsPage';
import { StrategyDetailPage } from './components/pages/StrategyDetailPage';
import { SystemPage } from './components/pages/SystemPage';
import { AlertsPage } from './components/pages/AlertsPage';
import { NotificationsPage } from './components/pages/NotificationsPage';

// Global Modals
import { AlertModal } from './components/dashboard/AlertModal';
import { PositionDrawer } from './components/dashboard/PositionDrawer';
import { EmergencyPanel } from './components/dashboard/EmergencyPanel';
import { KeyboardShortcuts } from './components/ui/KeyboardShortcuts';

// Hooks
import { useGlobalShortcuts } from './hooks/useGlobalShortcuts';

const AppContent: React.FC = () => {
  const [currentView, setCurrentView] = useState('Cockpit');
  
  // Access global state
  const {
    isAlertModalOpen, alertSymbol, alertPrice, closeAlertModal,
    isPositionDrawerOpen, selectedPosition, closePositionDrawer,
    isEmergencyPanelOpen, openEmergencyPanel, closeEmergencyPanel,
    openAlertModal, selectedStrategyId,
    isShortcutsOpen, closeShortcuts
  } = useDashboard();

  // Initialize Global Shortcuts Hook
  useGlobalShortcuts(setCurrentView);

  // Watch for strategy selection to switch view
  useEffect(() => {
    if (selectedStrategyId) {
      setCurrentView('Strategy Detail');
    } else if (currentView === 'Strategy Detail' && !selectedStrategyId) {
      setCurrentView('Strategies');
    }
  }, [selectedStrategyId, currentView]);

  const renderView = () => {
    switch(currentView) {
      case 'Cockpit': return <CockpitPage />;
      case 'Strategies': return <StrategiesPage />;
      case 'Portfolio': return <PortfolioPage />;
      case 'Regime': return <RegimePage />;
      case 'Risk': return <RiskPage />;
      case 'Alerts': return <AlertsPage />;
      case 'Trade History': return <TradeHistoryPage />;
      case 'System': return <SystemPage />;
      case 'Settings': return <SettingsPage />;
      case 'Strategy Detail': return <StrategyDetailPage />;
      case 'Notifications': return <NotificationsPage />;
      default: return <CockpitPage />;
    }
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen bg-paper-100 dark:bg-obsidian-400 text-obsidian-400 dark:text-paper-100 transition-colors duration-300 font-sans selection:bg-turquoise-mist/30">
        <Sidebar currentView={currentView} onNavigate={setCurrentView} />
        <main className="flex-1 relative flex flex-col min-w-0 overflow-hidden">
          <Header title={currentView} onNavigate={setCurrentView} />
          <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-8 lg:p-10 custom-scrollbar">
            <div className="max-w-7xl mx-auto w-full">
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentView}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.2 }}
                >
                  {renderView()}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </main>
      </div>

      {/* Global Modals Layer */}
      <AlertModal
        isOpen={isAlertModalOpen}
        onClose={closeAlertModal}
        symbol={alertSymbol}
        currentPrice={alertPrice}
      />

      <PositionDrawer
        isOpen={isPositionDrawerOpen}
        onClose={closePositionDrawer}
        position={selectedPosition}
        onAlert={(sym) => {
          openAlertModal(sym);
        }}
      />

      <EmergencyPanel 
        isOpen={isEmergencyPanelOpen} 
        onClose={closeEmergencyPanel} 
      />

      <KeyboardShortcuts 
        isOpen={isShortcutsOpen} 
        onClose={closeShortcuts} 
      />

    </SidebarProvider>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <ToastProvider>
        <DashboardProvider>
          <AppContent />
        </DashboardProvider>
      </ToastProvider>
    </ThemeProvider>
  );
};

export default App;
