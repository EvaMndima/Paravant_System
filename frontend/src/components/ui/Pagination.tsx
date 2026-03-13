import React from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  className?: string;
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
  className,
}) => {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  // Build visible page numbers with ellipsis
  const getPageNumbers = (): (number | 'ellipsis')[] => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    if (page <= 4) return [1, 2, 3, 4, 5, 'ellipsis', totalPages];
    if (page >= totalPages - 3) return [1, 'ellipsis', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
    return [1, 'ellipsis', page - 1, page, page + 1, 'ellipsis', totalPages];
  };

  const pageNumbers = getPageNumbers();

  const btnBase = cn(
    'inline-flex items-center justify-center rounded-lg text-xs font-mono font-medium transition-colors duration-150',
    'focus:outline-none focus:ring-2 focus:ring-turquoise-mist/40',
    'h-8 w-8'
  );

  const btnNav = cn(
    btnBase,
    'text-obsidian-400/60 dark:text-paper-100/60',
    'hover:bg-deep-teal-800/5 dark:hover:bg-white/5',
    'disabled:opacity-30 disabled:pointer-events-none'
  );

  return (
    <div className={cn('flex items-center justify-between gap-4 flex-wrap', className)}>
      {/* Count info */}
      <div className="text-[11px] font-mono text-obsidian-400/50 dark:text-paper-100/50 shrink-0">
        {total === 0 ? 'No results' : `${from}–${to} of ${total.toLocaleString()}`}
      </div>

      {/* Page controls */}
      <div className="flex items-center gap-1">
        {/* First + Prev */}
        <button
          className={btnNav}
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
          aria-label="First page"
        >
          <ChevronsLeft className="w-3.5 h-3.5" />
        </button>
        <button
          className={btnNav}
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>

        {/* Page numbers */}
        {pageNumbers.map((p, idx) =>
          p === 'ellipsis' ? (
            <span
              key={`ellipsis-${idx}`}
              className="h-8 w-8 inline-flex items-center justify-center text-xs font-mono text-obsidian-400/30 dark:text-paper-100/30"
            >
              ...
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p as number)}
              aria-current={p === page ? 'page' : undefined}
              className={cn(
                btnBase,
                p === page
                  ? 'bg-turquoise-mist text-white shadow-sm'
                  : 'text-obsidian-400/70 dark:text-paper-100/70 hover:bg-deep-teal-800/5 dark:hover:bg-white/5'
              )}
            >
              {p}
            </button>
          )
        )}

        {/* Next + Last */}
        <button
          className={btnNav}
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
        <button
          className={btnNav}
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
          aria-label="Last page"
        >
          <ChevronsRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Page size selector */}
      {onPageSizeChange && (
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px] font-mono text-obsidian-400/50 dark:text-paper-100/50">Rows</span>
          <select
            value={pageSize}
            onChange={e => {
              onPageSizeChange(Number(e.target.value));
              onPageChange(1);
            }}
            className={cn(
              'h-8 px-2 text-xs font-mono rounded-lg border',
              'border-deep-teal-800/15 dark:border-white/10',
              'bg-deep-teal-800/5 dark:bg-white/5',
              'text-obsidian-400 dark:text-paper-100',
              'focus:outline-none focus:ring-2 focus:ring-turquoise-mist/40'
            )}
          >
            {pageSizeOptions.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};
