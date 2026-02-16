
import React, { createContext, useContext, useState, ReactNode } from 'react';

// Unified types for state management
export interface PositionDetails {
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
  // Alert Modal
  isAlertModalOpen: boolean;
  alertSymbol: string;
  alertPrice?: number;
  openAlertModal: (symbol?: string, currentPrice?: number) => void;
  closeAlertModal: () => void;

  // Position Drawer
  isPositionDrawerOpen: boolean;
  selectedPosition: PositionDetails | null;
  openPositionDrawer: (position: PositionDetails) => void;
  closePositionDrawer: () => void;

  // Emergency Panel
  isEmergencyPanelOpen: boolean;
  openEmergencyPanel: () => void;
  closeEmergencyPanel: () => void;

  // Strategy Detail Navigation
  selectedStrategyId: string | null;
  viewStrategy: (id: string) => void;
  clearSelectedStrategy: () => void;

  // Keyboard Shortcuts Modal
  isShortcutsOpen: boolean;
  openShortcuts: () => void;
  closeShortcuts: () => void;
  toggleShortcuts: () => void;

  // Settings Navigation
  activeSettingsTab: string;
  navigateToSettingsTab: (tab: string) => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Alert Modal State
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [alertSymbol, setAlertSymbol] = useState('');
  const [alertPrice, setAlertPrice] = useState<number | undefined>(undefined);

  // Position Drawer State
  const [isPositionDrawerOpen, setIsPositionDrawerOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<PositionDetails | null>(null);

  // Emergency Panel State
  const [isEmergencyPanelOpen, setIsEmergencyPanelOpen] = useState(false);

  // Strategy Detail State
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);

  // Shortcuts Modal State
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);

  // Settings Tab State
  const [activeSettingsTab, setActiveSettingsTab] = useState('profile');

  // Handlers
  const openAlertModal = (symbol: string = '', currentPrice?: number) => {
    setAlertSymbol(symbol);
    setAlertPrice(currentPrice);
    setIsAlertModalOpen(true);
  };
  const closeAlertModal = () => setIsAlertModalOpen(false);

  const openPositionDrawer = (position: PositionDetails) => {
    setSelectedPosition(position);
    setIsPositionDrawerOpen(true);
  };
  const closePositionDrawer = () => setIsPositionDrawerOpen(false);

  const openEmergencyPanel = () => setIsEmergencyPanelOpen(true);
  const closeEmergencyPanel = () => setIsEmergencyPanelOpen(false);

  const viewStrategy = (id: string) => {
    setSelectedStrategyId(id);
  };
  const clearSelectedStrategy = () => {
    setSelectedStrategyId(null);
  };

  const openShortcuts = () => setIsShortcutsOpen(true);
  const closeShortcuts = () => setIsShortcutsOpen(false);
  const toggleShortcuts = () => setIsShortcutsOpen(prev => !prev);

  const navigateToSettingsTab = (tab: string) => {
    setActiveSettingsTab(tab);
  };

  return (
    <DashboardContext.Provider value={{
      isAlertModalOpen, alertSymbol, alertPrice, openAlertModal, closeAlertModal,
      isPositionDrawerOpen, selectedPosition, openPositionDrawer, closePositionDrawer,
      isEmergencyPanelOpen, openEmergencyPanel, closeEmergencyPanel,
      selectedStrategyId, viewStrategy, clearSelectedStrategy,
      isShortcutsOpen, openShortcuts, closeShortcuts, toggleShortcuts,
      activeSettingsTab, navigateToSettingsTab
    }}>
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboard = () => {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
};
