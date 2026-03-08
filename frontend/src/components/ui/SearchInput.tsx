import React from 'react';
import { Search, X } from 'lucide-react';
import { Input } from './Input';
import type { InputProps } from './Input';
import { cn } from '@/lib/utils';

export interface SearchInputProps extends Omit<InputProps, 'leftIcon' | 'rightIcon'> {
  onClear?: () => void;
  shortcut?: string;
}

const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, value, onClear, shortcut = "⌘K", ...props }, ref) => {
    const hasValue = value && String(value).length > 0;

    return (
      <Input
        ref={ref}
        value={value}
        className={cn("font-sans", className)}
        leftIcon={<Search className="w-4 h-4" />}
        rightIcon={
          <div className="flex items-center gap-2">
            {hasValue && onClear && (
              <button
                type="button"
                onClick={onClear}
                className="p-1 rounded-full hover:bg-obsidian-400/10 dark:hover:bg-white/10 text-obsidian-400/40 dark:text-paper-100/40 hover:text-deep-teal-800 dark:hover:text-paper-100 transition-colors focus:outline-none focus:ring-1 focus:ring-turquoise-mist"
                aria-label="Clear search"
              >
                <X className="w-3 h-3" />
              </button>
            )}
            {shortcut && !hasValue && (
              <kbd className="hidden md:inline-flex items-center gap-0.5 rounded border border-obsidian-400/10 dark:border-white/10 bg-obsidian-400/5 dark:bg-white/5 px-1.5 py-0.5 text-[10px] font-mono font-medium text-obsidian-400/40 dark:text-paper-100/40 select-none">
                {shortcut}
              </kbd>
            )}
          </div>
        }
        {...props}
      />
    );
  }
);

SearchInput.displayName = "SearchInput";

export { SearchInput };
