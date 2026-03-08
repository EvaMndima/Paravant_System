
import React, { useState, useEffect } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import { SizedResponsiveContainer } from './SizedResponsiveContainer';
import { cn, formatPercent } from '@/lib/utils';
import { useTheme } from '@/contexts/ThemeContext';

export interface BenchmarkDataPoint {
  date: string;
  portfolio: number;
  benchmark: number;
}

export interface BenchmarkChartProps {
  data: BenchmarkDataPoint[];
  height?: number;
  className?: string;
}

// Custom Tooltip
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-3 min-w-[180px]">
        <p className="text-paper-100/60 font-sans text-xs mb-2">{label}</p>
        <div className="space-y-1">
          {payload.map((entry: any, idx: number) => (
            <div key={idx} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.stroke }} />
                <span className="text-paper-100/80 text-xs font-sans capitalize">{entry.name}</span>
              </div>
              <span className="text-paper-100 font-mono text-sm font-medium">
                {formatPercent(entry.value / 100)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export const BenchmarkChart: React.FC<BenchmarkChartProps> = ({
  data,
  height = 300,
  className,
}) => {
  const { mode, appTheme } = useTheme();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const checkDark = () => {
      if (typeof window === 'undefined') return false;
      return mode === 'dark' || (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    };
    setIsDark(checkDark());
  }, [mode]);

  // Dynamic color selection based on active theme
  const getThemeColor = () => {
    if (isDark) {
        switch (appTheme) {
          case 'sapphire': return '#60A5FA';
          case 'emerald': return '#34D399';
          case 'onyx': return '#FCD34D';
          case 'ocean':
          default: return '#48CAE4';
        }
    }
    switch (appTheme) {
      case 'sapphire': return '#3B82F6';
      case 'emerald': return '#10B981';
      case 'onyx': return '#D4AF37';
      case 'ocean':
      default: return '#2A9D8F';
    }
  };

  const accentColor = getThemeColor();

  const colors = {
    portfolioStroke: accentColor,
    portfolioFill: accentColor,
    benchmarkStroke: isDark ? '#9CA3AF' : '#6B7280',
    grid: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(15, 61, 62, 0.05)',
    axis: isDark ? 'rgba(248, 245, 242, 0.4)' : 'rgba(16, 20, 19, 0.4)',
  };

  return (
    <div className={cn("w-full", className)} style={{ width: '100%', height: height, minHeight: height }}>
      <SizedResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 0, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorPortfolio" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colors.portfolioFill} stopOpacity={0.3} />
              <stop offset="95%" stopColor={colors.portfolioFill} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorBenchmark" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colors.benchmarkStroke} stopOpacity={0.1} />
              <stop offset="95%" stopColor={colors.benchmarkStroke} stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
            stroke={colors.grid}
          />

          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fill: colors.axis, fontSize: 10, fontFamily: 'monospace' }}
            dy={10}
            minTickGap={30}
          />

          <YAxis
            hide={false}
            axisLine={false}
            tickLine={false}
            tick={{ fill: colors.axis, fontSize: 10, fontFamily: 'monospace' }}
            tickFormatter={(val) => `${val}%`}
          />

          <Tooltip content={<CustomTooltip />} cursor={{ stroke: colors.grid }} />

          <Legend
            verticalAlign="top"
            align="right"
            iconType="circle"
            wrapperStyle={{ fontSize: '12px', fontFamily: 'Inter' }}
          />

          <Area
            name="Benchmark (SPY)"
            type="monotone"
            dataKey="benchmark"
            stroke={colors.benchmarkStroke}
            strokeWidth={2}
            strokeDasharray="4 4"
            fill="url(#colorBenchmark)"
            fillOpacity={1}
          />

          <Area
            name="Portfolio"
            type="monotone"
            dataKey="portfolio"
            stroke={colors.portfolioStroke}
            strokeWidth={2}
            fill="url(#colorPortfolio)"
            fillOpacity={1}
          />
        </AreaChart>
      </SizedResponsiveContainer>
    </div>
  );
};
