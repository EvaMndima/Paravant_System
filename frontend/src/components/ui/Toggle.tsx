import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { smoothSpring } from '@/lib/animations';

export interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

const Toggle = React.forwardRef<HTMLButtonElement, ToggleProps>(
  ({ checked, onChange, label, description, disabled, className }, ref) => {
    return (
      <div className={cn("flex items-start gap-3", className)}>
        <button
          ref={ref}
          type="button"
          role="switch"
          aria-checked={checked}
          disabled={disabled}
          onClick={() => !disabled && onChange(!checked)}
          className={cn(
            "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out",
            "focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50 focus:ring-offset-2 dark:focus:ring-offset-obsidian-400",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            checked
              ? "bg-turquoise-mist"
              : "bg-obsidian-400/20 dark:bg-white/10"
          )}
        >
          <motion.span
            layout
            transition={smoothSpring}
            className={cn(
              "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-paper-100 shadow-lg ring-0",
              checked ? "translate-x-5" : "translate-x-0"
            )}
          />
        </button>
        {(label || description) && (
          <div className="flex flex-col">
            {label && (
              <span className="text-sm font-medium text-obsidian-400 dark:text-paper-100">
                {label}
              </span>
            )}
            {description && (
              <span className="text-xs text-obsidian-400/50 dark:text-paper-100/50">
                {description}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }
);

Toggle.displayName = "Toggle";

export { Toggle };
