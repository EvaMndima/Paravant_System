"""Signal generators for strategy templates.

Each generator implements the SignalGenerator ABC and evaluates template-
specific indicator conditions to produce TradingSignal outputs.

Available generators:
    Original (7):
    - EmaTrendRsiGenerator: EMA crossover with RSI filter
    - BbSqueezeBreakoutGenerator: Bollinger Band squeeze breakout
    - MacdPullbackGenerator: MACD trend with pullback entries
    - RsiBbMeanReversionGenerator: RSI + BB mean reversion
    - SupertrendVolumeMacdGenerator: SuperTrend + Volume + MACD confluence
    - DonchianAtrGenerator: Donchian channel breakout with ATR filter
    - VwapPullbackVolumeGenerator: VWAP pullback with volume confirmation

    Bear-Regime Strategies (6):
    - BbSqueezeMomentumGenerator: TTM Squeeze (BB inside KC) breakout
    - IchimokuCloudTrendGenerator: Ichimoku Cloud trend following
    - KeltnerFadeAdxGenerator: Keltner Channel fade with ADX filter
    - BearTrendFollowerGenerator: Multi-TF bear trend follower (1H+4H)
    - RegimeAwareMeanReversionGenerator: Multi-TF regime-aware mean reversion
    - CascadingMomentumFilterGenerator: Triple-TF cascade filter (1H+4H+Daily)

    Bull-Regime Strategies (11):
    - BullTrendPullbackGenerator: Long-only RSI pullback within confirmed bull trend
    - TrendAccelerationMomentumGenerator: EMA spread + volume + ATR acceleration
    - VolatilityRegimeBreakoutGenerator: BB squeeze-release into squeeze-window breakout
    - MultiTfConfluenceGenerator: Daily EMA + 4H MACD + 1H RSI pullback
    - RsiDivergenceReversalGenerator: Price/RSI divergence at confirmed swing pivots
    - EmaRibbonExpansionGenerator: EMA ribbon compression-expansion in bull alignment
    - VolumeBalanceBreakoutGenerator: Up-volume ratio + range breakout confirmation
    - RocMomentumSurgeGenerator: ROC acceleration in RSI 60-75 power zone
    - AdxDirectionalThrustGenerator: ADX rising + +DI/-DI spread dominance
    - KeltnerChannelContinuationGenerator: First close above upper KC in bull regime
    - StochRsiBullCrossGenerator: StochRSI K/D cross from oversold in bull trend
"""
from src.core.strategy.generators.bb_squeeze_breakout import \
    BbSqueezeBreakoutGenerator
from src.core.strategy.generators.bb_squeeze_momentum import \
    BbSqueezeMomentumGenerator
from src.core.strategy.generators.bear_trend_follower import \
    BearTrendFollowerGenerator
from src.core.strategy.generators.cascading_momentum_filter import \
    CascadingMomentumFilterGenerator
from src.core.strategy.generators.donchian_atr import DonchianAtrGenerator
from src.core.strategy.generators.ema_trend_rsi import EmaTrendRsiGenerator
from src.core.strategy.generators.ichimoku_cloud_trend import \
    IchimokuCloudTrendGenerator
from src.core.strategy.generators.keltner_fade_adx import \
    KeltnerFadeAdxGenerator
from src.core.strategy.generators.macd_pullback import MacdPullbackGenerator
from src.core.strategy.generators.regime_aware_mean_reversion import \
    RegimeAwareMeanReversionGenerator
from src.core.strategy.generators.rsi_bb_mean_reversion import \
    RsiBbMeanReversionGenerator
from src.core.strategy.generators.supertrend_volume_macd import \
    SupertrendVolumeMacdGenerator
from src.core.strategy.generators.vwap_pullback_volume import \
    VwapPullbackVolumeGenerator
from src.core.strategy.generators.bull_trend_pullback import \
    BullTrendPullbackGenerator
from src.core.strategy.generators.trend_acceleration_momentum import \
    TrendAccelerationMomentumGenerator
from src.core.strategy.generators.volatility_regime_breakout import \
    VolatilityRegimeBreakoutGenerator
from src.core.strategy.generators.multi_tf_confluence import \
    MultiTfConfluenceGenerator
from src.core.strategy.generators.rsi_divergence_reversal import \
    RsiDivergenceReversalGenerator
from src.core.strategy.generators.ema_ribbon_expansion import \
    EmaRibbonExpansionGenerator
from src.core.strategy.generators.volume_balance_breakout import \
    VolumeBalanceBreakoutGenerator
from src.core.strategy.generators.roc_momentum_surge import \
    RocMomentumSurgeGenerator
from src.core.strategy.generators.adx_directional_thrust import \
    AdxDirectionalThrustGenerator
from src.core.strategy.generators.keltner_channel_continuation import \
    KeltnerChannelContinuationGenerator
from src.core.strategy.generators.stoch_rsi_bull_cross import \
    StochRsiBullCrossGenerator
from src.core.strategy.generators.crypto_wick_reversal import \
    CryptoWickReversalGenerator
from src.core.strategy.generators.obv_trend_divergence import \
    ObvTrendDivergenceGenerator
from src.core.strategy.generators.heikin_ashi_trend_pulse import \
    HeikinAshiTrendPulseGenerator
from src.core.strategy.generators.vpt_momentum import \
    VptMomentumGenerator
from src.core.strategy.generators.realized_vol_compression_breakout import \
    RealizedVolCompressionBreakoutGenerator

__all__ = [
    # Original generators
    "EmaTrendRsiGenerator",
    "BbSqueezeBreakoutGenerator",
    "MacdPullbackGenerator",
    "RsiBbMeanReversionGenerator",
    "SupertrendVolumeMacdGenerator",
    "DonchianAtrGenerator",
    "VwapPullbackVolumeGenerator",
    # Bear-regime generators
    "BbSqueezeMomentumGenerator",
    "IchimokuCloudTrendGenerator",
    "KeltnerFadeAdxGenerator",
    "BearTrendFollowerGenerator",
    "RegimeAwareMeanReversionGenerator",
    "CascadingMomentumFilterGenerator",
    # Bull-regime generators
    "BullTrendPullbackGenerator",
    "TrendAccelerationMomentumGenerator",
    "VolatilityRegimeBreakoutGenerator",
    "MultiTfConfluenceGenerator",
    "RsiDivergenceReversalGenerator",
    "EmaRibbonExpansionGenerator",
    "VolumeBalanceBreakoutGenerator",
    "RocMomentumSurgeGenerator",
    "AdxDirectionalThrustGenerator",
    "KeltnerChannelContinuationGenerator",
    "StochRsiBullCrossGenerator",
    # Crypto-native bull-regime generators (2026-05-08)
    "CryptoWickReversalGenerator",
    "ObvTrendDivergenceGenerator",
    "HeikinAshiTrendPulseGenerator",
    "VptMomentumGenerator",
    "RealizedVolCompressionBreakoutGenerator",
]
