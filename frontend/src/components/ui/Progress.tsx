import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { smoothSpring } from '@/lib/animations';

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  size?: 'sm' | 'md';
  variant?: 'default' | 'success' | 'warning' | 'danger';
  showLabel?: boolean;
  animated?: boolean;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ value, max = 100, size = 'md', variant = 'default', showLabel = false, animated = true, className, ...props }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

    const variants = {
      default: "bg-turquoise-mist shadow-[0_0_12px_rgba(42,157,143,0.4)]",
      success: "bg-gain shadow-[0_0_12px_rgba(46,204,113,0.4)]",
      warning: "bg-warning shadow-[0_0_12px_rgba(243,156,18,0.4)]",
      danger: "bg-loss shadow-[0_0_12px_rgba(231,76,60,0.4)]"
    };

    const heights = { sm: "h-1.5", md: "h-2.5" };

    return (
      <div ref={ref} className={cn("w-full flex items-center gap-3", className)} {...props}>
        <div className={cn("flex-1 bg-obsidian-400/5 dark:bg-white/10 rounded-full overflow-hidden backdrop-blur-sm", heights[size])}>
          <motion.div
            className={cn("h-full rounded-full", variants[variant])}
            initial={animated ? { width: 0 } : { width: `${percentage}%` }}
            animate={{ width: `${percentage}%` }}
            transition={{ ...smoothSpring, duration: 1.5 }}
          />
        </div>
        {showLabel && (
          <div className="min-w-[2.5rem] text-right">
            <span className="font-mono text-xs font-medium text-obsidian-400/60 dark:text-paper-100/60 tabular-nums">
              {Math.round(percentage)}%
            </span>
          </div>
        )}
      </div>
    );
  }
);

Progress.displayName = "Progress";

export { Progress };
