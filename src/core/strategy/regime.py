"""Market regime management for strategy-regime alignment.

Provides manual regime tagging per symbol and regime-aware position sizing.
The MarketRegimeManager persists regime state via the DataStore and checks
strategy-regime compatibility using template ``recommended_for`` fields.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
MVP Scope: Manual regime tagging only (no automated detection)
"""
from __future__ import annotations

import enum

from src.core.config.templates import TemplateManager
from src.core.exceptions import RegimeError
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Position size reduction factor when strategy runs in a non-recommended regime
REGIME_MISMATCH_SIZE_FACTOR = 0.5


class MarketRegime(str, enum.Enum):
    """Market regime classification.

    MVP supports five regimes set manually by the operator.
    Automated detection is planned for V2.
    """

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


def set_regime(
    symbol: str,
    regime: MarketRegime,
    store: DataStore,
) -> None:
    """Set the market regime for a symbol.

    Persists regime to SystemState.circuit_breakers JSON under a
    ``market_regimes`` key to avoid schema migration for MVP.

    Args:
        symbol: Trading pair symbol (e.g., ``BTCUSDT``).
        regime: The regime to assign.
        store: DataStore instance for persistence.

    Raises:
        RegimeError: If the symbol is empty or persistence fails.
    """
    if not symbol or not symbol.strip():
        raise RegimeError(symbol=symbol, reason="Symbol cannot be empty")

    state = store.get_system_state()
    regimes = dict(state.circuit_breakers.get("market_regimes", {}))
    regimes[symbol] = regime.value

    # Store regimes inside circuit_breakers JSON to avoid schema change
    cb = dict(state.circuit_breakers)
    cb["market_regimes"] = regimes
    store.update_system_state(circuit_breakers=cb)

    logger.info(
        "regime_set",
        symbol=symbol,
        regime=regime.value,
    )


def get_regime(symbol: str, store: DataStore) -> MarketRegime:
    """Get the current market regime for a symbol.

    Args:
        symbol: Trading pair symbol.
        store: DataStore instance.

    Returns:
        Current MarketRegime for the symbol, defaults to UNKNOWN.
    """
    state = store.get_system_state()
    regimes: dict[str, str] = state.circuit_breakers.get("market_regimes", {})
    raw = regimes.get(symbol, MarketRegime.UNKNOWN.value)

    try:
        return MarketRegime(raw)
    except ValueError:
        logger.warning(
            "invalid_regime_value",
            symbol=symbol,
            raw_value=raw,
        )
        return MarketRegime.UNKNOWN


def get_all_regimes(store: DataStore) -> dict[str, MarketRegime]:
    """Get all currently set market regimes.

    Args:
        store: DataStore instance.

    Returns:
        Dictionary mapping symbol to MarketRegime.
    """
    state = store.get_system_state()
    raw_regimes: dict[str, str] = state.circuit_breakers.get("market_regimes", {})

    result: dict[str, MarketRegime] = {}
    for symbol, raw in raw_regimes.items():
        try:
            result[symbol] = MarketRegime(raw)
        except ValueError:
            result[symbol] = MarketRegime.UNKNOWN

    return result


def should_reduce_size(
    template_id: str,
    symbol: str,
    store: DataStore,
    template_manager: TemplateManager,
) -> bool:
    """Check if position size should be reduced due to regime mismatch.

    Compares the current regime for the symbol against the template's
    ``recommended_for`` list. If the regime is not recommended, returns
    True to signal a 50% size reduction.

    Args:
        template_id: Strategy template identifier.
        symbol: Trading pair symbol.
        store: DataStore instance.
        template_manager: TemplateManager for template lookup.

    Returns:
        True if position size should be reduced (regime mismatch).
    """
    current_regime = get_regime(symbol, store)

    # UNKNOWN regime does not trigger reduction - operator has not classified yet
    if current_regime == MarketRegime.UNKNOWN:
        return False

    try:
        template = template_manager.get_template(template_id)
    except ValueError:
        logger.warning(
            "regime_check_template_not_found",
            template_id=template_id,
            symbol=symbol,
        )
        return False

    # If template has no recommendations, no mismatch possible
    if not template.recommended_for:
        return False

    is_recommended = current_regime.value in template.recommended_for
    if not is_recommended:
        logger.info(
            "regime_mismatch_detected",
            template_id=template_id,
            symbol=symbol,
            current_regime=current_regime.value,
            recommended_for=template.recommended_for,
            size_reduction_factor=REGIME_MISMATCH_SIZE_FACTOR,
        )

    return not is_recommended


def get_size_factor(
    template_id: str,
    symbol: str,
    store: DataStore,
    template_manager: TemplateManager,
) -> float:
    """Get the position size factor based on regime alignment.

    Returns 1.0 for aligned regimes, REGIME_MISMATCH_SIZE_FACTOR (0.5)
    for misaligned regimes.

    Args:
        template_id: Strategy template identifier.
        symbol: Trading pair symbol.
        store: DataStore instance.
        template_manager: TemplateManager for template lookup.

    Returns:
        Size multiplier (1.0 or REGIME_MISMATCH_SIZE_FACTOR).
    """
    if should_reduce_size(template_id, symbol, store, template_manager):
        return REGIME_MISMATCH_SIZE_FACTOR
    return 1.0
