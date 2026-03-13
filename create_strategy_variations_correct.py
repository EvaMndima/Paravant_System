#!/usr/bin/env python
"""
Create multiple strategy variations with CORRECT parameters
"""
import requests

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

        response = requests.post(f"{BASE_URL}/strategies", json=payload)
        if response.status_code == 201:
            print(f"  [OK] {name}")
            return True
        else:
            error = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            if isinstance(error, dict) and 'detail' in error:
                error_msg = error.get('detail', {})
                if isinstance(error_msg, dict):
                    msg = error_msg.get('message', str(error_msg))[:100]
                else:
                    msg = str(error_msg)[:100]
                print(f"  [FAIL] {name}: {msg}")
            else:
                print(f"  [FAIL] {name}")
            return False
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        return False

def main():
    print("=" * 70)
    print("CREATING STRATEGY VARIATIONS WITH CORRECT PARAMETERS")
    print("=" * 70)

    strategies = [
        # EMA Trend RSI variations (uses template defaults if no params)
        {
            "name": "EMA Fast Aggressive (BTC)",
            "template": "ema_trend_rsi",
            "params": {
                "fast_ema_period": 8,
                "slow_ema_period": 18,
                "rsi_period": 10,
                "rsi_buy_threshold": 40,
                "rsi_sell_threshold": 60,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "atr_multiplier": 1.5,
                "atr_period": 10,
            }
        },
        {
            "name": "EMA Medium Conservative (BTC)",
            "template": "ema_trend_rsi",
            "params": {
                "fast_ema_period": 15,
                "slow_ema_period": 40,
                "rsi_period": 14,
                "rsi_buy_threshold": 50,
                "rsi_sell_threshold": 50,
                "rsi_overbought": 75,
                "rsi_oversold": 25,
                "atr_multiplier": 2.0,
                "atr_period": 14,
            }
        },
        {
            "name": "EMA Slow Long-term (BTC)",
            "template": "ema_trend_rsi",
            "params": {
                "fast_ema_period": 30,
                "slow_ema_period": 80,
                "rsi_period": 20,
                "rsi_buy_threshold": 45,
                "rsi_sell_threshold": 55,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "atr_multiplier": 2.5,
                "atr_period": 20,
            }
        },
        {
            "name": "EMA Breakout Style (ETH)",
            "template": "ema_trend_rsi",
            "params": {
                "fast_ema_period": 10,
                "slow_ema_period": 30,
                "rsi_period": 7,
                "rsi_buy_threshold": 35,
                "rsi_sell_threshold": 65,
                "rsi_overbought": 80,
                "rsi_oversold": 20,
                "atr_multiplier": 1.8,
                "atr_period": 12,
            }
        },
        {
            "name": "EMA Scalp Quick (BNB)",
            "template": "ema_trend_rsi",
            "params": {
                "fast_ema_period": 5,
                "slow_ema_period": 12,
                "rsi_period": 7,
                "rsi_buy_threshold": 40,
                "rsi_sell_threshold": 60,
                "rsi_overbought": 75,
                "rsi_oversold": 25,
                "atr_multiplier": 1.2,
                "atr_period": 7,
            }
        },

        # Donchian ATR variations
        {
            "name": "Donchian Breakout Conservative (BTC)",
            "template": "donchian_atr",
        },
        {
            "name": "Donchian Breakout Aggressive (ETH)",
            "template": "donchian_atr",
        },
        {
            "name": "Donchian Scalp (BNB)",
            "template": "donchian_atr",
        },

        # Bollinger Squeeze variations
        {
            "name": "BB Squeeze Tight (BTC)",
            "template": "bb_squeeze_breakout",
        },
        {
            "name": "BB Squeeze Wide (ETH)",
            "template": "bb_squeeze_breakout",
        },
        {
            "name": "BB Squeeze Medium (BNB)",
            "template": "bb_squeeze_breakout",
        },

        # MACD Pullback variations
        {
            "name": "MACD Fast Pullback (BTC)",
            "template": "macd_pullback",
        },
        {
            "name": "MACD Standard Pullback (ETH)",
            "template": "macd_pullback",
        },
        {
            "name": "MACD Slow Pullback (BNB)",
            "template": "macd_pullback",
        },

        # RSI BB Mean Reversion variations
        {
            "name": "RSI MR Sensitive (BTC)",
            "template": "rsi_bb_mean_reversion",
        },
        {
            "name": "RSI MR Balanced (ETH)",
            "template": "rsi_bb_mean_reversion",
        },
        {
            "name": "RSI MR Conservative (BNB)",
            "template": "rsi_bb_mean_reversion",
        },

        # Supertrend Volume MACD variations
        {
            "name": "Supertrend Fast (BTC)",
            "template": "supertrend_volume_macd",
        },
        {
            "name": "Supertrend Medium (ETH)",
            "template": "supertrend_volume_macd",
        },
        {
            "name": "Supertrend Slow (BNB)",
            "template": "supertrend_volume_macd",
        },

        # VWAP Pullback Volume variations
        {
            "name": "VWAP Pullback Scalp (BTC)",
            "template": "vwap_pullback_volume",
        },
        {
            "name": "VWAP Pullback Swing (ETH)",
            "template": "vwap_pullback_volume",
        },
        {
            "name": "VWAP Pullback Trend (BNB)",
            "template": "vwap_pullback_volume",
        },
    ]

    success_count = 0
    total_count = len(strategies)

    print(f"\nCreating {total_count} strategy variations...\n")

    for strat in strategies:
        if create_strategy(strat["name"], strat["template"], strat.get("params")):
            success_count += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"SUMMARY: {success_count}/{total_count} strategies created successfully")
    print("=" * 70)

    # List all strategies
    print("\nAll available strategies for backtesting:\n")
    try:
        response = requests.get(f"{BASE_URL}/strategies")
        if response.status_code == 200:
            strategies_list = response.json()
            for i, strat in enumerate(strategies_list, 1):
                template = strat.get('template_id', 'unknown')
                print(f"  {i:2d}. {strat.get('name', 'Unknown'):40s} | {template:25s}")
        print(f"\nTotal: {len(strategies_list)} strategies available for backtesting")
    except Exception as e:
        print(f"Error listing strategies: {e}")

    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Open http://localhost:3001/backtest")
    print("2. Select a strategy from the dropdown")
    print("3. Choose an asset (BTCUSDT, ETHUSDT, BNBUSDT)")
    print("4. Set lookback period (30-90 days)")
    print("5. Click 'Run Backtest'")
    print("6. Review results (return %, win rate, max drawdown, etc.)")

if __name__ == "__main__":
    main()
