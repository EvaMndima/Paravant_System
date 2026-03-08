import React, { useState, useRef, useEffect } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { cn } from '@/lib/utils';
import { smoothSpring } from '@/lib/animations';

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
  disabled?: boolean;
  className?: string;
  triggerClassName?: string;
}

const Tooltip: React.FC<TooltipProps> = ({ content, children, side = 'top', delay = 200, disabled = false, className, triggerClassName }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); return () => setMounted(false); }, []);

  const updatePosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const gap = 8;
    let top = 0; let left = 0;
    switch (side) {
      case 'top':    top = rect.top + scrollY - gap;              left = rect.left + scrollX + rect.width / 2; break;
      case 'bottom': top = rect.bottom + scrollY + gap;           left = rect.left + scrollX + rect.width / 2; break;
      case 'left':   top = rect.top + scrollY + rect.height / 2;  left = rect.left + scrollX - gap; break;
      case 'right':  top = rect.top + scrollY + rect.height / 2;  left = rect.right + scrollX + gap; break;
    }
    setCoords({ top, left });
  };

  const handleMouseEnter = () => {
    if (disabled) return;
    updatePosition();
    timeoutRef.current = setTimeout(() => setIsVisible(true), delay);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  useEffect(() => {
    if (isVisible) {
      window.addEventListener('scroll', updatePosition);
      window.addEventListener('resize', updatePosition);
    }
    return () => {
      window.removeEventListener('scroll', updatePosition);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isVisible]);

  const variants: Variants = {
    initial: { opacity: 0, scale: 0.95, y: side === 'top' ? 4 : side === 'bottom' ? -4 : 0, x: side === 'left' ? 4 : side === 'right' ? -4 : 0 },
    animate: { opacity: 1, scale: 1, y: 0, x: 0, transition: smoothSpring },
    exit: { opacity: 0, scale: 0.95, transition: { duration: 0.15, ease: 'easeOut' } },
  };

  const transformStyles: React.CSSProperties = {
    top: coords.top,
    left: coords.left,
    transform: side === 'top' ? 'translate(-50%, -100%)' : side === 'bottom' ? 'translate(-50%, 0)' : side === 'left' ? 'translate(-100%, -50%)' : 'translate(0, -50%)',
  };

  const arrowClasses = cn(
    "absolute w-2.5 h-2.5 rotate-45 border-white/10 bg-obsidian-400 dark:bg-obsidian-300 backdrop-blur-md z-[-1]",
    side === 'top'    && "bottom-[-5px] left-1/2 -translate-x-1/2 border-b border-r",
    side === 'bottom' && "top-[-5px] left-1/2 -translate-x-1/2 border-t border-l",
    side === 'left'   && "right-[-5px] top-1/2 -translate-y-1/2 border-t border-r",
    side === 'right'  && "left-[-5px] top-1/2 -translate-y-1/2 border-b border-l"
  );

  return (
    <>
      <div ref={triggerRef} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave} className={cn("inline-block", triggerClassName)}>
        {children}
      </div>
      {mounted && createPortal(
        <AnimatePresence>
          {isVisible && (
            <motion.div
              initial="initial" animate="animate" exit="exit" variants={variants}
              style={{ ...transformStyles, position: 'absolute', zIndex: 50 }}
              className="pointer-events-none fixed"
            >
              <div className={cn(
                "relative px-3 py-1.5 rounded-lg border border-white/10 shadow-xl shadow-black/20",
                "bg-obsidian-400/90 dark:bg-obsidian-300/95 backdrop-blur-md",
                "text-paper-100 text-xs font-sans tracking-wide whitespace-nowrap",
                className
              )}>
                {content}
                <div className={arrowClasses} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  );
};

export { Tooltip };
