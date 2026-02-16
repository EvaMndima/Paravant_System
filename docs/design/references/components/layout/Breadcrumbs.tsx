import React from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ items, className }) => {
  return (
    <nav 
      aria-label="Breadcrumb"
      className={cn("flex items-center flex-wrap gap-2 text-sm font-sans", className)}
    >
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <React.Fragment key={index}>
            {index > 0 && (
              <ChevronRight 
                className="w-4 h-4 text-obsidian-400/30 dark:text-paper-100/30 flex-shrink-0" 
                strokeWidth={1.5} 
              />
            )}
            
            {isLast ? (
              <span 
                aria-current="page"
                className="font-medium text-obsidian-400 dark:text-paper-100 cursor-default"
              >
                {item.label}
              </span>
            ) : (
              <a
                href={item.href || '#'}
                className="text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-turquoise-mist transition-colors duration-200"
              >
                {item.label}
              </a>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
