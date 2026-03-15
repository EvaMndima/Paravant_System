#!/usr/bin/env python
"""
Full DB strategy runner.

Reads ALL strategies from the database, deduplicates by (template_id + params),
runs each unique config against BTC and ETH, and prints a comprehensive
comparison table with pass/fail verdicts.

Covers all 7 templates across all unique parameter variants.

Usage (from project root with venv activated):
    python run_all_db_strategies.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from run_backtest_shared import verdict
from src.core.strategy.backtest.engine import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.backtest.validator import SUPERVISED_THRESHOLDS
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.database import get_db
from src.data.market_data import MarketDataFetcher, OHLCVSeries
from src.data.models.strategy import Strategy
from sqlalchemy import select

LOOKBACK_DAYS = 60
TIMEFRAME = "1h"
INITIAL_CAPITAL = 10_000.0
TEST_SYMBOLS = ["BTCUSDT", "ETHUSDT"]


def _params_hash(params: dict[str, Any]) -> str:
    """Stable hash for deduplication of identical parameter sets."""
    return hashlib.md5(
        json.dumps(params, sort_keys=True).encode()
    ).hexdigest()[:8]


def _load_unique_configs() -> list[dict[str, Any]]:
    """Load all DB strategies, deduplicate by (template_id, params_hash).

    Returns a list of unique configs, each with 'names' listing all DB
    strategy names that share the same params.
    """
    seen: dict[str, dict[str, Any]] = {}
    with get_db() as session:
        rows = session.execute(select(Strategy)).scalars().all()
        for row in rows:
            key = f"{row.template_id}::{_params_hash(row.parameters)}"
            if key not in seen:
                seen[key] = {
                    "key": key,
                    "template_id": row.template_id,
                    "parameters": dict(row.parameters),
                    "names": [row.name],
                }
            else:
                seen[key]["names"].append(row.name)

    return list(seen.values())


async def _fetch_data(
    fetcher: MarketDataFetcher,
    symbol: str,
    end_date: datetime,
) -> OHLCVSeries:
    start = end_date - timedelta(days=LOOKBACK_DAYS)
    return await fetcher.fetch_historical_ohlcv(
        symbol=symbol,
        timeframe=TIMEFRAME,
        start_date=start,
        end_date=end_date,
    )


async def run_all() -> None:
    """Run all unique DB configs against BTC and ETH, print full report."""
    end_date = datetime.now(timezone.utc)
    fetcher = MarketDataFetcher()
    factory = SignalGeneratorFactory()
    engine = BacktestEngine(signal_generator_factory=factory)
    config = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    print("\n" + "=" * 110)
    print("PARAVANT — Full DB Strategy Backtest | All Templates | Deduplicated | 60d 1H")
    print(f"Thresholds: SUPERVISED  Sharpe>=0.5 | DD<=25% | PF>=1.35 | Trades>=30 | Exp>$0")
    print("=" * 110)

    # Load unique configs
    configs = _load_unique_configs()
    print(f"\nLoaded {len(configs)} unique parameter sets from database.\n")

    # Group by template for display
    by_template: dict[str, list[dict[str, Any]]] = {}
    for cfg in configs:
        by_template.setdefault(cfg["template_id"], []).append(cfg)

    for tmpl, cfgs in by_template.items():
        print(f"  {tmpl}: {len(cfgs)} unique param set(s)")
    print()

    # Pre-fetch market data
    print("Fetching market data...")
    data_cache: dict[str, OHLCVSeries] = {}
    for symbol in TEST_SYMBOLS:
        print(f"  {symbol} ... ", end="", flush=True)
        try:
            data_cache[symbol] = await _fetch_data(fetcher, symbol, end_date)
            print(f"{len(data_cache[symbol])} bars")
        except Exception as exc:
            print(f"FAILED: {exc}")
            sys.exit(1)

    # Run all unique configs on each test symbol
    print("\nRunning backtests...")
    rows: list[dict[str, Any]] = []
    run_id = 0

    for cfg in configs:
        for symbol in TEST_SYMBOLS:
            run_id += 1
            short_name = cfg["names"][0][:28]
            label = f"  [{run_id:02d}] {cfg['template_id']:<28} {symbol}"
            print(f"{label} ... ", end="", flush=True)

            strat = SimpleNamespace(
                id=f"{cfg['key']}_{symbol}",
                name=cfg["names"][0],
                template_id=cfg["template_id"],
                parameters=cfg["parameters"],
            )
            try:
                result = engine.run_backtest(
                    strategy=strat,
                    series=data_cache[symbol],
                    config=config,
                    thresholds=SUPERVISED_THRESHOLDS,
                )
                m = result.metrics
                rows.append({
                    "run_id": run_id,
                    "template": cfg["template_id"],
                    "name": cfg["names"][0],
                    "aliases": len(cfg["names"]) - 1,
                    "symbol": symbol,
                    "params_hash": cfg["key"].split("::")[-1],
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
                    "params": cfg["parameters"],
                })
                print(verdict(result.passed_validation, result.validation_errors))
            except Exception as exc:
                print(f"ERROR: {exc}")
                rows.append({
                    "run_id": run_id,
                    "template": cfg["template_id"],
                    "name": cfg["names"][0],
                    "symbol": symbol,
                    "error": str(exc),
                })

    # ---- Results table -------------------------------------------------------
    print("\n" + "=" * 110)
    print("RESULTS TABLE — ALL RUNS")
    print("=" * 110)
    header = (
        f"{'#':>3} {'Template':<28} {'Sym':<8} {'Ret%':>6} {'Sharpe':>7} "
        f"{'PF':>6} {'DD%':>5} {'WR%':>5} {'Trades':>6} {'Exp$':>7}  Verdict"
    )
    print(header)
    print("-" * 110)

    for row in sorted(rows, key=lambda r: r.get("sharpe", -99), reverse=True):
        if "error" in row:
            print(f"{row['run_id']:>3} {row['template']:<28} {row['symbol']:<8}  ERROR: {row['error'][:55]}")
            continue
        line = (
            f"{row['run_id']:>3} {row['template']:<28} {row['symbol']:<8}"
            f" {row['ret']:>5.1f}%"
            f" {row['sharpe']:>7.3f}"
            f" {row['pf']:>6.3f}"
            f" {row['dd']:>4.1f}%"
            f" {row['wr']:>4.1f}%"
            f" {row['trades']:>6}"
            f" {row['expectancy']:>6.2f}  "
            f"{verdict(row['passed'], row['errors'])}"
        )
        print(line)

    print("-" * 110)

    # ---- Summary by template -------------------------------------------------
    print("\n" + "=" * 110)
    print("SUMMARY BY TEMPLATE")
    print("=" * 110)
    templates = sorted({r["template"] for r in rows if "error" not in r})
    for tmpl in templates:
        tmpl_rows = [r for r in rows if "error" not in r and r["template"] == tmpl]
        if not tmpl_rows:
            continue
        best = max(tmpl_rows, key=lambda r: r["sharpe"])
        max_trades = max(r["trades"] for r in tmpl_rows)
        avg_sharpe = sum(r["sharpe"] for r in tmpl_rows) / len(tmpl_rows)
        passing = [r for r in tmpl_rows if r["passed"]]
        print(
            f"  {tmpl:<30} runs={len(tmpl_rows)}  "
            f"best_sharpe={best['sharpe']:+.3f} ({best['symbol']})  "
            f"max_trades={max_trades}  avg_sharpe={avg_sharpe:+.3f}  "
            f"passing={len(passing)}"
        )

    # ---- Full ranking of valid runs ------------------------------------------
    valid = [r for r in rows if "error" not in r]
    passing_all = [r for r in valid if r["passed"]]
    print(f"\n{'=' * 110}")
    print(f"FULL RANKING BY SHARPE  ({len(passing_all)} PASSING / {len(valid)} TOTAL RUNS)")
    print("=" * 110)
    for rank, row in enumerate(sorted(valid, key=lambda r: r["sharpe"], reverse=True), 1):
        v = verdict(row["passed"], row["errors"])
        calmar = f"{row['calmar']:.2f}" if row["calmar"] not in (float("inf"), float("-inf")) else "inf"
        mark = "*** PASS ***" if row["passed"] else ""
        print(
            f"  #{rank:02d} {row['template']:<28} {row['symbol']:<8}"
            f"  Sharpe={row['sharpe']:>+7.3f}  PF={row['pf']:>5.3f}"
            f"  Trades={row['trades']:>3}  Exp=${row['expectancy']:>8.2f}"
            f"  Calmar={calmar:>6}  {v}  {mark}"
        )

    # ---- Diagnosis for zero-trade strategies ---------------------------------
    zero_trade = [r for r in valid if r["trades"] == 0]
    if zero_trade:
        print(f"\n{'=' * 110}")
        print(f"ZERO-TRADE DIAGNOSIS ({len(zero_trade)} runs)")
        print("=" * 110)
        seen_templates: set[str] = set()
        for row in zero_trade:
            if row["template"] in seen_templates:
                continue
            seen_templates.add(row["template"])
            p = row["params"]
            print(f"\n  {row['template']}:")
            print(f"    Params: {json.dumps(p, indent=6)}")
            if row["template"] == "donchian_atr":
                print(f"    Diagnosis: atr_threshold={p.get('atr_threshold')} AND "
                      f"volume_multiplier={p.get('volume_multiplier')} too strict.")
                print(f"    Fix: lower atr_threshold to 0.001, volume_multiplier to 1.0")
            elif row["template"] == "rsi_bb_mean_reversion":
                print(f"    Diagnosis: adx_threshold={p.get('adx_threshold')} blocks all trades in "
                      f"trending/bearish regime (ADX typically 30-50 in downtrend).")
                print(f"    Fix: raise adx_threshold to 40-50, widen rsi bands to os=30/ob=70")
            elif row["template"] == "bb_squeeze_breakout":
                print(f"    Diagnosis: squeeze_threshold={p.get('squeeze_threshold')} too tight "
                      f"(0.04 = fewer setups than 0.07 which only gave 10 trades).")
                print(f"    Fix: raise to 0.10-0.12, lower volume_threshold to 1.0")

    print(f"\n{'=' * 110}\n")


if __name__ == "__main__":
    asyncio.run(run_all())
