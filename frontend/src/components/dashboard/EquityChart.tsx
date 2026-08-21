import React, { useState, useMemo } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { AreaChart } from '@/components/charts/AreaChart';
import type { AreaChartData } from '@/components/charts/AreaChart';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { SyntheticDataBadge } from '@/components/ui/SyntheticDataBadge';
import { cn } from '@/lib/utils';
import { requiresSyntheticLabel, resolveProvenance } from '@/lib/provenance';
import type { ProvenanceProps } from '@/lib/provenance';

export type EquityTimeRange = '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL';

export interface EquityChartProps extends ProvenanceProps {
  data?: AreaChartData[];
  height?: number;
  title?: string;
  startingCapital?: number;
  className?: string;
}

const TIME_RANGES: EquityTimeRange[] = ['1D', '1W', '1M', '3M', '1Y', 'ALL'];

// Generate synthetic equity curve for a given number of data points
function generateEquity(points: number, seed = 100_000): AreaChartData[] {
  const result: AreaChartData[] = [];
  let value = seed;
  const now = new Date();

  for (let i = points - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const delta = (Math.random() - 0.46) * (seed * 0.008);
    value = Math.max(seed * 0.7, value + delta);
    result.push({
      date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: Math.round(value),
    });
  }
  return result;
}

const RANGE_POINTS: Record<EquityTimeRange, number> = {
  '1D': 24,
  '1W': 7,
  '1M': 30,
  '3M': 90,
  '1Y': 252,
  'ALL': 365,
};

export const EquityChart: React.FC<EquityChartProps> = ({
  data,
  dataProvenance,
  height = 220,
  title = 'Portfolio Equity',
  startingCapital = 100_000,
  className,
}) => {
  const [range, setRange] = useState<EquityTimeRange>('3M');

  const chartData = useMemo(() => {
    if (data) return data;
    return generateEquity(RANGE_POINTS[range], startingCapital);
  }, [data, range, startingCapital]);

  // Generated data is synthetic no matter what the caller declared.
  const provenance = resolveProvenance(dataProvenance, data);

  const first = chartData[0]?.value ?? startingCapital;
  const last = chartData[chartData.length - 1]?.value ?? startingCapital;
  const absChange = last - first;
  const pctChange = first > 0 ? (absChange / first) * 100 : 0;
  const isPositive = absChange >= 0;

  return (
    <GlassCard variant="default" padding="md" className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
              {title}
            </h3>
            {requiresSyntheticLabel(provenance) && <SyntheticDataBadge compact />}
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-2xl font-mono font-bold text-obsidian-400 dark:text-paper-100">
              ${last.toLocaleString()}
            </span>
            <Badge variant={isPositive ? 'success' : 'danger'} size="sm">
              {isPositive ? <TrendingUp className="w-3 h-3 mr-1 inline" /> : <TrendingDown className="w-3 h-3 mr-1 inline" />}
              {isPositive ? '+' : ''}{pctChange.toFixed(2)}%
            </Badge>
          </div>
          <p className="text-xs font-mono text-obsidian-400/40 dark:text-paper-100/40">
            {isPositive ? '+' : ''}${absChange.toLocaleString()} over {range}
          </p>
        </div>

        {/* Time range selector */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-deep-teal-800/5 dark:bg-white/5">
          {TIME_RANGES.map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={cn(
                'px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold uppercase tracking-widest transition-all duration-150',
                range === r
                  ? 'bg-turquoise-mist text-white shadow-sm'
                  : 'text-obsidian-400/50 dark:text-paper-100/50 hover:text-obsidian-400 dark:hover:text-paper-100'
              )}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <AreaChart
        data={chartData}
        height={height}
        showGrid
        curveType="monotone"
        gradientId={`equity-${range}`}
        animate
      />
    </GlassCard>
  );
};
