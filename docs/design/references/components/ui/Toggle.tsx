import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { cn } from '../../lib/utils';
import { smoothSpring } from '../../lib/animations';

interface ToggleProps extends Omit<HTMLMotionProps<"button">, "children"> {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  size?: 'sm' | 'md';
  disabled?: boolean;
}

const Toggle = React.forwardRef<HTMLButtonElement, ToggleProps>(
  ({ checked, onCheckedChange, size = 'md', disabled = false, className, style, ...props }, ref) => {
    
    const dimensions = {
      sm: { w: 36, h: 20, p: 2 },
      md: { w: 44, h: 24, p: 2 }
    };

    const currentDim = dimensions[size];
    const thumbSize = currentDim.h - (currentDim.p * 2);

    return (
      <motion.button
        ref={ref}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onCheckedChange(!checked)}
        className={cn(
          "relative rounded-full transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50 focus:ring-offset-2 dark:focus:ring-offset-obsidian-400",
          checked ? "bg-turquoise-mist" : "bg-obsidian-400/10 dark:bg-white/10",
          disabled && "opacity-50 cursor-not-allowed",
          className
        )}
        style={{ width: currentDim.w, height: currentDim.h, ...style }}
        {...props}
      >
        <motion.div
          className="bg-white rounded-full shadow-sm"
          layout
          transition={smoothSpring}
          animate={{
            x: checked ? currentDim.w - currentDim.h : 0
          }}
          style={{
            width: thumbSize,
            height: thumbSize,
            margin: currentDim.p
          }}
        />
      </motion.button>
    );
  }
);

Toggle.displayName = "Toggle";

export { Toggle };