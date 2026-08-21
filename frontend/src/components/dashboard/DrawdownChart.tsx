import React, { Component, useMemo } from 'react';
import type { ReactNode } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { SizedResponsiveContainer } from '@/components/charts/SizedResponsiveContainer';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { SyntheticDataBadge } from '@/components/ui/SyntheticDataBadge';
import { cn } from '@/lib/utils';
import { requiresSyntheticLabel, resolveProvenance } from '@/lib/provenance';
import type { ProvenanceProps } from '@/lib/provenance';

export interface DrawdownDataPoint {
  date: string;
  drawdown: number; // Negative value, e.g. -5.2 for -5.2%
}

export interface DrawdownChartProps extends ProvenanceProps {
  data?: DrawdownDataPoint[];
  height?: number;
  maxDrawdown?: number;
  currentDrawdown?: number;
  title?: string;
  className?: string;
}

// Error boundary for Recharts
interface EBProps { fallback: ReactNode; children?: ReactNode }
interface EBState { hasError: boolean }
class DrawdownErrorBoundary extends Component<EBProps, EBState> {
  public state: EBState = { hasError: false };
  static getDerivedStateFromError(): EBState { return { hasError: true }; }
  render() { return this.state.hasError ? this.props.fallback : this.props.children; }
}

// Custom tooltip
const DrawdownTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const value: number = payload[0].value;
    return (
      <div className="bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-3 min-w-[130px]">
        <p className="text-paper-100/60 font-sans text-xs mb-1">{label}</p>
        <p className={cn('font-mono text-base font-medium', value < -10 ? 'text-loss' : value < -5 ? 'text-warning' : 'text-gain')}>
          {Number(value).toFixed(1)}%
        </p>
      </div>
    );
  }
  return null;
};

// Generate synthetic drawdown data (90 days)
function generateDrawdownData(): DrawdownDataPoint[] {
  const data: DrawdownDataPoint[] = [];
  let drawdown = 0;
  let recovering = false;

  for (let i = 0; i < 60; i++) {
    const d = new Date(2024, 9, 1);
    d.setDate(d.getDate() + i * 1.5);

    if (!recovering) {
      drawdown -= Math.random() * 1.2;
      if (drawdown < -18 || Math.random() < 0.08) recovering = true;
    } else {
      drawdown += Math.random() * 1.8;
      if (drawdown >= 0) { drawdown = 0; recovering = false; }
    }

    data.push({
      date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      drawdown: Math.min(0, Math.round(drawdown * 10) / 10),
    });
  }
  return data;
}

// Color a bar based on its drawdown depth
function getBarColor(value: number): string {
  if (value > -5) return 'rgba(16, 185, 129, 0.7)';
  if (value > -10) return 'rgba(245, 158, 11, 0.7)';
  if (value > -15) return 'rgba(239, 68, 68, 0.7)';
  return 'rgba(220, 38, 38, 0.9)';
}

// Recharts passes a negative height for bars that extend below the baseline.
// Use Math.abs and adjust y so the rect always renders top-down.
const ColoredBar = (props: any) => {
  const { x, y, width, height, value } = props;
  if (!height) return null;
  const absHeight = Math.abs(height);
  const barY = height < 0 ? y + height : y;
  return (
    <rect
      x={x}
      y={barY}
      width={width}
      height={absHeight}
      fill={getBarColor(value)}
      rx={1}
    />
  );
};

export const DrawdownChart: React.FC<DrawdownChartProps> = ({
  data,
  dataProvenance,
  height = 200,
  maxDrawdown,
  currentDrawdown = 0,
  title = 'Drawdown',
  className,
}) => {
  const chartData = useMemo(() => data ?? generateDrawdownData(), [data]);

  // Generated data is synthetic no matter what the caller declared.
  const provenance = resolveProvenance(dataProvenance, data);

  const computedMax = useMemo(
    () => maxDrawdown ?? Math.min(...chartData.map(d => d.drawdown)),
    [maxDrawdown, chartData]
  );

  const maxDepth = Math.min(computedMax * 1.15, -1); // Y axis lower bound with padding

  const gridStroke = 'rgba(255,255,255,0.05)';
  const axisColor = 'rgba(248, 245, 242, 0.3)';

  return (
    <GlassCard variant="default" padding="md" className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-mono uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50">
              {title}
            </h3>
            {requiresSyntheticLabel(provenance) && <SyntheticDataBadge compact />}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-mono font-bold text-obsidian-400 dark:text-paper-100">
              {computedMax.toFixed(1)}%
            </span>
            <span className="text-xs font-sans text-obsidian-400/40 dark:text-paper-100/40">max drawdown</span>
          </div>
        </div>
        <div className="text-right space-y-1">
          <Badge
            variant={currentDrawdown < -10 ? 'danger' : currentDrawdown < -5 ? 'warning' : 'success'}
            size="sm"
            dot
          >
            Current: {currentDrawdown.toFixed(1)}%
          </Badge>
          {currentDrawdown < -5 && (
            <div className="text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40">
              Recovering
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <DrawdownErrorBoundary
        fallback={
          <div className="flex items-center justify-center rounded-xl bg-deep-teal-800/5 dark:bg-white/5 text-obsidian-400/40 dark:text-paper-100/40 font-mono text-xs"
            style={{ height }}>
            Drawdown chart unavailable
          </div>
        }
      >
        <div style={{ height }}>
          <SizedResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 0, left: -25, bottom: 0 }}
              barCategoryGap="20%"
            >
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke={gridStroke}
              />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: axisColor, fontSize: 9, fontFamily: 'monospace' }}
                dy={8}
                minTickGap={30}
              />
              <YAxis
                domain={[maxDepth, 0]}
                axisLine={false}
                tickLine={false}
                tick={{ fill: axisColor, fontSize: 9, fontFamily: 'monospace' }}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip content={<DrawdownTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
              {/* Warning lines at -5% and -10% */}
              <ReferenceLine y={-5} stroke="rgba(245,158,11,0.3)" strokeDasharray="4 4" strokeWidth={1} />
              <ReferenceLine y={-10} stroke="rgba(239,68,68,0.3)" strokeDasharray="4 4" strokeWidth={1} />
              <Bar
                dataKey="drawdown"
                shape={<ColoredBar />}
                isAnimationActive={true}
                animationDuration={1000}
              />
            </BarChart>
          </SizedResponsiveContainer>
        </div>
      </DrawdownErrorBoundary>

      {/* Legend */}
      <div className="flex items-center gap-4 justify-end">
        {[
          { color: 'rgba(16,185,129,0.7)', label: '0–5%' },
          { color: 'rgba(245,158,11,0.7)', label: '5–10%' },
          { color: 'rgba(239,68,68,0.7)', label: '10%+' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
            <span className="text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50">{label}</span>
          </div>
        ))}
      </div>
    </GlassCard>
  );
};
