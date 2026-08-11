import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';

// --- Types ---

export interface DashboardPosition {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  assetType: 'Stock' | 'ETF' | 'Option' | 'Cash' | 'Crypto';
  quantity: number;
  avgCost: number;
  price: number;
  value: number;
  pnl: number;
  pnlPercent: number;
  weight: number;
}

interface DashboardContextType {
  // Emergency Panel
  isEmergencyOpen: boolean;
  openEmergency: () => void;
  closeEmergency: () => void;

  // Alert Modal
  isAlertModalOpen: boolean;
  alertModalSymbol: string;
  openAlertModal: (symbol?: string) => void;
  closeAlertModal: () => void;

  // Position Drawer
  isPositionDrawerOpen: boolean;
  selectedPosition: DashboardPosition | null;
  openPositionDrawer: (position: DashboardPosition) => void;
  closePositionDrawer: () => void;

  // Export Modal
  isExportModalOpen: boolean;
  openExportModal: () => void;
  closeExportModal: () => void;

  // Strategy Viewer (opens StrategyDetailDrawer or BacktestResultsModal)
  selectedStrategyId: string | null;
  viewStrategy: (id: string) => void;
  closeStrategyViewer: () => void;

  // Settings Tab Navigation
  activeSettingsTab: string;
  navigateToSettingsTab: (tab: string) => void;
}

const DashboardContext = createContext<DashboardContextType | null>(null);

export const DashboardProvider = ({ children }: { children: ReactNode }) => {
  const [isEmergencyOpen, setIsEmergencyOpen] = useState(false);
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [alertModalSymbol, setAlertModalSymbol] = useState('');
  const [isPositionDrawerOpen, setIsPositionDrawerOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<DashboardPosition | null>(null);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [activeSettingsTab, setActiveSettingsTab] = useState('profile');

  const openEmergency = useCallback(() => setIsEmergencyOpen(true), []);
  const closeEmergency = useCallback(() => setIsEmergencyOpen(false), []);

  const openAlertModal = useCallback((symbol = '') => {
    setAlertModalSymbol(symbol);
    setIsAlertModalOpen(true);
  }, []);
  const closeAlertModal = useCallback(() => setIsAlertModalOpen(false), []);

  const openPositionDrawer = useCallback((position: DashboardPosition) => {
    setSelectedPosition(position);
    setIsPositionDrawerOpen(true);
  }, []);
  const closePositionDrawer = useCallback(() => {
    setIsPositionDrawerOpen(false);
    setTimeout(() => setSelectedPosition(null), 300);
  }, []);

  const openExportModal = useCallback(() => setIsExportModalOpen(true), []);
  const closeExportModal = useCallback(() => setIsExportModalOpen(false), []);

  const viewStrategy = useCallback((id: string) => setSelectedStrategyId(id), []);
  const closeStrategyViewer = useCallback(() => setSelectedStrategyId(null), []);

  const navigateToSettingsTab = useCallback((tab: string) => setActiveSettingsTab(tab), []);

  return (
    <DashboardContext.Provider
      value={{
        isEmergencyOpen,
        openEmergency,
        closeEmergency,
        isAlertModalOpen,
        alertModalSymbol,
        openAlertModal,
        closeAlertModal,
        isPositionDrawerOpen,
        selectedPosition,
        openPositionDrawer,
        closePositionDrawer,
        isExportModalOpen,
        openExportModal,
        closeExportModal,
        selectedStrategyId,
        viewStrategy,
        closeStrategyViewer,
        activeSettingsTab,
        navigateToSettingsTab,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboard = (): DashboardContextType => {
  const ctx = useContext(DashboardContext);
  if (!ctx) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return ctx;
};
