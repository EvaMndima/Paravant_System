#!/usr/bin/env python
"""Full strategy universe backtest runner.

Fetches 1H OHLCV data from Binance mainnet, runs ALL 17 strategy templates
against an expanded symbol universe, and prints a comparison table with
SUPERVISED threshold pass/fail status.

Usage:
    # Default: all 17 strategies x 2 symbols x 90 days (recommended for bull strategies)
    python scripts/backtest_new_strategies.py

    # Extended: all 17 strategies x 8 symbols x 90 days
    python scripts/backtest_new_strategies.py --extended

    # Custom:
    python scripts/backtest_new_strategies.py --days 60 --symbols BTCUSDT,ETHUSDT,SOLUSDT

    # Bear-regime only (original 6 new strategies):
    python scripts/backtest_new_strategies.py --group bear

    # Original 7 only:
    python scripts/backtest_new_strategies.py --group original

    # Bull-regime only (5 bull strategies):
    python scripts/backtest_new_strategies.py --group bull

Requires:
    - BINANCE_TESTNET=false in .env (mainnet)
    - Valid API keys in .env
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.brokers.binance.client import BinanceClient
from src.core.strategy.backtest import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.backtest.validator import SUPERVISED_THRESHOLDS
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher
from src.utils.logging import get_logger, setup_logging

# Suppress debug/info noise from bar-level simulation logs during backtests
setup_logging(level="WARNING")

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Symbol sets
# ---------------------------------------------------------------------------
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
EXTENDED_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
    "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT",
]

# ---------------------------------------------------------------------------
# Original 7 strategy templates (v1.1 with regime upgrades where applicable)
# ---------------------------------------------------------------------------
ORIGINAL_TEMPLATES: dict[str, dict] = {
    "ema_trend_rsi": {
        # 12/21 pair validated by bull sweep (Sharpe=5.748 on ETH vs 4.163 for 12/26)
        "fast_ema_period": 12,
        "slow_ema_period": 21,
        "rsi_period": 14,
        "rsi_buy_threshold": 45.0,
        "rsi_sell_threshold": 55.0,
        "rsi_overbought": 75.0,
        "rsi_oversold": 25.0,
        "atr_multiplier": 2.0,
        "atr_period": 14,
        "risk_reward_ratio": 2.0,
    },
    "bb_squeeze_breakout": {
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "squeeze_threshold": 0.04,
        "squeeze_lookback": 10,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "volume_threshold": 1.5,
    },
    "macd_pullback": {
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "pullback_ema_period": 21,
        "atr_period": 14,
        # stop=2.5 validated by bull sweep: wider trail survives 1H bar noise
        # without degrading entry selectivity (tol=0.5 kept tight)
        "atr_stop_multiplier": 2.5,
        "risk_reward_ratio": 2.0,
        "pullback_tolerance_pct": 0.5,
        "regime_ema_period": 200,
    },
    "rsi_bb_mean_reversion": {
        "rsi_period": 14,
        "rsi_oversold": 25.0,
        "rsi_overbought": 75.0,
        "rsi_exit_long": 50.0,
        "rsi_exit_short": 50.0,
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "adx_threshold": 25.0,
        "stop_loss_pct": 2.5,
        "ema_regime_period": 200,
    },
    "supertrend_volume_macd": {
        "supertrend_period": 10,
        "supertrend_multiplier": 3.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "volume_ma_period": 20,
        "volume_multiplier": 1.3,
    },
    "donchian_atr": {
        "donchian_period": 20,
        "atr_period": 14,
        "atr_threshold": 0.003,
        "atr_stop_multiplier": 1.5,
        "volume_ma_period": 20,
        "volume_multiplier": 1.2,
        "ema_regime_period": 200,
    },
    "vwap_pullback_volume": {
        "entry_buffer_pct": 0.3,
        "exit_distance_pct": 1.5,
        "volume_ma_period": 20,
        "volume_multiplier": 1.2,
        "exit_volume_threshold": 0.8,
        "rsi_period": 14,
        "stop_loss_pct": 1.5,
    },
}

# ---------------------------------------------------------------------------
# Bear-regime 6 strategy templates (tuned defaults from Phase 4 refinement)
# ---------------------------------------------------------------------------
BEAR_TEMPLATES: dict[str, dict] = {
    "bb_squeeze_momentum": {
        "bb_period": 20,
        "bb_std_dev": 2.5,
        "kc_ema_period": 20,
        "kc_atr_period": 14,
        "kc_multiplier": 1.5,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "volume_threshold": 1.5,
        "supertrend_period": 10,
        "supertrend_multiplier": 3.0,
        "atr_period": 14,
        "time_stop_bars": 20,
    },
    "ichimoku_cloud_trend": {
        "tenkan_period": 20,
        "kijun_period": 60,
        "senkou_b_period": 120,
        "displacement": 30,
        "atr_period": 14,
        "volume_period": 20,
        "volume_threshold": 1.3,
    },
    "keltner_fade_adx": {
        "kc_ema_period": 20,
        "kc_atr_period": 14,
        "kc_multiplier": 2.0,
        "ema_trend_period": 50,
        "ema_slope_lookback": 10,
        "adx_period": 10,
        "adx_max_threshold": 30.0,
        "stoch_rsi_period": 14,
        "stoch_k_smooth": 3,
        "stoch_d_smooth": 3,
        "stoch_overbought": 70.0,
        "stoch_oversold": 30.0,
        "atr_period": 14,
    },
    "bear_trend_follower": {
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
    },
    "regime_aware_mean_reversion": {
        "htf_ema_period": 200,
        "rsi_period": 9,
        "rsi_overbought_bear": 70.0,
        "rsi_oversold_bear": 25.0,
        "rsi_overbought_bull": 75.0,
        "rsi_oversold_bull": 30.0,
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "kc_ema_period": 20,
        "kc_atr_period": 14,
        "kc_multiplier": 2.0,
        "vwap_deviation_pct": 2.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14,
        "time_stop_bars": 12,
    },
    "cascading_momentum_filter": {
        "daily_st_period": 10,
        "daily_st_multiplier": 3.0,
        "htf_ema_period": 21,
        "htf_adx_period": 14,
        "htf_adx_min": 15.0,
        "htf_slope_lookback": 5,
        "st_period_1h": 10,
        "st_multiplier_1h": 3.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14,
    },
}

# ---------------------------------------------------------------------------
# Bull-regime strategy templates (long-only, EMA regime gate)
# ---------------------------------------------------------------------------
BULL_TEMPLATES: dict[str, dict] = {
    "bull_trend_pullback": {
        # htf_ema=150 + rsi_high=60: best combo from sweep (DOGE PF=2.79, Sharpe=4.5, Trades=11)
        # htf_ema=200 produces 0-4 trades; 150 reaches 10-11 trades with quality intact
        "htf_ema_period": 150,
        "trend_ema_period": 50,
        "rsi_period": 14,
        "rsi_pullback_low": 30.0,
        "rsi_pullback_high": 60.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
    },
    "trend_acceleration_momentum": {
        # vol=2.0 + stop=2.5: best combo from sweep (BTC PF=1.38, Sharpe=3.44, Trades=14)
        # vol=1.2 produces PF<1 everywhere; vol=2.0 filters to high-conviction entries only
        "fast_ema_period": 8,
        "slow_ema_period": 21,
        "rsi_period": 14,
        "rsi_bull_min": 50.0,
        "rsi_bull_max": 72.0,
        "volume_period": 20,
        "volume_threshold": 2.0,
        "atr_period": 14,
        "acceleration_lookback": 5,
        "atr_acceleration_lookback": 5,
        "atr_stop_multiplier": 2.5,
        "risk_reward_ratio": 2.5,
        # Regime gate: LONG only above EMA(200), SHORT only below EMA(200)
        "regime_ema_period": 200,
    },
    "volatility_regime_breakout": {
        # EMA(200) regime gate: LONG only above EMA-200 (bull confirmation).
        # Without the gate VRB fires on both directions in mixed regimes —
        # SHORT entries in bull markets hit the WR floor (19-26%) and drag PF below 1.
        # BTC showed edge at 34.5% WR / PF=1.16 with no gate; bull-only gate
        # should raise WR by removing counter-trend short entries.
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "squeeze_lookback": 20,
        "squeeze_percentile": 20.0,
        "reference_lookback": 100,
        "volume_period": 20,
        "volume_threshold": 1.5,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
        "regime_ema_period": 200,
    },
    "multi_tf_confluence": {
        # rsi_min=40/rsi_max=65: best RSI zone from sweep (adds 2-3 trades vs default)
        # 4H MACD-only gate still limits to 15-17 trades in 45d; daily EMA is the true bottleneck
        "daily_ema_period": 21,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "rsi_period": 14,
        "rsi_pullback_min": 40.0,
        "rsi_pullback_max": 65.0,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
    },
    "rsi_divergence_reversal": {
        # Confirmed signal quality (BTC PF=1.57/Sharpe=4.15, AVAX PF=1.35/Sharpe=1.91)
        # Only 4 trades in 45d — needs 90+ day window to accumulate enough for SUPERVISED
        "rsi_period": 14,
        "swing_bars": 5,
        "divergence_lookback": 50,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 3.0,
        # Regime gate: bullish divergence only in bull, bearish only in bear
        "regime_ema_period": 200,
    },
    # --- New bull strategies (2026-05-07) ---
    "ema_ribbon_expansion": {
        # EMA ribbon compression-expansion in bull alignment.
        # Three EMAs (8/21/50): ribbon contracts during pullbacks, expands on resumption.
        # Distinct from VRB (BB width) and BTP (RSI dips) — measures trend momentum geometry.
        # regime_ema_period=200: blocks entries in bear-market relief bounces.
        # ribbon_percentile=10: deeper compression required (vs 25) — only fires when
        #   ribbon is in the lowest 10% of its recent range, not just any dip.
        # ribbon_min_expansion=1.15: expansion must be 15% above recent mean — filters
        #   weak "expansions" that are just noise off the compressed baseline.
        # rsi 50-75: momentum positive (above midline) and not overbought.
        # volume_threshold=1.5: stricter breakout volume confirmation.
        # rr=3.5: wider target to capture the full trend resumption move.
        "fast_ema_period": 8,
        "medium_ema_period": 21,
        "slow_ema_period": 50,
        "ribbon_lookback": 20,
        "ribbon_percentile": 10.0,
        "ribbon_min_expansion": 1.15,
        "volume_period": 20,
        "volume_threshold": 1.5,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 3.5,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 75.0,
    },
    "volume_balance_breakout": {
        # Up-volume ratio + range breakout.
        # balance_threshold=0.60 (loosened from 0.65): original was too strict,
        # only 1-6 trades in 90d. 60% still filters to institutional accumulation.
        # rsi_min/max=40/70: wider zone captures more of the accumulation phase.
        # ema_period=200: EMA-200 trend gate (vs 50) — blocks bear-phase entries.
        # breakout_lookback=10: shorter window = more breakout opportunities.
        "balance_period": 15,
        "balance_threshold": 0.60,
        "breakout_lookback": 10,
        "ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 40.0,
        "rsi_max": 70.0,
        "volume_period": 20,
        "volume_threshold": 1.5,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 3.0,
    },
    "roc_momentum_surge": {
        # ROC acceleration + RSI in 60-78 power zone (widened for more trades).
        # Counter-intuitive: buys "overbought" RSI as bull-strength confirmation.
        # In crypto, RSI 60-78 = mid-bull acceleration, not exhaustion.
        # rsi_bull_min=60 (vs 65): captures earlier stage of power zone.
        # rsi_bull_max=78 (vs 75): captures the top of acceleration before exhaustion.
        # roc_threshold=1.5 (lowered from 2.5): mixed regime has fewer 2.5%+ moves.
        # regime_ema_period=200: blocks dead-cat bounces in macro downtrends.
        # risk_reward_ratio=4.0: high target to benefit from strong momentum runs.
        "roc_period": 5,
        "roc_threshold": 1.5,
        "roc_accel_period": 3,
        "rsi_period": 14,
        "rsi_bull_min": 60.0,
        "rsi_bull_max": 78.0,
        "ema_period": 50,
        "volume_period": 20,
        "volume_threshold": 1.2,
        "atr_period": 14,
        "atr_stop_multiplier": 1.5,
        "risk_reward_ratio": 4.0,
        "regime_ema_period": 200,
    },
}

# New bull strategies for targeted backtest (batch 1: 2026-05-07)
NEW_BULL_TEMPLATES: dict[str, dict] = {
    k: BULL_TEMPLATES[k]
    for k in ["ema_ribbon_expansion", "volume_balance_breakout", "roc_momentum_surge"]
}

# New bull strategies batch 2 (2026-05-08): ADX DI system, KC continuation, StochRSI cross
NEW_BULL2_TEMPLATES: dict[str, dict] = {
    "adx_directional_thrust": {
        # ADX rising + +DI/-DI spread dominance in bull regime.
        # R3: lowered rr 3.0->2.0 (WR 21-35% doesn't sustain 3x ATR targets),
        #     di_min_spread 8->5 (more qualifying bars while still requiring dominance),
        #     adx_rise_bars 3->2 (reduces lag — trend might already be fading by bar 3).
        "adx_period": 14,
        "adx_threshold": 20.0,
        "adx_rise_bars": 2,
        "di_min_spread": 5.0,
        "ema_period": 50,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 45.0,
        "rsi_max": 70.0,
        "volume_period": 20,
        "volume_threshold": 1.3,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.0,
    },
    "keltner_channel_continuation": {
        # First close ABOVE upper KC band in confirmed bull trend.
        # R3: kc_multiplier 1.5->2.0 (wider band = higher-conviction breaks only),
        #     kc_reset_bars 3->5 (longer inside-band window before next breakout),
        #     rr 2.5->3.0 (bigger bands = bigger moves when it does break out).
        "kc_ema_period": 20,
        "kc_atr_period": 14,
        "kc_multiplier": 2.0,
        "kc_reset_bars": 5,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 78.0,
        "volume_period": 20,
        "volume_threshold": 1.5,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 3.0,
    },
    "stoch_rsi_bull_cross": {
        # StochRSI K/D cross from oversold in confirmed bull trend.
        # Detects micro-pullback inflection points faster than RSI(14).
        # stoch_oversold=20: K must reach below 20 in lookback = real pullback.
        # stoch_max=70: K must still be below 70 at cross = not chasing.
        # stoch_lookback=5: checks last 5 bars for the oversold condition.
        # regime_ema_period=200: macro bull gate.
        "rsi_period": 14,
        "stoch_period": 14,
        "smooth_k": 3,
        "smooth_d": 3,
        "stoch_oversold": 20.0,
        "stoch_max": 70.0,
        "stoch_lookback": 5,
        "ema_period": 50,
        "regime_ema_period": 200,
        "rsi_min": 40.0,
        "rsi_max": 70.0,
        "volume_period": 20,
        "volume_threshold": 1.2,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 3.0,
    },
}

# ---------------------------------------------------------------------------
# Template registry — crypto-native bull strategies (2026-05-08 batch 3)
# ---------------------------------------------------------------------------
NEW_BULL3_TEMPLATES: dict[str, dict] = {
    "crypto_wick_reversal": {
        # R3: restore wick_body_ratio 2.0->2.5 (R2 loosening destroyed edge:
        # BTC PF 3.01->0.77; the 2 added trades at 2.0x ratio were both losers).
        # The 2.5x threshold IS the signal definition — smaller wicks are not stop-hunts.
        # volume/rsi kept from R2 (1.4/30-70) — only the wick ratio reverts.
        "wick_body_ratio": 2.5,
        "wick_atr_min": 1.0,
        "ema_period": 50,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 30.0,
        "rsi_max": 70.0,
        "volume_period": 20,
        "volume_threshold": 1.4,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
    },
    "obv_trend_divergence": {
        # R3: divergence logic fix applied in generator (OBV must peak obv_lead_min
        # to obv_lead_max bars BEFORE price breakout, not simultaneously).
        # obv_lead_min=2, obv_lead_max=8 expose the lead-window params to config.
        # Restore volume_threshold 1.2->1.5 and rr 2.0->2.5 (R2 loosening was
        # pre-fix; with correct divergence logic the original params are correct).
        # rsi_min 45->50: divergence + price breakout = mid-momentum, not oversold.
        "obv_period": 20,
        "obv_ema_period": 10,
        "obv_lead_min": 2,
        "obv_lead_max": 8,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 75.0,
        "volume_period": 20,
        "volume_threshold": 1.5,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
    },
    "heikin_ashi_trend_pulse": {
        # R3: one more tightening step on prior-wick count.
        # ha_prior_wick_min 5->6 (require 6 of 7 prior bars with lower wicks —
        # captures deeper, more sustained pullbacks before the no-wick bar).
        # rr 2.5->2.0 (R2 ETH PF=1.32/Sharpe=1.165 with 2.5x was barely under 1.35;
        # 2.0x target is more consistent with 1H HA trend pulse move size).
        "ha_wick_lookback": 7,
        "ha_prior_wick_min": 6,
        "wick_tolerance": 0.05,
        "ema_period": 50,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 75.0,
        "volume_period": 20,
        "volume_threshold": 1.4,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.0,
    },
    "vpt_momentum": {
        # R3: restore exact R1 params (R2 loosening dropped BTC PF 1.42->1.21;
        # DOGE was identical across both rounds = confirmed stable signal).
        # contrib_threshold 1.3->1.5 and volume_threshold 1.1->1.3 both revert.
        # Loosening added marginal-quality VPT bars that diluted the edge.
        "vpt_ema_period": 20,
        "vpt_lookback": 15,
        "vpt_contrib_period": 20,
        "vpt_contrib_threshold": 1.5,
        "ema_period": 50,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 75.0,
        "volume_period": 20,
        "volume_threshold": 1.3,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
    },
    "realized_vol_compression_breakout": {
        # R3: hold R2 params unchanged — testing stability of ETH PF=1.42 and
        # AVAX PF=4.32 signals. If results repeat, the signal is real.
        # If they diverge, the R2 result was lucky (4-6 trade sample is thin).
        "hv_short_period": 20,
        "hv_medium_period": 60,
        "hv_compression_ratio": 0.65,
        "hv_min_compression_bars": 3,
        "breakout_lookback": 20,
        "regime_ema_period": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 78.0,
        "volume_period": 20,
        "volume_threshold": 1.3,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "risk_reward_ratio": 2.5,
    },
}

# ---------------------------------------------------------------------------
# Combined template registry + short labels
# ---------------------------------------------------------------------------
ALL_TEMPLATES: dict[str, dict] = {
    **ORIGINAL_TEMPLATES, **BEAR_TEMPLATES, **BULL_TEMPLATES,
    **NEW_BULL2_TEMPLATES, **NEW_BULL3_TEMPLATES,
}

LABELS: dict[str, str] = {
    # Original 7
    "ema_trend_rsi": "EMA_RSI",
    "bb_squeeze_breakout": "BB_SQZ",
    "macd_pullback": "MACD_PB",
    "rsi_bb_mean_reversion": "RSI_BB",
    "supertrend_volume_macd": "ST_MACD",
    "donchian_atr": "DONCH",
    "vwap_pullback_volume": "VWAP_PB",
    # Bear-regime 6
    "bb_squeeze_momentum": "BSMB",
    "ichimoku_cloud_trend": "ICVP",
    "keltner_fade_adx": "KFA",
    "bear_trend_follower": "BTF",
    "regime_aware_mean_reversion": "RAMR",
    "cascading_momentum_filter": "CMF",
    # Bull-regime 8
    "bull_trend_pullback": "BTP",
    "trend_acceleration_momentum": "TAM",
    "volatility_regime_breakout": "VRB",
    "multi_tf_confluence": "MTC",
    "rsi_divergence_reversal": "RDR",
    "ema_ribbon_expansion": "EREE",
    "volume_balance_breakout": "VBB",
    "roc_momentum_surge": "RMS",
    # Bull-regime batch 2
    "adx_directional_thrust": "ADT",
    "keltner_channel_continuation": "KCC",
    "stoch_rsi_bull_cross": "SRC",
    # Crypto-native bull-regime batch 3
    "crypto_wick_reversal": "CWR",
    "obv_trend_divergence": "OBV_TD",
    "heikin_ashi_trend_pulse": "HATP",
    "vpt_momentum": "VPT",
    "realized_vol_compression_breakout": "RVCB",
}


async def fetch_data(
    symbols: list[str],
    days: int,
) -> dict[str, any]:
    """Fetch historical 1H OHLCV data from Binance mainnet.

    Args:
        symbols: List of trading symbols.
        days: Number of days of history to fetch.

    Returns:
        Dict mapping symbol -> OHLCVSeries.
    """
    client = BinanceClient(testnet=False)
    fetcher = MarketDataFetcher(client)

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    data = {}
    for symbol in symbols:
        print(f"  Fetching {symbol} 1H data ({days}d)...", end=" ", flush=True)
        try:
            series = await fetcher.fetch_historical_ohlcv(
                symbol=symbol,
                timeframe="1h",
                start_date=start_date,
                end_date=end_date,
            )
            print(f"{len(series)} bars")
            data[symbol] = series
        except Exception as e:
            print(f"FAILED: {e}")
            logger.error("fetch_failed", symbol=symbol, error=str(e))

    return data


def run_single_backtest(
    template_id: str,
    params: dict,
    symbol: str,
    series: any,
    factory: SignalGeneratorFactory,
    config: BacktestConfig,
) -> dict:
    """Run a single backtest and return results dict.

    Args:
        template_id: Strategy template ID.
        params: Strategy parameters.
        symbol: Trading symbol.
        series: OHLCV data.
        factory: Signal generator factory.
        config: Backtest configuration.

    Returns:
        Dict with metrics and pass/fail status.
    """
    engine = BacktestEngine(factory)

    # Create a duck-typed strategy object (no DB needed)
    strategy = SimpleNamespace(
        id=f"bt_{template_id}_{symbol}",
        name=f"{LABELS.get(template_id, template_id)} {symbol}",
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
            "status": "ok",
            "trades": m.total_trades,
            "win_rate": m.win_rate_pct,
            "sharpe": m.sharpe_ratio,
            "profit_factor": m.profit_factor,
            "max_dd": m.max_drawdown_pct,
            "total_return": m.total_return_pct,
            "expectancy": m.expectancy,
            "avg_duration_h": m.avg_trade_duration_hours,
            "passed": result.passed_validation,
            "errors": result.validation_errors,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "trades": 0,
            "win_rate": 0.0,
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "max_dd": 0.0,
            "total_return": 0.0,
            "expectancy": 0.0,
            "avg_duration_h": 0.0,
            "passed": False,
            "errors": [str(e)],
        }


def print_results_table(
    results: dict[str, dict[str, dict]],
    templates: dict[str, dict],
    symbols: list[str],
) -> None:
    """Print formatted comparison table of all backtest results.

    Args:
        results: Nested dict: template_id -> symbol -> result dict.
        templates: Template dict used for iteration order.
        symbols: List of symbols tested.
    """
    print("\n" + "=" * 90)
    print("SUPERVISED Thresholds: Sharpe>=0.5  PF>=1.35  Trades>=30  DD<=25%  Exp>$0")
    print("=" * 90)

    header = f"{'Strategy':<8} {'Symbol':<9} {'Trades':>7} {'WR%':>7} {'Sharpe':>7} "
    header += f"{'PF':>7} {'DD%':>7} {'Ret%':>8} {'Exp$':>8} {'Pass':>6}"
    print(header)
    print("-" * 90)

    pass_count = 0
    total_count = 0

    for tid in templates:
        label = LABELS.get(tid, tid[:8])
        for sym in symbols:
            r = results.get(tid, {}).get(sym, {})
            if not r:
                continue
            total_count += 1

            if r.get("status") == "error":
                print(f"{label:<8} {sym:<9} {'ERROR':>7} -- {r.get('error', '')[:50]}")
                continue

            passed = r.get("passed", False)
            if passed:
                pass_count += 1
                mark = "PASS"
            else:
                mark = "FAIL"

            print(
                f"{label:<8} {sym:<9} "
                f"{r.get('trades', 0):>7d} "
                f"{r.get('win_rate', 0):>6.1f}% "
                f"{r.get('sharpe', 0):>7.3f} "
                f"{r.get('profit_factor', 0):>7.2f} "
                f"{r.get('max_dd', 0):>6.1f}% "
                f"{r.get('total_return', 0):>7.2f}% "
                f"{r.get('expectancy', 0):>7.2f}$ "
                f"{mark:>6}"
            )

    print("-" * 90)
    print(f"Results: {pass_count}/{total_count} passed SUPERVISED thresholds")
    print("=" * 90)

    # Promotion recommendations
    print("\nPromotion Recommendations:")
    for tid in templates:
        label = LABELS.get(tid, tid[:8])
        passes_any = False
        for sym in symbols:
            r = results.get(tid, {}).get(sym, {})
            if r.get("passed"):
                passes_any = True
                print(f"  [PROMOTE] {label} on {sym} -> SIMULATED_PAPER")
        if not passes_any:
            best_pf = 0.0
            best_sym = ""
            for sym in symbols:
                r = results.get(tid, {}).get(sym, {})
                pf = r.get("profit_factor", 0)
                if pf > best_pf:
                    best_pf = pf
                    best_sym = sym
            if best_pf > 1.0:
                print(
                    f"  [TUNE]    {label} on {best_sym} (PF={best_pf:.2f}) "
                    f"-- promising, needs parameter tuning"
                )
            else:
                print(f"  [DEFER]   {label} -- no edge detected in current regime")


async def main() -> None:
    """Main entry point: fetch data, run backtests, print results."""
    parser = argparse.ArgumentParser(
        description="PARAVANT full strategy universe backtest runner",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days of historical data (default: 90)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbols (overrides --extended)",
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Use extended 8-symbol universe (BTC,ETH,BNB,SOL,XRP,AVAX,DOGE,DOT)",
    )
    parser.add_argument(
        "--group",
        type=str,
        choices=["all", "original", "bear", "bull", "new_bull", "new_bull2", "new_bull3"],
        default="all",
        help="Strategy group: all, original (7), bear (6), bull (8), new_bull, new_bull2 (3), new_bull3 (5 crypto-native)",
    )
    args = parser.parse_args()

    # Determine symbols
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    elif args.extended:
        symbols = EXTENDED_SYMBOLS
    else:
        symbols = DEFAULT_SYMBOLS

    # Determine strategy group
    if args.group == "original":
        templates = ORIGINAL_TEMPLATES
    elif args.group == "bear":
        templates = BEAR_TEMPLATES
    elif args.group == "bull":
        templates = BULL_TEMPLATES
    elif args.group == "new_bull":
        templates = NEW_BULL_TEMPLATES
    elif args.group == "new_bull2":
        templates = NEW_BULL2_TEMPLATES
    elif args.group == "new_bull3":
        templates = NEW_BULL3_TEMPLATES
    else:
        templates = ALL_TEMPLATES

    days = args.days

    print(f"\nPARAVANT Strategy Universe Backtest Runner")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Data: {days} days, Symbols: {', '.join(symbols)}")
    print(f"Strategies: {len(templates)} templates ({args.group})")
    print(f"Total runs: {len(templates) * len(symbols)}")
    print()

    # --- Fetch Data ---
    print("Fetching mainnet data...")
    data = await fetch_data(symbols, days)
    # Remove symbols that failed to fetch
    symbols = [s for s in symbols if s in data]
    if not symbols:
        print("ERROR: No data fetched. Check API keys and network.")
        return
    print(f"Data ready: {len(symbols)} symbols\n")

    # --- Run Backtests ---
    factory = SignalGeneratorFactory()
    config = BacktestConfig(
        initial_capital=10_000.0,
        commission_rate=0.001,   # 0.1% taker fee
        slippage_rate=0.0005,    # 0.05% slippage
    )

    results: dict[str, dict[str, dict]] = {}
    total = len(templates) * len(symbols)
    count = 0

    for tid, params in templates.items():
        label = LABELS.get(tid, tid)
        results[tid] = {}

        for sym in symbols:
            count += 1
            series = data[sym]
            print(
                f"  [{count}/{total}] {label} x {sym} "
                f"({len(series)} bars)...",
                end=" ",
                flush=True,
            )

            r = run_single_backtest(
                template_id=tid,
                params=params,
                symbol=sym,
                series=series,
                factory=factory,
                config=config,
            )
            results[tid][sym] = r

            if r["status"] == "ok":
                print(
                    f"Trades={r['trades']}, "
                    f"Sharpe={r['sharpe']:.3f}, "
                    f"PF={r['profit_factor']:.2f}"
                )
            else:
                print(f"ERROR: {r.get('error', 'unknown')[:60]}")

    # --- Print Results ---
    print_results_table(results, templates, symbols)


if __name__ == "__main__":
    asyncio.run(main())
