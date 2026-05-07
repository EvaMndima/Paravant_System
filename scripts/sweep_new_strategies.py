#!/usr/bin/env python
"""Targeted parameter sweep for new bull-regime strategies.

Sweeps the highest-impact parameters for the three strategies showing
signal quality (MTC, BTP, TAM) to find configurations that pass
SUPERVISED thresholds (Sharpe>=0.5, PF>=1.35, Trades>=30, DD<=25%).

Root causes being addressed:
  MTC: RSI pullback zone too tight — trades=7-15 vs needed 30.
       Sweep: rsi_pullback_max x rsi_pullback_min
  BTP: EMA(200) gate too strict — only 1-4 trades per symbol.
       Sweep: htf_ema_period x rsi_pullback_high
  TAM: Quality too low despite regime gate — PF < 1.0 everywhere.
       Sweep: rsi_bull_min x volume_threshold x atr_stop_multiplier

VRB not swept here — needs structural redesign first. Separate script
sweep_vrb_params.py is the right place once compression is reworked.

Data: 45 days (covers April 2026 bull run)
Symbols: BTCUSDT, ETHUSDT, DOGEUSDT, AVAXUSDT (best performers from initial backtest)

Usage:
    python -m scripts.sweep_new_strategies
    python -m scripts.sweep_new_strategies --strategy mtc
    python -m scripts.sweep_new_strategies --strategy btp
    python -m scripts.sweep_new_strategies --strategy tam

Requires:
    - BINANCE_TESTNET=false in .env (mainnet)
    - Valid API keys in .env
"""
from __future__ import annotations

import argparse
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
SYMBOLS = ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "AVAXUSDT"]

# ---------------------------------------------------------------------------
# MTC sweep: RSI pullback zone width
# Root cause: [35,58] too tight in bull trend where RSI stays above 60
# ---------------------------------------------------------------------------
MTC_BASE: dict = {
    "daily_ema_period": 21,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "rsi_period": 14,
    "atr_period": 14,
    "atr_stop_multiplier": 2.0,
    "risk_reward_ratio": 2.5,
}
# Lower bound: keep it tight enough to capture genuine pullbacks
MTC_RSI_MIN = [30.0, 35.0, 40.0, 45.0]
# Upper bound: raising from 58 to 65-70 should 2-3x trade count
MTC_RSI_MAX = [58.0, 62.0, 65.0, 68.0, 72.0]

# ---------------------------------------------------------------------------
# BTP sweep: regime EMA period x RSI pullback zone
# Root cause: EMA(200) gate too strict, misses many valid pullback entries
# ---------------------------------------------------------------------------
BTP_BASE: dict = {
    "trend_ema_period": 50,
    "rsi_period": 14,
    "rsi_pullback_low": 30.0,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "atr_period": 14,
    "atr_stop_multiplier": 2.0,
    "risk_reward_ratio": 2.5,
}
# Regime EMA: 200 rarely has 200-bar pullbacks, 100 or 50 gives more entries
BTP_HTF_EMA = [50, 100, 150, 200]
# RSI pullback high: 55 → 60 → 65 gives progressively more entries
BTP_RSI_HIGH = [55.0, 60.0, 65.0]

# ---------------------------------------------------------------------------
# TAM sweep: tighten entry conditions to raise PF above 1.0
# Root cause: conditions too broadly satisfied in bull trend
# ---------------------------------------------------------------------------
TAM_BASE: dict = {
    "fast_ema_period": 8,
    "slow_ema_period": 21,
    "rsi_period": 14,
    "rsi_bull_max": 72.0,
    "volume_period": 20,
    "atr_period": 14,
    "acceleration_lookback": 5,
    "atr_acceleration_lookback": 5,
    "risk_reward_ratio": 2.5,
    "regime_ema_period": 200,
}
# RSI lower bound: raising from 50 to 55-60 filters out weak momentum entries
TAM_RSI_MIN = [50.0, 53.0, 55.0, 58.0]
# Volume threshold: higher = more selective (fewer but better entries)
TAM_VOL_THRESH = [1.2, 1.5, 2.0]
# Stop multiplier: wider stop = fewer premature exits (helps PF)
TAM_STOP_MULT = [2.0, 2.5, 3.0]


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
    """Run one backtest and return metrics dict."""
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
    """Print sweep results sorted by Sharpe descending, top 40 rows."""
    col_w = 10
    param_header = " ".join(f"{c:>{col_w}}" for c in param_cols)
    print(f"\n{'='*110}")
    print(f"  {title}")
    print(f"  {DAYS}d data  |  SUPERVISED: Sharpe>=0.5 PF>=1.35 Trades>=30 DD<=25%")
    print(f"{'='*110}")
    print(
        f"  {param_header}  {'Symbol':<9} "
        f"{'Trades':>7} {'WR%':>6} {'Sharpe':>8} {'PF':>6} "
        f"{'DD%':>6} {'Ret%':>7} {'Exp$':>7} {'Pass':>5}"
    )
    print(f"  {'-'*106}")

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

    passed = [r for r in results if r.get("passed")]
    ok = [r for r in results if r.get("ok")]
    print(f"\n  PASSED: {len(passed)}/{len(ok)} runs")

    # Best per symbol
    print(f"\n  Best Sharpe per symbol (top 3):")
    for sym in SYMBOLS:
        sym_rows = sorted(
            [r for r in ok if r["symbol"] == sym],
            key=lambda x: x["sharpe"],
            reverse=True,
        )[:3]
        for i, r in enumerate(sym_rows):
            prefix = f"  [{sym}] #{i+1}" if i == 0 else f"         #{i+1}"
            mark = "PASS" if r["passed"] else "FAIL"
            param_vals = " ".join(str(r.get(c, "?")) for c in param_cols)
            print(
                f"  {prefix:15}  params=({param_vals})  "
                f"Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}  "
                f"Trades={r['trades']}  {mark}"
            )
    print(f"{'='*110}\n")


async def sweep_mtc(data: dict, factory: SignalGeneratorFactory, config: BacktestConfig) -> None:
    """Sweep MTC RSI pullback zone parameters."""
    grid = [(mn, mx) for mn, mx in itertools.product(MTC_RSI_MIN, MTC_RSI_MAX) if mn < mx]
    total = len(grid) * len([s for s in SYMBOLS if s in data])
    active = [s for s in SYMBOLS if s in data]
    print(f"\nMTC sweep: {len(grid)} RSI combos x {len(active)} symbols = {total} runs")

    results: list[dict] = []
    count = 0
    for rsi_min, rsi_max in grid:
        for sym in active:
            count += 1
            params = {**MTC_BASE, "rsi_pullback_min": rsi_min, "rsi_pullback_max": rsi_max}
            label = f"rsi{rsi_min:.0f}-{rsi_max:.0f}"
            print(
                f"  [{count}/{total}] MTC rsi_min={rsi_min:.0f} rsi_max={rsi_max:.0f} {sym}...",
                end=" ", flush=True,
            )
            r = run_one("multi_tf_confluence", params, sym, data[sym], factory, config, label)
            r["rsi_min"] = rsi_min
            r["rsi_max"] = rsi_max
            results.append(r)
            if r["ok"]:
                print(f"Trades={r['trades']}  Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}")
            else:
                print(f"ERROR: {r.get('error', '')[:60]}")

    print_table(results, "MTC — rsi_pullback_min x rsi_pullback_max", ["rsi_min", "rsi_max"])


async def sweep_btp(data: dict, factory: SignalGeneratorFactory, config: BacktestConfig) -> None:
    """Sweep BTP regime EMA period and RSI pullback high."""
    grid = list(itertools.product(BTP_HTF_EMA, BTP_RSI_HIGH))
    active = [s for s in SYMBOLS if s in data]
    total = len(grid) * len(active)
    print(f"\nBTP sweep: {len(grid)} EMA/RSI combos x {len(active)} symbols = {total} runs")

    results: list[dict] = []
    count = 0
    for htf_ema, rsi_high in grid:
        for sym in active:
            count += 1
            params = {**BTP_BASE, "htf_ema_period": htf_ema, "rsi_pullback_high": rsi_high}
            label = f"ema{htf_ema}_rsi{rsi_high:.0f}"
            print(
                f"  [{count}/{total}] BTP htf_ema={htf_ema} rsi_high={rsi_high:.0f} {sym}...",
                end=" ", flush=True,
            )
            r = run_one("bull_trend_pullback", params, sym, data[sym], factory, config, label)
            r["htf_ema"] = htf_ema
            r["rsi_high"] = rsi_high
            results.append(r)
            if r["ok"]:
                print(f"Trades={r['trades']}  Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}")
            else:
                print(f"ERROR: {r.get('error', '')[:60]}")

    print_table(results, "BTP — htf_ema_period x rsi_pullback_high", ["htf_ema", "rsi_high"])


async def sweep_tam(data: dict, factory: SignalGeneratorFactory, config: BacktestConfig) -> None:
    """Sweep TAM RSI lower bound, volume threshold, stop multiplier."""
    grid = list(itertools.product(TAM_RSI_MIN, TAM_VOL_THRESH, TAM_STOP_MULT))
    active = [s for s in SYMBOLS if s in data]
    total = len(grid) * len(active)
    print(f"\nTAM sweep: {len(grid)} combos x {len(active)} symbols = {total} runs")

    results: list[dict] = []
    count = 0
    for rsi_min, vol_thresh, stop_mult in grid:
        for sym in active:
            count += 1
            params = {
                **TAM_BASE,
                "rsi_bull_min": rsi_min,
                "volume_threshold": vol_thresh,
                "atr_stop_multiplier": stop_mult,
            }
            label = f"rsi{rsi_min:.0f}_v{vol_thresh:.1f}_s{stop_mult:.1f}"
            print(
                f"  [{count}/{total}] TAM rsi_min={rsi_min:.0f} vol={vol_thresh:.1f} stop={stop_mult:.1f} {sym}...",
                end=" ", flush=True,
            )
            r = run_one("trend_acceleration_momentum", params, sym, data[sym], factory, config, label)
            r["rsi_min"] = rsi_min
            r["vol_thresh"] = vol_thresh
            r["stop_mult"] = stop_mult
            results.append(r)
            if r["ok"]:
                print(f"Trades={r['trades']}  Sharpe={r['sharpe']:.3f}  PF={r['pf']:.2f}")
            else:
                print(f"ERROR: {r.get('error', '')[:60]}")

    print_table(results, "TAM — rsi_bull_min x volume_threshold x atr_stop_multiplier", ["rsi_min", "vol_thresh", "stop_mult"])


async def main() -> None:
    """Run targeted parameter sweeps for new bull-regime strategies."""
    parser = argparse.ArgumentParser(description="New strategies parameter sweep")
    parser.add_argument(
        "--strategy",
        choices=["all", "mtc", "btp", "tam"],
        default="all",
        help="Which strategy to sweep (default: all)",
    )
    args = parser.parse_args()

    print(f"\nPARAVANT New Strategies Parameter Sweep")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Data: {DAYS} days  |  Symbols: {', '.join(SYMBOLS)}\n")

    print("Fetching mainnet data...")
    data = await fetch_data(SYMBOLS, DAYS)
    if not data:
        print("ERROR: No data fetched.")
        return
    print(f"Data ready: {len(data)} symbols\n")

    factory = SignalGeneratorFactory()
    config = BacktestConfig(
        initial_capital=10_000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    if args.strategy in ("all", "mtc"):
        await sweep_mtc(data, factory, config)

    if args.strategy in ("all", "btp"):
        await sweep_btp(data, factory, config)

    if args.strategy in ("all", "tam"):
        await sweep_tam(data, factory, config)


if __name__ == "__main__":
    asyncio.run(main())
