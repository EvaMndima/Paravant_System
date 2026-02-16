import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { smoothSpring } from '../../lib/animations';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'full';
  closeOnBackdropClick?: boolean;
}

const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = 'md',
  closeOnBackdropClick = true,
}) => {
  const [mounted, setMounted] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Size mapping
  const sizes = {
    sm: "max-w-sm",
    md: "max-w-lg",
    lg: "max-w-2xl",
    full: "max-w-4xl",
  };

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // Handle body scroll lock and Escape key
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
      };
      
      window.addEventListener('keydown', handleEscape);
      return () => {
        document.body.style.overflow = 'unset';
        window.removeEventListener('keydown', handleEscape);
      };
    } else {
      // Ensure scroll is restored if closed programmatically
      document.body.style.overflow = 'unset';
    }
  }, [isOpen, onClose]);

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => closeOnBackdropClick && onClose()}
            className="absolute inset-0 bg-obsidian-400/60 backdrop-blur-sm transition-all"
            aria-hidden="true"
          />

          {/* Modal Panel */}
          <motion.div
            ref={containerRef}
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={smoothSpring}
            role="dialog"
            aria-modal="true"
            className={cn(
              "relative w-full rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]",
              // Glass styling
              "bg-paper-100 dark:bg-obsidian-300",
              "border border-deep-teal-800/10 dark:border-white/10",
              sizes[size]
            )}
          >
            {/* Header */}
            {(title || description) && (
              <div className="px-6 py-5 border-b border-deep-teal-800/5 dark:border-white/5 flex items-start justify-between bg-white/50 dark:bg-black/20 backdrop-blur-xl">
                <div className="space-y-1 pr-8">
                  {title && (
                    <h2 className="text-xl font-display font-semibold text-deep-teal-800 dark:text-paper-100">
                      {title}
                    </h2>
                  )}
                  {description && (
                    <p className="text-sm font-sans text-obsidian-400/60 dark:text-paper-100/60">
                      {description}
                    </p>
                  )}
                </div>
                {/* Close Button Mobile/Desktop */}
                <button
                  onClick={onClose}
                  className="rounded-full p-2 text-obsidian-400/50 hover:bg-deep-teal-800/5 hover:text-deep-teal-800 dark:text-paper-100/50 dark:hover:bg-white/10 dark:hover:text-paper-100 transition-colors focus:outline-none focus:ring-2 focus:ring-turquoise-mist"
                  aria-label="Close modal"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}

            {/* Close Button if no header */}
            {(!title && !description) && (
               <button
                  onClick={onClose}
                  className="absolute top-4 right-4 z-10 rounded-full p-2 text-obsidian-400/50 hover:bg-deep-teal-800/5 hover:text-deep-teal-800 dark:text-paper-100/50 dark:hover:bg-white/10 dark:hover:text-paper-100 transition-colors focus:outline-none focus:ring-2 focus:ring-turquoise-mist"
                  aria-label="Close modal"
                >
                  <X className="w-5 h-5" />
                </button>
            )}

            {/* Scrollable Content */}
            <div className="p-6 overflow-y-auto custom-scrollbar relative bg-paper-100/50 dark:bg-obsidian-300/50 backdrop-blur-xl">
              {children}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
};

export { Modal };