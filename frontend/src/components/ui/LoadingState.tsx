import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface LoadingStateProps {
  variant?: 'page' | 'section' | 'inline';
  message?: string;
  className?: string;
}

const LoadingState: React.FC<LoadingStateProps> = ({
  variant = 'section',
  message = 'Loading...',
  className,
}) => {
  if (variant === 'inline') {
    return (
      <div className={cn("flex items-center gap-2 text-sm text-obsidian-400/50 dark:text-paper-100/50", className)}>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>{message}</span>
      </div>
    );
  }

  if (variant === 'page') {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-paper-100/80 dark:bg-obsidian-400/80 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-deep-teal-600 to-deep-teal-800 dark:from-turquoise-mist dark:to-deep-teal-600 flex items-center justify-center shadow-xl">
              <span className="font-display font-bold text-2xl text-white">P</span>
            </div>
            <div className="absolute -inset-4 border-2 border-deep-teal-800/20 dark:border-turquoise-mist/20 rounded-[24px] animate-pulse" />
          </div>
          <p className="text-sm font-mono uppercase tracking-widest text-deep-teal-800 dark:text-turquoise-mist animate-pulse">
            {message}
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col items-center justify-center min-h-[200px] p-8", className)}>
      <Loader2 className="w-8 h-8 text-turquoise-mist animate-spin mb-3" />
      <p className="text-xs font-mono uppercase tracking-wide text-obsidian-400/40 dark:text-paper-100/40">
        {message}
      </p>
    </div>
  );
};

export { LoadingState };
