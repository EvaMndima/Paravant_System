#!/usr/bin/env python
"""ATR stop-multiplier sweep for BTF and ICVP strategies.

EP Chan rationale:
    Trailing stop distance = |fill_price - initial_stop_loss|. When
    stop_loss is set but take_profit is None, the engine auto-trails at
    that fixed distance. For 1H crypto, intrabar noise (H-L range) ~= 1x ATR,
    so a 1.5x ATR trail gets clipped by normal bar noise within 1-2 bars.
    Minimum viable trail distance: 2-3x ATR. This sweep finds the optimal
    region without over-fitting (one variable, empirical search).

Usage:
    python scripts/sweep_stop_multiplier.py

Requires:
    - BINANCE_TESTNET=false in .env
    - DATABASE_URL set (or blank defaults to sqlite)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.brokers.binance.client import BinanceClient
from src.core.strategy.backtest import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.backtest.validator import SUPERVISED_THRESHOLDS
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher
from src.utils.logging import get_logger, setup_logging

setup_logging(level="WARNING")
logger = get_logger(__name__)

DAYS = 120

# Symbols with strongest directional edge from the 104-run backtest
BTF_SYMBOLS = ["DOGEUSDT", "DOTUSDT", "ETHUSDT", "BNBUSDT"]
ICVP_SYMBOLS = ["BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT"]

# EP Chan: test the full plausible range, not just the expected optimum.
# Crypto 1H noise is ~1x ATR per bar; need at least 2x to survive a
# single adverse bar. Upper bound: beyond 4x the trade rarely gets stopped.
BTF_STOP_MULTS = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
ICVP_STOP_MULTS = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

# Base parameters (unchanged from the main backtest)
BTF_BASE_PARAMS: dict = {
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
}

ICVP_BASE_PARAMS: dict = {
    "tenkan_period": 20,
    "kijun_period": 60,
    "senkou_b_period": 120,
    "displacement": 30,
    "atr_period": 14,
    "volume_period": 20,
    "volume_threshold": 1.3,
}


async def fetch_data(
    symbols: list[str],
    days: int,
) -> dict[str, object]:
    """Fetch 1H OHLCV data from Binance mainnet."""
    client = BinanceClient(testnet=False)
    fetcher = MarketDataFetcher(client)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    data = {}
    for symbol in symbols:
        print(f"  Fetching {symbol}...", end=" ", flush=True)
        try:
            series = await fetcher.fetch_historical_ohlcv(
                symbol=symbol,
                timeframe="1h",
                start_date=start_date,
                end_date=end_date,
            )
            print(f"{len(series)} bars")
            data[symbol] = series
        except Exception as e:
            print(f"FAILED: {e}")
    return data


def run_one(
    template_id: str,
    params: dict,
    symbol: str,
    series: object,
    factory: SignalGeneratorFactory,
    config: BacktestConfig,
    label: str,
) -> dict:
    """Run a single backtest and return metrics."""
    engine = BacktestEngine(factory)
    strategy = SimpleNamespace(
        id=f"sweep_{template_id}_{symbol}_{label}",
        name=f"{label} {symbol}",
        template_id=template_id,
        parameters=params,
    )
    try:
        result = engine.run_backtest(
            strategy=strategy,
            series=series,
            config=config,
            thresholds=SUPERVISED_THRESHOLDS,
        )
        m = result.metrics
        return {
            "ok": True,
            "trades": m.total_trades,
            "win_rate": m.win_rate_pct,
            "sharpe": m.sharpe_ratio,
            "pf": m.profit_factor,
            "dd": m.max_drawdown_pct,
            "ret": m.total_return_pct,
            "exp": m.expectancy,
            "passed": result.passed_validation,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "trades": 0, "sharpe": 0.0,
                "pf": 0.0, "dd": 0.0, "ret": 0.0, "exp": 0.0,
                "win_rate": 0.0, "passed": False}


def print_sweep_table(
    results: list[dict],
    strategy_name: str,
) -> None:
    """Print sweep results sorted by Sharpe ratio."""
    print(f"\n{'='*85}")
    print(f"  {strategy_name} — Stop Multiplier Sweep  (120d, SUPERVISED thresholds)")
    print("  EP Chan: trail_distance = atr_stop_multiplier x ATR at entry")
    print(f"{'='*85}")
    header = (
        f"{'Mult':>6} {'Symbol':<9} {'Trades':>7} {'WR%':>6} "
        f"{'Sharpe':>8} {'PF':>6} {'DD%':>6} {'Ret%':>7} {'Exp$':>7} {'Pass':>5}"
    )
    print(header)
    print(f"{'-'*85}")

    # Sort by Sharpe descending
    for r in sorted(results, key=lambda x: x.get("sharpe", -99), reverse=True):
        if not r.get("ok", False):
            print(f"  {r.get('mult',0):>5.1f}  {r.get('symbol',''):<9}  ERROR: {r.get('error','')[:50]}")
            continue
        mark = "PASS" if r["passed"] else "----"
        print(
            f"  {r['mult']:>5.1f}  {r['symbol']:<9} "
            f"{r['trades']:>7d} {r['win_rate']:>5.1f}% "
            f"{r['sharpe']:>8.3f} {r['pf']:>6.2f} "
            f"{r['dd']:>5.1f}% {r['ret']:>6.2f}% "
            f"{r['exp']:>6.2f}$  {mark:>5}"
        )

    # Summary: best Sharpe per symbol
    print("\n  Best Sharpe per symbol:")
    symbols = sorted({r["symbol"] for r in results if r.get("ok")})
    for sym in symbols:
        sym_rows = [r for r in results if r.get("ok") and r["symbol"] == sym]
        if not sym_rows:
            continue
        best = max(sym_rows, key=lambda x: x["sharpe"])
        print(
            f"    {sym:<9}  mult={best['mult']:.1f}  "
            f"Sharpe={best['sharpe']:.3f}  PF={best['pf']:.2f}  "
            f"Trades={best['trades']}  {'PASS' if best['passed'] else 'FAIL'}"
        )
    print(f"{'='*85}\n")


async def main() -> None:
    """Fetch data once, run all sweep combinations, print results."""
    print("\nPARAVANT — ATR Stop-Multiplier Sweep (EP Chan framework)")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Period: {DAYS} days  |  Timeframe: 1H  |  Capital: $10,000\n")

    # Fetch all required symbols (deduplicated)
    all_symbols = list(dict.fromkeys(BTF_SYMBOLS + ICVP_SYMBOLS))
    print("Fetching mainnet data...")
    data = await fetch_data(all_symbols, DAYS)
    print(f"Data ready: {len(data)} symbols\n")

    factory = SignalGeneratorFactory()
    config = BacktestConfig(
        initial_capital=10_000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    # -----------------------------------------------------------------------
    # BTF sweep
    # -----------------------------------------------------------------------
    print(f"Running BTF sweep: {len(BTF_STOP_MULTS)} multipliers x {len(BTF_SYMBOLS)} symbols "
          f"= {len(BTF_STOP_MULTS)*len(BTF_SYMBOLS)} runs...")

    btf_results: list[dict] = []
    total = len(BTF_STOP_MULTS) * len(BTF_SYMBOLS)
    count = 0
    for mult in BTF_STOP_MULTS:
        for sym in BTF_SYMBOLS:
            if sym not in data:
                continue
            count += 1
            params = {**BTF_BASE_PARAMS, "atr_stop_multiplier": mult}
            label = f"BTF_m{mult:.1f}"
            print(
                f"  [{count}/{total}] BTF  mult={mult:.1f}  {sym}...",
                end=" ", flush=True,
            )
            r = run_one("bear_trend_follower", params, sym, data[sym],
                        factory, config, label)
            r["mult"] = mult
            r["symbol"] = sym
            btf_results.append(r)
            if r["ok"]:
                print(f"Trades={r['trades']}  Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}")
            else:
                print(f"ERROR: {r.get('error','')[:60]}")

    print_sweep_table(btf_results, "BTF (Bear Trend Follower)")

    # -----------------------------------------------------------------------
    # ICVP sweep
    # -----------------------------------------------------------------------
    print(f"Running ICVP sweep: {len(ICVP_STOP_MULTS)} multipliers x {len(ICVP_SYMBOLS)} symbols "
          f"= {len(ICVP_STOP_MULTS)*len(ICVP_SYMBOLS)} runs...")

    icvp_results: list[dict] = []
    total = len(ICVP_STOP_MULTS) * len(ICVP_SYMBOLS)
    count = 0
    for mult in ICVP_STOP_MULTS:
        for sym in ICVP_SYMBOLS:
            if sym not in data:
                continue
            count += 1
            params = {**ICVP_BASE_PARAMS, "atr_stop_multiplier": mult}
            label = f"ICVP_m{mult:.1f}"
            print(
                f"  [{count}/{total}] ICVP  mult={mult:.1f}  {sym}...",
                end=" ", flush=True,
            )
            r = run_one("ichimoku_cloud_trend", params, sym, data[sym],
                        factory, config, label)
            r["mult"] = mult
            r["symbol"] = sym
            icvp_results.append(r)
            if r["ok"]:
                print(f"Trades={r['trades']}  Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}")
            else:
                print(f"ERROR: {r.get('error','')[:60]}")

    print_sweep_table(icvp_results, "ICVP (Ichimoku Cloud Trend)")


if __name__ == "__main__":
    asyncio.run(main())
