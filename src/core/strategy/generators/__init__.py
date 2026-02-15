"""Signal generators for strategy templates.

Each generator implements the SignalGenerator ABC and evaluates template-
specific indicator conditions to produce TradingSignal outputs.

Available generators:
- EmaTrendRsiGenerator: EMA crossover with RSI filter
- BbSqueezeBreakoutGenerator: Bollinger Band squeeze breakout
- MacdPullbackGenerator: MACD trend with pullback entries
- RsiBbMeanReversionGenerator: RSI + BB mean reversion
- SupertrendVolumeMacdGenerator: SuperTrend + Volume + MACD confluence
- DonchianAtrGenerator: Donchian channel breakout with ATR filter
- VwapPullbackVolumeGenerator: VWAP pullback with volume confirmation
"""
from src.core.strategy.generators.bb_squeeze_breakout import \
    BbSqueezeBreakoutGenerator
from src.core.strategy.generators.donchian_atr import DonchianAtrGenerator
from src.core.strategy.generators.ema_trend_rsi import EmaTrendRsiGenerator
from src.core.strategy.generators.macd_pullback import MacdPullbackGenerator
from src.core.strategy.generators.rsi_bb_mean_reversion import \
    RsiBbMeanReversionGenerator
from src.core.strategy.generators.supertrend_volume_macd import \
    SupertrendVolumeMacdGenerator
from src.core.strategy.generators.vwap_pullback_volume import \
    VwapPullbackVolumeGenerator

__all__ = [
    "EmaTrendRsiGenerator",
    "BbSqueezeBreakoutGenerator",
    "MacdPullbackGenerator",
    "RsiBbMeanReversionGenerator",
    "SupertrendVolumeMacdGenerator",
    "DonchianAtrGenerator",
    "VwapPullbackVolumeGenerator",
]
