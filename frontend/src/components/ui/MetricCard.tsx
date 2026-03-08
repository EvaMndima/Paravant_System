import React from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { GlassCard } from './GlassCard';
import type { GlassCardProps } from './GlassCard';
import { cn, formatCurrency, formatNumber } from '@/lib/utils';

export interface MetricCardProps extends Omit<GlassCardProps, 'children' | 'padding'> {
  title: string;
  value: number;
  change?: number;
  changeLabel?: string;
  prefix?: string;
  suffix?: string;
  icon?: LucideIcon;
  format?: 'currency' | 'number' | 'percent' | 'raw';
  sparkline?: React.ReactNode;
  delay?: number;
}

const MetricCard = React.forwardRef<HTMLDivElement, MetricCardProps>(
  ({
    title,
    value,
    change,
    changeLabel = "vs last period",
    prefix,
    suffix,
    icon: Icon,
    variant = 'default',
    format,
    sparkline,
    className,
    delay = 0,
    ...props
  }, ref) => {
    const formattedValue = React.useMemo(() => {
      if (format === 'raw') return value;
      if (format === 'currency' || prefix === '$') return formatCurrency(value);
      if (format === 'percent') return `${formatNumber(value)}%`;
      return formatNumber(value);
    }, [value, format, prefix]);

    // Adaptive font size: shrink when the value string is long to prevent overflow
    const valueFontSize = React.useMemo(() => {
      const totalLen = String(formattedValue).length + (suffix?.length ?? 0);
      if (totalLen <= 7) return 'text-3xl';
      if (totalLen <= 11) return 'text-2xl';
      return 'text-xl';
    }, [formattedValue, suffix]);

    const trend = change ? (change > 0 ? 'up' : change < 0 ? 'down' : 'neutral') : 'neutral';

    const trendColors = {
      up: "text-gain",
      down: "text-loss",
      neutral: "text-obsidian-400/40 dark:text-paper-100/40",
    };

    const TrendIcon = { up: ArrowUpRight, down: ArrowDownRight, neutral: Minus }[trend];

    const isDark = variant === 'dark';

    const titleStyles = isDark
      ? "text-turquoise-mist opacity-90"
      : "text-obsidian-400/50 dark:text-paper-100/50";

    const valueStyles = isDark
      ? "text-paper-50"
      : "text-deep-teal-800 dark:text-paper-100";

    const iconContainerStyles = isDark
      ? "bg-white/10 text-turquoise-mist"
      : "bg-deep-teal-800/5 dark:bg-white/5 text-deep-teal-800 dark:text-turquoise-mist";

    return (
      <GlassCard
        ref={ref}
        variant={variant}
        padding="md"
        className={cn("flex flex-col relative overflow-hidden min-h-[140px] justify-between", className)}
        enableHover={true}
        {...props}
      >
        <div className="flex justify-between items-start z-20 relative">
          <h3 className={cn("text-xs font-mono font-bold uppercase tracking-widest truncate pr-2 mt-1", titleStyles)}>
            {title}
          </h3>
          {Icon && (
            <div className={cn("p-1.5 rounded-lg backdrop-blur-sm shrink-0", iconContainerStyles)}>
              <Icon className="w-4 h-4" strokeWidth={1.5} />
            </div>
          )}
        </div>

        <div className="flex items-end justify-between mt-4 z-20 relative">
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: delay + 0.1, duration: 0.3 }}
            className={cn(
              "font-mono font-medium tracking-tighter tabular-nums leading-none",
              valueFontSize,
              valueStyles
            )}
          >
            {format === 'currency' || prefix === '$' ? formattedValue : (
              <>
                {prefix && <span className="opacity-60 text-[0.6em] mr-0.5 align-top">{prefix}</span>}
                {formattedValue}
                {suffix && <span className="opacity-60 text-[0.4em] ml-1 align-top">{suffix}</span>}
              </>
            )}
          </motion.div>

          {change !== undefined ? (
            <motion.div
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: delay + 0.2 }}
              className="flex flex-col items-end mb-0.5"
            >
              <div className={cn("flex items-center gap-1 text-sm font-mono font-bold", trendColors[trend])}>
                <TrendIcon className="w-4 h-4 shrink-0" strokeWidth={2} />
                <span>{Math.abs(change)}%</span>
              </div>
              {changeLabel && (
                <span className="text-[10px] text-obsidian-400/40 dark:text-paper-100/40 font-sans text-right hidden sm:inline-block">
                  {changeLabel}
                </span>
              )}
            </motion.div>
          ) : <div />}
        </div>

        {sparkline && (
          <div className="absolute bottom-0 left-0 right-0 h-20 z-0 pointer-events-none opacity-30 dark:opacity-40 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-b from-paper-100/90 via-transparent to-transparent dark:from-obsidian-300/90 dark:via-transparent dark:to-transparent z-10" />
            <div className="h-full w-full transform translate-y-2">
              {sparkline}
            </div>
          </div>
        )}
      </GlassCard>
    );
  }
);

MetricCard.displayName = "MetricCard";

export { MetricCard };
