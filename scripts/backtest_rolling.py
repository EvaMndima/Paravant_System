#!/usr/bin/env python
"""Rolling-window backtest for paper-deployed strategies.

Runs the same backtest on N independent non-overlapping windows so we
can see whether the edge is stable across time or whether it was a
one-window fluke. This is the analysis that should have been done
BEFORE BTF was promoted on the Q1 2026 numbers.

A strategy whose PF varies dramatically across windows (e.g. 3.0 in
Q1 then 0.4 in May) is not robust — it's overfit to a specific market
regime. A strategy whose PF stays in [1.2, 1.8] across all windows is
showing a real (if modest) edge.

Usage:
    # Default: BTF on 4x 30-day windows ending today
    python -m scripts.backtest_rolling

    # All current paper strategies (BTF/CMF/RSI_BB/ICVP)
    python -m scripts.backtest_rolling --strategy all

    # Single strategy across windows
    python -m scripts.backtest_rolling --strategy bear_trend_follower

    # Custom: 6 windows of 21 days each
    python -m scripts.backtest_rolling --windows 6 --window-days 21

    # Quick scan: 2 windows on BTC only
    python -m scripts.backtest_rolling --symbols BTCUSDT --windows 2

Output:
    Per-window, per-symbol table + stability verdict per strategy.

Decision: DEC-2026-05-27-005 (rolling-window validation requirement).
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from src.brokers.binance.client import BinanceClient
from src.core.strategy.backtest import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher
from src.utils.logging import get_logger, setup_logging

setup_logging(level="WARNING")
logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# Strategy parameter snapshots — kept here so the diagnostic is reproducible
# even if scripts/run_paper_trading.py changes. Update these if the live
# paper config changes.
# -----------------------------------------------------------------------------
STRATEGY_PARAMS: dict[str, dict[str, Any]] = {
    "bear_trend_follower": {
        "htf_ema_period": 200,
        "kc_ema_period": 20,
        "kc_atr_period": 14,
        "kc_multiplier": 1.5,
        "adx_period": 14,
        "adx_min_threshold": 20.0,
        "rsi_period": 14,
        "rsi_oversold": 25.0,
        "supertrend_period": 10,
        "supertrend_multiplier": 3.0,
        "atr_period": 14,
        "atr_stop_multiplier": 2.5,
    },
    "cascading_momentum_filter": {
        "daily_st_period": 10,
        "daily_st_multiplier": 3.0,
        "htf_ema_period": 21,
        "htf_adx_period": 14,
        "htf_adx_min": 15.0,
        "htf_slope_lookback": 5,
        "st_period_1h": 10,
        "st_multiplier_1h": 3.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14,
    },
    "rsi_bb_mean_reversion": {
        "rsi_period": 14,
        "rsi_oversold": 25.0,
        "rsi_overbought": 75.0,
        "rsi_exit_long": 50.0,
        "rsi_exit_short": 50.0,
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "adx_threshold": 25.0,
        "stop_loss_pct": 2.5,
        "ema_regime_period": 200,
    },
    "ichimoku_cloud_trend": {
        "tenkan_period": 20,
        "kijun_period": 60,
        "senkou_b_period": 120,
        "displacement": 30,
        "atr_period": 14,
        "volume_period": 20,
        "volume_threshold": 1.3,
    },
}

STRATEGY_SYMBOLS: dict[str, list[str]] = {
    "bear_trend_follower": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
        "XRPUSDT", "AVAXUSDT", "DOGEUSDT",
    ],
    "cascading_momentum_filter": ["SOLUSDT", "XRPUSDT", "AVAXUSDT", "ETHUSDT"],
    "rsi_bb_mean_reversion": ["ETHUSDT", "BNBUSDT", "DOGEUSDT"],
    "ichimoku_cloud_trend": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
        "XRPUSDT", "AVAXUSDT", "DOGEUSDT",
    ],
}


@dataclass(frozen=True)
class WindowResult:
    """One backtest result for one window/symbol pair."""

    template: str
    symbol: str
    window_start: datetime
    window_end: datetime
    trades: int
    win_rate: float
    profit_factor: float
    sharpe: float
    max_dd_pct: float
    total_return_pct: float


def _build_windows(num_windows: int, window_days: int,
                   end_date: datetime) -> list[tuple[datetime, datetime]]:
    """Build N non-overlapping windows of `window_days` ending at `end_date`.

    Windows are ordered oldest to newest. e.g. for 4 windows of 30 days
    ending 2026-05-27:
      Window 1: 2026-01-27 -> 2026-02-26
      Window 2: 2026-02-26 -> 2026-03-28
      Window 3: 2026-03-28 -> 2026-04-27
      Window 4: 2026-04-27 -> 2026-05-27
    """
    windows: list[tuple[datetime, datetime]] = []
    end = end_date
    for _ in range(num_windows):
        start = end - timedelta(days=window_days)
        windows.append((start, end))
        end = start
    return list(reversed(windows))


async def _fetch(fetcher: MarketDataFetcher, symbol: str,
                 start: datetime, end: datetime) -> Any:
    """Fetch 1H OHLCV for [start, end] from Binance."""
    return await fetcher.fetch_historical_ohlcv(
        symbol=symbol, timeframe="1h",
        start_date=start, end_date=end,
    )


def _run_one(engine: BacktestEngine, template: str, symbol: str,
             params: dict, series: Any, config: BacktestConfig,
             window: tuple[datetime, datetime]) -> WindowResult:
    """Run a single backtest and return the result row."""
    strategy = SimpleNamespace(
        id=f"roll_{template}_{symbol}_{window[0].date()}",
        name=f"{template} {symbol} window={window[0].date()}",
        template_id=template,
        parameters=params,
    )
    result = engine.run_backtest(
        strategy=strategy, series=series, config=config,
    )
    m = result.metrics
    return WindowResult(
        template=template,
        symbol=symbol,
        window_start=window[0],
        window_end=window[1],
        trades=m.total_trades,
        win_rate=m.win_rate_pct,
        profit_factor=m.profit_factor,
        sharpe=m.sharpe_ratio,
        max_dd_pct=m.max_drawdown_pct,
        total_return_pct=m.total_return_pct,
    )


async def run(strategies: list[str], symbols_override: list[str] | None,
              num_windows: int, window_days: int,
              end_date: datetime) -> list[WindowResult]:
    """Run rolling-window backtests across all strategy/symbol/window combos."""
    client = BinanceClient(testnet=False)
    fetcher = MarketDataFetcher(client)
    factory = SignalGeneratorFactory()
    config = BacktestConfig(
        initial_capital=10_000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )
    engine = BacktestEngine(factory)

    windows = _build_windows(num_windows, window_days, end_date)

    # Fetch the longest contiguous range once per symbol, slice locally.
    fetch_start = windows[0][0] - timedelta(days=5)  # padding for indicator warmup
    fetch_end = windows[-1][1]

    all_symbols: set[str] = set()
    for tmpl in strategies:
        syms = symbols_override or STRATEGY_SYMBOLS[tmpl]
        all_symbols.update(syms)

    print(f"\nFetching {len(all_symbols)} symbols x {(fetch_end-fetch_start).days}d ...")
    series_by_sym: dict[str, Any] = {}
    for sym in sorted(all_symbols):
        try:
            s = await _fetch(fetcher, sym, fetch_start, fetch_end)
            series_by_sym[sym] = s
            print(f"  {sym}: {len(s)} bars")
        except Exception as e:
            print(f"  {sym}: FETCH FAILED — {e}")

    # Iterate strategies x symbols x windows.
    results: list[WindowResult] = []
    print()
    print(f"Running backtests: "
          f"{len(strategies)} strategies x "
          f"{len(all_symbols)} symbols x "
          f"{num_windows} windows ...")

    for tmpl in strategies:
        params = STRATEGY_PARAMS[tmpl]
        syms = symbols_override or STRATEGY_SYMBOLS[tmpl]
        for sym in syms:
            full_series = series_by_sym.get(sym)
            if full_series is None:
                continue
            for window in windows:
                # Slice to the window (using the OHLCVSeries duck-typed list)
                start_ts = window[0]
                end_ts = window[1]
                # Naive slice: OHLCVSeries is iterable of OHLCV bars with .timestamp
                sliced = [
                    bar for bar in full_series
                    if start_ts <= bar.timestamp <= end_ts
                ]
                if len(sliced) < 50:
                    continue
                # Reconstruct a series-like via SimpleNamespace; BacktestEngine
                # uses the .bars protocol. Defensive: try to use the original
                # type if it's a list.
                try:
                    series_window = type(full_series)(sliced) if not isinstance(
                        full_series, list
                    ) else sliced
                except TypeError:
                    series_window = sliced
                try:
                    r = _run_one(engine, tmpl, sym, params,
                                 series_window, config, window)
                    results.append(r)
                except Exception as e:
                    logger.warning("backtest_failed",
                                   template=tmpl, symbol=sym,
                                   window_start=str(start_ts), error=str(e))
    return results


def _stability_score(pfs: list[float]) -> tuple[float, float, float]:
    """Return (median PF, min PF, coefficient of variation)."""
    finite = [p for p in pfs if p > 0 and p != float("inf")]
    if not finite:
        return 0.0, 0.0, 0.0
    med = statistics.median(finite)
    mn = min(finite)
    if len(finite) >= 2:
        mu = statistics.mean(finite)
        cv = (statistics.stdev(finite) / mu) if mu else 0.0
    else:
        cv = 0.0
    return med, mn, cv


def print_report(results: list[WindowResult]) -> None:
    """Print per-window detail + per-strategy stability verdict."""
    if not results:
        print("\nNo backtest results.")
        return

    # Per-window detail
    print("\n" + "=" * 110)
    print("ROLLING-WINDOW DETAIL")
    print("=" * 110)
    print(
        f"{'Template':<28} {'Symbol':<10} {'Window':<24} "
        f"{'N':>4} {'WR%':>6} {'PF':>7} {'Sharpe':>7} {'DD%':>6}"
    )
    print("-" * 110)
    for r in sorted(results, key=lambda r: (r.template, r.symbol, r.window_start)):
        win_str = f"{r.window_start.date()}->{r.window_end.date()}"
        print(
            f"{r.template:<28} "
            f"{r.symbol:<10} "
            f"{win_str:<24} "
            f"{r.trades:>4d} "
            f"{r.win_rate:>5.1f}% "
            f"{r.profit_factor:>7.2f} "
            f"{r.sharpe:>7.3f} "
            f"{r.max_dd_pct:>5.1f}%"
        )

    # Per-strategy stability verdict
    print("\n" + "=" * 110)
    print("STABILITY VERDICT")
    print("=" * 110)
    print(
        "Reading: median/min PF across windows + coefficient of variation. "
        "Low CV = stable edge. High CV = noise or overfit."
    )
    print()
    by_template: dict[str, list[WindowResult]] = {}
    for r in results:
        by_template.setdefault(r.template, []).append(r)

    for tmpl, items in by_template.items():
        # Aggregate across symbols (each symbol contributes its windows)
        pfs = [r.profit_factor for r in items if r.trades > 0]
        med, mn, cv = _stability_score(pfs)
        total_trades = sum(r.trades for r in items)
        if med >= 1.35 and cv < 0.30 and mn >= 1.0:
            verdict = "STABLE_EDGE"
        elif med >= 1.20 and cv < 0.50:
            verdict = "PROMISING"
        elif med >= 1.0:
            verdict = "MARGINAL"
        elif total_trades >= 10:
            verdict = "OVERFIT_OR_BROKEN"
        else:
            verdict = "INSUFFICIENT"
        print(
            f"  {tmpl:<32} "
            f"trades={total_trades:>4d} | "
            f"PF med={med:.2f} min={mn:.2f} CV={cv:.2f} | "
            f"-> {verdict}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Rolling-window backtest")
    parser.add_argument(
        "--strategy", type=str, default="bear_trend_follower",
        help="Strategy template_id or 'all' for all current paper strategies",
    )
    parser.add_argument(
        "--symbols", type=str, default=None,
        help="Comma-separated symbols (overrides strategy defaults)",
    )
    parser.add_argument(
        "--windows", type=int, default=4,
        help="Number of windows (default 4)",
    )
    parser.add_argument(
        "--window-days", type=int, default=30,
        help="Days per window (default 30)",
    )
    parser.add_argument(
        "--end", type=str, default=None,
        help="End date YYYY-MM-DD (default: today UTC)",
    )
    args = parser.parse_args()

    if args.strategy == "all":
        strategies = list(STRATEGY_PARAMS.keys())
    else:
        if args.strategy not in STRATEGY_PARAMS:
            valid = ", ".join(STRATEGY_PARAMS.keys())
            raise SystemExit(
                f"Unknown strategy '{args.strategy}'. Valid: {valid}"
            )
        strategies = [args.strategy]

    symbols_override = (
        [s.strip() for s in args.symbols.split(",")] if args.symbols else None
    )
    end_date = (
        datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
        if args.end else datetime.now(timezone.utc)
    )

    results = asyncio.run(run(
        strategies, symbols_override,
        args.windows, args.window_days, end_date,
    ))
    print_report(results)


if __name__ == "__main__":
    main()
