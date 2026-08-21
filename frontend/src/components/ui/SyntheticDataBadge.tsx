/**
 * Visible marker that the values beside it are not from a real account.
 *
 * Rendered by every chart and table whose data is not explicitly `'live'`.
 * Carries `data-testid="synthetic-data-badge"` because `provenance.test.tsx`
 * enumerates chart components and asserts each one shows it.
 *
 * @see ../../lib/provenance for why the default is to show this rather than hide it
 */
import React from 'react';
import { AlertTriangle } from 'lucide-react';

import { cn } from '@/lib/utils';

export interface SyntheticDataBadgeProps {
  /** Optional extra classes for positioning within a card header. */
  className?: string;
  /** Shorter form for tight headers. The full form is used by default. */
  compact?: boolean;
}

/**
 * A small amber banner reading "Sample data".
 *
 * Deliberately not dismissible and not subtle. A label a reader can close, or
 * one rendered in muted grey at the bottom of a card, is a label that has been
 * technically applied rather than actually communicated.
 */
export const SyntheticDataBadge: React.FC<SyntheticDataBadgeProps> = ({
  className,
  compact = false,
}) => (
  <span
    data-testid="synthetic-data-badge"
    role="note"
    aria-label="These values are sample data, not from a real account"
    title="Generated in the browser for layout purposes. Not from a real account."
    className={cn(
      'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5',
      'text-[11px] font-medium leading-none',
      'border-amber-500/40 bg-amber-500/10 text-amber-600',
      'dark:border-amber-400/30 dark:bg-amber-400/10 dark:text-amber-300',
      className,
    )}
  >
    <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
    {compact ? 'Sample' : 'Sample data'}
  </span>
);
