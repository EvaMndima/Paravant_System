import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertTriangle, Info, Zap, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToastItem } from '@/contexts/ToastContext';

interface ToastProps {
  toast: ToastItem;
  onDismiss: () => void;
}

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
  critical: Zap,
};

const styleMap = {
  success: {
    border: 'border-gain/30',
    icon: 'text-gain',
    bg: 'bg-gain/5',
    extra: '',
  },
  error: {
    border: 'border-loss/30',
    icon: 'text-loss',
    bg: 'bg-loss/5',
    extra: '',
  },
  warning: {
    border: 'border-neutral/30',
    icon: 'text-neutral',
    bg: 'bg-neutral/5',
    extra: '',
  },
  info: {
    border: 'border-deep-teal-500/30',
    icon: 'text-deep-teal-500',
    bg: 'bg-deep-teal-500/5',
    extra: '',
  },
  critical: {
    border: 'border-loss/70 animate-pulse',
    icon: 'text-loss',
    bg: 'bg-loss/10',
    extra: 'ring-1 ring-loss/30',
  },
};

export const Toast: React.FC<ToastProps> = ({ toast, onDismiss }) => {
  const Icon = iconMap[toast.type];
  const styles = styleMap[toast.type];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      className={cn(
        'pointer-events-auto w-80 rounded-xl border backdrop-blur-xl shadow-2xl',
        'bg-paper-100/90 dark:bg-obsidian-300/90',
        styles.border,
        styles.extra,
      )}
    >
      <div className="flex items-start gap-3 p-4">
        <div className={cn('mt-0.5 shrink-0', styles.icon)}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-deep-teal-800 dark:text-paper-100">
            {toast.title}
          </p>
          {toast.message && (
            <p className="mt-1 text-xs text-obsidian-400/70 dark:text-paper-100/60 font-mono">
              {toast.message}
            </p>
          )}
        </div>
        <button
          onClick={onDismiss}
          className="shrink-0 text-obsidian-400/40 dark:text-paper-100/40 hover:text-obsidian-400 dark:hover:text-paper-100 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
};
