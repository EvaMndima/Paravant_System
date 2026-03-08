import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Bell, Download, AlertTriangle } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { DashboardProvider, useDashboard } from '@/contexts/DashboardContext';
import { cn } from '@/lib/utils';
import { fadeInUp, staggerContainer } from '@/lib/animations';
import type { AppTheme, ThemeMode } from '@/types';

// --- Dashboard Components ---
import { MarketTicker } from '@/components/dashboard/MarketTicker';
import type { MarketItem } from '@/components/dashboard/MarketTicker';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import type { ActivityItem } from '@/components/dashboard/ActivityFeed';
import { Watchlist } from '@/components/dashboard/Watchlist';
import type { WatchlistItem } from '@/components/dashboard/Watchlist';
import { PositionsTable } from '@/components/dashboard/PositionsTable';
import type { Position } from '@/components/dashboard/PositionsTable';
import { MarketRegimePanel } from '@/components/dashboard/MarketRegimePanel';
import type { MarketRegimeData } from '@/components/dashboard/MarketRegimePanel';
import { StrategyCard } from '@/components/dashboard/StrategyCard';
import { StrategyGrid } from '@/components/dashboard/StrategyGrid';
import type { StrategyCardProps } from '@/components/dashboard/StrategyCard';
import { EmergencyPanel } from '@/components/dashboard/EmergencyPanel';
import { AlertModal } from '@/components/dashboard/AlertModal';
import { PositionDrawer } from '@/components/dashboard/PositionDrawer';
import type { DrawerPosition } from '@/components/dashboard/PositionDrawer';
import { ExportModal } from '@/components/dashboard/ExportModal';
import type { ExportConfig } from '@/components/dashboard/ExportModal';
import { StrategyConfigModal } from '@/components/dashboard/StrategyConfigModal';
import { BacktestResultsModal } from '@/components/dashboard/BacktestResultsModal';
import { StrategyDetailDrawer } from '@/components/dashboard/StrategyDetailDrawer';
import { RiskGauge } from '@/components/dashboard/RiskGauge';
import { DrawdownChart } from '@/components/dashboard/DrawdownChart';
import { TradeDetailModal } from '@/components/dashboard/TradeDetailModal';
import { RegimeTagSelector } from '@/components/dashboard/RegimeTagSelector';
import type { MarketRegime } from '@/components/dashboard/RegimeTagSelector';
import { SystemStatusBar } from '@/components/dashboard/SystemStatusBar';

// --- UI Primitives ---
import { Button } from '@/components/ui/Button';
import { GlassCard } from '@/components/ui/GlassCard';
import { MetricCard } from '@/components/ui/MetricCard';
import { SparklineChart } from '@/components/charts/SparklineChart';

// ── Theme metadata ───────────────────────────────────────────
const THEMES: { id: AppTheme; label: string }[] = [
  { id: 'ocean', label: 'Ocean' },
  { id: 'sapphire', label: 'Sapphire' },
  { id: 'emerald', label: 'Emerald' },
  { id: 'onyx', label: 'Onyx' },
];

const MODES: { id: ThemeMode; label: string }[] = [
  { id: 'light', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'system', label: 'System' },
];

// ── Mock Data ────────────────────────────────────────────────

const TICKER_ITEMS: MarketItem[] = [
  { symbol: 'BTC/USDT',  value: 67763.74, change: 2381.20,  changePercent: 3.64 },
  { symbol: 'ETH/USDT',  value: 3512.40,  change: 88.30,    changePercent: 2.58 },
  { symbol: 'BNB/USDT',  value: 594.20,   change: -6.80,    changePercent: -1.13 },
  { symbol: 'SOL/USDT',  value: 142.85,   change: 5.60,     changePercent: 4.08 },
  { symbol: 'ADA/USDT',  value: 0.4812,   change: 0.0120,   changePercent: 2.56 },
  { symbol: 'AVAX/USDT', value: 36.24,    change: -0.82,    changePercent: -2.21 },
  { symbol: 'DOT/USDT',  value: 7.18,     change: 0.31,     changePercent: 4.50 },
  { symbol: 'LINK/USDT', value: 14.62,    change: 0.48,     changePercent: 3.39 },
];

const ACTIVITY_ITEMS: ActivityItem[] = [
  {
    id: 'a1', type: 'trade', title: 'BUY BTCUSDT executed',
    description: 'Momentum_MACD strategy — market order filled at $67,420',
    timestamp: new Date(Date.now() - 2 * 60 * 1000),
    metadata: { qty: '0.5', price: '$67,420', strategy: 'Momentum_MACD' },
  },
  {
    id: 'a2', type: 'alert', title: 'Risk limit approaching',
    description: 'Daily drawdown at 4.2% — limit is 5%. Monitor closely.',
    timestamp: new Date(Date.now() - 8 * 60 * 1000),
  },
  {
    id: 'a3', type: 'agent', title: 'Simple_MA strategy paused',
    description: 'Curator paused Simple_MA: low signal confidence in current regime.',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    metadata: { reason: 'Low confidence', regime: 'Ranging' },
  },
  {
    id: 'a4', type: 'trade', title: 'SELL ETHUSDT executed',
    description: 'Scalper_RSI strategy — position closed at $3,510',
    timestamp: new Date(Date.now() - 28 * 60 * 1000),
    metadata: { qty: '2.0', pnl: '+$88.30' },
  },
  {
    id: 'a5', type: 'deposit', title: 'Capital deposit confirmed',
    description: '$50,000 USDT added to portfolio.',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
  },
  {
    id: 'a6', type: 'agent', title: 'Donchian_BB resumed',
    description: 'Curator resumed Donchian_BB: trend regime detected.',
    timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000),
  },
];

const WATCHLIST_ITEMS: WatchlistItem[] = [
  { id: 'w1', symbol: 'BTC',  name: 'Bitcoin',   price: 67763.74, change: 2381.20, changePercent: 3.64 },
  { id: 'w2', symbol: 'ETH',  name: 'Ethereum',  price: 3512.40,  change: 88.30,   changePercent: 2.58 },
  { id: 'w3', symbol: 'BNB',  name: 'BNB',       price: 594.20,   change: -6.80,   changePercent: -1.13 },
  { id: 'w4', symbol: 'SOL',  name: 'Solana',    price: 142.85,   change: 5.60,    changePercent: 4.08 },
  { id: 'w5', symbol: 'AVAX', name: 'Avalanche', price: 36.24,    change: -0.82,   changePercent: -2.21 },
];

const POSITIONS_DATA: Position[] = [
  { id: 'p1', symbol: 'BTC',  name: 'Bitcoin',   quantity: 2.5,  avgPrice: 64200, currentPrice: 67763, pl: 8907.50,  plPercent: 5.55,  weight: 35.2, assetType: 'Crypto' },
  { id: 'p2', symbol: 'ETH',  name: 'Ethereum',  quantity: 12.0, avgPrice: 3280,  currentPrice: 3512,  pl: 2784.00,  plPercent: 7.07,  weight: 21.8, assetType: 'Crypto' },
  { id: 'p3', symbol: 'BNB',  name: 'BNB',       quantity: 50.0, avgPrice: 620,   currentPrice: 594,   pl: -1300.00, plPercent: -4.19, weight: 15.4, assetType: 'Crypto' },
  { id: 'p4', symbol: 'SOL',  name: 'Solana',    quantity: 200,  avgPrice: 128,   currentPrice: 142,   pl: 2800.00,  plPercent: 10.94, weight: 14.8, assetType: 'Crypto' },
  { id: 'p5', symbol: 'AVAX', name: 'Avalanche', quantity: 300,  avgPrice: 38.50, currentPrice: 36.24, pl: -678.00,  plPercent: -5.87, weight: 5.6,  assetType: 'Crypto' },
];

const REGIME_DATA: MarketRegimeData = {
  type: 'TRENDING BULLISH',
  confidence: 78,
  duration: 'Active for 3d 14h — since Mar 04, 2026',
  indicators: {
    vix: { value: 18.2, label: 'Low Fear', status: 'good' },
    breadth: { value: '74%', label: 'Advancing', status: 'good' },
    trend: { value: 'Strong', label: 'ADX > 25', status: 'good' },
    correlation: { value: 0.62, label: 'Moderate', status: 'neutral' },
    putCall: { value: 0.81, label: 'Bullish Bias', status: 'good' },
  },
  commentary: 'Market breadth remains strong with 74% of assets trending above 50-day moving averages. Low volatility environment favours momentum strategies. Maintain current allocation bias toward trend-following.',
};

const STRATEGIES: StrategyCardProps[] = [
  {
    id: 's1', name: 'Simple_MA', type: 'momentum', status: 'active',
    performance: { pnl: 4152.00, winRate: 61.2, sharpe: 1.42 },
    lastSignal: { action: 'buy', symbol: 'BTCUSDT', time: '10:42 AM' },
  },
  {
    id: 's2', name: 'Donchian_BB', type: 'mean-reversion', status: 'active',
    performance: { pnl: 2890.50, winRate: 54.8, sharpe: 1.18 },
    lastSignal: { action: 'sell', symbol: 'ETHUSDT', time: '09:15 AM' },
  },
  {
    id: 's3', name: 'Scalper_RSI', type: 'arbitrage', status: 'paused',
    performance: { pnl: -320.00, winRate: 48.3, sharpe: 0.72 },
  },
  {
    id: 's4', name: 'Conservative_EMA', type: 'macro', status: 'active',
    performance: { pnl: 1640.00, winRate: 67.5, sharpe: 2.10 },
    lastSignal: { action: 'hold', symbol: 'BNBUSDT', time: '08:30 AM' },
  },
  {
    id: 's5', name: 'Momentum_MACD', type: 'momentum', status: 'training',
    performance: { pnl: 0, winRate: 0, sharpe: 0 },
  },
  {
    id: 's6', name: 'BreakoutRetest', type: 'ml-signal', status: 'error',
    performance: { pnl: -180.00, winRate: 42.1, sharpe: 0.38 },
    lastSignal: { action: 'buy', symbol: 'SOLUSDT', time: 'Yesterday' },
  },
];

const SPARKLINE_UP = [42, 45, 43, 48, 52, 49, 55, 58, 54, 60, 63, 59, 65, 68, 64, 70, 72, 68, 75, 78];
const SPARKLINE_DOWN = [80, 76, 74, 70, 72, 68, 65, 61, 63, 58, 55, 57, 52, 49, 51, 47, 44, 46, 41, 38];

// ── Inner content (needs DashboardContext) ───────────────────

function Dev2Content() {
  const { mode, setMode, appTheme, setAppTheme } = useTheme();

  // Panel/modal state (via DashboardContext)
  const {
    isEmergencyOpen, openEmergency, closeEmergency,
    isAlertModalOpen, alertModalSymbol, openAlertModal, closeAlertModal,
    isPositionDrawerOpen, selectedPosition, openPositionDrawer, closePositionDrawer,
    isExportModalOpen, openExportModal, closeExportModal,
  } = useDashboard();

  const [drawerPosition, setDrawerPosition] = useState<DrawerPosition | null>(null);

  // New component overlay state
  const [isStrategyConfigOpen, setIsStrategyConfigOpen] = useState(false);
  const [isBacktestOpen, setIsBacktestOpen] = useState(false);
  const [isStrategyDetailOpen, setIsStrategyDetailOpen] = useState(false);
  const [isTradeDetailOpen, setIsTradeDetailOpen] = useState(false);
  const [currentRegime, setCurrentRegime] = useState<MarketRegime>('trending_up');

  const handlePositionClick = (pos: Position) => {
    const p: DrawerPosition = {
      id: pos.id,
      symbol: pos.symbol,
      name: pos.name,
      sector: pos.assetType ?? 'Crypto',
      assetType: (pos.assetType as DrawerPosition['assetType']) ?? 'Crypto',
      quantity: pos.quantity,
      avgCost: pos.avgPrice,
      price: pos.currentPrice,
      value: pos.currentPrice * pos.quantity,
      pnl: pos.pl,
      pnlPercent: pos.plPercent,
      weight: pos.weight,
    };
    setDrawerPosition(p);
    openPositionDrawer(p);
  };

  const SectionTitle = ({ children }: { children: React.ReactNode }) => (
    <h2 className="font-sans font-semibold text-xs uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-4">
      {children}
    </h2>
  );

  return (
    <div className="min-h-screen bg-paper-100 dark:bg-obsidian-400 pb-16 transition-colors duration-300">

      {/* MarketTicker — full width, top of page */}
      <MarketTicker items={TICKER_ITEMS} speed="normal" />

      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="max-w-6xl mx-auto px-6 space-y-10 pt-8"
      >

        {/* ── Header ────────────────────────────────────────── */}
        <motion.div variants={fadeInUp}>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-turquoise mb-2">
            Phase 5 — Dashboard Component Gallery
          </p>
          <h1 className="font-display text-5xl text-deep-teal-800 dark:text-paper-100 mb-2" style={{ fontVariant: 'small-caps' }}>
            Paravant
          </h1>
          <p className="font-sans text-sm text-obsidian-400/60 dark:text-paper-100/60">
            11 dashboard components — verify all visually before Session 7 page builds
          </p>
        </motion.div>

        {/* ── Theme Controls ────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-4">
          <SectionTitle>Theme Controls</SectionTitle>
          <div className="flex flex-wrap gap-6">
            <div className="space-y-2">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 uppercase tracking-wider">Mode</p>
              <div className="flex gap-2">
                {MODES.map(({ id, label }) => (
                  <button key={id} onClick={() => setMode(id)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-sans font-medium transition-all',
                      mode === id
                        ? 'bg-turquoise text-white'
                        : 'bg-deep-teal-800/10 dark:bg-white/10 text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/20 dark:hover:bg-white/20'
                    )}
                  >{label}</button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 uppercase tracking-wider">Palette</p>
              <div className="flex gap-2">
                {THEMES.map(({ id, label }) => (
                  <button key={id} onClick={() => setAppTheme(id)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-sans font-medium transition-all',
                      appTheme === id
                        ? 'bg-turquoise text-white'
                        : 'bg-deep-teal-800/10 dark:bg-white/10 text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/20 dark:hover:bg-white/20'
                    )}
                  >{label}</button>
                ))}
              </div>
            </div>
          </div>
        </motion.section>

        {/* ── MetricCard overflow fix demo ──────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>MetricCard — Adaptive Font Sizing (overflow fix)</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-4">
            Values &gt; 1M now auto-scale to text-xl / text-2xl so nothing clips or overflows.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard
              title="Net Liquidity"
              value={994272.52}
              format="currency"
              change={1.24}
              changeLabel="24h"
              sparkline={<SparklineChart data={SPARKLINE_UP} color="turquoise" />}
            />
            <MetricCard
              title="Total AUM"
              value={1234567.89}
              format="currency"
              change={0.82}
              changeLabel="24h"
              sparkline={<SparklineChart data={SPARKLINE_UP} color="gain" />}
            />
            <MetricCard
              title="Day P&L"
              value={14203.12}
              format="currency"
              change={1.24}
              changeLabel="today"
              sparkline={<SparklineChart data={SPARKLINE_UP} color="gain" />}
            />
            <MetricCard
              title="Drawdown"
              value={4.2}
              suffix="%"
              change={-0.8}
              variant="dark"
              sparkline={<SparklineChart data={SPARKLINE_DOWN} color="loss" />}
            />
          </div>
        </motion.section>

        {/* ── 5.1 MarketTicker ──────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>5.1 MarketTicker — infinite scroll ticker</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-4">
            Hover to pause. Individual items flash green/red on price change. Dual-copy for seamless loop.
          </p>
          <MarketTicker items={TICKER_ITEMS} speed="slow" />
          <div className="mt-3 flex gap-3">
            <MarketTicker items={TICKER_ITEMS.slice(0, 4)} speed="normal" className="flex-1" />
            <MarketTicker items={TICKER_ITEMS.slice(4)} speed="fast" className="flex-1" />
          </div>
        </motion.section>

        {/* ── 5.2 ActivityFeed ──────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>5.2 ActivityFeed — filterable timeline</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-4">
            Use the filter dropdown to switch between All / Trades / Alerts / Transfers views.
          </p>
          <div className="h-[520px]">
            <ActivityFeed
              items={ACTIVITY_ITEMS}
              maxItems={8}
              onItemClick={(item) => console.log('Activity clicked:', item.id)}
            />
          </div>
        </motion.section>

        {/* ── 5.3 Watchlist ─────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>5.3 Watchlist — price list with hover actions</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-4">
            Hover a row to reveal Bell (set alert) and X (remove) actions. Prices flash on change.
          </p>
          <div className="max-w-xs h-[360px]">
            <Watchlist
              items={WATCHLIST_ITEMS}
              onSelect={(item) => console.log('Selected:', item.symbol)}
              onAlert={(item) => openAlertModal(item.symbol)}
              onRemove={(id) => console.log('Remove:', id)}
              onAdd={() => console.log('Add to watchlist')}
            />
          </div>
        </motion.section>

        {/* ── 5.4 PositionsTable ────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>5.4 PositionsTable — sortable holdings table</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-4">
            Click column headers to sort. Click a row to open the PositionDrawer. Weight column has mini progress bars.
          </p>
          <PositionsTable
            data={POSITIONS_DATA}
            title="Current Holdings"
            onPositionClick={handlePositionClick}
          />
        </motion.section>

        {/* ── 5.5 MarketRegimePanel ─────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>5.5 MarketRegimePanel — regime assessment</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-4">
            Dark glass card. Shows regime type, confidence, indicator grid, and curator commentary.
          </p>
          <div className="max-w-lg">
            <MarketRegimePanel data={REGIME_DATA} />
          </div>
        </motion.section>

        {/* ── 5.6 StrategyCard — individual ─────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>5.6 StrategyCard — all 4 status states</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-4">
            Active (pulsing green), Paused (amber), Error (red), Training (pulsing blue). Pause/Resume buttons stop propagation.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {STRATEGIES.map(s => (
              <StrategyCard
                key={s.id}
                {...s}
                onPause={(id) => console.log('Pause:', id)}
                onResume={(id) => console.log('Resume:', id)}
                onConfigure={(id) => console.log('Configure:', id)}
                onClick={(id) => console.log('Card click:', id)}
              />
            ))}
          </div>
        </motion.section>

        {/* ── 5.7 StrategyGrid ──────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>5.7 StrategyGrid — staggered grid animation</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono mb-4">
            All 6 MVP strategies. Cards stagger-animate in on mount. Responsive 1/2/3 col.
          </p>
          <StrategyGrid
            strategies={STRATEGIES}
            onStrategyClick={(id) => console.log('Strategy grid click:', id)}
          />
        </motion.section>

        {/* ── Loading states ─────────────────────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6">
          <SectionTitle>Loading states — Skeleton placeholders</SectionTitle>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-3">StrategyGrid loading</p>
              <StrategyGrid strategies={[]} isLoading />
            </div>
            <div>
              <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-3">Watchlist loading</p>
              <div className="h-[240px]">
                <Watchlist items={[]} isLoading />
              </div>
            </div>
          </div>
          <div className="mt-6">
            <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-3">PositionsTable loading</p>
            <PositionsTable isLoading />
          </div>
        </motion.section>

        {/* ── 5.8–5.11 Panel/Modal triggers ────────────────── */}
        <motion.section variants={fadeInUp} className="glass-panel rounded-2xl p-6 space-y-6">
          <SectionTitle>5.8–5.11 Overlay Components — portals</SectionTitle>
          <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 font-mono">
            All four overlay components render into document.body via createPortal, sitting outside the sidebar/layout stacking context.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* EmergencyPanel */}
            <GlassCard variant="subtle" padding="md" className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-loss/10 text-loss">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <span className="text-sm font-mono font-bold text-obsidian-400 dark:text-paper-100">
                  5.8 EmergencyPanel
                </span>
              </div>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                Full-width right drawer with kill switch, position list, manual override, and CONFIRM gate.
              </p>
              <Button
                variant="danger"
                size="sm"
                className="w-full"
                onClick={openEmergency}
                leftIcon={<ShieldAlert className="w-4 h-4" />}
              >
                Open Emergency Panel
              </Button>
            </GlassCard>

            {/* AlertModal */}
            <GlassCard variant="subtle" padding="md" className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-warning/10 text-warning">
                  <Bell className="w-4 h-4" />
                </div>
                <span className="text-sm font-mono font-bold text-obsidian-400 dark:text-paper-100">
                  5.9 AlertModal
                </span>
              </div>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                Alert creator with condition selector, live price visualizer, frequency, and notification channels.
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={() => openAlertModal('BTC')}
                leftIcon={<Bell className="w-4 h-4" />}
              >
                Create Alert (BTC)
              </Button>
            </GlassCard>

            {/* PositionDrawer */}
            <GlassCard variant="subtle" padding="md" className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-info/10 text-info">
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <span className="text-sm font-mono font-bold text-obsidian-400 dark:text-paper-100">
                  5.10 PositionDrawer
                </span>
              </div>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                Right slide-out with position summary, 30-day area chart, transaction history, fundamentals, and notes.
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={() => {
                  const pos: DrawerPosition = {
                    id: 'p1', symbol: 'BTC', name: 'Bitcoin', sector: 'Crypto',
                    assetType: 'Crypto', quantity: 2.5, avgCost: 64200,
                    price: 67763, value: 169407.50, pnl: 8907.50,
                    pnlPercent: 5.55, weight: 35.2,
                  };
                  setDrawerPosition(pos);
                  openPositionDrawer(pos);
                }}
              >
                Open BTC Position
              </Button>
            </GlassCard>

            {/* ExportModal */}
            <GlassCard variant="subtle" padding="md" className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-turquoise-mist/10 text-turquoise-mist">
                  <Download className="w-4 h-4" />
                </div>
                <span className="text-sm font-mono font-bold text-obsidian-400 dark:text-paper-100">
                  5.11 ExportModal
                </span>
              </div>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                Format picker (CSV / PDF / JSON), date range inputs, and info banner showing the export config.
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={openExportModal}
                leftIcon={<Download className="w-4 h-4" />}
              >
                Export Data
              </Button>
            </GlassCard>
          </div>
        </motion.section>

        {/* ── Section 6: System Status Bar ─────────────────────── */}
        <motion.section variants={fadeInUp}>
          <SectionTitle>6.0 SystemStatusBar</SectionTitle>
          <div className="space-y-4">
            {/* Collapsed (default) */}
            <div>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 mb-2 font-mono">
                Collapsed (click expand arrow to reveal service details)
              </p>
              <SystemStatusBar collapsible={true} defaultExpanded={false} />
            </div>
            {/* Pre-expanded */}
            <div>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 mb-2 font-mono">
                Expanded — shows per-service latency, status, and details
              </p>
              <SystemStatusBar collapsible={true} defaultExpanded={true} />
            </div>
          </div>
        </motion.section>

        {/* ── Section 7: Regime Tag Selector ───────────────────── */}
        <motion.section variants={fadeInUp}>
          <SectionTitle>7.0 RegimeTagSelector</SectionTitle>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Interactive */}
            <div>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 mb-2 font-mono">
                Interactive — click any option, confirm popup appears before apply
              </p>
              <RegimeTagSelector
                current={currentRegime}
                onChange={setCurrentRegime}
                showConfirmation={true}
              />
            </div>
            {/* Disabled */}
            <div>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50 mb-2 font-mono">
                Disabled state (read-only)
              </p>
              <RegimeTagSelector
                current="volatile"
                disabled={true}
                showConfirmation={false}
              />
            </div>
          </div>
        </motion.section>

        {/* ── Section 8: Risk Gauge ─────────────────────────────── */}
        <motion.section variants={fadeInUp}>
          <SectionTitle>8.0 RiskGauge</SectionTitle>

          {/* Risk level legend — context before viewing the gauges */}
          <GlassCard variant="subtle" padding="sm" className="mb-5">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-1">
              <span className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 shrink-0">
                Risk Levels
              </span>
              {[
                { color: '#10B981', label: 'Low', range: '0–40%' },
                { color: '#F59E0B', label: 'Medium', range: '40–65%' },
                { color: '#EF4444', label: 'High', range: '65–85%' },
                { color: '#DC2626', label: 'Critical', range: '85–100%' },
              ].map(({ color, label, range }) => (
                <div key={label} className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                  <span className="text-xs font-mono font-medium text-obsidian-400 dark:text-paper-100">{label}</span>
                  <span className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">{range}</span>
                </div>
              ))}
              <span className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40 ml-auto hidden lg:block">
                Needle animates from 0 on mount. Capital bar shows used vs available below gauge.
              </span>
            </div>
          </GlassCard>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <RiskGauge
              value={28}
              label="Portfolio Risk"
              sublabel="Low risk — healthy"
              usedCapital={28000}
              totalCapital={100000}
            />
            <RiskGauge
              value={52}
              label="Daily Exposure"
              sublabel="Medium risk"
              usedCapital={52000}
              totalCapital={100000}
            />
            <RiskGauge
              value={78}
              label="Drawdown Level"
              sublabel="High risk zone"
              usedCapital={78000}
              totalCapital={100000}
            />
            <RiskGauge
              value={94}
              label="Leverage Usage"
              sublabel="CRITICAL — reduce now"
              usedCapital={94000}
              totalCapital={100000}
            />
          </div>
        </motion.section>

        {/* ── Section 9: Drawdown Chart ─────────────────────────── */}
        <motion.section variants={fadeInUp}>
          <SectionTitle>9.0 DrawdownChart</SectionTitle>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DrawdownChart
              title="Portfolio Drawdown — 90D"
              maxDrawdown={-18.4}
              currentDrawdown={-3.2}
              height={220}
            />
            <DrawdownChart
              title="BTC Strategy Drawdown"
              maxDrawdown={-24.1}
              currentDrawdown={-11.6}
              height={220}
            />
          </div>
        </motion.section>

        {/* ── Section 10: Strategy Workflow Modals ─────────────── */}
        <motion.section variants={fadeInUp}>
          <SectionTitle>10.0 Strategy Workflow — ConfigModal + BacktestResultsModal + DetailDrawer</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* StrategyConfigModal */}
            <GlassCard variant="subtle" padding="md" className="space-y-3">
              <div className="space-y-1">
                <span className="text-sm font-mono font-bold text-obsidian-400 dark:text-paper-100">
                  10.1 StrategyConfigModal
                </span>
                <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                  Parameter sliders + risk rules per strategy type. Includes R:R ratio indicator.
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                className="w-full"
                onClick={() => setIsStrategyConfigOpen(true)}
              >
                Configure Momentum_MACD
              </Button>
            </GlassCard>

            {/* BacktestResultsModal */}
            <GlassCard variant="subtle" padding="md" className="space-y-3">
              <div className="space-y-1">
                <span className="text-sm font-mono font-bold text-obsidian-400 dark:text-paper-100">
                  10.2 BacktestResultsModal
                </span>
                <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                  Equity curve, 4 core metrics, collapsible trade log with individual rows.
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={() => setIsBacktestOpen(true)}
              >
                View Backtest Results
              </Button>
            </GlassCard>

            {/* StrategyDetailDrawer */}
            <GlassCard variant="subtle" padding="md" className="space-y-3">
              <div className="space-y-1">
                <span className="text-sm font-mono font-bold text-obsidian-400 dark:text-paper-100">
                  10.3 StrategyDetailDrawer
                </span>
                <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                  Slide-in drawer with 90D curve, signal history, and strategy stats.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => setIsStrategyDetailOpen(true)}
              >
                Strategy Deep Dive
              </Button>
            </GlassCard>
          </div>
        </motion.section>

        {/* ── Section 11: TradeDetailModal ────────────────────── */}
        <motion.section variants={fadeInUp}>
          <SectionTitle>11.0 TradeDetailModal</SectionTitle>
          <GlassCard variant="subtle" padding="md" className="space-y-3 max-w-sm">
            <div className="space-y-1">
              <span className="text-sm font-mono font-bold text-obsidian-400 dark:text-paper-100">
                11.1 TradeDetailModal
              </span>
              <p className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                Full execution detail: P&L hero, price chart during trade, cost breakdown (fees + slippage), signal context.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              className="w-full"
              onClick={() => setIsTradeDetailOpen(true)}
            >
              View Trade TRD-20241203-0042
            </Button>
          </GlassCard>
        </motion.section>

        {/* ── Footer ────────────────────────────────────────── */}
        <motion.div variants={fadeInUp} className="pb-8 text-center">
          <p className="text-xs font-mono text-obsidian-400/30 dark:text-paper-100/30">
            Session 6 + Session 7 prep complete — 19 dashboard components verified
          </p>
        </motion.div>

      </motion.div>

      {/* ── Overlay Components (portals) ──────────────────── */}
      <EmergencyPanel isOpen={isEmergencyOpen} onClose={closeEmergency} />

      <AlertModal
        isOpen={isAlertModalOpen}
        onClose={closeAlertModal}
        symbol={alertModalSymbol}
      />

      <PositionDrawer
        isOpen={isPositionDrawerOpen}
        onClose={closePositionDrawer}
        position={drawerPosition}
        onAlert={(symbol) => { closePositionDrawer(); openAlertModal(symbol); }}
      />

      <ExportModal
        isOpen={isExportModalOpen}
        onClose={closeExportModal}
        onExport={(config: ExportConfig) => console.log('Export config:', config)}
        title="Export Portfolio Data"
      />

      {/* New Session 7 prep overlays */}
      <StrategyConfigModal
        isOpen={isStrategyConfigOpen}
        onClose={() => setIsStrategyConfigOpen(false)}
        strategyId="s5"
        strategyName="Momentum_MACD"
        strategyType="momentum"
        onSave={(id, params, risk) => console.log('Strategy saved:', id, params, risk)}
      />

      <BacktestResultsModal
        isOpen={isBacktestOpen}
        onClose={() => setIsBacktestOpen(false)}
      />

      <StrategyDetailDrawer
        isOpen={isStrategyDetailOpen}
        onClose={() => setIsStrategyDetailOpen(false)}
      />

      <TradeDetailModal
        isOpen={isTradeDetailOpen}
        onClose={() => setIsTradeDetailOpen(false)}
      />
    </div>
  );
}

// ── Dev2Page wraps content with required providers ───────────
export default function Dev2Page() {
  return (
    <DashboardProvider>
      <Dev2Content />
    </DashboardProvider>
  );
}
