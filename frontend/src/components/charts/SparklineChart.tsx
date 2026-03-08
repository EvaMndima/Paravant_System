
import React, { useState, useEffect } from 'react';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  YAxis
} from 'recharts';
import { SizedResponsiveContainer } from './SizedResponsiveContainer';
import { cn } from '@/lib/utils';
import { useTheme } from '@/contexts/ThemeContext';

export interface SparklineChartProps {
  data: number[];
  width?: number | string;
  height?: number | string;
  color?: 'gain' | 'loss' | 'neutral' | 'turquoise';
  showArea?: boolean;
  className?: string;
}

export const SparklineChart: React.FC<SparklineChartProps> = ({
  data,
  width = "100%",
  height = "100%",
  color = 'turquoise',
  showArea = true,
  className
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

  // Transform primitive array to object array for Recharts
  const chartData = data.map((val, i) => ({ i, value: val }));

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

  // Color Mapping
  const colorMap = {
    gain: '#2ECC71',
    loss: '#E74C3C',
    neutral: isDark ? '#9CA3AF' : '#6B7280',
    turquoise: accentColor
  };

  const strokeColor = colorMap[color];
  const uniqueId = React.useId().replace(/:/g, ''); // Ensure valid ID for gradient
  const gradientId = `sparkline-${color}-${uniqueId}`;

  return (
    <div className={cn("relative", className)} style={{ width, height, minHeight: typeof height === 'number' ? height : undefined }}>
      <SizedResponsiveContainer width="100%" height="100%">
        {showArea ? (
          <AreaChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={strokeColor} stopOpacity={0.4} />
                <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <YAxis domain={['dataMin', 'dataMax']} hide />
            <Area
              type="monotone"
              dataKey="value"
              stroke={strokeColor}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              isAnimationActive={false}
            />
          </AreaChart>
        ) : (
          <LineChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
             <YAxis domain={['dataMin', 'dataMax']} hide />
            <Line
              type="monotone"
              dataKey="value"
              stroke={strokeColor}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        )}
      </SizedResponsiveContainer>
    </div>
  );
};
