/**
 * RegimeChangeModal — Confirmation modal for changing the market regime.
 *
 * Shows current → new regime change summary and optional note field.
 * Calls useSetRegime() mutation on confirm.
 *
 * Per 7.3.2: confirmation required before regime change takes effect.
 */
import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

// Regime types from the API
export type RegimeType = 'trending_up' | 'trending_down' | 'ranging' | 'volatile' | 'unknown';

const REGIME_OPTIONS: { value: RegimeType; label: string; color: string; bg: string }[] = [
  { value: 'trending_up',   label: 'Trending Up',   color: 'text-gain',    bg: 'bg-gain/10 border-gain/30' },
  { value: 'trending_down', label: 'Trending Down', color: 'text-loss',    bg: 'bg-loss/10 border-loss/30' },
  { value: 'ranging',       label: 'Ranging',       color: 'text-warning', bg: 'bg-warning/10 border-warning/30' },
  { value: 'volatile',      label: 'Volatile',      color: 'text-loss',    bg: 'bg-loss/10 border-loss/30' },
  { value: 'unknown',       label: 'Unknown',       color: 'text-paper-100/50', bg: 'bg-white/5 border-white/10' },
];

function getRegimeStyle(regime: RegimeType) {
  return REGIME_OPTIONS.find((r) => r.value === regime) ?? REGIME_OPTIONS[4];
}

export interface RegimeChangeModalProps {
  isOpen: boolean;
  currentRegime: RegimeType;
  onClose: () => void;
  onConfirm: (newRegime: RegimeType, note: string) => Promise<void>;
}

export const RegimeChangeModal: React.FC<RegimeChangeModalProps> = ({
  isOpen,
  currentRegime,
  onClose,
  onConfirm,
}) => {
  const [selected, setSelected] = useState<RegimeType>(currentRegime);
  const [note, setNote] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const currentStyle = getRegimeStyle(currentRegime);
  const selectedStyle = getRegimeStyle(selected);
  const isChanged = selected !== currentRegime;

  const handleConfirm = async () => {
    if (!isChanged || isLoading) return;
    setIsLoading(true);
    try {
      await onConfirm(selected, note);
      setNote('');
      onClose();
    } catch {
      // Parent handles error toast
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (isLoading) return;
    setSelected(currentRegime);
    setNote('');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose}>
      <div className="space-y-5">
        <div>
          <h2 className="text-xl font-display font-medium mb-1">Change Market Regime</h2>
          <p className="text-sm text-paper-100/60">
            Select the new regime. Strategies will adapt their parameters accordingly.
          </p>
        </div>

        {/* Current → New summary */}
        <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
          <span className={cn('px-2.5 py-1 rounded-lg text-xs font-mono font-bold border', currentStyle.bg, currentStyle.color)}>
            {currentStyle.label}
          </span>
          <ArrowRight className="w-4 h-4 text-paper-100/30 flex-shrink-0" />
          {isChanged ? (
            <span className={cn('px-2.5 py-1 rounded-lg text-xs font-mono font-bold border', selectedStyle.bg, selectedStyle.color)}>
              {selectedStyle.label}
            </span>
          ) : (
            <span className="text-xs text-paper-100/30 font-mono">No change</span>
          )}
        </div>

        {/* Regime selector */}
        <div>
          <label className="block text-xs font-mono font-bold uppercase tracking-widest text-paper-100/60 mb-2">
            New Regime
          </label>
          <div className="flex flex-wrap gap-2">
            {REGIME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setSelected(opt.value)}
                disabled={isLoading}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-mono font-bold border transition-all',
                  selected === opt.value
                    ? cn(opt.bg, opt.color, 'ring-2 ring-offset-1 ring-offset-obsidian-400 ring-current')
                    : 'bg-white/5 border-white/10 text-paper-100/50 hover:bg-white/10',
                  'disabled:opacity-50',
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Optional note */}
        <div>
          <label className="block text-xs font-mono font-bold uppercase tracking-widest text-paper-100/60 mb-2">
            Note <span className="opacity-50">(optional)</span>
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Reason for regime change..."
            rows={2}
            disabled={isLoading}
            className={cn(
              'w-full px-3 py-2 rounded-xl text-sm resize-none',
              'bg-white/5 border border-white/10 focus:border-white/30 focus:ring-2 focus:ring-white/10',
              'placeholder:text-paper-100/30 text-paper-100 outline-none transition-colors',
              'disabled:opacity-50',
            )}
          />
        </div>

        <div className="flex gap-3 justify-end pt-1">
          <Button variant="ghost" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            disabled={!isChanged || isLoading}
            isLoading={isLoading}
          >
            Confirm Change
          </Button>
        </div>
      </div>
    </Modal>
  );
};

// Re-export for convenient use in Header
export { REGIME_OPTIONS };
