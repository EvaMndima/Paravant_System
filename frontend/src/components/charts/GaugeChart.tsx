import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

// Arc math constants: semi-circle with radius 80, center at (100, 100)
// SVG path: M 20,100 A 80,80 0 0,1 180,100 (upper semicircle, clockwise)
const GAUGE_R = 80;
const GAUGE_CX = 100;
const GAUGE_CY = 100;
// Total arc length of a semicircle: pi * r
const ARC_LEN = Math.PI * GAUGE_R; // ~251.33

/**
 * Map usage percentage (0-100) to a color:
 * - 0-50%: green (safe zone)
 * - 50-80%: amber (warning zone)
 * - 80-100%: red (critical zone)
 */
function gaugeColor(pct: number): string {
  if (pct >= 80) return '#EF4444'; // red-500
  if (pct >= 50) return '#F59E0B'; // amber-500
  return '#10B981';                 // emerald-500
}

/**
 * Returns a Tailwind stroke class so tests can use toHaveClass() checks.
 * Maps the same zones as gaugeColor().
 */
function gaugeColorClass(pct: number): string {
  if (pct >= 80) return 'stroke-loss';
  if (pct >= 50) return 'stroke-neutral';
  return 'stroke-gain';
}

export interface GaugeChartProps {
  /**
   * Current usage as a percentage of the limit (0-100).
   * e.g. pass 25 if you are at 25% of the configured limit.
   */
  value: number;
  /** Short label displayed below the gauge (e.g. "Daily Loss") */
  label: string;
  /** Pre-formatted current value string shown in the center (e.g. "1.20%") */
  currentDisplay: string;
  /** Pre-formatted limit string shown at the right end-tick (e.g. "10%") */
  limitDisplay: string;
  className?: string;
}

/**
 * Semi-circular SVG gauge component used on the Risk page.
 * Renders a track arc + animated fill arc with color zones,
 * a center readout, and end-tick scale labels.
 *
 * PRD: Risk Monitoring (GAP-04)
 */
export const GaugeChart: React.FC<GaugeChartProps> = ({
  value,
  label,
  currentDisplay,
  limitDisplay,
  className,
}) => {
  const clamped = Math.min(Math.max(value, 0), 100);
  // How many SVG units of arc to fill: fills from left endpoint clockwise
  const fillLen = (clamped / 100) * ARC_LEN;
  const color = gaugeColor(clamped);

  // SVG arc path string (re-used for both track and value arc)
  const arcPath = `M ${GAUGE_CX - GAUGE_R},${GAUGE_CY} A ${GAUGE_R},${GAUGE_R} 0 0,1 ${GAUGE_CX + GAUGE_R},${GAUGE_CY}`;

  return (
    <div className={cn('flex flex-col items-center', className)}>
      <svg
        viewBox="0 0 200 120"
        aria-hidden="true"
        className="w-full max-w-[180px]"
        style={{ overflow: 'visible' }}
      >
        {/* Background track: full semicircle at low opacity */}
        <path
          d={arcPath}
          fill="none"
          stroke="currentColor"
          strokeWidth="14"
          strokeLinecap="round"
          opacity="0.12"
        />

        {/* Value arc: animated fill using stroke-dasharray/offset technique */}
        <motion.path
          data-testid="gauge-arc"
          d={arcPath}
          fill="none"
          stroke={color}
          className={gaugeColorClass(clamped)}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={ARC_LEN}
          initial={{ strokeDashoffset: ARC_LEN }}
          animate={{ strokeDashoffset: ARC_LEN - fillLen }}
          transition={{ duration: 1.2, ease: 'easeOut', delay: 0.1 }}
        />

        {/* Center readout: current value */}
        <text
          x={GAUGE_CX}
          y={GAUGE_CY - 14}
          textAnchor="middle"
          fill="currentColor"
          fontSize="22"
          fontWeight="600"
        >
          {currentDisplay}
        </text>

        {/* Percentage of limit label */}
        <text
          x={GAUGE_CX}
          y={GAUGE_CY + 6}
          textAnchor="middle"
          fill="currentColor"
          fontSize="11"
          opacity="0.50"
          fontFamily="monospace"
        >
          {clamped.toFixed(0)}% of limit
        </text>

        {/* Left tick: "0" label */}
        <text
          x={GAUGE_CX - GAUGE_R - 4}
          y={GAUGE_CY + 18}
          textAnchor="end"
          fill="currentColor"
          fontSize="9"
          opacity="0.35"
          fontFamily="monospace"
        >
          0
        </text>

        {/* Right tick: limit value label */}
        <text
          x={GAUGE_CX + GAUGE_R + 4}
          y={GAUGE_CY + 18}
          textAnchor="start"
          fill="currentColor"
          fontSize="9"
          opacity="0.35"
          fontFamily="monospace"
        >
          {limitDisplay}
        </text>
      </svg>

      {/* Label below gauge */}
      <span className="mt-1 text-xs font-mono font-bold uppercase tracking-widest opacity-50">
        {label}
      </span>
    </div>
  );
};
