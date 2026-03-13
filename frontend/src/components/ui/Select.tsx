import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps {
  options: SelectOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  id?: string;
}

const sizeStyles = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-4 text-base',
};

export const Select: React.FC<SelectProps> = ({
  options,
  value,
  onChange,
  placeholder = 'Select...',
  label,
  error,
  disabled = false,
  size = 'md',
  className,
  id,
}) => {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = options.find(o => o.value === value);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelect = (option: SelectOption) => {
    if (option.disabled) return;
    onChange?.(option.value);
    setOpen(false);
  };

  return (
    <div className={cn('flex flex-col gap-1.5', className)} ref={containerRef}>
      {label && (
        <label
          htmlFor={id}
          className="text-xs font-mono font-medium text-obsidian-400/70 dark:text-paper-100/70 uppercase tracking-widest"
        >
          {label}
        </label>
      )}

      <div className="relative">
        <button
          id={id}
          type="button"
          onClick={() => !disabled && setOpen(v => !v)}
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={open}
          className={cn(
            'w-full flex items-center justify-between rounded-xl border transition-all duration-150 font-sans',
            'bg-deep-teal-800/5 dark:bg-white/5',
            'focus:outline-none focus:ring-2 focus:ring-turquoise-mist/40',
            sizeStyles[size],
            error
              ? 'border-loss/50 text-loss'
              : open
              ? 'border-turquoise-mist/50 text-obsidian-400 dark:text-paper-100'
              : 'border-deep-teal-800/15 dark:border-white/10 text-obsidian-400 dark:text-paper-100 hover:border-deep-teal-800/30 dark:hover:border-white/20',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <span className={cn(!selected && 'text-obsidian-400/40 dark:text-paper-100/40')}>
            {selected ? selected.label : placeholder}
          </span>
          <ChevronDown
            className={cn(
              'w-4 h-4 shrink-0 text-obsidian-400/40 dark:text-paper-100/40 transition-transform duration-200',
              open && 'rotate-180'
            )}
          />
        </button>

        {/* Dropdown list */}
        {open && (
          <div
            role="listbox"
            className={cn(
              'absolute z-50 w-full mt-1.5 rounded-xl border border-deep-teal-800/10 dark:border-white/10',
              'bg-paper-100 dark:bg-obsidian-300 shadow-xl backdrop-blur-md',
              'overflow-hidden'
            )}
          >
            <ul className="py-1 max-h-56 overflow-y-auto">
              {options.map(option => (
                <li
                  key={option.value}
                  role="option"
                  aria-selected={option.value === value}
                  onClick={() => handleSelect(option)}
                  className={cn(
                    'flex items-center justify-between px-4 py-2.5 text-sm font-sans cursor-pointer transition-colors duration-100',
                    option.value === value
                      ? 'bg-turquoise-mist/10 text-deep-teal-800 dark:text-turquoise-mist font-medium'
                      : 'text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5',
                    option.disabled && 'opacity-40 cursor-not-allowed pointer-events-none'
                  )}
                >
                  <span>{option.label}</span>
                  {option.value === value && <Check className="w-3.5 h-3.5 shrink-0" />}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {error && (
        <p className="text-[11px] font-sans text-loss">{error}</p>
      )}
    </div>
  );
};
