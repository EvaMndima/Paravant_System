/**
 * ApiErrorDisplay — Presentational component for failed API calls.
 *
 * Handles 3 error categories:
 * - Network errors (no response): "Unable to connect to server"
 * - 401 Unauthorized: "Session expired"
 * - 500 / other server errors: "Server error"
 */
import React from 'react';
import { WifiOff, ServerCrash, ShieldAlert, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ApiErrorDisplayProps {
  error: Error | { status?: number; message?: string } | null | unknown;
  onRetry?: () => void;
  /** compact = inline message line, full = glass-card block */
  compact?: boolean;
  className?: string;
}

interface ErrorConfig {
  icon: React.ElementType;
  heading: string;
  message: string;
  showRetry: boolean;
}

function classifyError(error: unknown): ErrorConfig {
  // Check for HTTP status codes
  if (error && typeof error === 'object' && 'status' in error) {
    const status = (error as { status: number }).status;
    if (status === 401) {
      return {
        icon: ShieldAlert,
        heading: 'Session expired',
        message: 'Your session has expired. Please reload the page to continue.',
        showRetry: false,
      };
    }
    if (status >= 500) {
      return {
        icon: ServerCrash,
        heading: 'Server error',
        message: 'Server error. The team has been notified.',
        showRetry: true,
      };
    }
  }

  // Network / fetch error
  if (
    error instanceof TypeError ||
    (error instanceof Error && error.message.toLowerCase().includes('fetch'))
  ) {
    return {
      icon: WifiOff,
      heading: 'Unable to connect',
      message: 'Unable to connect to server. Check your connection.',
      showRetry: true,
    };
  }

  // Fallback
  return {
    icon: ServerCrash,
    heading: 'Something went wrong',
    message: 'An unexpected error occurred. Please try again.',
    showRetry: true,
  };
}

export const ApiErrorDisplay: React.FC<ApiErrorDisplayProps> = ({
  error,
  onRetry,
  compact = false,
  className,
}) => {
  if (!error) return null;

  const { icon: Icon, heading, message, showRetry } = classifyError(error);

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2 py-2 text-sm text-warning', className)}>
        <Icon className="w-4 h-4 flex-shrink-0" />
        <span className="font-mono">{message}</span>
        {showRetry && onRetry && (
          <button
            onClick={onRetry}
            className="ml-auto flex items-center gap-1 text-xs underline hover:no-underline"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 py-12 text-center rounded-2xl',
        'bg-white/5 border border-white/10',
        className,
      )}
    >
      <div className="w-12 h-12 rounded-full bg-warning/10 flex items-center justify-center">
        <Icon className="w-6 h-6 text-warning" />
      </div>
      <div>
        <p className="font-display font-medium text-base mb-1">{heading}</p>
        <p className="text-sm text-paper-100/60 max-w-xs">{message}</p>
      </div>
      {showRetry && onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-sm font-medium transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Try again
        </button>
      )}
    </div>
  );
};
