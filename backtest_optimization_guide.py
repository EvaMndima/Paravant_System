#!/usr/bin/env python
"""
Backtest Optimization Guide - Regime-Aligned Testing

This script provides a systematic approach to finding and optimizing
the best strategy for paper trading.

Key Insight: 200-day backtests fail because they mix regimes.
Solution: Test each strategy in its optimal regime.
"""

TESTING_STRATEGY = """
================================================================================
SYSTEMATIC BACKTEST & OPTIMIZATION STRATEGY
================================================================================

PHASE 1: QUICK REGIME-ALIGNED TESTING (3-5 days)
================================================================================

Goal: Find top 3 strategies that work best in THEIR designed regimes

STEP 1A: Test Trending Up Strategies
  These work BEST in uptrending markets

  Strategies to test:
  ✓ Regime_TrendingUp_Fast_Momentum (BTC)     - Aggressive, fast entries
  ✓ Regime_TrendingUp_Breakout (ETH)         - Breakout confirmation
  ✓ Regime_TrendingUp_Momentum_MACD (BNB)    - MACD confirmation
  ✓ Regime_TrendingUp_SupertrendFollow (BTC) - Trend follower

  Backtest Settings:
  - Lookback: 30 days
  - Symbol: BTCUSDT (most stable)
  - Timeframe: 1h (good balance of signals)

  Expected: 50%+ win rate in uptrending periods

  → Record TOP PERFORMER


STEP 1B: Test Ranging Strategies
  These work BEST in sideways/consolidating markets

  Strategies to test:
  ✓ Regime_Ranging_MeanReversion_Sensitive (BTC)
  ✓ Regime_Ranging_BBSqueeze_Breakout (ETH)
  ✓ Regime_Ranging_VWAP_Pullback (BNB)
  ✓ Regime_Ranging_EMA_Conservative (BTC)

  Backtest Settings:
  - Lookback: 30 days
  - Symbol: ETHUSDT (more volatile for ranging)
  - Timeframe: 1h

  Expected: 45%+ win rate in ranging periods

  → Record TOP PERFORMER


STEP 1C: Test Volatile Strategies
  These work BEST in choppy/high-volatility markets

  Strategies to test:
  ✓ Regime_Volatile_Wide_Stops (BTC)
  ✓ Regime_Volatile_Protective_Breakout (ETH)
  ✓ Regime_Volatile_Supertrend_Conservative (BNB)

  Backtest Settings:
  - Lookback: 30 days
  - Symbol: BNBUSDT (smaller cap = choppier)
  - Timeframe: 1h

  Expected: 40%+ win rate in volatile periods

  → Record TOP PERFORMER


STEP 1D: Create Comparison Table

  After testing, create a table:

  ┌──────────────────────────────────┬──────────┬───────┬─────────┐
  │ Strategy                          │ Win Rate │ Return│ Sharpe  │
  ├──────────────────────────────────┼──────────┼───────┼─────────┤
  │ TrendingUp_Fast_Momentum (BTC)   │ 62%      │ 8.5%  │ 1.8     │ ← BEST
  │ TrendingUp_Breakout (ETH)        │ 55%      │ 5.2%  │ 1.2     │
  │ Ranging_MeanReversion (BTC)      │ 58%      │ 6.1%  │ 1.5     │ ← BEST
  │ Volatile_Wide_Stops (BTC)        │ 45%      │ 3.8%  │ 0.9     │ ← BEST
  └──────────────────────────────────┴──────────┴───────┴─────────┘

  TOP 3 CANDIDATES:
  1. TrendingUp_Fast_Momentum (62% win rate)
  2. Ranging_MeanReversion (58% win rate)
  3. [Your third choice]


================================================================================
PHASE 2: PARAMETER OPTIMIZATION (1-2 weeks)
================================================================================

Goal: Fine-tune the top 3 candidates to maximize returns

For the TOP PERFORMER (e.g., TrendingUp_Fast_Momentum):

  Current Parameters (from template):
  - fast_ema_period: 8
  - slow_ema_period: 20
  - rsi_period: 10
  - rsi_buy_threshold: 35
  - rsi_sell_threshold: 65

  Optimization Tests:

  TEST A: Adjust EMA periods (tighter/wider)
  ├─ fast_ema: 5, slow_ema: 15   (TIGHTER - more entries)
  ├─ fast_ema: 8, slow_ema: 20   (CURRENT - baseline)
  └─ fast_ema: 12, slow_ema: 30  (WIDER - fewer entries)

  → Record which gives best risk/reward

  TEST B: Adjust RSI thresholds
  ├─ Buy at 30, Sell at 70  (MORE AGGRESSIVE)
  ├─ Buy at 35, Sell at 65  (CURRENT - balanced)
  └─ Buy at 40, Sell at 60  (CONSERVATIVE - fewer trades)

  → Record which gives best Sharpe ratio

  TEST C: Different symbols (BTC, ETH, BNB)
  ├─ BTCUSDT (most liquid)
  ├─ ETHUSDT (more volatile)
  └─ BNBUSDT (trickiest)

  → Record which symbol works best


================================================================================
PHASE 3: VALIDATION (1 week)
================================================================================

Goal: Prove the optimized strategy works CONSISTENTLY

For your final candidate:

  TEST 1: Different lookback periods
  ├─ 30 days:  Does it still work? (Should: YES)
  ├─ 60 days:  Consistent? (Should: YES, maybe slightly lower)
  └─ 90 days:  Still profitable? (Should: YES)

  REQUIREMENT: Win rate should stay >40% across all periods

  TEST 2: Different timeframes
  ├─ 15m: Faster, more trades
  ├─ 1h:  Balanced (your current)
  └─ 4h:  Fewer, bigger trades

  REQUIREMENT: Sharpe ratio >1.0 at minimum

  TEST 3: Forward test (Recent data only)
  ├─ Last 30 days only (most recent market)

  REQUIREMENT: >30% win rate in recent data


================================================================================
PHASE 4: PAPER TRADING PREP (Final)
================================================================================

Once you pass Phase 3 validation:

✅ You have ONE strategy with:
   - 50%+ win rate in optimal regime
   - Consistent performance across periods
   - Validated on recent data

✅ Ready for paper trading:
   1. Deploy to Paper Trading Mode
   2. Run for 2-4 weeks
   3. Monitor real-world performance
   4. Make final tweaks if needed
   5. Consider live trading


================================================================================
QUICK START: TODAY
================================================================================

Do this TODAY (30 minutes):

1. Open backtest page: http://localhost:3001/backtest

2. Test "Regime_TrendingUp_Fast_Momentum (BTC)"
   - Lookback: 30 days
   - Asset: BTCUSDT
   - Timeframe: 1h
   - Initial Capital: 10000

3. Record: Win Rate, Total Return, Sharpe Ratio

4. Test "Regime_Ranging_MeanReversion_Sensitive (BTC)"
   - Same settings

5. Compare results - which is better?

6. Come back and tell me the top performers!


================================================================================
KEY PRINCIPLES
================================================================================

1. TEST REGIME-MATCHED STRATEGIES
   ❌ DON'T: Test all 45 strategies randomly
   ✅ DO: Test each strategy type in its designed regime

2. SHORTER LOOKBACK = FASTER INSIGHTS
   ❌ DON'T: Start with 200-day backtests
   ✅ DO: Start with 30-day, validate with 60-90

3. OPTIMIZE WINNERS, NOT LOSERS
   ❌ DON'T: Try to fix a 25% win rate strategy
   ✅ DO: Take a 55% winner and push it to 65%

4. CONSISTENCY BEATS PEAK PERFORMANCE
   ❌ DON'T: Optimize for one 200-day run
   ✅ DO: Find what works across multiple periods

5. PAPER TRADE BEFORE LIVE
   ❌ DON'T: Go live after one good backtest
   ✅ DO: Paper trade for 2-4 weeks first


================================================================================
"""

if __name__ == "__main__":
    print(TESTING_STRATEGY)
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("""
1. Read this guide carefully
2. Go to http://localhost:3001/backtest
3. Start with the regime-aligned strategies
4. Run your first optimization test
5. Come back with results and we'll optimize together!
    """)
