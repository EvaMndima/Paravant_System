"""Indicator Factory for dynamic indicator creation.

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-11-001 - Compute-on-demand indicator strategy

Factory pattern for creating indicators by name. Enables dynamic indicator
creation from configuration, user input, or strategy definitions.

Example:
    >>> factory = IndicatorFactory()
    >>> rsi = factory.create("rsi", period=14)
    >>> ema = factory.create("ema", period=20)
"""

from __future__ import annotations

from typing import Any, Type

from src.core.indicators.adx import ADX
from src.core.indicators.atr import ATR
from src.core.indicators.base import Indicator
from src.core.indicators.bollinger import BollingerBands
from src.core.indicators.donchian import DonchianChannel
from src.core.indicators.ema import EMA
from src.core.indicators.macd import MACD
from src.core.indicators.rsi import RSI
from src.core.indicators.sma import SMA
from src.core.indicators.supertrend import SuperTrend
from src.core.indicators.volume import VolumeAverage
from src.core.indicators.vwap import VWAP


class IndicatorFactory:
    """Factory for creating indicators by name.

    Decision: DEC-2026-02-08-006 - Type hints 100% coverage

    Registry-based factory pattern. Supports indicator creation by string name
    with arbitrary parameters, enabling dynamic configuration.

    Example:
        >>> factory = IndicatorFactory()
        >>> # Create indicators by name
        >>> rsi = factory.create("rsi", period=14)
        >>> ema = factory.create("ema", period=20)
        >>> bb = factory.create("bollinger", period=20, multiplier=2.0)
        >>>
        >>> # List available indicators
        >>> indicators = factory.list_indicators()
        >>> print(indicators)  # ["ema", "sma", "rsi", "atr", ...]
        >>>
        >>> # Register custom indicator
        >>> factory.register("my_custom", MyCustomIndicator)
    """

    _registry: dict[str, Type[Indicator]] = {
        # Moving averages
        "ema": EMA,
        "sma": SMA,
        # Momentum oscillators
        "rsi": RSI,
        "macd": MACD,
        # Volatility indicators
        "atr": ATR,
        "bollinger": BollingerBands,
        "bb": BollingerBands,  # Alias
        # Trend indicators
        "donchian": DonchianChannel,
        "dc": DonchianChannel,  # Alias
        "supertrend": SuperTrend,
        "st": SuperTrend,  # Alias
        "adx": ADX,
        # Volume indicators
        "vwap": VWAP,
        "volume": VolumeAverage,
        "vol_avg": VolumeAverage,  # Alias
    }

    @classmethod
    def create(cls, name: str, **params: Any) -> Indicator:
        """Create indicator by name with parameters.

        Args:
            name: Indicator name (case-insensitive).
                 Examples: "rsi", "ema", "bollinger", "bb".
            **params: Indicator-specific parameters.
                     Examples: period=14, multiplier=2.0.

        Returns:
            Indicator instance configured with parameters.

        Raises:
            ValueError: If indicator name not registered.
            TypeError: If parameters are invalid for indicator.

        Example:
            >>> factory = IndicatorFactory()
            >>> # Create with default parameters
            >>> rsi = factory.create("rsi")
            >>>
            >>> # Create with custom parameters
            >>> rsi14 = factory.create("rsi", period=14)
            >>> ema50 = factory.create("ema", period=50)
            >>> bb = factory.create("bollinger", period=20, multiplier=2.5)
            >>>
            >>> # Use aliases
            >>> bb_alias = factory.create("bb", period=20, multiplier=2.0)
            >>> st = factory.create("st", period=10, multiplier=3.0)
        """
        name_lower = name.lower()

        if name_lower not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(
                f"Unknown indicator: '{name}'. "
                f"Available indicators: {available}"
            )

        indicator_class = cls._registry[name_lower]

        try:
            return indicator_class(**params)
        except TypeError as e:
            # Provide helpful error message about parameter issues
            raise TypeError(
                f"Invalid parameters for {indicator_class.__name__}: {e}"
            ) from e

    @classmethod
    def register(cls, name: str, indicator_class: Type[Indicator]) -> None:
        """Register a custom indicator in the factory.

        Enables registration of user-defined indicators for dynamic creation.

        Args:
            name: Indicator name for factory lookup (case-insensitive).
            indicator_class: Indicator class (must inherit from Indicator).

        Raises:
            ValueError: If name is empty or indicator_class is not an Indicator subclass.

        Example:
            >>> class MyCustomIndicator(Indicator):
            ...     def calculate(self, series):
            ...         # Custom calculation
            ...         pass
            >>>
            >>> factory = IndicatorFactory()
            >>> factory.register("my_custom", MyCustomIndicator)
            >>> indicator = factory.create("my_custom", period=10)
        """
        if not name or not name.strip():
            raise ValueError("Indicator name cannot be empty")

        if not issubclass(indicator_class, Indicator):
            raise ValueError(
                f"{indicator_class.__name__} must inherit from Indicator base class"
            )

        name_lower = name.lower()
        cls._registry[name_lower] = indicator_class

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister an indicator from the factory.

        Args:
            name: Indicator name to remove (case-insensitive).

        Raises:
            ValueError: If indicator name not registered.

        Example:
            >>> factory = IndicatorFactory()
            >>> factory.unregister("my_custom")
        """
        name_lower = name.lower()

        if name_lower not in cls._registry:
            raise ValueError(f"Indicator '{name}' is not registered")

        del cls._registry[name_lower]

    @classmethod
    def list_indicators(cls) -> list[str]:
        """Get list of all registered indicator names.

        Returns:
            Sorted list of indicator names (lowercase).

        Example:
            >>> factory = IndicatorFactory()
            >>> indicators = factory.list_indicators()
            >>> print(indicators)
            ['adx', 'atr', 'bb', 'bollinger', 'dc', 'donchian', 'ema', ...]
        """
        return sorted(cls._registry.keys())

    @classmethod
    def get_indicator_class(cls, name: str) -> Type[Indicator]:
        """Get indicator class by name (without instantiation).

        Useful for inspecting indicator class without creating instance.

        Args:
            name: Indicator name (case-insensitive).

        Returns:
            Indicator class type.

        Raises:
            ValueError: If indicator name not registered.

        Example:
            >>> factory = IndicatorFactory()
            >>> rsi_class = factory.get_indicator_class("rsi")
            >>> print(rsi_class.__name__)  # "RSI"
            >>> print(rsi_class.__doc__)   # RSI docstring
        """
        name_lower = name.lower()

        if name_lower not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(
                f"Unknown indicator: '{name}'. "
                f"Available indicators: {available}"
            )

        return cls._registry[name_lower]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if indicator name is registered.

        Args:
            name: Indicator name to check (case-insensitive).

        Returns:
            True if indicator is registered.

        Example:
            >>> factory = IndicatorFactory()
            >>> factory.is_registered("rsi")
            True
            >>> factory.is_registered("unknown")
            False
        """
        return name.lower() in cls._registry
