#!/usr/bin/env python
"""
Round 2: Targeted refinements for all 7 strategy templates.

Strategy:
  - EMA: Test best 3 DB variants on 90d lookback (more trades)
  - BB Squeeze: 3 relaxed squeeze variants (0.08, 0.10, 0.12)
  - Donchian: 3 relaxed ATR+volume variants
  - RSI_BB: 3 relaxed ADX variants (remove ranging-only filter)
  - Supertrend: 2 variants with looser volume filter on ETH (best regime)
  - MACD Pullback: 2 higher-selectivity variants
  - VWAP: 1 tighter stop variant on ETH (only test that showed any signal)

All tests run against BTCUSDT and ETHUSDT, 60d AND 90d where specified.

Usage (from project root with venv activated):
    python run_round2_refinements.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from run_backtest_shared import make_strategy, verdict
from src.core.strategy.backtest.engine import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.backtest.validator import SUPERVISED_THRESHOLDS
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher, OHLCVSeries

INITIAL_CAPITAL = 10_000.0
TIMEFRAME = "1h"


# ---------------------------------------------------------------------------
# Round 2 test definitions
# ---------------------------------------------------------------------------

TESTS: list[dict[str, Any]] = [

    # =========================================================================
    # GROUP A: EMA — best 3 DB variants on 90d window (more trade opportunities)
    # =========================================================================
    {
        "id": "ema_slow_90d_btc",
        "name": "EMA_SlowLT_BTC_90d",
        "template_id": "ema_trend_rsi",
        "symbol": "BTCUSDT",
        "lookback": 90,
        "parameters": {
            "fast_ema_period": 30,
            "slow_ema_period": 80,
            "rsi_period": 20,
            "rsi_buy_threshold": 45,
            "rsi_sell_threshold": 55,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "atr_multiplier": 2.5,
            "atr_period": 20,
        },
        "group": "EMA_90d",
        "rationale": "Best Sharpe/PF on 60d (#10 rank) — 90d gives ~40% more trades",
    },
    {
        "id": "ema_slow_90d_eth",
        "name": "EMA_SlowLT_ETH_90d",
        "template_id": "ema_trend_rsi",
        "symbol": "ETHUSDT",
        "lookback": 90,
        "parameters": {
            "fast_ema_period": 30,
            "slow_ema_period": 80,
            "rsi_period": 20,
            "rsi_buy_threshold": 45,
            "rsi_sell_threshold": 55,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "atr_multiplier": 2.5,
            "atr_period": 20,
        },
        "group": "EMA_90d",
        "rationale": "ETH version — higher vol = more crossovers",
    },
    {
        "id": "ema_volatile_90d_btc",
        "name": "EMA_Volatile_BTC_90d",
        "template_id": "ema_trend_rsi",
        "symbol": "BTCUSDT",
        "lookback": 90,
        "parameters": {
            "fast_ema_period": 15,
            "slow_ema_period": 40,
            "rsi_period": 16,
            "rsi_buy_threshold": 48,
            "rsi_sell_threshold": 52,
            "rsi_overbought": 75,
            "rsi_oversold": 25,
            "atr_multiplier": 3.0,
            "atr_period": 16,
        },
        "group": "EMA_90d",
        "rationale": "Best PF/Sharpe on 60d (1.434/3.638) — needs more trades via 90d",
    },
    {
        "id": "ema_volatile_90d_eth",
        "name": "EMA_Volatile_ETH_90d",
        "template_id": "ema_trend_rsi",
        "symbol": "ETHUSDT",
        "lookback": 90,
        "parameters": {
            "fast_ema_period": 15,
            "slow_ema_period": 40,
            "rsi_period": 16,
            "rsi_buy_threshold": 48,
            "rsi_sell_threshold": 52,
            "rsi_overbought": 75,
            "rsi_oversold": 25,
            "atr_multiplier": 3.0,
            "atr_period": 16,
        },
        "group": "EMA_90d",
        "rationale": "ETH version of volatile wide-stops",
    },
    {
        "id": "ema_medium_90d_btc",
        "name": "EMA_MedConservative_BTC_90d",
        "template_id": "ema_trend_rsi",
        "symbol": "BTCUSDT",
        "lookback": 90,
        "parameters": {
            "fast_ema_period": 15,
            "slow_ema_period": 40,
            "rsi_period": 14,
            "rsi_buy_threshold": 50,
            "rsi_sell_threshold": 50,
            "rsi_overbought": 75,
            "rsi_oversold": 25,
            "atr_multiplier": 2.0,
            "atr_period": 14,
        },
        "group": "EMA_90d",
        "rationale": "PF=3.148 on 60d, needs 90d for more crossovers",
    },

    # =========================================================================
    # GROUP B: EMA — relaxed RSI thresholds for more entries on 60d
    # =========================================================================
    {
        "id": "ema_volatile_rsi_relaxed_btc",
        "name": "EMA_Volatile_RSIrelaxed_BTC",
        "template_id": "ema_trend_rsi",
        "symbol": "BTCUSDT",
        "lookback": 60,
        "parameters": {
            "fast_ema_period": 15,
            "slow_ema_period": 40,
            "rsi_period": 16,
            "rsi_buy_threshold": 40,   # was 48 — more entries allowed
            "rsi_sell_threshold": 60,  # was 52 — more exits allowed
            "rsi_overbought": 75,
            "rsi_oversold": 25,
            "atr_multiplier": 3.0,
            "atr_period": 16,
        },
        "group": "EMA_RSI_relaxed",
        "rationale": "buy_threshold 48->40 unlocks more entries in weak-RSI bear environment",
    },
    {
        "id": "ema_volatile_rsi_relaxed_eth",
        "name": "EMA_Volatile_RSIrelaxed_ETH",
        "template_id": "ema_trend_rsi",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "fast_ema_period": 15,
            "slow_ema_period": 40,
            "rsi_period": 16,
            "rsi_buy_threshold": 40,
            "rsi_sell_threshold": 60,
            "rsi_overbought": 75,
            "rsi_oversold": 25,
            "atr_multiplier": 3.0,
            "atr_period": 16,
        },
        "group": "EMA_RSI_relaxed",
        "rationale": "Same on ETH",
    },

    # =========================================================================
    # GROUP C: BB Squeeze — relaxed squeeze threshold variants
    # Current DB: squeeze_threshold=0.04, volume_threshold=1.5 -> 6-8 trades
    # Tested 0.07 -> 10 trades (80% WR). Now trying 0.08, 0.10, 0.12
    # =========================================================================
    {
        "id": "bb_squeeze_eth_v3",
        "name": "BB_Squeeze_ETH_v3_t08",
        "template_id": "bb_squeeze_breakout",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.08,
            "squeeze_lookback": 10,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.0,   # dropped from 1.5 — volume bar no longer strict
        },
        "group": "BB_Squeeze",
        "rationale": "Slight relaxation: 0.04->0.08. volume_threshold removed. Target: 15-20 trades",
    },
    {
        "id": "bb_squeeze_eth_v4",
        "name": "BB_Squeeze_ETH_v4_t10",
        "template_id": "bb_squeeze_breakout",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.10,
            "squeeze_lookback": 10,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.0,
        },
        "group": "BB_Squeeze",
        "rationale": "Moderate relaxation: 0.10. Target: 20-25 trades",
    },
    {
        "id": "bb_squeeze_eth_v5",
        "name": "BB_Squeeze_ETH_v5_t12",
        "template_id": "bb_squeeze_breakout",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.12,
            "squeeze_lookback": 10,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.0,
        },
        "group": "BB_Squeeze",
        "rationale": "Aggressive relaxation: 0.12. Target: 25-35 trades",
    },
    {
        "id": "bb_squeeze_btc_v3",
        "name": "BB_Squeeze_BTC_v3_t10",
        "template_id": "bb_squeeze_breakout",
        "symbol": "BTCUSDT",
        "lookback": 60,
        "parameters": {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.10,
            "squeeze_lookback": 10,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.0,
        },
        "group": "BB_Squeeze",
        "rationale": "BTC version: 0.10 threshold — BTC squeezes differently than ETH",
    },
    {
        "id": "bb_squeeze_eth_90d",
        "name": "BB_Squeeze_ETH_90d_t08",
        "template_id": "bb_squeeze_breakout",
        "symbol": "ETHUSDT",
        "lookback": 90,
        "parameters": {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "squeeze_threshold": 0.08,
            "squeeze_lookback": 10,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.0,
        },
        "group": "BB_Squeeze",
        "rationale": "90d + relaxed threshold: more squeeze events in broader window",
    },

    # =========================================================================
    # GROUP D: Donchian ATR — fix zero-trade problem
    # Current: atr_threshold=0.003, volume_multiplier=1.2 -> 0 trades
    # Both conditions must fire on same bar as channel breakout — too strict
    # =========================================================================
    {
        "id": "donchian_btc_loose_v1",
        "name": "Donchian_BTC_loose_v1",
        "template_id": "donchian_atr",
        "symbol": "BTCUSDT",
        "lookback": 60,
        "parameters": {
            "donchian_period": 20,
            "atr_period": 14,
            "atr_threshold": 0.001,    # 0.003 -> 0.001: ATR just needs to exist
            "atr_stop_multiplier": 2.5,
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,  # 1.2 -> 1.0: average volume OK
        },
        "group": "Donchian",
        "rationale": "Remove ATR filter (0.003->0.001) + volume filter (1.2->1.0)",
    },
    {
        "id": "donchian_eth_loose_v1",
        "name": "Donchian_ETH_loose_v1",
        "template_id": "donchian_atr",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "donchian_period": 20,
            "atr_period": 14,
            "atr_threshold": 0.001,
            "atr_stop_multiplier": 2.5,
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,
        },
        "group": "Donchian",
        "rationale": "ETH version — ETH has higher ATR so should fire more",
    },
    {
        "id": "donchian_btc_shorter_period",
        "name": "Donchian_BTC_period14",
        "template_id": "donchian_atr",
        "symbol": "BTCUSDT",
        "lookback": 60,
        "parameters": {
            "donchian_period": 14,     # shorter = more breakouts (vs 20)
            "atr_period": 14,
            "atr_threshold": 0.001,
            "atr_stop_multiplier": 2.0,
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,
        },
        "group": "Donchian",
        "rationale": "Shorter channel (14 vs 20) = more frequent new highs/lows",
    },
    {
        "id": "donchian_eth_shorter_period",
        "name": "Donchian_ETH_period14",
        "template_id": "donchian_atr",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "donchian_period": 14,
            "atr_period": 14,
            "atr_threshold": 0.001,
            "atr_stop_multiplier": 2.0,
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,
        },
        "group": "Donchian",
        "rationale": "ETH version of 14-period Donchian",
    },

    # =========================================================================
    # GROUP E: RSI + BB Mean Reversion — fix ADX zero-trade problem
    # Current: adx_threshold=25 -> only enters when ADX < 25 (pure ranging)
    # Jan-Mar 2026 BTC/ETH: ADX typically 25-50 (trending) -> 0 entries
    # =========================================================================
    {
        "id": "rsi_bb_btc_adx40",
        "name": "RSI_BB_BTC_ADX40",
        "template_id": "rsi_bb_mean_reversion",
        "symbol": "BTCUSDT",
        "lookback": 60,
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 30.0,      # was 25 — catches more oversold conditions
            "rsi_overbought": 70.0,    # was 75 — catches more overbought
            "rsi_exit_long": 50.0,
            "rsi_exit_short": 50.0,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adx_threshold": 40.0,    # was 25 — allows moderate trending markets
            "stop_loss_pct": 2.5,
        },
        "group": "RSI_BB",
        "rationale": "ADX 25->40: allows entries in moderate-trend conditions. RSI bands widened.",
    },
    {
        "id": "rsi_bb_eth_adx40",
        "name": "RSI_BB_ETH_ADX40",
        "template_id": "rsi_bb_mean_reversion",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 30.0,
            "rsi_overbought": 70.0,
            "rsi_exit_long": 50.0,
            "rsi_exit_short": 50.0,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adx_threshold": 40.0,
            "stop_loss_pct": 2.5,
        },
        "group": "RSI_BB",
        "rationale": "ETH: mean reversion works better on higher-volatility asset",
    },
    {
        "id": "rsi_bb_btc_adx50",
        "name": "RSI_BB_BTC_ADX50",
        "template_id": "rsi_bb_mean_reversion",
        "symbol": "BTCUSDT",
        "lookback": 60,
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 30.0,
            "rsi_overbought": 70.0,
            "rsi_exit_long": 50.0,
            "rsi_exit_short": 50.0,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adx_threshold": 50.0,    # nearly disabled — fires in almost any market
            "stop_loss_pct": 2.0,     # tighter stop in trending environment
        },
        "group": "RSI_BB",
        "rationale": "ADX=50 effectively removes regime filter. Tighter stop for safety.",
    },
    {
        "id": "rsi_bb_eth_adx50",
        "name": "RSI_BB_ETH_ADX50",
        "template_id": "rsi_bb_mean_reversion",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "rsi_period": 14,
            "rsi_oversold": 30.0,
            "rsi_overbought": 70.0,
            "rsi_exit_long": 50.0,
            "rsi_exit_short": 50.0,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "adx_threshold": 50.0,
            "stop_loss_pct": 2.0,
        },
        "group": "RSI_BB",
        "rationale": "ETH version of unlocked RSI_BB",
    },

    # =========================================================================
    # GROUP F: Supertrend + MACD — looser volume filter
    # ETH: 10 trades, Sharpe=1.537 (promising but PF=1.02 borderline)
    # BTC: 8 trades, Sharpe=0.62
    # volume_multiplier=1.3 -> try 1.0 (average volume OK)
    # Also try shorter supertrend period for more direction changes
    # =========================================================================
    {
        "id": "supertrend_eth_loose_vol",
        "name": "Supertrend_ETH_vol10",
        "template_id": "supertrend_volume_macd",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,  # was 1.3 — allow average-volume entries
        },
        "group": "Supertrend",
        "rationale": "ETH best performer: relax volume gate to increase trade count",
    },
    {
        "id": "supertrend_btc_loose_vol",
        "name": "Supertrend_BTC_vol10",
        "template_id": "supertrend_volume_macd",
        "symbol": "BTCUSDT",
        "lookback": 60,
        "parameters": {
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,
        },
        "group": "Supertrend",
        "rationale": "BTC version: lower volume gate",
    },
    {
        "id": "supertrend_eth_fast",
        "name": "Supertrend_ETH_fast7",
        "template_id": "supertrend_volume_macd",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "supertrend_period": 7,    # faster = more direction changes
            "supertrend_multiplier": 2.5,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,
        },
        "group": "Supertrend",
        "rationale": "Faster period (10->7) + tighter multiplier = more trend flips",
    },
    {
        "id": "supertrend_eth_90d",
        "name": "Supertrend_ETH_90d",
        "template_id": "supertrend_volume_macd",
        "symbol": "ETHUSDT",
        "lookback": 90,
        "parameters": {
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,
        },
        "group": "Supertrend",
        "rationale": "90d lookback to capture more trend reversals (bear->bounce cycles)",
    },

    # =========================================================================
    # GROUP G: MACD Pullback — higher selectivity (less chasing reversals)
    # BTC 60d: 25 trades, PF=0.45 (losing). In downtrend, pullback-long fails.
    # Fix: Tighter pullback_tolerance + higher risk_reward = only great setups
    # Also: try on 90d
    # =========================================================================
    {
        "id": "macd_btc_selective",
        "name": "MACD_BTC_selective",
        "template_id": "macd_pullback",
        "symbol": "BTCUSDT",
        "lookback": 60,
        "parameters": {
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "pullback_ema_period": 21,
            "atr_period": 14,
            "atr_stop_multiplier": 1.2,  # tighter stop = less risk per trade
            "risk_reward_ratio": 3.0,    # higher RR = only high-conviction entries
            "pullback_tolerance_pct": 0.3,  # tighter pullback = must be closer to EMA
        },
        "group": "MACD",
        "rationale": "Tighter stop + higher RR filters out low-quality bear-bounce entries",
    },
    {
        "id": "macd_eth_selective",
        "name": "MACD_ETH_selective",
        "template_id": "macd_pullback",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "pullback_ema_period": 21,
            "atr_period": 14,
            "atr_stop_multiplier": 1.2,
            "risk_reward_ratio": 3.0,
            "pullback_tolerance_pct": 0.3,
        },
        "group": "MACD",
        "rationale": "ETH version — ETH had 57% WR on original, better raw signal",
    },

    # =========================================================================
    # GROUP H: VWAP Pullback — tighter config on ETH (only promising direction)
    # Original: -5.3% BTC, -3.8% ETH. Both losing. Not a bear-market strategy.
    # Test with much tighter stop (1.0%) and higher exit target
    # =========================================================================
    {
        "id": "vwap_eth_tight",
        "name": "VWAP_ETH_tight_stop",
        "template_id": "vwap_pullback_volume",
        "symbol": "ETHUSDT",
        "lookback": 60,
        "parameters": {
            "entry_buffer_pct": 0.2,      # tighter entry (was 0.3)
            "exit_distance_pct": 2.0,     # wider target (was 1.5)
            "volume_ma_period": 20,
            "volume_multiplier": 1.0,     # lower volume gate (was 1.2)
            "exit_volume_threshold": 0.6,  # exit on less volume (was 0.8)
            "rsi_period": 14,
            "stop_loss_pct": 1.0,         # tighter stop (was 1.5)
        },
        "group": "VWAP",
        "rationale": "Tighter stop + wider target improves RR. Lower volume gate = more trades.",
    },
]


async def run_round2() -> None:
    """Run all Round 2 refinement tests and print ranked results."""
    end_date = datetime.now(timezone.utc)
    fetcher = MarketDataFetcher()
    factory = SignalGeneratorFactory()
    engine = BacktestEngine(signal_generator_factory=factory)
    config = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    print("\n" + "=" * 115)
    print("PARAVANT — Round 2 Refinements | All 7 Templates | Targeted Parameter Fixes")
    print("Thresholds: SUPERVISED  Sharpe>=0.5 | DD<=25% | PF>=1.35 | Trades>=30 | Exp>$0")
    print("=" * 115)

    # Pre-fetch data for all required (symbol, lookback) combinations
    data_cache: dict[tuple[str, int], OHLCVSeries] = {}
    needed = {(t["symbol"], t["lookback"]) for t in TESTS}
    print(f"\nFetching {len(needed)} data windows...")
    for symbol, lb in sorted(needed):
        key = (symbol, lb)
        start = end_date - timedelta(days=lb)
        print(f"  {symbol} {lb}d ... ", end="", flush=True)
        try:
            data_cache[key] = await fetcher.fetch_historical_ohlcv(
                symbol=symbol,
                timeframe=TIMEFRAME,
                start_date=start,
                end_date=end_date,
            )
            print(f"{len(data_cache[key])} bars")
        except Exception as exc:
            print(f"FAILED: {exc}")
            sys.exit(1)

    print(f"\nRunning {len(TESTS)} backtest configurations...")
    rows: list[dict[str, Any]] = []

    for t in TESTS:
        strat = make_strategy(t)
        series = data_cache[(t["symbol"], t["lookback"])]
        print(f"  [{t['group']:<14}] {t['name']:<35} ... ", end="", flush=True)
        try:
            result = engine.run_backtest(
                strategy=strat,
                series=series,
                config=config,
                thresholds=SUPERVISED_THRESHOLDS,
            )
            m = result.metrics
            rows.append({
                "name": t["name"],
                "group": t["group"],
                "symbol": t["symbol"],
                "lookback": t["lookback"],
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
                "params": t["parameters"],
                "rationale": t["rationale"],
            })
            print(verdict(result.passed_validation, result.validation_errors))
        except Exception as exc:
            print(f"ERROR: {exc}")
            rows.append({"name": t["name"], "group": t["group"], "symbol": t["symbol"], "error": str(exc)})

    # ---- Results table -------------------------------------------------------
    print("\n" + "=" * 115)
    print("RESULTS TABLE — ROUND 2")
    print("=" * 115)
    header = (
        f"{'Strategy':<35} {'Grp':<14} {'Sym':<8} {'LB':>4} "
        f"{'Ret%':>6} {'Sharpe':>7} {'PF':>6} {'DD%':>5} "
        f"{'WR%':>5} {'Trades':>6} {'Exp$':>7}  Verdict"
    )
    print(header)
    print("-" * 115)
    for row in sorted(rows, key=lambda r: r.get("sharpe", -99), reverse=True):
        if "error" in row:
            print(f"{row['name']:<35} ERROR: {row['error'][:60]}")
            continue
        line = (
            f"{row['name']:<35} {row['group']:<14} {row['symbol']:<8} {row['lookback']:>4}d"
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
    print("-" * 115)

    # ---- Summary by group ----------------------------------------------------
    valid = [r for r in rows if "error" not in r]
    passing = [r for r in valid if r["passed"]]
    print(f"\n{'=' * 115}")
    print(f"FULL RANKING  ({len(passing)} PASSING / {len(valid)} TOTAL)")
    print("=" * 115)
    for rank, row in enumerate(sorted(valid, key=lambda r: r["sharpe"], reverse=True), 1):
        v = verdict(row["passed"], row["errors"])
        calmar = f"{row['calmar']:.2f}" if row["calmar"] not in (float("inf"), float("-inf")) else "inf"
        mark = "*** PASS ***" if row["passed"] else ""
        print(
            f"  #{rank:02d} [{row['group']:<14}] {row['name']:<35} {row['symbol']:<8} {row['lookback']:>3}d"
            f"  Sh={row['sharpe']:>+7.3f}  PF={row['pf']:>5.3f}"
            f"  Tr={row['trades']:>3}  Exp=${row['expectancy']:>7.2f}"
            f"  Cal={calmar:>6}  {v}  {mark}"
        )

    # ---- Passing strategies: paper trading advice ---------------------------
    if passing:
        print(f"\n{'=' * 115}")
        print("STRATEGIES READY FOR PAPER TRADING")
        print("=" * 115)
        for r in sorted(passing, key=lambda x: x["sharpe"], reverse=True):
            print(f"\n  STRATEGY: {r['name']}  [{r['group']}]  {r['symbol']}  {r['lookback']}d")
            print(f"  Sharpe={r['sharpe']:.3f} | Return={r['ret']:.1f}% | PF={r['pf']:.3f} | "
                  f"DD={r['dd']:.1f}% | WR={r['wr']:.1f}% | Trades={r['trades']} | Exp=${r['expectancy']:.2f}")
            print(f"  Params: {r['params']}")
            print(f"  Rationale: {r['rationale']}")
    else:
        print(f"\n{'=' * 115}")
        print("NO STRATEGIES PASSED SUPERVISED THRESHOLDS IN ROUND 2")
        print("=" * 115)
        top3 = sorted(valid, key=lambda r: r["sharpe"], reverse=True)[:5]
        print("\nTop 5 closest — gap analysis:")
        for row in top3:
            gaps = []
            if row["sharpe"] < 0.5:
                gaps.append(f"Sharpe needs +{0.5 - row['sharpe']:.3f}")
            if row["trades"] < 30:
                gaps.append(f"{30 - row['trades']} more trades")
            if row["pf"] < 1.35:
                gaps.append(f"PF needs +{1.35 - row['pf']:.3f}")
            if row["dd"] > 25:
                gaps.append(f"DD too high by {row['dd'] - 25:.1f}%")
            if row["expectancy"] < 0.01:
                gaps.append(f"Expectancy negative ${row['expectancy']:.2f}")
            print(f"  {row['name']:<35} {row['symbol']}  Sh={row['sharpe']:+.3f}  "
                  f"Tr={row['trades']}  PF={row['pf']:.3f}  |  GAPS: {' | '.join(gaps)}")

    print(f"\n{'=' * 115}\n")


if __name__ == "__main__":
    asyncio.run(run_round2())
