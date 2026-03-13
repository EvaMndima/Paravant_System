#!/usr/bin/env python
"""
Create strategies optimized for different market regimes
Based on the system's available regimes:
- trending_up: Uptrend momentum strategies
- trending_down: Downtrend momentum strategies
- ranging: Mean reversion/range-bound strategies
- volatile: Wide stop-loss protective strategies
- unknown: Conservative strategies
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def create_strategy(name: str, template_id: str, params: dict = None) -> bool:
    """Create a strategy via API"""
    try:
        payload = {
            "name": name,
            "template_id": template_id,
            "description": f"{name}",
        }
        if params:
            payload["parameters"] = params

        response = requests.post(f"{BASE_URL}/strategies", json=payload, timeout=5)
        if response.status_code == 201:
            print(f"  [OK] {name}")
            return True
        else:
            print(f"  [FAIL] {name}")
            return False
    except Exception as e:
        print(f"  [ERROR] {name}: {str(e)[:50]}")
        return False

def main():
    print("=" * 70)
    print("CREATING REGIME-OPTIMIZED STRATEGIES")
    print("=" * 70)
    print("\nMarket Regimes Available:")
    print("  - trending_up: Use momentum/breakout strategies")
    print("  - trending_down: Use trend-following with short bias")
    print("  - ranging: Use mean reversion strategies")
    print("  - volatile: Use wide stops and protective strategies")
    print("  - unknown: Use conservative strategies")

    strategies = [
        # ===== TRENDING UP STRATEGIES =====
        # Use fast EMAs and aggressive entry thresholds
        {
            "name": "Regime_TrendingUp_Fast_Momentum (BTC)",
            "template": "ema_trend_rsi",
            "regime": "trending_up",
            "params": {
                "fast_ema_period": 8,
                "slow_ema_period": 20,
                "rsi_period": 10,
                "rsi_buy_threshold": 35,
                "rsi_sell_threshold": 65,
                "rsi_overbought": 80,
                "rsi_oversold": 20,
                "atr_multiplier": 1.2,
                "atr_period": 10,
            }
        },
        {
            "name": "Regime_TrendingUp_Breakout (ETH)",
            "template": "donchian_atr",
            "regime": "trending_up",
            "params": {}  # Use defaults
        },
        {
            "name": "Regime_TrendingUp_Momentum_MACD (BNB)",
            "template": "macd_pullback",
            "regime": "trending_up",
            "params": {}  # Use defaults
        },
        {
            "name": "Regime_TrendingUp_SupertrendFollow (BTC)",
            "template": "supertrend_volume_macd",
            "regime": "trending_up",
            "params": {}  # Use defaults
        },

        # ===== TRENDING DOWN STRATEGIES =====
        # Use EMA crosses with bearish bias
        {
            "name": "Regime_TrendingDown_Downtrend (BTC)",
            "template": "ema_trend_rsi",
            "regime": "trending_down",
            "params": {
                "fast_ema_period": 10,
                "slow_ema_period": 25,
                "rsi_period": 14,
                "rsi_buy_threshold": 50,
                "rsi_sell_threshold": 50,
                "rsi_overbought": 75,
                "rsi_oversold": 25,
                "atr_multiplier": 1.8,
                "atr_period": 14,
            }
        },
        {
            "name": "Regime_TrendingDown_BreakoutShort (ETH)",
            "template": "donchian_atr",
            "regime": "trending_down",
            "params": {}
        },
        {
            "name": "Regime_TrendingDown_MACDShort (BNB)",
            "template": "macd_pullback",
            "regime": "trending_down",
            "params": {}
        },

        # ===== RANGING STRATEGIES =====
        # Use mean reversion and Bollinger Squeeze
        {
            "name": "Regime_Ranging_MeanReversion_Sensitive (BTC)",
            "template": "rsi_bb_mean_reversion",
            "regime": "ranging",
            "params": {}  # Use aggressive defaults for ranging
        },
        {
            "name": "Regime_Ranging_BBSqueeze_Breakout (ETH)",
            "template": "bb_squeeze_breakout",
            "regime": "ranging",
            "params": {}
        },
        {
            "name": "Regime_Ranging_VWAP_Pullback (BNB)",
            "template": "vwap_pullback_volume",
            "regime": "ranging",
            "params": {}
        },
        {
            "name": "Regime_Ranging_EMA_Conservative (BTC)",
            "template": "ema_trend_rsi",
            "regime": "ranging",
            "params": {
                "fast_ema_period": 20,
                "slow_ema_period": 50,
                "rsi_period": 14,
                "rsi_buy_threshold": 50,
                "rsi_sell_threshold": 50,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "atr_multiplier": 2.0,
                "atr_period": 14,
            }
        },

        # ===== VOLATILE STRATEGIES =====
        # Use wider stops and protective measures
        {
            "name": "Regime_Volatile_Wide_Stops (BTC)",
            "template": "ema_trend_rsi",
            "regime": "volatile",
            "params": {
                "fast_ema_period": 15,
                "slow_ema_period": 40,
                "rsi_period": 16,
                "rsi_buy_threshold": 48,
                "rsi_sell_threshold": 52,
                "rsi_overbought": 75,
                "rsi_oversold": 25,
                "atr_multiplier": 3.0,  # Wider stops for volatility
                "atr_period": 16,
            }
        },
        {
            "name": "Regime_Volatile_Protective_Breakout (ETH)",
            "template": "donchian_atr",
            "regime": "volatile",
            "params": {}
        },
        {
            "name": "Regime_Volatile_Supertrend_Conservative (BNB)",
            "template": "supertrend_volume_macd",
            "regime": "volatile",
            "params": {}
        },

        # ===== UNKNOWN REGIME STRATEGIES =====
        # Use most conservative/balanced approaches
        {
            "name": "Regime_Unknown_Balanced_EMA (BTC)",
            "template": "ema_trend_rsi",
            "regime": "unknown",
            "params": {
                "fast_ema_period": 12,
                "slow_ema_period": 26,
                "rsi_period": 14,
                "rsi_buy_threshold": 45,
                "rsi_sell_threshold": 55,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "atr_multiplier": 2.0,
                "atr_period": 14,
            }
        },
        {
            "name": "Regime_Unknown_Balanced_Donchian (ETH)",
            "template": "donchian_atr",
            "regime": "unknown",
            "params": {}
        },
        {
            "name": "Regime_Unknown_Balanced_MACD (BNB)",
            "template": "macd_pullback",
            "regime": "unknown",
            "params": {}
        },
    ]

    success_count = 0
    total_count = len(strategies)

    print(f"\nCreating {total_count} regime-optimized strategies...\n")

    # Group by regime for better organization
    by_regime = {}
    for strat in strategies:
        regime = strat.get("regime", "unknown")
        if regime not in by_regime:
            by_regime[regime] = []
        by_regime[regime].append(strat)

    # Create strategies organized by regime
    for regime in ["trending_up", "trending_down", "ranging", "volatile", "unknown"]:
        if regime in by_regime:
            print(f"\n[{regime.upper()}]")
            for strat in by_regime[regime]:
                if create_strategy(strat["name"], strat["template"], strat.get("params")):
                    success_count += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"SUMMARY: {success_count}/{total_count} regime-optimized strategies created")
    print("=" * 70)

    # List all strategies
    print("\nAll available strategies (by regime):\n")
    try:
        response = requests.get(f"{BASE_URL}/strategies", timeout=5)
        if response.status_code == 200:
            strategies_list = response.json()

            # Filter to show regime-optimized ones
            regime_strategies = [s for s in strategies_list if "Regime_" in s.get('name', '')]

            print(f"Regime-Optimized Strategies ({len(regime_strategies)} found):\n")
            for regime in ["trending_up", "trending_down", "ranging", "volatile", "unknown"]:
                regime_strats = [s for s in regime_strategies if f"Regime_{regime.title()}" in s.get('name', '') or f"Regime_{regime.replace('_', '').title()}" in s.get('name', '')]
                if regime_strats:
                    print(f"  {regime.upper()}:")
                    for strat in regime_strats:
                        print(f"    - {strat.get('name', 'Unknown')}")

            print(f"\n\nTotal strategies available: {len(strategies_list)}")
    except Exception as e:
        print(f"Error listing strategies: {e}")

    print("\n" + "=" * 70)
    print("BACKTEST RECOMMENDATIONS BY REGIME:")
    print("=" * 70)
    print("""
TRENDING UP:
  Use: Fast momentum strategies (Regime_TrendingUp_*)
  Why: Capitalize on upward momentum with quick entries

TRENDING DOWN:
  Use: Downtrend followers (Regime_TrendingDown_*)
  Why: Follow the trend with defensive positioning

RANGING/SIDEWAYS:
  Use: Mean reversion strategies (Regime_Ranging_*)
  Why: Buy oversold, sell overbought in bounded price action

VOLATILE:
  Use: Wide-stop strategies (Regime_Volatile_*)
  Why: Protect against whipsaws with larger stop-losses

UNKNOWN:
  Use: Balanced strategies (Regime_Unknown_*)
  Why: Safe middle-ground approach until regime is clear
    """)

    print("\nNEXT STEP:")
    print("Open http://localhost:3001/backtest")
    print("Select a regime-optimized strategy and backtest it!")

if __name__ == "__main__":
    main()
