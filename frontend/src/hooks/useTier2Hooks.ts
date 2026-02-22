import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useVisibilityPolling } from './useVisibilityPolling';

/**
 * TIER 2 HOOKS - Visibility-Aware Polling
 * These hooks poll periodically but stop when tab is hidden
 * Reduces API requests while maintaining reasonable freshness
 */

export function useDashboardSummary() {
  const refetchInterval = useVisibilityPolling(30000); // 30s

  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: api.dashboard.getSummary,
    refetchInterval,
    refetchOnWindowFocus: false,
  });
}

export function useEquityCurve(timeRange = '1M') {
  const refetchInterval = useVisibilityPolling(120000); // 2min

  return useQuery({
    queryKey: ['dashboard', 'equity', timeRange],
    queryFn: () => api.dashboard.getEquity(timeRange),
    refetchInterval,
    refetchOnWindowFocus: false,
  });
}

export function usePerformanceMetrics() {
  const refetchInterval = useVisibilityPolling(60000); // 1min

  return useQuery({
    queryKey: ['dashboard', 'performance'],
    queryFn: api.dashboard.getPerformance,
    refetchInterval,
    refetchOnWindowFocus: false,
  });
}

export function useStrategies(statusFilter?: string) {
  const refetchInterval = useVisibilityPolling(60000); // 1min

  return useQuery({
    queryKey: ['strategies', 'list', statusFilter],
    queryFn: () => api.strategies.list(statusFilter),
    refetchInterval,
    refetchOnWindowFocus: false,
  });
}

export function usePnlHeatmap(years = 1) {
  const refetchInterval = useVisibilityPolling(300000); // 5min

  return useQuery({
    queryKey: ['pnl', 'heatmap', years],
    queryFn: () => api.pnl.heatmap(years),
    refetchInterval,
    refetchOnWindowFocus: false,
  });
}

export function useDailyPnL(days = 30) {
  const refetchInterval = useVisibilityPolling(60000); // 1min

  return useQuery({
    queryKey: ['pnl', 'daily', days],
    queryFn: () => api.pnl.daily(days),
    refetchInterval,
    refetchOnWindowFocus: false,
  });
}

export function useMonthlyPnL(months = 12) {
  const refetchInterval = useVisibilityPolling(300000); // 5min

  return useQuery({
    queryKey: ['pnl', 'monthly', months],
    queryFn: () => api.pnl.monthly(months),
    refetchInterval,
    refetchOnWindowFocus: false,
  });
}

export function useStrategyPnL(days = 30) {
  const refetchInterval = useVisibilityPolling(120000); // 2min

  return useQuery({
    queryKey: ['pnl', 'by-strategy', days],
    queryFn: () => api.pnl.byStrategy(days),
    refetchInterval,
    refetchOnWindowFocus: false,
  });
}
