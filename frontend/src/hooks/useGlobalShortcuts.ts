/**
 * useGlobalShortcuts — per 7.3.6
 *
 * Keyboard shortcuts:
 *  G then D → /              (Cockpit Dashboard)
 *  G then P → /portfolio     (Portfolio)
 *  G then S → /strategies    (Strategies)
 *  G then R → /risk          (Risk)
 *  G then O → /orders        (Orders)
 *  G then A → /alerts        (Alerts)
 *  G then B → /backtest      (Backtest)
 *
 *  Ctrl+K  → toggle kill switch modal
 *  Ctrl+/  → show keyboard help overlay
 *
 * Implementation:
 * - G+letter is a sequential 2-keypress pattern (2000ms window)
 * - Skips shortcuts when focus is inside an input/textarea/select
 * - Triggers kill switch via data-kill-switch-trigger attribute (Sidebar.tsx)
 */
import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const NAV_SHORTCUT_MAP: Record<string, string> = {
  d: '/',
  p: '/portfolio',
  s: '/strategies',
  r: '/risk',
  o: '/orders',
  a: '/alerts',
  b: '/backtest',
};

export interface ShortcutEntry {
  keys: string;
  description: string;
}

export const SHORTCUT_REFERENCE: ShortcutEntry[] = [
  { keys: 'G then D', description: 'Go to Dashboard' },
  { keys: 'G then P', description: 'Go to Portfolio' },
  { keys: 'G then S', description: 'Go to Strategies' },
  { keys: 'G then R', description: 'Go to Risk' },
  { keys: 'G then O', description: 'Go to Orders' },
  { keys: 'G then A', description: 'Go to Alerts' },
  { keys: 'G then B', description: 'Go to Backtest' },
  { keys: 'Ctrl+K', description: 'Toggle Kill Switch' },
  { keys: 'Ctrl+/', description: 'Show Keyboard Shortcuts' },
];

function isInputFocused(): boolean {
  const el = document.activeElement;
  return (
    el instanceof HTMLInputElement ||
    el instanceof HTMLTextAreaElement ||
    el instanceof HTMLSelectElement ||
    (el instanceof HTMLElement && el.isContentEditable)
  );
}

export function useGlobalShortcuts() {
  const navigate = useNavigate();
  const [showHelp, setShowHelp] = useState(false);
  const [gPressed, setGPressed] = useState(false);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Always skip shortcuts when focus is in an input field
      if (isInputFocused()) return;

      // Ctrl+K — trigger kill switch (dispatches click to data-kill-switch-trigger element)
      if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        const btn = document.querySelector<HTMLButtonElement>('[data-kill-switch-trigger]');
        btn?.click();
        return;
      }

      // Ctrl+/ — show help overlay
      if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        setShowHelp((p) => !p);
        return;
      }

      // Escape — close help overlay
      if (e.key === 'Escape' && showHelp) {
        setShowHelp(false);
        return;
      }

      // G — start the G+letter sequence
      if (e.key === 'g' || e.key === 'G') {
        e.preventDefault();
        setGPressed(true);
        // Clear the g-pressed state after 2 seconds
        setTimeout(() => setGPressed(false), 2000);
        return;
      }

      // Second key of G+letter sequence
      if (gPressed) {
        const key = e.key.toLowerCase();
        if (key in NAV_SHORTCUT_MAP) {
          e.preventDefault();
          navigate(NAV_SHORTCUT_MAP[key]);
        }
        setGPressed(false);
        return;
      }
    },
    [gPressed, navigate, showHelp],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return { showHelp, setShowHelp, shortcuts: SHORTCUT_REFERENCE };
}
