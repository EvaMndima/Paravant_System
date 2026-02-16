import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { cn } from '../../lib/utils';
import { hoverCard } from '../../lib/animations';

export interface GlassCardProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  variant?: 'default' | 'elevated' | 'subtle' | 'dark';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  enableHover?: boolean;
  className?: string;
  onClick?: (event: React.MouseEvent<HTMLDivElement>) => void;
}

const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ 
    className, 
    variant = 'default', 
    padding = 'md',
    enableHover = false,
    children, 
    ...props 
  }, ref) => {
    
    const variants = {
      default: "bg-paper-100/80 dark:bg-obsidian-300/60 backdrop-blur-xl border border-deep-teal-800/10 dark:border-white/10 shadow-lg",
      elevated: "bg-paper-50/90 dark:bg-obsidian-300/80 backdrop-blur-2xl border border-deep-teal-800/10 dark:border-white/10 shadow-2xl",
      subtle: "bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-md border border-deep-teal-800/5 dark:border-white/5",
      dark: "bg-deep-teal-800/95 dark:bg-obsidian-400/90 text-paper-100 backdrop-blur-xl border border-white/10 shadow-xl",
    };

    const paddings = {
      none: "p-0",
      sm: "p-3",
      md: "p-6",
      lg: "p-8"
    };

    return (
      <motion.div
        ref={ref}
        className={cn(
          "rounded-2xl transition-colors duration-300",
          variants[variant],
          paddings[padding],
          className
        )}
        whileHover={enableHover ? hoverCard : undefined}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

GlassCard.displayName = "GlassCard";

export { GlassCard };