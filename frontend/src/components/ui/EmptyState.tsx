import React from 'react';
import { motion } from 'framer-motion';
import { Search, AlertCircle, Inbox } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { fadeInUp } from '@/lib/animations';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  variant?: 'default' | 'search' | 'error';
  className?: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon,
  action,
  variant = 'default',
  className,
}) => {
  const DisplayIcon = Icon || (variant === 'search' ? Search : variant === 'error' ? AlertCircle : Inbox);

  const colors = {
    default: "text-obsidian-400/30 dark:text-paper-100/30 bg-obsidian-400/5 dark:bg-white/5",
    search: "text-turquoise-mist/50 bg-turquoise-mist/10",
    error: "text-loss/50 bg-loss/10",
  };

  return (
    <motion.div
      variants={fadeInUp}
      initial="initial"
      animate="animate"
      className={cn("flex flex-col items-center justify-center text-center p-8 min-h-[250px]", className)}
    >
      <div className={cn("p-4 rounded-full mb-4 transition-colors", colors[variant])}>
        <DisplayIcon className="w-8 h-8" strokeWidth={1.5} />
      </div>
      <h3 className="text-lg font-display font-medium text-obsidian-400 dark:text-paper-100 mb-1">
        {title}
      </h3>
      <p className="text-sm text-obsidian-400/50 dark:text-paper-100/50 max-w-sm mb-6 leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-2">{action}</div>}
    </motion.div>
  );
};

export { EmptyState };
