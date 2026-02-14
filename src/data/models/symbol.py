"""Symbol info model.

Decision: DEC-2026-02-08-002 - SQLAlchemy 2.0 with Mapped[T]
Decision: DEC-2026-02-08-007 - Input validation at model layer
Decision: DEC-2026-02-08-010 - Lambda functions for mutable defaults

This module defines the SymbolInfo model for storing trading pair metadata
from exchange (lot sizes, tick sizes, min notional, etc.).

Used for:
- Order quantity validation
- Price rounding
- Order value validation
- Trading status checks
"""

from __future__ import annotations

import math
from typing import Any, cast

from sqlalchemy import JSON, Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from src.data.models.base import Base, TimestampMixin, generate_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SymbolInfo(Base, TimestampMixin):
    """Symbol metadata from exchange.

    Decision: DEC-2026-02-08-002 - SQLAlchemy 2.0 with Mapped[T]

    Stores trading pair information from exchange (Binance) including
    lot sizes, tick sizes, and trading rules.

    Attributes:
        id: Unique symbol ID (generated).
        symbol: Trading pair symbol (e.g., "BTCUSDT").
        base_asset: Base asset (e.g., "BTC").
        quote_asset: Quote asset (e.g., "USDT").
        min_quantity: Minimum order quantity.
        max_quantity: Maximum order quantity.
        step_size: Quantity increment step (lot size).
        tick_size: Price increment step.
        min_price: Minimum price (optional).
        max_price: Maximum price (optional).
        min_notional: Minimum order value (quantity * price).
        is_trading: Whether symbol is currently tradable.
        is_spot_trading_allowed: Whether spot trading is allowed.
        is_margin_trading_allowed: Whether margin trading is allowed.
        filters: Additional exchange filters (JSON).
    """

    __tablename__ = "symbols"

    # Primary key
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: generate_id("sym"),
    )

    # Symbol identification
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    base_asset: Mapped[str] = mapped_column(String(10), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(10), nullable=False)

    # Lot size filter (quantity constraints)
    min_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    max_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    step_size: Mapped[float] = mapped_column(Float, nullable=False)

    # Price filter (price constraints)
    tick_size: Mapped[float] = mapped_column(Float, nullable=False)
    min_price: Mapped[float | None] = mapped_column(Float)
    max_price: Mapped[float | None] = mapped_column(Float)

    # Min notional filter (minimum order value)
    min_notional: Mapped[float] = mapped_column(Float, nullable=False)

    # Trading status
    is_trading: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_spot_trading_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_margin_trading_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Additional filters (JSON)
    # Decision: DEC-2026-02-08-009 - Explicit JSON type
    # Decision: DEC-2026-02-08-010 - Lambda for mutable defaults
    filters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: cast(dict[str, Any], {}),
    )

    # Decision: DEC-2026-02-08-007 - Input validation at model layer
    @validates("min_quantity", "max_quantity", "step_size", "tick_size", "min_notional")
    def validate_positive_values(self, key: str, value: float | None) -> float | None:
        """Validate numeric values are positive and not NaN/Infinity.

        Decision: DEC-2026-02-08-007 - Input validation at model layer

        Args:
            key: Field name being validated.
            value: Field value being validated.

        Returns:
            Validated value.

        Raises:
            ValueError: If value is invalid (NaN, Infinity, <= 0).
        """
        if value is None:
            return value

        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")

        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")

        if value <= 0:
            raise ValueError(f"{key} must be positive (got {value})")

        return value

    @validates("min_price", "max_price")
    def validate_optional_prices(self, key: str, value: float | None) -> float | None:
        """Validate optional price values.

        Args:
            key: Field name being validated.
            value: Field value being validated.

        Returns:
            Validated value.

        Raises:
            ValueError: If value is invalid (NaN, Infinity, <= 0).
        """
        if value is None:
            return value

        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")

        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")

        if value <= 0:
            raise ValueError(f"{key} must be positive (got {value})")

        return value

    def round_quantity(self, quantity: float) -> float:
        """Round quantity to valid step size.

        Args:
            quantity: Quantity to round.

        Returns:
            Rounded quantity that satisfies step_size constraint.
        """
        # Round to nearest multiple of step_size
        return round(quantity / self.step_size) * self.step_size

    def round_price(self, price: float) -> float:
        """Round price to valid tick size.

        Args:
            price: Price to round.

        Returns:
            Rounded price that satisfies tick_size constraint.
        """
        # Round to nearest multiple of tick_size
        return round(price / self.tick_size) * self.tick_size

    def validate_quantity(self, quantity: float) -> tuple[bool, str | None]:
        """Validate order quantity against exchange rules.

        Args:
            quantity: Order quantity to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        # Check minimum
        if quantity < self.min_quantity:
            return False, f"Quantity {quantity} below minimum {self.min_quantity}"

        # Check maximum
        if quantity > self.max_quantity:
            return False, f"Quantity {quantity} above maximum {self.max_quantity}"

        # Check step size (must be exact multiple)
        # Decision: DEC-2026-02-11-001 - Robust floating point check
        # Use a tolerance for floating point math errors
        tolerance = 1e-9
        remainder = (quantity / self.step_size) % 1
        
        # Check if remainder is close to 0 or close to 1
        is_integer = math.isclose(remainder, 0, abs_tol=tolerance) or math.isclose(remainder, 1, abs_tol=tolerance)
        
        if not is_integer:
            logger.debug(
                "quantity_precision_check_failed",
                quantity=quantity,
                step_size=self.step_size,
                remainder=remainder,
                calc=quantity / self.step_size,
            )
            rounded = self.round_quantity(quantity)
            return False, f"Quantity {quantity} not a multiple of step size {self.step_size} (use {rounded})"

        return True, None

    def validate_price(self, price: float) -> tuple[bool, str | None]:
        """Validate order price against exchange rules.

        Args:
            price: Order price to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        # Check minimum (if set)
        if self.min_price is not None and price < self.min_price:
            return False, f"Price {price} below minimum {self.min_price}"

        # Check maximum (if set)
        if self.max_price is not None and price > self.max_price:
            return False, f"Price {price} above maximum {self.max_price}"

        # Check tick size (must be exact multiple)
        remainder = (price / self.tick_size) % 1
        if remainder > 0.0001:  # Small tolerance for floating point errors
            rounded = self.round_price(price)
            return False, f"Price {price} not a multiple of tick size {self.tick_size} (use {rounded})"

        return True, None

    def validate_notional(self, quantity: float, price: float) -> tuple[bool, str | None]:
        """Validate order notional value (quantity * price).

        Args:
            quantity: Order quantity.
            price: Order price.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        notional = quantity * price

        if notional < self.min_notional:
            return False, f"Order value {notional} below minimum {self.min_notional}"

        return True, None

    def validate_order(
        self,
        quantity: float,
        price: float,
    ) -> tuple[bool, list[str]]:
        """Validate complete order against all exchange rules.

        Args:
            quantity: Order quantity.
            price: Order price.

        Returns:
            Tuple of (is_valid, error_messages).
            error_messages list is empty if valid.
        """
        errors: list[str] = []

        # Validate trading status
        if not self.is_trading:
            errors.append(f"Symbol {self.symbol} is not currently trading")

        if not self.is_spot_trading_allowed:
            errors.append(f"Spot trading not allowed for {self.symbol}")

        # Validate quantity
        quantity_valid, quantity_error = self.validate_quantity(quantity)
        if not quantity_valid and quantity_error:
            errors.append(quantity_error)

        # Validate price
        price_valid, price_error = self.validate_price(price)
        if not price_valid and price_error:
            errors.append(price_error)

        # Validate notional (only if quantity and price valid)
        if quantity_valid and price_valid:
            notional_valid, notional_error = self.validate_notional(quantity, price)
            if not notional_valid and notional_error:
                errors.append(notional_error)

        return len(errors) == 0, errors

    def __repr__(self) -> str:
        """String representation of symbol info.

        Returns:
            String with symbol and key constraints.
        """
        return (
            f"<SymbolInfo(symbol={self.symbol}, "
            f"min_qty={self.min_quantity}, step={self.step_size}, "
            f"tick={self.tick_size}, min_notional={self.min_notional})>"
        )
