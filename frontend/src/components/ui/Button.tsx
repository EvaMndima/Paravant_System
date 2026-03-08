import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { smoothSpring } from '@/lib/animations';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  children: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading = false, leftIcon, rightIcon, children, disabled, ...props }, ref) => {

    const baseStyles = "relative inline-flex items-center justify-center rounded-xl font-sans font-medium tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-turquoise-mist/50 focus:ring-offset-2 dark:focus:ring-offset-obsidian-400 disabled:opacity-50 disabled:pointer-events-none select-none";

    const variants = {
      primary: "bg-turquoise-mist text-white hover:shadow-[0_0_20px_rgba(42,157,143,0.4)] border border-transparent shadow-md shadow-turquoise-mist/20",
      secondary: "bg-transparent border border-turquoise-mist/50 text-deep-teal-800 dark:text-turquoise-mist hover:bg-turquoise-mist/10 hover:border-turquoise-mist",
      ghost: "bg-transparent border border-transparent text-obsidian-400 dark:text-paper-100 hover:bg-deep-teal-800/5 dark:hover:bg-white/5",
      danger: "bg-loss text-white border border-transparent hover:shadow-[0_0_20px_rgba(231,76,60,0.4)]"
    };

    const sizes = {
      sm: "h-8 px-3 text-xs gap-1.5",
      md: "h-10 px-5 text-sm gap-2",
      lg: "h-12 px-8 text-base gap-2.5"
    };

    return (
      <motion.button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        whileHover={!disabled && !isLoading ? { scale: 1.02, y: -1, transition: smoothSpring } : undefined}
        whileTap={!disabled && !isLoading ? { scale: 0.98 } : undefined}
        transition={smoothSpring}
        {...(props as any)}
      >
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
              <Loader2 className={cn("animate-spin", size === 'sm' ? 'h-3 w-3' : 'h-4 w-4')} />
            </motion.div>
          </div>
        )}
        <span className={cn(
          "flex items-center inherit-color",
          isLoading ? "invisible opacity-0" : "visible opacity-100",
          size === 'sm' ? 'gap-1.5' : size === 'lg' ? 'gap-2.5' : 'gap-2'
        )}>
          {leftIcon && <span className="flex-shrink-0 flex items-center">{leftIcon}</span>}
          <span>{children}</span>
          {rightIcon && <span className="flex-shrink-0 flex items-center">{rightIcon}</span>}
        </span>
      </motion.button>
    );
  }
);

Button.displayName = "Button";

export { Button };
