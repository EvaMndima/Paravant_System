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
from src.core.strategy.regime.historical_classifier import (
    HistoricalRegimeClassifier,
    SubRegime,
)
from src.data.market_data import MarketDataFetcher, OHLCVSeries
from src.utils.logging import get_logger, setup_logging

setup_logging(level="WARNING")
logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# Strategy parameter snapshots — kept here so the diagnostic is reproducible
# even if scripts/run_paper_trading.py changes. Update these if the live
# paper config changes.
# -----------------------------------------------------------------------------
STRATEGY_PARAMS: dict[str, dict[str, Any]] = {
    # -------------------------------- BEAR --------------------------------
    "bear_trend_follower": {
        # BTF — RETIRED from live paper (DEC-2026-05-27-007) but KEPT in
        # backtest registry so we can verify per-regime whether the
        # retirement was warranted in every regime or only in CHOPPY_BEAR.
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
    # -------------------------------- BULL --------------------------------
    "macd_pullback": {
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "pullback_ema_period": 21,
        "atr_period": 14,
        "atr_stop_multiplier": 2.5,
        "risk_reward_ratio": 2.0,
        "pullback_tolerance_pct": 0.5,
        "regime_ema_period": 200,
    },
    "bull_trend_pullback": {
        "htf_ema_period": 150,
        "trend_ema_period": 50,
        "rsi_period": 14,
        "rsi_pullback_low": 30.0,
        "rsi_pullback_high": 60.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
    },
    "volatility_regime_breakout": {
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "squeeze_lookback": 20,
        "squeeze_percentile": 20.0,
        "reference_lookback": 100,
        "volume_period": 20,
        "volume_threshold": 1.5,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
        "regime_ema_period": 200,
    },
    "volume_balance_breakout": {
        "balance_period": 15,
        "balance_threshold": 0.60,
        "breakout_lookback": 10,
        "ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 40.0,
        "rsi_max": 70.0,
        "volume_period": 20,
        "volume_threshold": 1.5,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 3.0,
    },
    "stoch_rsi_bull_cross": {
        "rsi_period": 14,
        "stoch_period": 14,
        "smooth_k": 3,
        "smooth_d": 3,
        "stoch_oversold": 20.0,
        "stoch_max": 70.0,
        "stoch_lookback": 5,
        "ema_period": 50,
        "regime_ema_period": 200,
        "rsi_min": 40.0,
        "rsi_max": 70.0,
        "volume_period": 20,
        "volume_threshold": 1.2,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 3.0,
    },
    "heikin_ashi_trend_pulse": {
        "ha_wick_lookback": 7,
        "ha_prior_wick_min": 6,
        "wick_tolerance": 0.05,
        "ema_period": 50,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 75.0,
        "volume_period": 20,
        "volume_threshold": 1.4,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.0,
    },
    "vpt_momentum": {
        "vpt_ema_period": 20,
        "vpt_lookback": 15,
        "vpt_contrib_period": 20,
        "vpt_contrib_threshold": 1.5,
        "ema_period": 50,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 75.0,
        "volume_period": 20,
        "volume_threshold": 1.3,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
    },
    "realized_vol_compression_breakout": {
        "hv_short_period": 20,
        "hv_medium_period": 60,
        "hv_compression_ratio": 0.65,
        "hv_min_compression_bars": 3,
        "breakout_lookback": 20,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 78.0,
        "volume_period": 20,
        "volume_threshold": 1.3,
        "atr_period": 14,
        "atr_stop_multiplier": 2.5,
        "risk_reward_ratio": 2.5,
    },
    # ----------------------------- ALL-REGIME -----------------------------
    "ichimoku_cloud_trend": {
        "tenkan_period": 20,
        "kijun_period": 60,
        "senkou_b_period": 120,
        "displacement": 30,
        "atr_period": 14,
        "volume_period": 20,
        "volume_threshold": 1.3,
    },
    # Forward hypothesis loop -- H-2026-06-002 (TRENDING_BULL breakout-continuation).
    # donchian_atr is an EXISTING production template (already in
    # SignalGeneratorFactory) that was never DSR-screened; registered here for the
    # regime-DSR screen via the research-side eval registry (DEC-2026-06-04-019).
    # Params are the entry's pre-registered defaults in research/hypotheses/ledger.yaml.
    "donchian_atr": {
        "donchian_period": 20,
        "atr_period": 14,
        "atr_threshold": 0.005,
        "atr_stop_multiplier": 2.0,
        "volume_ma_period": 20,
        "volume_multiplier": 1.2,
        "ema_regime_period": 200,
    },
}

STRATEGY_SYMBOLS: dict[str, list[str]] = {
    # Bear
    "bear_trend_follower": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
        "XRPUSDT", "AVAXUSDT", "DOGEUSDT",
    ],
    "cascading_momentum_filter": ["SOLUSDT", "XRPUSDT", "AVAXUSDT", "ETHUSDT"],
    "rsi_bb_mean_reversion": ["ETHUSDT", "BNBUSDT", "DOGEUSDT"],
    # Bull
    "macd_pullback": ["DOGEUSDT", "AVAXUSDT"],
    "bull_trend_pullback": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "DOGEUSDT"],
    "volatility_regime_breakout": ["BTCUSDT"],
    "volume_balance_breakout": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "stoch_rsi_bull_cross": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "heikin_ashi_trend_pulse": ["BTCUSDT", "BNBUSDT", "AVAXUSDT"],
    "vpt_momentum": ["BTCUSDT"],
    "realized_vol_compression_breakout": ["AVAXUSDT"],
    # All-regime
    "ichimoku_cloud_trend": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
        "XRPUSDT", "AVAXUSDT", "DOGEUSDT",
    ],
    # Forward hypothesis loop -- H-2026-06-002. Multi-symbol (4 liquid majors) is
    # the breadth correction the retired VRB lacked (it was BTC-only).
    "donchian_atr": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
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
    regime: SubRegime = SubRegime.UNKNOWN


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
             window: tuple[datetime, datetime],
             regime: SubRegime) -> WindowResult:
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
        regime=regime,
    )


async def run(strategies: list[str], symbols_override: list[str] | None,
              num_windows: int, window_days: int,
              end_date: datetime, market: str = "spot") -> list[WindowResult]:
    """Run rolling-window backtests across all strategy/symbol/window combos.

    Args:
        market: "spot" = long-only, no funding (what Binance spot can execute).
            "futures" = long+short with a conservative perpetual funding drag.
            Decision: DEC-2026-05-28-001.
    """
    client = BinanceClient(testnet=False)
    fetcher = MarketDataFetcher(client)
    factory = SignalGeneratorFactory()
    if market == "futures":
        config = BacktestConfig(
            initial_capital=10_000.0,
            commission_rate=0.001,
            slippage_rate=0.0005,
            allow_shorts=True,
            funding_rate_per_8h=0.0001,  # conservative ~0.03%/day perp funding
        )
    else:  # spot
        config = BacktestConfig(
            initial_capital=10_000.0,
            commission_rate=0.001,
            slippage_rate=0.0005,
            allow_shorts=False,
            funding_rate_per_8h=0.0,
        )
    print(f"Market mode: {market} "
          f"(allow_shorts={config.allow_shorts}, "
          f"funding/8h={config.funding_rate_per_8h})")
    engine = BacktestEngine(factory)

    windows = _build_windows(num_windows, window_days, end_date)

    # Fetch the longest contiguous range once per symbol, slice locally.
    # We need ~35d of warmup BEFORE windows[0][0] so indicators can fire
    # within that earliest window (BTF needs 4H EMA-200 = ~800 1H bars).
    fetch_start = windows[0][0] - timedelta(days=40)
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

    # Also fetch BTC daily so we can classify each window's macro regime.
    # Decision: DEC-2026-05-27-008 — BTC daily is the universal regime anchor.
    print("\nFetching BTC daily for regime classification ...")
    try:
        btc_daily = await fetcher.fetch_historical_ohlcv(
            symbol="BTCUSDT",
            timeframe="1d",
            start_date=fetch_start - timedelta(days=250),  # ema_slow warmup
            end_date=fetch_end,
        )
        print(f"  BTCUSDT 1d: {len(btc_daily)} bars")
        classifier = HistoricalRegimeClassifier()
        regime_labels = classifier.classify_series(btc_daily)
        # Build a timestamp -> regime lookup for window dominant-regime lookups.
        regime_by_ts = {
            bar.timestamp: regime
            for bar, regime in zip(btc_daily.candles, regime_labels)
        }
    except Exception as e:
        print(f"  BTC daily FETCH FAILED — {e}. Continuing without regime tags.")
        btc_daily = None
        regime_by_ts = {}

    def _window_regime(start: datetime, end: datetime) -> SubRegime:
        """Mode regime over the daily bars falling within [start, end]."""
        if not regime_by_ts:
            return SubRegime.UNKNOWN
        in_window = [
            regime for ts, regime in regime_by_ts.items()
            if start <= ts <= end
            and regime not in (SubRegime.UNKNOWN, SubRegime.TRANSITIONAL)
        ]
        if not in_window:
            return SubRegime.UNKNOWN
        counts: dict[SubRegime, int] = {}
        for r in in_window:
            counts[r] = counts.get(r, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

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
                start_ts = window[0]
                end_ts = window[1]
                # Each window needs ~34 days of warmup data BEFORE its
                # nominal start so indicators can fire. We slice from
                # (start_ts - 35d) to end_ts and then run the backtest on
                # that span. Trades during the warmup prefix will count
                # toward the window's metrics (acceptable: it gives us
                # signal density similar to live trading).
                warmup_start = start_ts - timedelta(days=35)
                sliced_candles = [
                    bar for bar in full_series.candles
                    if warmup_start <= bar.timestamp <= end_ts
                ]
                if len(sliced_candles) < 850:  # need ~812 for BTF warmup
                    logger.warning(
                        "window_too_short",
                        template=tmpl, symbol=sym,
                        bars=len(sliced_candles),
                        window_start=str(start_ts),
                    )
                    continue
                series_window = OHLCVSeries(
                    candles=sliced_candles,
                    symbol=full_series.symbol,
                    timeframe=full_series.timeframe,
                )
                try:
                    window_regime = _window_regime(start_ts, end_ts)
                    r = _run_one(engine, tmpl, sym, params,
                                 series_window, config, window, window_regime)
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
    """Print per-window detail + per-strategy stability + per-regime breakdown."""
    if not results:
        print("\nNo backtest results.")
        return

    # Per-window detail (now with regime column)
    print("\n" + "=" * 125)
    print("ROLLING-WINDOW DETAIL")
    print("=" * 125)
    print(
        f"{'Template':<28} {'Symbol':<10} {'Window':<24} "
        f"{'Regime':<16} {'N':>4} {'WR%':>6} {'PF':>7} {'Sharpe':>7} {'DD%':>6}"
    )
    print("-" * 125)
    for r in sorted(results, key=lambda r: (r.template, r.symbol, r.window_start)):
        win_str = f"{r.window_start.date()}->{r.window_end.date()}"
        print(
            f"{r.template:<28} "
            f"{r.symbol:<10} "
            f"{win_str:<24} "
            f"{r.regime.value:<16} "
            f"{r.trades:>4d} "
            f"{r.win_rate:>5.1f}% "
            f"{r.profit_factor:>7.2f} "
            f"{r.sharpe:>7.3f} "
            f"{r.max_dd_pct:>5.1f}%"
        )

    # Per-strategy stability verdict (unchanged)
    print("\n" + "=" * 125)
    print("OVERALL STABILITY VERDICT (across all regimes)")
    print("=" * 125)
    print(
        "Reading: median/min PF across windows + coefficient of variation. "
        "Low CV = stable edge across regimes. High CV = noise OR regime-specific edge."
    )
    print()
    by_template: dict[str, list[WindowResult]] = {}
    for r in results:
        by_template.setdefault(r.template, []).append(r)

    for tmpl, items in by_template.items():
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

    # Per-regime breakdown — THE KEY NEW DIAGNOSTIC.
    # A strategy with OVERFIT verdict overall but STABLE in one regime is
    # actually a REGIME-SPECIFIC edge, not overfit. This is what would
    # have caught BTF as "edge in TRENDING_BEAR, broken in CHOPPY_BEAR"
    # rather than "broken everywhere."
    print("\n" + "=" * 125)
    print("PER-REGIME BREAKDOWN (the key diagnostic)")
    print("=" * 125)
    print(
        "If a strategy has STABLE_EDGE in one regime but POOR in another, it's "
        "a REGIME-SPECIFIC edge — valid IF deployed only in that regime.\n"
        "If a strategy is POOR in its declared/expected regime, it has no real edge."
    )
    print()
    print(
        f"{'Template':<32} {'Regime':<16} "
        f"{'Windows':>8} {'Trades':>7} {'PF med':>7} {'PF min':>7} {'CV':>5} {'Verdict':>20}"
    )
    print("-" * 125)
    for tmpl, items in by_template.items():
        by_regime: dict[SubRegime, list[WindowResult]] = {}
        for r in items:
            by_regime.setdefault(r.regime, []).append(r)
        for regime, reg_items in sorted(
            by_regime.items(), key=lambda kv: kv[0].value,
        ):
            pfs = [r.profit_factor for r in reg_items if r.trades > 0]
            med, mn, cv = _stability_score(pfs)
            total_trades = sum(r.trades for r in reg_items)
            n_windows = len(reg_items)
            if n_windows < 2:
                verdict = "INSUFFICIENT_WINDOWS"
            elif med >= 1.35 and mn >= 1.0:
                verdict = "STABLE_EDGE_IN_REGIME"
            elif med >= 1.20:
                verdict = "PROMISING_IN_REGIME"
            elif med >= 1.0:
                verdict = "MARGINAL_IN_REGIME"
            elif total_trades >= 10:
                verdict = "POOR_IN_REGIME"
            else:
                verdict = "INSUFFICIENT"
            print(
                f"  {tmpl:<30} {regime.value:<16} "
                f"{n_windows:>8d} {total_trades:>7d} "
                f"{med:>7.2f} {mn:>7.2f} {cv:>5.2f} "
                f"{verdict:>20s}"
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
        "--window-days", type=int, default=60,
        help=(
            "Days per window (default 60). Must be large enough to "
            "include indicator warmup — BTF needs ~34 days (4H EMA(200) = "
            "~800 1H bars). 60 days gives 1440 bars per window: ~812 "
            "warmup + ~628 active trading bars."
        ),
    )
    parser.add_argument(
        "--end", type=str, default=None,
        help="End date YYYY-MM-DD (default: today UTC)",
    )
    parser.add_argument(
        "--market", type=str, default="spot", choices=["spot", "futures"],
        help=(
            "spot = long-only, no funding (what Binance spot can execute). "
            "futures = long+short with conservative perp funding drag. "
            "Default spot. (DEC-2026-05-28-001)"
        ),
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
        args.windows, args.window_days, end_date, args.market,
    ))
    print_report(results)


if __name__ == "__main__":
    main()
