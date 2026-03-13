#!/usr/bin/env python
"""
Create four EMA trend-following strategy variants for A/B comparison.

Based on the optimization guide finding that Regime_TrendingUp_Fast_Momentum
(ema_trend_rsi, fast=8 / slow=20) produced 62% win rate / 1.8 Sharpe in
trending_up regime on BTCUSDT 1H.

Refinement hypothesis (three targeted changes):
  1. Widen the EMA gap: slow_ema 20 -> 26 (the classic MACD pair, reduces
     false crossovers from sub-movements inside the trend).
  2. Tighten ATR stop: atr_multiplier 1.2 -> 1.0, atr_period 10 -> 14
     (cuts losses faster on BTC's intraday whipsaws, lowers avg loss).
  3. Test on ETHUSDT: ETH has ~30% more intraday volatility meaning larger
     price moves per signal and larger average wins on the same parameters.

Run all four through backtest, then compare:
    Sharpe ratio  (primary ranking metric)
    Profit factor (secondary)
    Max drawdown  (risk check)

Backtest recommended settings:
    Lookback:        30 days AND 60 days (consistency check)
    Initial capital: 10000 USDT
    Timeframe:       1h
    Regime tag:      trending_up (match strategy to its designed regime)

Usage:
    python create_strategy_variations.py
"""
import io
import sys

import requests

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "http://localhost:8000/api/v1"

# ---------------------------------------------------------------------------
# Strategy variant definitions
# ---------------------------------------------------------------------------

VARIANTS: list[dict] = [
    # ------------------------------------------------------------------
    # BASELINE - original parameters from optimization guide
    # This is the performance benchmark everything else is compared against.
    # Expected: ~62% win rate, ~1.8 Sharpe on BTC 30-day trending_up
    # ------------------------------------------------------------------
    {
        "name": "EMA_Refined_Baseline_BTC",
        "template_id": "ema_trend_rsi",
        "description": (
            "Baseline fast-momentum EMA strategy on BTCUSDT. "
            "Replicates the Regime_TrendingUp_Fast_Momentum parameters "
            "from the optimization guide (fast=8, slow=20, atr_mult=1.2). "
            "Use as benchmark for refined variants A, B, C."
        ),
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
        "backtest_asset": "BTCUSDT",
        "backtest_note": "Benchmark. Run first to establish baseline metrics.",
    },
    # ------------------------------------------------------------------
    # REFINED A - wider EMA gap + tighter ATR stop on BTC
    # Hypothesis: EMA(8)/EMA(26) is the classic MACD pair. The wider gap
    # reduces false signals inside a trend. Tighter ATR (mult=1.0,
    # period=14) cuts losses faster, improving profit factor.
    # Expected: slightly lower trade count, higher win/loss ratio
    # ------------------------------------------------------------------
    {
        "name": "EMA_Refined_A_BTC",
        "template_id": "ema_trend_rsi",
        "description": (
            "Refined BTC variant: wider EMA gap (8/26 vs 8/20) + tighter "
            "ATR stop (mult=1.0, period=14 vs 1.2/10). Hypothesis: the "
            "EMA(8)/EMA(26) pair reduces false crossovers in sub-trending "
            "moves while the tighter stop cuts avg loss, improving PF."
        ),
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
        "backtest_asset": "BTCUSDT",
        "backtest_note": (
            "Compare Sharpe and PF against Baseline. If both improve, "
            "this is the BTC production candidate."
        ),
    },
    # ------------------------------------------------------------------
    # REFINED B - same as A but on ETHUSDT
    # Hypothesis: ETH has ~30% more intraday volatility than BTC. The same
    # parameters produce larger price moves per signal, meaning larger
    # average wins. Higher raw return and Sharpe expected.
    # ------------------------------------------------------------------
    {
        "name": "EMA_Refined_B_ETH",
        "template_id": "ema_trend_rsi",
        "description": (
            "Refined A parameters applied to ETHUSDT. ETH has ~30% more "
            "intraday volatility than BTC - same signal logic generates "
            "larger average wins. Hypothesis: higher annualized return "
            "and Sharpe than Refined A / Baseline on BTC."
        ),
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
        "backtest_asset": "ETHUSDT",
        "backtest_note": (
            "Run on ETHUSDT. Compare all metrics against Refined A (BTC). "
            "If Sharpe > Refined A with drawdown still < 20%, prefer ETH."
        ),
    },
    # ------------------------------------------------------------------
    # REFINED C - faster entry on ETH (5/20)
    # Hypothesis: ETH's higher volatility may generate more usable signals
    # with an even tighter fast EMA (5). More trades per period means more
    # data and potentially higher absolute return, at cost of slightly
    # more noise.
    # ------------------------------------------------------------------
    {
        "name": "EMA_Refined_C_ETH",
        "template_id": "ema_trend_rsi",
        "description": (
            "Fastest-entry variant on ETHUSDT: fast_ema=5 (vs 8 in others). "
            "Hypothesis: tighter EMA pair on ETH's higher volatility "
            "generates more valid signals and higher trade count, improving "
            "statistical confidence. Risk: slightly more noise entries."
        ),
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
        "backtest_asset": "ETHUSDT",
        "backtest_note": (
            "Compare trade count and Sharpe against Refined B. If trade "
            "count increases but Sharpe holds, this is the ETH candidate."
        ),
    },
]

# ---------------------------------------------------------------------------
# Comparison table — printed after creation
# ---------------------------------------------------------------------------

COMPARISON_TABLE = """
================================================================================
COMPARISON TEST PLAN
================================================================================

After creating all four variants, run each backtest with these settings:

  Asset:           see each strategy's backtest_asset above
  Timeframe:       1h
  Lookback:        30 days  (quick validation)
  Initial capital: 10000 USDT
  Regime tag:      trending_up  (match strategy to its designed regime)

Record these metrics for each variant:

  Strategy                 | Sharpe | PF   | Win% | MaxDD | Trades
  -------------------------|--------|------|------|-------|-------
  EMA_Refined_Baseline_BTC |        |      |      |       |
  EMA_Refined_A_BTC        |        |      |      |       |
  EMA_Refined_B_ETH        |        |      |      |       |
  EMA_Refined_C_ETH        |        |      |      |       |

Decision criteria:
  1. Winner = highest Sharpe with MaxDD still < 20%
  2. If two strategies within 0.1 Sharpe: prefer higher Profit Factor
  3. Re-run winner on 60-day lookback to confirm consistency
  4. If consistent: deploy winner to paper trading (SIMULATED_PAPER)

Validation tier to use:
  SUPERVISED_THRESHOLDS (current phase - you are watching daily)
  Switch to AUTOMATED_THRESHOLDS when moving to live automated trading

Pass criteria under Supervised tier (validator.py defaults):
  Sharpe  >= 0.5   |  PF >= 1.35  |  Trades >= 30  |  Expectancy > 0
  Win rate NOT enforced  |  Calmar NOT enforced

Expected ranking hypothesis:
  Refined B (ETH, 8/26) >= Refined A (BTC, 8/26) >= Baseline (BTC, 8/20)
  Refined C (ETH, 5/20) - compare vs B (more trades vs noise)
================================================================================
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def create_strategy(variant: dict) -> bool:
    """Create a single strategy via the API."""
    payload = {
        "name": variant["name"],
        "template_id": variant["template_id"],
        "description": variant["description"],
        "parameters": variant["parameters"],
    }
    try:
        resp = requests.post(
            f"{BASE_URL}/strategies",
            json=payload,
            timeout=10,
        )
        if resp.status_code == 201:
            data = resp.json()
            strategy_id = data.get("id", "unknown")
            print(f"  [OK] {variant['name']}  (id: {strategy_id})")
            print(f"       Backtest on: {variant['backtest_asset']}")
            print(f"       Note:        {variant['backtest_note']}")
            return True
        else:
            print(f"  [FAIL] {variant['name']}  status={resp.status_code}")
            try:
                print(f"         {resp.json()}")
            except Exception:
                pass
            return False
    except requests.ConnectionError:
        print(
            f"  [ERROR] {variant['name']}: API not reachable at {BASE_URL}. "
            "Start the backend with: uvicorn src.api.main:app --reload"
        )
        return False
    except Exception as exc:
        print(f"  [ERROR] {variant['name']}: {exc}")
        return False


def main() -> None:
    """Create all four refined strategy variants."""
    print("=" * 72)
    print("EMA REFINED STRATEGY VARIANTS - A/B COMPARISON SET")
    print("=" * 72)
    print()
    print("Creating 4 variants for comparison backtesting:")
    print("  Baseline  - BTC, 8/20 EMA (benchmark, reproduces ~1.8 Sharpe)")
    print("  Refined A - BTC, 8/26 EMA + tighter ATR stop")
    print("  Refined B - ETH, 8/26 EMA + tighter ATR stop (volatility boost)")
    print("  Refined C - ETH, 5/20 EMA + tighter ATR stop (faster entry)")
    print()

    created = 0
    failed = 0
    for variant in VARIANTS:
        success = create_strategy(variant)
        if success:
            created += 1
        else:
            failed += 1
        print()

    print("=" * 72)
    print(f"RESULT: {created} created, {failed} failed")
    print("=" * 72)
    print(COMPARISON_TABLE)

    if created > 0:
        print("NEXT STEPS:")
        print("  1. Go to http://localhost:3001/backtest")
        print("  2. Run each strategy (settings in comparison table above)")
        print("  3. Fill in the table: Sharpe, PF, Win%, MaxDD, Trades")
        print("  4. Winner = highest Sharpe with MaxDD < 20%")
        print("  5. Re-run winner on 60-day lookback to confirm consistency")
        print("  6. If consistent: deploy to paper trading")
        print()


if __name__ == "__main__":
    main()
