import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { cn } from '../../lib/utils';
import { smoothSpring } from '../../lib/animations';
import { ToastData, useToast } from '../../contexts/ToastContext';

// --- Toast Item Component ---

interface ToastItemProps {
  toast: ToastData;
  onDismiss: (id: string) => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onDismiss }) => {
  const { id, title, description, type = 'info', duration = 5000, action } = toast;

  // Auto-dismiss logic
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onDismiss(id);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [id, duration, onDismiss]);

  // Visual Configuration based on Type
  const config = {
    success: {
      icon: CheckCircle,
      accent: "bg-gain",
      iconColor: "text-gain",
    },
    error: {
      icon: AlertCircle,
      accent: "bg-loss",
      iconColor: "text-loss",
    },
    warning: {
      icon: AlertTriangle,
      accent: "bg-warning",
      iconColor: "text-warning",
    },
    info: {
      icon: Info,
      accent: "bg-info",
      iconColor: "text-info",
    }
  }[type];

  const Icon = config.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 100, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.95 }}
      transition={{ ...smoothSpring, duration: 0.4 }}
      className={cn(
        "relative w-full min-w-[320px] max-w-[420px] rounded-xl overflow-hidden shadow-xl pointer-events-auto",
        "bg-paper-100/95 dark:bg-obsidian-300/95 backdrop-blur-xl",
        "border border-deep-teal-800/10 dark:border-white/10"
      )}
      role="alert"
    >
      {/* Left Accent Bar */}
      <div className={cn("absolute left-0 top-0 bottom-0 w-[3px]", config.accent)} />

      <div className="p-4 pl-5 flex items-start gap-3">
        {/* Icon */}
        <div className={cn("mt-0.5 flex-shrink-0", config.iconColor)}>
          <Icon className="w-5 h-5" strokeWidth={2} />
        </div>

        {/* Content */}
        <div className="flex-1 space-y-1">
          <h3 className="font-sans font-medium text-sm text-obsidian-400 dark:text-paper-100 leading-tight">
            {title}
          </h3>
          {description && (
            <p className="font-sans text-xs text-obsidian-400/70 dark:text-paper-100/70 leading-relaxed">
              {description}
            </p>
          )}
          
          {/* Optional Action Button */}
          {action && (
            <button 
              onClick={(e) => {
                e.stopPropagation();
                action.onClick();
              }}
              className="mt-2 text-xs font-medium text-deep-teal-800 dark:text-turquoise-mist hover:underline focus:outline-none"
            >
              {action.label}
            </button>
          )}
        </div>

        {/* Close Button */}
        <button
          onClick={() => onDismiss(id)}
          className="flex-shrink-0 -mr-1 -mt-1 p-1.5 rounded-md text-obsidian-400/40 dark:text-paper-100/40 hover:bg-black/5 dark:hover:bg-white/5 hover:text-obsidian-400 dark:hover:text-paper-100 transition-colors focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50"
          aria-label="Close notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Progress Bar */}
      {duration > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-obsidian-400/5 dark:bg-white/5">
          <motion.div
            initial={{ width: "100%" }}
            animate={{ width: "0%" }}
            transition={{ duration: duration / 1000, ease: "linear" }}
            className={cn("h-full", config.accent)}
          />
        </div>
      )}
    </motion.div>
  );
};

// --- Toast Container ---

export const ToastContainer = ({ toasts }: { toasts: ToastData[] }) => {
  const { dismiss } = useToast();

  return (
    <div 
      className="fixed bottom-6 right-6 z-[120] flex flex-col gap-3 pointer-events-none p-4 md:p-0"
      aria-live="polite"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </AnimatePresence>
    </div>
  );
};