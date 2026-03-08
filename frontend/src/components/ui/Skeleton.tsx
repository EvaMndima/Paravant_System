import React from 'react';
import { cn } from '@/lib/utils';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circle' | 'card' | 'chart';
}

const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, variant = 'text', ...props }, ref) => {

    const variants = {
      text: "h-4 w-full rounded-md",
      circle: "h-10 w-10 rounded-full",
      card: "h-24 w-full rounded-xl",
      chart: "h-40 w-full rounded-lg"
    };

    return (
      <div
        ref={ref}
        className={cn(
          "animate-pulse bg-obsidian-400/5 dark:bg-white/5",
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);

Skeleton.displayName = "Skeleton";

export { Skeleton };
