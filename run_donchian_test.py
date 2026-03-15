#!/usr/bin/env python
"""Quick Donchian post-fix sanity check + mainnet confirmation."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from run_backtest_shared import verdict
from src.core.strategy.backtest.engine import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.backtest.validator import SUPERVISED_THRESHOLDS
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher

TESTS = [
    {
        "name": "Donchian_BTC_original_DB",
        "sym": "BTCUSDT",
        "params": {"donchian_period": 20, "atr_period": 14, "atr_threshold": 0.003,
                   "atr_stop_multiplier": 2.5, "volume_ma_period": 20, "volume_multiplier": 1.2},
    },
    {
        "name": "Donchian_ETH_original_DB",
        "sym": "ETHUSDT",
        "params": {"donchian_period": 20, "atr_period": 14, "atr_threshold": 0.003,
                   "atr_stop_multiplier": 2.5, "volume_ma_period": 20, "volume_multiplier": 1.2},
    },
    {
        "name": "Donchian_BTC_loose_atr001",
        "sym": "BTCUSDT",
        "params": {"donchian_period": 20, "atr_period": 14, "atr_threshold": 0.001,
                   "atr_stop_multiplier": 2.5, "volume_ma_period": 20, "volume_multiplier": 1.0},
    },
    {
        "name": "Donchian_ETH_loose_atr001",
        "sym": "ETHUSDT",
        "params": {"donchian_period": 20, "atr_period": 14, "atr_threshold": 0.001,
                   "atr_stop_multiplier": 2.5, "volume_ma_period": 20, "volume_multiplier": 1.0},
    },
    {
        "name": "Donchian_BTC_period14",
        "sym": "BTCUSDT",
        "params": {"donchian_period": 14, "atr_period": 14, "atr_threshold": 0.001,
                   "atr_stop_multiplier": 2.0, "volume_ma_period": 20, "volume_multiplier": 1.0},
    },
    {
        "name": "Donchian_ETH_period14",
        "sym": "ETHUSDT",
        "params": {"donchian_period": 14, "atr_period": 14, "atr_threshold": 0.001,
                   "atr_stop_multiplier": 2.0, "volume_ma_period": 20, "volume_multiplier": 1.0},
    },
    {
        "name": "Donchian_BTC_period10",
        "sym": "BTCUSDT",
        "params": {"donchian_period": 10, "atr_period": 14, "atr_threshold": 0.001,
                   "atr_stop_multiplier": 2.0, "volume_ma_period": 20, "volume_multiplier": 1.0},
    },
    {
        "name": "Donchian_ETH_period10",
        "sym": "ETHUSDT",
        "params": {"donchian_period": 10, "atr_period": 14, "atr_threshold": 0.001,
                   "atr_stop_multiplier": 2.0, "volume_ma_period": 20, "volume_multiplier": 1.0},
    },
]


async def main() -> None:
    end = datetime.now(timezone.utc)
    fetcher = MarketDataFetcher()
    factory = SignalGeneratorFactory()
    engine = BacktestEngine(signal_generator_factory=factory)
    config = BacktestConfig(initial_capital=10_000.0, commission_rate=0.001, slippage_rate=0.0005)

    print()
    print("=" * 100)
    print("DONCHIAN ATR -- POST-FIX | MAINNET 60d DATA")
    print("Fix: intrabar high/low breakout + SHORT exit added + entries before exits")
    print("=" * 100)

    print("\nFetching mainnet 60d data...")
    btc = await fetcher.fetch_historical_ohlcv("BTCUSDT", "1h", end - timedelta(days=60), end)
    eth = await fetcher.fetch_historical_ohlcv("ETHUSDT", "1h", end - timedelta(days=60), end)
    print(f"  BTC: {len(btc)} bars  {btc[0].timestamp.strftime('%Y-%m-%d')} -> {btc[-1].timestamp.strftime('%Y-%m-%d')}")
    print(f"  ETH: {len(eth)} bars  {eth[0].timestamp.strftime('%Y-%m-%d')} -> {eth[-1].timestamp.strftime('%Y-%m-%d')}")
    print()

    rows = []
    for t in TESTS:
        series = btc if t["sym"] == "BTCUSDT" else eth
        strat = SimpleNamespace(id=t["name"], name=t["name"], template_id="donchian_atr", parameters=t["params"])
        print(f"  {t['name']:<36} ... ", end="", flush=True)
        try:
            r = engine.run_backtest(strat, series, config, SUPERVISED_THRESHOLDS)
            m = r.metrics
            rows.append({
                "name": t["name"], "sym": t["sym"],
                "sharpe": m.sharpe_ratio, "pf": m.profit_factor,
                "dd": m.max_drawdown_pct, "wr": m.win_rate_pct,
                "trades": m.total_trades, "exp": m.expectancy, "ret": m.total_return_pct,
                "passed": r.passed_validation, "errors": r.validation_errors,
            })
            print(verdict(r.passed_validation, r.validation_errors))
        except Exception as e:
            print(f"ERROR: {e}")
            rows.append({"name": t["name"], "sym": t["sym"], "error": str(e)})

    print()
    print("=" * 100)
    hdr = f"{'Name':<36} {'Sym':<8} {'Ret%':>6} {'Sharpe':>7} {'PF':>6} {'DD%':>5} {'WR%':>5} {'Tr':>4} {'Exp$':>7}  Verdict"
    print(hdr)
    print("-" * 100)
    for r in sorted(rows, key=lambda x: x.get("sharpe", -99), reverse=True):
        if "error" in r:
            print(f"{r['name']:<36} ERROR: {r['error'][:50]}")
            continue
        v = verdict(r["passed"], r["errors"])
        print(f"{r['name']:<36} {r['sym']:<8} {r['ret']:>5.1f}% {r['sharpe']:>7.3f}"
              f" {r['pf']:>6.3f} {r['dd']:>4.1f}% {r['wr']:>4.1f}% {r['trades']:>4}"
              f" {r['exp']:>6.2f}  {v}")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
