import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { GlassCard } from '@/components/ui/GlassCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { useDailyPnL } from '@/hooks';

const NUM_BUCKETS = 20;

interface BucketEntry {
  label: string;
  midpoint: number;
  count: number;
}

/**
 * Partition daily return percentages into evenly-spaced histogram buckets.
 * Returns only non-empty buckets to avoid sparse gaps in the chart.
 */
function buildHistogram(returns: number[]): BucketEntry[] {
  if (returns.length === 0) return [];
  const min = Math.min(...returns);
  const max = Math.max(...returns);
  const range = max - min;

  if (range < 0.0001) {
    return [
      {
        label: `${returns[0] >= 0 ? '+' : ''}${returns[0].toFixed(2)}%`,
        midpoint: returns[0],
        count: returns.length,
      },
    ];
  }

  const bucketSize = range / NUM_BUCKETS;
  return Array.from({ length: NUM_BUCKETS }, (_, i) => {
    const low = min + i * bucketSize;
    const high = low + bucketSize;
    const isLast = i === NUM_BUCKETS - 1;
    const count = returns.filter((r) => r >= low && (isLast ? r <= high : r < high)).length;
    const midpoint = (low + high) / 2;
    return {
      label: `${midpoint >= 0 ? '+' : ''}${midpoint.toFixed(2)}%`,
      midpoint,
      count,
    };
  }).filter((b) => b.count > 0);
}

/** Find the bucket label whose midpoint is closest to the given value. */
function findClosestBucket(buckets: BucketEntry[], value: number): string {
  if (buckets.length === 0) return '';
  return buckets.reduce((prev, curr) =>
    Math.abs(curr.midpoint - value) < Math.abs(prev.midpoint - value) ? curr : prev
  ).label;
}

export interface TradeDistributionHistogramProps {
  /** Optional className forwarded to the outer GlassCard */
  className?: string;
}

/**
 * Histogram of daily return distribution with mean and median reference lines.
 * Uses daily P&L records as proxy for per-trade returns (daily_pnl / portfolio_value × 100).
 * Expectancy annotation shows the mean daily return %. PRD §6.3.3
 */
export const TradeDistributionHistogram: React.FC<TradeDistributionHistogramProps> = ({
  className,
}) => {
  const { data: pnlData, isLoading } = useDailyPnL(90);

  const { buckets, mean, median, expectancy } = useMemo(() => {
    const records = pnlData?.records ?? [];
    if (records.length === 0) {
      return { buckets: [] as BucketEntry[], mean: 0, median: 0, expectancy: 0 };
    }

    const returns = records
      .filter((r) => r.portfolio_value > 0)
      .map((r) => (r.total_pnl / r.portfolio_value) * 100);

    if (returns.length === 0) {
      return { buckets: [] as BucketEntry[], mean: 0, median: 0, expectancy: 0 };
    }

    // Arithmetic mean
    const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    // Median from sorted array
    const sorted = [...returns].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];

    return { buckets: buildHistogram(returns), mean, median, expectancy: mean };
  }, [pnlData]);

  if (isLoading) {
    return <Skeleton className={`h-[300px] rounded-2xl ${className ?? ''}`} />;
  }

  if (buckets.length === 0) {
    return (
      <GlassCard variant="subtle" className={`h-full ${className ?? ''}`}>
        <h3 className="font-display text-lg font-medium mb-4">Return Distribution</h3>
        <div className="h-[250px] flex items-center justify-center text-obsidian-400/40 dark:text-paper-100/40 text-sm">
          No return data available
        </div>
      </GlassCard>
    );
  }

  const meanLabel = findClosestBucket(buckets, mean);
  const medianLabel = findClosestBucket(buckets, median);

  return (
    <GlassCard variant="subtle" className={`h-full ${className ?? ''}`}>
      <div className="flex justify-between items-start mb-4">
        <h3 className="font-display text-lg font-medium">Return Distribution</h3>
        <div className="text-right text-xs font-mono">
          <span className="text-obsidian-400/60 dark:text-paper-100/60">Expectancy </span>
          <span className={expectancy >= 0 ? 'text-gain' : 'text-loss'}>
            {expectancy >= 0 ? '+' : ''}
            {(expectancy * 100).toFixed(0)}bp/day
          </span>
        </div>
      </div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={buckets} margin={{ top: 16, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 8, fill: 'currentColor' }}
              strokeOpacity={0.3}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 9, fill: 'currentColor' }}
              strokeOpacity={0.3}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(23, 23, 23, 0.9)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
              }}
              formatter={(value: number) => [value, 'Days']}
              labelFormatter={(label: string) => `Return: ${label}`}
            />
            <Bar dataKey="count" radius={[2, 2, 0, 0]}>
              {buckets.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.midpoint >= 0 ? '#2ecc71' : '#e74c3c'}
                  fillOpacity={0.75}
                />
              ))}
            </Bar>
            {/* Mean reference line — teal dashed */}
            <ReferenceLine
              x={meanLabel}
              stroke="#2A9D8F"
              strokeDasharray="4 2"
              strokeWidth={1.5}
              label={{ value: 'Mean', position: 'insideTopLeft', fontSize: 9, fill: '#2A9D8F' }}
            />
            {/* Median reference line — amber dashed */}
            {meanLabel !== medianLabel && (
              <ReferenceLine
                x={medianLabel}
                stroke="#E9C46A"
                strokeDasharray="4 2"
                strokeWidth={1.5}
                label={{ value: 'Med', position: 'insideTopRight', fontSize: 9, fill: '#E9C46A' }}
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
};
