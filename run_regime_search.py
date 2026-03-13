#!/usr/bin/env python
"""
Regime-appropriate strategy search — corrected parameter names.

Tests 6 candidates across 4 templates designed to work in volatile/ranging
or bidirectional (can short) markets. Uses 60-day 1H lookback.
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

INITIAL_CAPITAL = 10_000.0
LOOKBACK_DAYS = 60
TIMEFRAME = "1h"

TESTS: list[dict[str, Any]] = [
    # --- Donchian ATR: breakout in BOTH directions (handles downtrends) ---
    {
        "id": "donchian_btc_1h",
        "name": "Donchian_BTC_1h",
        "template_id": "donchian_atr",
        "symbol": "BTCUSDT",
        "parameters": {
            "donchian_period": 20,
            "atr_period": 14,
            "atr_threshold": 0.003,
            "atr_stop_multiplier": 2.5,
            "volume_ma_period": 20,
            "volume_multiplier": 1.2,
        },
        "rationale": "N-period channel breakout, shorts included",
    },
    {
        "id": "donchian_eth_1h",
        "name": "Donchian_ETH_1h",
        "template_id": "donchian_atr",
        "symbol": "ETHUSDT",
        "parameters": {
            "donchian_period": 20,
            "atr_period": 14,
            "atr_threshold": 0.003,
            "atr_stop_multiplier": 2.5,
            "volume_ma_period": 20,
            "volume_multiplier": 1.2,
        },
        "rationale": "Same on ETH — higher vol = more breakouts",
    },
    # --- Supertrend + MACD: trend-following with short capability ---
    {
        "id": "supertrend_btc_1h",
        "name": "Supertrend_BTC_1h",
        "template_id": "supertrend_volume_macd",
        "symbol": "BTCUSDT",
        "parameters": {
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_ma_period": 20,
            "volume_multiplier": 1.3,
        },
        "rationale": "Supertrend flips direction — profits in downtrends too",
    },
    # --- RSI + BB Mean Reversion: designed for ranging/choppy markets ---
    {
        "id": "rsi_bb_eth_1h",
        "name": "RSI_BB_MeanRev_ETH_1h",
        "template_id": "rsi_bb_mean_reversion",
        "symbol": "ETHUSDT",
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 25.0,
            "rsi_overbought": 75.0,
            "rsi_exit_long": 50.0,
            "rsi_exit_short": 50.0,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adx_threshold": 25.0,
            "stop_loss_pct": 2.5,
        },
        "rationale": "Mean-reversion thrives in choppy/ranging markets",
    },
    {
        "id": "rsi_bb_btc_1h",
        "name": "RSI_BB_MeanRev_BTC_1h",
        "template_id": "rsi_bb_mean_reversion",
        "symbol": "BTCUSDT",
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 25.0,
            "rsi_overbought": 75.0,
            "rsi_exit_long": 50.0,
            "rsi_exit_short": 50.0,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adx_threshold": 25.0,
            "stop_loss_pct": 2.5,
        },
        "rationale": "Same strategy on BTC for comparison",
    },
    # --- VWAP Pullback: intraday, works in any trending direction ---
    {
        "id": "vwap_btc_1h",
        "name": "VWAP_Pullback_BTC_1h",
        "template_id": "vwap_pullback_volume",
        "symbol": "BTCUSDT",
        "parameters": {
            "entry_buffer_pct": 0.3,
            "exit_distance_pct": 1.5,
            "volume_ma_period": 20,
            "volume_multiplier": 1.2,
            "exit_volume_threshold": 0.8,
            "rsi_period": 14,
            "stop_loss_pct": 1.5,
        },
        "rationale": "VWAP mean-reversion — works in any trending day",
    },
    # --- BB Squeeze with looser squeeze threshold to generate more signals ---
    {
        "id": "bb_squeeze_eth_loose",
        "name": "BB_Squeeze_ETH_loose",
        "template_id": "bb_squeeze_breakout",
        "symbol": "ETHUSDT",
        "parameters": {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.07,   # raised from 0.04 -> easier to trigger
            "squeeze_lookback": 10,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.2,     # lowered from 1.5 -> easier to confirm
        },
        "rationale": "Relaxed squeeze filter to get more trade events",
    },
]


def _make_strategy(t: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=t["id"],
        name=t["name"],
        template_id=t["template_id"],
        parameters=t["parameters"],
    )


def _verdict(passed: bool, errors: list[str]) -> str:
    if passed:
        return "PASS"
    first = errors[0] if errors else "?"
    first = (
        first
        .replace("Insufficient trades:", "trades:")
        .replace("Sharpe ratio too low:", "sharpe:")
        .replace("Max drawdown too high:", "drawdown:")
        .replace("Profit factor too low:", "PF:")
        .replace("Expectancy too low:", "expectancy:")
    )
    return f"FAIL ({first})"


async def run_all() -> None:
    """Run all regime-search tests and print comparison table."""
    end_date = datetime.now(timezone.utc)
    fetcher = MarketDataFetcher()
    factory = SignalGeneratorFactory()
    engine = BacktestEngine(signal_generator_factory=factory)
    config = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    print("\n" + "=" * 95)
    print("PARAVANT — Regime Search: Full Template Suite | 60d 1H | Jan-Mar 2026")
    print("Thresholds: SUPERVISED  Sharpe>=0.5 | DD<=25% | PF>=1.35 | Trades>=30 | Exp>$0")
    print("=" * 95)

    # Pre-fetch unique symbol/timeframe combinations
    data_cache: dict[str, OHLCVSeries] = {}
    for t in TESTS:
        if t["symbol"] not in data_cache:
            start = end_date - timedelta(days=LOOKBACK_DAYS)
            print(f"Fetching {t['symbol']} {TIMEFRAME} {LOOKBACK_DAYS}d ... ", end="", flush=True)
            try:
                data_cache[t["symbol"]] = await fetcher.fetch_historical_ohlcv(
                    symbol=t["symbol"],
                    timeframe=TIMEFRAME,
                    start_date=start,
                    end_date=end_date,
                )
                print(f"{len(data_cache[t['symbol']])} bars")
            except Exception as exc:
                print(f"FAILED: {exc}")
                sys.exit(1)

    print("\nRunning backtests...")
    rows: list[dict[str, Any]] = []

    for t in TESTS:
        strategy = _make_strategy(t)
        series = data_cache[t["symbol"]]
        print(f"  {t['name']:<30} ... ", end="", flush=True)
        try:
            result = engine.run_backtest(
                strategy=strategy,
                series=series,
                config=config,
                thresholds=SUPERVISED_THRESHOLDS,
            )
            m = result.metrics
            rows.append({
                "name": t["name"],
                "symbol": t["symbol"],
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
                "rationale": t["rationale"],
            })
            print(_verdict(result.passed_validation, result.validation_errors))
        except Exception as exc:
            print(f"ERROR: {exc}")
            rows.append({"name": t["name"], "symbol": t["symbol"], "error": str(exc)})

    # Results table
    print("\n" + "=" * 95)
    print("RESULTS TABLE")
    print("=" * 95)
    header = (
        f"{'Strategy':<30} {'Sym':<8} {'Ret%':>6} {'Sharpe':>7} {'PF':>6} "
        f"{'DD%':>6} {'WR%':>6} {'Trades':>7} {'Exp$':>7}  Verdict"
    )
    print(header)
    print("-" * 95)

    for row in rows:
        if "error" in row:
            print(f"{row['name']:<30}  ERROR: {row['error'][:55]}")
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

    print("-" * 95)

    passing = [r for r in rows if "error" not in r and r["passed"]]
    failing = [r for r in rows if "error" not in r and not r["passed"]]
    errored = [r for r in rows if "error" in r]

    print("\nANALYSIS & RECOMMENDATION")
    print("-" * 55)

    # Always show full ranking
    valid_rows = [r for r in rows if "error" not in r]
    print(f"\nFull ranking by Sharpe ({len(passing)} passing / {len(valid_rows)} ran):\n")
    for rank, r in enumerate(sorted(valid_rows, key=lambda x: x["sharpe"], reverse=True), 1):
        verdict = _verdict(r["passed"], r["errors"])
        calmar = f"{r['calmar']:.2f}" if r["calmar"] != float("inf") else "inf"
        print(
            f"  #{rank}  {r['name']:<30}  Sharpe={r['sharpe']:>6.3f}  "
            f"PF={r['pf']:>5.3f}  Trades={r['trades']:>3}  "
            f"Exp=${r['expectancy']:>7.2f}  Calmar={calmar:>6}  {verdict}"
        )

    if errored:
        print(f"\nErrors ({len(errored)}):")
        for r in errored:
            print(f"  {r['name']}: {r['error'][:70]}")

    print()
    if not passing:
        print("NO STRATEGIES PASSED in the current 60-day period.")
        print()
        top = sorted(valid_rows, key=lambda x: x["sharpe"], reverse=True)[:3]
        print("Top 3 closest to passing:")
        for r in top:
            gaps = []
            if r["sharpe"] < 0.5:
                gaps.append(f"Sharpe needs +{0.5 - r['sharpe']:.3f}")
            if r["trades"] < 30:
                gaps.append(f"{30 - r['trades']} more trades needed")
            if r["pf"] < 1.35:
                gaps.append(f"PF needs +{1.35 - r['pf']:.3f}")
            if r["dd"] > 25:
                gaps.append(f"DD too high by {r['dd'] - 25:.1f}%")
            if r["expectancy"] < 0.01:
                gaps.append(f"Expectancy negative: ${r['expectancy']:.2f}")
            print(f"  {r['name']}: {' | '.join(gaps)}")
        print()
        print("NEXT STEPS:")
        print("  1. The Jan-Mar 2026 period was strongly bearish for BTC/ETH.")
        print("     Most long-only or symmetric strategies struggle in a sustained downtrend.")
        print("  2. Try MACD Pullback template — it uses trend context and may adapt better.")
        print("  3. Reduce lookback to last 14-21 days to avoid the worst of January.")
        print("  4. Consider that the system may need to sit out unfavorable regimes.")
        print("     Chan: 'The highest skill in trading is knowing when NOT to trade.'")
    else:
        best = max(passing, key=lambda r: r["sharpe"])
        print(f"BEST STRATEGY: {best['name']}")
        print(f"  Sharpe={best['sharpe']:.3f} | Return={best['ret']:.1f}% | PF={best['pf']:.3f} | "
              f"DD={best['dd']:.1f}% | WR={best['wr']:.1f}% | Trades={best['trades']} | "
              f"Exp/trade=${best['expectancy']:.2f}")
        print()
        print("RECOMMENDATION: Promote to SIMULATED_PAPER trading.")
        print("  -> Paper trade for 2-4 weeks before any live capital")
        print("  -> Weekly review: Sharpe should stay above 0.5")
        print("  -> Pause trigger: consecutive week with Sharpe < 0.3 or DD > 20%")

    print("\n" + "=" * 95 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all())
