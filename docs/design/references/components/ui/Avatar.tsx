import React, { useState } from 'react';
import { cn } from '../../lib/utils';

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  name?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  status?: 'online' | 'offline';
}

const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({ 
    src, 
    alt, 
    name, 
    size = 'md', 
    status, 
    className, 
    ...props 
  }, ref) => {
    const [imageError, setImageError] = useState(false);

    // Dimensions & Text Sizes
    const sizeStyles = {
      sm: "h-8 w-8 text-[10px]",
      md: "h-10 w-10 text-xs",
      lg: "h-12 w-12 text-sm",
      xl: "h-16 w-16 text-base"
    };

    // Status Indicator Sizes & Positions
    const statusStyles = {
      sm: "h-2 w-2 border-[1.5px] -bottom-0.5 -right-0.5",
      md: "h-2.5 w-2.5 border-2 -bottom-0.5 -right-0.5",
      lg: "h-3 w-3 border-2 bottom-0 right-0",
      xl: "h-4 w-4 border-[3px] bottom-0.5 right-0.5"
    };

    // Extract initials: "John Doe" -> "JD", "Paravant" -> "PA"
    const initials = name
      ? name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase()
      : '??';

    return (
      <div 
        ref={ref}
        className={cn("relative inline-block", className)} 
        {...props}
      >
        <div className={cn(
          "relative flex items-center justify-center rounded-full overflow-hidden transition-all duration-300 group select-none",
          // Hover ring effect
          "ring-2 ring-transparent hover:ring-turquoise-mist/30",
          // Fallback background
          "bg-deep-teal-800/10 dark:bg-turquoise-mist/10",
          sizeStyles[size]
        )}>
          {src && !imageError ? (
            <img
              src={src}
              alt={alt || name}
              onError={() => setImageError(true)}
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
            />
          ) : (
            <span className="font-mono font-medium text-deep-teal-800 dark:text-turquoise-mist tracking-widest leading-none">
              {initials}
            </span>
          )}
        </div>

        {/* Status Indicator */}
        {status && (
          <span className={cn(
            "absolute rounded-full box-content",
            // The border matches the page background to create a 'cutout' look
            "border-paper-100 dark:border-obsidian-400",
            status === 'online' ? "bg-gain shadow-[0_0_8px_rgba(46,204,113,0.6)]" : "bg-obsidian-400/30 dark:bg-paper-100/30",
            statusStyles[size]
          )} />
        )}
      </div>
    );
  }
);

Avatar.displayName = "Avatar";

export { Avatar };