
import React, { useState, useEffect, useRef } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Sector
} from 'recharts';
import { SizedResponsiveContainer } from './SizedResponsiveContainer';
import { cn, formatPercent } from '@/lib/utils';
import { useTheme } from '@/contexts/ThemeContext';

export interface DonutSegment {
  name: string;
  value: number;
  color: string;
  [key: string]: any;
}

export interface DonutChartProps {
  data: DonutSegment[];
  height?: number;
  innerRadius?: string | number;
  outerRadius?: string | number;
  showLabels?: boolean;
  showLegend?: boolean;
  centerContent?: React.ReactNode;
  className?: string;
}

interface TooltipState {
  name: string;
  value: number;
  color: string;
}

interface MousePos {
  x: number;
  y: number;
  /** Container width captured with the cursor, so render never reads the ref. */
  containerWidth: number;
}

// Custom Active Shape for Hover Effect
const renderActiveShape = (props: any) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;

  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 4}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        className="drop-shadow-lg transition-all duration-300"
      />
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={innerRadius - 2}
        outerRadius={innerRadius}
        fill={fill}
        fillOpacity={0.5}
      />
    </g>
  );
};

export const DonutChart: React.FC<DonutChartProps> = ({
  data,
  height = 300,
  innerRadius = "60%",
  outerRadius = "80%",
  showLabels: _showLabels = false,
  showLegend = true,
  centerContent,
  className,
}) => {
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const [tooltipData, setTooltipData] = useState<TooltipState | null>(null);
  const [mousePos, setMousePos] = useState<MousePos | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { appTheme, mode } = useTheme();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const checkDark = () => {
      if (typeof window === 'undefined') return false;
      return mode === 'dark' || (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    };
    setIsDark(checkDark());
  }, [mode]);

  const getThemePalette = () => {
    if (isDark) {
      switch (appTheme) {
        case 'sapphire': return ['#60A5FA', '#3B82F6', '#93C5FD', '#2563EB', '#1E40AF'];
        case 'emerald': return ['#34D399', '#10B981', '#6EE7B7', '#059669', '#047857'];
        case 'onyx': return ['#FCD34D', '#D4AF37', '#F59E0B', '#FFFBEB', '#78350F'];
        case 'ocean':
        default: return ['#2A9D8F', '#48CAE4', '#90E0EF', '#F4A261', '#E76F51'];
      }
    } else {
      switch (appTheme) {
        case 'sapphire': return ['#3B82F6', '#1E3A8A', '#60A5FA', '#93C5FD', '#2563EB'];
        case 'emerald': return ['#10B981', '#064E3B', '#34D399', '#6EE7B7', '#059669'];
        case 'onyx': return ['#D4AF37', '#18181B', '#B45309', '#71717A', '#F59E0B'];
        case 'ocean':
        default: return ['#2A9D8F', '#264653', '#E9C46A', '#F4A261', '#E76F51'];
      }
    }
  };

  const colors = getThemePalette();

  const themedData = data.map((item, index) => ({
    ...item,
    color: colors[index % colors.length]
  }));

  const showTooltipFor = (index: number) => {
    const item = themedData[index];
    setActiveIndex(index);
    setTooltipData({ name: item.name, value: item.value, color: item.color });
  };

  const hideTooltip = () => {
    setActiveIndex(-1);
    setTooltipData(null);
    setMousePos(null);
  };

  const onPieEnter = (_: any, index: number) => {
    showTooltipFor(index);
  };

  const onPieLeave = () => {
    hideTooltip();
  };

  // Track cursor position within the chart container for floating tooltip
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      containerWidth: containerRef.current.offsetWidth,
    });
  };

  const handleContainerLeave = () => {
    // Only hide if activeIndex was set from segment hover (not legend)
    if (mousePos !== null) {
      hideTooltip();
    }
  };

  // Tooltip offset — flip horizontally so it stays inside the container
  const getTooltipStyle = (): React.CSSProperties => {
    // Reads state, not the ref. Accessing containerRef.current during render
    // can leave the tooltip positioned from a stale layout; the width is
    // captured in the mousemove handler, where refs are legitimate.
    if (!mousePos) return {};
    const containerWidth = mousePos.containerWidth;
    const offsetX = 14;
    const offsetY = -40;
    const flipThreshold = containerWidth * 0.6;
    return {
      left: mousePos.x > flipThreshold
        ? mousePos.x - offsetX
        : mousePos.x + offsetX,
      top: mousePos.y + offsetY,
      transform: mousePos.x > flipThreshold ? 'translateX(-100%)' : 'translateX(0)',
    };
  };

  return (
    <div className={cn("flex flex-col items-center justify-center w-full", className)}>
      {/* Chart area — position:relative anchors the floating tooltip */}
      <div
        ref={containerRef}
        className="relative w-full"
        style={{ width: '100%', height, minHeight: height }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleContainerLeave}
      >
        {/* Floating cursor-following tooltip */}
        {tooltipData && mousePos && (
          <div
            className="absolute z-20 pointer-events-none bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md border border-white/10 shadow-xl rounded-lg px-3 py-2 flex items-center gap-2 whitespace-nowrap"
            style={getTooltipStyle()}
          >
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: tooltipData.color }}
            />
            <div>
              <div className="text-paper-100/60 font-sans text-xs leading-none mb-0.5">
                {tooltipData.name}
              </div>
              <div className="text-paper-100 font-mono text-sm font-medium">
                {formatPercent(tooltipData.value)}
              </div>
            </div>
          </div>
        )}

        {/* debounce={1} prevents the Recharts width(-1)/height(-1) warning on mount */}
        <SizedResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={themedData}
              cx="50%"
              cy="50%"
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              dataKey="value"
              onMouseEnter={onPieEnter}
              onMouseLeave={onPieLeave}
              stroke="none"
              paddingAngle={2}
              {...({
                activeIndex,
                activeShape: renderActiveShape
              } as any)}
            >
              {themedData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  className="transition-opacity duration-300 outline-none"
                  style={{
                    opacity: activeIndex === -1 || activeIndex === index ? 1 : 0.6
                  }}
                />
              ))}
            </Pie>
          </PieChart>
        </SizedResponsiveContainer>

        {/* Center Content Overlay */}
        {centerContent && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="pointer-events-auto">
              {centerContent}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      {showLegend && (
        <div className="flex flex-wrap justify-center gap-3 mt-4 w-full">
          {themedData.map((entry, index) => (
            <div
              key={entry.name}
              className={cn(
                "flex items-center gap-2 px-2 py-1 rounded-md transition-opacity duration-200 cursor-default",
                activeIndex !== -1 && activeIndex !== index ? "opacity-40" : "opacity-100"
              )}
              onMouseEnter={() => {
                showTooltipFor(index);
                setMousePos(null); // legend hover: no cursor pos, so tooltip won't render
              }}
              onMouseLeave={hideTooltip}
            >
              <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className="text-xs font-sans text-obsidian-400 dark:text-paper-100">
                {entry.name}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
