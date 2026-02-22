import React from 'react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { usePnlHeatmap } from '@/hooks';
import { formatPercent } from '@/lib/utils';
import type { HeatmapCell } from '@/types/api';

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Interpolate an RGB color from white toward red (negative) or green (positive).
 * t = 0 → white, t = 1 → full red/green
 */
function heatColor(returnPct: number, maxAbsReturn: number): string {
  const t = Math.min(Math.abs(returnPct) / Math.max(maxAbsReturn, 0.01), 1);
  if (returnPct > 0) {
    // white → #2ecc71 (gain)
    const r = Math.round(255 * (1 - t) + 46 * t);
    const g = Math.round(255 * (1 - t) + 204 * t);
    const b = Math.round(255 * (1 - t) + 113 * t);
    return `rgb(${r},${g},${b})`;
  } else if (returnPct < 0) {
    // white → #e74c3c (loss)
    const r = Math.round(255 * (1 - t) + 231 * t);
    const g = Math.round(255 * (1 - t) + 76 * t);
    const b = Math.round(255 * (1 - t) + 60 * t);
    return `rgb(${r},${g},${b})`;
  }
  return 'rgb(255,255,255)';
}

/** Determine readable text color given a background interpolated toward dark/light. */
function textColor(returnPct: number, maxAbsReturn: number): string {
  const t = Math.min(Math.abs(returnPct) / Math.max(maxAbsReturn, 0.01), 1);
  return t > 0.5 ? '#fff' : '#1a1a2e';
}

export interface MonthlyHeatmapProps {
  /** Optional className forwarded to the outer GlassCard */
  className?: string;
}

/**
 * Monthly returns heatmap: rows=years, columns=months (Jan–Dec).
 * Color scale: red (negative) → white (zero) → green (positive).
 * Cell content: return_pct % + trade count. PRD §6.3.2
 */
export const MonthlyHeatmap: React.FC<MonthlyHeatmapProps> = ({ className }) => {
  const { data, isLoading } = usePnlHeatmap(3);

  if (isLoading) {
    return <Skeleton className={`h-[300px] rounded-2xl ${className ?? ''}`} />;
  }

  const cells = data?.cells ?? [];
  const years = data?.years ?? [];

  if (cells.length === 0) {
    return (
      <GlassCard variant="subtle" className={`h-full ${className ?? ''}`}>
        <h3 className="font-display text-lg font-medium mb-4">Monthly Returns</h3>
        <div className="h-[250px] flex items-center justify-center text-obsidian-400/40 dark:text-paper-100/40 text-sm">
          No monthly return data available
        </div>
      </GlassCard>
    );
  }

  // Build O(1) lookup by "year-month" key
  const cellIndex = new Map<string, HeatmapCell>();
  cells.forEach((c) => cellIndex.set(`${c.year}-${c.month}`, c));

  const maxAbs = Math.max(...cells.map((c) => Math.abs(c.return_pct)), 0.01);

  return (
    <GlassCard variant="subtle" className={`h-full ${className ?? ''}`}>
      <h3 className="font-display text-lg font-medium mb-4">Monthly Returns</h3>
      <div className="overflow-x-auto">
        {/* Month header row */}
        <div
          className="grid gap-1 mb-1"
          style={{ gridTemplateColumns: '3rem repeat(12, 1fr)' }}
        >
          <div />
          {MONTH_LABELS.map((m) => (
            <div
              key={m}
              className="text-center text-[10px] font-mono uppercase text-obsidian-400/50 dark:text-paper-100/50"
            >
              {m}
            </div>
          ))}
        </div>

        {/* Year data rows */}
        {years.map((year) => (
          <div
            key={year}
            className="grid gap-1 mb-1"
            style={{ gridTemplateColumns: '3rem repeat(12, 1fr)' }}
          >
            <div className="text-[10px] font-mono text-obsidian-400/50 dark:text-paper-100/50 flex items-center justify-end pr-2">
              {year}
            </div>
            {Array.from({ length: 12 }, (_, i) => {
              const cell = cellIndex.get(`${year}-${i + 1}`);
              const bg = cell ? heatColor(cell.return_pct, maxAbs) : undefined;
              const fg = cell ? textColor(cell.return_pct, maxAbs) : undefined;
              return (
                <div
                  key={i}
                  className="aspect-square rounded text-center flex flex-col items-center justify-center transition-opacity hover:opacity-80 cursor-default"
                  style={{
                    backgroundColor: bg ?? 'rgba(128,128,128,0.08)',
                    color: fg,
                  }}
                  title={
                    cell
                      ? `${MONTH_LABELS[i]} ${year}: ${formatPercent(cell.return_pct)} (${cell.trade_count} trades)`
                      : `${MONTH_LABELS[i]} ${year}: no data`
                  }
                >
                  {cell ? (
                    <>
                      <span className="text-[9px] font-mono font-bold leading-tight">
                        {cell.return_pct > 0 ? '+' : ''}
                        {cell.return_pct.toFixed(1)}%
                      </span>
                      <span className="text-[8px] opacity-60 leading-tight">
                        {cell.trade_count}T
                      </span>
                    </>
                  ) : (
                    <span className="text-[9px] opacity-20">—</span>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </GlassCard>
  );
};
