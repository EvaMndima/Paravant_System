import { useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart2, Play, Clock } from 'lucide-react';
import { GlassCard, Badge, Button } from '@/components/ui';
import { SparklineChart } from '@/components/charts';
import { BacktestResultsModal } from '@/components/dashboard';
import { staggerContainer, fadeInUp } from '@/lib/animations';

// ── Types ─────────────────────────────────────────────────────────────────────

interface StrategySummary {
  id: string;
  name: string;
  symbol: string;
  timeframe: string;
  status: 'active' | 'paused' | 'stopped';
  lastRun: string | null;
  lastResult: {
    totalReturnPct: number;
    sharpe: number;
    maxDrawdown: number;
    winRate: number;
    totalTrades: number;
    passed: boolean;
  } | null;
  equitySpark: number[];
}

// ── Static data ───────────────────────────────────────────────────────────────

const STRATEGIES: StrategySummary[] = [
  {
    id: 'btf', name: 'Bear Trend Follower', symbol: 'BTC/ETH/SOL', timeframe: '1h',
    status: 'active', lastRun: '2026-04-29',
    lastResult: { totalReturnPct: 24.8, sharpe: 2.8, maxDrawdown: -8.2,  winRate: 72, totalTrades: 34, passed: true  },
    equitySpark: [100,103,105,108,107,112,110,115,118,124],
  },
  {
    id: 'icvp', name: 'Ichimoku Cloud VP', symbol: 'All pairs', timeframe: '4h',
    status: 'active', lastRun: '2026-04-29',
    lastResult: { totalReturnPct: 18.2, sharpe: 2.1, maxDrawdown: -11.4, winRate: 65, totalTrades: 52, passed: true  },
    equitySpark: [100,102,104,103,106,108,107,110,112,118],
  },
  {
    id: 'cmf', name: 'Cascading Momentum Filter', symbol: 'SOL/XRP/AVAX', timeframe: '1h',
    status: 'active', lastRun: '2026-04-28',
    lastResult: { totalReturnPct: 14.1, sharpe: 1.9, maxDrawdown: -9.8,  winRate: 68, totalTrades: 29, passed: true  },
    equitySpark: [100,101,103,102,105,104,107,106,110,114],
  },
  {
    id: 'ema', name: 'EMA Trend RSI', symbol: 'ETH/BNB', timeframe: '1h',
    status: 'active', lastRun: '2026-04-28',
    lastResult: { totalReturnPct: 8.6,  sharpe: 1.2, maxDrawdown: -14.1, winRate: 55, totalTrades: 41, passed: false },
    equitySpark: [100,99,101,100,102,101,103,102,104,108],
  },
  {
    id: 'bsb', name: 'BB Squeeze Breakout', symbol: 'BTC', timeframe: '15m',
    status: 'paused', lastRun: '2026-04-27',
    lastResult: { totalReturnPct: 11.4, sharpe: 1.5, maxDrawdown: -12.3, winRate: 61, totalTrades: 18, passed: true  },
    equitySpark: [100,101,102,101,103,102,104,103,105,111],
  },
  {
    id: 'bsm', name: 'BB Squeeze Momentum', symbol: 'ETH', timeframe: '15m',
    status: 'paused', lastRun: '2026-04-27',
    lastResult: { totalReturnPct: 9.2,  sharpe: 1.3, maxDrawdown: -13.7, winRate: 58, totalTrades: 12, passed: false },
    equitySpark: [100,101,100,102,101,103,102,104,103,109],
  },
  {
    id: 'don', name: 'Donchian ATR', symbol: 'BTC/SOL', timeframe: '4h',
    status: 'active', lastRun: '2026-04-26',
    lastResult: { totalReturnPct: 16.2, sharpe: 1.7, maxDrawdown: -10.5, winRate: 63, totalTrades: 27, passed: true  },
    equitySpark: [100,102,101,104,103,106,105,108,107,116],
  },
  {
    id: 'ramr', name: 'Regime-Aware Mean Reversion', symbol: 'ETH/BNB', timeframe: '1h',
    status: 'stopped', lastRun: '2026-04-20',
    lastResult: { totalReturnPct: -2.1, sharpe: 0.3, maxDrawdown: -18.9, winRate: 44, totalTrades: 9,  passed: false },
    equitySpark: [100,99,98,97,98,97,96,97,96,98],
  },
  {
    id: 'super', name: 'Supertrend Volume MACD', symbol: 'BTC/DOGE', timeframe: '1h',
    status: 'active', lastRun: '2026-04-29',
    lastResult: { totalReturnPct: 15.8, sharpe: 1.6, maxDrawdown: -11.2, winRate: 60, totalTrades: 33, passed: true  },
    equitySpark: [100,101,103,102,105,104,107,106,109,115],
  },
];

const STATUS_BADGE: Record<string, 'success' | 'warning' | 'neutral'> = {
  active:  'success',
  paused:  'warning',
  stopped: 'neutral',
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function BacktestResultsPage() {
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);

  const totalPassed = STRATEGIES.filter(s => s.lastResult?.passed).length;
  const avgSharpe   = STRATEGIES
    .filter(s => s.lastResult)
    .reduce((sum, s) => sum + (s.lastResult?.sharpe ?? 0), 0) / STRATEGIES.filter(s => s.lastResult).length;

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
          <h1 className="text-2xl font-semibold text-paper-100">Backtest Results</h1>
          <p className="text-sm text-paper-400 mt-1">Per-strategy backtest performance &mdash; click any row to view full results</p>
        </div>
      </motion.div>

      {/* Summary Strip */}
      <motion.div variants={fadeInUp}>
        <GlassCard className="flex flex-wrap gap-6 p-4">
          <div>
            <div className="text-xs text-paper-400 mb-0.5">Total Strategies</div>
            <div className="text-xl font-semibold text-paper-100">{STRATEGIES.length}</div>
          </div>
          <div className="w-px bg-obsidian-200 hidden sm:block" />
          <div>
            <div className="text-xs text-paper-400 mb-0.5">Passed Validation</div>
            <div className="text-xl font-semibold text-gain">{totalPassed} / {STRATEGIES.length}</div>
          </div>
          <div className="w-px bg-obsidian-200 hidden sm:block" />
          <div>
            <div className="text-xs text-paper-400 mb-0.5">Avg Sharpe</div>
            <div className="text-xl font-semibold text-paper-100">{avgSharpe.toFixed(2)}</div>
          </div>
          <div className="w-px bg-obsidian-200 hidden sm:block" />
          <div>
            <div className="text-xs text-paper-400 mb-0.5">Best Performer</div>
            <div className="text-xl font-semibold text-gain">BTF +24.8%</div>
          </div>
        </GlassCard>
      </motion.div>

      {/* Strategy Cards */}
      <motion.div variants={staggerContainer} className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {STRATEGIES.map(s => (
          <motion.div key={s.id} variants={fadeInUp}>
            <GlassCard
              className="cursor-pointer hover:border-turquoise/30 transition-all group"
              onClick={() => s.lastResult && setSelectedStrategyId(s.id)}
            >
              {/* Card header */}
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-paper-100 truncate">{s.name}</h3>
                    {s.lastResult && (
                      <Badge variant={s.lastResult.passed ? 'success' : 'danger'} size="sm">
                        {s.lastResult.passed ? 'PASS' : 'FAIL'}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-paper-400 mt-0.5">{s.symbol} &bull; {s.timeframe}</p>
                </div>
                <Badge variant={STATUS_BADGE[s.status]} size="sm" dot>{s.status}</Badge>
              </div>

              {/* Sparkline */}
              {s.lastResult ? (
                <>
                  <div className="flex items-center justify-between mb-2">
                    <SparklineChart
                      data={s.equitySpark}
                      width={120}
                      height={32}
                      color={s.lastResult.totalReturnPct >= 0 ? 'gain' : 'loss'}
                    />
                    <div className="text-right">
                      <div className={`text-lg font-bold ${s.lastResult.totalReturnPct >= 0 ? 'text-gain' : 'text-loss'}`}>
                        {s.lastResult.totalReturnPct >= 0 ? '+' : ''}{s.lastResult.totalReturnPct.toFixed(1)}%
                      </div>
                      <div className="text-xs text-paper-400">total return</div>
                    </div>
                  </div>

                  {/* Metrics grid */}
                  <div className="grid grid-cols-4 gap-2 py-2 border-t border-obsidian-200/50 mb-3">
                    <div className="text-center">
                      <div className="text-xs font-medium text-paper-200">{s.lastResult.sharpe.toFixed(1)}</div>
                      <div className="text-xs text-paper-500">Sharpe</div>
                    </div>
                    <div className="text-center">
                      <div className={`text-xs font-medium ${s.lastResult.maxDrawdown < -15 ? 'text-loss' : 'text-paper-200'}`}>
                        {s.lastResult.maxDrawdown}%
                      </div>
                      <div className="text-xs text-paper-500">Max DD</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xs font-medium text-paper-200">{s.lastResult.winRate}%</div>
                      <div className="text-xs text-paper-500">Win Rate</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xs font-medium text-paper-200">{s.lastResult.totalTrades}</div>
                      <div className="text-xs text-paper-500">Trades</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1 text-xs text-paper-400">
                      <Clock className="w-3 h-3" />
                      <span>Last run: {s.lastRun}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-turquoise group-hover:text-turquoise/80 px-2"
                      onClick={e => { e.stopPropagation(); setSelectedStrategyId(s.id); }}
                    >
                      <BarChart2 className="w-3.5 h-3.5 mr-1" /> View Results
                    </Button>
                  </div>
                </>
              ) : (
                <div className="py-4 text-center">
                  <p className="text-xs text-paper-400 mb-3">No backtest results yet</p>
                  <Button variant="ghost" size="sm" className="text-xs">
                    <Play className="w-3.5 h-3.5 mr-1" /> Run Backtest
                  </Button>
                </div>
              )}
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>

      {/* Results Modal */}
      <BacktestResultsModal
        isOpen={selectedStrategyId !== null}
        onClose={() => setSelectedStrategyId(null)}
        strategyId={selectedStrategyId ?? undefined}
      />
    </motion.div>
  );
}
