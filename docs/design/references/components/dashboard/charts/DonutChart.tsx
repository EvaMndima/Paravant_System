
import React, { useState, useEffect } from 'react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  Tooltip,
  Sector
} from 'recharts';
import { cn, formatPercent } from '../../../lib/utils';
import { useTheme } from '../../../contexts/ThemeContext';

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

// Custom Active Shape for Hover Effect
const renderActiveShape = (props: any) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;

  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 4} // Expand slightly
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
  showLabels = false,
  showLegend = true,
  centerContent,
  className,
}) => {
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const { appTheme, mode } = useTheme();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const checkDark = () => {
      if (typeof window === 'undefined') return false;
      return mode === 'dark' || (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    };
    setIsDark(checkDark());
  }, [mode]);

  // Dynamic color palette based on active theme AND mode
  const getThemePalette = () => {
    if (isDark) {
      // High contrast palettes for Dark Mode
      switch (appTheme) {
        case 'sapphire': return ['#60A5FA', '#3B82F6', '#93C5FD', '#2563EB', '#1E40AF']; // Brighter Blues
        case 'emerald': return ['#34D399', '#10B981', '#6EE7B7', '#059669', '#047857']; // Brighter Greens
        case 'onyx': return ['#FCD34D', '#D4AF37', '#F59E0B', '#FFFBEB', '#78350F']; // Bright Golds & Ambers
        case 'ocean':
        default: return ['#2A9D8F', '#48CAE4', '#90E0EF', '#F4A261', '#E76F51']; // Ocean Brights
      }
    } else {
      // Standard palettes for Light Mode
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

  const onPieEnter = (_: any, index: number) => {
    setActiveIndex(index);
  };
  
  const onPieLeave = () => {
    setActiveIndex(-1);
  };

  return (
    <div className={cn("flex flex-col items-center justify-center w-full", className)}>
      <div className="relative w-full" style={{ width: '100%', height: height, minHeight: height }}>
        <ResponsiveContainer width="100%" height="100%">
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
            
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                   const { name, value, color } = payload[0].payload;
                   return (
                     <div className="bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-2 flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                        <div>
                           <div className="text-paper-100/60 font-sans text-xs">{name}</div>
                           <div className="text-paper-100 font-mono text-sm">{formatPercent(value)}</div>
                        </div>
                     </div>
                   );
                }
                return null;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        
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
               onMouseEnter={() => setActiveIndex(index)}
               onMouseLeave={() => setActiveIndex(-1)}
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
