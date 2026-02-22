
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Play,
  History,
  TrendingUp,
  Settings2,
  CheckCircle2,
  AlertOctagon,
  Activity,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { MetricCard } from '@/components/ui/MetricCard';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatCurrency, formatPercent } from '@/lib/utils';
import type { BacktestResponse, BacktestRequest } from '@/types/api';
import { useStrategies, useRunBacktest } from '@/hooks';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';

// --- Config Panel (controlled form wired to real hooks) ---
interface BacktestConfigProps {
  onResult: (result: BacktestResponse) => void;
}

const BacktestConfig: React.FC<BacktestConfigProps> = ({ onResult }) => {
  const { data: strategies, isLoading: strategiesLoading } = useStrategies();
  const runBacktest = useRunBacktest();

  const [strategyId, setStrategyId] = useState('');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [lookbackDays, setLookbackDays] = useState(90);
  const [initialCapital, setInitialCapital] = useState(10000);
  const [commissionRate, setCommissionRate] = useState(0.001);

  const handleRun = () => {
    if (!strategyId) return;
    const request: Omit<BacktestRequest, 'strategy_id'> = {
      initial_capital: initialCapital,
      commission_rate: commissionRate,
      symbol,
      timeframe,
      lookback_days: lookbackDays,
    };
    runBacktest.mutate(
      { strategyId, request },
      { onSuccess: (data) => onResult(data) }
    );
  };

  return (
    <GlassCard variant="default" className="space-y-6">
      <div className="flex items-center gap-2 mb-4 border-b border-deep-teal-800/10 dark:border-white/10 pb-4">
        <Settings2 className="w-5 h-5 text-deep-teal-800 dark:text-turquoise-mist" />
        <h3 className="font-display font-medium text-lg">Configuration</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium opacity-80">Strategy</label>
          {strategiesLoading ? (
            <Skeleton className="h-10 rounded-xl" />
          ) : (
            <select
              aria-label="Select strategy"
              className="w-full bg-white/50 dark:bg-black/20 border border-deep-teal-800/10 dark:border-white/10 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 ring-turquoise-mist/50"
              value={strategyId}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStrategyId(e.target.value)}
            >
              <option value="">Select a strategy…</option>
              {(strategies ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium opacity-80">Asset</label>
          <select
            aria-label="Select asset"
            className="w-full bg-white/50 dark:bg-black/20 border border-deep-teal-800/10 dark:border-white/10 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 ring-turquoise-mist/50"
            value={symbol}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSymbol(e.target.value)}
          >
            <option value="BTCUSDT">BTCUSDT</option>
            <option value="ETHUSDT">ETHUSDT</option>
            <option value="BNBUSDT">BNBUSDT</option>
          </select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium opacity-80">Lookback Days</label>
          <Input
            type="number"
            aria-label="Lookback days"
            value={lookbackDays}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setLookbackDays(Number(e.target.value))
            }
            className="w-full"
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium opacity-80">Timeframe</label>
          <select
            aria-label="Select timeframe"
            className="w-full bg-white/50 dark:bg-black/20 border border-deep-teal-800/10 dark:border-white/10 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 ring-turquoise-mist/50"
            value={timeframe}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTimeframe(e.target.value)}
          >
            <option value="1m">1m</option>
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1d">1d</option>
          </select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium opacity-80">Initial Capital ($)</label>
          <Input
            type="number"
            aria-label="Initial capital"
            value={initialCapital}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setInitialCapital(Number(e.target.value))
            }
            className="w-full"
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium opacity-80">Commission Rate</label>
          <Input
            type="number"
            aria-label="Commission rate"
            value={commissionRate}
            step={0.0001}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setCommissionRate(Number(e.target.value))
            }
            className="w-full"
          />
        </div>
      </div>

      <div className="pt-4">
        <Button
          className="w-full gap-2 text-lg h-12"
          onClick={handleRun}
          isLoading={runBacktest.isPending}
          disabled={!strategyId || runBacktest.isPending}
          aria-label="Run backtest"
        >
          <Play className="w-5 h-5 fill-current" /> Run Backtest
        </Button>
        {runBacktest.isError && (
          <ApiErrorDisplay
            error={runBacktest.error as Error}
            onRetry={() => handleRun()}
          />
        )}
      </div>
    </GlassCard>
  );
};

// --- Results Component (uses real BacktestResponse with nested metrics) ---
const BacktestResults = ({ result }: { result: BacktestResponse }) => (
  <GlassCard variant="elevated" className="space-y-8">
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-deep-teal-800/10 dark:border-white/10 pb-4">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h3 className="font-display font-bold text-xl">Backtest Results</h3>
          <span
            className={`text-xs font-mono px-2 py-0.5 rounded-full ${
              result.status === 'completed'
                ? 'bg-gain/20 text-gain'
                : 'bg-warning/20 text-warning'
            }`}
          >
            {result.status.toUpperCase()}
          </span>
        </div>
        <p className="text-xs font-mono opacity-60">
          {result.strategy_name} &bull; {result.start_date} &rarr; {result.end_date}
        </p>
      </div>
      <div className="text-right">
        <p className="text-xs font-mono opacity-50">Capital</p>
        <p className="font-display font-medium">
          {formatCurrency(result.initial_capital)} &rarr; {formatCurrency(result.final_capital)}
        </p>
      </div>
    </div>

    {/* Metrics Grid — sourced from result.metrics nested object */}
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        title="Total Return"
        value={result.metrics.total_return_pct}
        format="percent"
        icon={TrendingUp}
        variant="subtle"
      />
      <MetricCard
        title="Sharpe Ratio"
        value={result.metrics.sharpe_ratio}
        format="number"
        icon={Activity}
        variant="subtle"
      />
      <MetricCard
        title="Max Drawdown"
        value={result.metrics.max_drawdown_pct}
        format="percent"
        icon={AlertOctagon}
        variant="subtle"
      />
      <MetricCard
        title="Win Rate"
        value={result.metrics.win_rate_pct}
        format="percent"
        icon={CheckCircle2}
        variant="subtle"
      />
    </div>

    {/* Secondary metrics */}
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
      {[
        { label: 'Total Trades', value: String(result.metrics.total_trades) },
        { label: 'Profit Factor', value: result.metrics.profit_factor.toFixed(2) },
        { label: 'Expectancy', value: formatCurrency(result.metrics.expectancy) },
        {
          label: 'Validation',
          value: result.metrics.passed_validation ? 'PASSED' : 'FAILED',
          colored: true,
          pass: result.metrics.passed_validation,
        },
      ].map(({ label, value, colored, pass }) => (
        <div key={label} className="rounded-xl bg-deep-teal-800/5 dark:bg-white/5 p-3">
          <p className="text-xs font-mono opacity-50 mb-1">{label}</p>
          <p
            className={`font-display font-medium text-sm ${
              colored ? (pass ? 'text-gain' : 'text-loss') : ''
            }`}
          >
            {value}
          </p>
        </div>
      ))}
    </div>

    {/* Annualised return */}
    <p className="text-xs font-mono opacity-50 text-center">
      Annualised Return:{' '}
      <span className="text-turquoise-mist">
        {formatPercent(result.metrics.annualized_return_pct)}
      </span>
      {result.metrics.validation_errors.length > 0 && (
        <span className="ml-4 text-warning">
          Warnings: {result.metrics.validation_errors.join(', ')}
        </span>
      )}
    </p>
  </GlassCard>
);

// --- Empty state shown before any backtest is run ---
const BacktestEmpty = () => (
  <GlassCard variant="elevated" className="h-full flex flex-col items-center justify-center py-20 text-center">
    <div className="bg-deep-teal-800/5 dark:bg-white/5 p-5 rounded-full mb-4">
      <Activity className="w-10 h-10 text-obsidian-400/30 dark:text-paper-100/30" strokeWidth={1} />
    </div>
    <p className="font-display text-lg font-medium opacity-40">No backtest results yet</p>
    <p className="text-sm opacity-30 mt-1 font-mono">Configure and run a backtest to see results here.</p>
  </GlassCard>
);

export const BacktestPage: React.FC = () => {
  const [result, setResult] = useState<BacktestResponse | null>(null);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 pb-12"
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
            Backtesting
          </h1>
          <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
            Simulate strategies against historical data.
          </p>
        </div>
        <Button variant="ghost" className="gap-2" aria-label="View backtest history">
          <History className="w-4 h-4" /> History
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <BacktestConfig onResult={setResult} />
        </div>
        <div className="lg:col-span-2">
          {result ? <BacktestResults result={result} /> : <BacktestEmpty />}
        </div>
      </div>
    </motion.div>
  );
};
