import React, { useState, useMemo } from 'react';
import {
  TrendingUp, TrendingDown, BarChart2, Target, Award, AlertTriangle,
  ChevronDown, ChevronUp,
} from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { AreaChart } from '@/components/charts/AreaChart';
import { cn, formatCurrency, formatNumber } from '@/lib/utils';
import type { AreaChartData } from '@/components/charts/AreaChart';

export interface BacktestTrade {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  entryDate: string;
  exitDate: string;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPct: number;
  duration: string;
}

export interface BacktestResult {
  strategyName: string;
  symbol: string;
  period: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  finalCapital: number;
  totalReturn: number;
  totalReturnPct: number;
  annualizedReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  equityCurve: AreaChartData[];
  trades: BacktestTrade[];
}

export interface BacktestResultsModalProps {
  isOpen: boolean;
  onClose: () => void;
  result?: BacktestResult;
}

// Generate a realistic equity curve from a starting capital
function generateEquityCurve(
  start: number,
  returnPct: number,
  days: number
): AreaChartData[] {
  const data: AreaChartData[] = [];
  let value = start;
  const monthlyReturn = Math.pow(1 + returnPct / 100, 1 / (days / 30)) - 1;

  for (let i = 0; i <= days; i += Math.ceil(days / 60)) {
    const drift = monthlyReturn / 30;
    const noise = (Math.random() - 0.45) * 0.015;
    value = value * (1 + drift + noise);
    const date = new Date(2024, 0, 1);
    date.setDate(date.getDate() + i);
    data.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: Math.round(value * 100) / 100,
    });
  }
  return data;
}

// Mock result used when no real result is passed
const mockResult: BacktestResult = {
  strategyName: 'Momentum_MACD',
  symbol: 'BTCUSDT',
  period: '12M',
  startDate: 'Jan 1, 2024',
  endDate: 'Dec 31, 2024',
  initialCapital: 10000,
  finalCapital: 13420,
  totalReturn: 3420,
  totalReturnPct: 34.2,
  annualizedReturn: 34.2,
  maxDrawdown: -12.4,
  sharpeRatio: 1.87,
  winRate: 62.5,
  totalTrades: 48,
  winningTrades: 30,
  losingTrades: 18,
  avgWin: 285,
  avgLoss: -142,
  profitFactor: 2.01,
  equityCurve: generateEquityCurve(10000, 34.2, 365),
  trades: [
    { id: '1', symbol: 'BTCUSDT', side: 'long', entryDate: 'Jan 3', exitDate: 'Jan 8', entryPrice: 43250, exitPrice: 45100, pnl: 428, pnlPct: 4.28, duration: '5d' },
    { id: '2', symbol: 'BTCUSDT', side: 'short', entryDate: 'Jan 12', exitDate: 'Jan 15', entryPrice: 44800, exitPrice: 43500, pnl: 290, pnlPct: 2.9, duration: '3d' },
    { id: '3', symbol: 'ETHUSDT', side: 'long', entryDate: 'Jan 18', exitDate: 'Jan 22', entryPrice: 2580, exitPrice: 2490, pnl: -174, pnlPct: -3.49, duration: '4d' },
    { id: '4', symbol: 'BTCUSDT', side: 'long', entryDate: 'Feb 2', exitDate: 'Feb 9', entryPrice: 42100, exitPrice: 44600, pnl: 594, pnlPct: 5.94, duration: '7d' },
    { id: '5', symbol: 'BNBUSDT', side: 'long', entryDate: 'Feb 15', exitDate: 'Feb 19', entryPrice: 312, exitPrice: 298, pnl: -224, pnlPct: -4.49, duration: '4d' },
    { id: '6', symbol: 'BTCUSDT', side: 'short', entryDate: 'Mar 5', exitDate: 'Mar 8', entryPrice: 68200, exitPrice: 65800, pnl: 570, pnlPct: 3.52, duration: '3d' },
  ],
};

interface MetricTileProps {
  label: string;
  value: string;
  subtext?: string;
  positive?: boolean;
  negative?: boolean;
  icon: React.ElementType;
}

const MetricTile: React.FC<MetricTileProps> = ({ label, value, subtext, positive, negative, icon: Icon }) => (
  <div className="p-4 rounded-xl bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/5 dark:border-white/5">
    <div className="flex items-center gap-2 mb-2">
      <Icon className="w-3.5 h-3.5 text-obsidian-400/40 dark:text-paper-100/40" />
      <span className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40">
        {label}
      </span>
    </div>
    <div className={cn(
      'font-mono font-bold text-lg leading-none',
      positive ? 'text-gain' : negative ? 'text-loss' : 'text-obsidian-400 dark:text-paper-100'
    )}>
      {value}
    </div>
    {subtext && (
      <div className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40 mt-1">{subtext}</div>
    )}
  </div>
);

export const BacktestResultsModal: React.FC<BacktestResultsModalProps> = ({
  isOpen,
  onClose,
  result,
}) => {
  const r = result ?? mockResult;
  const [showTrades, setShowTrades] = useState(false);

  const winRateColor = r.winRate >= 55 ? 'success' : r.winRate >= 45 ? 'warning' : 'danger';

  const equityCurve = useMemo(() => r.equityCurve, [r]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Backtest: ${r.strategyName}`}
      description={`${r.symbol} — ${r.startDate} to ${r.endDate}`}
      size="lg"
    >
      <div className="space-y-6">
        {/* Summary badges */}
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" size="sm">{r.period} period</Badge>
          <Badge variant="outline" size="sm">{r.totalTrades} trades</Badge>
          <Badge variant={winRateColor} size="sm" dot>
            {r.winRate}% win rate
          </Badge>
          <Badge variant={r.totalReturnPct >= 0 ? 'success' : 'danger'} size="sm">
            {r.totalReturnPct >= 0 ? '+' : ''}{formatNumber(r.totalReturnPct)}% return
          </Badge>
        </div>

        {/* Core metrics grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricTile
            label="Total Return"
            value={`${r.totalReturnPct >= 0 ? '+' : ''}${formatNumber(r.totalReturnPct)}%`}
            subtext={formatCurrency(r.totalReturn)}
            positive={r.totalReturnPct >= 0}
            negative={r.totalReturnPct < 0}
            icon={TrendingUp}
          />
          <MetricTile
            label="Max Drawdown"
            value={`${formatNumber(r.maxDrawdown)}%`}
            subtext="Peak-to-trough"
            negative={true}
            icon={TrendingDown}
          />
          <MetricTile
            label="Sharpe Ratio"
            value={formatNumber(r.sharpeRatio)}
            subtext={r.sharpeRatio >= 1.5 ? 'Excellent' : r.sharpeRatio >= 1 ? 'Good' : 'Below avg'}
            positive={r.sharpeRatio >= 1}
            icon={Award}
          />
          <MetricTile
            label="Profit Factor"
            value={formatNumber(r.profitFactor)}
            subtext={`${r.winningTrades}W / ${r.losingTrades}L`}
            positive={r.profitFactor >= 1.5}
            icon={Target}
          />
        </div>

        {/* Secondary metrics */}
        <div className="grid grid-cols-3 gap-3">
          <MetricTile label="Avg Win" value={formatCurrency(r.avgWin)} positive icon={BarChart2} />
          <MetricTile label="Avg Loss" value={formatCurrency(Math.abs(r.avgLoss))} negative icon={AlertTriangle} />
          <MetricTile label="Final Capital" value={formatCurrency(r.finalCapital)} icon={Award} />
        </div>

        {/* Equity curve */}
        <div>
          <h4 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-3">
            Equity Curve
          </h4>
          <AreaChart
            data={equityCurve}
            height={200}
            showGrid={true}
            gradientId="backtest-equity"
            showTooltip={true}
          />
        </div>

        {/* Trade log toggle */}
        <div>
          <button
            onClick={() => setShowTrades(v => !v)}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-deep-teal-800/5 dark:bg-white/5 hover:bg-deep-teal-800/10 dark:hover:bg-white/10 transition-colors"
          >
            <span className="text-xs font-mono uppercase tracking-widest text-obsidian-400/60 dark:text-paper-100/60">
              Trade Log ({r.trades.length} shown)
            </span>
            {showTrades ? <ChevronUp className="w-4 h-4 text-obsidian-400/40 dark:text-paper-100/40" /> : <ChevronDown className="w-4 h-4 text-obsidian-400/40 dark:text-paper-100/40" />}
          </button>

          {showTrades && (
            <div className="mt-2 rounded-xl overflow-hidden border border-deep-teal-800/5 dark:border-white/5">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="bg-deep-teal-800/5 dark:bg-white/5 border-b border-deep-teal-800/5 dark:border-white/5">
                    {['Symbol', 'Side', 'Entry', 'Exit', 'Duration', 'P&L'].map(h => (
                      <th key={h} className="px-3 py-2 text-left text-[10px] uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {r.trades.map(trade => (
                    <tr
                      key={trade.id}
                      className="border-b border-deep-teal-800/5 dark:border-white/5 last:border-0 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors"
                    >
                      <td className="px-3 py-2.5 font-semibold text-obsidian-400 dark:text-paper-100">
                        {trade.symbol.replace('USDT', '')}
                      </td>
                      <td className="px-3 py-2.5">
                        <Badge variant={trade.side === 'long' ? 'success' : 'danger'} size="sm">
                          {trade.side}
                        </Badge>
                      </td>
                      <td className="px-3 py-2.5 text-obsidian-400/60 dark:text-paper-100/60">{trade.entryDate}</td>
                      <td className="px-3 py-2.5 text-obsidian-400/60 dark:text-paper-100/60">{trade.exitDate}</td>
                      <td className="px-3 py-2.5 text-obsidian-400/50 dark:text-paper-100/50">{trade.duration}</td>
                      <td className={cn('px-3 py-2.5 font-bold', trade.pnl >= 0 ? 'text-gain' : 'text-loss')}>
                        {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                        <span className="text-[10px] ml-1 opacity-60">({trade.pnlPct >= 0 ? '+' : ''}{trade.pnlPct}%)</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};
