
export type ThemeMode = 'light' | 'dark' | 'system';
export type AppTheme = 'ocean' | 'sapphire' | 'emerald' | 'onyx';

export interface ThemeContextType {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  appTheme: AppTheme;
  setAppTheme: (theme: AppTheme) => void;
  compactMode: boolean;
  setCompactMode: (enabled: boolean) => void;
  reducedMotion: boolean;
  setReducedMotion: (enabled: boolean) => void;
}

export interface MetricCardProps {
  title: string;
  value: number;
  change?: number;
  prefix?: string;
  suffix?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export interface UserProfile {
  id: string;
  name: string;
  role: 'admin' | 'viewer' | 'trader';
  preferences: {
    theme: ThemeMode;
    currency: string;
    notifications: boolean;
  };
}

export interface PortfolioPosition {
  symbol: string;
  quantity: number;
  avgPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
}
