import { useState } from 'react';
import { motion } from 'framer-motion';
import { Server, Wifi, Shield, Activity, Download } from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { GlassCard, Badge, Button, Progress } from '@/components/ui';
import { DonutChart } from '@/components/charts';
import { MarketRegimePanel } from '@/components/dashboard';
import type { MarketRegimeData } from '@/components/dashboard/MarketRegimePanel';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Types ─────────────────────────────────────────────────────────────────────

interface DecisionEntry {
  id: string;
  time: string;
  category: 'Allocation' | 'Strategy' | 'Risk' | 'Regime';
  action: string;
  detail: string;
}

interface StrategyRow {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'stopped';
  symbol: string;
  pnlTotal: number;
  winRate: number;
  sharpe: number;
  trades: number;
}

// ── Static data ───────────────────────────────────────────────────────────────

const STRATEGY_ALLOCATION = [
  { name: 'BTF',     value: 28, color: '#14b8a6' },
  { name: 'ICVP',    value: 22, color: '#6366f1' },
  { name: 'CMF',     value: 15, color: '#f59e0b' },
  { name: 'EMA-RSI', value: 12, color: '#10b981' },
  { name: 'Donchian',value: 10, color: '#3b82f6' },
  { name: 'Supertrend', value: 8, color: '#8b5cf6' },
  { name: 'Other',   value: 5,  color: '#6b7280' },
];

const CRYPTO_ALLOCATION = [
  { name: 'BTC',  value: 38, color: '#f7931a' },
  { name: 'ETH',  value: 25, color: '#627eea' },
  { name: 'SOL',  value: 12, color: '#9945ff' },
  { name: 'BNB',  value: 11, color: '#f3ba2f' },
  { name: 'AVAX', value: 5,  color: '#e84142' },
  { name: 'XRP',  value: 4,  color: '#00aae4' },
  { name: 'DOGE', value: 5,  color: '#c2a633' },
];

const DECISIONS: DecisionEntry[] = [
  { id: '1', time: '14:32', category: 'Strategy', action: 'BTF activated on BTCUSDT',      detail: 'Bear trend confirmed — momentum below 0 on 1h' },
  { id: '2', time: '13:58', category: 'Regime',   action: 'Regime updated: Bear Trending', detail: 'BTC below 20-day MA, Fear & Greed at 22' },
  { id: '3', time: '13:15', category: 'Risk',     action: 'BB Squeeze Breakout paused',    detail: 'Drawdown limit reached: -2.1% on daily' },
  { id: '4', time: '12:40', category: 'Allocation', action: 'CMF weight raised to 15%',   detail: 'High conviction signal across SOL/XRP/AVAX' },
  { id: '5', time: '11:22', category: 'Strategy', action: 'RAMR stopped',                  detail: 'Mean reversion unsuitable in current regime' },
  { id: '6', time: '10:05', category: 'Risk',     action: 'Daily loss limit adjusted',     detail: 'Tightened to 1.5% given high volatility' },
  { id: '7', time: '09:30', category: 'Regime',   action: 'Session opened: bear bias',     detail: 'Overnight BTC -3.2%, volume above average' },
];

const STRATEGIES: StrategyRow[] = [
  { id: 'btf',   name: 'Bear Trend Follower',       status: 'active',  symbol: 'BTC/ETH/SOL', pnlTotal: 4821,  winRate: 72, sharpe: 2.8, trades: 34 },
  { id: 'icvp',  name: 'Ichimoku Cloud VP',         status: 'active',  symbol: 'All pairs',   pnlTotal: 2903,  winRate: 65, sharpe: 2.1, trades: 52 },
  { id: 'cmf',   name: 'Cascading Momentum Filter', status: 'active',  symbol: 'SOL/XRP/AVAX',pnlTotal: 1412,  winRate: 68, sharpe: 1.9, trades: 29 },
  { id: 'ema',   name: 'EMA Trend RSI',             status: 'active',  symbol: 'ETH/BNB',     pnlTotal: 620,   winRate: 55, sharpe: 1.2, trades: 41 },
  { id: 'bsb',   name: 'BB Squeeze Breakout',       status: 'paused',  symbol: 'BTC',         pnlTotal: 380,   winRate: 61, sharpe: 1.5, trades: 18 },
  { id: 'bsm',   name: 'BB Squeeze Momentum',       status: 'paused',  symbol: 'ETH',         pnlTotal: 210,   winRate: 58, sharpe: 1.3, trades: 12 },
  { id: 'don',   name: 'Donchian ATR',              status: 'active',  symbol: 'BTC/SOL',     pnlTotal: 940,   winRate: 63, sharpe: 1.7, trades: 27 },
  { id: 'ramr',  name: 'Regime-Aware Mean Rev.',    status: 'stopped', symbol: 'ETH/BNB',     pnlTotal: -120,  winRate: 44, sharpe: 0.3, trades: 9 },
  { id: 'super', name: 'Supertrend Volume MACD',    status: 'active',  symbol: 'BTC/DOGE',    pnlTotal: 1180,  winRate: 60, sharpe: 1.6, trades: 33 },
];

const REGIME_DATA: MarketRegimeData = {
  type: 'BEAR TRENDING',
  confidence: 78,
  duration: '12d',
  indicators: {
    vix:         { value: 28.4,  label: 'Crypto Fear Index',   status: 'elevated' },
    breadth:     { value: '34%', label: 'Coins Above 20MA',    status: 'weak'     },
    trend:       { value: -3.2,  label: 'BTC 7d Change %',     status: 'bearish'  },
    correlation: { value: 0.82,  label: 'Cross-Asset Corr',    status: 'high'     },
    putCall:     { value: 22,    label: 'Fear & Greed Index',  status: 'fear'     },
  },
  commentary: 'BTC below 20-day MA with high cross-asset correlation. Bear trending strategies active. Avoid mean-reversion entries.',
};

const RISK_LIMITS = [
  { label: 'Daily Loss',       used: 62,  limit: '1.5% capital' },
  { label: 'Position Size',    used: 45,  limit: '5% per trade' },
  { label: 'Portfolio Drawdown', used: 28, limit: '10% total' },
  { label: 'Open Positions',   used: 55,  limit: '5 concurrent' },
];

const CATEGORY_COLOR: Record<string, string> = {
  Allocation: 'bg-turquoise/10 text-turquoise',
  Strategy:   'bg-info/10 text-info',
  Risk:       'bg-loss/10 text-loss',
  Regime:     'bg-warning/10 text-warning',
};

const STATUS_COLOR: Record<string, string> = {
  active:  'text-gain',
  paused:  'text-warning',
  stopped: 'text-paper-400',
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function SystemPage() {
  const { openExportModal, viewStrategy } = useDashboard();
  const [filterCategory, setFilterCategory] = useState<string>('All');

  const categories = ['All', 'Allocation', 'Strategy', 'Risk', 'Regime'];
  const filteredDecisions = filterCategory === 'All'
    ? DECISIONS
    : DECISIONS.filter(d => d.category === filterCategory);

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-4"
    >
      {/* Header */}
      <motion.div variants={fadeInUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-paper-100">System Overview</h1>
          <p className="text-sm text-paper-400 mt-1">Capital allocation, regime state, and strategy performance</p>
        </div>
        <Button variant="ghost" size="sm" onClick={openExportModal}>
          <Download className="w-4 h-4 mr-1" /> Export
        </Button>
      </motion.div>

      {/* Health Cards */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: Server,    label: 'System Uptime',     value: '99.8%',   status: 'success' as const, note: '12d 4h running' },
          { icon: Wifi,      label: 'Binance Connection', value: 'Online',  status: 'success' as const, note: 'Spot API + WebSocket' },
          { icon: Shield,    label: 'Trading Mode',       value: 'PAPER',   status: 'warning' as const, note: 'Simulated execution' },
          { icon: Activity,  label: 'Active Strategies',  value: '6 / 9',   status: 'info' as const,    note: '2 paused, 1 stopped' },
        ].map(card => (
          <GlassCard key={card.label} className="p-4">
            <div className="flex items-start justify-between">
              <card.icon className="w-5 h-5 text-paper-400" />
              <Badge variant={card.status} size="sm">{card.status === 'success' ? 'OK' : card.status === 'warning' ? 'Paper' : 'Active'}</Badge>
            </div>
            <div className="mt-3">
              <div className="text-xl font-semibold text-paper-100">{card.value}</div>
              <div className="text-xs text-paper-400 mt-0.5">{card.label}</div>
              <div className="text-xs text-paper-500 mt-1">{card.note}</div>
            </div>
          </GlassCard>
        ))}
      </motion.div>

      {/* Capital Allocation + Regime */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Strategy Allocation */}
        <motion.div variants={fadeInUp}>
          <GlassCard className="h-full">
            <h2 className="text-sm font-medium text-paper-200 mb-3">Capital by Strategy</h2>
            <DonutChart
              data={STRATEGY_ALLOCATION}
              height={180}
              showLegend
              centerContent={
                <div className="text-center">
                  <div className="text-base font-semibold text-paper-100">$102K</div>
                  <div className="text-xs text-paper-400">deployed</div>
                </div>
              }
            />
          </GlassCard>
        </motion.div>

        {/* Crypto Allocation */}
        <motion.div variants={fadeInUp}>
          <GlassCard className="h-full">
            <h2 className="text-sm font-medium text-paper-200 mb-3">Capital by Asset</h2>
            <DonutChart
              data={CRYPTO_ALLOCATION}
              height={180}
              showLegend
              centerContent={
                <div className="text-center">
                  <div className="text-base font-semibold text-paper-100">7</div>
                  <div className="text-xs text-paper-400">assets</div>
                </div>
              }
            />
          </GlassCard>
        </motion.div>

        {/* Regime */}
        <motion.div variants={fadeInUp}>
          <MarketRegimePanel data={REGIME_DATA} className="h-full" />
        </motion.div>
      </div>

      {/* Decision Log + Risk Limits */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Decision Log */}
        <motion.div variants={fadeInUp} className="lg:col-span-2">
          <GlassCard>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-paper-200">System Decision Log</h2>
              <div className="flex gap-1">
                {categories.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setFilterCategory(cat)}
                    className={`px-2 py-1 text-xs rounded transition-colors ${
                      filterCategory === cat
                        ? 'bg-turquoise/10 text-turquoise'
                        : 'text-paper-400 hover:text-paper-200'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-3">
              {filteredDecisions.map(d => (
                <div key={d.id} className="flex gap-3 p-2 rounded-lg hover:bg-obsidian-300/30 transition-colors">
                  <div className="text-xs text-paper-400 w-10 flex-shrink-0 pt-0.5">{d.time}</div>
                  <span className={`text-xs px-1.5 py-0.5 rounded h-fit flex-shrink-0 ${CATEGORY_COLOR[d.category]}`}>
                    {d.category}
                  </span>
                  <div className="min-w-0">
                    <div className="text-sm text-paper-100">{d.action}</div>
                    <div className="text-xs text-paper-400 mt-0.5">{d.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>

        {/* Risk Limits */}
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <h2 className="text-sm font-medium text-paper-200 mb-4">Risk Limit Usage</h2>
            <div className="space-y-4">
              {RISK_LIMITS.map(r => (
                <div key={r.label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-paper-300">{r.label}</span>
                    <span className={r.used > 80 ? 'text-loss' : r.used > 60 ? 'text-warning' : 'text-gain'}>
                      {r.used}%
                    </span>
                  </div>
                  <Progress
                    value={r.used}
                    max={100}
                    variant={r.used > 80 ? 'danger' : r.used > 60 ? 'warning' : 'success'}
                  />
                  <div className="text-xs text-paper-500 mt-1">Limit: {r.limit}</div>
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* Strategy Performance Table */}
      <motion.div variants={fadeInUp}>
        <GlassCard>
          <h2 className="text-sm font-medium text-paper-200 mb-4">Strategy Performance</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-paper-400 border-b border-obsidian-200">
                  <th className="text-left pb-2 font-medium">Strategy</th>
                  <th className="text-left pb-2 font-medium">Symbol</th>
                  <th className="text-left pb-2 font-medium">Status</th>
                  <th className="text-right pb-2 font-medium">Total P&L</th>
                  <th className="text-right pb-2 font-medium">Win Rate</th>
                  <th className="text-right pb-2 font-medium">Sharpe</th>
                  <th className="text-right pb-2 font-medium">Trades</th>
                  <th className="text-right pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {STRATEGIES.map(s => (
                  <tr key={s.id} className="border-b border-obsidian-200/50 last:border-0 hover:bg-obsidian-300/20 transition-colors">
                    <td className="py-2.5 text-paper-100 font-medium">{s.name}</td>
                    <td className="py-2.5 text-paper-300 text-xs">{s.symbol}</td>
                    <td className="py-2.5">
                      <span className={`text-xs font-medium capitalize ${STATUS_COLOR[s.status]}`}>{s.status}</span>
                    </td>
                    <td className={`py-2.5 text-right font-medium ${s.pnlTotal >= 0 ? 'text-gain' : 'text-loss'}`}>
                      {s.pnlTotal >= 0 ? '+' : ''}${s.pnlTotal.toLocaleString()}
                    </td>
                    <td className="py-2.5 text-right text-paper-200">{s.winRate}%</td>
                    <td className="py-2.5 text-right text-paper-200">{s.sharpe.toFixed(1)}</td>
                    <td className="py-2.5 text-right text-paper-400">{s.trades}</td>
                    <td className="py-2.5 text-right">
                      <button
                        onClick={() => viewStrategy(s.id)}
                        className="text-xs text-turquoise hover:text-turquoise/80 transition-colors"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
