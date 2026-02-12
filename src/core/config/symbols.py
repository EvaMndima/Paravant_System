"""Symbol configuration for trading pairs.

Decision: DEC-2026-01-15-001 - Asset Class - Crypto ONLY
Decision: DEC-2026-01-15-002 - Broker - Binance ONLY

This module defines the trading pairs available in the system.
Per MVP scope, only crypto pairs from Binance are supported.

Configuration:
- Default enabled symbols for trading
- Available symbols that can be enabled
- Symbol naming conventions and validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SymbolConfig:
    """Configuration for trading symbols.

    Decision: DEC-2026-01-15-001 - Asset Class - Crypto ONLY

    Attributes:
        symbol: Trading pair symbol (e.g., "BTCUSDT").
        enabled: Whether this symbol is enabled for trading.
        min_position_size_usdt: Minimum position size in USDT for risk management.
        max_position_size_pct: Maximum position size as percentage of capital.
        metadata: Additional symbol-specific configuration.
    """

    symbol: str
    enabled: bool = True
    min_position_size_usdt: float = 10.0  # Minimum $10 USDT position
    max_position_size_pct: float = 10.0  # Max 10% of capital per position
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate symbol configuration."""
        # Validate symbol format (should end with USDT for MVP)
        if not self.symbol.endswith("USDT"):
            raise ValueError(
                f"Symbol {self.symbol} must be USDT pair (MVP constraint)"
            )

        # Validate position sizing
        if self.min_position_size_usdt <= 0:
            raise ValueError(
                f"min_position_size_usdt must be positive (got {self.min_position_size_usdt})"
            )

        if not 0 < self.max_position_size_pct <= 100:
            raise ValueError(
                f"max_position_size_pct must be between 0 and 100 (got {self.max_position_size_pct})"
            )


# ============================================================================
# MVP SYMBOL CONFIGURATION
# ============================================================================

# Decision: DEC-2026-01-15-001 - Asset Class - Crypto ONLY
# Decision: DEC-2026-01-15-002 - Broker - Binance ONLY

# Default symbols enabled for trading in MVP
DEFAULT_ENABLED_SYMBOLS = [
    "BTCUSDT",  # Bitcoin - Primary crypto, highest liquidity
    "ETHUSDT",  # Ethereum - Second largest, DeFi leader
]

# Available symbols that can be enabled (all Binance USDT pairs)
# These are tested and verified on Binance testnet
AVAILABLE_SYMBOLS = [
    "BTCUSDT",  # Bitcoin
    "ETHUSDT",  # Ethereum
    "BNBUSDT",  # Binance Coin
    "SOLUSDT",  # Solana
    "XRPUSDT",  # Ripple
    "ADAUSDT",  # Cardano
    "DOGEUSDT",  # Dogecoin
    "AVAXUSDT",  # Avalanche
    "DOTUSDT",  # Polkadot
    "LINKUSDT",  # Chainlink
    "MATICUSDT",  # Polygon (Matic)
    "LTCUSDT",  # Litecoin
]


def get_default_symbol_configs() -> list[SymbolConfig]:
    """Get default symbol configurations for MVP.

    Returns:
        List of SymbolConfig objects for default enabled symbols.

    Example:
        ```python
        configs = get_default_symbol_configs()
        for config in configs:
            print(f"{config.symbol}: enabled={config.enabled}")
        ```
    """
    configs = []

    for symbol in DEFAULT_ENABLED_SYMBOLS:
        config = SymbolConfig(
            symbol=symbol,
            enabled=True,
            min_position_size_usdt=10.0,
            max_position_size_pct=10.0,
            metadata={
                "source": "default",
                "description": f"Default enabled symbol for {symbol.replace('USDT', '')}",
            },
        )
        configs.append(config)

    logger.info(
        "default_symbol_configs_loaded",
        count=len(configs),
        symbols=[c.symbol for c in configs],
    )

    return configs


def get_all_available_symbols() -> list[str]:
    """Get all available trading symbols.

    Decision: DEC-2026-01-15-001 - Asset Class - Crypto ONLY

    Returns:
        List of all available symbol strings (e.g., ["BTCUSDT", "ETHUSDT", ...]).

    Note:
        These are all USDT pairs from Binance testnet that have been
        verified to work with the system.
    """
    return AVAILABLE_SYMBOLS.copy()


def is_symbol_available(symbol: str) -> bool:
    """Check if a symbol is available for trading.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT").

    Returns:
        True if symbol is in available list, False otherwise.

    Example:
        ```python
        if is_symbol_available("BTCUSDT"):
            print("BTC is available for trading")
        ```
    """
    return symbol in AVAILABLE_SYMBOLS


def validate_symbol(symbol: str) -> tuple[bool, str | None]:
    """Validate a trading symbol for MVP constraints.

    Decision: DEC-2026-01-15-001 - Asset Class - Crypto ONLY

    Validation checks:
    - Symbol is in available list
    - Symbol is USDT pair (crypto only)
    - Symbol follows naming convention

    Args:
        symbol: Trading pair symbol to validate.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid.

    Example:
        ```python
        is_valid, error = validate_symbol("BTCUSDT")
        if not is_valid:
            print(f"Invalid symbol: {error}")
        ```
    """
    # Check if empty
    if not symbol:
        return False, "Symbol cannot be empty"

    # Check naming convention (uppercase, ends with USDT)
    if not symbol.isupper():
        return False, f"Symbol must be uppercase (got {symbol})"

    if not symbol.endswith("USDT"):
        return False, f"Symbol must be USDT pair for MVP (got {symbol})"

    # Check if available
    if not is_symbol_available(symbol):
        return False, f"Symbol {symbol} not in available list"

    return True, None


def create_symbol_config(
    symbol: str,
    enabled: bool = True,
    min_position_size_usdt: float = 10.0,
    max_position_size_pct: float = 10.0,
    metadata: dict[str, Any] | None = None,
) -> SymbolConfig:
    """Create a symbol configuration with validation.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT").
        enabled: Whether symbol is enabled for trading (default True).
        min_position_size_usdt: Minimum position size in USDT (default 10.0).
        max_position_size_pct: Maximum position size percentage (default 10.0).
        metadata: Optional additional configuration.

    Returns:
        Validated SymbolConfig object.

    Raises:
        ValueError: If symbol is invalid or configuration is invalid.

    Example:
        ```python
        config = create_symbol_config(
            symbol="BTCUSDT",
            enabled=True,
            min_position_size_usdt=20.0,
            max_position_size_pct=15.0
        )
        ```
    """
    # Validate symbol first
    is_valid, error = validate_symbol(symbol)
    if not is_valid:
        raise ValueError(f"Invalid symbol: {error}")

    # Create config (will validate in __post_init__)
    config = SymbolConfig(
        symbol=symbol,
        enabled=enabled,
        min_position_size_usdt=min_position_size_usdt,
        max_position_size_pct=max_position_size_pct,
        metadata=metadata or {},
    )

    logger.info(
        "symbol_config_created",
        symbol=symbol,
        enabled=enabled,
        min_position_size_usdt=min_position_size_usdt,
        max_position_size_pct=max_position_size_pct,
    )

    return config


# ============================================================================
# SYMBOL GROUPS (for strategy configuration)
# ============================================================================

# High liquidity symbols (recommended for beginners)
HIGH_LIQUIDITY_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
]

# High volatility symbols (for experienced traders)
HIGH_VOLATILITY_SYMBOLS = [
    "SOLUSDT",
    "AVAXUSDT",
    "DOGEUSDT",
]

# Large cap symbols (lower risk)
LARGE_CAP_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
]

# Mid cap symbols (medium risk)
MID_CAP_SYMBOLS = [
    "SOLUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "MATICUSDT",
    "AVAXUSDT",
    "LTCUSDT",
]


def get_symbols_by_group(group: str) -> list[str]:
    """Get symbols by predefined group.

    Args:
        group: Group name ("high_liquidity", "high_volatility", "large_cap", "mid_cap").

    Returns:
        List of symbols in the group.

    Raises:
        ValueError: If group name is invalid.

    Example:
        ```python
        # Get high liquidity symbols for a conservative strategy
        symbols = get_symbols_by_group("high_liquidity")
        print(symbols)  # ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        ```
    """
    groups = {
        "high_liquidity": HIGH_LIQUIDITY_SYMBOLS,
        "high_volatility": HIGH_VOLATILITY_SYMBOLS,
        "large_cap": LARGE_CAP_SYMBOLS,
        "mid_cap": MID_CAP_SYMBOLS,
    }

    if group not in groups:
        valid_groups = ", ".join(groups.keys())
        raise ValueError(
            f"Invalid group '{group}'. Valid groups: {valid_groups}"
        )

    return groups[group].copy()
