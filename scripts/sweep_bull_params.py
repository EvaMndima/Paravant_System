#!/usr/bin/env python
"""Bull-regime parameter sweep: MACD_PB and EMA_RSI tuning.

Diagnoses why MACD_PB and EMA_RSI underperform in the 30-day bull
backtest and finds optimal parameter configurations.

MACD_PB root cause: pullback_tolerance_pct=0.5 is too tight for
crypto (price rarely sits within 0.5% of EMA in a trending market).
Sweep: pullback_tolerance_pct x atr_stop_multiplier.

EMA_RSI root cause: 12/26 EMA crossovers are infrequent (low trade count).
Sweep: fast_ema x slow_ema x rsi_buy_threshold.

Data: 45 days (covers full April bull run + late-March transition)
Symbols: BTCUSDT, ETHUSDT, DOGEUSDT, DOTUSDT (highest PF in 30d test)

Usage:
    python -m scripts.sweep_bull_params

Requires:
    - BINANCE_TESTNET=false in .env (mainnet)
    - Valid API keys in .env
"""
from __future__ import annotations

import asyncio
import itertools
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

DAYS = 45
SYMBOLS = ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "DOTUSDT"]

# ---------------------------------------------------------------------------
# MACD_PB sweep grid
# ---------------------------------------------------------------------------
MACD_PB_BASE: dict = {
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "pullback_ema_period": 21,
    "atr_period": 14,
    "risk_reward_ratio": 2.0,
}

# Root issue: tolerance band too tight for trending crypto (1H bars move 0.5-2%)
MACD_PB_TOLERANCE = [0.5, 1.0, 1.5, 2.0, 3.0]
# Stop sizing: 1.0x is too tight for 1H bars; 2.0 gives more room to breathe
MACD_PB_STOP_MULT = [1.0, 1.5, 2.0, 2.5]

# ---------------------------------------------------------------------------
# EMA_RSI sweep grid
# ---------------------------------------------------------------------------
EMA_RSI_BASE: dict = {
    "rsi_period": 14,
    "rsi_sell_threshold": 55.0,
    "rsi_overbought": 75.0,
    "rsi_oversold": 25.0,
    "atr_multiplier": 2.0,
    "atr_period": 14,
}

# Faster EMA pairs cross ~3x more often than 12/26 with modest quality drop
EMA_RSI_FAST = [5, 8, 12]
EMA_RSI_SLOW = [21, 26]
# rsi_buy_threshold: lower = more entries (accepts weaker momentum at crossover)
EMA_RSI_BUY = [35.0, 40.0, 45.0, 50.0]


async def fetch_data(symbols: list[str], days: int) -> dict[str, object]:
    """Fetch 1H OHLCV data from Binance mainnet."""
    client = BinanceClient(testnet=False)
    fetcher = MarketDataFetcher(client)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    data: dict[str, object] = {}
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
        except Exception as exc:
            print(f"FAILED: {exc}")
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
    """Run one backtest configuration and return a metrics dict."""
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
            "label": label,
            "symbol": symbol,
            "trades": m.total_trades,
            "win_rate": m.win_rate_pct,
            "sharpe": m.sharpe_ratio,
            "pf": m.profit_factor,
            "dd": m.max_drawdown_pct,
            "ret": m.total_return_pct,
            "exp": m.expectancy,
            "passed": result.passed_validation,
        }
    except Exception as exc:
        return {
            "ok": False,
            "label": label,
            "symbol": symbol,
            "error": str(exc),
            "trades": 0,
            "win_rate": 0.0,
            "sharpe": -99.0,
            "pf": 0.0,
            "dd": 0.0,
            "ret": 0.0,
            "exp": 0.0,
            "passed": False,
        }


def print_table(results: list[dict], title: str, param_cols: list[str]) -> None:
    """Print sweep results sorted by Sharpe descending."""
    col_w = 10
    param_header = " ".join(f"{c:>{col_w}}" for c in param_cols)
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"  {DAYS}d data  |  SUPERVISED: Sharpe>=0.5 PF>=1.35 Trades>=30 DD<=25%")
    print(f"{'='*100}")
    print(
        f"  {param_header}  {'Symbol':<9} "
        f"{'Trades':>7} {'WR%':>6} {'Sharpe':>8} {'PF':>6} "
        f"{'DD%':>6} {'Ret%':>7} {'Exp$':>7} {'Pass':>5}"
    )
    print(f"  {'-'*96}")

    sorted_rows = sorted(
        [r for r in results if r.get("ok", False)],
        key=lambda x: x.get("sharpe", -99),
        reverse=True,
    )
    for r in sorted_rows[:40]:
        mark = "PASS" if r["passed"] else "----"
        param_vals = " ".join(f"{r.get(c, '?'):>{col_w}}" for c in param_cols)
        print(
            f"  {param_vals}  {r['symbol']:<9} "
            f"{r['trades']:>7d} {r['win_rate']:>5.1f}% "
            f"{r['sharpe']:>8.3f} {r['pf']:>6.2f} "
            f"{r['dd']:>5.1f}% {r['ret']:>6.2f}% "
            f"{r['exp']:>6.2f}$  {mark:>5}"
        )

    # Best per symbol summary
    all_ok = [r for r in results if r.get("ok")]
    print("\n  Best Sharpe per symbol (top 3):")
    for sym in SYMBOLS:
        sym_rows = sorted(
            [r for r in all_ok if r["symbol"] == sym],
            key=lambda x: x["sharpe"],
            reverse=True,
        )[:3]
        for i, r in enumerate(sym_rows):
            prefix = f"  [{sym}] #{i+1}" if i == 0 else f"         #{i+1}"
            mark = "PASS" if r["passed"] else "FAIL"
            param_vals = " ".join(f"{r.get(c, '?')}" for c in param_cols)
            print(
                f"  {prefix:15}  params=({param_vals})  "
                f"Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}  "
                f"Trades={r['trades']}  {mark}"
            )
    print(f"{'='*100}\n")


async def main() -> None:
    """Fetch data, run MACD_PB and EMA_RSI sweeps, print results."""
    print("\nPARAVANT Bull Regime Parameter Sweep")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Data: {DAYS} days  |  Symbols: {', '.join(SYMBOLS)}\n")

    print("Fetching mainnet data...")
    data = await fetch_data(SYMBOLS, DAYS)
    active_symbols = [s for s in SYMBOLS if s in data]
    if not active_symbols:
        print("ERROR: No data fetched.")
        return
    print(f"Data ready: {len(active_symbols)} symbols\n")

    factory = SignalGeneratorFactory()
    config = BacktestConfig(
        initial_capital=10_000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    # -----------------------------------------------------------------------
    # MACD_PB sweep: pullback_tolerance_pct x atr_stop_multiplier
    # -----------------------------------------------------------------------
    macd_grid = list(itertools.product(MACD_PB_TOLERANCE, MACD_PB_STOP_MULT))
    total_macd = len(macd_grid) * len(active_symbols)
    print(
        f"MACD_PB sweep: {len(MACD_PB_TOLERANCE)} tolerances x "
        f"{len(MACD_PB_STOP_MULT)} stop mults x {len(active_symbols)} symbols "
        f"= {total_macd} runs"
    )

    macd_results: list[dict] = []
    count = 0
    for tol, stop_mult in macd_grid:
        for sym in active_symbols:
            count += 1
            params = {
                **MACD_PB_BASE,
                "pullback_tolerance_pct": tol,
                "atr_stop_multiplier": stop_mult,
            }
            label = f"tol{tol:.1f}_m{stop_mult:.1f}"
            print(
                f"  [{count}/{total_macd}] MACD_PB  "
                f"tol={tol:.1f}  stop={stop_mult:.1f}  {sym}...",
                end=" ", flush=True,
            )
            r = run_one("macd_pullback", params, sym, data[sym], factory, config, label)
            r["tol"] = tol
            r["stop"] = stop_mult
            macd_results.append(r)
            if r["ok"]:
                print(f"Trades={r['trades']}  Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}")
            else:
                print(f"ERROR: {r.get('error','')[:60]}")

    print_table(macd_results, "MACD_PB — pullback_tolerance_pct x atr_stop_multiplier", ["tol", "stop"])

    # -----------------------------------------------------------------------
    # EMA_RSI sweep: fast_ema x slow_ema x rsi_buy_threshold
    # -----------------------------------------------------------------------
    ema_grid = list(itertools.product(EMA_RSI_FAST, EMA_RSI_SLOW, EMA_RSI_BUY))
    # Remove combinations where fast >= slow
    ema_grid = [(f, s, b) for f, s, b in ema_grid if f < s]
    total_ema = len(ema_grid) * len(active_symbols)
    print(
        f"\nEMA_RSI sweep: {len(ema_grid)} EMA/RSI combos x {len(active_symbols)} symbols "
        f"= {total_ema} runs"
    )

    ema_results: list[dict] = []
    count = 0
    for fast, slow, rsi_buy in ema_grid:
        for sym in active_symbols:
            count += 1
            params = {
                **EMA_RSI_BASE,
                "fast_ema_period": fast,
                "slow_ema_period": slow,
                "rsi_buy_threshold": rsi_buy,
            }
            label = f"ema{fast}/{slow}_rsi{rsi_buy:.0f}"
            print(
                f"  [{count}/{total_ema}] EMA_RSI  "
                f"ema={fast}/{slow}  rsi_buy={rsi_buy:.0f}  {sym}...",
                end=" ", flush=True,
            )
            r = run_one("ema_trend_rsi", params, sym, data[sym], factory, config, label)
            r["fast"] = fast
            r["slow"] = slow
            r["rsi_buy"] = rsi_buy
            ema_results.append(r)
            if r["ok"]:
                print(f"Trades={r['trades']}  Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}")
            else:
                print(f"ERROR: {r.get('error','')[:60]}")

    print_table(ema_results, "EMA_RSI — fast_ema x slow_ema x rsi_buy_threshold", ["fast", "slow", "rsi_buy"])

    # -----------------------------------------------------------------------
    # Summary: recommended configs
    # -----------------------------------------------------------------------
    print("=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    passed_macd = [r for r in macd_results if r.get("passed")]
    passed_ema = [r for r in ema_results if r.get("passed")]

    if passed_macd:
        best_macd = max(passed_macd, key=lambda x: x["sharpe"])
        print("MACD_PB best passing config:")
        print(
            f"  tol={best_macd['tol']:.1f}  stop={best_macd['stop']:.1f}  "
            f"{best_macd['symbol']}  "
            f"Sharpe={best_macd['sharpe']:.3f}  PF={best_macd['pf']:.2f}  "
            f"Trades={best_macd['trades']}"
        )
    else:
        best_macd = max(
            [r for r in macd_results if r.get("ok")],
            key=lambda x: x.get("pf", 0) * (1 if x.get("trades", 0) >= 15 else 0.3),
        )
        print(
            f"MACD_PB no passing config found. Best candidate: "
            f"tol={best_macd.get('tol'):.1f}  stop={best_macd.get('stop'):.1f}  "
            f"{best_macd['symbol']}  "
            f"PF={best_macd['pf']:.2f}  Trades={best_macd['trades']}"
        )

    if passed_ema:
        best_ema = max(passed_ema, key=lambda x: x["sharpe"])
        print("EMA_RSI best passing config:")
        print(
            f"  ema={best_ema['fast']}/{best_ema['slow']}  "
            f"rsi_buy={best_ema['rsi_buy']:.0f}  "
            f"{best_ema['symbol']}  "
            f"Sharpe={best_ema['sharpe']:.3f}  PF={best_ema['pf']:.2f}  "
            f"Trades={best_ema['trades']}"
        )
    else:
        ok_ema = [r for r in ema_results if r.get("ok")]
        if ok_ema:
            best_ema = max(ok_ema, key=lambda x: x.get("pf", 0))
            print(
                f"EMA_RSI no passing config found. Best candidate: "
                f"ema={best_ema.get('fast')}/{best_ema.get('slow')}  "
                f"rsi_buy={best_ema.get('rsi_buy'):.0f}  "
                f"{best_ema['symbol']}  "
                f"PF={best_ema['pf']:.2f}  Trades={best_ema['trades']}"
            )

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
