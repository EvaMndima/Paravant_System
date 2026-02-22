import React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, leftIcon, rightIcon, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-xs font-mono font-medium uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-obsidian-400/40 dark:text-paper-100/40">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            className={cn(
              "w-full rounded-xl border border-deep-teal-800/10 dark:border-white/10",
              "bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-md",
              "px-4 py-2.5 font-sans text-sm",
              "text-obsidian-400 dark:text-paper-100",
              "placeholder:text-obsidian-400/40 dark:placeholder:text-paper-100/40",
              "focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50 focus:border-turquoise-mist",
              "transition-colors duration-200",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              error && "border-loss focus:ring-loss/50 focus:border-loss",
              leftIcon && "pl-10",
              rightIcon && "pr-10",
              className
            )}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-obsidian-400/40 dark:text-paper-100/40">
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-1.5 text-xs font-sans text-loss">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export { Input };
