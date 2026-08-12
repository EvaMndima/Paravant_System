"""Tests for execution quality tracking: slippage, fill rates, and reports.

Covers SlippageTracker, SlippageEstimator, FillRateTracker, and
ExecutionReportGenerator with edge cases and formula verification.

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


from src.core.execution.quality import (
    ExecutionReportGenerator,
    FillRateTracker,
    SlippageEstimator,
    SlippageTracker,
)


# ---------------------------------------------------------------------------
# SlippageTracker tests
# ---------------------------------------------------------------------------


class TestSlippageTracker:
    """Tests for SlippageTracker slippage recording and statistics."""

    def test_buy_slippage_positive_worse_fill(self) -> None:
        """BUY at higher price -> positive slippage (worse fill)."""
        tracker = SlippageTracker()
        record = tracker.record("ord_1", "BTCUSDT", "buy", 45000.0, 45050.0)
        assert record is not None
        # (45050 - 45000) / 45000 * 100 = 0.1111%
        assert abs(record.slippage_pct - 0.1111) < 0.001

    def test_buy_slippage_negative_better_fill(self) -> None:
        """BUY at lower price -> negative slippage (better fill)."""
        tracker = SlippageTracker()
        record = tracker.record("ord_1", "BTCUSDT", "buy", 45000.0, 44950.0)
        assert record is not None
        assert record.slippage_pct < 0

    def test_sell_slippage_positive_worse_fill(self) -> None:
        """SELL at lower price -> positive slippage (worse fill)."""
        tracker = SlippageTracker()
        record = tracker.record("ord_1", "BTCUSDT", "sell", 45000.0, 44950.0)
        assert record is not None
        # (45000 - 44950) / 45000 * 100 = 0.1111%
        assert abs(record.slippage_pct - 0.1111) < 0.001

    def test_sell_slippage_negative_better_fill(self) -> None:
        """SELL at higher price -> negative slippage (better fill)."""
        tracker = SlippageTracker()
        record = tracker.record("ord_1", "BTCUSDT", "sell", 45000.0, 45050.0)
        assert record is not None
        assert record.slippage_pct < 0

    def test_zero_slippage(self) -> None:
        """Exact fill at expected price -> zero slippage."""
        tracker = SlippageTracker()
        record = tracker.record("ord_1", "BTCUSDT", "buy", 45000.0, 45000.0)
        assert record is not None
        assert abs(record.slippage_pct) < 0.0001

    def test_bps_calculation(self) -> None:
        """Basis points = percentage * 100."""
        tracker = SlippageTracker()
        record = tracker.record("ord_1", "BTCUSDT", "buy", 45000.0, 45045.0)
        assert record is not None
        assert abs(record.slippage_bps - record.slippage_pct * 100) < 0.0001

    def test_nan_price_returns_none(self) -> None:
        """NaN prices should be rejected."""
        tracker = SlippageTracker()
        result = tracker.record("ord_1", "BTCUSDT", "buy", float("nan"), 45000.0)
        assert result is None

    def test_inf_price_returns_none(self) -> None:
        """Infinity prices should be rejected."""
        tracker = SlippageTracker()
        result = tracker.record("ord_1", "BTCUSDT", "buy", 45000.0, float("inf"))
        assert result is None

    def test_zero_expected_price_returns_none(self) -> None:
        """Zero expected price should be rejected (division by zero)."""
        tracker = SlippageTracker()
        result = tracker.record("ord_1", "BTCUSDT", "buy", 0.0, 45000.0)
        assert result is None

    def test_average_slippage_overall(self) -> None:
        """Average slippage across all records."""
        tracker = SlippageTracker()
        tracker.record("ord_1", "BTCUSDT", "buy", 100.0, 101.0)  # 1%
        tracker.record("ord_2", "BTCUSDT", "buy", 100.0, 100.0)  # 0%
        avg = tracker.get_average_slippage()
        assert abs(avg - 0.5) < 0.01

    def test_average_slippage_by_symbol(self) -> None:
        """Average slippage filtered by symbol."""
        tracker = SlippageTracker()
        tracker.record("ord_1", "BTCUSDT", "buy", 100.0, 101.0)  # 1%
        tracker.record("ord_2", "ETHUSDT", "buy", 100.0, 100.5)  # 0.5%
        avg_btc = tracker.get_average_slippage(symbol="BTCUSDT")
        assert abs(avg_btc - 1.0) < 0.01
        avg_eth = tracker.get_average_slippage(symbol="ETHUSDT")
        assert abs(avg_eth - 0.5) < 0.01

    def test_average_slippage_no_records(self) -> None:
        """No records returns 0.0."""
        tracker = SlippageTracker()
        assert tracker.get_average_slippage() == 0.0

    def test_slippage_stats_comprehensive(self) -> None:
        """Full statistics with breakdowns."""
        tracker = SlippageTracker()
        tracker.record("ord_1", "BTCUSDT", "buy", 100.0, 100.5)   # 0.5%
        tracker.record("ord_2", "BTCUSDT", "sell", 100.0, 99.7)   # 0.3%
        tracker.record("ord_3", "ETHUSDT", "buy", 100.0, 100.2)   # 0.2%

        stats = tracker.get_slippage_stats()
        assert stats.total_orders == 3
        assert abs(stats.average_slippage_pct - (0.5 + 0.3 + 0.2) / 3) < 0.01
        assert stats.best_slippage <= stats.worst_slippage
        assert "BTCUSDT" in stats.slippage_by_symbol
        assert "ETHUSDT" in stats.slippage_by_symbol
        assert "buy" in stats.slippage_by_side
        assert "sell" in stats.slippage_by_side

    def test_empty_stats(self) -> None:
        """Empty tracker returns zero stats."""
        tracker = SlippageTracker()
        stats = tracker.get_slippage_stats()
        assert stats.total_orders == 0
        assert stats.average_slippage_pct == 0.0


# ---------------------------------------------------------------------------
# SlippageEstimator tests
# ---------------------------------------------------------------------------


class TestSlippageEstimator:
    """Tests for pre-trade slippage estimation (PRD Feature F)."""

    def test_small_order_proceeds(self) -> None:
        """Small order relative to volume should get PROCEED."""
        estimator = SlippageEstimator()
        estimate = estimator.estimate_slippage(
            symbol="BTCUSDT",
            order_size_usd=10000.0,
            avg_daily_volume_usd=1_000_000_000.0,
        )
        assert estimate.recommended_action == "PROCEED"
        assert not estimate.should_warn
        assert not estimate.should_block

    def test_medium_order_warns(self) -> None:
        """Medium order gets REDUCE_SIZE warning."""
        estimator = SlippageEstimator()
        # Large order relative to small volume
        estimate = estimator.estimate_slippage(
            symbol="BTCUSDT",
            order_size_usd=500000.0,
            avg_daily_volume_usd=50_000_000.0,
        )
        assert estimate.should_warn

    def test_large_order_blocks(self) -> None:
        """Very large order should be blocked."""
        estimator = SlippageEstimator()
        estimate = estimator.estimate_slippage(
            symbol="BTCUSDT",
            order_size_usd=1_000_000.0,
            avg_daily_volume_usd=10_000_000.0,
        )
        assert estimate.should_block
        assert estimate.recommended_action == "CANCEL"

    def test_components_breakdown(self) -> None:
        """Estimate includes component breakdown."""
        estimator = SlippageEstimator()
        estimate = estimator.estimate_slippage(
            symbol="BTCUSDT",
            order_size_usd=10000.0,
            avg_daily_volume_usd=1_000_000_000.0,
            current_atr=500.0,
            avg_atr=400.0,
            current_spread_pct=0.02,
        )
        assert "base" in estimate.components
        assert "size" in estimate.components
        assert "volatility" in estimate.components
        assert "spread" in estimate.components

    def test_no_volume_data_fallback(self) -> None:
        """Missing volume data uses fallback."""
        estimator = SlippageEstimator()
        estimate = estimator.estimate_slippage(
            symbol="BTCUSDT",
            order_size_usd=10000.0,
            avg_daily_volume_usd=None,
        )
        assert estimate.components["size"] == 0.01  # fallback

    def test_store_and_compare_accurate(self) -> None:
        """Compare estimated vs actual slippage."""
        estimator = SlippageEstimator()
        estimator.store_estimate("ord_1", 0.1)
        result = estimator.compare_estimate_vs_actual("ord_1", 0.12)
        assert result is not None
        assert result.error_direction == "ACCURATE"  # within 5bps tolerance

    def test_compare_underestimated(self) -> None:
        """Actual slippage significantly more than estimated."""
        estimator = SlippageEstimator()
        estimator.store_estimate("ord_1", 0.1)
        result = estimator.compare_estimate_vs_actual("ord_1", 0.5)
        assert result is not None
        assert result.error_direction == "UNDERESTIMATED"

    def test_compare_overestimated(self) -> None:
        """Actual slippage significantly less than estimated."""
        estimator = SlippageEstimator()
        estimator.store_estimate("ord_1", 0.5)
        result = estimator.compare_estimate_vs_actual("ord_1", 0.1)
        assert result is not None
        assert result.error_direction == "OVERESTIMATED"

    def test_compare_no_estimate(self) -> None:
        """Comparison with missing estimate returns None."""
        estimator = SlippageEstimator()
        result = estimator.compare_estimate_vs_actual("unknown_order", 0.1)
        assert result is None

    def test_max_slippage_clamped(self) -> None:
        """Estimated slippage is clamped to MAX_ESTIMATED_SLIPPAGE_PCT."""
        estimator = SlippageEstimator()
        estimate = estimator.estimate_slippage(
            symbol="BTCUSDT",
            order_size_usd=100_000_000.0,
            avg_daily_volume_usd=1_000_000.0,  # Extremely large relative to volume
        )
        assert estimate.estimated_slippage_pct <= 5.0


# ---------------------------------------------------------------------------
# FillRateTracker tests
# ---------------------------------------------------------------------------


class TestFillRateTracker:
    """Tests for fill rate tracking and statistics."""

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def test_track_fill(self) -> None:
        """Record a filled order."""
        tracker = FillRateTracker()
        t1 = self._now()
        t2 = t1 + timedelta(seconds=0.5)
        tracker.track_order_fill("ord_1", "BTCUSDT", "market", t1, t2)
        stats = tracker.get_stats()
        assert stats.total_orders == 1
        assert stats.filled_orders == 1
        assert stats.fill_rate_pct == 100.0

    def test_track_cancellation(self) -> None:
        """Record a cancelled order."""
        tracker = FillRateTracker()
        t1 = self._now()
        t2 = t1 + timedelta(seconds=1.0)
        tracker.track_order_cancellation("ord_1", "BTCUSDT", "market", t1, t2)
        stats = tracker.get_stats()
        assert stats.cancelled_orders == 1
        assert stats.cancellation_rate_pct == 100.0

    def test_track_rejection(self) -> None:
        """Record a rejected order."""
        tracker = FillRateTracker()
        t1 = self._now()
        t2 = t1 + timedelta(seconds=0.1)
        tracker.track_order_rejection("ord_1", "BTCUSDT", "market", t1, t2)
        stats = tracker.get_stats()
        assert stats.rejected_orders == 1
        assert stats.rejection_rate_pct == 100.0

    def test_mixed_outcomes(self) -> None:
        """Mixed fill/cancel/reject calculations."""
        tracker = FillRateTracker()
        t1 = self._now()

        tracker.track_order_fill("ord_1", "BTCUSDT", "market", t1, t1 + timedelta(seconds=0.3))
        tracker.track_order_fill("ord_2", "BTCUSDT", "market", t1, t1 + timedelta(seconds=0.5))
        tracker.track_order_cancellation("ord_3", "ETHUSDT", "market", t1, t1 + timedelta(seconds=1))
        tracker.track_order_rejection("ord_4", "BNBUSDT", "market", t1, t1 + timedelta(seconds=0.1))

        stats = tracker.get_stats()
        assert stats.total_orders == 4
        assert stats.filled_orders == 2
        assert abs(stats.fill_rate_pct - 50.0) < 0.01
        assert abs(stats.cancellation_rate_pct - 25.0) < 0.01
        assert abs(stats.rejection_rate_pct - 25.0) < 0.01

    def test_fill_time_statistics(self) -> None:
        """Fill time min/max/avg calculations."""
        tracker = FillRateTracker()
        t1 = self._now()

        tracker.track_order_fill("ord_1", "BTCUSDT", "market", t1, t1 + timedelta(seconds=0.2))
        tracker.track_order_fill("ord_2", "BTCUSDT", "market", t1, t1 + timedelta(seconds=0.8))

        stats = tracker.get_stats()
        assert abs(stats.min_fill_time_seconds - 0.2) < 0.01
        assert abs(stats.max_fill_time_seconds - 0.8) < 0.01
        assert abs(stats.average_fill_time_seconds - 0.5) < 0.01

    def test_by_order_type_breakdown(self) -> None:
        """Stats breakdown by order type."""
        tracker = FillRateTracker()
        t1 = self._now()

        tracker.track_order_fill("ord_1", "BTCUSDT", "market", t1, t1 + timedelta(seconds=0.3))
        tracker.track_order_fill("ord_2", "BTCUSDT", "limit", t1, t1 + timedelta(seconds=1.0))
        tracker.track_order_cancellation("ord_3", "BTCUSDT", "limit", t1, t1 + timedelta(seconds=2.0))

        stats = tracker.get_stats()
        assert "market" in stats.stats_by_order_type
        assert "limit" in stats.stats_by_order_type
        assert stats.stats_by_order_type["market"]["fill_rate_pct"] == 100.0
        assert stats.stats_by_order_type["limit"]["fill_rate_pct"] == 50.0

    def test_by_symbol_breakdown(self) -> None:
        """Stats breakdown by symbol."""
        tracker = FillRateTracker()
        t1 = self._now()

        tracker.track_order_fill("ord_1", "BTCUSDT", "market", t1, t1 + timedelta(seconds=0.3))
        tracker.track_order_rejection("ord_2", "ETHUSDT", "market", t1, t1 + timedelta(seconds=0.1))

        stats = tracker.get_stats()
        assert "BTCUSDT" in stats.stats_by_symbol
        assert "ETHUSDT" in stats.stats_by_symbol
        assert stats.stats_by_symbol["BTCUSDT"]["fill_rate_pct"] == 100.0
        assert stats.stats_by_symbol["ETHUSDT"]["fill_rate_pct"] == 0.0

    def test_empty_stats(self) -> None:
        """Empty tracker returns zero stats."""
        tracker = FillRateTracker()
        stats = tracker.get_stats()
        assert stats.total_orders == 0
        assert stats.fill_rate_pct == 0.0


# ---------------------------------------------------------------------------
# ExecutionReportGenerator tests
# ---------------------------------------------------------------------------


class TestExecutionReportGenerator:
    """Tests for comprehensive report generation."""

    def _make_filled_scenario(
        self,
    ) -> tuple[SlippageTracker, FillRateTracker]:
        """Create trackers with sample data."""
        slip = SlippageTracker()
        fill = FillRateTracker()
        t = datetime.now(timezone.utc)

        # Record slippage
        slip.record("ord_1", "BTCUSDT", "buy", 100.0, 100.5)   # 0.5%
        slip.record("ord_2", "BTCUSDT", "buy", 100.0, 100.1)   # 0.1%
        slip.record("ord_3", "ETHUSDT", "buy", 100.0, 100.6)   # 0.6% (high)

        # Record fills
        fill.track_order_fill("ord_1", "BTCUSDT", "market", t, t + timedelta(seconds=0.3))
        fill.track_order_fill("ord_2", "BTCUSDT", "market", t, t + timedelta(seconds=0.5))
        fill.track_order_fill("ord_3", "ETHUSDT", "market", t, t + timedelta(seconds=0.7))
        fill.track_order_rejection("ord_4", "BNBUSDT", "market", t, t + timedelta(seconds=0.1))

        return slip, fill

    def test_report_generation(self) -> None:
        """Generate a full execution report."""
        slip, fill = self._make_filled_scenario()
        gen = ExecutionReportGenerator(slip, fill)

        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        report = gen.generate_report(start, end)

        assert report.total_orders == 4
        assert report.filled_orders == 3
        assert report.rejected_orders == 1
        assert abs(report.fill_rate_pct - 75.0) < 0.01
        assert report.average_slippage_pct > 0
        assert len(report.recommendations) > 0

    def test_high_slippage_symbols_detected(self) -> None:
        """Symbols with high slippage are flagged."""
        slip, fill = self._make_filled_scenario()
        gen = ExecutionReportGenerator(slip, fill)

        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        report = gen.generate_report(start, end)

        # ETHUSDT has 0.6% slippage > 0.5% threshold
        assert "ETHUSDT" in report.symbols_with_high_slippage

    def test_low_fill_rate_symbols_detected(self) -> None:
        """Symbols with low fill rate are flagged."""
        slip, fill = self._make_filled_scenario()
        gen = ExecutionReportGenerator(slip, fill)

        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        report = gen.generate_report(start, end)

        # BNBUSDT has 0% fill rate (only rejected) < 95%
        assert "BNBUSDT" in report.symbols_with_low_fill_rate

    def test_empty_report(self) -> None:
        """Report with no data."""
        slip = SlippageTracker()
        fill = FillRateTracker()
        gen = ExecutionReportGenerator(slip, fill)

        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        report = gen.generate_report(start, end)

        assert report.total_orders == 0
        assert report.fill_rate_pct == 0.0

    def test_excellent_fill_rate_recommendation(self) -> None:
        """Excellent fill rate generates positive recommendation."""
        slip = SlippageTracker()
        fill = FillRateTracker()
        t = datetime.now(timezone.utc)

        # 100% fill rate
        for i in range(10):
            fill.track_order_fill(f"ord_{i}", "BTCUSDT", "market", t, t + timedelta(seconds=0.1))
            slip.record(f"ord_{i}", "BTCUSDT", "buy", 100.0, 100.01)  # 0.01% slippage

        gen = ExecutionReportGenerator(slip, fill)
        report = gen.generate_report(t - timedelta(days=1), t)

        # Should have "excellent" recommendation
        recs = " ".join(report.recommendations)
        assert "excellent" in recs.lower()
