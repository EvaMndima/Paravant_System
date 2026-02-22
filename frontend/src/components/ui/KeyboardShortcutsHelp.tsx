/**
 * KeyboardShortcutsHelp — Modal overlay showing all keyboard shortcuts.
 * Triggered by Ctrl+/ or the shortcut reference button in the UI.
 */
import React from 'react';
import { X, Keyboard } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ShortcutEntry } from '@/hooks/useGlobalShortcuts';
import { cn } from '@/lib/utils';

interface KeyboardShortcutsHelpProps {
  isOpen: boolean;
  shortcuts: ShortcutEntry[];
  onClose: () => void;
}

export const KeyboardShortcutsHelp: React.FC<KeyboardShortcutsHelpProps> = ({
  isOpen,
  shortcuts,
  onClose,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[150] bg-obsidian-400/70 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <div className="fixed inset-0 z-[160] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 12 }}
              transition={{ type: 'spring', stiffness: 400, damping: 35 }}
              className={cn(
                'w-full max-w-sm rounded-2xl overflow-hidden',
                'bg-obsidian-300 border border-white/10 shadow-2xl',
              )}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-deep-teal-800/20 rounded-lg">
                    <Keyboard className="w-4 h-4 text-deep-teal-500" />
                  </div>
                  <h2 className="font-serif font-bold">Keyboard Shortcuts</h2>
                </div>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                  aria-label="Close shortcuts"
                >
                  <X className="w-4 h-4 text-paper-100/50" />
                </button>
              </div>

              {/* Shortcut list */}
              <div className="px-6 py-4 space-y-2">
                {shortcuts.map((s) => (
                  <div
                    key={s.keys}
                    className="flex items-center justify-between py-1.5"
                  >
                    <span className="text-sm text-paper-100/60">{s.description}</span>
                    <kbd className="font-mono text-[11px] bg-obsidian-400/80 border border-white/10 rounded-md px-2 py-0.5 text-paper-100/80 whitespace-nowrap">
                      {s.keys}
                    </kbd>
                  </div>
                ))}
              </div>

              {/* Footer */}
              <div className="px-6 py-3 border-t border-white/10 text-center">
                <p className="text-xs text-paper-100/30 font-mono">Press Esc or Ctrl+/ to close</p>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};
