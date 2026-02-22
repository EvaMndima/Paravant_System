/**
 * KillSwitchModal — Safety-critical modal for activating/deactivating the kill switch.
 *
 * Activation:  Requires a reason (text field) → calls API → logs transaction_id
 * Deactivation: Requires typing "DEACTIVATE" exactly → button only enabled when match
 *
 * Per 7.3.1 acceptance criteria:
 * - Modal doesn't close on API failure (error toast shown instead)
 * - transaction_id from response logged to console for audit trail
 * - Focus trapped within modal (handled by existing Modal component)
 */
import React, { useCallback, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/utils';

export interface KillSwitchModalProps {
  isOpen: boolean;
  /** Whether the kill switch is currently ACTIVE. Determines which modal mode shows. */
  isActive: boolean;
  onConfirm: (reason: string) => Promise<void>;
  onCancel: () => void;
}

const REQUIRED_DEACTIVATION_TEXT = 'DEACTIVATE';

export const KillSwitchModal: React.FC<KillSwitchModalProps> = ({
  isOpen,
  isActive,
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState('');
  const [deactivateConfirm, setDeactivateConfirm] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const resetState = useCallback(() => {
    setReason('');
    setDeactivateConfirm('');
    setIsLoading(false);
  }, []);

  const handleClose = useCallback(() => {
    if (isLoading) return; // Prevent closing while API call is in flight
    resetState();
    onCancel();
  }, [isLoading, resetState, onCancel]);

  const handleActivate = useCallback(async () => {
    if (!reason.trim()) return; // Reason is required
    setIsLoading(true);
    try {
      await onConfirm(reason.trim());
      resetState();
      // Note: parent closes the modal on success
    } catch {
      // Parent handles error toast; modal remains open
    } finally {
      setIsLoading(false);
    }
  }, [reason, onConfirm, resetState]);

  const handleDeactivate = useCallback(async () => {
    if (deactivateConfirm !== REQUIRED_DEACTIVATION_TEXT) return;
    setIsLoading(true);
    try {
      await onConfirm('');
      resetState();
    } catch {
      // Parent handles error toast; modal remains open
    } finally {
      setIsLoading(false);
    }
  }, [deactivateConfirm, onConfirm, resetState]);

  const deactivateTextMatches = deactivateConfirm === REQUIRED_DEACTIVATION_TEXT;
  const hasReason = reason.trim().length > 0;

  return (
    <Modal isOpen={isOpen} onClose={handleClose}>
      {!isActive ? (
        /* ── ACTIVATION MODE ─────────────────────────────────────────── */
        <div className="space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-loss/15 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5 text-loss" />
            </div>
            <div>
              <h2 className="text-xl font-display font-medium">Activate Kill Switch?</h2>
              <p className="text-sm text-paper-100/60 mt-0.5">
                This will halt <strong>ALL trading immediately.</strong> Open positions remain open
                but no new trades can be executed.
              </p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-bold uppercase tracking-widest text-paper-100/60 mb-2">
              Reason <span className="text-loss">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Market flash crash, system error, manual intervention"
              rows={3}
              disabled={isLoading}
              className={cn(
                'w-full px-4 py-3 rounded-xl text-sm font-sans resize-none',
                'bg-white/5 border border-white/10 focus:border-loss/50 focus:ring-2 focus:ring-loss/20',
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
              variant="danger"
              onClick={handleActivate}
              disabled={!hasReason || isLoading}
              isLoading={isLoading}
              className="min-w-[180px]"
            >
              🚨 HALT ALL TRADING
            </Button>
          </div>
        </div>
      ) : (
        /* ── DEACTIVATION MODE ───────────────────────────────────────── */
        <div className="space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-loss/15 flex items-center justify-center flex-shrink-0 animate-pulse">
              <AlertTriangle className="w-5 h-5 text-loss" />
            </div>
            <div>
              <h2 className="text-xl font-display font-medium">Deactivate Kill Switch?</h2>
              <p className="text-sm text-paper-100/60 mt-0.5">
                Trading will resume once deactivated. Type{' '}
                <code className="bg-black/30 px-1.5 py-0.5 rounded text-loss font-mono">
                  {REQUIRED_DEACTIVATION_TEXT}
                </code>{' '}
                to confirm.
              </p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-bold uppercase tracking-widest text-paper-100/60 mb-2">
              Confirmation
            </label>
            <Input
              type="text"
              value={deactivateConfirm}
              onChange={(e) => setDeactivateConfirm(e.target.value)}
              placeholder={`Type ${REQUIRED_DEACTIVATION_TEXT}`}
              disabled={isLoading}
              className={cn(
                'font-mono tracking-widest',
                deactivateConfirm && !deactivateTextMatches && 'ring-2 ring-loss/50',
                deactivateTextMatches && 'ring-2 ring-gain/50',
              )}
            />
            {deactivateConfirm && !deactivateTextMatches && (
              <p className="text-[11px] text-loss/80 font-mono mt-1.5">
                Must match exactly: {REQUIRED_DEACTIVATION_TEXT}
              </p>
            )}
          </div>

          <div className="flex gap-3 justify-end pt-1">
            <Button variant="ghost" onClick={handleClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleDeactivate}
              disabled={!deactivateTextMatches || isLoading}
              isLoading={isLoading}
              className="min-w-[180px]"
            >
              Confirm Deactivation
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
};
