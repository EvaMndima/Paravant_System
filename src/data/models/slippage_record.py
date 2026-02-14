"""Slippage tracking model for execution quality monitoring.

Records the difference between expected and actual execution prices
for every filled order. Used by SlippageTracker in quality.py for
historical analysis and model recalibration.

Decision: DEC-2026-02-08-002 - SQLAlchemy 2.0 with Mapped[T]
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-007 - Input validation at model layer

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from .base import Base, TimestampMixin, generate_id


class SlippageRecord(Base, TimestampMixin):
    """Slippage record for execution quality tracking.

    Each record captures the slippage for a single order fill,
    comparing the expected price (at signal time) with the actual
    fill price from the exchange.

    Attributes:
        id: Unique identifier (format: slip_YYYYMMDDHHMMSS_uuid).
        order_id: Reference to the parent order.
        symbol: Trading pair symbol.
        side: Order side ("buy" or "sell").
        expected_price: Price expected at signal generation time.
        actual_price: Actual fill price from exchange.
        slippage_pct: Slippage as percentage (positive = worse fill).
        slippage_bps: Slippage in basis points (slippage_pct * 100).
        recorded_at: When the slippage was recorded.
    """

    __tablename__ = "slippage_records"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: generate_id("slip"),
    )

    # Foreign key
    order_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    # Slippage details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    expected_price: Mapped[float] = mapped_column(Float, nullable=False)
    actual_price: Mapped[float] = mapped_column(Float, nullable=False)
    slippage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    slippage_bps: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @validates("expected_price", "actual_price")
    def validate_prices(self, key: str, value: float | None) -> float:
        """Validate price values are positive and not NaN/Infinity.

        Args:
            key: Field name being validated.
            value: Value to validate.

        Returns:
            Validated value.

        Raises:
            ValueError: If value is invalid.
        """
        if value is None:
            raise ValueError(f"{key} cannot be None")
        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")
        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")
        if value <= 0:
            raise ValueError(f"{key} must be positive, got {value}")
        return value

    @validates("slippage_pct", "slippage_bps")
    def validate_slippage_values(self, key: str, value: float | None) -> float:
        """Validate slippage values are not NaN/Infinity.

        Slippage can be positive (worse fill) or negative (better fill).

        Args:
            key: Field name being validated.
            value: Value to validate.

        Returns:
            Validated value.

        Raises:
            ValueError: If value is NaN or Infinity.
        """
        if value is None:
            raise ValueError(f"{key} cannot be None")
        if math.isnan(value):
            raise ValueError(f"{key} cannot be NaN")
        if math.isinf(value):
            raise ValueError(f"{key} cannot be Infinity")
        return value

    def __repr__(self) -> str:
        """String representation of the slippage record."""
        return (
            f"<SlippageRecord(id={self.id}, symbol={self.symbol}, "
            f"slippage={self.slippage_pct:.3f}%)>"
        )
