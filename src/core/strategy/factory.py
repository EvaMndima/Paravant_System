"""Signal generator factory for mapping template IDs to generators.

Provides a registry-based factory that maps template_id strings to
their corresponding SignalGenerator implementations. New generators
can be registered at runtime.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from src.core.exceptions import TemplateNotFoundError
from src.core.strategy.generators import (AdxDirectionalThrustGenerator,
                                          BbSqueezeBreakoutGenerator,
                                          BbSqueezeMomentumGenerator,
                                          BearTrendFollowerGenerator,
                                          BullTrendPullbackGenerator,
                                          CascadingMomentumFilterGenerator,
                                          CryptoWickReversalGenerator,
                                          DonchianAtrGenerator,
                                          EmaRibbonExpansionGenerator,
                                          EmaTrendRsiGenerator,
                                          HeikinAshiTrendPulseGenerator,
                                          IchimokuCloudTrendGenerator,
                                          KeltnerChannelContinuationGenerator,
                                          KeltnerFadeAdxGenerator,
                                          MacdPullbackGenerator,
                                          MultiTfConfluenceGenerator,
                                          ObvTrendDivergenceGenerator,
                                          RealizedVolCompressionBreakoutGenerator,
                                          RegimeAwareMeanReversionGenerator,
                                          RocMomentumSurgeGenerator,
                                          RsiBbMeanReversionGenerator,
                                          RsiDivergenceReversalGenerator,
                                          StochRsiBullCrossGenerator,
                                          SupertrendVolumeMacdGenerator,
                                          TrendAccelerationMomentumGenerator,
                                          VolatilityRegimeBreakoutGenerator,
                                          VolumeBalanceBreakoutGenerator,
                                          VptMomentumGenerator,
                                          VwapPullbackVolumeGenerator)
from src.core.strategy.signals import SignalGenerator
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Default generator registry mapping template_id -> generator class
_DEFAULT_GENERATORS: dict[str, type[SignalGenerator]] = {
    "ema_trend_rsi": EmaTrendRsiGenerator,
    "bb_squeeze_breakout": BbSqueezeBreakoutGenerator,
    "macd_pullback": MacdPullbackGenerator,
    "rsi_bb_mean_reversion": RsiBbMeanReversionGenerator,
    "supertrend_volume_macd": SupertrendVolumeMacdGenerator,
    "donchian_atr": DonchianAtrGenerator,
    "vwap_pullback_volume": VwapPullbackVolumeGenerator,
    # Bear-regime strategies
    "bb_squeeze_momentum": BbSqueezeMomentumGenerator,
    "ichimoku_cloud_trend": IchimokuCloudTrendGenerator,
    "keltner_fade_adx": KeltnerFadeAdxGenerator,
    "bear_trend_follower": BearTrendFollowerGenerator,
    "regime_aware_mean_reversion": RegimeAwareMeanReversionGenerator,
    "cascading_momentum_filter": CascadingMomentumFilterGenerator,
    # Bull-regime strategies
    "bull_trend_pullback": BullTrendPullbackGenerator,
    "trend_acceleration_momentum": TrendAccelerationMomentumGenerator,
    "volatility_regime_breakout": VolatilityRegimeBreakoutGenerator,
    "multi_tf_confluence": MultiTfConfluenceGenerator,
    "rsi_divergence_reversal": RsiDivergenceReversalGenerator,
    # New bull-regime strategies (2026-05-07/08)
    "ema_ribbon_expansion": EmaRibbonExpansionGenerator,
    "volume_balance_breakout": VolumeBalanceBreakoutGenerator,
    "roc_momentum_surge": RocMomentumSurgeGenerator,
    # New bull-regime strategies (2026-05-08 batch 2)
    "adx_directional_thrust": AdxDirectionalThrustGenerator,
    "keltner_channel_continuation": KeltnerChannelContinuationGenerator,
    "stoch_rsi_bull_cross": StochRsiBullCrossGenerator,
    # Crypto-native bull-regime strategies (2026-05-08 batch 3)
    "crypto_wick_reversal": CryptoWickReversalGenerator,
    "obv_trend_divergence": ObvTrendDivergenceGenerator,
    "heikin_ashi_trend_pulse": HeikinAshiTrendPulseGenerator,
    "vpt_momentum": VptMomentumGenerator,
    "realized_vol_compression_breakout": RealizedVolCompressionBreakoutGenerator,
}


class SignalGeneratorFactory:
    """Factory for creating signal generators by template ID.

    Maintains a registry of template_id -> SignalGenerator class mappings.
    Pre-populated with all built-in generators; custom generators can be
    registered at runtime.

    Example:
        >>> factory = SignalGeneratorFactory()
        >>> generator = factory.get_generator("ema_trend_rsi")
        >>> signal = generator.generate(series, params, "BTCUSDT")
    """

    def __init__(self) -> None:
        """Initialize factory with default generator registry."""
        self._registry: dict[str, type[SignalGenerator]] = dict(_DEFAULT_GENERATORS)

    def get_generator(self, template_id: str) -> SignalGenerator:
        """Create and return a signal generator for the given template ID.

        Args:
            template_id: The strategy template identifier.

        Returns:
            An instance of the corresponding SignalGenerator.

        Raises:
            TemplateNotFoundError: If no generator is registered for the ID.
        """
        generator_class = self._registry.get(template_id)
        if generator_class is None:
            raise TemplateNotFoundError(template_id)

        return generator_class()

    def register_generator(
        self,
        template_id: str,
        generator_class: type[SignalGenerator],
    ) -> None:
        """Register a custom signal generator for a template ID.

        Args:
            template_id: The template identifier to map.
            generator_class: The SignalGenerator subclass to register.

        Raises:
            ValueError: If template_id is empty or generator_class is invalid.
        """
        if not template_id or not template_id.strip():
            raise ValueError("Template ID cannot be empty")

        if not (isinstance(generator_class, type) and issubclass(generator_class, SignalGenerator)):
            raise ValueError(
                f"generator_class must be a SignalGenerator subclass, "
                f"got {type(generator_class).__name__}"
            )

        self._registry[template_id] = generator_class
        logger.info(
            "generator_registered",
            template_id=template_id,
            generator_class=generator_class.__name__,
        )

    def list_template_ids(self) -> list[str]:
        """List all registered template IDs.

        Returns:
            Sorted list of registered template ID strings.
        """
        return sorted(self._registry.keys())

    def has_generator(self, template_id: str) -> bool:
        """Check if a generator is registered for the given template ID.

        Args:
            template_id: Template identifier to check.

        Returns:
            True if a generator is registered.
        """
        return template_id in self._registry
