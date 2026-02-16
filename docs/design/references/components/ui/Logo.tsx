
import React from 'react';
import { cn } from '../../lib/utils';

interface LogoProps {
  className?: string;
  showText?: boolean;
  iconClassName?: string;
  textClassName?: string;
}

export const Logo: React.FC<LogoProps> = ({ 
  className, 
  showText = true,
  iconClassName,
  textClassName
}) => {
  return (
    <div className={cn("flex items-center gap-3 select-none", className)}>
      {/* Icon: The Wing Symbol */}
      <svg 
        viewBox="0 0 100 100" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
        className={cn("w-8 h-8 text-turquoise-bright", iconClassName)}
      >
        <path 
          d="M20 85C20 85 35 80 45 65C55 50 85 20 85 20C85 20 60 35 45 55C30 75 20 85 20 85Z" 
          fill="currentColor" 
          className="opacity-90"
        />
        <path 
          d="M15 70C15 70 30 65 40 50C50 35 75 10 75 10C75 10 55 25 40 40C25 55 15 70 15 70Z" 
          fill="currentColor" 
          className="opacity-75"
        />
        <path 
          d="M10 55C10 55 25 50 35 35C45 20 65 0 65 0C65 0 45 15 30 30C15 45 10 55 10 55Z" 
          fill="currentColor" 
          className="opacity-60"
        />
      </svg>

      {/* Wordmark: PARAVANT */}
      {showText && (
        <span 
          className={cn(
            "font-sans font-bold text-xl tracking-[0.15em] text-obsidian-400 dark:text-paper-100", 
            textClassName
          )}
        >
          PARAVANT
        </span>
      )}
    </div>
  );
};
