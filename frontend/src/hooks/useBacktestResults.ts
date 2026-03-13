/**
 * Hook for fetching complete backtest results from the API.
 *
 * Fetches GET /api/v1/strategies/{strategyId}/backtest/results and maps
 * the backend response to the BacktestResult shape expected by
 * BacktestResultsModal.
 */
import { useState, useEffect } from 'react';
import type { BacktestResult, BacktestTrade } from '@/components/dashboard/BacktestResultsModal';
import type { AreaChartData } from '@/components/charts/AreaChart';

// ── Backend response types ────────────────────────────────────────────────────

interface ApiEquityPoint {
  timestamp: string;
  value: number;
}

interface ApiTrade {
  id: string;
  entry_time: string;
  exit_time: string;
  symbol: string;
  direction: 'long' | 'short';
  entry_price: number;
  exit_price: number;
  quantity: number;
  realized_pnl: number;
  return_pct: number;
  duration_hours: number;
  commission_total: number;
}

interface ApiMetrics {
  total_return_pct: number;
  annualized_return_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown_pct: number;
  max_drawdown_duration_days: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  profit_factor: number;
  expectancy: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  largest_win: number;
  largest_loss: number;
  passed_validation: boolean;
  validation_errors: string[];
}

interface ApiBacktestResponse {
  strategy_id: string;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  metrics: ApiMetrics;
  equity_curve: ApiEquityPoint[];
  trades: ApiTrade[];
  passed_validation: boolean;
  validation_errors: string[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatIsoToShortDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}

function formatDurationHours(hours: number): string {
  if (hours >= 24) {
    return `${Math.round(hours / 24)}d`;
  }
  return `${Math.round(hours)}h`;
}

/** Strip base asset from pair, e.g. "BTCUSDT" -> "BTC", "ETHUSDT" -> "ETH". */
function stripQuoteCurrency(symbol: string): string {
  return symbol.replace(/USDT$|BUSD$|USD$/, '');
}

/** Derive a human-readable period label from start/end ISO strings. */
function derivePeriod(startIso: string, endIso: string): string {
  try {
    const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
    const months = Math.round(ms / (30.44 * 24 * 3600 * 1000));
    if (months <= 0) return '1M';
    if (months >= 12) return `${Math.round(months / 12)}Y`;
    return `${months}M`;
  } catch {
    return '--';
  }
}

// ── Mapper ────────────────────────────────────────────────────────────────────

function mapApiResponse(api: ApiBacktestResponse): BacktestResult {
  const equityCurve: AreaChartData[] = api.equity_curve.map((ep) => ({
    date: formatIsoToShortDate(ep.timestamp),
    value: ep.value,
  }));

  const trades: BacktestTrade[] = api.trades.map((t) => ({
    id: t.id,
    symbol: stripQuoteCurrency(t.symbol),
    side: t.direction,
    entryDate: formatIsoToShortDate(t.entry_time),
    exitDate: formatIsoToShortDate(t.exit_time),
    entryPrice: t.entry_price,
    exitPrice: t.exit_price,
    pnl: t.realized_pnl,
    pnlPct: t.return_pct,
    duration: formatDurationHours(t.duration_hours),
  }));

  // Compute avg win / avg loss in dollar terms from actual trade P&L
  const winners = api.trades.filter((t) => t.realized_pnl > 0);
  const losers = api.trades.filter((t) => t.realized_pnl < 0);
  const avgWin =
    winners.length > 0
      ? winners.reduce((sum, t) => sum + t.realized_pnl, 0) / winners.length
      : 0;
  const avgLoss =
    losers.length > 0
      ? losers.reduce((sum, t) => sum + t.realized_pnl, 0) / losers.length
      : 0;

  const m = api.metrics;
  const maxDrawdownAbs = Math.abs(m.max_drawdown_pct);
  const recoveryFactor = maxDrawdownAbs > 0 ? m.total_return_pct / maxDrawdownAbs : 0;

  return {
    strategyName: api.strategy_name,
    symbol: api.symbol,
    period: derivePeriod(api.start_date, api.end_date),
    startDate: formatIsoToShortDate(api.start_date),
    endDate: formatIsoToShortDate(api.end_date),
    initialCapital: api.initial_capital,
    finalCapital: api.final_capital,
    totalReturn: api.final_capital - api.initial_capital,
    totalReturnPct: m.total_return_pct,
    annualizedReturn: m.annualized_return_pct,
    maxDrawdown: -maxDrawdownAbs,  // modal expects negative, e.g. -12.4
    sharpeRatio: m.sharpe_ratio,
    winRate: m.win_rate_pct,
    totalTrades: m.total_trades,
    winningTrades: m.winning_trades,
    losingTrades: m.losing_trades,
    avgWin,
    avgLoss,
    profitFactor: m.profit_factor,
    equityCurve,
    trades,
    // Extended optional fields
    sortinoRatio: m.sortino_ratio,
    calmarRatio: m.calmar_ratio,
    expectancy: m.expectancy,
    recoveryFactor,
    maxDrawdownDuration: m.max_drawdown_duration_days,
    passedValidation: api.passed_validation,
    validationErrors: api.validation_errors,
  };
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export interface UseBacktestResultsReturn {
  data: BacktestResult | null;
  isLoading: boolean;
  error: string | null;
}

export function useBacktestResults(
  strategyId: string | null,
): UseBacktestResultsReturn {
  const [data, setData] = useState<BacktestResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!strategyId) {
      setData(null);
      setError(null);
      return;
    }

    let cancelled = false;

    setIsLoading(true);
    setError(null);

    fetch(`/api/v1/strategies/${strategyId}/backtest/results`)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((body) => {
            throw new Error(body?.detail ?? `HTTP ${res.status}`);
          });
        }
        return res.json() as Promise<ApiBacktestResponse>;
      })
      .then((api) => {
        if (!cancelled) {
          setData(mapApiResponse(api));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load backtest results');
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [strategyId]);

  return { data, isLoading, error };
}
