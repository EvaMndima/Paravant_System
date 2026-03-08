import React, { createContext, useContext, useState, useCallback } from 'react';
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
}

const DashboardContext = createContext<DashboardContextType | null>(null);

export const DashboardProvider = ({ children }: { children: ReactNode }) => {
  // Emergency Panel state
  const [isEmergencyOpen, setIsEmergencyOpen] = useState(false);

  // Alert Modal state
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [alertModalSymbol, setAlertModalSymbol] = useState('');

  // Position Drawer state
  const [isPositionDrawerOpen, setIsPositionDrawerOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<DashboardPosition | null>(null);

  // Export Modal state
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);

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
    // Delay clearing position so exit animation completes
    setTimeout(() => setSelectedPosition(null), 300);
  }, []);

  const openExportModal = useCallback(() => setIsExportModalOpen(true), []);
  const closeExportModal = useCallback(() => setIsExportModalOpen(false), []);

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
