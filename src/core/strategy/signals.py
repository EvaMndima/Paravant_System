"""Signal generation interfaces for strategy templates.

Defines the TradingSignal output dataclass and the SignalGenerator abstract
base class that all template-specific generators must implement.

IMPORTANT: ``TradingSignal`` is the signal generation output dataclass.
It is NOT the same as ``src.data.models.signal.Signal`` (the database model).
TradingSignal is created by generators and later persisted as a Signal DB row.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class TradingSignal:
    """Immutable signal output from a signal generator.

    Represents a trading signal produced by evaluating indicator conditions
    against an OHLCVSeries. This is a value object - once created, it cannot
    be modified. Downstream consumers convert this into a Signal DB model row.

    Attributes:
        direction: Signal direction (LONG, SHORT, or CLOSE).
        symbol: Trading pair symbol (e.g., ``BTCUSDT``).
        price: Price at signal time (close of the evaluated bar).
        timestamp: Timezone-aware UTC timestamp of signal generation.
        strength: Signal confidence between 0.0 and 1.0. Higher values
            indicate stronger confluence of indicators.
        stop_loss: Suggested stop loss price (optional).
        take_profit: Suggested take profit price (optional).
        indicators: Snapshot of indicator values at signal time.
        metadata: Additional generator-specific context.
    """

    direction: SignalDirection
    symbol: str
    price: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strength: float = 0.5
    stop_loss: float | None = None
    take_profit: float | None = None
    indicators: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate signal fields after initialization.

        Raises:
            ValueError: If any field has an invalid value.
        """
        if not self.symbol or not self.symbol.strip():
            raise ValueError("TradingSignal symbol cannot be empty")

        if math.isnan(self.price) or math.isinf(self.price):
            raise ValueError(
                f"TradingSignal price must be finite, got {self.price}"
            )
        if self.price <= 0:
            raise ValueError(
                f"TradingSignal price must be positive, got {self.price}"
            )

        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                f"TradingSignal strength must be in [0.0, 1.0], got {self.strength}"
            )

        if self.timestamp.tzinfo is None:
            raise ValueError("TradingSignal timestamp must be timezone-aware")

        # Validate optional stop_loss / take_profit
        for name, val in [("stop_loss", self.stop_loss), ("take_profit", self.take_profit)]:
            if val is not None:
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(f"TradingSignal {name} must be finite, got {val}")
                if val <= 0:
                    raise ValueError(f"TradingSignal {name} must be positive, got {val}")


class SignalGenerator(ABC):
    """Abstract base class for template-specific signal generators.

    Each strategy template (e.g., ``ema_trend_rsi``) has a corresponding
    SignalGenerator subclass that evaluates indicator conditions against
    an OHLCVSeries and optionally produces a TradingSignal.

    Generators are stateless - each ``generate()`` call is independent.
    The generator receives pre-validated parameters from the StrategyEngine.

    Example:
        >>> generator = EmaTrendRsiGenerator()
        >>> params = {"fast_ema_period": 12, "slow_ema_period": 26, ...}
        >>> signal = generator.generate(series, params, "BTCUSDT")
        >>> if signal is not None:
        ...     print(f"Signal: {signal.direction} at {signal.price}")
    """

    @abstractmethod
    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate indicators and optionally produce a trading signal.

        Args:
            series: OHLCV series for the target symbol and timeframe.
            params: Validated strategy parameters from the template.
            symbol: Trading pair symbol (e.g., ``BTCUSDT``).

        Returns:
            TradingSignal if conditions are met, None otherwise.

        Raises:
            SignalGenerationError: If indicator calculation fails.
            ValueError: If series has insufficient data.
        """

    def validate_series(
        self,
        series: OHLCVSeries,
        min_bars: int,
    ) -> bool:
        """Check if series has enough data for signal generation.

        Args:
            series: OHLCV series to validate.
            min_bars: Minimum number of bars required.

        Returns:
            True if series has sufficient data.
        """
        if len(series) < min_bars:
            logger.debug(
                "insufficient_data_for_signal",
                available_bars=len(series),
                required_bars=min_bars,
                generator=self.__class__.__name__,
            )
            return False
        return True

    @property
    @abstractmethod
    def template_id(self) -> str:
        """Return the template ID this generator handles.

        Returns:
            Template identifier string matching a YAML template file.
        """

    @property
    @abstractmethod
    def min_bars_required(self) -> int:
        """Return the minimum number of bars needed for signal generation.

        This accounts for all indicator warmup periods used by the generator.

        Returns:
            Minimum bar count.
        """

    def __repr__(self) -> str:
        """String representation of the generator."""
        return f"{self.__class__.__name__}(template_id={self.template_id})"
