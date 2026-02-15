"""Strategy management module.

Provides the core strategy engine, signal generation framework,
market regime management, similarity detection, and signal generator factory.

Key components:
- StrategyEngine: Lifecycle management and template orchestration
- TradingSignal / SignalGenerator: Signal generation abstractions
- MarketRegime / regime functions: Market regime classification
- SimilarityResult / check_similarity: Strategy duplicate detection
- SignalGeneratorFactory: Template-to-generator mapping
"""
from src.core.strategy.engine import VALID_TRANSITIONS, StrategyEngine
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.regime import (MarketRegime, get_all_regimes,
                                      get_regime, get_size_factor, set_regime,
                                      should_reduce_size)
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.core.strategy.similarity import (ExistingStrategy, SimilarityResult,
                                          StrategyCandidate, check_similarity)

__all__ = [
    # Engine
    "StrategyEngine",
    "VALID_TRANSITIONS",
    # Signals
    "TradingSignal",
    "SignalGenerator",
    # Factory
    "SignalGeneratorFactory",
    # Regime
    "MarketRegime",
    "get_regime",
    "set_regime",
    "get_all_regimes",
    "should_reduce_size",
    "get_size_factor",
    # Similarity
    "SimilarityResult",
    "StrategyCandidate",
    "ExistingStrategy",
    "check_similarity",
]
