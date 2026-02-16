import React, { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown, Inbox } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Skeleton } from '../ui/Skeleton';
import { smoothSpring } from '../../lib/animations';
import { motion, AnimatePresence } from 'framer-motion';

export interface Column<T> {
  key: string;
  header: string;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  render?: (value: any, row: T) => React.ReactNode;
  width?: string;
  className?: string; // Added for responsive hiding (e.g., 'hidden md:table-cell')
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  isLoading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  stickyHeader?: boolean;
  className?: string;
}

type SortDirection = 'asc' | 'desc' | null;

interface SortConfig {
  key: string | null;
  direction: SortDirection;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  isLoading = false,
  emptyMessage = "No data available",
  onRowClick,
  stickyHeader = false,
  className,
}: DataTableProps<T>) {
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: null, direction: null });

  const handleSort = (key: string) => {
    setSortConfig((current) => {
      if (current.key === key) {
        if (current.direction === 'asc') return { key, direction: 'desc' };
        if (current.direction === 'desc') return { key: null, direction: null };
      }
      return { key, direction: 'asc' };
    });
  };

  const sortedData = useMemo(() => {
    if (!sortConfig.key || !sortConfig.direction) return data;

    return [...data].sort((a, b) => {
      const aValue = a[sortConfig.key!];
      const bValue = b[sortConfig.key!];

      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, sortConfig]);

  return (
    <div className={cn("w-full overflow-hidden rounded-xl bg-transparent", className)}>
      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full border-collapse text-left">
          <thead className={cn(
            "bg-deep-teal-800/5 dark:bg-white/5",
            stickyHeader && "sticky top-0 z-20 backdrop-blur-md"
          )}>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={cn(
                    "px-6 py-4 text-xs font-mono font-medium uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 select-none whitespace-nowrap transition-colors",
                    col.align === 'right' && "text-right",
                    col.align === 'center' && "text-center",
                    col.sortable && "cursor-pointer hover:text-deep-teal-800 dark:hover:text-turquoise-mist group",
                    col.className, // Apply responsive classes here
                    col.width
                  )}
                  style={{ width: col.width }}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <div className={cn(
                    "flex items-center gap-1",
                    col.align === 'right' && "justify-end",
                    col.align === 'center' && "justify-center"
                  )}>
                    {col.header}
                    {col.sortable && (
                      <span className="flex flex-col opacity-0 group-hover:opacity-50 data-[active=true]:opacity-100 transition-opacity" data-active={sortConfig.key === col.key}>
                         {sortConfig.key === col.key && sortConfig.direction === 'asc' ? (
                             <ChevronUp className="w-3 h-3 text-turquoise-mist" />
                         ) : sortConfig.key === col.key && sortConfig.direction === 'desc' ? (
                             <ChevronDown className="w-3 h-3 text-turquoise-mist" />
                         ) : (
                             <ChevronsUpDown className="w-3 h-3" />
                         )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          
          <tbody className="divide-y divide-deep-teal-800/5 dark:divide-white/5 font-sans">
            {isLoading ? (
              // Skeleton Loading Rows
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="animate-pulse">
                  {columns.map((col, j) => (
                    <td key={j} className={cn("px-6 py-4", col.className)}>
                      <Skeleton className="h-5 w-full bg-obsidian-400/5 dark:bg-white/5 rounded" />
                    </td>
                  ))}
                </tr>
              ))
            ) : sortedData.length === 0 ? (
              // Empty State
              <tr>
                <td colSpan={columns.length} className="px-6 py-12 text-center">
                  <div className="flex flex-col items-center justify-center text-obsidian-400/30 dark:text-paper-100/30">
                    <div className="bg-deep-teal-800/5 dark:bg-white/5 p-4 rounded-full mb-3">
                        <Inbox className="w-8 h-8" strokeWidth={1} />
                    </div>
                    <p className="text-sm font-medium font-mono">{emptyMessage}</p>
                  </div>
                </td>
              </tr>
            ) : (
              // Data Rows
              <AnimatePresence initial={false} mode="wait">
                  {sortedData.map((row, index) => (
                    <motion.tr
                      key={index} // Ideally use a stable ID from data if available
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: index * 0.03, duration: 0.2 }}
                      onClick={() => onRowClick?.(row)}
                      className={cn(
                        "group transition-colors duration-200",
                        "hover:bg-deep-teal-800/5 dark:hover:bg-white/5",
                        onRowClick && "cursor-pointer active:bg-deep-teal-800/10 dark:active:bg-white/10"
                      )}
                    >
                      {columns.map((col) => (
                        <td
                          key={col.key}
                          className={cn(
                            "px-6 py-4 text-sm whitespace-nowrap",
                            col.align === 'right' && "text-right",
                            col.align === 'center' && "text-center",
                            "text-obsidian-400 dark:text-paper-100",
                            col.className // Apply responsive classes here too
                          )}
                        >
                          {col.render ? col.render(row[col.key], row) : row[col.key]}
                        </td>
                      ))}
                    </motion.tr>
                  ))}
              </AnimatePresence>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}