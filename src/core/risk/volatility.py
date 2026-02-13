"""Volatility regime classification and trading filter.

Classifies market volatility into regimes (LOW, NORMAL, HIGH, EXTREME)
and provides position size multipliers and trading restrictions based
on current volatility levels. Includes a cooldown mechanism that
blocks trading after extreme volatility events.

The analyzer accepts pre-computed volatility_pct (ATR/price * 100)
rather than fetching market data directly, keeping the risk module
sync and free of I/O dependencies.

Decision: DEC-2026-02-12-011 - Accepts pre-computed values
Decision: DEC-2026-02-12-012 - Injectable datetime for testability
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.utils.logging import get_logger

logger = get_logger(__name__)


class VolatilityRegime(str, Enum):
    """Market volatility classification levels.

    Values are ordered from lowest to highest volatility.
    Each regime maps to a position size multiplier.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True)
class VolatilityResult:
    """Immutable result of volatility analysis.

    Attributes:
        regime: Classified volatility regime.
        current_volatility: Input volatility percentage.
        threshold_used: The threshold that determined the regime.
        is_tradeable: Whether trading is allowed at this volatility.
        position_multiplier: Size multiplier (1.0=full, 0.0=no trading).
        message: Human-readable status message.
    """

    regime: VolatilityRegime
    current_volatility: float
    threshold_used: float
    is_tradeable: bool
    position_multiplier: float
    message: str = ""

    def __post_init__(self) -> None:
        """Validate result fields.

        Raises:
            ValueError: If numeric fields are NaN or Infinity.
        """
        if math.isnan(self.current_volatility):
            raise ValueError("current_volatility cannot be NaN")
        if math.isinf(self.current_volatility):
            raise ValueError("current_volatility cannot be Infinity")
        if math.isnan(self.threshold_used):
            raise ValueError("threshold_used cannot be NaN")
        if math.isinf(self.threshold_used):
            raise ValueError("threshold_used cannot be Infinity")
        if math.isnan(self.position_multiplier):
            raise ValueError("position_multiplier cannot be NaN")
        if math.isinf(self.position_multiplier):
            raise ValueError("position_multiplier cannot be Infinity")


# Regime to position size multiplier mapping
_REGIME_MULTIPLIERS: dict[VolatilityRegime, float] = {
    VolatilityRegime.LOW: 1.0,
    VolatilityRegime.NORMAL: 1.0,
    VolatilityRegime.HIGH: 0.5,
    VolatilityRegime.EXTREME: 0.0,
}


class VolatilityAnalyzer:
    """Classifies volatility regimes and applies trading restrictions.

    Thresholds define volatility percentage boundaries:
    - Below normal_threshold: LOW regime (full size)
    - normal_threshold to high_threshold: NORMAL regime (full size)
    - high_threshold to extreme_threshold: HIGH regime (half size)
    - Above extreme_threshold: EXTREME regime (no trading)

    After EXTREME volatility, a cooldown period blocks all trading
    even after volatility normalizes.

    Attributes:
        extreme_threshold: ATR/price % for EXTREME classification.
        high_threshold: ATR/price % for HIGH classification.
        normal_threshold: ATR/price % for NORMAL classification.
        cooldown_minutes: Minutes to block after EXTREME event.
    """

    def __init__(
        self,
        extreme_threshold: float = 5.0,
        high_threshold: float = 3.0,
        normal_threshold: float = 1.0,
        cooldown_minutes: int = 30,
    ) -> None:
        """Initialize the volatility analyzer.

        Args:
            extreme_threshold: ATR/price % above which = EXTREME.
            high_threshold: ATR/price % above which = HIGH.
            normal_threshold: ATR/price % above which = NORMAL.
            cooldown_minutes: Minutes to block after EXTREME event.

        Raises:
            ValueError: If thresholds are not in ascending order.
        """
        if not (0 < normal_threshold < high_threshold < extreme_threshold):
            raise ValueError(
                f"Thresholds must be ascending: "
                f"normal({normal_threshold}) < "
                f"high({high_threshold}) < "
                f"extreme({extreme_threshold})"
            )

        self.extreme_threshold: float = extreme_threshold
        self.high_threshold: float = high_threshold
        self.normal_threshold: float = normal_threshold
        self.cooldown_minutes: int = cooldown_minutes
        self._last_extreme_at: datetime | None = None

    def analyze(
        self,
        volatility_pct: float,
        now: datetime | None = None,
    ) -> VolatilityResult:
        """Analyze volatility and classify into a regime.

        Args:
            volatility_pct: ATR/price * 100 (pre-computed upstream).
            now: Current time (injectable for testing).

        Returns:
            VolatilityResult with regime classification and trading decision.

        Raises:
            ValueError: If volatility_pct is negative, NaN, or Infinity.
        """
        if math.isnan(volatility_pct):
            raise ValueError("volatility_pct cannot be NaN")
        if math.isinf(volatility_pct):
            raise ValueError("volatility_pct cannot be Infinity")
        if volatility_pct < 0:
            raise ValueError(
                f"volatility_pct must be non-negative, got {volatility_pct}"
            )

        now = now or datetime.now(timezone.utc)

        # Classify the regime
        regime = self._classify_regime(volatility_pct)
        multiplier = _REGIME_MULTIPLIERS[regime]

        # Track extreme events for cooldown
        if regime == VolatilityRegime.EXTREME:
            self._last_extreme_at = now

        # Check cooldown (blocks trading even if volatility normalizes)
        in_cooldown = self.is_in_cooldown(now)
        is_tradeable = multiplier > 0.0 and not in_cooldown

        # Build message
        message = ""
        if not is_tradeable:
            if in_cooldown and regime != VolatilityRegime.EXTREME:
                message = (
                    f"Volatility cooldown active "
                    f"(extreme event at "
                    f"{self._last_extreme_at.isoformat() if self._last_extreme_at else 'unknown'})"
                )
            elif regime == VolatilityRegime.EXTREME:
                message = (
                    f"Extreme volatility {volatility_pct:.2f}% "
                    f"(threshold: {self.extreme_threshold:.1f}%)"
                )

        # Determine which threshold was used for classification
        if regime == VolatilityRegime.EXTREME:
            threshold_used = self.extreme_threshold
        elif regime == VolatilityRegime.HIGH:
            threshold_used = self.high_threshold
        elif regime == VolatilityRegime.NORMAL:
            threshold_used = self.normal_threshold
        else:
            threshold_used = self.normal_threshold

        if not is_tradeable:
            # Override multiplier to 0 during cooldown
            multiplier = 0.0

        logger.info(
            "volatility_analyzed",
            volatility_pct=volatility_pct,
            regime=regime.value,
            is_tradeable=is_tradeable,
            position_multiplier=multiplier,
            in_cooldown=in_cooldown,
        )

        return VolatilityResult(
            regime=regime,
            current_volatility=volatility_pct,
            threshold_used=threshold_used,
            is_tradeable=is_tradeable,
            position_multiplier=multiplier,
            message=message,
        )

    def is_in_cooldown(self, now: datetime | None = None) -> bool:
        """Check if the post-extreme-volatility cooldown is active.

        Args:
            now: Current time (injectable for testing).

        Returns:
            True if cooldown is still active.
        """
        if self._last_extreme_at is None:
            return False

        now = now or datetime.now(timezone.utc)
        cooldown_end = self._last_extreme_at + timedelta(
            minutes=self.cooldown_minutes
        )
        return now < cooldown_end

    def _classify_regime(
        self, volatility_pct: float
    ) -> VolatilityRegime:
        """Classify volatility into a regime.

        Args:
            volatility_pct: ATR/price * 100.

        Returns:
            VolatilityRegime classification.
        """
        if volatility_pct >= self.extreme_threshold:
            return VolatilityRegime.EXTREME
        if volatility_pct >= self.high_threshold:
            return VolatilityRegime.HIGH
        if volatility_pct >= self.normal_threshold:
            return VolatilityRegime.NORMAL
        return VolatilityRegime.LOW
