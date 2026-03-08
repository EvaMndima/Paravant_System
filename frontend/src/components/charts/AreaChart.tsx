import React, { Component, type ReactNode, useEffect, useState } from 'react';
import {
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { SizedResponsiveContainer } from './SizedResponsiveContainer';
import { cn, formatCurrency } from '@/lib/utils';
import { useTheme } from '@/contexts/ThemeContext';

export interface AreaChartData {
  date: string;
  value: number;
}

export interface AreaChartProps {
  data: AreaChartData[];
  height?: number;
  showGrid?: boolean;
  gradientId?: string;
  curveType?: 'linear' | 'monotone' | 'step';
  showTooltip?: boolean;
  animate?: boolean;
  className?: string;
}

// --- Error Boundary ---
interface ErrorBoundaryProps {
  fallback: ReactNode;
  children?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class ChartErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(_error: unknown): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown, errorInfo: unknown) {
    console.error("Recharts Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }

    return this.props.children;
  }
}

// --- Custom Tooltip ---
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-3 min-w-[140px]">
        <p className="text-paper-100/60 font-sans text-xs mb-1">{label}</p>
        <p className="text-paper-100 font-mono text-lg font-medium tracking-tight">
          {formatCurrency(payload[0].value)}
        </p>
      </div>
    );
  }
  return null;
};

// --- Main Component ---
export const AreaChart: React.FC<AreaChartProps> = ({
  data,
  height = 300,
  showGrid = false,
  gradientId = "colorValue",
  curveType = "monotone",
  showTooltip = true,
  animate = true,
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

  // Colors mapped from tailwind config
  const colors = {
    stroke: accentColor,
    grid: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(15, 61, 62, 0.05)',
    axis: isDark ? 'rgba(248, 245, 242, 0.4)' : 'rgba(16, 20, 19, 0.4)',
  };

  // Simple SVG Fallback in case Recharts fails
  const FallbackChart = () => {
    if (!data || data.length === 0) return (
       <div className="flex items-center justify-center h-full w-full text-obsidian-400/40 dark:text-paper-100/40 font-mono text-xs">No Data</div>
    );

    const values = data.map(d => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const points = values.map((val, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = 90 - ((val - min) / range) * 80;
      return `${x},${y}`;
    }).join(' ');

    const lastVal = values[values.length - 1];

    return (
        <div className="w-full h-full relative flex flex-col items-center justify-center p-4 border border-dashed border-deep-teal-800/10 dark:border-white/10 rounded-xl bg-deep-teal-800/5 dark:bg-white/5">
             <div className="absolute top-4 left-4 text-xs font-mono text-obsidian-400/60 dark:text-paper-100/60">
                Chart Fallback Mode
             </div>

             <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-3/4 opacity-60">
                 <path
                    d={`M0,100 L${points.split(' ')[0]} ${points} L100,100 Z`}
                    fill="currentColor"
                    className="text-turquoise-mist opacity-10"
                    style={{ color: accentColor }}
                 />
                 <polyline
                    points={points}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    vectorEffect="non-scaling-stroke"
                    className="text-turquoise-mist"
                    style={{ color: accentColor }}
                 />
             </svg>

             <div className="mt-2 font-mono text-sm font-medium text-obsidian-400 dark:text-paper-100">
                Latest: {formatCurrency(lastVal)}
             </div>
        </div>
    );
  };

  return (
    <div
      className={cn("w-full transition-opacity duration-500", className)}
      style={{ width: '100%', height: height, minHeight: height }}
    >
      <ChartErrorBoundary fallback={<FallbackChart />}>
        <SizedResponsiveContainer width="100%" height="100%">
          <RechartsAreaChart
            data={data}
            margin={{ top: 10, right: 0, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors.stroke} stopOpacity={0.4} />
                <stop offset="95%" stopColor={colors.stroke} stopOpacity={0} />
              </linearGradient>
            </defs>

            {showGrid && (
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke={colors.grid}
              />
            )}

            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fill: colors.axis, fontSize: 10, fontFamily: 'monospace' }}
              dy={10}
              minTickGap={30}
            />

            <YAxis
              hide={true}
              domain={['auto', 'auto']}
            />

            {showTooltip && (
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ stroke: colors.grid, strokeWidth: 1 }}
              />
            )}

            <Area
              type={curveType}
              dataKey="value"
              stroke={colors.stroke}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#${gradientId})`}
              isAnimationActive={animate}
              animationDuration={1500}
              animationEasing="ease-in-out"
            />
          </RechartsAreaChart>
        </SizedResponsiveContainer>
      </ChartErrorBoundary>
    </div>
  );
};
