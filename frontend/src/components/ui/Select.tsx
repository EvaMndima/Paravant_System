import React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: Array<{ value: string; label: string }>;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-xs font-mono font-medium uppercase tracking-widest text-obsidian-400/50 dark:text-paper-100/50 mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            className={cn(
              "w-full rounded-xl border border-deep-teal-800/10 dark:border-white/10",
              "bg-paper-100/50 dark:bg-obsidian-400/50 backdrop-blur-md",
              "px-4 py-2.5 pr-10 font-sans text-sm",
              "text-obsidian-400 dark:text-paper-100",
              "focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50 focus:border-turquoise-mist",
              "transition-colors duration-200",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "appearance-none cursor-pointer",
              error && "border-loss focus:ring-loss/50 focus:border-loss",
              className
            )}
            {...props}
          >
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-obsidian-400/40 dark:text-paper-100/40 pointer-events-none">
            <ChevronDown className="w-4 h-4" />
          </div>
        </div>
        {error && (
          <p className="mt-1.5 text-xs font-sans text-loss">{error}</p>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";

export { Select };
