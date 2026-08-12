"""Tests for PositionTracker: lifecycle, P&L, sync, and staleness.

Covers all position operations: open, add-to, partial close, full close,
unrealized/realized P&L with commission, position sync, and staleness
monitoring with strategy-type thresholds and profitable extension.

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import PositionStorageError
from src.core.execution.interface import Balance
from src.core.execution.position_tracker import (
    PositionTracker,
)
from src.data.models.order import OrderSide
from src.data.models.position import Position, PositionSide, PositionStatus
from src.data.models.strategy import StrategyType
from src.data.models.trade import Trade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trade(
    symbol: str = "BTCUSDT",
    side: OrderSide = OrderSide.BUY,
    quantity: float = 0.5,
    price: float = 45000.0,
    commission: float = 5.0,
    account_id: str = "acc_test",
    order_id: str = "ord_test",
) -> MagicMock:
    """Create a mock trade with the given attributes."""
    trade = MagicMock(spec=Trade)
    trade.symbol = symbol
    trade.side = side
    trade.quantity = quantity
    trade.price = price
    trade.commission = commission
    trade.account_id = account_id
    trade.order_id = order_id
    trade.executed_at = datetime.now(timezone.utc)
    trade.id = "trd_test"
    return trade


def _make_position(
    symbol: str = "BTCUSDT",
    side: PositionSide = PositionSide.LONG,
    size: float = 0.5,
    entry_price: float = 45000.0,
    current_price: float = 45000.0,
    commission_paid: float = 5.0,
    pnl_usdt: float = 0.0,
    pnl_pct: float = 0.0,
    status: PositionStatus = PositionStatus.OPEN,
    opened_at: datetime | None = None,
    account_id: str = "acc_test",
    strategy_id: str | None = None,
) -> MagicMock:
    """Create a mock position with the given attributes."""
    pos = MagicMock(spec=Position)
    pos.id = "pos_test"
    pos.symbol = symbol
    pos.side = side
    pos.size = size
    pos.entry_price = entry_price
    pos.current_price = current_price
    pos.commission_paid = commission_paid
    pos.pnl_usdt = pnl_usdt
    pos.pnl_pct = pnl_pct
    pos.status = status
    pos.opened_at = opened_at or datetime.now(timezone.utc)
    pos.closed_at = None
    pos.exit_price = None
    pos.account_id = account_id
    pos.strategy_id = strategy_id
    return pos


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock DataStore."""
    store = MagicMock()
    store.get_open_positions = MagicMock(return_value=[])
    store.save_position = MagicMock(side_effect=lambda p: p)
    store.update_position = MagicMock(side_effect=lambda pid, **kw: _make_position(**kw) if kw else None)
    store.get_strategy = MagicMock(return_value=None)
    return store


@pytest.fixture
def tracker(mock_store: MagicMock) -> PositionTracker:
    """Create a PositionTracker with mocked DataStore."""
    return PositionTracker(data_store=mock_store)


# ---------------------------------------------------------------------------
# Test: Initialization
# ---------------------------------------------------------------------------


class TestInitialization:
    """Tests for PositionTracker initialization and cache loading."""

    @pytest.mark.asyncio
    async def test_initialize_loads_open_positions(self, mock_store: MagicMock) -> None:
        """Test that initialize() loads open positions into cache."""
        pos1 = _make_position(symbol="BTCUSDT")
        pos2 = _make_position(symbol="ETHUSDT")
        mock_store.get_open_positions = MagicMock(return_value=[pos1, pos2])

        tracker = PositionTracker(data_store=mock_store)
        await tracker.initialize()

        assert len(tracker._positions) == 2
        assert "BTCUSDT" in tracker._positions
        assert "ETHUSDT" in tracker._positions

    @pytest.mark.asyncio
    async def test_initialize_empty(self, tracker: PositionTracker) -> None:
        """Test initialize with no open positions."""
        await tracker.initialize()
        assert len(tracker._positions) == 0


# ---------------------------------------------------------------------------
# Test: Side conversion
# ---------------------------------------------------------------------------


class TestSideConversion:
    """Tests for trade side to position side conversion."""

    def test_buy_maps_to_long(self) -> None:
        result = PositionTracker._trade_side_to_position_side(OrderSide.BUY)
        assert result == PositionSide.LONG

    def test_sell_maps_to_short(self) -> None:
        result = PositionTracker._trade_side_to_position_side(OrderSide.SELL)
        assert result == PositionSide.SHORT


# ---------------------------------------------------------------------------
# Test: Trade data validation
# ---------------------------------------------------------------------------


class TestTradeValidation:
    """Tests for _validate_trade_data."""

    def test_nan_price_raises(self) -> None:
        trade = _make_trade(price=float("nan"))
        with pytest.raises(ValueError, match="NaN"):
            PositionTracker._validate_trade_data(trade)

    def test_inf_price_raises(self) -> None:
        trade = _make_trade(price=float("inf"))
        with pytest.raises(ValueError, match="Infinity"):
            PositionTracker._validate_trade_data(trade)

    def test_nan_quantity_raises(self) -> None:
        trade = _make_trade(quantity=float("nan"))
        with pytest.raises(ValueError, match="NaN"):
            PositionTracker._validate_trade_data(trade)

    def test_zero_quantity_raises(self) -> None:
        trade = _make_trade(quantity=0.0)
        with pytest.raises(ValueError, match="positive"):
            PositionTracker._validate_trade_data(trade)

    def test_negative_quantity_raises(self) -> None:
        trade = _make_trade(quantity=-1.0)
        with pytest.raises(ValueError, match="positive"):
            PositionTracker._validate_trade_data(trade)


# ---------------------------------------------------------------------------
# Test: Open position
# ---------------------------------------------------------------------------


class TestOpenPosition:
    """Tests for opening new positions from fills."""

    @pytest.mark.asyncio
    async def test_open_long_from_buy(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """BUY fill with no existing position opens a LONG."""
        trade = _make_trade(side=OrderSide.BUY, quantity=0.5, price=45000.0, commission=5.0)

        _position = await tracker.process_fill(trade, strategy_id="strat_1")

        mock_store.save_position.assert_called_once()
        saved = mock_store.save_position.call_args[0][0]
        assert saved.side == PositionSide.LONG
        assert saved.size == 0.5
        assert saved.entry_price == 45000.0
        assert saved.commission_paid == 5.0
        assert saved.status == PositionStatus.OPEN
        assert "BTCUSDT" in tracker._positions

    @pytest.mark.asyncio
    async def test_open_short_from_sell(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """SELL fill with no existing position opens a SHORT."""
        trade = _make_trade(side=OrderSide.SELL, quantity=1.0, price=2500.0, symbol="ETHUSDT")

        _position = await tracker.process_fill(trade)

        saved = mock_store.save_position.call_args[0][0]
        assert saved.side == PositionSide.SHORT
        assert saved.size == 1.0
        assert "ETHUSDT" in tracker._positions

    @pytest.mark.asyncio
    async def test_open_position_storage_error(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Database failure during open raises PositionStorageError."""
        mock_store.save_position = MagicMock(side_effect=Exception("DB down"))
        trade = _make_trade()

        with pytest.raises(PositionStorageError):
            await tracker.process_fill(trade)


# ---------------------------------------------------------------------------
# Test: Add to position
# ---------------------------------------------------------------------------


class TestAddToPosition:
    """Tests for adding to an existing position."""

    @pytest.mark.asyncio
    async def test_add_calculates_weighted_average(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Adding to a LONG should compute weighted average entry price."""
        existing = _make_position(
            size=0.5, entry_price=45000.0, commission_paid=5.0
        )
        tracker._positions["BTCUSDT"] = existing

        # Create an updated position that update_position returns
        updated = _make_position(
            size=1.0,
            entry_price=45500.0,  # (0.5*45000 + 0.5*46000) / 1.0 = 45500
            commission_paid=10.0,
        )
        mock_store.update_position = MagicMock(return_value=updated)

        trade = _make_trade(side=OrderSide.BUY, quantity=0.5, price=46000.0, commission=5.0)
        _result = await tracker.process_fill(trade)

        # Verify correct calculation passed to update
        call_kwargs = mock_store.update_position.call_args
        assert call_kwargs[0][0] == "pos_test"  # position_id
        assert abs(call_kwargs[1]["size"] - 1.0) < 0.001
        assert abs(call_kwargs[1]["entry_price"] - 45500.0) < 0.001
        assert abs(call_kwargs[1]["commission_paid"] - 10.0) < 0.001

    @pytest.mark.asyncio
    async def test_add_storage_error(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Database failure during add raises PositionStorageError."""
        existing = _make_position()
        tracker._positions["BTCUSDT"] = existing
        mock_store.update_position = MagicMock(side_effect=Exception("DB error"))

        trade = _make_trade(side=OrderSide.BUY)
        with pytest.raises(PositionStorageError):
            await tracker.process_fill(trade)


# ---------------------------------------------------------------------------
# Test: Reduce / close position
# ---------------------------------------------------------------------------


class TestReducePosition:
    """Tests for partial and full position closes."""

    @pytest.mark.asyncio
    async def test_partial_close_long(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Selling half a LONG position realizes partial P&L."""
        existing = _make_position(
            side=PositionSide.LONG,
            size=1.0,
            entry_price=45000.0,
            commission_paid=5.0,
            pnl_usdt=0.0,
        )
        tracker._positions["BTCUSDT"] = existing

        updated = _make_position(size=0.5, pnl_usdt=490.0)
        mock_store.update_position = MagicMock(return_value=updated)

        # Sell 0.5 at 46000 -> realized = (46000-45000)*0.5 - 5 = 495
        trade = _make_trade(side=OrderSide.SELL, quantity=0.5, price=46000.0, commission=5.0)
        _result = await tracker.process_fill(trade)

        call_kwargs = mock_store.update_position.call_args[1]
        assert abs(call_kwargs["size"] - 0.5) < 0.001
        # Realized PnL: (46000-45000)*0.5 - 5 = 495
        assert abs(call_kwargs["pnl_usdt"] - 495.0) < 0.01
        # Position should still be in cache
        assert "BTCUSDT" in tracker._positions

    @pytest.mark.asyncio
    async def test_full_close_long(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Selling entire LONG position closes it and removes from cache."""
        existing = _make_position(
            side=PositionSide.LONG,
            size=0.5,
            entry_price=45000.0,
            commission_paid=5.0,
            pnl_usdt=0.0,
        )
        tracker._positions["BTCUSDT"] = existing

        updated = _make_position(
            size=0.0, status=PositionStatus.CLOSED, pnl_usdt=495.0
        )
        mock_store.update_position = MagicMock(return_value=updated)

        trade = _make_trade(side=OrderSide.SELL, quantity=0.5, price=46000.0, commission=5.0)
        _result = await tracker.process_fill(trade)

        call_kwargs = mock_store.update_position.call_args[1]
        assert call_kwargs["status"] == PositionStatus.CLOSED
        assert call_kwargs.get("exit_price") == 46000.0
        # Removed from cache after full close
        assert "BTCUSDT" not in tracker._positions

    @pytest.mark.asyncio
    async def test_full_close_short(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Buying back entire SHORT position closes it."""
        existing = _make_position(
            side=PositionSide.SHORT,
            size=1.0,
            entry_price=2500.0,
            commission_paid=3.0,
            pnl_usdt=0.0,
            symbol="ETHUSDT",
        )
        tracker._positions["ETHUSDT"] = existing

        updated = _make_position(
            size=0.0, status=PositionStatus.CLOSED, symbol="ETHUSDT"
        )
        mock_store.update_position = MagicMock(return_value=updated)

        # BUY back at 2400 -> realized = (2500-2400)*1.0 - 2.0 = 98
        trade = _make_trade(side=OrderSide.BUY, quantity=1.0, price=2400.0, commission=2.0, symbol="ETHUSDT")
        _result = await tracker.process_fill(trade)

        call_kwargs = mock_store.update_position.call_args[1]
        assert call_kwargs["status"] == PositionStatus.CLOSED
        assert abs(call_kwargs["pnl_usdt"] - 98.0) < 0.01
        assert "ETHUSDT" not in tracker._positions

    @pytest.mark.asyncio
    async def test_over_close_prevented(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Fill quantity larger than position size should close at position size."""
        existing = _make_position(
            side=PositionSide.LONG,
            size=0.3,
            entry_price=45000.0,
            pnl_usdt=0.0,
        )
        tracker._positions["BTCUSDT"] = existing

        updated = _make_position(size=0.0, status=PositionStatus.CLOSED)
        mock_store.update_position = MagicMock(return_value=updated)

        # Sell 0.5 when only 0.3 exists - should use min(0.5, 0.3) = 0.3
        trade = _make_trade(side=OrderSide.SELL, quantity=0.5, price=46000.0, commission=2.0)
        _result = await tracker.process_fill(trade)

        call_kwargs = mock_store.update_position.call_args[1]
        # Should be fully closed, not negative size
        assert call_kwargs["status"] == PositionStatus.CLOSED


# ---------------------------------------------------------------------------
# Test: Unrealized P&L calculations (Critical Invariant #3)
# ---------------------------------------------------------------------------


class TestUnrealizedPnL:
    """Tests for unrealized P&L calculations including all mandatory cases."""

    def test_long_profit(self) -> None:
        """LONG position in profit: (46000-45000)*0.5 - 5 = 495."""
        pos = _make_position(
            side=PositionSide.LONG, size=0.5,
            entry_price=45000.0, commission_paid=5.0,
        )
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 46000.0)
        assert abs(pnl - 495.0) < 0.01

    def test_long_loss(self) -> None:
        """LONG position in loss: (44000-45000)*0.5 - 5 = -505."""
        pos = _make_position(
            side=PositionSide.LONG, size=0.5,
            entry_price=45000.0, commission_paid=5.0,
        )
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 44000.0)
        assert abs(pnl - (-505.0)) < 0.01

    def test_short_profit(self) -> None:
        """SHORT position in profit: (2500-2400)*1.0 - 3 = 97."""
        pos = _make_position(
            side=PositionSide.SHORT, size=1.0,
            entry_price=2500.0, commission_paid=3.0,
        )
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 2400.0)
        assert abs(pnl - 97.0) < 0.01

    def test_short_loss(self) -> None:
        """SHORT position in loss: (2500-2600)*1.0 - 3 = -103."""
        pos = _make_position(
            side=PositionSide.SHORT, size=1.0,
            entry_price=2500.0, commission_paid=3.0,
        )
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 2600.0)
        assert abs(pnl - (-103.0)) < 0.01

    def test_nan_price_returns_nan(self) -> None:
        """NaN current price returns NaN P&L."""
        pos = _make_position()
        pnl = PositionTracker.calculate_unrealized_pnl(pos, float("nan"))
        assert math.isnan(pnl)

    def test_inf_price_returns_nan(self) -> None:
        """Infinity current price returns NaN P&L."""
        pos = _make_position()
        pnl = PositionTracker.calculate_unrealized_pnl(pos, float("inf"))
        assert math.isnan(pnl)

    def test_zero_size_returns_zero(self) -> None:
        """Zero-size position returns 0 P&L."""
        pos = _make_position(size=0.001)
        # Size is checked as <= 0, so 0 should return 0
        pos.size = 0.0
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 46000.0)
        assert pnl == 0.0

    def test_zero_commission(self) -> None:
        """Position with zero commission."""
        pos = _make_position(
            side=PositionSide.LONG, size=1.0,
            entry_price=100.0, commission_paid=0.0,
        )
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 110.0)
        assert abs(pnl - 10.0) < 0.01


# ---------------------------------------------------------------------------
# Test: Return percentage
# ---------------------------------------------------------------------------


class TestReturnPct:
    """Tests for return percentage calculations."""

    def test_positive_return(self) -> None:
        """Long 0.5 BTC @ 45000, commission 5, price 46000 -> ~2.2%."""
        pos = _make_position(
            side=PositionSide.LONG, size=0.5,
            entry_price=45000.0, commission_paid=5.0,
        )
        pct = PositionTracker.calculate_return_pct(pos, 46000.0)
        # (495 / 22500) * 100 = 2.2%
        assert abs(pct - 2.2) < 0.01

    def test_negative_return(self) -> None:
        pos = _make_position(
            side=PositionSide.LONG, size=0.5,
            entry_price=45000.0, commission_paid=5.0,
        )
        pct = PositionTracker.calculate_return_pct(pos, 44000.0)
        assert pct < 0

    def test_nan_price_returns_nan(self) -> None:
        pos = _make_position()
        pct = PositionTracker.calculate_return_pct(pos, float("nan"))
        assert math.isnan(pct)


# ---------------------------------------------------------------------------
# Test: Realized P&L
# ---------------------------------------------------------------------------


class TestRealizedPnL:
    """Tests for realized P&L accessor."""

    def test_returns_pnl_usdt(self) -> None:
        pos = _make_position(pnl_usdt=150.0)
        assert PositionTracker.calculate_realized_pnl(pos) == 150.0

    def test_zero_pnl(self) -> None:
        pos = _make_position(pnl_usdt=0.0)
        assert PositionTracker.calculate_realized_pnl(pos) == 0.0


# ---------------------------------------------------------------------------
# Test: Position queries
# ---------------------------------------------------------------------------


class TestPositionQueries:
    """Tests for get_position and get_all_positions."""

    @pytest.mark.asyncio
    async def test_get_position_found(self, tracker: PositionTracker) -> None:
        pos = _make_position(symbol="BTCUSDT")
        tracker._positions["BTCUSDT"] = pos
        result = await tracker.get_position("BTCUSDT")
        assert result is pos

    @pytest.mark.asyncio
    async def test_get_position_not_found(self, tracker: PositionTracker) -> None:
        result = await tracker.get_position("XYZUSDT")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_positions(self, tracker: PositionTracker) -> None:
        tracker._positions["BTCUSDT"] = _make_position(symbol="BTCUSDT")
        tracker._positions["ETHUSDT"] = _make_position(symbol="ETHUSDT")
        result = await tracker.get_all_positions()
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Test: Position sync
# ---------------------------------------------------------------------------


class TestPositionSync:
    """Tests for position synchronization with exchange balances."""

    @pytest.mark.asyncio
    async def test_sync_no_discrepancy(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Sync with matching balances reports all synced."""
        pos = _make_position(symbol="BTCUSDT", size=0.5)
        tracker._positions["BTCUSDT"] = pos

        engine = AsyncMock()
        engine.get_account_balance = AsyncMock(return_value=[
            Balance(asset="BTC", free=0.5, locked=0.0, total=0.5),
        ])

        result = await tracker.sync_positions(engine)
        assert result.total_positions == 1
        assert result.synced_positions == 1
        assert result.corrected_positions == 0

    @pytest.mark.asyncio
    async def test_sync_with_discrepancy(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """Sync with mismatched balance corrects local position."""
        pos = _make_position(symbol="BTCUSDT", size=0.5)
        tracker._positions["BTCUSDT"] = pos

        updated = _make_position(symbol="BTCUSDT", size=0.6)
        mock_store.update_position = MagicMock(return_value=updated)

        engine = AsyncMock()
        engine.get_account_balance = AsyncMock(return_value=[
            Balance(asset="BTC", free=0.4, locked=0.2, total=0.6),
        ])

        result = await tracker.sync_positions(engine)
        assert result.total_positions == 1
        assert result.corrected_positions == 1
        assert len(result.discrepancies) == 1

    @pytest.mark.asyncio
    async def test_sync_balance_fetch_failure(self, tracker: PositionTracker) -> None:
        """Sync gracefully handles balance fetch failure."""
        tracker._positions["BTCUSDT"] = _make_position()

        engine = AsyncMock()
        engine.get_account_balance = AsyncMock(side_effect=Exception("API error"))

        result = await tracker.sync_positions(engine)
        assert result.total_positions == 1
        assert result.synced_positions == 0


# ---------------------------------------------------------------------------
# Test: Staleness monitoring
# ---------------------------------------------------------------------------


class TestStaleness:
    """Tests for position staleness checking."""

    def test_fresh_position_is_ok(self, tracker: PositionTracker) -> None:
        """Recently opened position has OK status."""
        pos = _make_position(opened_at=datetime.now(timezone.utc))
        result = tracker.check_staleness(pos, StrategyType.MEAN_REVERSION)
        assert result.status == "OK"
        assert not result.should_warn
        assert not result.should_review
        assert not result.should_close

    def test_day_trading_warning_threshold(self, tracker: PositionTracker) -> None:
        """Day trading position held >24h triggers WARNING."""
        opened = datetime.now(timezone.utc) - timedelta(hours=25)
        pos = _make_position(opened_at=opened)
        result = tracker.check_staleness(pos, StrategyType.INTRADAY_PULLBACK)
        assert result.status == "WARNING"
        assert result.should_warn

    def test_day_trading_review_threshold(self, tracker: PositionTracker) -> None:
        """Day trading position held >48h triggers REVIEW_REQUIRED."""
        opened = datetime.now(timezone.utc) - timedelta(hours=49)
        pos = _make_position(opened_at=opened)
        result = tracker.check_staleness(pos, StrategyType.VOLATILITY_BREAKOUT)
        assert result.status == "REVIEW_REQUIRED"
        assert result.should_review

    def test_day_trading_max_hold_exceeded(self, tracker: PositionTracker) -> None:
        """Day trading position held >72h triggers MAX_HOLD_EXCEEDED."""
        opened = datetime.now(timezone.utc) - timedelta(hours=73)
        pos = _make_position(opened_at=opened)
        result = tracker.check_staleness(pos, StrategyType.MEAN_REVERSION)
        assert result.status == "MAX_HOLD_EXCEEDED"
        assert result.should_close

    def test_swing_trading_thresholds(self, tracker: PositionTracker) -> None:
        """Swing trading uses 7d/14d/30d thresholds."""
        # 8 days old - should be WARNING
        opened = datetime.now(timezone.utc) - timedelta(days=8)
        pos = _make_position(opened_at=opened)
        result = tracker.check_staleness(pos, StrategyType.TREND_FOLLOWING)
        assert result.status == "WARNING"

    def test_position_trading_thresholds(self, tracker: PositionTracker) -> None:
        """Position trading uses 30d/60d/90d thresholds."""
        # 35 days old - should be WARNING
        opened = datetime.now(timezone.utc) - timedelta(days=35)
        pos = _make_position(opened_at=opened)
        result = tracker.check_staleness(pos, StrategyType.TREND_BREAKOUT)
        assert result.status == "WARNING"

    def test_profitable_position_gets_extension(self, tracker: PositionTracker) -> None:
        """Profitable position gets 1.5x threshold extension."""
        # 25h old day trading position - WARNING without profit, OK with profit
        opened = datetime.now(timezone.utc) - timedelta(hours=25)
        pos = _make_position(opened_at=opened)

        # Without profit -> WARNING (24h threshold)
        result_loss = tracker.check_staleness(
            pos, StrategyType.MEAN_REVERSION, unrealized_pnl=-100.0
        )
        assert result_loss.status == "WARNING"

        # With profit -> OK (24*1.5=36h threshold)
        result_profit = tracker.check_staleness(
            pos, StrategyType.MEAN_REVERSION, unrealized_pnl=100.0
        )
        assert result_profit.status == "OK"

    def test_default_strategy_type_is_swing(self, tracker: PositionTracker) -> None:
        """None strategy type defaults to swing_trading thresholds."""
        opened = datetime.now(timezone.utc) - timedelta(days=8)
        pos = _make_position(opened_at=opened)
        result = tracker.check_staleness(pos, strategy_type=None)
        assert result.status == "WARNING"

    def test_days_remaining_calculation(self, tracker: PositionTracker) -> None:
        """Days remaining is correctly calculated."""
        now = datetime.now(timezone.utc)
        opened = now - timedelta(hours=12)
        pos = _make_position(opened_at=opened)
        result = tracker.check_staleness(
            pos, StrategyType.MEAN_REVERSION, now=now
        )
        # Day trading max = 72h, held 12h, remaining = 60h = 2.5 days
        assert abs(result.days_remaining - 2.5) < 0.01

    def test_naive_datetime_handled(self, tracker: PositionTracker) -> None:
        """Naive datetimes from DB are treated as UTC."""
        # Create position with naive datetime
        opened = datetime.now(timezone.utc).replace(tzinfo=None)
        pos = _make_position(opened_at=opened)
        # Should not raise
        result = tracker.check_staleness(pos, StrategyType.MEAN_REVERSION)
        assert result.status == "OK"

    @pytest.mark.asyncio
    async def test_process_stale_positions(self, tracker: PositionTracker, mock_store: MagicMock) -> None:
        """process_stale_positions checks all open positions."""
        pos = _make_position(
            opened_at=datetime.now(timezone.utc) - timedelta(hours=25)
        )
        tracker._positions["BTCUSDT"] = pos

        results = await tracker.process_stale_positions()
        assert len(results) == 1
