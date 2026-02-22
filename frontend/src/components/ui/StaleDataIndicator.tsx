/**
 * StaleDataIndicator — Shows "Last updated: X min ago" with color tinting.
 *
 * Usage: Place inside card footers driven by SSE data.
 * - < 30s: no indicator shown
 * - 30s–2min: yellow timestamp + subtle yellow tint on card
 * - > 2min: red timestamp + red tint on card
 */
import React, { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface StaleDataIndicatorProps {
  /** Timestamp of last SSE update (Date or ISO string). Null = never updated. */
  lastUpdatedAt: Date | string | null;
  /** Additional className for the indicator text. */
  className?: string;
}

function useRelativeTime(date: Date | string | null): { label: string; staleness: 'fresh' | 'stale' | 'very-stale' } {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(id);
  }, []);

  if (!date) return { label: 'Never updated', staleness: 'very-stale' };

  const elapsed = now - new Date(date).getTime();
  const seconds = Math.floor(elapsed / 1000);

  if (seconds < 30) return { label: 'Just now', staleness: 'fresh' };

  const minutes = Math.floor(seconds / 60);
  const label = minutes < 1
    ? `${seconds}s ago`
    : minutes === 1
      ? '1 min ago'
      : `${minutes} min ago`;

  const staleness = elapsed > 2 * 60_000 ? 'very-stale' : 'stale';
  return { label, staleness };
}

export const StaleDataIndicator: React.FC<StaleDataIndicatorProps> = ({
  lastUpdatedAt,
  className,
}) => {
  const { label, staleness } = useRelativeTime(lastUpdatedAt);

  if (staleness === 'fresh') return null;

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 text-[10px] font-mono',
        staleness === 'very-stale' ? 'text-loss/80' : 'text-warning/80',
        className,
      )}
    >
      <Clock className="w-3 h-3 flex-shrink-0" />
      <span>Last updated: {label}</span>
    </div>
  );
};

/** CSS class to apply to the parent card when data is stale */
export function getStaleCardClass(lastUpdatedAt: Date | string | null): string {
  if (!lastUpdatedAt) return '';
  const elapsed = Date.now() - new Date(lastUpdatedAt).getTime();
  if (elapsed > 2 * 60_000) return 'ring-1 ring-loss/20 bg-loss/5';
  if (elapsed > 30_000) return 'ring-1 ring-warning/20 bg-warning/5';
  return '';
}
