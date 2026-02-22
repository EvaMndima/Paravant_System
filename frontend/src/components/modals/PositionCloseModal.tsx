/**
 * PositionCloseModal — per 7.3.3
 *
 * Displays key position data (symbol, side, PnL) and requires confirmation
 * before closing. Uses useClosePosition mutation (takes symbol: string).
 */
import React, { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useClosePosition } from '@/hooks';
import { useToast } from '@/contexts/ToastContext';
import { cn } from '@/lib/utils';

/**
 * Minimal position shape needed to close. Both DashboardPositionEntry
 * and PositionResponse satisfy this interface.
 */
export interface ClosablePosition {
  symbol: string;
  side: string;
  /** quantity (DashboardPositionEntry) or size (PositionResponse) */
  quantity?: number;
  size?: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
}

export interface PositionCloseModalProps {
  isOpen: boolean;
  position: ClosablePosition | null;
  onClose: () => void;
  onSuccess?: () => void;
}

function formatPnl(value: number): { text: string; positive: boolean } {
  const positive = value >= 0;
  return {
    text: `${positive ? '+' : ''}${value.toFixed(2)} USDT`,
    positive,
  };
}

export const PositionCloseModal: React.FC<PositionCloseModalProps> = ({
  isOpen,
  position,
  onClose,
  onSuccess,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const closeMutation = useClosePosition();
  const { addToast } = useToast();

  if (!isOpen || !position) return null;

  const pnl = formatPnl(position.unrealized_pnl);

  const handleConfirm = async () => {
    setIsLoading(true);
    try {
      // Backend closes by symbol
      await closeMutation.mutateAsync(position.symbol);
      addToast(
        'success',
        'Position closed',
        `${position.symbol} ${position.side} position closed at market price.`,
      );
      onSuccess?.();
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to close position';
      addToast('error', 'Close failed', msg);
      // Keep modal open on error so user can retry/cancel
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[80] bg-obsidian-400/70 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Dialog */}
          <div className="fixed inset-0 z-[90] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 12 }}
              transition={{ type: 'spring', stiffness: 400, damping: 35 }}
              className="w-full max-w-sm bg-obsidian-300 rounded-2xl border border-white/10 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
                <div className="p-2 rounded-lg bg-loss/20">
                  <AlertTriangle className="w-5 h-5 text-loss" />
                </div>
                <div>
                  <h2 className="font-serif text-lg font-bold">Close Position</h2>
                  <p className="text-xs text-paper-100/50 font-mono">Market close — immediate fill</p>
                </div>
              </div>

              {/* Position Summary */}
              <div className="px-6 py-5 space-y-3">
                <div className="rounded-lg bg-obsidian-400/50 border border-white/5 p-4 space-y-3">
                  {/* Symbol + Side */}
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-lg">{position.symbol}</span>
                    <span
                      className={cn(
                        'text-xs font-bold uppercase px-2 py-0.5 rounded-full',
                        position.side === 'LONG'
                          ? 'bg-gain/20 text-gain'
                          : 'bg-loss/20 text-loss',
                      )}
                    >
                      {position.side}
                    </span>
                  </div>

                  {/* Details */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-paper-100/40 mb-0.5">Quantity</p>
                      <p className="font-mono font-medium">{position.size ?? position.quantity}</p>
                    </div>
                    <div>
                      <p className="text-paper-100/40 mb-0.5">Entry Price</p>
                      <p className="font-mono font-medium">${position.entry_price.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-paper-100/40 mb-0.5">Current Price</p>
                      <p className="font-mono font-medium">${position.current_price.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-paper-100/40 mb-0.5">Unrealized P&amp;L</p>
                      <p className={cn('font-mono font-bold', pnl.positive ? 'text-gain' : 'text-loss')}>
                        {pnl.text}
                      </p>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-paper-100/50 text-center">
                  A market order will be placed immediately. This cannot be undone.
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-2 px-6 pb-5">
                <button
                  onClick={onClose}
                  disabled={isLoading}
                  className="flex-1 py-2.5 rounded-lg border border-white/10 text-sm text-paper-100/70 hover:bg-white/5 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={isLoading}
                  className={cn(
                    'flex-1 py-2.5 rounded-lg text-sm font-bold transition-all',
                    'bg-loss hover:bg-loss/90 text-white shadow-lg shadow-loss/20',
                    'disabled:opacity-60 disabled:cursor-not-allowed',
                    isLoading && 'animate-pulse',
                  )}
                >
                  {isLoading ? 'Closing…' : 'Close Position'}
                </button>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};
