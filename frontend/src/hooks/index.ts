// ========== SSE Real-Time Connection ==========
export { useEventStream } from './useEventStream';

// ========== Utility Hooks ==========
export { useVisibilityPolling } from './useVisibilityPolling';

// ========== Tier 1: SSE-Driven Real-Time Hooks ==========
export {
  useKillSwitch,
  useSystemStatus,
  useRiskStatus,
  useDashboardPositions,
  useDashboardAlerts,
  useRegime,
} from './useTier1Hooks';

// ========== Tier 2: Visibility-Aware Polling Hooks ==========
export {
  useDashboardSummary,
  useEquityCurve,
  usePerformanceMetrics,
  useStrategies,
  usePnlHeatmap,
  useDailyPnL,
  useMonthlyPnL,
  useStrategyPnL,
} from './useTier2Hooks';

// ========== Tier 3: On-Demand Hooks ==========
export {
  useStrategy,
  useAccount,
  useAccountBalance,
  useAccountPnL,
  useOrder,
  useOrderList,
  usePositionList,
  usePosition,
  useAccounts,
  usePaperTradingStatus,
  useRiskLimits,
  useDashboardTrades,
  usePositionStaleness,
  useHealthCheck,
  useStrategyTransitions,
} from './useTier3Hooks';

// ========== Mutation Hooks ==========
export {
  useStartSystem,
  useStopSystem,
  useSetRegime,
  useActivateKillSwitch,
  useDeactivateKillSwitch,
  useGetDeactivationCode,
  useUpdateRiskLimits,
  useTransitionStrategy,
  useCreateStrategy,
  useUpdateStrategyParameters,
  useDeleteStrategy,
  useCreateOrder,
  useCancelOrder,
  useReconcileOrders,
  useClosePosition,
  useRunBacktest,
  useStartPaperTrading,
  useStopPaperTrading,
  useAcknowledgeAlert,
  useCreateAccount,
  useUpdateAccount,
} from './useMutations';

// ========== Utility / Effect Hooks ==========
export { useGlobalShortcuts } from './useGlobalShortcuts';
