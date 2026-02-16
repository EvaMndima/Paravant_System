import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import { fadeInUp } from '../../lib/animations';
import { Breadcrumbs, BreadcrumbItem } from './Breadcrumbs';

export interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  actions,
  breadcrumbs,
  className
}) => {
  return (
    <motion.div
      variants={fadeInUp}
      initial="initial"
      animate="animate"
      className={cn("space-y-6 mb-10", className)}
    >
      {breadcrumbs && (
        <div className="flex justify-center md:justify-start">
           <Breadcrumbs items={breadcrumbs} />
        </div>
      )}

      <div className="flex flex-col md:flex-row items-center md:items-end justify-between gap-6 text-center md:text-left">
        <div className="space-y-2 max-w-3xl">
          <h1 className="font-display text-3xl md:text-4xl font-medium text-obsidian-400 dark:text-paper-100 tracking-tight leading-tight">
            {title}
          </h1>
          {description && (
            <p className="text-obsidian-400/60 dark:text-paper-100/60 font-light text-lg leading-relaxed">
              {description}
            </p>
          )}
        </div>
        
        {actions && (
          <div className="flex items-center gap-3 shrink-0 w-full md:w-auto justify-center md:justify-end">
            {actions}
          </div>
        )}
      </div>
    </motion.div>
  );
};