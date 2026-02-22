/**
 * EquityCurveChart — Full equity curve visualization with Recharts.
 *
 * Features:
 * - Main equity area line with gradient fill
 * - Benchmark overlay (dashed line, toggleable)
 * - Drawdown underwater chart below (synced x-axis)
 * - Time range selector: 1W | 1M | 3M | 6M | 1Y | ALL
 * - Custom tooltip per DESIGN_GUIDE §4.7
 * - Responsive, theme-aware, handles empty data
 */
import React, { useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  type TooltipProps,
} from 'recharts';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EquityDataPoint {
  date: string;
  equity: number;
  benchmark?: number;
  drawdown_pct?: number;
}

export interface EquityCurveChartProps {
  data: EquityDataPoint[];
  range: string;
  onRangeChange: (range: string) => void;
  showBenchmark?: boolean;
  showDrawdown?: boolean;
  /** Height of main chart in px. Defaults to 400. */
  height?: number;
  /** Height of drawdown chart in px. Defaults to 120. */
  drawdownHeight?: number;
  className?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TIME_RANGES = ['1W', '1M', '3M', '6M', '1Y', 'ALL'] as const;

// Semantic colors — per DESIGN_GUIDE §4.3 (never use CSS variables in Recharts attributes)
const COLOR_GAIN = '#2ECC71';
const COLOR_LOSS = '#E74C3C';
const COLOR_GRID = 'rgba(255, 255, 255, 0.05)';
const COLOR_AXIS = 'rgba(255, 255, 255, 0.3)';
const COLOR_ACCENT = '#2A9D8F'; // turquoise-mist for benchmark

// ---------------------------------------------------------------------------
// Custom Tooltip
// ---------------------------------------------------------------------------

const CustomTooltip: React.FC<TooltipProps<number, string>> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;

  const equity = payload.find((p) => p.dataKey === 'equity')?.value as number | undefined;
  const benchmark = payload.find((p) => p.dataKey === 'benchmark')?.value as number | undefined;
  const drawdown = payload.find((p) => p.dataKey === 'drawdown_pct')?.value as number | undefined;

  return (
    <div
      className="rounded-xl px-3 py-2.5 text-xs font-mono shadow-xl"
      style={{
        background: 'rgba(22, 25, 24, 0.95)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        color: '#F8F5F2',
        minWidth: '160px',
      }}
    >
      <div className="font-bold text-[10px] uppercase tracking-widest mb-2 opacity-60">{label}</div>
      {equity !== undefined && (
        <div className="flex justify-between gap-4">
          <span className="opacity-60">Equity</span>
          <span className="font-medium" style={{ color: COLOR_GAIN }}>
            ${equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      )}
      {benchmark !== undefined && (
        <div className="flex justify-between gap-4 mt-0.5">
          <span className="opacity-60">Benchmark</span>
          <span className="font-medium" style={{ color: COLOR_ACCENT }}>
            ${benchmark.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      )}
      {drawdown !== undefined && (
        <div className="flex justify-between gap-4 mt-0.5">
          <span className="opacity-60">Drawdown</span>
          <span className="font-medium" style={{ color: COLOR_LOSS }}>
            {drawdown.toFixed(2)}%
          </span>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Time range filter
// ---------------------------------------------------------------------------

function filterByRange(data: EquityDataPoint[], range: string): EquityDataPoint[] {
  if (range === 'ALL' || data.length === 0) return data;

  const now = new Date();
  const cutoff = new Date(now);

  switch (range) {
    case '1W': cutoff.setDate(now.getDate() - 7); break;
    case '1M': cutoff.setMonth(now.getMonth() - 1); break;
    case '3M': cutoff.setMonth(now.getMonth() - 3); break;
    case '6M': cutoff.setMonth(now.getMonth() - 6); break;
    case '1Y': cutoff.setFullYear(now.getFullYear() - 1); break;
    default: return data;
  }

  return data.filter((d) => new Date(d.date) >= cutoff);
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

const EmptyState: React.FC<{ height: number }> = ({ height }) => (
  <div
    className="flex items-center justify-center rounded-xl bg-white/5 border border-white/5"
    style={{ height }}
  >
    <p className="text-xs font-mono uppercase tracking-widest opacity-30">No data available</p>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({
  data,
  range,
  onRangeChange,
  showBenchmark = true,
  showDrawdown = true,
  height = 400,
  drawdownHeight = 120,
  className,
}) => {
  const [hoveredRange, setHoveredRange] = useState<string | null>(null);

  const filteredData = useMemo(() => filterByRange(data, range), [data, range]);

  const hasBenchmark = filteredData.some((d) => d.benchmark !== undefined);
  const hasDrawdown = filteredData.some((d) => d.drawdown_pct !== undefined);

  // Format x-axis labels based on range
  const formatXAxis = (value: string): string => {
    try {
      const d = new Date(value);
      if (['1W', '1M'].includes(range)) {
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }
      return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    } catch {
      return value;
    }
  };

  const formatYAxis = (value: number): string =>
    value >= 1000 ? `$${(value / 1000).toFixed(0)}k` : `$${value.toFixed(0)}`;

  const formatDrawdownY = (value: number): string => `${value.toFixed(0)}%`;

  return (
    <div className={cn('space-y-3', className)}>
      {/* Time range selector */}
      <div className="flex gap-1">
        {TIME_RANGES.map((r) => (
          <button
            key={r}
            onClick={() => onRangeChange(r)}
            onMouseEnter={() => setHoveredRange(r)}
            onMouseLeave={() => setHoveredRange(null)}
            className={cn(
              'px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold uppercase tracking-widest transition-all duration-150',
              range === r
                ? 'bg-turquoise-mist/20 text-turquoise-mist border border-turquoise-mist/30'
                : hoveredRange === r
                  ? 'bg-white/10 text-paper-100/80 border border-white/10'
                  : 'text-paper-100/40 border border-transparent hover:text-paper-100/60',
            )}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Main equity chart */}
      {filteredData.length === 0 ? (
        <EmptyState height={height} />
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <ResponsiveContainer width="100%" height={height}>
            <ComposedChart data={filteredData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLOR_GAIN} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={COLOR_GAIN} stopOpacity={0} />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke={COLOR_GRID}
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tickFormatter={formatXAxis}
                tick={{ fill: COLOR_AXIS, fontSize: 10, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis
                tickFormatter={formatYAxis}
                tick={{ fill: COLOR_AXIS, fontSize: 10, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
                width={55}
              />
              <Tooltip content={<CustomTooltip />} />

              {/* Benchmark overlay */}
              {showBenchmark && hasBenchmark && (
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke={COLOR_ACCENT}
                  strokeWidth={1.5}
                  strokeDasharray="5 5"
                  dot={false}
                  activeDot={{ r: 3, fill: COLOR_ACCENT }}
                />
              )}

              {/* Main equity area */}
              <Area
                type="monotone"
                dataKey="equity"
                stroke={COLOR_GAIN}
                strokeWidth={2}
                fill="url(#equityGradient)"
                dot={false}
                activeDot={{ r: 4, fill: COLOR_GAIN, stroke: '#161918', strokeWidth: 2 }}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>

          {/* Drawdown underwater chart */}
          {showDrawdown && hasDrawdown && (
            <div className="mt-1">
              <div className="text-[10px] font-mono uppercase tracking-widest opacity-30 mb-1 pl-2">
                Drawdown
              </div>
              <ResponsiveContainer width="100%" height={drawdownHeight}>
                <AreaChart data={filteredData} margin={{ top: 0, right: 5, bottom: 0, left: 5 }}>
                  <defs>
                    <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLOR_LOSS} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={COLOR_LOSS} stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <XAxis hide dataKey="date" />
                  <YAxis
                    tickFormatter={formatDrawdownY}
                    tick={{ fill: COLOR_AXIS, fontSize: 9, fontFamily: 'JetBrains Mono' }}
                    axisLine={false}
                    tickLine={false}
                    width={35}
                    reversed
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="drawdown_pct"
                    stroke={COLOR_LOSS}
                    strokeWidth={1}
                    fill="url(#drawdownGradient)"
                    dot={false}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
};
