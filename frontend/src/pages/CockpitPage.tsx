import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Activity, Wifi, Clock, Download, BarChart2, Zap, TrendingUp } from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { useRealtimeSimulation, type StrategySummary } from '@/hooks/useRealtimeSimulation';
import { usePaperSessions } from '@/hooks/usePaperSessions';
import { GlassCard, Badge, Button, MetricCard } from '@/components/ui';
import { SVGAreaChart, DonutChart, SparklineChart } from '@/components/charts';
import { MarketTicker, ActivityFeed, Watchlist, PositionsTable } from '@/components/dashboard';
import type { MarketItem } from '@/components/dashboard/MarketTicker';
import type { WatchlistItem } from '@/components/dashboard/Watchlist';
import type { ActivityItem } from '@/components/dashboard/ActivityFeed';
import type { Position } from '@/components/dashboard/PositionsTable';
import type { AreaChartData } from '@/components/charts/AreaChart';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Static seed data ──────────────────────────────────────────────────────────

const INITIAL_MARKET: MarketItem[] = [
  { symbol: 'BTC/USDT', value: 62840, change: 1420, changePercent: 2.31 },
  { symbol: 'ETH/USDT', value: 3185,  change: -42,  changePercent: -1.30 },
  { symbol: 'BNB/USDT', value: 584,   change: 8.2,  changePercent: 1.42 },
  { symbol: 'SOL/USDT', value: 148,   change: 3.5,  changePercent: 2.42 },
  { symbol: 'AVAX/USDT', value: 38.2, change: -0.8, changePercent: -2.05 },
  { symbol: 'XRP/USDT', value: 0.524, change: 0.012, changePercent: 2.35 },
  { symbol: 'DOGE/USDT', value: 0.162, change: -0.004, changePercent: -2.41 },
];

const INITIAL_WATCHLIST: WatchlistItem[] = [
  { id: '1', symbol: 'BTC', name: 'Bitcoin',   price: 62840, change: 1420,   changePercent: 2.31 },
  { id: '2', symbol: 'ETH', name: 'Ethereum',  price: 3185,  change: -42,    changePercent: -1.30 },
  { id: '3', symbol: 'SOL', name: 'Solana',    price: 148,   change: 3.5,    changePercent: 2.42 },
  { id: '4', symbol: 'BNB', name: 'BNB',       price: 584,   change: 8.2,    changePercent: 1.42 },
  { id: '5', symbol: 'XRP', name: 'XRP',       price: 0.524, change: 0.012,  changePercent: 2.35 },
  { id: '6', symbol: 'AVAX', name: 'Avalanche', price: 38.2,  change: -0.8,  changePercent: -2.05 },
  { id: '7', symbol: 'DOGE', name: 'Dogecoin', price: 0.162, change: -0.004, changePercent: -2.41 },
];

const INITIAL_STRATEGIES: StrategySummary[] = [
  { id: 'btf',    name: 'Bear Trend Follower',       status: 'active',  pnlDay: 312.40,  pnlTotal: 4821.30, sparkline: [10,14,13,16,15,18,17,20,22,24] },
  { id: 'icvp',   name: 'Ichimoku Cloud VP',         status: 'active',  pnlDay: 184.20,  pnlTotal: 2903.10, sparkline: [8,9,11,10,13,14,13,16,15,17] },
  { id: 'cmf',    name: 'Cascading Momentum Filter', status: 'active',  pnlDay: 97.60,   pnlTotal: 1412.80, sparkline: [5,7,6,9,8,11,10,13,12,14] },
  { id: 'ema',    name: 'EMA Trend RSI',              status: 'active',  pnlDay: -43.10,  pnlTotal: 620.40,  sparkline: [12,11,10,9,11,10,9,8,10,9] },
  { id: 'bsb',    name: 'BB Squeeze Breakout',       status: 'paused',  pnlDay: 0,       pnlTotal: 380.20,  sparkline: [6,6,6,6,6,6,6,6,6,6] },
  { id: 'bsm',    name: 'BB Squeeze Momentum',       status: 'paused',  pnlDay: 0,       pnlTotal: 210.50,  sparkline: [4,4,4,4,4,4,4,4,4,4] },
  { id: 'don',    name: 'Donchian ATR',               status: 'active',  pnlDay: 58.30,   pnlTotal: 940.70,  sparkline: [7,8,9,8,10,9,11,10,12,11] },
  { id: 'ramr',   name: 'Regime-Aware Mean Rev.',    status: 'stopped', pnlDay: 0,       pnlTotal: -120.30, sparkline: [3,2,1,2,1,2,1,2,1,2] },
  { id: 'super',  name: 'Supertrend Volume MACD',    status: 'active',  pnlDay: 71.80,   pnlTotal: 1180.60, sparkline: [6,8,7,9,8,10,9,11,10,12] },
];

const INITIAL_ACTIVITY: ActivityItem[] = [
  { id: '1', type: 'trade',  title: 'BTC Long Closed',        description: 'BTF closed BTCUSDT long +$312', timestamp: new Date(Date.now() - 180000) },
  { id: '2', type: 'alert',  title: 'Regime Shift Detected',  description: 'Market regime updated to bear trending', timestamp: new Date(Date.now() - 600000) },
  { id: '3', type: 'agent',  title: 'ICVP Signal: ETH',       description: 'Ichimoku cloud cross detected on ETHUSDT 1h', timestamp: new Date(Date.now() - 1200000) },
  { id: '4', type: 'trade',  title: 'SOL Short Opened',       description: 'CMF opened SOLUSDT short at $148.20', timestamp: new Date(Date.now() - 1800000) },
  { id: '5', type: 'alert',  title: 'Drawdown Warning',       description: 'Portfolio daily drawdown at 1.8% of 2% limit', timestamp: new Date(Date.now() - 2400000) },
];

const INITIAL_POSITIONS: Position[] = [
  { id: '1', symbol: 'BTC',  name: 'Bitcoin',   quantity: 0.42,  avgPrice: 59200, currentPrice: 62840, pl: 1528.80, plPercent: 6.15,  weight: 38.2, assetType: 'Crypto' },
  { id: '2', symbol: 'ETH',  name: 'Ethereum',  quantity: 2.8,   avgPrice: 3240,  currentPrice: 3185,  pl: -154.00, plPercent: -1.70, weight: 24.6, assetType: 'Crypto' },
  { id: '3', symbol: 'SOL',  name: 'Solana',    quantity: 18,    avgPrice: 142,   currentPrice: 148,   pl: 108.00,  plPercent: 4.23,  weight: 12.1, assetType: 'Crypto' },
  { id: '4', symbol: 'BNB',  name: 'BNB',       quantity: 3.5,   avgPrice: 570,   currentPrice: 584,   pl: 49.00,   plPercent: 2.46,  weight: 11.8, assetType: 'Crypto' },
  { id: '5', symbol: 'AVAX', name: 'Avalanche', quantity: 24,    avgPrice: 41.5,  currentPrice: 38.2,  pl: -79.20,  plPercent: -7.95, weight: 5.3,  assetType: 'Crypto' },
];

const EQUITY_CURVE: AreaChartData[] = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.now() - (29 - i) * 86400000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  value: 98200 + Math.round((Math.sin(i * 0.3) * 800) + (i * 120) + (Math.random() * 400)),
}));

const ALLOCATION_DATA = [
  { name: 'BTC',  value: 38.2, color: '#f7931a' },
  { name: 'ETH',  value: 24.6, color: '#627eea' },
  { name: 'SOL',  value: 12.1, color: '#9945ff' },
  { name: 'BNB',  value: 11.8, color: '#f3ba2f' },
  { name: 'AVAX', value: 5.3,  color: '#e84142' },
  { name: 'XRP',  value: 3.1,  color: '#00aae4' },
  { name: 'USDT', value: 4.9,  color: '#26a17b' },
];

const STATUS_COLOR: Record<string, string> = {
  active:  'bg-gain',
  paused:  'bg-warning',
  stopped: 'bg-paper-400',
};

// ── Component ─────────────────────────────────────────────────────────────────

function templateName(templateId: string): string {
  return templateId
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

export default function CockpitPage() {
  const { openEmergency, openAlertModal, openExportModal, openPositionDrawer } = useDashboard();
  const [activeTab, setActiveTab] = useState<'activity' | 'positions' | 'allocation'>('activity');

  const { marketData, watchlist, strategies: simStrategies, activity, lastSync } = useRealtimeSimulation(
    INITIAL_MARKET,
    INITIAL_WATCHLIST,
    INITIAL_STRATEGIES,
    INITIAL_ACTIVITY,
  );

  const { sessions } = usePaperSessions();

  // When the API returns real sessions, prefer those over simulated data.
  const strategies: StrategySummary[] = useMemo(() => {
    if (sessions.length === 0) return simStrategies;
    return sessions.map(s => ({
      id:       s.sessionId,
      name:     `${templateName(s.templateId)} — ${s.symbol}`,
      status:   s.isActive ? 'active' as const : 'stopped' as const,
      pnlDay:   s.pnlDayUsdt,
      pnlTotal: s.pnlUsdt,
      sparkline: s.sparkline,
    }));
  }, [sessions, simStrategies]);

  const totalPnlDay  = strategies.reduce((s, x) => s + x.pnlDay, 0);
  const activeCount  = strategies.filter(s => s.status === 'active').length;
  const totalValue   = INITIAL_POSITIONS.reduce((s, p) => s + p.quantity * p.currentPrice, 0);

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-4"
    >
      {/* Ticker */}
      <motion.div variants={fadeInUp}>
        <MarketTicker items={marketData} speed="normal" pauseOnHover />
      </motion.div>

      {/* Header */}
      <motion.div variants={fadeInUp} className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-paper-100">Cockpit</h1>
            <Badge variant="warning" dot pulsing>PAPER TRADING</Badge>
            <Badge variant="success" dot>Binance Connected</Badge>
          </div>
          <p className="text-sm text-paper-400 mt-1">
            Real-time portfolio overview &mdash; synced {lastSync}s ago
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => openAlertModal()}>
            <Activity className="w-4 h-4 mr-1" /> Alerts
          </Button>
          <Button variant="ghost" size="sm" onClick={openExportModal}>
            <Download className="w-4 h-4 mr-1" /> Export
          </Button>
          <Button variant="danger" size="sm" onClick={openEmergency}>
            Emergency Stop
          </Button>
        </div>
      </motion.div>

      {/* KPI Row */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Portfolio Value"
          value={totalValue}
          format="currency"
          prefix="$"
          icon={BarChart2}
        />
        <MetricCard
          title="Day P&L"
          value={totalPnlDay}
          format="currency"
          prefix="$"
          change={totalPnlDay}
          icon={TrendingUp}
        />
        <MetricCard
          title="Active Strategies"
          value={activeCount}
          format="number"
          icon={Zap}
        />
        <MetricCard
          title="Sync Lag"
          value={lastSync}
          format="number"
          suffix="s"
          icon={Clock}
        />
      </motion.div>

      {/* System Health Bar */}
      <motion.div variants={fadeInUp}>
        <GlassCard className="flex flex-wrap gap-4 items-center p-3 text-sm">
          <div className="flex items-center gap-2">
            <Wifi className="w-4 h-4 text-gain" />
            <span className="text-paper-300">Binance API</span>
            <Badge variant="success" size="sm">Connected</Badge>
          </div>
          <div className="w-px h-4 bg-obsidian-200 hidden sm:block" />
          <div className="flex items-center gap-2">
            <span className="text-paper-400">Mode:</span>
            <Badge variant="warning" size="sm">Paper Trading</Badge>
          </div>
          <div className="w-px h-4 bg-obsidian-200 hidden sm:block" />
          <div className="flex items-center gap-2">
            <span className="text-paper-400">Last trade:</span>
            <span className="text-paper-200">3m ago &mdash; BTC long closed</span>
          </div>
          <div className="w-px h-4 bg-obsidian-200 hidden sm:block" />
          <div className="flex items-center gap-2">
            <span className="text-paper-400">Pending signals:</span>
            <span className="text-turquoise font-medium">2</span>
          </div>
        </GlassCard>
      </motion.div>

      {/* Main grid: chart + strategies + watchlist */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Left: equity + tabs */}
        <div className="lg:col-span-2 space-y-4">

          {/* Equity Curve */}
          <motion.div variants={fadeInUp}>
            <GlassCard>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-medium text-paper-200">30-Day NAV Curve</h2>
                <span className="text-xs text-paper-400">Paper portfolio equity</span>
              </div>
              <SVGAreaChart data={EQUITY_CURVE} height={160} showGrid />
            </GlassCard>
          </motion.div>

          {/* Tabbed Panel */}
          <motion.div variants={fadeInUp}>
            <GlassCard>
              <div className="flex gap-1 mb-4 border-b border-obsidian-200 pb-2">
                {(['activity', 'positions', 'allocation'] as const).map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-3 py-1.5 text-sm rounded-md capitalize transition-colors ${
                      activeTab === tab
                        ? 'bg-turquoise/10 text-turquoise font-medium'
                        : 'text-paper-400 hover:text-paper-200'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {activeTab === 'activity' && (
                <ActivityFeed items={activity} maxItems={8} showTimestamps />
              )}

              {activeTab === 'positions' && (
                <PositionsTable
                  data={INITIAL_POSITIONS}
                  onPositionClick={(p) => {
                    openPositionDrawer({
                      id: p.id, symbol: p.symbol, name: p.name,
                      sector: 'Crypto', assetType: 'Crypto',
                      quantity: p.quantity, avgCost: p.avgPrice,
                      price: p.currentPrice, value: p.quantity * p.currentPrice,
                      pnl: p.pl, pnlPercent: p.plPercent, weight: p.weight,
                    });
                  }}
                />
              )}

              {activeTab === 'allocation' && (
                <div className="flex justify-center">
                  <DonutChart
                    data={ALLOCATION_DATA}
                    height={220}
                    showLegend
                    centerContent={
                      <div className="text-center">
                        <div className="text-lg font-semibold text-paper-100">7</div>
                        <div className="text-xs text-paper-400">assets</div>
                      </div>
                    }
                  />
                </div>
              )}
            </GlassCard>
          </motion.div>
        </div>

        {/* Right: strategy fleet + watchlist */}
        <div className="space-y-4">

          {/* Strategy Fleet */}
          <motion.div variants={fadeInUp}>
            <GlassCard>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-medium text-paper-200">Strategy Fleet</h2>
                <Badge variant="neutral" size="sm">{activeCount}/{strategies.length} active</Badge>
              </div>
              <div className="space-y-2">
                {strategies.map(s => (
                  <div key={s.id} className="flex items-center justify-between py-1.5 border-b border-obsidian-200/50 last:border-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_COLOR[s.status]}`} />
                      <span className="text-xs text-paper-200 truncate">{s.name}</span>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <SparklineChart data={s.sparkline} width={40} height={20} color={s.pnlDay >= 0 ? 'gain' : 'loss'} />
                      <span className={`text-xs font-medium w-16 text-right ${s.pnlDay >= 0 ? 'text-gain' : 'text-loss'}`}>
                        {s.pnlDay >= 0 ? '+' : ''}{s.pnlDay.toFixed(0)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>

          {/* Watchlist */}
          <motion.div variants={fadeInUp}>
            <Watchlist
              items={watchlist}
              onAlert={(item) => openAlertModal(item.symbol)}
            />
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}
