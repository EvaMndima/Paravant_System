import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

/**
 * TIER 3 HOOKS - On-Demand Fetching
 * These hooks only fetch when enabled (user navigates to detail page)
 * No automatic refetching - data is fetched once and cached
 */

export function useStrategy(id: string, enabled = true) {
  return useQuery({
    queryKey: ['strategies', id],
    queryFn: () => api.strategies.get(id),
    enabled: !!id && enabled,
    staleTime: 60000, // 1 min freshness
  });
}

export function useAccount(id: string, enabled = true) {
  return useQuery({
    queryKey: ['accounts', id],
    queryFn: () => api.accounts.get(id),
    enabled: !!id && enabled,
    staleTime: 60000,
  });
}

export function useAccountBalance(id: string, enabled = true) {
  return useQuery({
    queryKey: ['accounts', id, 'balance'],
    queryFn: () => api.accounts.getBalance(id),
    enabled: !!id && enabled,
    staleTime: 30000, // 30s freshness for balance
  });
}

export function useAccountPnL(id: string, days = 30, enabled = true) {
  return useQuery({
    queryKey: ['accounts', id, 'pnl', days],
    queryFn: () => api.accounts.getPnL(id, days),
    enabled: !!id && enabled,
    staleTime: 60000,
  });
}

export function useOrder(id: string, enabled = true) {
  return useQuery({
    queryKey: ['orders', id],
    queryFn: () => api.orders.get(id),
    enabled: !!id && enabled,
    staleTime: 30000,
  });
}

export function useOrderList(status?: string, limit = 100) {
  return useQuery({
    queryKey: ['orders', 'list', status, limit],
    queryFn: () => api.orders.list(status, limit),
    staleTime: 30000,
  });
}

export function usePositionList(symbol?: string, status?: string) {
  return useQuery({
    queryKey: ['positions', 'list', symbol, status],
    queryFn: () => api.positions.list(symbol, status),
    staleTime: 30000,
  });
}

export function usePosition(symbol: string, enabled = true) {
  return useQuery({
    queryKey: ['positions', symbol],
    queryFn: () => api.positions.get(symbol),
    enabled: !!symbol && enabled,
    staleTime: 30000,
  });
}

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts', 'list'],
    queryFn: api.accounts.list,
    staleTime: 300000, // 5min - accounts change rarely
  });
}

export function usePaperTradingStatus(strategyId: string, enabled = true) {
  return useQuery({
    queryKey: ['paper', strategyId, 'status'],
    queryFn: () => api.paper.getStatus(strategyId),
    enabled: !!strategyId && enabled,
    staleTime: 60000,
  });
}

export function useRiskLimits() {
  return useQuery({
    queryKey: ['risk', 'limits'],
    queryFn: api.risk.getLimits,
    staleTime: 300000, // 5min - limits change rarely
  });
}

export function useDashboardTrades(limit = 50) {
  return useQuery({
    queryKey: ['dashboard', 'trades', limit],
    queryFn: () => api.dashboard.getTrades(limit),
    staleTime: 60000,
  });
}

export function usePositionStaleness() {
  return useQuery({
    queryKey: ['positions', 'staleness'],
    queryFn: api.positions.staleness,
    staleTime: 120000, // 2min
  });
}

export function useHealthCheck(type: 'quick' | 'full' = 'quick') {
  return useQuery({
    queryKey: ['health', type],
    queryFn: type === 'quick' ? api.system.healthQuick : api.system.healthFull,
    staleTime: 30000,
  });
}

/**
 * Fetches the available state transitions for a strategy.
 * Returns a map of state → allowable next states from the backend
 * state machine. Used by the Lifecycle tab (PRD §6.4.7).
 */
export function useStrategyTransitions(strategyId: string, enabled = true) {
  return useQuery({
    queryKey: ['strategies', strategyId, 'transitions'],
    queryFn: () => api.strategies.getTransitions(strategyId),
    enabled: !!strategyId && enabled,
    staleTime: 300000, // 5 min — state machine topology rarely changes
  });
}
