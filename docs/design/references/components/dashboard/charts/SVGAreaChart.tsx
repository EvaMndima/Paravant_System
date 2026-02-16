
import React, { useState, useRef, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn, formatCurrency } from '../../../lib/utils';
import { useTheme } from '../../../contexts/ThemeContext';

export interface AreaChartData {
  date: string;
  value: number;
}

export interface SVGAreaChartProps {
  data: AreaChartData[];
  height?: number;
  showGrid?: boolean;
  gradientId?: string;
  className?: string;
  curveTension?: number; // 0 = straight lines, 0.4 = smooth curves
}

export const SVGAreaChart: React.FC<SVGAreaChartProps> = ({
  data,
  height = 300,
  showGrid = true,
  gradientId = "svg-gradient",
  className,
  curveTension = 0.2
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const { mode, appTheme } = useTheme();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Determine if dark mode is active based on mode setting
    const checkDark = () => {
      if (typeof window === 'undefined') return false;
      return mode === 'dark' || (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    };
    setIsDark(checkDark());
  }, [mode]);

  // Dynamic color selection based on active theme
  const getThemeColor = () => {
    if (isDark) {
        // High contrast for Dark Mode
        switch (appTheme) {
          case 'sapphire': return '#60A5FA'; 
          case 'emerald': return '#34D399';
          case 'onyx': return '#FCD34D';
          case 'ocean':
          default: return '#48CAE4';
        }
    }
    // Standard for Light Mode
    switch (appTheme) {
      case 'sapphire': return '#3B82F6';
      case 'emerald': return '#10B981';
      case 'onyx': return '#D4AF37';
      case 'ocean':
      default: return '#2A9D8F';
    }
  };

  const accentColor = getThemeColor();

  // 1. Calculate Dimensions & Scales
  const { min, max, points } = useMemo(() => {
    if (!data.length) return { min: 0, max: 0, points: [] };

    const values = data.map(d => d.value);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const padding = (maxVal - minVal) * 0.1; // 10% padding top/bottom

    const safeMin = minVal - padding;
    const safeMax = maxVal + padding;
    const range = safeMax - safeMin;

    const points = data.map((d, i) => ({
      x: i / (data.length - 1), // Normalized 0-1
      y: 1 - (d.value - safeMin) / range, // Normalized 0-1 (inverted for SVG y-axis)
      original: d
    }));

    return { min: safeMin, max: safeMax, points };
  }, [data]);

  // 2. Generate SVG Path (Catmull-Rom spline or simple line)
  // Simple implementation using bezier curves for smoothing
  const generatePath = (pts: typeof points, close: boolean) => {
    if (pts.length === 0) return "";

    // Move to first point
    let path = `M ${pts[0].x * 100} ${pts[0].y * 100}`;

    // Draw curves
    for (let i = 0; i < pts.length - 1; i++) {
        const current = pts[i];
        const next = pts[i + 1];
        
        // Control points for smoothing
        const cp1x = (current.x + (next.x - current.x) * curveTension) * 100;
        const cp1y = current.y * 100;
        
        const cp2x = (next.x - (next.x - current.x) * curveTension) * 100;
        const cp2y = next.y * 100;

        const nextX = next.x * 100;
        const nextY = next.y * 100;

        path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${nextX} ${nextY}`;
    }

    if (close) {
        // Close shape for gradient fill
        path += ` L 100 100 L 0 100 Z`;
    }

    return path;
  };

  const linePath = generatePath(points, false);
  const areaPath = generatePath(points, true);

  // 3. Interaction Handlers
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const width = rect.width;
    
    // Find closest data point
    const relativeX = x / width;
    const index = Math.min(
      Math.max(Math.round(relativeX * (data.length - 1)), 0),
      data.length - 1
    );
    setHoverIndex(index);
  };

  return (
    <div 
      ref={containerRef}
      className={cn("relative w-full select-none cursor-crosshair group", className)}
      style={{ height }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoverIndex(null)}
    >
        {/* Main SVG */}
        <svg 
            width="100%" 
            height="100%" 
            viewBox="0 0 100 100" 
            preserveAspectRatio="none"
            className="overflow-visible"
        >
            <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={accentColor} stopOpacity={0.4} />
                    <stop offset="90%" stopColor={accentColor} stopOpacity={0} />
                </linearGradient>
            </defs>

            {/* Grid Lines */}
            {showGrid && (
                <g className={cn("opacity-10 stroke-deep-teal-800", isDark ? "dark:opacity-20 dark:stroke-white" : "")}>
                    <line x1="0" y1="25" x2="100" y2="25" strokeWidth="0.2" strokeDasharray="2 2" />
                    <line x1="0" y1="50" x2="100" y2="50" strokeWidth="0.2" strokeDasharray="2 2" />
                    <line x1="0" y1="75" x2="100" y2="75" strokeWidth="0.2" strokeDasharray="2 2" />
                </g>
            )}

            {/* Area Fill */}
            <motion.path
                d={areaPath}
                fill={`url(#${gradientId})`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 1 }}
            />

            {/* Stroke Line */}
            <motion.path
                d={linePath}
                fill="none"
                stroke={accentColor}
                strokeWidth="0.5" // Relative to viewBox 100x100
                vectorEffect="non-scaling-stroke"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.5, ease: "easeInOut" }}
            />

            {/* Active Hover Line */}
            {hoverIndex !== null && (
                <line 
                    x1={points[hoverIndex].x * 100} 
                    y1="0" 
                    x2={points[hoverIndex].x * 100} 
                    y2="100" 
                    stroke={accentColor} 
                    strokeWidth="1"
                    strokeDasharray="2 2"
                    vectorEffect="non-scaling-stroke"
                    className="opacity-50"
                />
            )}
            
            {/* Active Point Dot */}
            {hoverIndex !== null && (
                <circle 
                   cx={points[hoverIndex].x * 100}
                   cy={points[hoverIndex].y * 100}
                   r="1.5"
                   fill="#F8F5F2" // paper
                   stroke={accentColor}
                   strokeWidth="0.5"
                   vectorEffect="non-scaling-stroke"
                   className={cn(isDark ? "dark:fill-obsidian-400" : "")}
                />
            )}
        </svg>

        {/* HTML Tooltip Overlay */}
        {hoverIndex !== null && (
            <div 
                className="absolute top-0 pointer-events-none z-10"
                style={{ 
                    left: `${points[hoverIndex].x * 100}%`,
                    transform: 'translateX(-50%)'
                }}
            >
                <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: -40 }} // Move up
                    className="bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-3 min-w-[140px] text-center"
                >
                    <p className="text-paper-100/60 font-sans text-xs mb-1">
                        {data[hoverIndex].date}
                    </p>
                    <p className="text-paper-100 font-mono text-lg font-medium tracking-tight">
                        {formatCurrency(data[hoverIndex].value)}
                    </p>
                </motion.div>
            </div>
        )}
    </div>
  );
};
