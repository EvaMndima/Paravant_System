import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, TrendingUp, TrendingDown, Activity, Clock, Zap,
  ArrowUpRight, ArrowDownRight, Minus, BarChart2,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { AreaChart } from '@/components/charts/AreaChart';
import { cn, formatCurrency, formatNumber } from '@/lib/utils';
import type { StrategyCardProps, StrategyStatus } from './StrategyCard';
import type { AreaChartData } from '@/components/charts/AreaChart';

export interface StrategySignalEntry {
  id: string;
  action: 'buy' | 'sell' | 'hold';
  symbol: string;
  price: number;
  time: string;
  outcome?: 'win' | 'loss' | 'pending';
  pnlPct?: number;
}

export interface StrategyDetailData extends StrategyCardProps {
  description: string;
  activeSymbols: string[];
  avgTradeDuration: string;
  bestTrade: number;
  worstTrade: number;
  currentStreak: number;
  streakType: 'win' | 'loss';
  totalTrades: number;
  pnlCurve: AreaChartData[];
  recentSignals: StrategySignalEntry[];
}

export interface StrategyDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  strategy?: StrategyDetailData;
}

// Generate a PnL curve seeded from strategy performance
function buildPnlCurve(basePnl: number, winRate: number): AreaChartData[] {
  const data: AreaChartData[] = [];
  let equity = 10000;
  const days = 90;
  for (let i = 0; i <= days; i += 3) {
    const isWin = Math.random() < winRate / 100;
    const change = isWin ? Math.random() * 0.04 : -Math.random() * 0.025;
    equity = equity * (1 + change);
    const d = new Date(2024, 9, 1); // Oct 1 2024
    d.setDate(d.getDate() + i);
    data.push({
      date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: Math.round(equity * 100) / 100,
    });
  }
  // Nudge final value toward basePnl direction
  if (basePnl < 0 && data.length > 0) {
    const last = data[data.length - 1];
    data[data.length - 1] = { ...last, value: last.value * 0.88 };
  }
  return data;
}

const mockStrategy: StrategyDetailData = {
  id: 'strategy-detail-mock',
  name: 'Momentum_MACD',
  type: 'momentum',
  status: 'active',
  performance: { pnl: 3420, winRate: 62.5, sharpe: 1.87 },
  lastSignal: { action: 'buy', symbol: 'BTCUSDT', time: '2m ago' },
  description: 'MACD crossover strategy that trades momentum shifts on BTC and ETH. Enters on signal line crossover with volume confirmation.',
  activeSymbols: ['BTCUSDT', 'ETHUSDT'],
  avgTradeDuration: '4.2 days',
  bestTrade: 1240,
  worstTrade: -520,
  currentStreak: 4,
  streakType: 'win',
  totalTrades: 48,
  pnlCurve: buildPnlCurve(3420, 62.5),
  recentSignals: [
    { id: 's1', action: 'buy', symbol: 'BTCUSDT', price: 96400, time: '2m ago', outcome: 'pending' },
    { id: 's2', action: 'sell', symbol: 'ETHUSDT', price: 3280, time: '1h ago', outcome: 'win', pnlPct: 2.4 },
    { id: 's3', action: 'buy', symbol: 'BTCUSDT', price: 94100, time: '6h ago', outcome: 'win', pnlPct: 3.1 },
    { id: 's4', action: 'sell', symbol: 'ETHUSDT', price: 3350, time: '1d ago', outcome: 'loss', pnlPct: -1.8 },
    { id: 's5', action: 'buy', symbol: 'BTCUSDT', price: 91200, time: '2d ago', outcome: 'win', pnlPct: 4.7 },
  ],
};

const statusColors: Record<StrategyStatus, string> = {
  active: 'bg-gain',
  paused: 'bg-warning',
  error: 'bg-loss',
  training: 'bg-info',
};

const actionColors: Record<string, string> = {
  buy: 'text-gain',
  sell: 'text-loss',
  hold: 'text-warning',
};

const outcomeConfig = {
  win: { icon: ArrowUpRight, color: 'text-gain' },
  loss: { icon: ArrowDownRight, color: 'text-loss' },
  pending: { icon: Minus, color: 'text-warning' },
};

interface StatRowProps { label: string; value: string; accent?: boolean; positive?: boolean; negative?: boolean }
const StatRow: React.FC<StatRowProps> = ({ label, value, positive, negative }) => (
  <div className="flex items-center justify-between py-2 border-b border-deep-teal-800/5 dark:border-white/5 last:border-0">
    <span className="text-xs font-sans text-obsidian-400/60 dark:text-paper-100/60">{label}</span>
    <span className={cn(
      'text-sm font-mono font-medium',
      positive ? 'text-gain' : negative ? 'text-loss' : 'text-obsidian-400 dark:text-paper-100'
    )}>
      {value}
    </span>
  </div>
);

export const StrategyDetailDrawer: React.FC<StrategyDetailDrawerProps> = ({
  isOpen,
  onClose,
  strategy,
}) => {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); return () => setMounted(false); }, []);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
      window.addEventListener('keydown', handler);
      return () => {
        document.body.style.overflow = '';
        window.removeEventListener('keydown', handler);
      };
    } else {
      document.body.style.overflow = '';
    }
  }, [isOpen, onClose]);

  const s = strategy ?? mockStrategy;
  const pnlCurve = useMemo(() => s.pnlCurve, [s]);

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[90] flex justify-end">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="absolute inset-0 bg-obsidian-400/50 backdrop-blur-sm"
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className={cn(
              'relative w-full max-w-md h-full overflow-y-auto z-10',
              'bg-paper-100 dark:bg-obsidian-300',
              'border-l border-deep-teal-800/10 dark:border-white/10',
              'shadow-2xl custom-scrollbar',
            )}
          >
            {/* Header */}
            <div className="sticky top-0 z-20 bg-paper-100/95 dark:bg-obsidian-300/95 backdrop-blur-xl border-b border-deep-teal-800/5 dark:border-white/5 px-5 py-4">
              <div className="flex items-start justify-between">
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <div className={cn('relative flex h-2.5 w-2.5')}>
                      {(s.status === 'active' || s.status === 'training') && (
                        <span className={cn('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', statusColors[s.status])} />
                      )}
                      <span className={cn('relative inline-flex rounded-full h-2.5 w-2.5', statusColors[s.status])} />
                    </div>
                    <h2 className="text-xl font-display font-semibold text-deep-teal-800 dark:text-paper-100">
                      {s.name}
                    </h2>
                  </div>
                  <p className="text-sm font-sans text-obsidian-400/60 dark:text-paper-100/60 max-w-xs">
                    {s.description}
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="rounded-full p-2 text-obsidian-400/50 hover:bg-deep-teal-800/5 hover:text-deep-teal-800 dark:text-paper-100/50 dark:hover:bg-white/10 dark:hover:text-paper-100 transition-colors focus:outline-none shrink-0 mt-0.5"
                  aria-label="Close drawer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-5 space-y-6">
              {/* Active symbols */}
              <div className="flex items-center gap-2 flex-wrap">
                {s.activeSymbols.map(sym => (
                  <Badge key={sym} variant="outline" size="sm">{sym.replace('USDT', '/USDT')}</Badge>
                ))}
                <Badge variant={s.performance.pnl >= 0 ? 'success' : 'danger'} size="sm">
                  {s.performance.pnl >= 0 ? '+' : ''}{formatCurrency(s.performance.pnl)} P&L
                </Badge>
              </div>

              {/* Quick stats */}
              <GlassCard variant="subtle" padding="sm">
                <div className="grid grid-cols-3 divide-x divide-deep-teal-800/10 dark:divide-white/10">
                  <div className="text-center px-2">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-1.5">Win Rate</div>
                    <div className="text-lg font-mono font-bold text-obsidian-400 dark:text-paper-100">{s.performance.winRate}%</div>
                  </div>
                  <div className="text-center px-2">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-1.5">Sharpe</div>
                    <div className="text-lg font-mono font-bold text-obsidian-400 dark:text-paper-100">{s.performance.sharpe.toFixed(2)}</div>
                  </div>
                  <div className="text-center px-2">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-1.5">Streak</div>
                    <div className={cn('text-lg font-mono font-bold', s.streakType === 'win' ? 'text-gain' : 'text-loss')}>
                      {s.streakType === 'win' ? '+' : '-'}{s.currentStreak}
                    </div>
                  </div>
                </div>
              </GlassCard>

              {/* 90D PnL curve */}
              <div>
                <h3 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-3 flex items-center gap-2">
                  <BarChart2 className="w-3.5 h-3.5" />
                  90-Day Performance
                </h3>
                <AreaChart
                  data={pnlCurve}
                  height={160}
                  showGrid={false}
                  gradientId="strategy-detail-curve"
                  showTooltip={true}
                />
              </div>

              {/* Detailed stats */}
              <div>
                <h3 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-3 flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5" />
                  Statistics
                </h3>
                <GlassCard variant="subtle" padding="sm">
                  <StatRow label="Total Trades" value={String(s.totalTrades)} />
                  <StatRow label="Avg Trade Duration" value={s.avgTradeDuration} />
                  <StatRow label="Best Trade" value={formatCurrency(s.bestTrade)} positive />
                  <StatRow label="Worst Trade" value={formatCurrency(s.worstTrade)} negative />
                </GlassCard>
              </div>

              {/* Recent signals */}
              <div>
                <h3 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-3 flex items-center gap-2">
                  <Zap className="w-3.5 h-3.5" />
                  Recent Signals
                </h3>
                <div className="space-y-2">
                  {s.recentSignals.map(sig => {
                    const outcomeIcon = outcomeConfig[sig.outcome ?? 'pending'];
                    const OutcomeIcon = outcomeIcon.icon;
                    return (
                      <div
                        key={sig.id}
                        className="flex items-center gap-3 p-3 rounded-xl bg-deep-teal-800/5 dark:bg-white/5"
                      >
                        <div className={cn('text-xs font-mono font-bold uppercase w-8 shrink-0', actionColors[sig.action])}>
                          {sig.action}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-mono text-sm font-medium text-obsidian-400 dark:text-paper-100">
                            {sig.symbol.replace('USDT', '')}
                          </div>
                          <div className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">
                            @ {formatCurrency(sig.price)}
                          </div>
                        </div>
                        {sig.outcome && (
                          <div className={cn('flex items-center gap-1 text-sm font-mono font-bold', outcomeIcon.color)}>
                            <OutcomeIcon className="w-4 h-4" />
                            {sig.pnlPct !== undefined ? `${sig.pnlPct > 0 ? '+' : ''}${sig.pnlPct}%` : 'Live'}
                          </div>
                        )}
                        <div className="flex items-center gap-1 text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 shrink-0">
                          <Clock className="w-3 h-3" />
                          {sig.time}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Spacer so last item isn't flush with bottom */}
              <div className="h-4" />
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
};
