import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Download, Grid, List, Play, Pause, BarChart2 } from 'lucide-react';
import { useDashboard } from '@/contexts/DashboardContext';
import { useRealtimeSimulation, type StrategySummary } from '@/hooks/useRealtimeSimulation';
import { GlassCard, Badge, Button, SearchInput } from '@/components/ui';
import { SparklineChart } from '@/components/charts';
import { BacktestResultsModal } from '@/components/dashboard';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Types ─────────────────────────────────────────────────────────────────────

type StatusFilter = 'all' | 'active' | 'paused' | 'stopped';
type ViewMode = 'grid' | 'table';

// Extended StrategySummary with strategy-specific fields
interface StrategyFull extends StrategySummary {
  symbol: string;
  timeframe: string;
  winRate: number;
  sharpe: number;
  maxDrawdown: number;
  totalTrades: number;
  description: string;
}

// ── Static data ───────────────────────────────────────────────────────────────

const INITIAL_STRATEGIES: StrategyFull[] = [
  {
    id: 'btf',   name: 'Bear Trend Follower',
    status: 'active',  pnlDay: 312.40,  pnlTotal: 4821.30,
    sparkline: [10,14,13,16,15,18,17,20,22,24],
    symbol: 'BTC/ETH/SOL', timeframe: '1h',
    winRate: 72, sharpe: 2.8, maxDrawdown: -8.2, totalTrades: 34,
    description: 'Follows confirmed bear trends using EMA crosses and volume confirmation.',
  },
  {
    id: 'icvp',  name: 'Ichimoku Cloud VP',
    status: 'active',  pnlDay: 184.20,  pnlTotal: 2903.10,
    sparkline: [8,9,11,10,13,14,13,16,15,17],
    symbol: 'All pairs', timeframe: '4h',
    winRate: 65, sharpe: 2.1, maxDrawdown: -11.4, totalTrades: 52,
    description: 'Cloud breakout signals with volume profile confirmation zones.',
  },
  {
    id: 'cmf',   name: 'Cascading Momentum Filter',
    status: 'active',  pnlDay: 97.60,   pnlTotal: 1412.80,
    sparkline: [5,7,6,9,8,11,10,13,12,14],
    symbol: 'SOL/XRP/AVAX', timeframe: '1h',
    winRate: 68, sharpe: 1.9, maxDrawdown: -9.8, totalTrades: 29,
    description: 'Multi-timeframe momentum cascade filter for high-conviction entries.',
  },
  {
    id: 'ema',   name: 'EMA Trend RSI',
    status: 'active',  pnlDay: -43.10,  pnlTotal: 620.40,
    sparkline: [12,11,10,9,11,10,9,8,10,9],
    symbol: 'ETH/BNB', timeframe: '1h',
    winRate: 55, sharpe: 1.2, maxDrawdown: -14.1, totalTrades: 41,
    description: 'EMA trend direction filtered by RSI divergence for entry timing.',
  },
  {
    id: 'bsb',   name: 'BB Squeeze Breakout',
    status: 'paused',  pnlDay: 0,       pnlTotal: 380.20,
    sparkline: [6,6,6,6,6,6,6,6,6,6],
    symbol: 'BTC', timeframe: '15m',
    winRate: 61, sharpe: 1.5, maxDrawdown: -12.3, totalTrades: 18,
    description: 'Bollinger Band squeeze detection for explosive breakout entries.',
  },
  {
    id: 'bsm',   name: 'BB Squeeze Momentum',
    status: 'paused',  pnlDay: 0,       pnlTotal: 210.50,
    sparkline: [4,4,4,4,4,4,4,4,4,4],
    symbol: 'ETH', timeframe: '15m',
    winRate: 58, sharpe: 1.3, maxDrawdown: -13.7, totalTrades: 12,
    description: 'Momentum variant of squeeze detection with MACD confirmation.',
  },
  {
    id: 'don',   name: 'Donchian ATR',
    status: 'active',  pnlDay: 58.30,   pnlTotal: 940.70,
    sparkline: [7,8,9,8,10,9,11,10,12,11],
    symbol: 'BTC/SOL', timeframe: '4h',
    winRate: 63, sharpe: 1.7, maxDrawdown: -10.5, totalTrades: 27,
    description: 'Donchian channel breakouts with ATR-based position sizing.',
  },
  {
    id: 'ramr',  name: 'Regime-Aware Mean Reversion',
    status: 'stopped', pnlDay: 0,       pnlTotal: -120.30,
    sparkline: [3,2,1,2,1,2,1,2,1,2],
    symbol: 'ETH/BNB', timeframe: '1h',
    winRate: 44, sharpe: 0.3, maxDrawdown: -18.9, totalTrades: 9,
    description: 'Mean reversion strategy gated by market regime classification.',
  },
  {
    id: 'super', name: 'Supertrend Volume MACD',
    status: 'active',  pnlDay: 71.80,   pnlTotal: 1180.60,
    sparkline: [6,8,7,9,8,10,9,11,10,12],
    symbol: 'BTC/DOGE', timeframe: '1h',
    winRate: 60, sharpe: 1.6, maxDrawdown: -11.2, totalTrades: 33,
    description: 'Supertrend indicator combined with volume-weighted MACD signals.',
  },
];

const INITIAL_WATCHLIST: never[] = [];
const INITIAL_ACTIVITY: never[] = [];

const STATUS_BADGE: Record<string, 'success' | 'warning' | 'neutral'> = {
  active:  'success',
  paused:  'warning',
  stopped: 'neutral',
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function StrategiesPage() {
  const { openExportModal } = useDashboard();
  const [viewMode, setViewMode]       = useState<ViewMode>('grid');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [searchQuery, setSearchQuery]  = useState('');
  const [backtestStrategyId, setBacktestStrategyId] = useState<string | null>(null);

  const { strategies } = useRealtimeSimulation(
    [],
    INITIAL_WATCHLIST,
    INITIAL_STRATEGIES,
    INITIAL_ACTIVITY,
  );

  const enriched = useMemo(() => {
    return (strategies as StrategyFull[]).filter(s => {
      const matchesStatus = statusFilter === 'all' || s.status === statusFilter;
      const matchesSearch = searchQuery === '' ||
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.symbol.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [strategies, statusFilter, searchQuery]);

  const counts = useMemo(() => ({
    total:   strategies.length,
    active:  strategies.filter(s => s.status === 'active').length,
    paused:  strategies.filter(s => s.status === 'paused').length,
    stopped: strategies.filter(s => s.status === 'stopped').length,
  }), [strategies]);

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
          <h1 className="text-2xl font-semibold text-paper-100">Strategies</h1>
          <p className="text-sm text-paper-400 mt-1">PARAVANT strategy fleet &mdash; paper trading mode</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg overflow-hidden border border-obsidian-200">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 transition-colors ${viewMode === 'grid' ? 'bg-turquoise/10 text-turquoise' : 'text-paper-400 hover:text-paper-200'}`}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-2 transition-colors ${viewMode === 'table' ? 'bg-turquoise/10 text-turquoise' : 'text-paper-400 hover:text-paper-200'}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
          <Button variant="ghost" size="sm" onClick={openExportModal}>
            <Download className="w-4 h-4 mr-1" /> Export
          </Button>
        </div>
      </motion.div>

      {/* Summary Bar */}
      <motion.div variants={fadeInUp}>
        <GlassCard className="flex flex-wrap gap-4 p-3">
          {[
            { label: 'Total',   count: counts.total,   color: 'text-paper-200' },
            { label: 'Active',  count: counts.active,  color: 'text-gain' },
            { label: 'Paused',  count: counts.paused,  color: 'text-warning' },
            { label: 'Stopped', count: counts.stopped, color: 'text-paper-400' },
          ].map(s => (
            <button
              key={s.label}
              onClick={() => setStatusFilter(s.label.toLowerCase() as StatusFilter)}
              className={`flex items-center gap-2 hover:opacity-80 transition-opacity ${
                statusFilter === s.label.toLowerCase() || (s.label === 'Total' && statusFilter === 'all') ? 'opacity-100' : 'opacity-60'
              }`}
            >
              <span className={`text-lg font-semibold ${s.color}`}>{s.count}</span>
              <span className="text-xs text-paper-400">{s.label}</span>
            </button>
          ))}
        </GlassCard>
      </motion.div>

      {/* Filter Row */}
      <motion.div variants={fadeInUp} className="flex gap-3">
        <SearchInput
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search strategies..."
          className="flex-1 max-w-xs"
        />
        <div className="flex gap-1">
          {(['all', 'active', 'paused', 'stopped'] as StatusFilter[]).map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 text-xs rounded-lg capitalize transition-colors ${
                statusFilter === s
                  ? 'bg-turquoise/10 text-turquoise font-medium'
                  : 'bg-obsidian-300 text-paper-400 hover:text-paper-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Grid View */}
      {viewMode === 'grid' && (
        <motion.div variants={staggerContainer} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {enriched.map(s => (
            <motion.div key={s.id} variants={fadeInUp}>
              <GlassCard className="hover:border-turquoise/20 transition-colors group">
                {/* Card header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-paper-100 truncate">{s.name}</h3>
                    <p className="text-xs text-paper-400 mt-0.5">{s.symbol} &bull; {s.timeframe}</p>
                  </div>
                  <Badge variant={STATUS_BADGE[s.status]} size="sm" dot>{s.status}</Badge>
                </div>

                {/* Description */}
                <p className="text-xs text-paper-400 mb-3 line-clamp-2">{s.description}</p>

                {/* Sparkline + P&L */}
                <div className="flex items-center justify-between mb-3">
                  <SparklineChart
                    data={s.sparkline}
                    width={80}
                    height={28}
                    color={s.pnlDay >= 0 ? 'gain' : 'loss'}
                  />
                  <div className="text-right">
                    <div className={`text-sm font-semibold ${s.pnlTotal >= 0 ? 'text-gain' : 'text-loss'}`}>
                      {s.pnlTotal >= 0 ? '+' : ''}${s.pnlTotal.toFixed(0)}
                    </div>
                    <div className="text-xs text-paper-400">total P&L</div>
                  </div>
                </div>

                {/* Metrics row */}
                <div className="grid grid-cols-3 gap-2 mb-3 py-2 border-t border-b border-obsidian-200/50">
                  <div className="text-center">
                    <div className="text-sm font-medium text-paper-200">{s.winRate}%</div>
                    <div className="text-xs text-paper-500">Win rate</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium text-paper-200">{s.sharpe.toFixed(1)}</div>
                    <div className="text-xs text-paper-500">Sharpe</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-sm font-medium ${s.maxDrawdown < -15 ? 'text-loss' : 'text-paper-200'}`}>{s.maxDrawdown}%</div>
                    <div className="text-xs text-paper-500">Max DD</div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="flex-1 text-xs"
                    onClick={() => setBacktestStrategyId(s.id)}
                  >
                    <BarChart2 className="w-3 h-3 mr-1" /> Backtest
                  </Button>
                  {s.status === 'active' && (
                    <Button variant="ghost" size="sm" className="text-xs text-warning">
                      <Pause className="w-3 h-3" />
                    </Button>
                  )}
                  {s.status === 'paused' && (
                    <Button variant="ghost" size="sm" className="text-xs text-gain">
                      <Play className="w-3 h-3" />
                    </Button>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <motion.div variants={fadeInUp}>
          <GlassCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-paper-400 border-b border-obsidian-200">
                    <th className="text-left pb-3 font-medium">Strategy</th>
                    <th className="text-left pb-3 font-medium">Symbol</th>
                    <th className="text-left pb-3 font-medium">Status</th>
                    <th className="text-right pb-3 font-medium">Day P&L</th>
                    <th className="text-right pb-3 font-medium">Total P&L</th>
                    <th className="text-right pb-3 font-medium">Win Rate</th>
                    <th className="text-right pb-3 font-medium">Sharpe</th>
                    <th className="text-right pb-3 font-medium">Trades</th>
                    <th className="text-right pb-3 font-medium">Trend</th>
                    <th className="text-right pb-3 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {enriched.map(s => (
                    <tr key={s.id} className="border-b border-obsidian-200/50 last:border-0 hover:bg-obsidian-300/20 transition-colors">
                      <td className="py-3">
                        <div className="font-medium text-paper-100">{s.name}</div>
                        <div className="text-xs text-paper-500">{s.timeframe}</div>
                      </td>
                      <td className="py-3 text-xs text-paper-300">{s.symbol}</td>
                      <td className="py-3">
                        <Badge variant={STATUS_BADGE[s.status]} size="sm" dot>{s.status}</Badge>
                      </td>
                      <td className={`py-3 text-right font-medium ${s.pnlDay >= 0 ? 'text-gain' : 'text-loss'}`}>
                        {s.pnlDay >= 0 ? '+' : ''}{s.pnlDay.toFixed(2)}
                      </td>
                      <td className={`py-3 text-right font-medium ${s.pnlTotal >= 0 ? 'text-gain' : 'text-loss'}`}>
                        {s.pnlTotal >= 0 ? '+' : ''}${s.pnlTotal.toFixed(0)}
                      </td>
                      <td className="py-3 text-right text-paper-200">{s.winRate}%</td>
                      <td className="py-3 text-right text-paper-200">{s.sharpe.toFixed(1)}</td>
                      <td className="py-3 text-right text-paper-400">{s.totalTrades}</td>
                      <td className="py-3 text-right">
                        <SparklineChart data={s.sparkline} width={50} height={20} color={s.pnlDay >= 0 ? 'gain' : 'loss'} />
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => setBacktestStrategyId(s.id)}
                          className="text-xs text-turquoise hover:text-turquoise/80 transition-colors"
                        >
                          Backtest
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Backtest Modal */}
      <BacktestResultsModal
        strategyId={backtestStrategyId ?? undefined}
        isOpen={backtestStrategyId !== null}
        onClose={() => setBacktestStrategyId(null)}
      />
    </motion.div>
  );
}
