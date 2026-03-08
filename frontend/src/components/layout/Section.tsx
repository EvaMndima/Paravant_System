import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { smoothSpring } from '@/lib/animations';

export interface SectionProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  actions?: React.ReactNode;
}

export const Section: React.FC<SectionProps> = ({
  title,
  description,
  children,
  className,
  headerClassName,
  contentClassName,
  collapsible = false,
  defaultCollapsed = false,
  actions,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  const toggleCollapse = () => {
    if (collapsible) setIsCollapsed(!isCollapsed);
  };

  return (
    <div className={cn("w-full py-4", className)}>
      {(title || description || collapsible || actions) && (
        <div
          onClick={collapsible ? toggleCollapse : undefined}
          className={cn(
            "flex items-end justify-between mb-6 pb-3 border-b border-deep-teal-800/10 dark:border-white/5",
            collapsible && "cursor-pointer group select-none",
            headerClassName
          )}
        >
          <div className="space-y-1">
            {title && (
              <h3 className={cn(
                "text-xs font-mono font-bold uppercase tracking-widest transition-colors",
                collapsible
                  ? "text-obsidian-400/50 dark:text-paper-100/50 group-hover:text-deep-teal-800 dark:group-hover:text-turquoise-mist"
                  : "text-obsidian-400/40 dark:text-paper-100/40"
              )}>
                {title}
              </h3>
            )}
            {description && (
              <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60 font-sans max-w-prose">
                {description}
              </p>
            )}
          </div>

          <div className="flex items-center gap-4">
            {actions && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="cursor-auto"
              >
                {actions}
              </div>
            )}

            {collapsible && (
              <div className="text-obsidian-400/40 dark:text-paper-100/40 group-hover:text-deep-teal-800 dark:group-hover:text-turquoise-mist transition-colors p-1">
                {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              </div>
            )}
          </div>
        </div>
      )}

      <AnimatePresence initial={false}>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={smoothSpring}
            className={cn("overflow-hidden", contentClassName)}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
