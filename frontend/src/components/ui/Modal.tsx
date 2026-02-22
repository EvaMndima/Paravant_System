import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { modalBackdropVariants, modalPanelVariants } from '@/lib/animations';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const Modal = React.forwardRef<HTMLDivElement, ModalProps>(
  ({ isOpen, onClose, title, children, className, size = 'md' }, ref) => {

    // ESC key handler
    useEffect(() => {
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape' && isOpen) {
          onClose();
        }
      };

      if (isOpen) {
        document.addEventListener('keydown', handleEscape);
        // Lock body scroll
        document.body.style.overflow = 'hidden';
      }

      return () => {
        document.removeEventListener('keydown', handleEscape);
        document.body.style.overflow = 'unset';
      };
    }, [isOpen, onClose]);

    const sizes = {
      sm: 'max-w-sm',
      md: 'max-w-lg',
      lg: 'max-w-2xl',
      xl: 'max-w-4xl',
    };

    return (
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
              variants={modalBackdropVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
              onClick={onClose}
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            />

            {/* Panel */}
            <motion.div
              ref={ref}
              variants={modalPanelVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
              onClick={(e) => e.stopPropagation()}
              className={cn(
                "relative w-full rounded-2xl",
                "bg-paper-100/90 dark:bg-obsidian-300/90 backdrop-blur-2xl",
                "border border-deep-teal-800/10 dark:border-white/10",
                "shadow-2xl",
                "p-8",
                sizes[size],
                className
              )}
            >
              {/* Header */}
              {title && (
                <div className="flex items-start justify-between mb-6">
                  <h2 className="text-xl font-serif font-semibold text-deep-teal-800 dark:text-paper-100">
                    {title}
                  </h2>
                  <button
                    onClick={onClose}
                    className={cn(
                      "rounded-lg p-1 transition-colors",
                      "text-obsidian-400/50 dark:text-paper-100/50",
                      "hover:text-obsidian-400 dark:hover:text-paper-100",
                      "hover:bg-deep-teal-800/5 dark:hover:bg-white/5"
                    )}
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              )}

              {/* Close button (if no title) */}
              {!title && (
                <button
                  onClick={onClose}
                  className={cn(
                    "absolute top-4 right-4 rounded-lg p-1 transition-colors",
                    "text-obsidian-400/50 dark:text-paper-100/50",
                    "hover:text-obsidian-400 dark:hover:text-paper-100",
                    "hover:bg-deep-teal-800/5 dark:hover:bg-white/5"
                  )}
                >
                  <X className="w-5 h-5" />
                </button>
              )}

              {/* Content */}
              <div className="text-obsidian-400 dark:text-paper-100">
                {children}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    );
  }
);

Modal.displayName = "Modal";

export { Modal };
