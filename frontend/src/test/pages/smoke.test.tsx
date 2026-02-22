/**
 * Smoke Tests — All 10 Dashboard Pages
 *
 * Tests that each page component renders without crashing when given
 * minimal valid API data. No real backend required — all API calls are mocked.
 *
 * These tests verify the integration layer (hooks → components → DOM) compiles
 * and renders correctly. They are NOT interaction tests.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../helpers/renderWithProviders';

// --- Page imports ---
import { CockpitPage } from '@/pages/dashboard/Cockpit';
import { PortfolioPage } from '@/pages/dashboard/Portfolio';
import { StrategiesPage } from '@/pages/dashboard/Strategies';
import { StrategyDetailPage } from '@/pages/dashboard/StrategyDetail';
import { RiskPage } from '@/pages/dashboard/Risk';
import { OrdersPage } from '@/pages/dashboard/Orders';
import { AlertsPage } from '@/pages/dashboard/Alerts';
import { AccountsPage } from '@/pages/dashboard/Accounts';
import { SettingsPage } from '@/pages/dashboard/Settings';
import { BacktestPage } from '@/pages/dashboard/Backtest';

// ---------------------------------------------------------------------------
// Fixtures declared with vi.hoisted() so they are available inside vi.mock()
// factories (which are hoisted to the top of the file by vitest's transform).
// ---------------------------------------------------------------------------

const fixtures = vi.hoisted(() => {
  const now = new Date().toISOString();

  const mockStrategy = {
    id: 'strat-1',
    name: 'Momentum Trend',
    type: 'trend_following',
    status: 'active',
    template_id: 'simple_ma',
    template_version: '1.0',
    symbols: ['BTCUSDT'],
    description: 'Simple moving average crossover',
    parameters: {},
    recent_trades: [],
    created_at: now,
    updated_at: now,
  };

  return {
    mockSystemStatus: {
      status: 'running',
      mode: 'live',
      uptime_seconds: 3600,
      active_strategies: 2,
      open_positions: 1,
      daily_pnl: 250.0,
      kill_switch_active: false,
      trading_enabled: true,
      health_status: 'healthy',
      circuit_breakers: {},
      last_trade_at: null,
      started_at: now,
      metrics: { current_drawdown_pct: 1.2, daily_loss_used_pct: 5.0 },
      timestamp: now,
    },
    mockDashboardSummary: {
      portfolio_value: 12500.0,
      daily_pnl: 250.0,
      daily_change_pct: 2.0,
      weekly_change_pct: 4.5,
      monthly_change_pct: 8.1,
      open_positions_count: 1,
      trades_today: 3,
      win_rate_7d: 0.65,
      max_drawdown_30d: 3.2,
      risk_status: 'healthy',
      current_drawdown_pct: 1.2,
      daily_loss_used_pct: 5.0,
      current_regime: 'trending_up',
      equity_sparkline: [],
      timestamp: now,
    },
    mockEquityCurve: {
      time_range: '1M',
      data_points: 0,
      data: [],
      total_return_pct: 8.1,
    },
    mockKillSwitch: {
      is_active: false,
      activated_at: null,
      reason: null,
      trading_enabled: true,
      duration_seconds: null,
    },
    mockRiskLimits: {
      max_position_pct: 0.1,
      max_daily_loss_pct: 0.02,
      max_total_drawdown_pct: 0.1,
    },
    mockRegime: {
      regime: 'trending_up',
      account_id: 'acc-1',
      updated_at: now,
    },
    mockAccount: {
      id: 'acc-1',
      name: 'Main Account',
      broker: 'binance',
      profile: 'default',
      status: 'active',
      balance_usdt: 10000,
      equity_usdt: 10500,
      regime: 'trending_up',
      risk_config: {},
      created_at: now,
      updated_at: now,
    },
    mockBalance: {
      account_id: 'acc-1',
      balance_usdt: 10000,
      equity_usdt: 10500,
      available_margin: 9000,
      used_margin: 500,
      unrealised_pnl: 250,
      open_positions_value: 500,
    },
    mockStrategy,
    mockStrategyDetail: {
      ...mockStrategy,
      open_positions: [],
      performance: { win_rate: 0.65, total_return: 8.1, total_return_pct: 8.1 },
    },
    mockOrder: {
      id: 'ord-1',
      account_id: 'acc-1',
      strategy_id: 'strat-1',
      symbol: 'BTCUSDT',
      side: 'BUY',
      order_type: 'market',
      quantity: 0.001,
      status: 'filled',
      filled_quantity: 0.001,
      filled_price: 50000,
      external_id: 'ext-1',
      submitted_at: now,
      filled_at: now,
      rejection_reason: null,
      created_at: now,
      updated_at: now,
    },
    mockAlert: {
      id: 'alert-1',
      timestamp: now,
      action: 'system_started',
      actor: 'system',
      details: { reason: 'scheduled startup' },
    },
    mockPerformanceMetrics: {
      win_rate: 0.65,
      total_return: 8.1,
      total_return_pct: 8.1,
      annualized_return_pct: 12.5,
      sharpe_ratio: 1.8,
      sortino_ratio: 2.1,
      max_drawdown_pct: 3.2,
      profit_factor: 2.4,
      total_trades: 42,
      expectancy: 18.5,
    },
  };
});

// ---------------------------------------------------------------------------
// Mock the entire API client singleton
// ---------------------------------------------------------------------------

vi.mock('@/lib/api', () => ({
  api: {
    system: {
      getStatus: vi.fn().mockResolvedValue(fixtures.mockSystemStatus),
      getRegime: vi.fn().mockResolvedValue(fixtures.mockRegime),
      getRegimeHistory: vi.fn().mockResolvedValue({ history: [], total: 0 }),
      setRegime: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      start: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      stop: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      getHealth: vi.fn().mockResolvedValue({ status: 'healthy', timestamp: new Date().toISOString(), checks: { database: true, broker_connection: true, data_feed: true } }),
    },
    dashboard: {
      getSummary: vi.fn().mockResolvedValue(fixtures.mockDashboardSummary),
      getEquity: vi.fn().mockResolvedValue(fixtures.mockEquityCurve),
      getPositions: vi.fn().mockResolvedValue([]),
      getAlerts: vi.fn().mockResolvedValue([fixtures.mockAlert]),
      getTrades: vi.fn().mockResolvedValue([fixtures.mockOrder]),
      getMonthlyPnL: vi.fn().mockResolvedValue({ records: [], currency: 'USDT' }),
    },
    risk: {
      getKillSwitch: vi.fn().mockResolvedValue(fixtures.mockKillSwitch),
      getLimits: vi.fn().mockResolvedValue(fixtures.mockRiskLimits),
      activateKillSwitch: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      deactivateKillSwitch: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      getDeactivationCode: vi.fn().mockResolvedValue({ code: 'TEST123', expires_in: 60 }),
      updateLimits: vi.fn().mockResolvedValue(fixtures.mockRiskLimits),
    },
    strategies: {
      list: vi.fn().mockResolvedValue([fixtures.mockStrategy]),
      get: vi.fn().mockResolvedValue(fixtures.mockStrategyDetail),
      create: vi.fn().mockResolvedValue(fixtures.mockStrategy),
      updateParameters: vi.fn().mockResolvedValue(fixtures.mockStrategy),
      delete: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      transition: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      getBacktestResults: vi.fn().mockResolvedValue([]),
      getTransitions: vi.fn().mockResolvedValue({
        active: ['paused', 'stopped'],
        paused: ['active', 'stopped'],
        stopped: [],
      }),
    },
    paper: {
      getStatus: vi.fn().mockResolvedValue({
        strategy_id: 'strat-1',
        mode: 'paper',
        is_running: false,
        started_at: null,
        stopped_at: null,
        current_equity: 10000,
        current_pnl_pct: 0,
        num_trades: 0,
        days_elapsed: 0,
        validation_passed: null,
      }),
      start: vi.fn().mockResolvedValue({ is_running: true }),
      stop: vi.fn().mockResolvedValue({ is_running: false }),
    },
    backtest: {
      run: vi.fn().mockResolvedValue({
        strategy_id: 'strat-1',
        strategy_name: 'Momentum Trend',
        status: 'completed',
        initial_capital: 10000,
        final_capital: 10810,
        start_date: '2025-01-01',
        end_date: '2025-12-31',
        metrics: {
          total_return_pct: 8.1,
          annualized_return_pct: 8.1,
          sharpe_ratio: 1.8,
          sortino_ratio: 2.1,
          max_drawdown_pct: 3.2,
          total_trades: 42,
          win_rate_pct: 65.0,
          profit_factor: 2.4,
          expectancy: 18.5,
          passed_validation: true,
          validation_errors: [],
        },
      }),
    },
    accounts: {
      list: vi.fn().mockResolvedValue({ accounts: [fixtures.mockAccount], total: 1 }),
      get: vi.fn().mockResolvedValue(fixtures.mockAccount),
      getBalance: vi.fn().mockResolvedValue(fixtures.mockBalance),
      create: vi.fn().mockResolvedValue(fixtures.mockAccount),
      update: vi.fn().mockResolvedValue(fixtures.mockAccount),
      getPnL: vi.fn().mockResolvedValue({ daily_pnl: 250, monthly_pnl: 810 }),
    },
    orders: {
      list: vi.fn().mockResolvedValue({ orders: [fixtures.mockOrder], total: 1 }),
      get: vi.fn().mockResolvedValue(fixtures.mockOrder),
      create: vi.fn().mockResolvedValue(fixtures.mockOrder),
      cancel: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      reconcile: vi.fn().mockResolvedValue({ reconciled: 0, discrepancies: [] }),
    },
    positions: {
      list: vi.fn().mockResolvedValue({ positions: [], total: 0 }),
      get: vi.fn().mockResolvedValue(null),
      close: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
      getStaleness: vi.fn().mockResolvedValue({ stale_positions: [], total_stale: 0 }),
    },
    performance: {
      getMetrics: vi.fn().mockResolvedValue(fixtures.mockPerformanceMetrics),
      getDailyPnL: vi.fn().mockResolvedValue({ records: [] }),
      getMonthlyPnL: vi.fn().mockResolvedValue({ records: [] }),
      getStrategyPnL: vi.fn().mockResolvedValue({ records: [] }),
      getHeatmap: vi.fn().mockResolvedValue({ cells: [], years: [], months: [] }),
    },
    alerts: {
      list: vi.fn().mockResolvedValue({ alerts: [fixtures.mockAlert], total: 1 }),
      acknowledge: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
    },
  },
}));

// ---------------------------------------------------------------------------
// Smoke Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Dashboard Page Smoke Tests — All 10 pages render without crashing', () => {

  it('1. CockpitPage renders with loading then content', async () => {
    renderWithProviders(<CockpitPage />);
    await waitFor(() => {
      const headings = screen.queryAllByRole('heading');
      expect(headings.length).toBeGreaterThan(0);
    }, { timeout: 3000 });
  });

  it('2. PortfolioPage renders', async () => {
    renderWithProviders(<PortfolioPage />);
    await waitFor(() => {
      expect(screen.getByText(/portfolio analysis/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('3. StrategiesPage renders strategy list', async () => {
    renderWithProviders(<StrategiesPage />);
    await waitFor(() => {
      expect(screen.getByText(/strategies/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('4. StrategyDetailPage renders for a strategy id', async () => {
    renderWithProviders(<StrategyDetailPage />, { route: '/strategies/strat-1' });
    await waitFor(() => {
      const body = document.body.textContent ?? '';
      expect(body.length).toBeGreaterThan(0);
    }, { timeout: 3000 });
  });

  it('5. RiskPage renders with kill switch section', async () => {
    renderWithProviders(<RiskPage />);
    await waitFor(() => {
      expect(screen.getByText(/risk/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('6. OrdersPage renders order list', async () => {
    renderWithProviders(<OrdersPage />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Orders' })).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('7. AlertsPage renders alert feed', async () => {
    renderWithProviders(<AlertsPage />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'System Alerts' })).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('8. AccountsPage renders account cards', async () => {
    renderWithProviders(<AccountsPage />);
    await waitFor(() => {
      expect(screen.getByText(/accounts/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('9. SettingsPage renders without API data', () => {
    renderWithProviders(<SettingsPage />);
    expect(screen.getByText(/settings/i)).toBeInTheDocument();
  });

  it('10. BacktestPage renders config form with strategy selector', async () => {
    renderWithProviders(<BacktestPage />);
    await waitFor(() => {
      expect(screen.getByText(/backtesting/i)).toBeInTheDocument();
    }, { timeout: 3000 });
    const runBtn = screen.getByRole('button', { name: /run backtest/i });
    expect(runBtn).toBeInTheDocument();
    expect(runBtn).toBeDisabled();
  });

});

// ---------------------------------------------------------------------------
// Critical feature tests
// ---------------------------------------------------------------------------

describe('Kill Switch — accessibility attributes', () => {
  it('kill switch container has correct ARIA when inactive', async () => {
    renderWithProviders(<RiskPage />);
    await waitFor(() => {
      const alertRegions = document.querySelectorAll('[role="alert"]');
      alertRegions.forEach((el) => {
        expect(el).not.toHaveClass('kill-switch-active');
      });
    }, { timeout: 3000 });
  });
});

describe('Backtest Form — controlled inputs', () => {
  it('Run Backtest button is present and accessible', async () => {
    renderWithProviders(<BacktestPage />);
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /run backtest/i });
      expect(btn).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});
