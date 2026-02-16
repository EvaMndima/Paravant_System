import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';
import { smoothSpring } from '../../lib/animations';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  containerClassName?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ 
    className, 
    containerClassName, 
    type = "text", 
    label, 
    error, 
    helperText, 
    leftIcon, 
    rightIcon, 
    disabled, 
    ...props 
  }, ref) => {
    const [isFocused, setIsFocused] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    
    const isPassword = type === "password";
    const inputType = isPassword ? (showPassword ? "text" : "password") : type;

    return (
      <div className={cn("space-y-1.5 w-full", containerClassName)}>
        {label && (
          <label className="text-xs font-sans font-medium text-obsidian-400/70 dark:text-paper-100/70 ml-1">
            {label}
          </label>
        )}
        
        <motion.div
          animate={!disabled && isFocused ? { scale: 1.005 } : { scale: 1 }}
          transition={smoothSpring}
          className={cn(
            "relative flex items-center rounded-xl border transition-all duration-300",
            // Base Background & Border
            "bg-paper-50 dark:bg-white/5",
            // Conditional States
            error 
              ? "border-loss ring-1 ring-loss/20 shadow-[0_0_15px_rgba(231,76,60,0.1)]" 
              : isFocused 
                ? "border-turquoise-mist ring-2 ring-turquoise-mist/20 shadow-[0_0_15px_rgba(42,157,143,0.15)]" 
                : "border-deep-teal-800/10 dark:border-white/10 hover:border-deep-teal-800/20 dark:hover:border-white/20",
             disabled && "opacity-50 cursor-not-allowed bg-obsidian-400/5 dark:bg-white/5"
          )}
        >
            {/* Left Icon Slot */}
            {leftIcon && (
                <div className="pl-3 text-obsidian-400/40 dark:text-paper-100/40 select-none">
                    {leftIcon}
                </div>
            )}

            <input
                ref={ref}
                type={inputType}
                disabled={disabled}
                className={cn(
                    "w-full bg-transparent px-3 py-2.5 text-sm font-sans text-obsidian-400 dark:text-paper-100 placeholder:text-obsidian-400/30 dark:placeholder:text-paper-100/30 focus:outline-none disabled:cursor-not-allowed",
                    leftIcon ? "pl-2" : "pl-3",
                    (rightIcon || isPassword) ? "pr-2" : "pr-3",
                    className
                )}
                onFocus={(e) => {
                    setIsFocused(true);
                    props.onFocus?.(e);
                }}
                onBlur={(e) => {
                    setIsFocused(false);
                    props.onBlur?.(e);
                }}
                {...props}
            />

            {/* Right Icon & Password Toggle */}
            {(rightIcon || isPassword) && (
                <div className="pr-3 flex items-center gap-2 text-obsidian-400/40 dark:text-paper-100/40">
                    {rightIcon}
                    {isPassword && (
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="hover:text-deep-teal-800 dark:hover:text-turquoise-mist transition-colors focus:outline-none p-0.5 rounded-md hover:bg-black/5 dark:hover:bg-white/5"
                            tabIndex={-1}
                        >
                            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    )}
                </div>
            )}
        </motion.div>

        {/* Validation / Helper Message */}
        {(error || helperText) && (
            <motion.div 
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-1.5 ml-1 h-4"
            >
                {error && <AlertCircle className="w-3 h-3 text-loss" />}
                <span className={cn(
                    "text-xs font-medium tracking-wide",
                    error ? "text-loss" : "text-obsidian-400/50 dark:text-paper-100/50"
                )}>
                    {error || helperText}
                </span>
            </motion.div>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export { Input };