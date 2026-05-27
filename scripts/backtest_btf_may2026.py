#!/usr/bin/env python
"""BTF re-backtest on the May 2026 window — overfitting diagnostic.

Background:
    BTF was promoted on the basis of Q1 2026 backtests showing 100% WR and
    Sharpe 2.4-3.6. Live paper trading on the current May 2026 bear regime
    shows only 48% WR, PF 0.75 across 25 trades — a sharp degradation that
    suggests the Q1 numbers were sample-specific.

What this script does:
    Re-runs BTF on a configurable date window using EXACTLY the parameters
    currently deployed in scripts/run_paper_trading.py. Compares per-symbol
    metrics so we can see whether BTF still has positive expectancy on
    fresh data or whether the strategy needs to be rebuilt before it earns
    capital again.

Usage:
    # Default: May 2026 window across the 7 active BTF symbols
    python scripts/backtest_btf_may2026.py

    # Custom window
    python scripts/backtest_btf_may2026.py --start 2026-04-01 --end 2026-05-27

    # Q1 reference comparison (the window BTF was originally validated on)
    python scripts/backtest_btf_may2026.py --start 2026-01-15 --end 2026-03-31

Requires:
    BINANCE_API_KEY / BINANCE_SECRET_KEY in .env (mainnet read access only).
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from src.brokers.binance.client import BinanceClient
from src.core.strategy.backtest import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher
from src.utils.logging import get_logger, setup_logging

setup_logging(level="WARNING")
logger = get_logger(__name__)

# Exact params from scripts/run_paper_trading.py BEAR_STRATEGY_CONFIG.
# Kept in this file so the diagnostic is self-contained — if paper params
# change, update them here too.
BTF_PARAMS: dict = {
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
}

# Post-DOT-removal symbol list (matches paper config after 2026-05-27).
BTF_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
    "XRPUSDT", "AVAXUSDT", "DOGEUSDT",
]


async def run(start: datetime, end: datetime, symbols: list[str]) -> None:
    """Fetch data and backtest BTF across symbols within the window."""
    client = BinanceClient(testnet=False)
    fetcher = MarketDataFetcher(client)
    factory = SignalGeneratorFactory()

    config = BacktestConfig(
        initial_capital=10_000.0,
        commission_pct=0.001,
        slippage_pct=0.0005,
    )
    engine = BacktestEngine(factory)

    days = (end - start).days
    print(f"\nWindow: {start.date()} -> {end.date()} ({days} days)")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Strategy: BTF (bear_trend_follower) with stop_mult=2.5x ATR")
    print()

    results: list[dict] = []

    for sym in symbols:
        print(f"  Fetching {sym} 1H data... ", end="", flush=True)
        try:
            series = await fetcher.fetch_historical_ohlcv(
                symbol=sym,
                timeframe="1h",
                start_date=start,
                end_date=end,
            )
            print(f"{len(series)} bars", end=" ")
        except Exception as e:
            print(f"FETCH FAILED: {e}")
            continue

        strategy = SimpleNamespace(
            id=f"btf_diag_{sym}",
            name=f"BTF {sym}",
            template_id="bear_trend_follower",
            parameters=BTF_PARAMS,
        )

        try:
            result = engine.run_backtest(
                strategy=strategy, series=series, config=config,
            )
            m = result.metrics
            results.append({
                "symbol": sym,
                "trades": m.total_trades,
                "wr": m.win_rate_pct,
                "sharpe": m.sharpe_ratio,
                "pf": m.profit_factor,
                "dd": m.max_drawdown_pct,
                "ret": m.total_return_pct,
                "exp": m.expectancy,
            })
            print(f"-> {m.total_trades}T, PF={m.profit_factor:.2f}")
        except Exception as e:
            print(f"BACKTEST FAILED: {e}")

    print("\n" + "=" * 92)
    print(f"BTF DIAGNOSTIC RESULTS — {start.date()} to {end.date()}")
    print("=" * 92)
    print(
        f"{'Symbol':<10} {'Trades':>7} {'WR%':>7} {'Sharpe':>8} "
        f"{'PF':>7} {'DD%':>7} {'Ret%':>8} {'Exp$':>9}"
    )
    print("-" * 92)
    for r in results:
        print(
            f"{r['symbol']:<10} "
            f"{r['trades']:>7d} "
            f"{r['wr']:>6.1f}% "
            f"{r['sharpe']:>8.3f} "
            f"{r['pf']:>7.2f} "
            f"{r['dd']:>6.1f}% "
            f"{r['ret']:>7.2f}% "
            f"{r['exp']:>+8.2f}$"
        )
    print("-" * 92)

    n_with_trades = sum(1 for r in results if r["trades"] > 0)
    if n_with_trades:
        avg_pf = sum(r["pf"] for r in results if r["trades"] > 0) / n_with_trades
        passing = sum(1 for r in results if r["pf"] >= 1.35 and r["trades"] >= 10)
        print(
            f"Summary: {passing}/{n_with_trades} symbols passing PF>=1.35 with "
            f">=10 trades. Basket avg PF = {avg_pf:.2f}."
        )

    print()
    print("Interpretation:")
    print("  - PF >= 1.35 and Sharpe >= 0.5 = passes SUPERVISED gate")
    print("  - PF < 1.0 = strategy loses money on this window")
    print("  - Compare to live paper PF=0.75 to confirm/refute the")
    print("    backtest-overfit hypothesis.")


def main() -> None:
    p = argparse.ArgumentParser(description="BTF re-backtest diagnostic")
    p.add_argument("--start", type=str, default="2026-04-25",
                   help="Start date YYYY-MM-DD (default 2026-04-25)")
    p.add_argument("--end", type=str, default="2026-05-27",
                   help="End date YYYY-MM-DD (default 2026-05-27)")
    p.add_argument("--symbols", type=str, default=None,
                   help="Comma-separated symbols (default: all 7 BTF symbols)")
    args = p.parse_args()

    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    symbols = (
        [s.strip() for s in args.symbols.split(",")]
        if args.symbols else BTF_SYMBOLS
    )

    asyncio.run(run(start, end, symbols))


if __name__ == "__main__":
    main()
