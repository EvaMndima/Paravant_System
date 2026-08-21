import React, { useState, useMemo } from 'react';
import { useBacktestResults } from '@/hooks/useBacktestResults';
import {
  TrendingUp, TrendingDown, BarChart2, Target, Award, AlertTriangle,
  ShieldCheck, ShieldAlert, Activity, DollarSign, Percent, Clock,
  RefreshCw, ArrowUpDown,
} from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { SVGAreaChart } from '@/components/charts/SVGAreaChart';
import { DrawdownChart } from '@/components/dashboard/DrawdownChart';
import { cn, formatCurrency } from '@/lib/utils';
import type { AreaChartData } from '@/components/charts/AreaChart';
import type { DrawdownDataPoint } from '@/components/dashboard/DrawdownChart';
import { SyntheticDataBadge } from '@/components/ui/SyntheticDataBadge';
import { requiresSyntheticLabel, resolveProvenance } from '@/lib/provenance';
import type { ProvenanceProps } from '@/lib/provenance';

// ── Types ────────────────────────────────────────────────────────────────────

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
  maxDrawdown: number;         // negative pct, e.g. -12.4
  sharpeRatio: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;             // negative $
  profitFactor: number;
  equityCurve: AreaChartData[];
  trades: BacktestTrade[];
  // Extended (optional — filled by API or derived)
  sortinoRatio?: number;
  calmarRatio?: number;        // annualizedReturn / |maxDrawdown|
  expectancy?: number;         // (winRate * avgWin) + (lossRate * avgLoss)
  recoveryFactor?: number;     // totalReturnPct / |maxDrawdown|
  maxConsecWins?: number;
  maxConsecLosses?: number;
  maxDrawdownDuration?: number; // in data periods
  passedValidation?: boolean;
  validationErrors?: string[];
}

export interface BacktestResultsModalProps extends ProvenanceProps {
  isOpen: boolean;
  onClose: () => void;
  result?: BacktestResult;
  strategyId?: string;
}

// ── Derivation helpers ────────────────────────────────────────────────────────

interface DailyPnlRow {
  date: string;
  pnl: number;
  pnlPct: number;
  cumulative: number;
  drawdownPct: number;
}

function deriveDrawdownSeries(equity: AreaChartData[]): DrawdownDataPoint[] {
  if (!equity.length) return [];
  let peak = equity[0].value;
  return equity.map(pt => {
    if (pt.value > peak) peak = pt.value;
    const dd = peak > 0 ? ((pt.value - peak) / peak) * 100 : 0;
    return { date: pt.date, drawdown: Math.min(0, +dd.toFixed(2)) };
  });
}

function deriveDailyPnl(equity: AreaChartData[]): DailyPnlRow[] {
  if (!equity.length) return [];
  let peak = equity[0].value;
  return equity.map((pt, i) => {
    const prev    = i === 0 ? pt.value : equity[i - 1].value;
    const pnl     = pt.value - prev;
    const pnlPct  = prev > 0 ? (pnl / prev) * 100 : 0;
    const cumulative = pt.value - equity[0].value;
    if (pt.value > peak) peak = pt.value;
    const drawdownPct = peak > 0 ? ((pt.value - peak) / peak) * 100 : 0;
    return {
      date: pt.date,
      pnl:         +pnl.toFixed(2),
      pnlPct:      +pnlPct.toFixed(2),
      cumulative:  +cumulative.toFixed(2),
      drawdownPct: +drawdownPct.toFixed(2),
    };
  });
}

function deriveCumulativePnlCurve(equity: AreaChartData[]): AreaChartData[] {
  if (!equity.length) return [];
  const base = equity[0].value;
  return equity.map(pt => ({ date: pt.date, value: +(pt.value - base).toFixed(2) }));
}

function maxDrawdownDuration(ddSeries: DrawdownDataPoint[]): number {
  let maxLen = 0, curLen = 0;
  for (const pt of ddSeries) {
    if (pt.drawdown < 0) { curLen++; maxLen = Math.max(maxLen, curLen); }
    else curLen = 0;
  }
  return maxLen;
}

// ── Mock equity curve ─────────────────────────────────────────────────────────

function generateEquityCurve(start: number, returnPct: number, days: number): AreaChartData[] {
  const data: AreaChartData[] = [];
  let value = start;
  const drift = (returnPct / 100) / (days / 30) / 30;
  for (let i = 0; i <= days; i += Math.ceil(days / 60)) {
    const noise = (Math.random() - 0.45) * 0.015;
    value = value * (1 + drift + noise);
    const d = new Date(2024, 0, 1);
    d.setDate(d.getDate() + i);
    data.push({
      date:  d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: Math.round(value * 100) / 100,
    });
  }
  return data;
}

const mockEquity = generateEquityCurve(10000, 34.2, 365);

const mockResult: BacktestResult = {
  strategyName:      'Momentum_MACD',
  symbol:            'BTCUSDT',
  period:            '12M',
  startDate:         'Jan 1, 2024',
  endDate:           'Dec 31, 2024',
  initialCapital:    10000,
  finalCapital:      13420,
  totalReturn:       3420,
  totalReturnPct:    34.2,
  annualizedReturn:  34.2,
  maxDrawdown:       -12.4,
  sharpeRatio:       1.87,
  sortinoRatio:      2.31,
  calmarRatio:       2.76,
  expectancy:        124.88,
  recoveryFactor:    2.76,
  winRate:           62.5,
  totalTrades:       48,
  winningTrades:     30,
  losingTrades:      18,
  avgWin:            285,
  avgLoss:           -142,
  profitFactor:      2.01,
  maxConsecWins:     5,
  maxConsecLosses:   3,
  maxDrawdownDuration: 28,
  passedValidation:  true,
  validationErrors:  [],
  equityCurve: mockEquity,
  trades: [
    { id: '1', symbol: 'BTCUSDT', side: 'long',  entryDate: 'Jan 3',  exitDate: 'Jan 8',  entryPrice: 43250, exitPrice: 45100, pnl:  428, pnlPct:  4.28, duration: '5d' },
    { id: '2', symbol: 'BTCUSDT', side: 'short', entryDate: 'Jan 12', exitDate: 'Jan 15', entryPrice: 44800, exitPrice: 43500, pnl:  290, pnlPct:  2.90, duration: '3d' },
    { id: '3', symbol: 'ETHUSDT', side: 'long',  entryDate: 'Jan 18', exitDate: 'Jan 22', entryPrice: 2580,  exitPrice: 2490,  pnl: -174, pnlPct: -3.49, duration: '4d' },
    { id: '4', symbol: 'BTCUSDT', side: 'long',  entryDate: 'Feb 2',  exitDate: 'Feb 9',  entryPrice: 42100, exitPrice: 44600, pnl:  594, pnlPct:  5.94, duration: '7d' },
    { id: '5', symbol: 'BNBUSDT', side: 'long',  entryDate: 'Feb 15', exitDate: 'Feb 19', entryPrice: 312,   exitPrice: 298,   pnl: -224, pnlPct: -4.49, duration: '4d' },
    { id: '6', symbol: 'BTCUSDT', side: 'short', entryDate: 'Mar 5',  exitDate: 'Mar 8',  entryPrice: 68200, exitPrice: 65800, pnl:  570, pnlPct:  3.52, duration: '3d' },
  ],
};

// ── Sub-components ────────────────────────────────────────────────────────────

interface MetricTileProps {
  label: string;
  value: string;
  subtext?: string;
  positive?: boolean;
  negative?: boolean;
  neutral?: boolean;
  icon: React.ElementType;
  tooltip?: string;
}

const MetricTile: React.FC<MetricTileProps> = ({
  label, value, subtext, positive, negative, icon: Icon,
}) => (
  <div className="p-3.5 rounded-xl bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/5 dark:border-white/5">
    <div className="flex items-center gap-2 mb-2">
      <Icon className="w-3 h-3 text-obsidian-400/40 dark:text-paper-100/40 shrink-0" />
      <span className="text-[9px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 leading-none">
        {label}
      </span>
    </div>
    <div className={cn(
      'font-mono font-bold text-base leading-none',
      positive  ? 'text-gain'
      : negative ? 'text-loss'
      :            'text-obsidian-400 dark:text-paper-100'
    )}>
      {value}
    </div>
    {subtext && (
      <div className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40 mt-1 leading-none">
        {subtext}
      </div>
    )}
  </div>
);

// ── Tab: Overview ─────────────────────────────────────────────────────────────

const OverviewTab: React.FC<{ r: BacktestResult }> = ({ r }) => {
  const expectancy = r.expectancy ??
    (r.winRate / 100) * r.avgWin + (1 - r.winRate / 100) * (r.avgLoss);

  const calmar = r.calmarRatio ??
    (r.maxDrawdown !== 0 ? r.annualizedReturn / Math.abs(r.maxDrawdown) : 0);

  const sortino   = r.sortinoRatio  ?? r.sharpeRatio * 1.2;
  const recovery  = r.recoveryFactor ?? (r.maxDrawdown !== 0 ? r.totalReturnPct / Math.abs(r.maxDrawdown) : 0);
  const maxCWins  = r.maxConsecWins  ?? Math.floor(r.winningTrades * 0.2);
  const maxCLoss  = r.maxConsecLosses ?? Math.floor(r.losingTrades * 0.25);
  const ddDur     = r.maxDrawdownDuration ?? 0;
  const passed    = r.passedValidation ?? true;
  const errors    = r.validationErrors ?? [];

  const sharpeLabel  = r.sharpeRatio  >= 1.5 ? 'Excellent'   : r.sharpeRatio  >= 1 ? 'Acceptable' : 'Below avg';
  const sortinoLabel = sortino        >= 2.0 ? 'Excellent'   : sortino        >= 1.2 ? 'Good'      : 'Marginal';
  const calmarLabel  = calmar         >= 2   ? 'Strong'      : calmar         >= 1   ? 'Adequate'  : 'Weak';
  const pfLabel      = r.profitFactor >= 2   ? 'Excellent'   : r.profitFactor >= 1.5 ? 'Good'      : 'Marginal';

  return (
    <div className="space-y-5">
      {/* Validation banner */}
      {!passed && (
        <div className="flex items-start gap-3 p-3 rounded-xl bg-loss/10 border border-loss/20">
          <ShieldAlert className="w-4 h-4 text-loss mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-mono font-bold text-loss">Strategy failed validation</p>
            {errors.map((e, i) => (
              <p key={i} className="text-[10px] font-sans text-loss/70 mt-0.5">{e}</p>
            ))}
            <p className="text-[10px] font-sans text-obsidian-400/50 dark:text-paper-100/50 mt-1">
              You may still deploy with manual override — review metrics below before deciding.
            </p>
          </div>
        </div>
      )}
      {passed && (
        <div className="flex items-center gap-2 p-2.5 rounded-xl bg-gain/10 border border-gain/20">
          <ShieldCheck className="w-4 h-4 text-gain shrink-0" />
          <p className="text-xs font-mono text-gain font-medium">Passed all validation checks</p>
        </div>
      )}

      {/* Risk-adjusted returns */}
      <div>
        <p className="text-[9px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-2">
          Risk-Adjusted Performance
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <MetricTile
            label="Total Return"
            value={`${r.totalReturnPct >= 0 ? '+' : ''}${r.totalReturnPct.toFixed(1)}%`}
            subtext={formatCurrency(r.totalReturn)}
            positive={r.totalReturnPct >= 0}
            negative={r.totalReturnPct < 0}
            icon={TrendingUp}
          />
          <MetricTile
            label="Annualised"
            value={`${r.annualizedReturn >= 0 ? '+' : ''}${r.annualizedReturn.toFixed(1)}%`}
            subtext="Per year"
            positive={r.annualizedReturn >= 0}
            icon={Activity}
          />
          <MetricTile
            label="Sharpe Ratio"
            value={r.sharpeRatio.toFixed(2)}
            subtext={sharpeLabel}
            positive={r.sharpeRatio >= 1}
            negative={r.sharpeRatio < 0.8}
            icon={Award}
          />
          <MetricTile
            label="Sortino Ratio"
            value={sortino.toFixed(2)}
            subtext={`${sortinoLabel} — downside risk`}
            positive={sortino >= 1.2}
            negative={sortino < 0.8}
            icon={ArrowUpDown}
          />
        </div>
      </div>

      {/* Drawdown & risk */}
      <div>
        <p className="text-[9px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-2">
          Drawdown & Risk
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <MetricTile
            label="Max Drawdown"
            value={`${r.maxDrawdown.toFixed(1)}%`}
            subtext="Peak-to-trough"
            negative
            icon={TrendingDown}
          />
          <MetricTile
            label="Calmar Ratio"
            value={calmar.toFixed(2)}
            subtext={calmarLabel}
            positive={calmar >= 1}
            negative={calmar < 0.5}
            icon={Target}
          />
          <MetricTile
            label="Recovery Factor"
            value={recovery.toFixed(2)}
            subtext="Return ÷ max DD"
            positive={recovery >= 2}
            icon={RefreshCw}
          />
          <MetricTile
            label="DD Duration"
            value={ddDur > 0 ? `~${ddDur} periods` : 'N/A'}
            subtext="Longest underwater"
            negative={ddDur > 20}
            icon={Clock}
          />
        </div>
      </div>

      {/* Trade quality */}
      <div>
        <p className="text-[9px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-2">
          Trade Quality
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <MetricTile
            label="Profit Factor"
            value={r.profitFactor.toFixed(2)}
            subtext={pfLabel}
            positive={r.profitFactor >= 1.5}
            negative={r.profitFactor < 1}
            icon={BarChart2}
          />
          <MetricTile
            label="Expectancy"
            value={formatCurrency(expectancy)}
            subtext="Avg profit per trade"
            positive={expectancy > 0}
            negative={expectancy < 0}
            icon={DollarSign}
          />
          <MetricTile
            label="Win Rate"
            value={`${r.winRate.toFixed(1)}%`}
            subtext={`${r.winningTrades}W / ${r.losingTrades}L`}
            positive={r.winRate >= 55}
            negative={r.winRate < 45}
            icon={Percent}
          />
          <MetricTile
            label="Avg Win / Loss"
            value={`${r.avgWin.toFixed(0)} / ${Math.abs(r.avgLoss).toFixed(0)}`}
            subtext={`Ratio: ${(r.avgWin / Math.abs(r.avgLoss)).toFixed(2)}`}
            positive={r.avgWin > Math.abs(r.avgLoss)}
            icon={Award}
          />
        </div>
      </div>

      {/* Capital + consecutive */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <MetricTile label="Initial Capital" value={formatCurrency(r.initialCapital)} icon={DollarSign} />
        <MetricTile
          label="Final Capital"
          value={formatCurrency(r.finalCapital)}
          positive={r.finalCapital > r.initialCapital}
          negative={r.finalCapital < r.initialCapital}
          icon={DollarSign}
        />
        <MetricTile
          label="Max Consec Wins"
          value={`${maxCWins} trades`}
          positive
          icon={TrendingUp}
        />
        <MetricTile
          label="Max Consec Losses"
          value={`${maxCLoss} trades`}
          negative={maxCLoss >= 4}
          icon={AlertTriangle}
        />
      </div>
    </div>
  );
};

// ── Tab: Charts ───────────────────────────────────────────────────────────────

const ChartsTab: React.FC<{ r: BacktestResult }> = ({ r }) => {
  const ddSeries = useMemo(() => deriveDrawdownSeries(r.equityCurve), [r.equityCurve]);
  const worstDd = useMemo(() => Math.min(...ddSeries.map(d => d.drawdown)), [ddSeries]);
  const ddDur   = useMemo(() => maxDrawdownDuration(ddSeries), [ddSeries]);

  return (
    <div className="space-y-6">
      {/* Equity curve */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Equity Curve
          </p>
          <div className="flex gap-2">
            <Badge variant="neutral" size="sm">Initial: {formatCurrency(r.initialCapital)}</Badge>
            <Badge variant={r.finalCapital >= r.initialCapital ? 'success' : 'danger'} size="sm">
              Final: {formatCurrency(r.finalCapital)}
            </Badge>
          </div>
        </div>
        <SVGAreaChart
          data={r.equityCurve}
          height={200}
          showGrid
          gradientId="bt-equity"
          curveTension={0.25}
        />
      </div>

      {/* Divider with drawdown stats */}
      <div className="flex items-center gap-3 text-[10px] font-mono">
        <div className="flex-1 border-t border-deep-teal-800/10 dark:border-white/10" />
        <span className="text-loss font-semibold">
          Worst DD: {worstDd.toFixed(1)}%
        </span>
        <span className="text-obsidian-400/50 dark:text-paper-100/50">
          Max duration: ~{ddDur} periods
        </span>
        <div className="flex-1 border-t border-deep-teal-800/10 dark:border-white/10" />
      </div>

      {/* Underwater drawdown chart */}
      <div className="space-y-2">
        <p className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
          Drawdown (Underwater Curve)
        </p>
        <p className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40">
          Each bar shows how far below the previous equity peak. Extended periods underwater signal regime-sensitive strategies.
        </p>
        <DrawdownChart
          data={ddSeries}
          height={130}
          maxDrawdown={worstDd}
        />
      </div>

      {/* E. Chan interpretation guide */}
      <div className="p-3 rounded-xl bg-deep-teal-800/5 dark:bg-white/5 border border-deep-teal-800/5 dark:border-white/5">
        <p className="text-[9px] font-mono uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 mb-2">
          Reading these charts
        </p>
        <div className="space-y-1">
          {[
            ['Equity slope', 'Steeper = faster compounding. Abrupt drops signal momentum/volatility sensitivity.'],
            ['Underwater curve', 'Longest continuous drawdown = psychological risk. Calmar ratio discounts strategies with long underwater periods.'],
            ['V-shaped dips', 'Fast recovery = robust strategy. Flat bottoms = extended regime mismatch.'],
          ].map(([term, desc]) => (
            <p key={term} className="text-[10px] font-sans text-obsidian-400/50 dark:text-paper-100/50">
              <span className="font-mono font-semibold">{term}:</span> {desc}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── Tab: P&L Analysis ─────────────────────────────────────────────────────────

const PnLAnalysisTab: React.FC<{ r: BacktestResult }> = ({ r }) => {
  const [showAll, setShowAll] = useState(false);

  const cumulativeCurve = useMemo(() => deriveCumulativePnlCurve(r.equityCurve), [r.equityCurve]);
  const dailyRows       = useMemo(() => deriveDailyPnl(r.equityCurve), [r.equityCurve]);

  const positiveRows = dailyRows.filter(d => d.pnl > 0).length;
  const negativeRows = dailyRows.filter(d => d.pnl < 0).length;
  const avgDailyPnl  = dailyRows.reduce((s, d) => s + d.pnl, 0) / (dailyRows.length || 1);

  const displayRows = showAll ? dailyRows : dailyRows.slice(0, 12);
  const maxAbsPnl   = Math.max(...dailyRows.map(d => Math.abs(d.pnl)));

  return (
    <div className="space-y-5">
      {/* Cumulative P&L curve */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
            Cumulative P&L
          </p>
          <div className="flex gap-2">
            <Badge variant={avgDailyPnl >= 0 ? 'success' : 'danger'} size="sm">
              Avg: {formatCurrency(avgDailyPnl)} / period
            </Badge>
            <Badge variant="neutral" size="sm">
              {positiveRows}up / {negativeRows}dn
            </Badge>
          </div>
        </div>
        <SVGAreaChart
          data={cumulativeCurve}
          height={180}
          showGrid
          gradientId="bt-cumpnl"
          curveTension={0.2}
        />
        <p className="text-[10px] font-sans text-obsidian-400/40 dark:text-paper-100/40">
          Unlike the equity curve, this shows absolute gains from start ($0 = break-even). Flat stretches indicate inactive or losing periods.
        </p>
      </div>

      {/* Period-by-period P&L table */}
      <div className="space-y-2">
        <p className="text-[10px] font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
          Period P&L Breakdown with Drawdown
        </p>
        <div className="rounded-xl overflow-hidden border border-deep-teal-800/5 dark:border-white/5">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="bg-deep-teal-800/5 dark:bg-white/5 border-b border-deep-teal-800/5 dark:border-white/5">
                {['Date', 'P&L ($)', 'P&L (%)', 'Cumulative', 'Drawdown', 'Distribution'].map(h => (
                  <th key={h} className="px-3 py-2 text-left text-[9px] uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-deep-teal-800/5 dark:border-white/5 last:border-0 hover:bg-deep-teal-800/5 dark:hover:bg-white/5 transition-colors"
                >
                  <td className="px-3 py-2 text-obsidian-400/60 dark:text-paper-100/60 whitespace-nowrap">{row.date}</td>
                  <td className={cn('px-3 py-2 font-bold', row.pnl >= 0 ? 'text-gain' : 'text-loss')}>
                    {row.pnl >= 0 ? '+' : ''}{formatCurrency(row.pnl)}
                  </td>
                  <td className={cn('px-3 py-2', row.pnlPct >= 0 ? 'text-gain' : 'text-loss')}>
                    {row.pnlPct >= 0 ? '+' : ''}{row.pnlPct.toFixed(2)}%
                  </td>
                  <td className={cn('px-3 py-2 font-medium', row.cumulative >= 0 ? 'text-gain' : 'text-loss')}>
                    {row.cumulative >= 0 ? '+' : ''}{formatCurrency(row.cumulative)}
                  </td>
                  <td className={cn('px-3 py-2', row.drawdownPct < -5 ? 'text-loss font-bold' : row.drawdownPct < 0 ? 'text-warning' : 'text-obsidian-400/50 dark:text-paper-100/50')}>
                    {row.drawdownPct < 0 ? row.drawdownPct.toFixed(1) + '%' : '—'}
                  </td>
                  <td className="px-3 py-2 w-24">
                    <div className="h-2.5 w-full bg-deep-teal-800/5 dark:bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full', row.pnl >= 0 ? 'bg-gain/50' : 'bg-loss/50')}
                        style={{ width: `${maxAbsPnl > 0 ? (Math.abs(row.pnl) / maxAbsPnl) * 100 : 0}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {dailyRows.length > 12 && (
          <button
            onClick={() => setShowAll(v => !v)}
            className="w-full text-center text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50 hover:text-obsidian-400 dark:hover:text-paper-100 py-1.5 transition-colors"
          >
            {showAll ? 'Show less' : `Show all ${dailyRows.length} periods`}
          </button>
        )}
      </div>
    </div>
  );
};

// ── Tab: Trade Log ────────────────────────────────────────────────────────────

const TradeLogTab: React.FC<{ r: BacktestResult }> = ({ r }) => {
  const totalPnl = r.trades.reduce((s, t) => s + t.pnl, 0);
  const wins     = r.trades.filter(t => t.pnl >= 0);
  const losses   = r.trades.filter(t => t.pnl < 0);

  return (
    <div className="space-y-4">
      {/* Trade log summary strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <MetricTile label="Showing" value={`${r.trades.length} trades`} icon={BarChart2} />
        <MetricTile
          label="Net P&L"
          value={formatCurrency(totalPnl)}
          positive={totalPnl >= 0}
          negative={totalPnl < 0}
          icon={DollarSign}
        />
        <MetricTile
          label="Best Trade"
          value={formatCurrency(Math.max(...r.trades.map(t => t.pnl)))}
          positive
          icon={TrendingUp}
        />
        <MetricTile
          label="Worst Trade"
          value={formatCurrency(Math.min(...r.trades.map(t => t.pnl)))}
          negative
          icon={TrendingDown}
        />
      </div>

      {/* Full table */}
      <div className="rounded-xl overflow-hidden border border-deep-teal-800/5 dark:border-white/5">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="bg-deep-teal-800/5 dark:bg-white/5 border-b border-deep-teal-800/5 dark:border-white/5">
              {['Symbol', 'Side', 'Entry', 'Exit', 'Entry $', 'Exit $', 'Duration', 'P&L'].map(h => (
                <th key={h} className="px-2.5 py-2 text-left text-[9px] uppercase tracking-widest text-obsidian-400/40 dark:text-paper-100/40 font-medium">
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
                <td className="px-2.5 py-2 font-semibold text-obsidian-400 dark:text-paper-100">
                  {trade.symbol.replace('USDT', '')}
                </td>
                <td className="px-2.5 py-2">
                  <Badge variant={trade.side === 'long' ? 'success' : 'danger'} size="sm">
                    {trade.side}
                  </Badge>
                </td>
                <td className="px-2.5 py-2 text-obsidian-400/60 dark:text-paper-100/60">{trade.entryDate}</td>
                <td className="px-2.5 py-2 text-obsidian-400/60 dark:text-paper-100/60">{trade.exitDate}</td>
                <td className="px-2.5 py-2 text-obsidian-400/50 dark:text-paper-100/50">
                  {trade.entryPrice.toLocaleString()}
                </td>
                <td className="px-2.5 py-2 text-obsidian-400/50 dark:text-paper-100/50">
                  {trade.exitPrice.toLocaleString()}
                </td>
                <td className="px-2.5 py-2 text-obsidian-400/50 dark:text-paper-100/50">{trade.duration}</td>
                <td className={cn('px-2.5 py-2 font-bold', trade.pnl >= 0 ? 'text-gain' : 'text-loss')}>
                  {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                  <span className="text-[9px] ml-1 opacity-60">
                    ({trade.pnlPct >= 0 ? '+' : ''}{trade.pnlPct}%)
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Win/loss split */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-3 rounded-xl bg-gain/5 border border-gain/15">
          <p className="text-[9px] font-mono uppercase tracking-widest text-gain/60 mb-1">Winning Trades</p>
          <p className="text-base font-mono font-bold text-gain">
            {wins.length} trades · {formatCurrency(wins.reduce((s, t) => s + t.pnl, 0))}
          </p>
          <p className="text-[10px] font-sans text-gain/60">
            Avg: {formatCurrency(wins.length ? wins.reduce((s, t) => s + t.pnl, 0) / wins.length : 0)}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-loss/5 border border-loss/15">
          <p className="text-[9px] font-mono uppercase tracking-widest text-loss/60 mb-1">Losing Trades</p>
          <p className="text-base font-mono font-bold text-loss">
            {losses.length} trades · {formatCurrency(losses.reduce((s, t) => s + t.pnl, 0))}
          </p>
          <p className="text-[10px] font-sans text-loss/60">
            Avg: {formatCurrency(losses.length ? losses.reduce((s, t) => s + t.pnl, 0) / losses.length : 0)}
          </p>
        </div>
      </div>
    </div>
  );
};

// ── Main modal ────────────────────────────────────────────────────────────────


export const BacktestResultsModal: React.FC<BacktestResultsModalProps> = ({
  isOpen,
  onClose,
  result,
  strategyId,
  dataProvenance,
}) => {
  const { data: fetchedResult, isLoading, error } = useBacktestResults(
    result ? null : (strategyId ?? null),
  );
  const r = result ?? fetchedResult ?? mockResult;

  // Three sources with different provenance. `fetchedResult` is one of the
  // three real API calls in this dashboard; `mockResult` is fabricated. A
  // caller-supplied `result` is whatever the caller declares, and defaults
  // to synthetic when it declares nothing.
  const provenance = result !== undefined
    ? resolveProvenance(dataProvenance, result)
    : fetchedResult !== undefined && fetchedResult !== null
      ? 'live' as const
      : 'synthetic' as const;

  const winRateVariant = r.winRate >= 55 ? 'success' : r.winRate >= 45 ? 'warning' : 'danger';
  const passed         = r.passedValidation ?? true;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Backtest: ${r.strategyName}`}
      description={`${r.symbol} — ${r.startDate} to ${r.endDate}`}
      size="full"
    >
      <div className="space-y-4">
        {requiresSyntheticLabel(provenance) && (
          <div className="flex items-center">
            <SyntheticDataBadge />
          </div>
        )}
        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center gap-2 py-6 text-obsidian-400/50 dark:text-paper-100/40">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span className="text-xs font-mono">Loading backtest results...</span>
          </div>
        )}
        {/* Error state */}
        {error && !isLoading && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-loss/10 border border-loss/20">
            <AlertTriangle className="w-4 h-4 text-loss shrink-0" />
            <p className="text-xs font-mono text-loss">{error}</p>
          </div>
        )}
        {/* Summary badges + tabs (hidden while loading) */}
        {!isLoading && (
          <>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" size="sm">{r.period} period</Badge>
              <Badge variant="outline" size="sm">{r.totalTrades} trades</Badge>
              <Badge variant={winRateVariant} size="sm" dot>
                {r.winRate}% win rate
              </Badge>
              <Badge variant={r.totalReturnPct >= 0 ? 'success' : 'danger'} size="sm">
                {r.totalReturnPct >= 0 ? '+' : ''}{r.totalReturnPct.toFixed(1)}% return
              </Badge>
              <Badge variant={passed ? 'success' : 'danger'} size="sm">
                {passed ? 'Passed validation' : 'Failed validation'}
              </Badge>
            </div>

            {/* 4-tab analysis */}
            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="charts">Charts</TabsTrigger>
                <TabsTrigger value="pnl">P&amp;L Analysis</TabsTrigger>
                <TabsTrigger value="trades">Trade Log</TabsTrigger>
              </TabsList>

              <TabsContent value="overview">
                <OverviewTab r={r} />
              </TabsContent>

              <TabsContent value="charts">
                <ChartsTab r={r} />
              </TabsContent>

              <TabsContent value="pnl">
                <PnLAnalysisTab r={r} />
              </TabsContent>

              <TabsContent value="trades">
                <TradeLogTab r={r} />
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>
    </Modal>
  );
};
