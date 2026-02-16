import React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'outline';
  size?: 'sm' | 'md';
  dot?: boolean;
  pulsing?: boolean;
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ 
    className, 
    variant = 'neutral', 
    size = 'md', 
    dot = false, 
    pulsing = false,
    children, 
    ...props 
  }, ref) => {
    
    // Soft backgrounds for premium look, rather than solid blocks
    const variants = {
      success: "bg-gain/10 text-gain border-transparent",
      warning: "bg-warning/10 text-warning border-transparent",
      danger: "bg-loss/10 text-loss border-transparent",
      info: "bg-info/10 text-info border-transparent",
      neutral: "bg-obsidian-400/5 text-obsidian-400 dark:bg-paper-100/10 dark:text-paper-100 border-transparent",
      outline: "bg-transparent text-obsidian-400 dark:text-paper-100 border border-obsidian-400/20 dark:border-paper-100/20"
    };

    const sizes = {
      sm: "h-5 px-2 text-[10px] gap-1.5",
      md: "h-6 px-2.5 text-xs gap-2"
    };

    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-full font-mono font-medium tracking-wide border whitespace-nowrap transition-colors",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {dot && (
          <span className="relative flex h-1.5 w-1.5">
            {pulsing && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
            )}
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current"></span>
          </span>
        )}
        {children}
      </div>
    );
  }
);

Badge.displayName = "Badge";

export { Badge };