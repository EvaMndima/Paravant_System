import React, { useEffect } from 'react';
import { motion, animate, useMotionValue, useTransform } from 'framer-motion';
import { Shield, AlertTriangle, AlertOctagon } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { cn } from '@/lib/utils';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface RiskGaugeProps {
  /** Current risk utilization, 0-100 */
  value: number;
  /** Max allowed risk value (denominator), defaults to 100 */
  maxValue?: number;
  label?: string;
  sublabel?: string;
  showDetails?: boolean;
  usedCapital?: number;
  totalCapital?: number;
  className?: string;
}

function getRiskLevel(pct: number): RiskLevel {
  if (pct < 40) return 'low';
  if (pct < 65) return 'medium';
  if (pct < 85) return 'high';
  return 'critical';
}

const levelConfig: Record<RiskLevel, {
  color: string;
  trackColor: string;
  glowColor: string;
  label: string;
  icon: React.ElementType;
  badgeClass: string;
}> = {
  low: {
    color: '#10B981',
    trackColor: 'rgba(16, 185, 129, 0.15)',
    glowColor: 'rgba(16, 185, 129, 0.3)',
    label: 'Low Risk',
    icon: Shield,
    badgeClass: 'text-gain bg-gain/10',
  },
  medium: {
    color: '#F59E0B',
    trackColor: 'rgba(245, 158, 11, 0.15)',
    glowColor: 'rgba(245, 158, 11, 0.3)',
    label: 'Medium Risk',
    icon: AlertTriangle,
    badgeClass: 'text-warning bg-warning/10',
  },
  high: {
    color: '#EF4444',
    trackColor: 'rgba(239, 68, 68, 0.15)',
    glowColor: 'rgba(239, 68, 68, 0.3)',
    label: 'High Risk',
    icon: AlertOctagon,
    badgeClass: 'text-loss bg-loss/10',
  },
  critical: {
    color: '#DC2626',
    trackColor: 'rgba(220, 38, 38, 0.2)',
    glowColor: 'rgba(220, 38, 38, 0.5)',
    label: 'CRITICAL',
    icon: AlertOctagon,
    badgeClass: 'text-loss bg-loss/20 animate-pulse',
  },
};

// SVG arc parameters — horseshoe gauge opening downward
const CX = 90;           // horizontal center
const CY = 70;           // vertical center (shifted up)
const RADIUS = 60;
const STROKE_WIDTH = 10;
const ARC_START_DEG = 225;   // 7:30 — lower-left
const ARC_SWEEP_DEG = 270;   // sweeps clockwise to 4:30 — lower-right

function polarToCartesian(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number): string {
  const start = polarToCartesian(cx, cy, r, startDeg);
  const end = polarToCartesian(cx, cy, r, endDeg);
  const largeArc = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

// Compute the full 270° background track once (static)
const TRACK_PATH = describeArc(CX, CY, RADIUS, ARC_START_DEG, ARC_START_DEG + ARC_SWEEP_DEG);

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  value,
  maxValue = 100,
  label = 'Portfolio Risk',
  sublabel,
  showDetails = true,
  usedCapital,
  totalCapital,
  className,
}) => {
  const pct = Math.min(100, Math.max(0, (value / maxValue) * 100));
  const level = getRiskLevel(pct);
  const config = levelConfig[level];
  const LevelIcon = config.icon;

  // Single motion value drives BOTH the fill arc and the needle.
  // Animates from 0 on mount, and adapts when pct changes — like a donut chart.
  const animPct = useMotionValue(0);

  useEffect(() => {
    const controls = animate(animPct, pct, {
      duration: 1.2,
      ease: [0.16, 1, 0.3, 1], // expo-out: fast initial sweep, smooth settle
    });
    return controls.stop;
  }, [pct]);

  // Fill arc path: recomputed every animation frame from the live pct value.
  // Same angle formula as the needle — both read from animPct so they are
  // always in perfect sync regardless of frame timing.
  const fillArcPath = useTransform(animPct, (p: number) => {
    if (p < 0.1) return '';
    const endDeg = ARC_START_DEG + (ARC_SWEEP_DEG * Math.min(p, 100)) / 100;
    return describeArc(CX, CY, RADIUS, ARC_START_DEG, endDeg);
  });

  // Needle path: a slim clock-hand triangle pointing from pivot to the arc end.
  // Base width = 3px each side. Tip lands exactly at the arc centerline (RADIUS).
  // A short tail stub in the opposite direction gives visual balance.
  const needlePath = useTransform(animPct, (p: number) => {
    const angle = ARC_START_DEG + (ARC_SWEEP_DEG * Math.min(p, 100)) / 100;
    const tip = polarToCartesian(CX, CY, RADIUS, angle);
    // Perpendicular base points at the pivot
    const b1 = polarToCartesian(CX, CY, 2.5, angle + 90);
    const b2 = polarToCartesian(CX, CY, 2.5, angle - 90);
    // Short tail in the opposite direction
    const tail = polarToCartesian(CX, CY, 10, angle + 180);
    return [
      `M ${b1.x.toFixed(2)} ${b1.y.toFixed(2)}`,
      `L ${tip.x.toFixed(2)} ${tip.y.toFixed(2)}`,
      `L ${b2.x.toFixed(2)} ${b2.y.toFixed(2)}`,
      `L ${tail.x.toFixed(2)} ${tail.y.toFixed(2)}`,
      'Z',
    ].join(' ');
  });

  // Percentage label animates in sync with the arc sweep
  const displayPct = useTransform(animPct, (p: number) => `${Math.round(p)}%`);

  return (
    <GlassCard variant="default" padding="md" className={cn('flex flex-col items-center', className)}>
      {/* SVG Gauge */}
      <div className="w-[180px] h-[130px]">
        <svg viewBox="0 0 180 130" className="w-full h-full overflow-visible">
          <defs>
            <filter id={`gauge-glow-${level}`} x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {/* Background track — static full 270° arc */}
          <path
            d={TRACK_PATH}
            fill="none"
            stroke={config.trackColor}
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
          />

          {/* Filled arc — path computed frame-by-frame from animPct.
              No pathLength normalization needed: the path itself grows with the value. */}
          <motion.path
            d={fillArcPath}
            fill="none"
            stroke={config.color}
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 5px ${config.glowColor})` }}
          />

          {/* Tick marks at 25%, 50%, 75% */}
          {[25, 50, 75].map(tick => {
            const tickAngle = ARC_START_DEG + (ARC_SWEEP_DEG * tick) / 100;
            const outer = polarToCartesian(CX, CY, RADIUS + 6, tickAngle);
            const inner = polarToCartesian(CX, CY, RADIUS + 2, tickAngle);
            return (
              <line
                key={tick}
                x1={inner.x} y1={inner.y}
                x2={outer.x} y2={outer.y}
                stroke="currentColor"
                strokeWidth={1}
                className="text-obsidian-400/20 dark:text-paper-100/20"
              />
            );
          })}

          {/* Clock-hand needle — SVG polygon computed directly from animPct.
              No CSS rotation or transform-origin: the tip coordinate IS the arc end.
              Adapts immediately whenever pct changes. */}
          <motion.path
            d={needlePath}
            fill={config.color}
            opacity={0.92}
          />

          {/* Center pivot cap */}
          <circle cx={CX} cy={CY} r={5} fill={config.color} />
          <circle cx={CX} cy={CY} r={2.5} fill="white" opacity={0.85} />
        </svg>
      </div>

      {/* Percentage — animates in sync with the arc sweep */}
      <motion.span
        className="font-mono font-bold text-2xl leading-none text-obsidian-400 dark:text-paper-100 mt-1"
      >
        {displayPct}
      </motion.span>

      {/* Level badge */}
      <div className={cn(
        'mt-2 px-3 py-1 rounded-full text-xs font-mono font-bold flex items-center gap-1.5',
        config.badgeClass
      )}>
        <LevelIcon className="w-3.5 h-3.5" />
        {config.label}
      </div>

      {/* Labels */}
      <div className="mt-3 text-center space-y-0.5">
        <div className="text-sm font-sans font-medium text-obsidian-400 dark:text-paper-100">{label}</div>
        {sublabel && (
          <div className="text-xs font-sans text-obsidian-400/50 dark:text-paper-100/50">{sublabel}</div>
        )}
      </div>

      {/* Capital detail bar */}
      {showDetails && usedCapital !== undefined && totalCapital !== undefined && (
        <div className="mt-3 w-full">
          <div className="flex justify-between text-[10px] font-mono text-obsidian-400/40 dark:text-paper-100/40 mb-1">
            <span>Used</span>
            <span>Available</span>
          </div>
          <div className="relative h-1.5 w-full rounded-full bg-deep-teal-800/10 dark:bg-white/10 overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: config.color }}
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
          <div className="flex justify-between mt-1 text-[10px] font-mono">
            <span className="font-medium" style={{ color: config.color }}>
              ${usedCapital.toLocaleString()}
            </span>
            <span className="text-obsidian-400/50 dark:text-paper-100/50">
              ${(totalCapital - usedCapital).toLocaleString()}
            </span>
          </div>
        </div>
      )}
    </GlassCard>
  );
};
