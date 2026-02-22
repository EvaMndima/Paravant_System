/**
 * PositionDetailDrawer — per 7.3.7
 *
 * Slide-in panel from the right showing full position detail.
 * Currently read-only in MVP. Includes a "Close Position" trigger
 * that opens the PositionCloseModal.
 *
 * Uses PositionResponse type + StalenessEntry for staleness badge.
 */
import React, { useState } from 'react';
import { X, Clock, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PositionResponse } from '@/types/api';
import { PositionCloseModal } from '@/components/modals/PositionCloseModal';
import { cn } from '@/lib/utils';

export interface PositionDetailDrawerProps {
  isOpen: boolean;
  position: PositionResponse | null;
  staleDays?: number | null;
  onClose: () => void;
}

function formatNumber(value: number, decimals = 2): string {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatDateTime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

function durationHours(openedAt: string): number {
  try {
    return (Date.now() - new Date(openedAt).getTime()) / 3_600_000;
  } catch {
    return 0;
  }
}

interface StatRowProps {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}

const StatRow: React.FC<StatRowProps> = ({ label, value, mono = true }) => (
  <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-none">
    <span className="text-xs text-paper-100/40">{label}</span>
    <span className={cn('text-sm font-medium', mono && 'font-mono')}>{value}</span>
  </div>
);

export const PositionDetailDrawer: React.FC<PositionDetailDrawerProps> = ({
  isOpen,
  position,
  staleDays,
  onClose,
}) => {
  const [closeModalOpen, setCloseModalOpen] = useState(false);

  const isLong = position?.side === 'LONG';
  const pnlPositive = (position?.unrealized_pnl ?? 0) >= 0;
  const hoursHeld = position ? durationHours(position.opened_at) : 0;
  const isStale = staleDays !== null && staleDays !== undefined && staleDays > 0;

  return (
    <>
      <AnimatePresence>
        {isOpen && position && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[60] bg-obsidian-400/50 backdrop-blur-sm"
              onClick={onClose}
            />

            {/* Drawer */}
            <motion.aside
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 350, damping: 35 }}
              className={cn(
                'fixed top-0 right-0 h-full z-[70] w-full max-w-sm',
                'bg-obsidian-300 border-l border-white/10 shadow-2xl',
                'flex flex-col overflow-hidden',
              )}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div
                className={cn(
                  'flex items-center justify-between px-6 py-5 border-b border-white/10',
                  'bg-gradient-to-br',
                  isLong ? 'from-gain/10 to-transparent' : 'from-loss/10 to-transparent',
                )}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-lg">{position.symbol}</span>
                    <span
                      className={cn(
                        'text-[11px] font-bold uppercase px-2 py-0.5 rounded-full',
                        isLong ? 'bg-gain/20 text-gain' : 'bg-loss/20 text-loss',
                      )}
                    >
                      {position.side}
                    </span>
                    {isStale && (
                      <span className="flex items-center gap-1 text-[11px] text-warning font-mono bg-warning/10 px-1.5 py-0.5 rounded-full">
                        <AlertCircle className="w-3 h-3" />
                        Stale
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-paper-100/40 mt-0.5 font-mono">
                    {formatDateTime(position.opened_at)}
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                  aria-label="Close drawer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* P&L Hero */}
              <div className="px-6 py-5 border-b border-white/10">
                <p className="text-xs text-paper-100/40 mb-1">Unrealized P&amp;L</p>
                <div className="flex items-end gap-2">
                  {pnlPositive ? (
                    <TrendingUp className="w-5 h-5 text-gain mb-0.5" />
                  ) : (
                    <TrendingDown className="w-5 h-5 text-loss mb-0.5" />
                  )}
                  <span
                    className={cn(
                      'text-3xl font-mono font-bold',
                      pnlPositive ? 'text-gain' : 'text-loss',
                    )}
                  >
                    {pnlPositive ? '+' : ''}{formatNumber(position.unrealized_pnl)} USDT
                  </span>
                </div>
                <p
                  className={cn(
                    'text-sm font-mono mt-0.5',
                    pnlPositive ? 'text-gain/70' : 'text-loss/70',
                  )}
                >
                  {pnlPositive ? '+' : ''}{formatNumber(position.return_pct)}%
                </p>
              </div>

              {/* Stats */}
              <div className="flex-1 overflow-y-auto px-6 py-4">
                <div className="space-y-0">
                  <StatRow label="Quantity" value={formatNumber(position.size, 6)} />
                  <StatRow label="Entry Price" value={`$${formatNumber(position.entry_price)}`} />
                  <StatRow label="Current Price" value={`$${formatNumber(position.current_price)}`} />
                  <StatRow label="Realized P&L" value={
                    <span className={position.realized_pnl >= 0 ? 'text-gain' : 'text-loss'}>
                      {position.realized_pnl >= 0 ? '+' : ''}{formatNumber(position.realized_pnl)} USDT
                    </span>
                  } mono={false} />
                  <StatRow label="Commission Paid" value={`${formatNumber(position.commission_paid)} USDT`} />
                  <StatRow label="Status" value={
                    <span className="text-xs uppercase font-bold tracking-wider">{position.status}</span>
                  } mono={false} />
                  <StatRow
                    label="Time Held"
                    value={
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-paper-100/40" />
                        {hoursHeld < 24
                          ? `${formatNumber(hoursHeld, 1)}h`
                          : `${formatNumber(hoursHeld / 24, 1)}d`}
                      </span>
                    }
                    mono={false}
                  />
                  {position.strategy_id && (
                    <StatRow label="Strategy" value={
                      <span className="text-xs font-mono text-paper-100/60 truncate max-w-[140px]">
                        {position.strategy_id}
                      </span>
                    } mono={false} />
                  )}
                </div>
              </div>

              {/* Footer Actions */}
              <div className="px-6 py-4 border-t border-white/10 space-y-2">
                <button
                  onClick={() => setCloseModalOpen(true)}
                  className={cn(
                    'w-full py-3 rounded-xl text-sm font-bold transition-all',
                    'bg-loss/10 hover:bg-loss/20 text-loss border border-loss/20 hover:border-loss/50',
                  )}
                >
                  Close Position
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Close position confirmation modal */}
      <PositionCloseModal
        isOpen={closeModalOpen}
        position={position}
        onClose={() => setCloseModalOpen(false)}
        onSuccess={onClose}
      />
    </>
  );
};
