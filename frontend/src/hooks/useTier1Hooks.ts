import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { DerivedRiskStatus } from '@/types/api';

/**
 * TIER 1 HOOKS - SSE Real-Time Updates
 * These hooks are driven by Server-Sent Events (< 100ms latency)
 * staleTime: Infinity because SSE handles updates automatically
 * refetchOnWindowFocus: true to sync on tab switch
 */

export function useKillSwitch() {
  return useQuery({
    queryKey: ['risk', 'kill-switch'],
    queryFn: api.risk.getKillSwitch,
    staleTime: Infinity, // SSE updates the cache
    refetchOnWindowFocus: true,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: ['system', 'status'],
    queryFn: api.system.getStatus,
    staleTime: Infinity,
    refetchOnWindowFocus: true,
  });
}

/**
 * Derived risk status hook.
 * Backend has no dedicated /risk/status endpoint — risk data is part of SystemStatus.
 * This hook extracts risk-relevant fields from the system status response.
 */
export function useRiskStatus() {
  const query = useQuery({
    queryKey: ['system', 'status'],
    queryFn: api.system.getStatus,
    staleTime: Infinity,
    refetchOnWindowFocus: true,
    select: (data): DerivedRiskStatus => ({
      current_drawdown_pct: (data.metrics as Record<string, number>)?.current_drawdown_pct ?? 0,
      daily_loss_used_pct: (data.metrics as Record<string, number>)?.daily_loss_used_pct ?? 0,
      daily_pnl: data.daily_pnl,
      kill_switch_active: data.kill_switch_active,
      trading_enabled: data.trading_enabled,
      circuit_breakers: data.circuit_breakers,
      open_positions: data.open_positions,
      risk_status: data.health_status,
    }),
  });

  return query;
}

export function useDashboardPositions() {
  return useQuery({
    queryKey: ['dashboard', 'positions'],
    queryFn: api.dashboard.getPositions,
    staleTime: Infinity,
    refetchOnWindowFocus: true,
  });
}

export function useDashboardAlerts(unacknowledged = false) {
  return useQuery({
    queryKey: ['dashboard', 'alerts', unacknowledged],
    queryFn: () => api.dashboard.getAlerts(unacknowledged),
    staleTime: Infinity,
    refetchOnWindowFocus: true,
  });
}

export function useRegime() {
  return useQuery({
    queryKey: ['system', 'regime'],
    queryFn: api.system.getRegime,
    staleTime: Infinity,
    refetchOnWindowFocus: true,
  });
}
