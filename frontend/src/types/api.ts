// ========== System Types ==========
// Aligned with backend SystemStatusResponse (src/api/routes/system.py)

export interface SystemStatus {
  status: string;
  mode: string;
  uptime_seconds: number;
  active_strategies: number;
  open_positions: number;
  daily_pnl: number;
  kill_switch_active: boolean;
  trading_enabled: boolean;
  health_status: string;
  circuit_breakers: Record<string, unknown>;
  last_trade_at: string | null;
  started_at: string | null;
  metrics: Record<string, unknown>;
  timestamp: string;
}

// Aligned with backend RegimeResponse (src/api/routes/system.py)
export interface RegimeInfo {
  regime: string;
  account_id: string;
  updated_at: string;
}

export interface RegimeHistoryEntry {
  timestamp: string;
  action: string;
  actor: string;
  details: Record<string, unknown>;
}

export interface RegimeHistoryResponse {
  history: RegimeHistoryEntry[];
  total: number;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  checks: {
    database: boolean;
    broker_connection: boolean;
    data_feed: boolean;
  };
}

// ========== Dashboard Types ==========
// Aligned with backend DashboardSummaryResponse (src/api/routes/dashboard.py)

export interface DashboardSummary {
  portfolio_value: number;
  daily_change: number;
  daily_change_pct: number;
  weekly_change: number;
  weekly_change_pct: number;
  monthly_change: number;
  monthly_change_pct: number;
  open_positions_count: number;
  active_strategies_count: number;
  trades_today: number;
  win_rate_7d: number;
  max_drawdown_30d: number;
  risk_status: string;
  current_drawdown_pct: number;
  daily_loss_used_pct: number;
  current_regime: string;
  equity_sparkline: number[];
  timestamp: string;
}

// Aligned with backend EquityPoint / EquityCurveResponse
export interface EquityPoint {
  timestamp: string;
  equity: number;
}

export interface EquityCurve {
  data: EquityPoint[];
  time_range: string;
  total_return_pct: number;
  data_points: number;
}

// Aligned with backend PerformanceMetricsResponse
export interface PerformanceMetrics {
  win_rate: number;
  total_return: number;
  total_return_pct: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  profit_factor: number;
  period_days: number;
}

// Aligned with backend DashboardPositionEntry / DashboardPositionListResponse
export interface DashboardPositionEntry {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  duration_hours: number;
  strategy_name: string | null;
}

export interface DashboardPositionListResponse {
  positions: DashboardPositionEntry[];
  total: number;
}

// Aligned with backend TradeEntry / TradeListResponse
export interface TradeEntry {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  commission: number;
  executed_at: string;
  order_id: string;
}

export interface TradeListResponse {
  trades: TradeEntry[];
  total: number;
}

// Aligned with backend AlertEntry / AlertListResponse (audit log format)
export interface AlertEntry {
  id: string;
  timestamp: string;
  action: string;
  actor: string;
  details: Record<string, unknown>;
}

export interface AlertListResponse {
  alerts: AlertEntry[];
  total: number;
}

// ========== Risk Types ==========
// Aligned with backend KillSwitchStatusResponse (src/api/routes/risk.py)

export interface KillSwitchStatus {
  active: boolean;
  activated_at: string | null;
  reason: string | null;
  duration_seconds: number | null;
  trading_enabled: boolean;
}

export interface DeactivationCodeResponse {
  code: string;
  message: string;
}

// Derived from SystemStatus for risk page display
export interface DerivedRiskStatus {
  current_drawdown_pct: number;
  daily_loss_used_pct: number;
  daily_pnl: number;
  kill_switch_active: boolean;
  trading_enabled: boolean;
  circuit_breakers: Record<string, unknown>;
  open_positions: number;
  risk_status: string;
}

export interface RiskLimits {
  max_daily_loss_pct: number;
  max_total_drawdown_pct: number;
  max_position_size_pct: number;
  max_positions: number;
}

// ========== Order Types ==========
// Aligned with backend OrderResponse / OrderListResponse (src/api/routes/orders.py)

export interface OrderResponse {
  id: string;
  external_id: string | null;
  account_id: string;
  strategy_id: string | null;
  symbol: string;
  side: string;
  type: string;
  quantity: number;
  price: number | null;
  status: string;
  filled_quantity: number;
  filled_price: number | null;
  filled_at: string | null;
  submitted_at: string | null;
  rejection_reason: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface OrderListResponse {
  orders: OrderResponse[];
  total: number;
}

export interface CreateOrderRequest {
  symbol: string;
  side: 'BUY' | 'SELL';
  order_type: 'MARKET';
  quantity: number;
  strategy_id: string;
}

// Aligned with backend ReconciliationResponse
export interface ReconciliationResponse {
  orders_updated: number;
  updated_order_ids: string[];
  timestamp: string;
}

// ========== Position Types ==========
// Aligned with backend PositionResponse (src/api/routes/positions.py)

export interface PositionResponse {
  id: string;
  account_id: string;
  strategy_id: string | null;
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  return_pct: number;
  realized_pnl: number;
  commission_paid: number;
  status: string;
  opened_at: string;
  closed_at: string | null;
  exit_price: number | null;
}

export interface PositionListResponse {
  positions: PositionResponse[];
  total: number;
}

export interface StalenessEntry {
  position_id: string;
  symbol: string;
  hold_duration_hours: number;
  should_warn: boolean;
  should_review: boolean;
  should_close: boolean;
  days_remaining: number;
  status: string;
}

export interface StalenessAnalysis {
  positions: StalenessEntry[];
  total: number;
  warnings: number;
  reviews: number;
  exceeded: number;
}

// ========== Strategy Types ==========
// Aligned with backend StrategyResponse (src/api/routes/strategies.py)

export interface StrategyResponse {
  id: string;
  name: string;
  status: string;
  template_id: string;
  template_version: string;
  type: string;
  symbols: string[];
  description: string | null;
  parameters: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
}

export interface StrategyDetailResponse extends StrategyResponse {
  config: Record<string, unknown>;
  performance_metrics: PerformanceMetrics;
  recent_trades: TradeEntry[];
}

export interface StrategyListResponse {
  strategies: StrategyResponse[];
  total: number;
}

export interface CreateStrategyRequest {
  name: string;
  template_id: string;
  parameters: Record<string, unknown>;
  symbols: string[];
  description?: string;
}

export interface TransitionRequest {
  new_status: string;
  reason?: string;
}

// Aligned with backend BacktestRequest / BacktestResponse
export interface BacktestRequest {
  strategy_id: string;
  initial_capital: number;
  commission_rate?: number;
  slippage_rate?: number;
  symbol?: string;
  timeframe?: string;
  lookback_days?: number;
}

export interface BacktestMetrics {
  total_return_pct: number;
  annualized_return_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  total_trades: number;
  win_rate_pct: number;
  profit_factor: number;
  expectancy: number;
  passed_validation: boolean;
  validation_errors: string[];
}

export interface BacktestResponse {
  strategy_id: string;
  strategy_name: string;
  status: string;
  metrics: BacktestMetrics;
  initial_capital: number;
  final_capital: number;
  start_date: string;
  end_date: string;
}

// Aligned with backend PaperStatusResponse
export interface PaperTradingStatus {
  strategy_id: string;
  mode: string;
  is_running: boolean;
  started_at: string | null;
  stopped_at: string | null;
  current_equity: number;
  current_pnl_pct: number;
  num_trades: number;
  days_elapsed: number;
  validation_passed: boolean | null;
}

// ========== Account Types ==========
// Aligned with backend AccountResponse (src/api/routes/accounts.py)

export interface AccountResponse {
  id: string;
  name: string;
  broker: string;
  profile: string;
  status: string;
  balance_usdt: number;
  equity_usdt: number;
  regime: string;
  risk_config: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface AccountDetailResponse extends AccountResponse {
  open_positions_count: number;
  active_strategies_count: number;
}

export interface AccountListResponse {
  accounts: AccountResponse[];
  total: number;
}

// Aligned with backend BalanceResponse
export interface BalanceResponse {
  account_id: string;
  balance_usdt: number;
  equity_usdt: number;
  available_margin: number;
  open_positions_value: number;
  timestamp: string;
}

export interface PnLEntry {
  date: string;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  portfolio_value: number;
  daily_return_pct: number | null;
  trades_count: number;
}

export interface PnLSummary {
  total_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  best_day: number;
  worst_day: number;
}

export interface AccountPnLResponse {
  account_id: string;
  records: PnLEntry[];
  summary: PnLSummary;
  period_start: string;
  period_end: string;
}

// ========== P&L Types ==========
// Aligned with backend pnl.py models

export interface DailyPnLEntry {
  date: string;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  portfolio_value: number;
  daily_return_pct: number | null;
  drawdown_pct: number | null;
  trades_count: number;
  winning_trades: number;
  losing_trades: number;
}

export interface DailyPnLResponse {
  records: DailyPnLEntry[];
  total: number;
  period_start: string;
  period_end: string;
  cumulative_pnl: number;
}

export interface MonthlyPnLEntry {
  year: number;
  month: number;
  month_name: string;
  total_pnl: number;
  return_pct: number;
  trades_count: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
}

export interface MonthlyPnLResponse {
  records: MonthlyPnLEntry[];
  total: number;
}

export interface StrategyPnLEntry {
  strategy_id: string;
  strategy_name: string;
  total_pnl: number;
  return_pct: number;
  trades_count: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
}

export interface StrategyPnLResponse {
  strategies: StrategyPnLEntry[];
  total: number;
}

export interface HeatmapCell {
  year: number;
  month: number;
  return_pct: number;
  trade_count: number;
}

export interface HeatmapResponse {
  cells: HeatmapCell[];
  years: number[];
  months: number[];
}

// ========== Action Response ==========

export interface ActionResponse {
  status: string;
  message: string;
  timestamp: string;
}

// ========== Error Response ==========

export interface ApiError {
  detail: string;
  status_code?: number;
}
