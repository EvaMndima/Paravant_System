
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  Activity,
  DollarSign,
  BarChart2,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { MetricCard } from '@/components/ui/MetricCard';
import { ApiErrorDisplay } from '@/components/ui/ApiErrorDisplay';
import { GlassCard } from '@/components/ui/GlassCard';
import { DataTable } from '@/components/ui/DataTable';
import { Select } from '@/components/ui/Select';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { MonthlyHeatmap } from '@/components/charts/MonthlyHeatmap';
import { TradeDistributionHistogram } from '@/components/charts/TradeDistributionHistogram';
import {
  useEquityCurve,
  usePerformanceMetrics,
  useDashboardTrades,
} from '@/hooks';

// --- Equity Chart Component ---
const EquityChart = () => {
  const [timeRange, setTimeRange] = useState('1M');
  const { data: equity, isLoading } = useEquityCurve(timeRange);

  if (isLoading) {
    return <Skeleton className="h-[400px] rounded-2xl" />;
  }

  const data = equity?.data ?? [];
  const isPositive = data.length > 1 ? data[data.length - 1].equity >= data[0].equity : true;

  return (
    <GlassCard variant="elevated" className="h-[400px] flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="font-display text-lg font-medium">Equity Curve</h3>
          <p className="text-xs text-obsidian-400/60 dark:text-paper-100/60 font-mono">
            Total Return:{' '}
            <span className={isPositive ? 'text-gain' : 'text-loss'}>
              {formatPercent(equity?.total_return_pct ?? 0)}
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          <Select
            options={[
              { value: '1W', label: '1W' },
              { value: '1M', label: '1M' },
              { value: '3M', label: '3M' },
              { value: '6M', label: '6M' },
              { value: '1Y', label: '1Y' },
              { value: 'ALL', label: 'ALL' },
            ]}
            value={timeRange}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTimeRange(e.target.value)}
            className="w-24"
          />
        </div>
      </div>

      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={isPositive ? '#2ecc71' : '#e74c3c'}
                  stopOpacity={0.3}
                />
                <stop
                  offset="95%"
                  stopColor={isPositive ? '#2ecc71' : '#e74c3c'}
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
            <XAxis
              dataKey="timestamp"
              strokeOpacity={0.3}
              tick={{ fontSize: 10, fill: 'currentColor' }}
              tickFormatter={(val) =>
                new Date(val).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                })
              }
            />
            <YAxis
              strokeOpacity={0.3}
              tick={{ fontSize: 10, fill: 'currentColor' }}
              domain={['auto', 'auto']}
              tickFormatter={(val) => `$${val / 1000}k`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(23, 23, 23, 0.9)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                backdropFilter: 'blur(4px)',
              }}
              labelStyle={{ color: '#94a3b8' }}
              formatter={(value: number) => [formatCurrency(value), 'Equity']}
            />
            <Area
              type="monotone"
              dataKey="equity"
              stroke={isPositive ? '#2ecc71' : '#e74c3c'}
              strokeWidth={2}
              fill="url(#equityGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
};


// --- Recent Trades Table ---
const RecentTrades = () => {
  const { data: trades, isLoading } = useDashboardTrades(50);

  // DataTable requires (value: unknown) — cast inside each render function
  const columns = [
    {
      key: 'executed_at',
      header: 'Time',
      render: (val: unknown) => (
        <span className="text-xs font-mono opacity-60">
          {new Date(val as string).toLocaleTimeString()}
        </span>
      ),
    },
    {
      key: 'symbol',
      header: 'Symbol',
      render: (val: unknown) => <span className="font-bold">{val as string}</span>,
    },
    {
      key: 'side',
      header: 'Side',
      render: (val: unknown) => (
        <span
          className={`text-xs font-bold px-2 py-0.5 rounded ${
            val === 'BUY' ? 'bg-gain/20 text-gain' : 'bg-loss/20 text-loss'
          }`}
        >
          {val as string}
        </span>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      render: (val: unknown) => <span className="font-mono">{formatCurrency(val as number)}</span>,
    },
    {
      key: 'quantity',
      header: 'Size',
      render: (val: unknown) => <span className="font-mono">{val as number}</span>,
    },
    {
      key: 'commission',
      header: 'Commission',
      render: (val: unknown) => (
        <span className="font-mono text-xs opacity-60">{formatCurrency(val as number)}</span>
      ),
    },
  ];

  return (
    <GlassCard variant="default" padding="none" className="overflow-hidden">
      <div className="px-6 py-4 border-b border-deep-teal-800/5 dark:border-white/5 flex justify-between items-center bg-paper-100/50 dark:bg-obsidian-300/50">
        <h3 className="font-display text-lg font-medium">Recent Trades</h3>
        <span className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
          {trades?.length ?? 0} trades
        </span>
      </div>
      {isLoading ? (
        <div className="p-6">
          <Skeleton className="h-64 w-full" />
        </div>
      ) : trades && trades.length > 0 ? (
        <DataTable columns={columns} data={trades} className="border-none" />
      ) : (
        <div className="text-center py-12 text-obsidian-400/40 dark:text-paper-100/40 text-sm">
          No trades recorded
        </div>
      )}
    </GlassCard>
  );
};

export const PortfolioPage: React.FC = () => {
  const { data: metrics, isLoading: metricsLoading, isError, error, refetch } = usePerformanceMetrics();
  const { data: equity } = useEquityCurve();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 pb-12"
    >
      {isError && <ApiErrorDisplay error={error as Error} onRetry={refetch} />}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-medium text-deep-teal-800 dark:text-paper-100 mb-1">
            Portfolio Analysis
          </h1>
          <p className="text-obsidian-400/60 dark:text-paper-100/60 font-sans">
            Detailed performance metrics and trade history.
          </p>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metricsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))
        ) : (
          <>
            <MetricCard
              title="Total Return"
              value={equity?.total_return_pct ?? 0}
              format="percent"
              icon={TrendingUp}
              change={metrics?.total_return_pct ?? 0}
            />
            <MetricCard
              title="Win Rate"
              value={metrics?.win_rate ?? 0}
              format="percent"
              icon={Activity}
              variant="elevated"
            />
            <MetricCard
              title="Profit Factor"
              value={metrics?.profit_factor ?? 0}
              format="raw"
              icon={DollarSign}
            />
            <MetricCard
              title="Max Drawdown"
              value={metrics?.max_drawdown_pct ?? 0}
              format="percent"
              icon={BarChart2}
              variant={(metrics?.max_drawdown_pct ?? 0) > 15 ? 'dark' : 'default'}
            />
          </>
        )}
      </div>

      <EquityChart />

      {/* PRD §6.3: Monthly heatmap (§6.3.2) + trade distribution histogram (§6.3.3) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MonthlyHeatmap />
        <TradeDistributionHistogram />
      </div>

      <RecentTrades />
    </motion.div>
  );
};
