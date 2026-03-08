import React, { useState, useRef, useEffect } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { smoothSpring } from '@/lib/animations';

export type DropdownItemType =
  | {
      label: ReactNode;
      icon?: LucideIcon;
      onClick?: () => void;
      disabled?: boolean;
      danger?: boolean;
      type?: 'item';
    }
  | { type: 'divider' };

export interface DropdownProps {
  trigger: ReactNode;
  items: DropdownItemType[];
  align?: 'start' | 'end';
  side?: 'bottom' | 'top';
  className?: string;
}

const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  align = 'start',
  side = 'bottom',
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [coords, setCoords] = useState<{ top?: number; left?: number; right?: number }>({});
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const triggerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  const updatePosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const scrollY = window.scrollY;
    const gap = 6;
    const newCoords: { top?: number; left?: number; right?: number } = {};

    newCoords.top = side === 'bottom' ? rect.bottom + scrollY + gap : rect.top + scrollY - gap;

    if (align === 'start') {
      newCoords.left = rect.left + window.scrollX;
    } else {
      newCoords.right = document.documentElement.clientWidth - (rect.right + window.scrollX);
    }

    setCoords(newCoords);
  };

  const handleToggle = () => {
    if (!isOpen) {
      updatePosition();
      setIsOpen(true);
      setActiveIndex(-1);
    } else {
      setIsOpen(false);
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node) &&
        menuRef.current &&
        !menuRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      window.addEventListener('mousedown', handleClickOutside);
      window.addEventListener('scroll', updatePosition);
      window.addEventListener('resize', updatePosition);
    }
    return () => {
      window.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', updatePosition);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      const focusableItems = items.filter(
        (i): i is Extract<DropdownItemType, { label: ReactNode }> =>
          i.type !== 'divider' && !i.disabled
      );

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setActiveIndex(prev => (prev + 1) % focusableItems.length);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setActiveIndex(prev => (prev - 1 + focusableItems.length) % focusableItems.length);
          break;
        case 'Enter':
          e.preventDefault();
          if (activeIndex >= 0) {
            const item = focusableItems[activeIndex];
            if (item && item.onClick) {
              item.onClick();
              setIsOpen(false);
            }
          }
          break;
        case 'Escape':
          e.preventDefault();
          setIsOpen(false);
          break;
      }
    };

    if (isOpen) window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, activeIndex, items]);

  return (
    <>
      <div
        ref={triggerRef}
        onClick={handleToggle}
        className={cn("inline-block cursor-pointer", className)}
      >
        {trigger}
      </div>

      {mounted && createPortal(
        <AnimatePresence>
          {isOpen && (
            <motion.div
              ref={menuRef}
              initial={{ opacity: 0, scale: 0.95, y: side === 'bottom' ? -10 : 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={smoothSpring}
              style={{
                position: 'absolute',
                top: coords.top,
                left: coords.left,
                right: coords.right,
                zIndex: 50,
                transformOrigin: align === 'start' ? 'top left' : 'top right',
              }}
              className={cn(
                "min-w-[200px] p-1.5 rounded-xl shadow-xl border border-deep-teal-800/10 dark:border-white/10",
                "bg-paper-100/90 dark:bg-obsidian-300/90 backdrop-blur-xl"
              )}
            >
              {items.map((item, index) => {
                if (item.type === 'divider') {
                  return (
                    <div
                      key={index}
                      className="my-1.5 h-px bg-deep-teal-800/5 dark:bg-white/5 mx-2"
                    />
                  );
                }

                const focusableItems = items.filter(
                  (i): i is Extract<DropdownItemType, { label: ReactNode }> =>
                    i.type !== 'divider' && !i.disabled
                );
                const isFocused = focusableItems[activeIndex] === item;

                return (
                  <button
                    key={index}
                    disabled={item.disabled}
                    onClick={() => {
                      if (item.onClick) {
                        item.onClick();
                        setIsOpen(false);
                      }
                    }}
                    className={cn(
                      "w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-sm font-sans transition-colors text-left",
                      item.disabled
                        ? "opacity-50 cursor-not-allowed"
                        : "hover:bg-deep-teal-800/5 dark:hover:bg-white/5",
                      isFocused && !item.disabled && "bg-deep-teal-800/5 dark:bg-white/5",
                      item.danger
                        ? "text-loss hover:text-loss"
                        : "text-obsidian-400 dark:text-paper-100"
                    )}
                  >
                    {item.icon && (
                      <item.icon
                        className={cn(
                          "w-4 h-4",
                          item.danger ? "text-loss" : "text-obsidian-400/50 dark:text-paper-100/50"
                        )}
                      />
                    )}
                    <span className="flex-1 truncate">{item.label}</span>
                  </button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  );
};

export { Dropdown };
