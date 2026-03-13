#!/usr/bin/env python
"""
Direct strategy comparison backtest runner.

Runs all 4 EMA refined variants against 30-day 1H BTCUSDT and ETHUSDT data,
collects metrics, and prints a formatted comparison table with pass/fail verdict
against SUPERVISED_THRESHOLDS.

Usage (from project root with venv activated):
    python run_strategy_comparison.py

Decision: DEC-2026-02-22-003 - Two-Tier Backtest Validation Thresholds
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from src.core.strategy.backtest.engine import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.backtest.validator import SUPERVISED_THRESHOLDS
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher, OHLCVSeries

# ---------------------------------------------------------------------------
# Variant definitions — same 4 configs as create_strategy_variations.py
# ---------------------------------------------------------------------------

VARIANTS: list[dict[str, Any]] = [
    {
        "id": "ema_refined_baseline_btc",
        "name": "EMA_Refined_Baseline_BTC",
        "template_id": "ema_trend_rsi",
        "symbol": "BTCUSDT",
        "parameters": {
            "fast_ema_period": 8,
            "slow_ema_period": 20,
            "rsi_period": 10,
            "rsi_buy_threshold": 35,
            "rsi_sell_threshold": 65,
            "rsi_overbought": 80,
            "rsi_oversold": 20,
            "atr_multiplier": 1.2,
            "atr_period": 10,
        },
        "note": "Baseline — tighter stops, more entries",
    },
    {
        "id": "ema_refined_a_btc",
        "name": "EMA_Refined_A_BTC",
        "template_id": "ema_trend_rsi",
        "symbol": "BTCUSDT",
        "parameters": {
            "fast_ema_period": 8,
            "slow_ema_period": 26,
            "rsi_period": 10,
            "rsi_buy_threshold": 35,
            "rsi_sell_threshold": 65,
            "rsi_overbought": 80,
            "rsi_oversold": 20,
            "atr_multiplier": 1.0,
            "atr_period": 14,
        },
        "note": "Wider EMA spread, tighter ATR stop",
    },
    {
        "id": "ema_refined_b_eth",
        "name": "EMA_Refined_B_ETH",
        "template_id": "ema_trend_rsi",
        "symbol": "ETHUSDT",
        "parameters": {
            "fast_ema_period": 8,
            "slow_ema_period": 26,
            "rsi_period": 10,
            "rsi_buy_threshold": 35,
            "rsi_sell_threshold": 65,
            "rsi_overbought": 80,
            "rsi_oversold": 20,
            "atr_multiplier": 1.0,
            "atr_period": 14,
        },
        "note": "Same params as A but on ETH (higher volatility)",
    },
    {
        "id": "ema_refined_c_eth",
        "name": "EMA_Refined_C_ETH",
        "template_id": "ema_trend_rsi",
        "symbol": "ETHUSDT",
        "parameters": {
            "fast_ema_period": 5,
            "slow_ema_period": 20,
            "rsi_period": 10,
            "rsi_buy_threshold": 35,
            "rsi_sell_threshold": 65,
            "rsi_overbought": 80,
            "rsi_oversold": 20,
            "atr_multiplier": 1.0,
            "atr_period": 10,
        },
        "note": "Fast aggressive entry on ETH",
    },
]

LOOKBACK_DAYS = 60
TIMEFRAME = "1h"
INITIAL_CAPITAL = 10_000.0


def _make_strategy(variant: dict[str, Any]) -> SimpleNamespace:
    """Create a lightweight in-memory strategy object.

    The BacktestEngine only reads: id, name, template_id, parameters.
    Using SimpleNamespace avoids needing a database session while staying
    fully compatible with the engine interface.

    Args:
        variant: Variant dict with id, name, template_id, parameters.

    Returns:
        SimpleNamespace acting as a Strategy duck-type.
    """
    return SimpleNamespace(
        id=variant["id"],
        name=variant["name"],
        template_id=variant["template_id"],
        parameters=variant["parameters"],
    )


def _verdict(passed: bool, errors: list[str]) -> str:
    """Format pass/fail with first error if failed.

    Args:
        passed: Whether validation passed.
        errors: List of validation error messages.

    Returns:
        Short verdict string.
    """
    if passed:
        return "PASS"
    # Show only the first error to keep table readable
    first = errors[0] if errors else "unknown"
    # Abbreviate common prefixes
    first = (
        first
        .replace("Insufficient trades:", "trades:")
        .replace("Sharpe ratio too low:", "sharpe:")
        .replace("Max drawdown too high:", "drawdown:")
        .replace("Profit factor too low:", "PF:")
        .replace("Expectancy too low:", "expectancy:")
    )
    return f"FAIL  ({first})"


async def _fetch_data(
    fetcher: MarketDataFetcher,
    symbol: str,
    end_date: datetime,
) -> OHLCVSeries:
    """Fetch 30-day 1H historical data for a symbol.

    Args:
        fetcher: MarketDataFetcher instance.
        symbol: Trading pair (e.g., BTCUSDT).
        end_date: End of the lookback window.

    Returns:
        OHLCVSeries covering the lookback period.
    """
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    return await fetcher.fetch_historical_ohlcv(
        symbol=symbol,
        timeframe=TIMEFRAME,
        start_date=start_date,
        end_date=end_date,
    )


async def run_all() -> None:
    """Run all 4 variants and print a comparison table."""
    end_date = datetime.now(timezone.utc)
    fetcher = MarketDataFetcher()
    factory = SignalGeneratorFactory()
    engine = BacktestEngine(signal_generator_factory=factory)
    config = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    print("\n" + "=" * 80)
    print("PARAVANT — Strategy Comparison Backtest")
    print(f"Period : last {LOOKBACK_DAYS} days  |  Timeframe: {TIMEFRAME}  |  Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"Thresholds : SUPERVISED  (Sharpe>=0.5, DD<=25%, PF>=1.35, Trades>=30, Expectancy>0)")
    print("=" * 80)

    # Pre-fetch data for both symbols (avoid duplicate Binance calls)
    print("\nFetching market data from Binance testnet...")
    data_cache: dict[str, OHLCVSeries] = {}
    for symbol in {v["symbol"] for v in VARIANTS}:
        print(f"  {symbol} ... ", end="", flush=True)
        try:
            data_cache[symbol] = await _fetch_data(fetcher, symbol, end_date)
            print(f"{len(data_cache[symbol])} bars")
        except Exception as exc:
            print(f"FAILED: {exc}")
            sys.exit(1)

    # Run each variant
    print("\nRunning backtests...")
    rows: list[dict[str, Any]] = []

    for variant in VARIANTS:
        strategy = _make_strategy(variant)
        series = data_cache[variant["symbol"]]

        print(f"  {variant['name']} ... ", end="", flush=True)
        try:
            result = engine.run_backtest(
                strategy=strategy,
                series=series,
                config=config,
                thresholds=SUPERVISED_THRESHOLDS,
            )
            m = result.metrics
            rows.append({
                "name": variant["name"],
                "symbol": variant["symbol"],
                "sharpe": m.sharpe_ratio,
                "pf": m.profit_factor,
                "dd": m.max_drawdown_pct,
                "wr": m.win_rate_pct,
                "trades": m.total_trades,
                "expectancy": m.expectancy,
                "ret": m.total_return_pct,
                "calmar": m.calmar_ratio,
                "passed": result.passed_validation,
                "errors": result.validation_errors,
                "note": variant["note"],
            })
            verdict = _verdict(result.passed_validation, result.validation_errors)
            print(verdict)
        except Exception as exc:
            print(f"ERROR: {exc}")
            rows.append({
                "name": variant["name"],
                "symbol": variant["symbol"],
                "error": str(exc),
            })

    # ---------------------------------------------------------------------------
    # Print comparison table
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("RESULTS TABLE")
    print("=" * 80)

    header = (
        f"{'Strategy':<30} {'Sym':<8} {'Ret%':>6} {'Sharpe':>7} {'PF':>6} "
        f"{'DD%':>6} {'WR%':>6} {'Trades':>7} {'Exp$':>7} {'Verdict'}"
    )
    print(header)
    print("-" * 80)

    for row in rows:
        if "error" in row:
            print(f"{row['name']:<30} {'ERROR':<8}  {row['error'][:40]}")
            continue
        line = (
            f"{row['name']:<30} {row['symbol']:<8} "
            f"{row['ret']:>5.1f}% "
            f"{row['sharpe']:>7.3f} "
            f"{row['pf']:>6.3f} "
            f"{row['dd']:>5.1f}% "
            f"{row['wr']:>5.1f}% "
            f"{row['trades']:>7} "
            f"{row['expectancy']:>6.2f}  "
            f"{_verdict(row['passed'], row['errors'])}"
        )
        print(line)

    print("-" * 80)

    # ---------------------------------------------------------------------------
    # Rank passing strategies by Sharpe, then advise
    # ---------------------------------------------------------------------------
    passing = [r for r in rows if "error" not in r and r["passed"]]
    failing = [r for r in rows if "error" not in r and not r["passed"]]

    print("\nANALYSIS")
    print("-" * 40)

    if not passing:
        print("No strategies passed supervised thresholds this period.")
        print("\nTop failure reasons:")
        for row in sorted(rows, key=lambda r: r.get("sharpe", -99), reverse=True):
            if "error" not in row and row["errors"]:
                print(f"  {row['name']}: {row['errors'][0]}")
        print("\nRecommendation:")
        print("  1. Try a 60-day lookback (more trades -> higher statistical confidence)")
        print("  2. Switch to 4H timeframe (fewer but cleaner signals)")
        print("  3. Check whether current 30-day period was ranging/choppy")
        print("     (EMA trend strategies under-perform in non-trending conditions)")
    else:
        best = max(passing, key=lambda r: r["sharpe"])
        print(f"Strategies passing : {len(passing)}/{len(rows)}")
        print(f"Best by Sharpe     : {best['name']}")
        print(f"  Sharpe={best['sharpe']:.3f}  PF={best['pf']:.3f}  "
              f"DD={best['dd']:.1f}%  WR={best['wr']:.1f}%  "
              f"Trades={best['trades']}  Exp=${best['expectancy']:.2f}")
        print()
        print("RECOMMENDED NEXT STEP:")
        print(f"  -> Promote '{best['name']}' to SIMULATED_PAPER")
        print("  -> Run for 2-4 weeks on paper before considering live capital")
        print("  -> Validation gate: Sharpe >= 0.5, PF >= 1.35, Expectancy > 0")

        if len(passing) > 1:
            others = [r for r in passing if r["name"] != best["name"]]
            print("\nAlso passed (ranked by Sharpe):")
            for r in sorted(others, key=lambda x: x["sharpe"], reverse=True):
                print(f"  {r['name']}  Sharpe={r['sharpe']:.3f}  PF={r['pf']:.3f}")

        if failing:
            print("\nFailing variants and why:")
            for row in failing:
                print(f"  {row['name']}: {row['errors'][0] if row['errors'] else 'unknown'}")

    print("\n" + "=" * 80)
    print("Calmar ratios (annualised return / max drawdown) — for reference:")
    for row in rows:
        if "error" not in row:
            calmar_display = f"{row['calmar']:.3f}" if row["calmar"] != float("inf") else "inf"
            print(f"  {row['name']:<30}  Calmar={calmar_display}")
    print("  (Supervised mode does not gate on Calmar. Automated tier requires >= 1.0)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all())
