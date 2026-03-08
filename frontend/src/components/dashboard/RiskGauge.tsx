import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Shield, AlertTriangle, AlertOctagon } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { cn, formatNumber } from '@/lib/utils';

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

// SVG arc parameters
const RADIUS = 70;
const STROKE_WIDTH = 10;
const CENTER = 90;
// Arc spans 220 degrees: from 160deg to 380deg (20deg past 0)
const ARC_START_DEG = 160;
const ARC_SWEEP_DEG = 220;

function polarToCartesian(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}

function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number): string {
  const start = polarToCartesian(cx, cy, r, startDeg);
  const end = polarToCartesian(cx, cy, r, endDeg);
  const largeArc = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

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

  // Arc calculations
  const trackPath = useMemo(
    () => describeArc(CENTER, CENTER, RADIUS, ARC_START_DEG, ARC_START_DEG + ARC_SWEEP_DEG),
    []
  );

  const fillEndDeg = ARC_START_DEG + (ARC_SWEEP_DEG * pct) / 100;
  const fillPath = useMemo(
    () => pct > 0
      ? describeArc(CENTER, CENTER, RADIUS, ARC_START_DEG, Math.max(ARC_START_DEG + 2, fillEndDeg))
      : '',
    [pct, fillEndDeg]
  );

  // Needle angle: maps 0% -> ARC_START_DEG, 100% -> ARC_START_DEG + ARC_SWEEP_DEG
  const needleAngle = ARC_START_DEG + (ARC_SWEEP_DEG * pct) / 100;
  const needleTip = polarToCartesian(CENTER, CENTER, RADIUS - 8, needleAngle);

  // Arc length for dash animation
  const arcLength = Math.PI * RADIUS * (ARC_SWEEP_DEG / 180);
  const fillLength = (arcLength * pct) / 100;

  return (
    <GlassCard variant="default" padding="md" className={cn('flex flex-col items-center', className)}>
      {/* SVG Gauge */}
      <div className="relative w-[180px] h-[120px]">
        <svg viewBox="0 0 180 120" className="w-full h-full overflow-visible">
          <defs>
            <filter id="gauge-glow">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {/* Background track */}
          <path
            d={trackPath}
            fill="none"
            stroke={config.trackColor}
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
          />

          {/* Filled arc */}
          {pct > 0 && (
            <motion.path
              d={fillPath}
              fill="none"
              stroke={config.color}
              strokeWidth={STROKE_WIDTH}
              strokeLinecap="round"
              filter="url(#gauge-glow)"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: pct / 100 }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
              style={{ filter: `drop-shadow(0 0 4px ${config.glowColor})` }}
            />
          )}

          {/* Tick marks at 25%, 50%, 75% */}
          {[25, 50, 75].map(tick => {
            const tickAngle = ARC_START_DEG + (ARC_SWEEP_DEG * tick) / 100;
            const outer = polarToCartesian(CENTER, CENTER, RADIUS + 6, tickAngle);
            const inner = polarToCartesian(CENTER, CENTER, RADIUS + 2, tickAngle);
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

          {/* Needle */}
          <motion.line
            x1={CENTER}
            y1={CENTER}
            x2={needleTip.x}
            y2={needleTip.y}
            stroke={config.color}
            strokeWidth={2}
            strokeLinecap="round"
            initial={{ rotate: 0, originX: CENTER, originY: CENTER }}
            animate={{
              x2: needleTip.x,
              y2: needleTip.y,
            }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
          />
          <circle cx={CENTER} cy={CENTER} r={4} fill={config.color} />
        </svg>

        {/* Centre value overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="font-mono font-bold text-2xl leading-none text-obsidian-400 dark:text-paper-100"
          >
            {formatNumber(pct, 0)}%
          </motion.span>
        </div>
      </div>

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

      {/* Capital detail */}
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
              transition={{ duration: 1.2, ease: 'easeOut' }}
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
