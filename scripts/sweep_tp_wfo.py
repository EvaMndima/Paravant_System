#!/usr/bin/env python
"""Take-Profit Walk-Forward Optimizer -- PARAVANT

Professional quant methodology:

  Walk-Forward Optimization (WFO):
    3 rolling windows, each 90d IS + 30d OOS (offset by 30d).
    IS = in-sample window for parameter discovery.
    OOS = out-of-sample window for generalization validation.
    WFO score = average OOS Profit Factor across windows with >= 3 trades.

  Phase 1 -- 1D TP Sweep:
    Varies risk_reward_ratio (1.0 -> 4.0) with stop held at current value.
    Applied to all 8 configurable-TP promoted strategies (18 symbol pairs).

  Phase 2 -- 2D Joint Surface:
    Jointly varies atr_stop_multiplier AND risk_reward_ratio.
    Only for pairs where Phase 1 WFO avg OOS PF >= 1.5.
    Identifies the robust risk/reward regime, not just the TP peak.

  Non-configurable strategies (BTF, CMF, RSI_BB, ICVP):
    These are reported separately with recommendations for improvement.
    - BTF:    TP at Keltner middle (structural, correct as-is)
    - CMF:    Hardcoded 2.5x ATR TP => recommend adding risk_reward_ratio param
    - RSI_BB: BB middle band TP + RSI exits (structural, correct for mean-reversion)
    - ICVP:   TP = stop distance (1:1 R:R) => CRITICAL: should add separate rr param

Usage:
    PYTHONPATH=. .venv/Scripts/python scripts/sweep_tp_wfo.py
    PYTHONPATH=. .venv/Scripts/python scripts/sweep_tp_wfo.py --phase 1
    PYTHONPATH=. .venv/Scripts/python scripts/sweep_tp_wfo.py --phase 2
    PYTHONPATH=. .venv/Scripts/python scripts/sweep_tp_wfo.py --strategy SRC
    PYTHONPATH=. .venv/Scripts/python scripts/sweep_tp_wfo.py --strategy BTP --symbol BTCUSDT

Requires:
    BINANCE_TESTNET=false in .env (mainnet data)
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from src.brokers.binance.client import BinanceClient
from src.core.strategy.backtest import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig, TradeRecord
from src.core.strategy.backtest.validator import SUPERVISED_THRESHOLDS
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher, OHLCVSeries
from src.utils.logging import get_logger, setup_logging

setup_logging(level="WARNING")
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# WFO configuration
# ---------------------------------------------------------------------------
TOTAL_DAYS = 180          # total history to fetch
IS_DAYS    = 90           # in-sample window length (days)
OOS_DAYS   = 30           # out-of-sample window length (days)
BARS_PER_DAY = 24         # 1H timeframe
MIN_OOS_TRADES = 3        # windows below this are "sparse" (excluded from WFO avg)

# Window definitions: (is_start_day, is_end_day, oos_start_day, oos_end_day)
WFO_WINDOWS = [
    (0,   90,  90,  120),  # W1
    (30, 120, 120,  150),  # W2
    (60, 150, 150,  180),  # W3
]

# ---------------------------------------------------------------------------
# Phase 1 -- 1D TP grid
# ---------------------------------------------------------------------------
RR_GRID_1D: list[float] = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

# ---------------------------------------------------------------------------
# Phase 2 -- 2D joint surface (stop x TP)
# Only for strategy-symbol pairs where Phase 1 WFO avg OOS PF >= threshold
# ---------------------------------------------------------------------------
STOP_GRID_2D: list[float]    = [1.5, 2.0, 2.5, 3.0]
RR_GRID_2D: list[float]      = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
PHASE2_QUALIFY_PF: float     = 1.5   # minimum Phase 1 WFO avg OOS PF

# ---------------------------------------------------------------------------
# Strategy sweep targets -- 8 promoted strategies with configurable rr_ratio
# ---------------------------------------------------------------------------
SWEEP_TARGETS: dict[str, dict[str, Any]] = {
    "MACD_PB": {
        "template_id":  "macd_pullback",
        "symbols":      ["DOGEUSDT", "AVAXUSDT"],
        "current_rr":   2.0,
        "current_stop": 2.5,
        "base_params":  {
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "pullback_ema_period": 21, "atr_period": 14,
            "pullback_tolerance_pct": 0.5, "regime_ema_period": 200,
        },
    },
    "BTP": {
        "template_id":  "bull_trend_pullback",
        "symbols":      ["BTCUSDT", "ETHUSDT", "BNBUSDT", "DOGEUSDT"],
        "current_rr":   2.5,
        "current_stop": 2.0,
        "base_params":  {
            "htf_ema_period": 150, "trend_ema_period": 50,
            "rsi_period": 14, "rsi_pullback_low": 30.0, "rsi_pullback_high": 60.0,
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9, "atr_period": 14,
        },
    },
    "VRB": {
        "template_id":  "volatility_regime_breakout",
        "symbols":      ["BTCUSDT"],
        "current_rr":   2.5,
        "current_stop": 2.0,
        "base_params":  {
            "bb_period": 20, "bb_std_dev": 2.0, "squeeze_lookback": 20,
            "squeeze_percentile": 20.0, "reference_lookback": 100,
            "volume_period": 20, "volume_threshold": 1.5, "atr_period": 14,
            "regime_ema_period": 200,
        },
    },
    "VBB": {
        "template_id":  "volume_balance_breakout",
        "symbols":      ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "current_rr":   3.0,
        "current_stop": 2.0,
        "base_params":  {
            "balance_period": 15, "balance_threshold": 0.60,
            "breakout_lookback": 10, "ema_period": 200, "rsi_period": 14,
            "rsi_min": 40.0, "rsi_max": 70.0, "volume_period": 20,
            "volume_threshold": 1.5, "atr_period": 14,
        },
    },
    "SRC": {
        "template_id":  "stoch_rsi_bull_cross",
        "symbols":      ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "current_rr":   3.0,
        "current_stop": 2.0,
        "base_params":  {
            "rsi_period": 14, "stoch_period": 14, "smooth_k": 3, "smooth_d": 3,
            "stoch_oversold": 20.0, "stoch_max": 70.0, "stoch_lookback": 5,
            "ema_period": 50, "regime_ema_period": 200,
            "rsi_min": 40.0, "rsi_max": 70.0,
            "volume_period": 20, "volume_threshold": 1.2, "atr_period": 14,
        },
    },
    "HATP": {
        "template_id":  "heikin_ashi_trend_pulse",
        "symbols":      ["BTCUSDT", "BNBUSDT", "AVAXUSDT"],
        "current_rr":   2.0,
        "current_stop": 2.0,
        "base_params":  {
            "ha_wick_lookback": 7, "ha_prior_wick_min": 6, "wick_tolerance": 0.05,
            "ema_period": 50, "regime_ema_period": 200,
            "rsi_period": 14, "rsi_min": 50.0, "rsi_max": 75.0,
            "volume_period": 20, "volume_threshold": 1.4, "atr_period": 14,
        },
    },
    "VPT": {
        "template_id":  "vpt_momentum",
        "symbols":      ["BTCUSDT"],
        "current_rr":   2.5,
        "current_stop": 2.0,
        "base_params":  {
            "vpt_ema_period": 20, "vpt_lookback": 15, "vpt_contrib_period": 20,
            "vpt_contrib_threshold": 1.5, "ema_period": 50, "regime_ema_period": 200,
            "rsi_period": 14, "rsi_min": 50.0, "rsi_max": 75.0,
            "volume_period": 20, "volume_threshold": 1.3, "atr_period": 14,
        },
    },
    "RVCB": {
        "template_id":  "realized_vol_compression_breakout",
        "symbols":      ["AVAXUSDT"],
        "current_rr":   2.5,
        "current_stop": 2.0,
        "base_params":  {
            "hv_short_period": 20, "hv_medium_period": 60,
            "hv_compression_ratio": 0.65, "hv_min_compression_bars": 3,
            "breakout_lookback": 20, "regime_ema_period": 200,
            "rsi_period": 14, "rsi_min": 50.0, "rsi_max": 78.0,
            "volume_period": 20, "volume_threshold": 1.3, "atr_period": 14,
        },
    },
}

# Strategies that cannot be TP-optimized via rr_ratio (explanation notes)
NON_CONFIGURABLE_NOTES = [
    ("BTF",    "Keltner middle-band TP (structural exit) -- no rr_ratio param -- correct as-is"),
    ("CMF",    "CRITICAL: hardcoded TP = price + 2.5*ATR -- add risk_reward_ratio param to generator"),
    ("RSI_BB", "BB middle-band TP + RSI signal exit (mean-reversion target) -- structural, correct"),
    ("ICVP",   "CRITICAL: TP = stop distance (1:1 R:R, same multiplier for both) "
               "-- add separate risk_reward_ratio param; 1:1 requires >50% WR to be profitable"),
]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

async def fetch_all_symbols(
    strategy_keys: list[str],
    days: int,
) -> dict[str, OHLCVSeries]:
    """Fetch 1H OHLCV data for all unique symbols across selected strategies."""
    symbols_needed: list[str] = []
    for key in strategy_keys:
        for sym in SWEEP_TARGETS[key]["symbols"]:
            if sym not in symbols_needed:
                symbols_needed.append(sym)

    client  = BinanceClient(testnet=False)
    fetcher = MarketDataFetcher(client)
    end_date   = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    data: dict[str, OHLCVSeries] = {}
    for sym in symbols_needed:
        print(f"  Fetching {sym}...", end=" ", flush=True)
        try:
            series = await fetcher.fetch_historical_ohlcv(
                symbol=sym, timeframe="1h",
                start_date=start_date, end_date=end_date,
            )
            print(f"{len(series)} bars")
            data[sym] = series
        except Exception as exc:
            print(f"FAILED: {exc}")
    return data


def slice_series(
    series: OHLCVSeries,
    start_bar: int,
    end_bar: int,
) -> OHLCVSeries:
    """Return OHLCVSeries for candles[start_bar:end_bar]."""
    return OHLCVSeries(
        series.candles[start_bar:end_bar],
        series.symbol,
        series.timeframe,
    )


# ---------------------------------------------------------------------------
# Backtest runner
# ---------------------------------------------------------------------------

def run_slice(
    template_id: str,
    params: dict[str, Any],
    series: OHLCVSeries,
    start_bar: int,
    end_bar: int,
    factory: SignalGeneratorFactory,
    config: BacktestConfig,
    run_id: str,
) -> dict[str, Any]:
    """Run backtest on series[start_bar:end_bar], return metrics + trade_log."""
    sliced = slice_series(series, start_bar, end_bar)
    strategy = SimpleNamespace(
        id=run_id,
        name=run_id,
        template_id=template_id,
        parameters=params,
    )
    engine = BacktestEngine(factory)
    try:
        result = engine.run_backtest(
            strategy=strategy,
            series=sliced,
            config=config,
            thresholds=SUPERVISED_THRESHOLDS,
        )
        m = result.metrics
        return {
            "ok":        True,
            "trades":    m.total_trades,
            "win_rate":  m.win_rate_pct,
            "pf":        m.profit_factor,
            "sharpe":    m.sharpe_ratio,
            "exp":       m.expectancy,
            "max_dd":    m.max_drawdown_pct,
            "passed":    result.passed_validation,
            "trade_log": result.trade_log,
        }
    except Exception as exc:
        return {
            "ok": False, "error": str(exc),
            "trades": 0, "win_rate": 0.0, "pf": 0.0, "sharpe": 0.0,
            "exp": 0.0, "max_dd": 0.0, "passed": False, "trade_log": [],
        }


# ---------------------------------------------------------------------------
# OOS metrics from filtered trade log
# ---------------------------------------------------------------------------

def oos_metrics(
    trade_log: list[TradeRecord],
    oos_start_date: datetime,
) -> dict[str, Any]:
    """Compute metrics for trades with entry_time >= oos_start_date.

    The backtest is run on IS+OOS combined data (IS acts as warmup for
    indicator convergence). Only trades entering after oos_start_date
    count as OOS results.
    """
    oos = [t for t in trade_log if t.entry_time >= oos_start_date]
    n   = len(oos)

    if n == 0:
        return {"trades": 0, "win_rate": 0.0, "pf": 0.0,
                "exp": 0.0, "kelly": 0.0, "sparse": True}

    pnls    = [t.realized_pnl for t in oos]
    winners = [p for p in pnls if p > 0]
    losers  = [p for p in pnls if p < 0]

    win_rate = len(winners) / n * 100
    gross_profit = sum(winners)
    gross_loss   = abs(sum(losers)) if losers else 0.0

    if gross_loss > 0:
        pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pf = 9.99  # no losers -- cap at 9.99 for display
    else:
        pf = 0.0

    exp = sum(pnls) / n

    # Kelly fraction: edge / payout_ratio
    kelly = 0.0
    if winners and losers:
        avg_win  = sum(winners) / len(winners)
        avg_loss = abs(sum(losers)) / len(losers)
        payout   = avg_win / avg_loss if avg_loss > 0 else 9.9
        w        = len(winners) / n
        kelly    = max(-1.0, min(1.0, w - (1 - w) / payout))

    return {
        "trades":   n,
        "win_rate": win_rate,
        "pf":       pf,
        "exp":      exp,
        "kelly":    kelly,
        "sparse":   n < MIN_OOS_TRADES,
    }


def wfo_avg_pf(oos_window_metrics: list[dict]) -> float:
    """Mean OOS PF across non-sparse windows."""
    valid = [m for m in oos_window_metrics if not m.get("sparse", True)]
    if not valid:
        return 0.0
    return sum(m["pf"] for m in valid) / len(valid)


def robustness_plateau(
    rr_levels: list[float],
    wfo_scores: list[float],
    threshold_pct: float = 0.80,
) -> tuple[float, float]:
    """Return (low, high) plateau bounds where WFO score >= threshold_pct * peak."""
    if not wfo_scores or max(wfo_scores) == 0:
        return (0.0, 0.0)
    peak = max(wfo_scores)
    cutoff = peak * threshold_pct
    plateau_rr = [rr for rr, score in zip(rr_levels, wfo_scores) if score >= cutoff]
    if not plateau_rr:
        return (0.0, 0.0)
    return (min(plateau_rr), max(plateau_rr))


# ---------------------------------------------------------------------------
# Phase 1: 1D TP sweep
# ---------------------------------------------------------------------------

def run_phase1(
    strategy_keys: list[str],
    data: dict[str, OHLCVSeries],
    factory: SignalGeneratorFactory,
    config: BacktestConfig,
) -> dict[str, dict]:
    """Run Phase 1 WFO TP sweep for selected strategies.

    Returns a nested dict: phase1_results[strategy_label][symbol] = {
        rr: float -> {
            is_metrics: dict,
            oos_by_window: list[dict],  # 3 windows
            wfo_avg_pf: float,
        },
        recommendation: str,
        optimal_rr: float,
        plateau: tuple[float, float],
    }
    """
    phase1_results: dict[str, dict] = {}

    for label in strategy_keys:
        cfg = SWEEP_TARGETS[label]
        template_id = cfg["template_id"]
        current_rr  = cfg["current_rr"]
        current_stop = cfg["current_stop"]
        base_params  = cfg["base_params"]
        phase1_results[label] = {}

        print(f"\n{'='*82}")
        print(f"  PHASE 1 -- {label}  ({template_id})")
        print(f"  Current: RR={current_rr}  Stop={current_stop}x ATR")
        print(f"{'='*82}")

        for symbol in cfg["symbols"]:
            if symbol not in data:
                print(f"  {symbol}: no data -- skipped")
                continue

            series = data[symbol]
            n_bars = len(series)
            needed = TOTAL_DAYS * BARS_PER_DAY

            if n_bars < needed * 0.9:
                print(f"  {symbol}: only {n_bars} bars (need ~{needed}) -- skipped")
                continue

            print(f"\n  {symbol}  ({n_bars} bars available)")

            sym_results: dict[float, dict] = {}

            # --- IS run: use W1 IS window as representative ---
            w1_is_start = WFO_WINDOWS[0][0] * BARS_PER_DAY
            w1_is_end   = WFO_WINDOWS[0][1] * BARS_PER_DAY

            # Header
            print(f"  {'RR':>5}  {'IS_T':>5}  {'IS_PF':>6}  {'IS_Shr':>7}  "
                  f"OOS_W1(T/PF)  OOS_W2(T/PF)  OOS_W3(T/PF)  WFO_PF  Note")
            print(f"  {'-'*82}")

            for rr in RR_GRID_1D:
                params = {
                    **base_params,
                    "atr_stop_multiplier": current_stop,
                    "risk_reward_ratio":   rr,
                }

                # IS backtest (W1 IS window)
                is_result = run_slice(
                    template_id, params, series,
                    w1_is_start, w1_is_end,
                    factory, config,
                    f"tp1d_{label}_{symbol}_is_rr{rr:.1f}",
                )

                # OOS backtests -- run IS+OOS combined, filter trades by oos_start
                oos_window_metrics: list[dict] = []
                for win_idx, (is_s, is_e, oos_s, oos_e) in enumerate(WFO_WINDOWS):
                    # Need at least oos_end bars
                    required_bars = oos_e * BARS_PER_DAY
                    if n_bars < required_bars:
                        oos_window_metrics.append({"trades": 0, "pf": 0.0,
                                                   "sparse": True, "win_rate": 0.0,
                                                   "exp": 0.0, "kelly": 0.0})
                        continue

                    combined_start = is_s * BARS_PER_DAY
                    combined_end   = oos_e * BARS_PER_DAY
                    oos_start_dt   = series.candles[oos_s * BARS_PER_DAY].timestamp

                    combined_result = run_slice(
                        template_id, params, series,
                        combined_start, combined_end,
                        factory, config,
                        f"tp1d_{label}_{symbol}_w{win_idx+1}_rr{rr:.1f}",
                    )
                    if not combined_result["ok"]:
                        oos_window_metrics.append({"trades": 0, "pf": 0.0,
                                                   "sparse": True, "win_rate": 0.0,
                                                   "exp": 0.0, "kelly": 0.0})
                        continue

                    om = oos_metrics(combined_result["trade_log"], oos_start_dt)
                    oos_window_metrics.append(om)

                avg_pf  = wfo_avg_pf(oos_window_metrics)
                is_ok   = is_result.get("ok", False)
                is_t    = is_result["trades"] if is_ok else 0
                is_pf   = is_result["pf"]     if is_ok else 0.0
                is_shr  = is_result["sharpe"] if is_ok else 0.0

                sym_results[rr] = {
                    "is_metrics":      is_result,
                    "oos_by_window":   oos_window_metrics,
                    "wfo_avg_pf":      avg_pf,
                }

                # Build OOS summary strings
                oos_cols = []
                for om in oos_window_metrics:
                    if om["sparse"] or om["trades"] == 0:
                        oos_cols.append(f"{'<3':>3}/{'---':>5}")
                    else:
                        oos_cols.append(f"{om['trades']:>3}/{om['pf']:>5.2f}")

                note = ""
                if abs(rr - current_rr) < 0.01:
                    note = "CURRENT"
                elif avg_pf == 0:
                    note = "sparse"

                marker = "*" if abs(rr - current_rr) < 0.01 else " "
                print(
                    f"  {marker}{rr:>4.1f}  {is_t:>5d}  {is_pf:>6.2f}  {is_shr:>7.3f}  "
                    f"{'  '.join(oos_cols)}  {avg_pf:>6.2f}  {note}"
                )

            # Compute recommendation for this symbol
            wfo_scores = [sym_results[rr]["wfo_avg_pf"] for rr in RR_GRID_1D]
            peak_score = max(wfo_scores) if wfo_scores else 0.0
            plateau    = robustness_plateau(RR_GRID_1D, wfo_scores)

            optimal_rr = RR_GRID_1D[wfo_scores.index(peak_score)] if peak_score > 0 else current_rr
            current_score = sym_results.get(current_rr, {}).get("wfo_avg_pf", 0.0)
            gain   = peak_score - current_score

            rec_parts = [f"Optimal RR={optimal_rr:.1f}  (current={current_rr:.1f})"]
            if plateau[0] > 0:
                rec_parts.append(f"Plateau {plateau[0]:.1f}-{plateau[1]:.1f}")
            if gain > 0.05:
                rec_parts.append(f"WFO PF gain +{gain:.2f} => UPDATE RECOMMENDED")
            elif gain <= 0.05 and current_rr == optimal_rr:
                rec_parts.append("Current RR is optimal -- no change needed")
            else:
                rec_parts.append(f"WFO PF gain +{gain:.2f} => marginal, within plateau")

            print(f"\n  RECOMMENDATION [{symbol}]: {' | '.join(rec_parts)}")

            phase1_results[label][symbol] = {
                "rr_results": sym_results,
                "optimal_rr": optimal_rr,
                "wfo_peak":   peak_score,
                "plateau":    plateau,
                "current_rr": current_rr,
            }

    return phase1_results


# ---------------------------------------------------------------------------
# Phase 2: 2D joint surface (stop x TP)
# ---------------------------------------------------------------------------

def run_phase2(
    phase1_results: dict[str, dict],
    data: dict[str, OHLCVSeries],
    factory: SignalGeneratorFactory,
    config: BacktestConfig,
) -> None:
    """Run Phase 2 2D joint surface for qualifying strategy-symbol pairs.

    Qualifies pairs where Phase 1 WFO avg OOS PF >= PHASE2_QUALIFY_PF.
    Runs stop x TP grid on W1 IS window and W1 OOS window.
    """
    qualifying: list[tuple[str, str]] = []
    for label, sym_data in phase1_results.items():
        for symbol, results in sym_data.items():
            if results.get("wfo_peak", 0.0) >= PHASE2_QUALIFY_PF:
                qualifying.append((label, symbol))

    if not qualifying:
        print(f"\nPhase 2: No qualifying pairs (threshold: WFO PF >= {PHASE2_QUALIFY_PF})")
        return

    print(f"\n{'='*82}")
    print("  PHASE 2 -- 2D Joint Surface (Stop x TP)")
    print(f"  Qualifying pairs (WFO PF >= {PHASE2_QUALIFY_PF}): "
          f"{', '.join(f'{label}/{symbol}' for label, symbol in qualifying)}")
    print(f"{'='*82}")

    # W1 IS and OOS windows for surface analysis
    w1_is_s,  w1_is_e,  w1_oos_s, w1_oos_e  = WFO_WINDOWS[0]
    is_start  = w1_is_s  * BARS_PER_DAY
    is_end    = w1_is_e  * BARS_PER_DAY
    oos_combined_end = w1_oos_e * BARS_PER_DAY

    for label, symbol in qualifying:
        cfg         = SWEEP_TARGETS[label]
        template_id = cfg["template_id"]
        base_params = cfg["base_params"]
        current_rr  = cfg["current_rr"]
        current_stop = cfg["current_stop"]

        if symbol not in data:
            continue

        series = data[symbol]
        n_bars = len(series)
        if n_bars < oos_combined_end:
            print(f"\n  {label}/{symbol}: insufficient bars for Phase 2 -- skipped")
            continue

        oos_start_dt = series.candles[w1_oos_s * BARS_PER_DAY].timestamp

        print(f"\n  {label} -- {symbol}  [2D surface: {len(STOP_GRID_2D)} stops x {len(RR_GRID_2D)} RR]")
        print(f"  {'Stop':>5}  {'RR':>5}  {'IS_T':>5}  {'IS_PF':>6}  {'OOS_T':>6}  {'OOS_PF':>7}  {'OOS_WR':>7}  {'Kelly':>7}  Note")
        print(f"  {'-'*80}")

        best_oos_pf  = -1.0
        best_combo: tuple[float, float] = (current_stop, current_rr)
        surface: list[dict] = []

        for stop in STOP_GRID_2D:
            for rr in RR_GRID_2D:
                params = {
                    **base_params,
                    "atr_stop_multiplier": stop,
                    "risk_reward_ratio":   rr,
                }

                # IS run
                is_r = run_slice(
                    template_id, params, series,
                    is_start, is_end,
                    factory, config,
                    f"tp2d_{label}_{symbol}_s{stop}_r{rr}",
                )

                # OOS run (IS+OOS combined for warmup)
                oos_r = run_slice(
                    template_id, params, series,
                    is_start, oos_combined_end,
                    factory, config,
                    f"tp2d_oos_{label}_{symbol}_s{stop}_r{rr}",
                )

                om = oos_metrics(oos_r.get("trade_log", []), oos_start_dt) if oos_r["ok"] else {
                    "trades": 0, "pf": 0.0, "win_rate": 0.0, "kelly": 0.0, "sparse": True
                }

                row = {
                    "stop": stop, "rr": rr,
                    "is_trades": is_r["trades"] if is_r["ok"] else 0,
                    "is_pf":     is_r["pf"]     if is_r["ok"] else 0.0,
                    "oos_trades": om["trades"],
                    "oos_pf":     om["pf"],
                    "oos_wr":     om["win_rate"],
                    "kelly":      om["kelly"],
                    "sparse":     om["sparse"],
                }
                surface.append(row)

                if not om["sparse"] and om["pf"] > best_oos_pf:
                    best_oos_pf = om["pf"]
                    best_combo  = (stop, rr)

                note = ""
                if abs(stop - current_stop) < 0.01 and abs(rr - current_rr) < 0.01:
                    note = "CURRENT"
                elif not om["sparse"] and om["pf"] == best_oos_pf:
                    note = "BEST_OOS"

                oos_pf_str = f"{om['pf']:>7.2f}" if not om["sparse"] else f"{'sparse':>7}"
                print(
                    f"  {stop:>5.1f}  {rr:>5.1f}  "
                    f"{is_r['trades']:>5d}  {is_r['pf']:>6.2f}  "
                    f"{om['trades']:>6d}  {oos_pf_str}  "
                    f"{om['win_rate']:>6.1f}%  {om['kelly']:>7.3f}  {note}"
                )

        print(f"\n  2D OPTIMAL [{symbol}]: Stop={best_combo[0]:.1f}  RR={best_combo[1]:.1f}  "
              f"OOS PF={best_oos_pf:.2f}")
        print(f"  Current:   Stop={current_stop:.1f}  RR={current_rr:.1f}")
        if best_combo != (current_stop, current_rr) and best_oos_pf > 0:
            print(f"  => UPDATE RECOMMENDED: change to Stop={best_combo[0]:.1f}, RR={best_combo[1]:.1f}")


# ---------------------------------------------------------------------------
# Non-configurable strategy report
# ---------------------------------------------------------------------------

def print_non_configurable_report() -> None:
    """Print notes for strategies that cannot be TP-optimized via rr_ratio."""
    print(f"\n{'='*82}")
    print("  NON-CONFIGURABLE STRATEGIES -- TP Analysis")
    print(f"{'='*82}")
    for label, note in NON_CONFIGURABLE_NOTES:
        marker = "CRITICAL" if "CRITICAL" in note else "NOTE"
        print(f"  [{marker}] {label}: {note}")
    print()
    print("  Action items:")
    print("  1. ICVP: Add risk_reward_ratio param to ichimoku_cloud_trend.py")
    print("     Currently TP = atr_stop_mult * ATR = same as stop => 1:1 R:R.")
    print("     Fix: take_profit = price + rr_ratio * atr_stop_mult * atr")
    print()
    print("  2. CMF: Add risk_reward_ratio param to cascading_momentum_filter.py")
    print("     Currently TP = price + 2.5 * ATR (hardcoded, cannot be optimized).")
    print("     Fix: replace 2.5 with configurable risk_reward_ratio * atr_stop_mult.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(
    run_phase: str,
    only_strategy: str | None,
    only_symbol: str | None,
) -> None:
    """Fetch data and run selected sweep phases."""
    print("\nPARAVANT -- Take-Profit Walk-Forward Optimizer")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"WFO: {len(WFO_WINDOWS)} windows ({IS_DAYS}d IS + {OOS_DAYS}d OOS each)")
    print(f"Fetching {TOTAL_DAYS}d of 1H data from Binance mainnet")

    strategy_keys = list(SWEEP_TARGETS.keys())
    if only_strategy:
        if only_strategy not in SWEEP_TARGETS:
            print(f"Unknown strategy '{only_strategy}'. Options: {', '.join(strategy_keys)}")
            return
        strategy_keys = [only_strategy]

    if only_symbol:
        for key in strategy_keys:
            syms = SWEEP_TARGETS[key]["symbols"]
            if only_symbol in syms:
                SWEEP_TARGETS[key]["symbols"] = [only_symbol]
            else:
                SWEEP_TARGETS[key]["symbols"] = []

    # Fetch all required data
    print("\nFetching data...")
    data = await fetch_all_symbols(strategy_keys, TOTAL_DAYS)
    print(f"Data ready: {len(data)} symbols\n")

    factory = SignalGeneratorFactory()
    config  = BacktestConfig(
        initial_capital  = 10_000.0,
        commission_rate  = 0.001,
        slippage_rate    = 0.0005,
    )

    phase1_results: dict[str, dict] = {}

    if run_phase in ("1", "all"):
        phase1_results = run_phase1(strategy_keys, data, factory, config)

        # Phase 1 summary across all pairs
        print(f"\n{'='*82}")
        print("  PHASE 1 SUMMARY -- WFO TP Recommendations")
        print(f"{'='*82}")
        for label, sym_data in phase1_results.items():
            cfg = SWEEP_TARGETS[label]
            for symbol, results in sym_data.items():
                current_rr  = cfg["current_rr"]
                optimal_rr  = results["optimal_rr"]
                wfo_peak    = results["wfo_peak"]
                plateau     = results["plateau"]
                current_score = results["rr_results"].get(current_rr, {}).get("wfo_avg_pf", 0.0)
                gain = wfo_peak - current_score
                action = "UPDATE" if (gain > 0.05 and optimal_rr != current_rr) else "KEEP"
                print(
                    f"  {label:<8} {symbol:<12}  "
                    f"current={current_rr:.1f}  optimal={optimal_rr:.1f}  "
                    f"WFO_PF={wfo_peak:.2f}  plateau={plateau[0]:.1f}-{plateau[1]:.1f}  "
                    f"gain={gain:+.2f}  [{action}]"
                )

    if run_phase in ("2", "all"):
        if not phase1_results:
            print("Phase 2 requires Phase 1 results. Re-run with --phase all.")
        else:
            run_phase2(phase1_results, data, factory, config)

    print_non_configurable_report()

    print(f"\n{'='*82}")
    print("  DONE")
    print(f"{'='*82}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WFO Take-Profit Optimizer")
    parser.add_argument(
        "--phase", default="all", choices=["1", "2", "all"],
        help="Phase to run: '1' (1D sweep), '2' (2D surface), 'all' (default)",
    )
    parser.add_argument(
        "--strategy", default=None,
        help=f"Run only this strategy. Options: {', '.join(SWEEP_TARGETS.keys())}",
    )
    parser.add_argument(
        "--symbol", default=None,
        help="Run only this symbol (e.g. BTCUSDT)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.phase, args.strategy, args.symbol))
