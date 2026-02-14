"""Execution quality tracking: slippage, fill rates, and reporting.

Monitors execution quality across all orders to detect problems early
and provide actionable recommendations for improving trade execution.

Components:
    - SlippageTracker: Records actual vs expected fill prices
    - SlippageEstimator: Pre-trade slippage estimation (PRD Feature F)
    - FillRateTracker: Fill rate, timing, and rejection statistics
    - ExecutionReportGenerator: Aggregated reports with recommendations

Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Slippage dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlippageRecord:
    """Record of slippage for a single order fill.

    Attributes:
        order_id: Internal order identifier.
        symbol: Trading pair symbol.
        side: Order side ("buy" or "sell").
        expected_price: Price expected at signal time.
        actual_price: Actual fill price from exchange.
        slippage_pct: Slippage as percentage (positive = worse fill).
        slippage_bps: Slippage in basis points.
        recorded_at: When the slippage was recorded.
    """

    order_id: str
    symbol: str
    side: str
    expected_price: float
    actual_price: float
    slippage_pct: float
    slippage_bps: float
    recorded_at: datetime


@dataclass
class SlippageStats:
    """Aggregated slippage statistics.

    Attributes:
        total_orders: Number of orders tracked.
        average_slippage_pct: Average slippage percentage.
        average_slippage_bps: Average slippage in basis points.
        best_slippage: Best (most negative) slippage percentage.
        worst_slippage: Worst (most positive) slippage percentage.
        slippage_by_symbol: Average slippage per symbol.
        slippage_by_side: Average slippage per side (BUY/SELL).
    """

    total_orders: int = 0
    average_slippage_pct: float = 0.0
    average_slippage_bps: float = 0.0
    best_slippage: float = 0.0
    worst_slippage: float = 0.0
    slippage_by_symbol: dict[str, float] = field(default_factory=dict)
    slippage_by_side: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SlippageEstimate:
    """Pre-trade slippage estimation result (PRD Feature F).

    Attributes:
        estimated_slippage_pct: Total estimated slippage percentage.
        components: Breakdown of slippage components.
        should_warn: Whether estimated slippage exceeds warning threshold.
        should_block: Whether estimated slippage exceeds block threshold.
        recommended_action: Action string ("PROCEED", "REDUCE_SIZE", "CANCEL").
        recommendation: Human-readable recommendation message.
    """

    estimated_slippage_pct: float
    components: dict[str, float]
    should_warn: bool
    should_block: bool
    recommended_action: str
    recommendation: str


@dataclass(frozen=True)
class ComparisonResult:
    """Comparison of estimated vs actual slippage.

    Attributes:
        order_id: Order being compared.
        estimated: Estimated slippage percentage.
        actual: Actual slippage percentage.
        error: Difference (actual - estimated).
        error_direction: Whether estimation was over/under/accurate.
    """

    order_id: str
    estimated: float
    actual: float
    error: float
    error_direction: str  # "OVERESTIMATED", "UNDERESTIMATED", "ACCURATE"


# ---------------------------------------------------------------------------
# Fill rate dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FillRateStats:
    """Fill rate and timing statistics.

    Attributes:
        total_orders: Total number of orders tracked.
        filled_orders: Number of filled orders.
        cancelled_orders: Number of cancelled orders.
        rejected_orders: Number of rejected orders.
        partial_fills: Number of partially filled orders.
        fill_rate_pct: Fill rate as percentage.
        cancellation_rate_pct: Cancellation rate as percentage.
        rejection_rate_pct: Rejection rate as percentage.
        average_fill_time_seconds: Average time from submit to fill.
        min_fill_time_seconds: Fastest fill time.
        max_fill_time_seconds: Slowest fill time.
        stats_by_order_type: Breakdown by order type.
        stats_by_symbol: Breakdown by symbol.
    """

    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    partial_fills: int = 0
    fill_rate_pct: float = 0.0
    cancellation_rate_pct: float = 0.0
    rejection_rate_pct: float = 0.0
    average_fill_time_seconds: float = 0.0
    min_fill_time_seconds: float = 0.0
    max_fill_time_seconds: float = 0.0
    stats_by_order_type: dict[str, dict[str, Any]] = field(default_factory=dict)
    stats_by_symbol: dict[str, dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass
class ExecutionReport:
    """Comprehensive execution quality report.

    Attributes:
        period_start: Report period start.
        period_end: Report period end.
        total_orders: Total orders in period.
        filled_orders: Filled orders in period.
        cancelled_orders: Cancelled orders in period.
        rejected_orders: Rejected orders in period.
        fill_rate_pct: Overall fill rate.
        average_slippage_pct: Average slippage.
        average_slippage_bps: Average slippage in bps.
        best_slippage_pct: Best slippage.
        worst_slippage_pct: Worst slippage.
        average_fill_time_seconds: Average fill time.
        min_fill_time_seconds: Fastest fill.
        max_fill_time_seconds: Slowest fill.
        orders_by_type: Order count by type.
        slippage_by_type: Slippage by type.
        fill_rate_by_type: Fill rate by type.
        slippage_by_symbol: Slippage by symbol.
        fill_rate_by_symbol: Fill rate by symbol.
        symbols_with_high_slippage: Symbols with slippage > 0.5%.
        symbols_with_low_fill_rate: Symbols with fill rate < 95%.
        recommendations: Generated recommendations.
    """

    period_start: datetime
    period_end: datetime
    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    rejected_orders: int = 0
    fill_rate_pct: float = 0.0
    average_slippage_pct: float = 0.0
    average_slippage_bps: float = 0.0
    best_slippage_pct: float = 0.0
    worst_slippage_pct: float = 0.0
    average_fill_time_seconds: float = 0.0
    min_fill_time_seconds: float = 0.0
    max_fill_time_seconds: float = 0.0
    orders_by_type: dict[str, int] = field(default_factory=dict)
    slippage_by_type: dict[str, float] = field(default_factory=dict)
    fill_rate_by_type: dict[str, float] = field(default_factory=dict)
    slippage_by_symbol: dict[str, float] = field(default_factory=dict)
    fill_rate_by_symbol: dict[str, float] = field(default_factory=dict)
    symbols_with_high_slippage: list[str] = field(default_factory=list)
    symbols_with_low_fill_rate: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Pre-trade slippage estimation (PRD Feature F)
BASE_SLIPPAGE_PCT: float = 0.05
SIZE_FACTOR_MULTIPLIER: float = 0.5
VOLATILITY_FACTOR_MULTIPLIER: float = 0.1

# Slippage thresholds
WARN_THRESHOLD_PCT: float = 0.3
BLOCK_THRESHOLD_PCT: float = 1.0

# Report thresholds
HIGH_SLIPPAGE_THRESHOLD_PCT: float = 0.5
LOW_FILL_RATE_THRESHOLD_PCT: float = 95.0

# Maximum estimated slippage clamp (prevents absurd values)
MAX_ESTIMATED_SLIPPAGE_PCT: float = 5.0


# ---------------------------------------------------------------------------
# SlippageTracker
# ---------------------------------------------------------------------------


class SlippageTracker:
    """Tracks execution slippage on all order fills.

    Records the difference between expected (signal) price and actual
    fill price for every order, and provides statistics.

    Slippage definitions:
        BUY:  slippage = ((actual - expected) / expected) * 100
              (positive = paid more than expected = worse)
        SELL: slippage = ((expected - actual) / expected) * 100
              (positive = received less than expected = worse)

    Example:
        >>> tracker = SlippageTracker()
        >>> record = tracker.record("ord_123", "BTCUSDT", "buy", 45000.0, 45050.0)
        >>> assert abs(record.slippage_pct - 0.111) < 0.001
    """

    def __init__(self) -> None:
        """Initialize the slippage tracker."""
        self._records: list[SlippageRecord] = []

    def record(
        self,
        order_id: str,
        symbol: str,
        side: str,
        expected_price: float,
        actual_price: float,
    ) -> SlippageRecord | None:
        """Record slippage for an order fill.

        Args:
            order_id: Internal order identifier.
            symbol: Trading pair symbol.
            side: Order side ("buy" or "sell").
            expected_price: Price expected at signal time.
            actual_price: Actual fill price from exchange.

        Returns:
            SlippageRecord if valid, None if inputs are invalid.
        """
        # Validate inputs
        if (
            math.isnan(expected_price)
            or math.isinf(expected_price)
            or math.isnan(actual_price)
            or math.isinf(actual_price)
        ):
            logger.warning(
                "slippage_invalid_prices",
                order_id=order_id,
                expected_price=expected_price,
                actual_price=actual_price,
            )
            return None

        if expected_price <= 0:
            logger.warning(
                "slippage_zero_expected_price",
                order_id=order_id,
                expected_price=expected_price,
            )
            return None

        # Calculate slippage
        if side == "buy":
            slippage_pct = ((actual_price - expected_price) / expected_price) * 100
        else:
            slippage_pct = ((expected_price - actual_price) / expected_price) * 100

        slippage_bps = slippage_pct * 100  # 1% = 100 bps

        record = SlippageRecord(
            order_id=order_id,
            symbol=symbol,
            side=side,
            expected_price=expected_price,
            actual_price=actual_price,
            slippage_pct=slippage_pct,
            slippage_bps=slippage_bps,
            recorded_at=datetime.now(timezone.utc),
        )

        self._records.append(record)

        logger.info(
            "slippage_recorded",
            order_id=order_id,
            symbol=symbol,
            side=side,
            expected_price=expected_price,
            actual_price=actual_price,
            slippage_pct=slippage_pct,
            slippage_bps=slippage_bps,
        )

        return record

    def get_average_slippage(self, symbol: str | None = None) -> float:
        """Get average slippage percentage, optionally filtered by symbol.

        Args:
            symbol: Optional symbol to filter by.

        Returns:
            Average slippage percentage. Returns 0.0 if no records.
        """
        records = self._records
        if symbol:
            records = [r for r in records if r.symbol == symbol]

        if not records:
            return 0.0

        return sum(r.slippage_pct for r in records) / len(records)

    def get_slippage_stats(self) -> SlippageStats:
        """Get comprehensive slippage statistics.

        Returns:
            SlippageStats with averages, extremes, and breakdowns.
        """
        if not self._records:
            return SlippageStats()

        pcts = [r.slippage_pct for r in self._records]
        bps_values = [r.slippage_bps for r in self._records]

        # By-symbol breakdown
        by_symbol: dict[str, list[float]] = {}
        for r in self._records:
            by_symbol.setdefault(r.symbol, []).append(r.slippage_pct)

        # By-side breakdown
        by_side: dict[str, list[float]] = {}
        for r in self._records:
            by_side.setdefault(r.side, []).append(r.slippage_pct)

        return SlippageStats(
            total_orders=len(self._records),
            average_slippage_pct=sum(pcts) / len(pcts),
            average_slippage_bps=sum(bps_values) / len(bps_values),
            best_slippage=min(pcts),
            worst_slippage=max(pcts),
            slippage_by_symbol={
                sym: sum(vals) / len(vals)
                for sym, vals in by_symbol.items()
            },
            slippage_by_side={
                side: sum(vals) / len(vals)
                for side, vals in by_side.items()
            },
        )


# ---------------------------------------------------------------------------
# SlippageEstimator (PRD Feature F)
# ---------------------------------------------------------------------------


class SlippageEstimator:
    """Pre-trade slippage estimation (PRD Feature F).

    Estimates slippage BEFORE placing an order based on:
    - Base slippage (0.05% for market orders)
    - Size factor (order size relative to average daily volume)
    - Volatility factor (current ATR vs average ATR)
    - Spread factor (current bid-ask spread)

    Warns at > 0.3% estimated slippage, blocks at > 1.0%.

    Example:
        >>> estimator = SlippageEstimator()
        >>> estimate = estimator.estimate_slippage(
        ...     symbol="BTCUSDT", order_size_usd=10000.0,
        ...     avg_daily_volume_usd=1_000_000_000.0,
        ... )
        >>> assert estimate.recommended_action == "PROCEED"
    """

    def __init__(self) -> None:
        """Initialize the slippage estimator."""
        self._estimates: dict[str, float] = {}  # order_id -> estimated pct

    def estimate_slippage(
        self,
        symbol: str,
        order_size_usd: float,
        avg_daily_volume_usd: float | None = None,
        current_atr: float | None = None,
        avg_atr: float | None = None,
        current_spread_pct: float | None = None,
    ) -> SlippageEstimate:
        """Estimate slippage for a potential order.

        Args:
            symbol: Trading pair symbol.
            order_size_usd: Order size in USD equivalent.
            avg_daily_volume_usd: Average daily volume in USD.
            current_atr: Current ATR (14-period).
            avg_atr: Average ATR for comparison.
            current_spread_pct: Current bid-ask spread as percentage.

        Returns:
            SlippageEstimate with component breakdown and recommendation.
        """
        components: dict[str, float] = {}

        # Component 1: Base slippage
        base = BASE_SLIPPAGE_PCT
        components["base"] = base

        # Component 2: Size factor
        size_factor = 0.0
        if avg_daily_volume_usd and avg_daily_volume_usd > 0:
            size_factor = (order_size_usd / avg_daily_volume_usd) * SIZE_FACTOR_MULTIPLIER * 100
        else:
            # Fallback: assume 1% if volume unknown
            size_factor = 0.01
        components["size"] = size_factor

        # Component 3: Volatility factor
        vol_factor = 0.0
        if current_atr is not None and avg_atr is not None and avg_atr > 0:
            vol_factor = (current_atr / avg_atr) * VOLATILITY_FACTOR_MULTIPLIER
        components["volatility"] = vol_factor

        # Component 4: Spread factor
        spread_factor = 0.0
        if current_spread_pct is not None:
            spread_factor = current_spread_pct / 2.0
        components["spread"] = spread_factor

        # Total estimated slippage
        total = base + size_factor + vol_factor + spread_factor

        # Clamp to max reasonable value
        total = min(total, MAX_ESTIMATED_SLIPPAGE_PCT)

        # Determine action
        should_block = total > BLOCK_THRESHOLD_PCT
        should_warn = total > WARN_THRESHOLD_PCT

        if should_block:
            action = "CANCEL"
            recommendation = (
                f"Estimated slippage {total:.2f}% exceeds block threshold "
                f"({BLOCK_THRESHOLD_PCT}%). Consider reducing order size or "
                f"waiting for better liquidity."
            )
        elif should_warn:
            action = "REDUCE_SIZE"
            recommendation = (
                f"Estimated slippage {total:.2f}% exceeds warning threshold "
                f"({WARN_THRESHOLD_PCT}%). Consider smaller order size."
            )
        else:
            action = "PROCEED"
            recommendation = (
                f"Estimated slippage {total:.2f}% is within acceptable range."
            )

        logger.info(
            "slippage_estimated",
            symbol=symbol,
            order_size_usd=order_size_usd,
            estimated_pct=total,
            action=action,
            components=components,
        )

        return SlippageEstimate(
            estimated_slippage_pct=total,
            components=components,
            should_warn=should_warn,
            should_block=should_block,
            recommended_action=action,
            recommendation=recommendation,
        )

    def store_estimate(self, order_id: str, estimated_pct: float) -> None:
        """Store an estimate for post-trade comparison.

        Args:
            order_id: Internal order identifier.
            estimated_pct: Estimated slippage percentage.
        """
        self._estimates[order_id] = estimated_pct

    def compare_estimate_vs_actual(
        self,
        order_id: str,
        actual_slippage_pct: float,
    ) -> ComparisonResult | None:
        """Compare estimated slippage with actual slippage.

        Args:
            order_id: Internal order identifier.
            actual_slippage_pct: Actual slippage from SlippageTracker.

        Returns:
            ComparisonResult if estimate exists, None otherwise.
        """
        estimated = self._estimates.get(order_id)
        if estimated is None:
            return None

        error = actual_slippage_pct - estimated
        tolerance = 0.05  # 5 bps tolerance for "accurate"

        if abs(error) <= tolerance:
            direction = "ACCURATE"
        elif error < 0:
            direction = "OVERESTIMATED"
        else:
            direction = "UNDERESTIMATED"

        result = ComparisonResult(
            order_id=order_id,
            estimated=estimated,
            actual=actual_slippage_pct,
            error=error,
            error_direction=direction,
        )

        logger.info(
            "slippage_comparison",
            order_id=order_id,
            estimated=estimated,
            actual=actual_slippage_pct,
            error=error,
            direction=direction,
        )

        return result


# ---------------------------------------------------------------------------
# FillRateTracker
# ---------------------------------------------------------------------------


@dataclass
class _FillRecord:
    """Internal record for fill rate tracking."""

    order_id: str
    symbol: str
    order_type: str
    status: str  # "filled", "cancelled", "rejected"
    submitted_at: datetime
    completed_at: datetime
    fill_time_seconds: float | None = None


class FillRateTracker:
    """Tracks fill rate, timing, and rejection statistics.

    Records the outcome of every order submission to calculate
    fill rates, average fill times, and identify problematic symbols.

    Example:
        >>> tracker = FillRateTracker()
        >>> tracker.track_order_fill("ord_1", "BTCUSDT", "market", submit_t, fill_t)
        >>> stats = tracker.get_stats()
        >>> assert stats.fill_rate_pct == 100.0
    """

    def __init__(self) -> None:
        """Initialize the fill rate tracker."""
        self._records: list[_FillRecord] = []

    def track_order_fill(
        self,
        order_id: str,
        symbol: str,
        order_type: str,
        submitted_at: datetime,
        filled_at: datetime,
    ) -> None:
        """Record a filled order.

        Args:
            order_id: Internal order identifier.
            symbol: Trading pair symbol.
            order_type: Order type (e.g., "market").
            submitted_at: When order was submitted.
            filled_at: When order was filled.
        """
        fill_time = (filled_at - submitted_at).total_seconds()

        self._records.append(_FillRecord(
            order_id=order_id,
            symbol=symbol,
            order_type=order_type,
            status="filled",
            submitted_at=submitted_at,
            completed_at=filled_at,
            fill_time_seconds=fill_time,
        ))

        logger.debug(
            "fill_tracked",
            order_id=order_id,
            symbol=symbol,
            fill_time_seconds=fill_time,
        )

    def track_order_cancellation(
        self,
        order_id: str,
        symbol: str,
        order_type: str,
        submitted_at: datetime,
        cancelled_at: datetime,
    ) -> None:
        """Record a cancelled order.

        Args:
            order_id: Internal order identifier.
            symbol: Trading pair symbol.
            order_type: Order type.
            submitted_at: When order was submitted.
            cancelled_at: When order was cancelled.
        """
        self._records.append(_FillRecord(
            order_id=order_id,
            symbol=symbol,
            order_type=order_type,
            status="cancelled",
            submitted_at=submitted_at,
            completed_at=cancelled_at,
        ))

    def track_order_rejection(
        self,
        order_id: str,
        symbol: str,
        order_type: str,
        submitted_at: datetime,
        rejected_at: datetime,
    ) -> None:
        """Record a rejected order.

        Args:
            order_id: Internal order identifier.
            symbol: Trading pair symbol.
            order_type: Order type.
            submitted_at: When order was submitted.
            rejected_at: When order was rejected.
        """
        self._records.append(_FillRecord(
            order_id=order_id,
            symbol=symbol,
            order_type=order_type,
            status="rejected",
            submitted_at=submitted_at,
            completed_at=rejected_at,
        ))

    def get_stats(self) -> FillRateStats:
        """Get comprehensive fill rate statistics.

        Returns:
            FillRateStats with rates, timing, and breakdowns.
        """
        if not self._records:
            return FillRateStats()

        total = len(self._records)
        filled = [r for r in self._records if r.status == "filled"]
        cancelled = [r for r in self._records if r.status == "cancelled"]
        rejected = [r for r in self._records if r.status == "rejected"]

        fill_times = [
            r.fill_time_seconds
            for r in filled
            if r.fill_time_seconds is not None
        ]

        # By order type
        by_type: dict[str, dict[str, Any]] = {}
        for r in self._records:
            if r.order_type not in by_type:
                by_type[r.order_type] = {"total": 0, "filled": 0}
            by_type[r.order_type]["total"] += 1
            if r.status == "filled":
                by_type[r.order_type]["filled"] += 1

        stats_by_type: dict[str, dict[str, Any]] = {}
        for ot, counts in by_type.items():
            rate = (counts["filled"] / counts["total"] * 100) if counts["total"] > 0 else 0.0
            stats_by_type[ot] = {
                "total": counts["total"],
                "filled": counts["filled"],
                "fill_rate_pct": rate,
            }

        # By symbol
        by_symbol: dict[str, dict[str, Any]] = {}
        for r in self._records:
            if r.symbol not in by_symbol:
                by_symbol[r.symbol] = {"total": 0, "filled": 0}
            by_symbol[r.symbol]["total"] += 1
            if r.status == "filled":
                by_symbol[r.symbol]["filled"] += 1

        stats_by_symbol: dict[str, dict[str, Any]] = {}
        for sym, counts in by_symbol.items():
            rate = (counts["filled"] / counts["total"] * 100) if counts["total"] > 0 else 0.0
            stats_by_symbol[sym] = {
                "total": counts["total"],
                "filled": counts["filled"],
                "fill_rate_pct": rate,
            }

        return FillRateStats(
            total_orders=total,
            filled_orders=len(filled),
            cancelled_orders=len(cancelled),
            rejected_orders=len(rejected),
            partial_fills=0,
            fill_rate_pct=(len(filled) / total * 100) if total > 0 else 0.0,
            cancellation_rate_pct=(len(cancelled) / total * 100) if total > 0 else 0.0,
            rejection_rate_pct=(len(rejected) / total * 100) if total > 0 else 0.0,
            average_fill_time_seconds=(sum(fill_times) / len(fill_times)) if fill_times else 0.0,
            min_fill_time_seconds=min(fill_times) if fill_times else 0.0,
            max_fill_time_seconds=max(fill_times) if fill_times else 0.0,
            stats_by_order_type=stats_by_type,
            stats_by_symbol=stats_by_symbol,
        )


# ---------------------------------------------------------------------------
# ExecutionReportGenerator
# ---------------------------------------------------------------------------


class ExecutionReportGenerator:
    """Generates comprehensive execution quality reports.

    Aggregates data from SlippageTracker and FillRateTracker to
    produce reports with actionable recommendations.

    Example:
        >>> generator = ExecutionReportGenerator(slippage_tracker, fill_rate_tracker)
        >>> report = generator.generate_report(start_date, end_date)
        >>> for rec in report.recommendations:
        ...     print(rec)
    """

    def __init__(
        self,
        slippage_tracker: SlippageTracker,
        fill_rate_tracker: FillRateTracker,
    ) -> None:
        """Initialize the report generator.

        Args:
            slippage_tracker: SlippageTracker for slippage data.
            fill_rate_tracker: FillRateTracker for fill rate data.
        """
        self.slippage_tracker = slippage_tracker
        self.fill_rate_tracker = fill_rate_tracker

    def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> ExecutionReport:
        """Generate a comprehensive execution report for a date range.

        Args:
            start_date: Report period start (inclusive).
            end_date: Report period end (inclusive).

        Returns:
            ExecutionReport with aggregated metrics and recommendations.
        """
        # Get statistics
        slippage_stats = self.slippage_tracker.get_slippage_stats()
        fill_stats = self.fill_rate_tracker.get_stats()

        # Identify problematic symbols
        high_slippage_symbols = [
            sym for sym, avg in slippage_stats.slippage_by_symbol.items()
            if avg > HIGH_SLIPPAGE_THRESHOLD_PCT
        ]

        low_fill_symbols = [
            sym for sym, data in fill_stats.stats_by_symbol.items()
            if data.get("fill_rate_pct", 100.0) < LOW_FILL_RATE_THRESHOLD_PCT
        ]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            slippage_stats, fill_stats, high_slippage_symbols, low_fill_symbols
        )

        report = ExecutionReport(
            period_start=start_date,
            period_end=end_date,
            total_orders=fill_stats.total_orders,
            filled_orders=fill_stats.filled_orders,
            cancelled_orders=fill_stats.cancelled_orders,
            rejected_orders=fill_stats.rejected_orders,
            fill_rate_pct=fill_stats.fill_rate_pct,
            average_slippage_pct=slippage_stats.average_slippage_pct,
            average_slippage_bps=slippage_stats.average_slippage_bps,
            best_slippage_pct=slippage_stats.best_slippage,
            worst_slippage_pct=slippage_stats.worst_slippage,
            average_fill_time_seconds=fill_stats.average_fill_time_seconds,
            min_fill_time_seconds=fill_stats.min_fill_time_seconds,
            max_fill_time_seconds=fill_stats.max_fill_time_seconds,
            orders_by_type={
                ot: data.get("total", 0)
                for ot, data in fill_stats.stats_by_order_type.items()
            },
            slippage_by_type={},  # Would need per-type slippage data
            fill_rate_by_type={
                ot: data.get("fill_rate_pct", 0.0)
                for ot, data in fill_stats.stats_by_order_type.items()
            },
            slippage_by_symbol=slippage_stats.slippage_by_symbol,
            fill_rate_by_symbol={
                sym: data.get("fill_rate_pct", 0.0)
                for sym, data in fill_stats.stats_by_symbol.items()
            },
            symbols_with_high_slippage=high_slippage_symbols,
            symbols_with_low_fill_rate=low_fill_symbols,
            recommendations=recommendations,
        )

        logger.info(
            "execution_report_generated",
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            total_orders=report.total_orders,
            fill_rate_pct=report.fill_rate_pct,
            avg_slippage_pct=report.average_slippage_pct,
            recommendations_count=len(recommendations),
        )

        return report

    @staticmethod
    def _generate_recommendations(
        slippage_stats: SlippageStats,
        fill_stats: FillRateStats,
        high_slippage_symbols: list[str],
        low_fill_symbols: list[str],
    ) -> list[str]:
        """Generate actionable recommendations from execution data.

        Args:
            slippage_stats: Slippage statistics.
            fill_stats: Fill rate statistics.
            high_slippage_symbols: Symbols with high slippage.
            low_fill_symbols: Symbols with low fill rate.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        # Slippage recommendations
        for sym in high_slippage_symbols:
            avg = slippage_stats.slippage_by_symbol.get(sym, 0.0)
            recommendations.append(
                f"{sym} has high slippage ({avg:.2f}%), "
                f"consider reducing order size or using limit orders"
            )

        # Fill rate recommendations
        for sym in low_fill_symbols:
            recommendations.append(
                f"{sym} has low fill rate, check for liquidity issues"
            )

        # Overall assessment
        if fill_stats.fill_rate_pct >= 98.0:
            recommendations.append(
                f"Overall fill rate is excellent ({fill_stats.fill_rate_pct:.1f}%)"
            )
        elif fill_stats.fill_rate_pct >= 95.0:
            recommendations.append(
                f"Overall fill rate is good ({fill_stats.fill_rate_pct:.1f}%)"
            )
        elif fill_stats.total_orders > 0:
            recommendations.append(
                f"Overall fill rate needs attention ({fill_stats.fill_rate_pct:.1f}%)"
            )

        if slippage_stats.average_slippage_pct > 0.3:
            recommendations.append(
                f"Average slippage ({slippage_stats.average_slippage_pct:.2f}%) "
                f"exceeds target (0.3%). Review order sizing."
            )

        return recommendations
