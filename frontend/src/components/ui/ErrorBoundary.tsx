/**
 * ErrorBoundary — Catches React render errors in child component tree.
 *
 * Per DESIGN_GUIDE: shows styled glass-panel error UI. Each page route
 * should be wrapped independently so one page crash doesn't kill the whole app.
 */
import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';

interface Props {
  children: React.ReactNode;
  /** Optional custom fallback. Defaults to built-in error UI. */
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // Log for debugging. In production this could forward to an error tracking service.
    console.error('[ErrorBoundary] Component tree error:', error, info.componentStack);
  }

  private handleReload = (): void => {
    window.location.reload();
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex items-start justify-center py-16 px-6">
          <GlassCard variant="dark" className="max-w-md w-full">
            <div className="flex flex-col items-center text-center gap-4">
              <div className="w-14 h-14 rounded-full bg-loss/10 flex items-center justify-center">
                <AlertTriangle className="w-7 h-7 text-loss" />
              </div>
              <div>
                <h2 className="text-lg font-display font-medium mb-1">Something went wrong</h2>
                <p className="text-sm text-paper-100/60">
                  An unexpected error occurred in this section. Your data is safe.
                </p>
              </div>
              {this.state.error && (
                <details className="w-full text-left">
                  <summary className="text-xs font-mono text-paper-100/40 cursor-pointer hover:text-paper-100/60">
                    Error details
                  </summary>
                  <pre className="mt-2 text-[10px] font-mono text-loss/80 whitespace-pre-wrap break-all bg-black/20 rounded-lg p-3 max-h-40 overflow-auto">
                    {this.state.error.message}
                  </pre>
                </details>
              )}
              <button
                onClick={this.handleReload}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-sm font-medium transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Reload Page
              </button>
            </div>
          </GlassCard>
        </div>
      );
    }

    return this.props.children;
  }
}
