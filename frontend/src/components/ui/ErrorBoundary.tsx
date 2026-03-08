import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import { GlassCard } from './GlassCard';

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="w-full h-full min-h-[300px] flex items-center justify-center p-4">
          <GlassCard className="max-w-md w-full flex flex-col items-center text-center p-8" variant="subtle">
            <div className="p-3 bg-loss/10 rounded-full text-loss mb-4">
              <AlertTriangle className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-display font-bold text-obsidian-400 dark:text-paper-100 mb-2">
              System Error
            </h2>
            <p className="text-sm text-obsidian-400/60 dark:text-paper-100/60 mb-6 leading-relaxed">
              An unexpected component crash occurred. The event has been logged. Please try refreshing the interface.
            </p>
            <div className="flex flex-col w-full gap-2">
              <Button
                onClick={this.handleReload}
                variant="primary"
                leftIcon={<RefreshCw className="w-4 h-4" />}
                className="w-full"
              >
                Reload Application
              </Button>
              <div className="mt-4 p-2 bg-black/5 dark:bg-black/20 rounded text-[10px] font-mono text-left w-full overflow-hidden text-obsidian-400/40 dark:text-paper-100/40 truncate">
                Error: {this.state.error?.message}
              </div>
            </div>
          </GlassCard>
        </div>
      );
    }

    return this.props.children;
  }
}
