"""Integration tests for position lifecycle with PositionTracker.

Tests the full lifecycle: open -> add-to -> partial close -> full close
with actual P&L calculations verified against manual computations.

Phase 4B: Position Tracking & Execution Quality
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.core.execution.position_tracker import PositionTracker
from src.data.models.order import OrderSide
from src.data.models.position import Position, PositionSide, PositionStatus
from src.data.models.trade import Trade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trade_mock(
    symbol: str = "BTCUSDT",
    side: OrderSide = OrderSide.BUY,
    quantity: float = 1.0,
    price: float = 45000.0,
    commission: float = 5.0,
    account_id: str = "acc_int",
    order_id: str = "ord_int",
) -> MagicMock:
    """Create a mock Trade for integration tests."""
    trade = MagicMock(spec=Trade)
    trade.symbol = symbol
    trade.side = side
    trade.quantity = quantity
    trade.price = price
    trade.commission = commission
    trade.account_id = account_id
    trade.order_id = order_id
    trade.executed_at = datetime.now(timezone.utc)
    trade.id = f"trd_{side.value}_{price}"
    return trade


class PositionStore:
    """In-memory position store for integration tests.

    Simulates DataStore's save_position and update_position behavior
    without requiring a real database.
    """

    def __init__(self) -> None:
        self._positions: dict[str, MagicMock] = {}

    def get_open_positions(self) -> list[MagicMock]:
        return [p for p in self._positions.values() if p.status == PositionStatus.OPEN]

    def save_position(self, position: MagicMock) -> MagicMock:
        self._positions[position.id] = position
        return position

    def update_position(self, position_id: str, **kwargs: object) -> MagicMock | None:
        pos = self._positions.get(position_id)
        if pos is None:
            return None
        for key, value in kwargs.items():
            setattr(pos, key, value)
        return pos

    def get_strategy(self, strategy_id: str) -> None:
        return None


# ---------------------------------------------------------------------------
# Tests: Full position lifecycle
# ---------------------------------------------------------------------------


class TestPositionLifecycle:
    """Full lifecycle tests: open -> add -> partial close -> full close."""

    @pytest.mark.asyncio
    async def test_long_lifecycle(self) -> None:
        """Test complete LONG position lifecycle with P&L verification.

        Steps:
            1. BUY 0.5 BTC @ $45,000 (commission $5) -> Open LONG
            2. BUY 0.5 BTC @ $46,000 (commission $5) -> Add to LONG
            3. SELL 0.3 BTC @ $47,000 (commission $3) -> Partial close
            4. SELL 0.7 BTC @ $48,000 (commission $4) -> Full close

        Manual P&L calculations for verification:
            After step 2: avg_entry = (0.5*45000 + 0.5*46000)/1.0 = $45,500
            Step 3 realized: (47000 - 45500) * 0.3 - 3 = $447
            Step 4 realized: (48000 - 45500) * 0.7 - 4 = $1,746
            Total realized: $447 + $1,746 = $2,193
        """
        store = PositionStore()
        tracker = PositionTracker(data_store=store)  # type: ignore[arg-type]
        await tracker.initialize()

        # Step 1: Open LONG 0.5 BTC @ $45,000
        trade1 = _make_trade_mock(
            side=OrderSide.BUY, quantity=0.5, price=45000.0, commission=5.0
        )
        pos = await tracker.process_fill(trade1, strategy_id="strat_1")

        assert pos.side == PositionSide.LONG
        assert abs(pos.size - 0.5) < 1e-8
        assert abs(pos.entry_price - 45000.0) < 0.01
        assert abs(pos.commission_paid - 5.0) < 0.01
        assert pos.status == PositionStatus.OPEN

        # Step 2: Add 0.5 BTC @ $46,000
        trade2 = _make_trade_mock(
            side=OrderSide.BUY, quantity=0.5, price=46000.0, commission=5.0
        )
        pos = await tracker.process_fill(trade2)

        assert abs(pos.size - 1.0) < 1e-8
        # Weighted avg: (0.5*45000 + 0.5*46000) / 1.0 = 45500
        assert abs(pos.entry_price - 45500.0) < 0.01
        assert abs(pos.commission_paid - 10.0) < 0.01
        assert pos.status == PositionStatus.OPEN

        # Verify unrealized P&L at $47,000
        unrealized = PositionTracker.calculate_unrealized_pnl(pos, 47000.0)
        # (47000 - 45500) * 1.0 - 10 = 1490
        assert abs(unrealized - 1490.0) < 0.01

        # Step 3: Partial close - SELL 0.3 @ $47,000
        trade3 = _make_trade_mock(
            side=OrderSide.SELL, quantity=0.3, price=47000.0, commission=3.0
        )
        pos = await tracker.process_fill(trade3)

        assert abs(pos.size - 0.7) < 1e-8
        # Realized: (47000 - 45500) * 0.3 - 3 = 447
        assert abs(pos.pnl_usdt - 447.0) < 0.01
        assert pos.status == PositionStatus.OPEN
        assert "BTCUSDT" in tracker._positions

        # Step 4: Full close - SELL 0.7 @ $48,000
        trade4 = _make_trade_mock(
            side=OrderSide.SELL, quantity=0.7, price=48000.0, commission=4.0
        )
        pos = await tracker.process_fill(trade4)

        assert pos.status == PositionStatus.CLOSED
        assert abs(pos.size - 0.0) < 1e-8
        assert pos.exit_price == 48000.0
        # Total realized: 447 + (48000-45500)*0.7 - 4 = 447 + 1746 = 2193
        assert abs(pos.pnl_usdt - 2193.0) < 0.01
        # Removed from cache
        assert "BTCUSDT" not in tracker._positions

    @pytest.mark.asyncio
    async def test_short_lifecycle(self) -> None:
        """Test complete SHORT position lifecycle.

        Steps:
            1. SELL 1.0 ETH @ $2,500 (commission $3) -> Open SHORT
            2. BUY 0.5 ETH @ $2,400 (commission $2) -> Partial close
            3. BUY 0.5 ETH @ $2,300 (commission $2) -> Full close

        Manual P&L:
            Step 2 realized: (2500 - 2400) * 0.5 - 2 = $48
            Step 3 realized: (2500 - 2300) * 0.5 - 2 = $98
            Total: $146
        """
        store = PositionStore()
        tracker = PositionTracker(data_store=store)  # type: ignore[arg-type]
        await tracker.initialize()

        # Step 1: Open SHORT
        trade1 = _make_trade_mock(
            symbol="ETHUSDT", side=OrderSide.SELL,
            quantity=1.0, price=2500.0, commission=3.0,
        )
        pos = await tracker.process_fill(trade1)
        assert pos.side == PositionSide.SHORT
        assert abs(pos.size - 1.0) < 1e-8

        # Verify unrealized P&L at $2,400
        unrealized = PositionTracker.calculate_unrealized_pnl(pos, 2400.0)
        # (2500 - 2400) * 1.0 - 3 = 97
        assert abs(unrealized - 97.0) < 0.01

        # Step 2: Partial close
        trade2 = _make_trade_mock(
            symbol="ETHUSDT", side=OrderSide.BUY,
            quantity=0.5, price=2400.0, commission=2.0,
        )
        pos = await tracker.process_fill(trade2)
        assert abs(pos.size - 0.5) < 1e-8
        assert abs(pos.pnl_usdt - 48.0) < 0.01

        # Step 3: Full close
        trade3 = _make_trade_mock(
            symbol="ETHUSDT", side=OrderSide.BUY,
            quantity=0.5, price=2300.0, commission=2.0,
        )
        pos = await tracker.process_fill(trade3)

        assert pos.status == PositionStatus.CLOSED
        # Total: 48 + (2500-2300)*0.5 - 2 = 48 + 98 = 146
        assert abs(pos.pnl_usdt - 146.0) < 0.01
        assert "ETHUSDT" not in tracker._positions

    @pytest.mark.asyncio
    async def test_losing_trade_lifecycle(self) -> None:
        """Test lifecycle with losses (negative P&L).

        Steps:
            1. BUY 1.0 BTC @ $50,000 (commission $10) -> Open LONG
            2. SELL 1.0 BTC @ $48,000 (commission $10) -> Full close at loss

        Manual P&L:
            Realized: (48000 - 50000) * 1.0 - 10 = -$2,010
        """
        store = PositionStore()
        tracker = PositionTracker(data_store=store)  # type: ignore[arg-type]
        await tracker.initialize()

        # Open LONG
        trade1 = _make_trade_mock(
            side=OrderSide.BUY, quantity=1.0, price=50000.0, commission=10.0
        )
        pos = await tracker.process_fill(trade1)

        # Close at loss
        trade2 = _make_trade_mock(
            side=OrderSide.SELL, quantity=1.0, price=48000.0, commission=10.0
        )
        pos = await tracker.process_fill(trade2)

        assert pos.status == PositionStatus.CLOSED
        assert abs(pos.pnl_usdt - (-2010.0)) < 0.01

    @pytest.mark.asyncio
    async def test_multiple_symbols_independent(self) -> None:
        """Positions for different symbols are independent."""
        store = PositionStore()
        tracker = PositionTracker(data_store=store)  # type: ignore[arg-type]
        await tracker.initialize()

        # Open BTC LONG
        btc_trade = _make_trade_mock(
            symbol="BTCUSDT", side=OrderSide.BUY,
            quantity=0.1, price=45000.0, commission=1.0,
        )
        btc_pos = await tracker.process_fill(btc_trade)

        # Open ETH LONG
        eth_trade = _make_trade_mock(
            symbol="ETHUSDT", side=OrderSide.BUY,
            quantity=1.0, price=2500.0, commission=0.5,
        )
        eth_pos = await tracker.process_fill(eth_trade)

        assert len(tracker._positions) == 2
        assert "BTCUSDT" in tracker._positions
        assert "ETHUSDT" in tracker._positions

        # Close BTC - ETH should remain
        btc_close = _make_trade_mock(
            symbol="BTCUSDT", side=OrderSide.SELL,
            quantity=0.1, price=46000.0, commission=1.0,
        )
        await tracker.process_fill(btc_close)

        assert "BTCUSDT" not in tracker._positions
        assert "ETHUSDT" in tracker._positions
        assert len(tracker._positions) == 1


# ---------------------------------------------------------------------------
# Tests: P&L accuracy
# ---------------------------------------------------------------------------


class TestPnLAccuracy:
    """Verify P&L calculations with precise manual computations."""

    def test_long_unrealized_with_commission(self) -> None:
        """LONG unrealized P&L = (current - entry) * size - commission."""
        pos = MagicMock(spec=Position)
        pos.id = "pos_acc_1"
        pos.side = PositionSide.LONG
        pos.size = 2.0
        pos.entry_price = 30000.0
        pos.commission_paid = 20.0

        # At $35,000: (35000-30000)*2.0 - 20 = 9980
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 35000.0)
        assert abs(pnl - 9980.0) < 0.01

    def test_short_unrealized_with_commission(self) -> None:
        """SHORT unrealized P&L = (entry - current) * size - commission."""
        pos = MagicMock(spec=Position)
        pos.id = "pos_acc_2"
        pos.side = PositionSide.SHORT
        pos.size = 5.0
        pos.entry_price = 2000.0
        pos.commission_paid = 10.0

        # At $1,800: (2000-1800)*5.0 - 10 = 990
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 1800.0)
        assert abs(pnl - 990.0) < 0.01

    def test_return_pct_formula(self) -> None:
        """Return % = (unrealized_pnl / (entry * size)) * 100."""
        pos = MagicMock(spec=Position)
        pos.id = "pos_ret_1"
        pos.side = PositionSide.LONG
        pos.size = 0.5
        pos.entry_price = 45000.0
        pos.commission_paid = 5.0

        # Unrealized at 46000: (46000-45000)*0.5 - 5 = 495
        # Return: (495 / (45000*0.5)) * 100 = 2.2%
        pct = PositionTracker.calculate_return_pct(pos, 46000.0)
        assert abs(pct - 2.2) < 0.01

    def test_breakeven_with_commission(self) -> None:
        """Commission creates a cost that must be overcome for breakeven."""
        pos = MagicMock(spec=Position)
        pos.id = "pos_be_1"
        pos.side = PositionSide.LONG
        pos.size = 1.0
        pos.entry_price = 100.0
        pos.commission_paid = 1.0

        # At entry price: (100-100)*1.0 - 1 = -1 (not breakeven due to commission)
        pnl = PositionTracker.calculate_unrealized_pnl(pos, 100.0)
        assert pnl < 0
        assert abs(pnl - (-1.0)) < 0.01
