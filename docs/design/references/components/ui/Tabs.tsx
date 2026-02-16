import React, { createContext, useContext, useState, useRef, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../lib/utils';
import { smoothSpring } from '../../lib/animations';

// --- Context ---

type TabsContextValue = {
  value: string;
  onValueChange: (value: string) => void;
  variant: 'underline' | 'pill';
};

const TabsContext = createContext<TabsContextValue | undefined>(undefined);

const useTabs = () => {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('Tabs compound components must be used within a Tabs provider');
  }
  return context;
};

// --- Components ---

export interface TabsProps {
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: ReactNode;
  className?: string;
}

const Tabs: React.FC<TabsProps> = ({
  defaultValue,
  value: controlledValue,
  onValueChange,
  children,
  className,
}) => {
  const [localValue, setLocalValue] = useState(defaultValue || '');
  
  const isControlled = controlledValue !== undefined;
  const currentValue = isControlled ? controlledValue : localValue;

  const handleValueChange = (newValue: string) => {
    if (!isControlled) {
      setLocalValue(newValue);
    }
    onValueChange?.(newValue);
  };

  // We default variant to 'underline' here, but it's overridden by TabsList prop usually.
  // However, since TabsList is a child, we can't easily lift that prop up to Context here 
  // without two-pass rendering or state.
  // Pattern adjustment: We will accept variant on TabsList and pass it down via a secondary context 
  // or simply allow TabsList to style itself and Triggers to read from a specific prop?
  // Better approach for cleaner API: Let TabsList manage the visual style context or props.
  // Actually, to keep it clean, let's put styling logic in the Context provided by Tabs? 
  // No, the requirement says "Variants (optional prop on TabsList)". 
  // So TabsList will wrap its children in a context provider overriding the variant or passing it.

  return (
    <TabsContext.Provider value={{ value: currentValue, onValueChange: handleValueChange, variant: 'underline' }}>
      <div className={cn("w-full", className)}>
        {children}
      </div>
    </TabsContext.Provider>
  );
};

// --- Tabs List ---

export interface TabsListProps {
  children: ReactNode;
  className?: string;
  variant?: 'underline' | 'pill';
}

// Internal context to pass variant from List to Triggers
const TabsListContext = createContext<{ variant: 'underline' | 'pill' }>({ variant: 'underline' });

const TabsList: React.FC<TabsListProps> = ({ 
  children, 
  className, 
  variant = 'underline' 
}) => {
  const listRef = useRef<HTMLDivElement>(null);

  // Keyboard Navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!listRef.current) return;
    
    const tabs = Array.from(listRef.current.querySelectorAll('[role="tab"]')) as HTMLElement[];
    const index = tabs.indexOf(document.activeElement as HTMLElement);
    
    if (index === -1) return;

    let nextIndex = index;
    if (e.key === 'ArrowRight') {
      nextIndex = (index + 1) % tabs.length;
    } else if (e.key === 'ArrowLeft') {
      nextIndex = (index - 1 + tabs.length) % tabs.length;
    } else {
      return;
    }

    e.preventDefault();
    const nextTab = tabs[nextIndex];
    nextTab.focus();
    nextTab.click(); // Auto-activate on focus for typical "Tabs" feel, or remove to require Enter
  };

  return (
    <TabsListContext.Provider value={{ variant }}>
      <div
        ref={listRef}
        role="tablist"
        onKeyDown={handleKeyDown}
        className={cn(
          "flex items-center",
          variant === 'underline' && "border-b border-deep-teal-800/10 dark:border-white/10 gap-6",
          variant === 'pill' && "gap-2 p-1 bg-deep-teal-800/5 dark:bg-white/5 rounded-xl border border-deep-teal-800/5 dark:border-white/5 inline-flex",
          className
        )}
      >
        {children}
      </div>
    </TabsListContext.Provider>
  );
};

// --- Tabs Trigger ---

export interface TabsTriggerProps {
  value: string;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
}

const TabsTrigger: React.FC<TabsTriggerProps> = ({ 
  value, 
  children, 
  className, 
  disabled 
}) => {
  const { value: selectedValue, onValueChange } = useTabs();
  const { variant } = useContext(TabsListContext);
  
  const isActive = selectedValue === value;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      disabled={disabled}
      onClick={() => onValueChange(value)}
      className={cn(
        "relative flex items-center justify-center font-sans font-medium text-sm transition-colors duration-200 outline-none focus-visible:ring-2 focus-visible:ring-turquoise-mist/50",
        disabled && "opacity-50 cursor-not-allowed",
        // Variant Styles
        variant === 'underline' 
          ? cn(
              "py-3 px-1",
              isActive 
                ? "text-deep-teal-800 dark:text-turquoise-mist" 
                : "text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-paper-100"
            )
          : cn(
              "py-2 px-4 rounded-lg z-10",
              isActive 
                ? "text-deep-teal-800 dark:text-paper-100" 
                : "text-obsidian-400/60 dark:text-paper-100/60 hover:text-deep-teal-800 dark:hover:text-paper-100"
            ),
        className
      )}
    >
      {/* Active Indicators */}
      {isActive && variant === 'underline' && (
        <motion.div
          layoutId="activeTabUnderline"
          className="absolute bottom-0 left-0 right-0 h-0.5 bg-turquoise-mist"
          transition={smoothSpring}
        />
      )}
      
      {isActive && variant === 'pill' && (
        <motion.div
          layoutId="activeTabPill"
          className="absolute inset-0 bg-white dark:bg-white/10 shadow-sm rounded-lg -z-10"
          transition={smoothSpring}
        />
      )}
      
      {children}
    </button>
  );
};

// --- Tabs Content ---

export interface TabsContentProps {
  value: string;
  children: ReactNode;
  className?: string;
}

const TabsContent: React.FC<TabsContentProps> = ({ 
  value, 
  children, 
  className 
}) => {
  const { value: selectedValue } = useTabs();
  const isSelected = selectedValue === value;

  if (!isSelected) return null;

  return (
    <motion.div
      role="tabpanel"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn(
        "mt-6 outline-none focus-visible:ring-2 focus-visible:ring-turquoise-mist/50 rounded-lg",
        className
      )}
      tabIndex={0}
    >
      {children}
    </motion.div>
  );
};

export { Tabs, TabsList, TabsTrigger, TabsContent };
