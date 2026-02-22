import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { CreateOrderRequest, RiskLimits } from '@/types/api';

/**
 * MUTATION HOOKS - Write Operations
 * These hooks handle POST/PUT/DELETE operations
 * Automatically invalidate related queries on success
 */

// ========== System Mutations ==========

export function useStartSystem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.system.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
    },
  });
}

export function useStopSystem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.system.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
    },
  });
}

export function useSetRegime() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ regime, note }: { regime: string; note?: string }) =>
      api.system.setRegime(regime, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system', 'regime'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] });
    },
  });
}

// ========== Risk Mutations ==========

export function useActivateKillSwitch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (reason: string) => api.risk.activateKillSwitch(reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', 'kill-switch'] });
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
    },
  });
}

export function useDeactivateKillSwitch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (confirmationCode: string) =>
      api.risk.deactivateKillSwitch(confirmationCode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', 'kill-switch'] });
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
    },
  });
}

export function useGetDeactivationCode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.risk.getDeactivationCode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', 'kill-switch'] });
    },
  });
}

export function useUpdateRiskLimits() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (limits: Partial<RiskLimits>) => api.risk.updateLimits(limits),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', 'limits'] });
    },
  });
}

// ========== Strategy Mutations ==========

// Single transition hook replaces activate/pause/stop
export function useTransitionStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      strategyId,
      newStatus,
      reason,
    }: {
      strategyId: string;
      newStatus: string;
      reason?: string;
    }) => api.strategies.transition(strategyId, newStatus, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] });
    },
  });
}

export function useCreateStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategy: {
      name: string;
      template_id: string;
      parameters: Record<string, unknown>;
      symbols: string[];
      description?: string;
    }) => api.strategies.create(strategy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}

export function useUpdateStrategyParameters() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      strategyId,
      parameters,
    }: {
      strategyId: string;
      parameters: Record<string, unknown>;
    }) => api.strategies.updateParameters(strategyId, parameters),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['strategies', variables.strategyId],
      });
      queryClient.invalidateQueries({ queryKey: ['strategies', 'list'] });
    },
  });
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategyId: string) => api.strategies.delete(strategyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] });
    },
  });
}

// ========== Order Mutations ==========

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (order: CreateOrderRequest) => api.orders.create(order),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'positions'] });
    },
  });
}

export function useCancelOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (orderId: string) => api.orders.cancel(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useReconcileOrders() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.orders.reconcile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['positions'] });
    },
  });
}

// ========== Position Mutations ==========

// Backend uses symbol as position identifier
export function useClosePosition() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (symbol: string) => api.positions.close(symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'positions'] });
    },
  });
}

// ========== Backtest Mutations ==========

export function useRunBacktest() {
  return useMutation({
    mutationFn: ({
      strategyId,
      request,
    }: {
      strategyId: string;
      request: Omit<
        import('@/types/api').BacktestRequest,
        'strategy_id'
      >;
    }) => api.backtest.run(strategyId, request),
  });
}

// ========== Paper Trading Mutations ==========

export function useStartPaperTrading() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      strategyId,
      initialCapital,
    }: {
      strategyId: string;
      initialCapital: number;
    }) => api.paper.start(strategyId, initialCapital),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['paper', variables.strategyId],
      });
    },
  });
}

export function useStopPaperTrading() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategyId: string) => api.paper.stop(strategyId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['paper', variables] });
    },
  });
}

// ========== Alert Mutations ==========

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: string) => api.dashboard.acknowledgeAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'alerts'] });
    },
  });
}

// ========== Account Mutations ==========

export function useCreateAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (account: {
      name: string;
      broker: string;
      profile: string;
      initial_balance?: number;
    }) => api.accounts.create(account),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useUpdateAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      accountId,
      updates,
    }: {
      accountId: string;
      updates: {
        name?: string;
        profile?: string;
        regime?: string;
        risk_config?: Record<string, unknown>;
      };
    }) => api.accounts.update(accountId, updates),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['accounts', variables.accountId],
      });
      queryClient.invalidateQueries({ queryKey: ['accounts', 'list'] });
    },
  });
}
