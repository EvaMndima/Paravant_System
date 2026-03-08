import React from 'react';
import { motion } from 'framer-motion';
import { StrategyCard } from './StrategyCard';
import type { StrategyCardProps } from './StrategyCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { staggerContainer, fadeInUp } from '@/lib/animations';
import { cn } from '@/lib/utils';

export interface StrategyGridProps {
  strategies: StrategyCardProps[];
  isLoading?: boolean;
  onStrategyClick?: (id: string) => void;
  className?: string;
}

export const StrategyGrid: React.FC<StrategyGridProps> = ({
  strategies,
  isLoading = false,
  onStrategyClick,
  className,
}) => {
  if (isLoading) {
    return (
      <div className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6', className)}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-[240px] rounded-2xl overflow-hidden bg-obsidian-400/5 dark:bg-white/5 border border-deep-teal-800/5 dark:border-white/5 p-6 flex flex-col gap-4 animate-pulse"
          >
            <div className="flex justify-between items-start">
              <Skeleton variant="text" className="w-1/2 h-6" />
              <Skeleton variant="circle" className="w-3 h-3" />
            </div>
            <Skeleton variant="text" className="w-1/3 h-4" />
            <div className="grid grid-cols-3 gap-4 mt-4">
              <Skeleton variant="text" className="h-8" />
              <Skeleton variant="text" className="h-8" />
              <Skeleton variant="text" className="h-8" />
            </div>
            <div className="mt-auto flex justify-between items-center">
              <Skeleton variant="text" className="w-1/3 h-4" />
              <div className="flex gap-2">
                <Skeleton variant="circle" className="w-8 h-8" />
                <Skeleton variant="circle" className="w-8 h-8" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6', className)}
    >
      {strategies.map((strategy) => (
        <motion.div key={strategy.id} variants={fadeInUp}>
          <StrategyCard {...strategy} onClick={onStrategyClick} />
        </motion.div>
      ))}
    </motion.div>
  );
};
