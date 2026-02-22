import React, { createContext, useCallback, useContext, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Toast } from '@/components/ui/Toast';

/**
 * Enhanced ToastContext — Session 7C additions:
 * - `critical` type (persistent red, no auto-dismiss)
 * - `duration` parameter (default 5s, 0 = persistent)
 * - Max 3 visible toasts; oldest dismissed when 4th arrives
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'critical';

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  /** Duration in ms. 0 = persistent (user must dismiss). Default: 5000 */
  duration?: number;
}

interface ToastContextType {
  addToast: (type: ToastType, title: string, message?: string, duration?: number) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const MAX_VISIBLE = 3;
const DEFAULT_DURATION = 5000;
/** Critical toasts are persistent by default */
const CRITICAL_DURATION = 0;

// eslint-disable-next-line react-refresh/only-export-components -- context hook must be co-located with provider
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

let toastCounter = 0;

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, title: string, message?: string, duration?: number) => {
      const id = `toast-${++toastCounter}`;

      // Resolve duration: critical defaults to persistent (0), else DEFAULT_DURATION
      const resolvedDuration = duration !== undefined
        ? duration
        : type === 'critical' ? CRITICAL_DURATION : DEFAULT_DURATION;

      setToasts((prev) => {
        const next = [...prev, { id, type, title, message, duration: resolvedDuration }];
        // If more than MAX_VISIBLE exist, remove the oldest non-critical ones
        if (next.length > MAX_VISIBLE) {
          // Find oldest non-critical to remove
          const oldestNonCriticalIdx = next.findIndex((t) => t.type !== 'critical');
          if (oldestNonCriticalIdx !== -1) {
            next.splice(oldestNonCriticalIdx, 1);
          } else {
            // All critical — remove first anyway to prevent unbounded growth
            next.splice(0, 1);
          }
        }
        return next;
      });

      // Auto-dismiss if duration > 0
      if (resolvedDuration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, resolvedDuration);
      }
      // If duration === 0, toast is persistent until manually dismissed
    },
    [removeToast],
  );

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      {/* Toast container - bottom-right, newest on top */}
      <div className="fixed bottom-4 right-4 z-[200] flex flex-col-reverse gap-2 pointer-events-none">
        <AnimatePresence mode="popLayout">
          {toasts.map((toast) => (
            <Toast
              key={toast.id}
              toast={toast}
              onDismiss={() => removeToast(toast.id)}
            />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};
