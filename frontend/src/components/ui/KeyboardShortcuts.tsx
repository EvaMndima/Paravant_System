import React from 'react';
import {
  Command, Search, Shield,
  LayoutDashboard, Bot, Wallet, History,
  X
} from 'lucide-react';
import { Modal } from './Modal';

interface KeyboardShortcutsProps {
  isOpen: boolean;
  onClose: () => void;
}

const ShortcutKey: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <kbd className="hidden sm:inline-flex items-center justify-center min-w-[24px] h-6 px-1.5 text-[10px] font-mono font-bold text-obsidian-400 dark:text-paper-100 bg-paper-100 dark:bg-white/10 border border-deep-teal-800/20 dark:border-white/20 rounded shadow-sm">
    {children}
  </kbd>
);

const ShortcutRow = ({ label, keys, icon: Icon }: { label: string, keys: React.ReactNode[], icon?: React.ElementType }) => (
  <div className="flex items-center justify-between py-2 border-b border-deep-teal-800/5 dark:border-white/5 last:border-0">
    <div className="flex items-center gap-3">
      {Icon && <Icon className="w-4 h-4 text-obsidian-400/50 dark:text-paper-100/50" />}
      <span className="text-sm text-obsidian-400 dark:text-paper-100">{label}</span>
    </div>
    <div className="flex items-center gap-1">
      {keys.map((k, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span className="text-xs text-obsidian-400/30 dark:text-paper-100/30 mx-0.5">+</span>}
          <ShortcutKey>{k}</ShortcutKey>
        </React.Fragment>
      ))}
    </div>
  </div>
);

export const KeyboardShortcuts: React.FC<KeyboardShortcutsProps> = ({ isOpen, onClose }) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Keyboard Shortcuts"
      description="Quick navigation and power user controls."
      size="md"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

        {/* Navigation Group */}
        <div className="space-y-4">
          <h4 className="text-xs font-mono uppercase tracking-widest text-turquoise-mist opacity-80 mb-2">Navigation</h4>
          <div className="bg-deep-teal-800/5 dark:bg-white/5 rounded-xl border border-deep-teal-800/10 dark:border-white/10 px-4 py-1">
            <ShortcutRow
              label="Go to Cockpit"
              keys={['G', 'C']}
              icon={LayoutDashboard}
            />
            <ShortcutRow
              label="Go to Agents"
              keys={['G', 'A']}
              icon={Bot}
            />
            <ShortcutRow
              label="Go to Portfolio"
              keys={['G', 'P']}
              icon={Wallet}
            />
            <ShortcutRow
              label="Go to History"
              keys={['G', 'T']}
              icon={History}
            />
          </div>
        </div>

        {/* System & Global */}
        <div className="space-y-4">
          <h4 className="text-xs font-mono uppercase tracking-widest text-warning opacity-80 mb-2">System</h4>
          <div className="bg-deep-teal-800/5 dark:bg-white/5 rounded-xl border border-deep-teal-800/10 dark:border-white/10 px-4 py-1">
            <ShortcutRow
              label="Global Search"
              keys={['Ctrl', 'K']}
              icon={Search}
            />
            <ShortcutRow
              label="Emergency Panel"
              keys={['Ctrl', 'Shift', 'K']}
              icon={Shield}
            />
            <ShortcutRow
              label="Show Shortcuts"
              keys={['?']}
              icon={Command}
            />
            <ShortcutRow
              label="Close Modal"
              keys={['Esc']}
              icon={X}
            />
          </div>
        </div>

      </div>

      <div className="mt-6 pt-4 border-t border-deep-teal-800/5 dark:border-white/5 text-center">
        <p className="text-xs text-obsidian-400/40 dark:text-paper-100/40 font-mono">
          Press keys in sequence for 'G' commands.
        </p>
      </div>
    </Modal>
  );
};
