import React, { useState, useRef, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn, formatCurrency } from '@/lib/utils';
import { useTheme } from '@/contexts/ThemeContext';
import type { AreaChartData } from '@/components/charts/AreaChart';

export type { AreaChartData };

export interface SVGAreaChartProps {
  data: AreaChartData[];
  height?: number;
  showGrid?: boolean;
  gradientId?: string;
  className?: string;
  curveTension?: number;
}

export const SVGAreaChart: React.FC<SVGAreaChartProps> = ({
  data,
  height = 300,
  showGrid = true,
  gradientId = 'svg-gradient',
  className,
  curveTension = 0.2,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const { mode, appTheme } = useTheme();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const checkDark = () => {
      if (typeof window === 'undefined') return false;
      return (
        mode === 'dark' ||
        (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
      );
    };
    setIsDark(checkDark());
  }, [mode]);

  // Accent color follows active theme and light/dark mode
  const accentColor = (() => {
    if (isDark) {
      switch (appTheme) {
        case 'sapphire': return '#60A5FA';
        case 'emerald':  return '#34D399';
        case 'onyx':     return '#FCD34D';
        case 'ocean':
        default:         return '#48CAE4';
      }
    }
    switch (appTheme) {
      case 'sapphire': return '#3B82F6';
      case 'emerald':  return '#10B981';
      case 'onyx':     return '#D4AF37';
      case 'ocean':
      default:         return '#2A9D8F';
    }
  })();

  // Normalize data points to 0-1 coordinate space
  const { points } = useMemo(() => {
    if (!data.length) return { points: [] };

    const values = data.map(d => d.value);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const padding = (maxVal - minVal) * 0.1;
    const safeMin = minVal - padding;
    const safeMax = maxVal + padding;
    const range = safeMax - safeMin || 1;

    const pts = data.map((d, i) => ({
      x: i / Math.max(data.length - 1, 1),
      y: 1 - (d.value - safeMin) / range, // inverted: SVG y=0 is top
      original: d,
    }));

    return { points: pts };
  }, [data]);

  // Build bezier path — control points create smooth curves while preserving shape
  const buildPath = (pts: typeof points, close: boolean): string => {
    if (!pts.length) return '';

    let d = `M ${pts[0].x * 100} ${pts[0].y * 100}`;

    for (let i = 0; i < pts.length - 1; i++) {
      const cur  = pts[i];
      const next = pts[i + 1];
      const dx   = (next.x - cur.x) * curveTension;

      const cp1x = (cur.x  + dx) * 100;
      const cp1y = cur.y  * 100;
      const cp2x = (next.x - dx) * 100;
      const cp2y = next.y * 100;

      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${next.x * 100} ${next.y * 100}`;
    }

    if (close) d += ' L 100 100 L 0 100 Z';

    return d;
  };

  const linePath = buildPath(points, false);
  const areaPath = buildPath(points, true);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current || !points.length) return;
    const rect = containerRef.current.getBoundingClientRect();
    const relX = (e.clientX - rect.left) / rect.width;
    const idx  = Math.min(Math.max(Math.round(relX * (data.length - 1)), 0), data.length - 1);
    setHoverIndex(idx);
  };

  const hoverPt = hoverIndex !== null ? points[hoverIndex] : null;

  return (
    <div
      ref={containerRef}
      className={cn('relative w-full select-none cursor-crosshair', className)}
      style={{ height }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoverIndex(null)}
    >
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="overflow-visible"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor={accentColor} stopOpacity={0.4} />
            <stop offset="90%" stopColor={accentColor} stopOpacity={0}   />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {showGrid && (
          <g className="opacity-10 dark:opacity-[0.18] text-deep-teal-800 dark:text-white" stroke="currentColor" strokeWidth="0.2" strokeDasharray="2 2">
            <line x1="0" y1="25" x2="100" y2="25" />
            <line x1="0" y1="50" x2="100" y2="50" />
            <line x1="0" y1="75" x2="100" y2="75" />
          </g>
        )}

        {/* Gradient fill */}
        <motion.path
          d={areaPath}
          fill={`url(#${gradientId})`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        />

        {/* Stroke line — animates on mount */}
        <motion.path
          d={linePath}
          fill="none"
          stroke={accentColor}
          strokeWidth="0.5"
          vectorEffect="non-scaling-stroke"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.4, ease: 'easeInOut' }}
        />

        {/* Hover crosshair */}
        {hoverPt && (
          <>
            <line
              x1={hoverPt.x * 100} y1="0"
              x2={hoverPt.x * 100} y2="100"
              stroke={accentColor}
              strokeWidth="1"
              strokeDasharray="2 2"
              vectorEffect="non-scaling-stroke"
              className="opacity-50"
            />
            <circle
              cx={hoverPt.x * 100}
              cy={hoverPt.y * 100}
              r="1.5"
              fill={isDark ? '#1A1A2E' : '#F8F5F2'}
              stroke={accentColor}
              strokeWidth="0.5"
              vectorEffect="non-scaling-stroke"
            />
          </>
        )}
      </svg>

      {/* Tooltip */}
      {hoverPt && hoverIndex !== null && (
        <div
          className="absolute top-0 pointer-events-none z-10"
          style={{ left: `${hoverPt.x * 100}%`, transform: 'translateX(-50%)' }}
        >
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: -44 }}
            transition={{ duration: 0.12 }}
            className="bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md border border-white/10 shadow-xl rounded-lg px-3 py-2 min-w-[130px] text-center"
          >
            <p className="text-paper-100/60 font-sans text-[10px] mb-0.5">
              {data[hoverIndex].date}
            </p>
            <p className="text-paper-100 font-mono text-base font-medium tracking-tight">
              {formatCurrency(data[hoverIndex].value)}
            </p>
          </motion.div>
        </div>
      )}
    </div>
  );
};
