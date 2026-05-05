"""Regime management for PARAVANT — manual tagging and automated detection.

This package unifies two regime systems:

1. Manual regime tagging (from the original regime.py):
   MarketRegime, get_regime, set_regime, get_all_regimes,
   should_reduce_size, get_size_factor

2. Automated regime detection (new — DEC-2026-05-04-001/002):
   RegimeState, RegimeDetector, RegimeRouter

The original regime.py is now shadowed by this package. All its exports
are re-exported from here to preserve backward compatibility with
src.core.strategy.__init__ and any other importers.

Decision: DEC-2026-05-04-001 - Dual-EMA composite 4-state approach
Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule
"""
# Automated detection (new)
from src.core.strategy.regime.detector import RegimeDetector, RegimeState
from src.core.strategy.regime.router import RegimeRouter

# Manual tagging (migrated from regime.py for backward compatibility)
from src.core.strategy.regime.manual import (
    REGIME_MISMATCH_SIZE_FACTOR,
    MarketRegime,
    get_all_regimes,
    get_regime,
    get_size_factor,
    set_regime,
    should_reduce_size,
)

__all__ = [
    # Automated detection
    "RegimeState",
    "RegimeDetector",
    "RegimeRouter",
    # Manual tagging
    "MarketRegime",
    "get_regime",
    "set_regime",
    "get_all_regimes",
    "should_reduce_size",
    "get_size_factor",
    "REGIME_MISMATCH_SIZE_FACTOR",
]
