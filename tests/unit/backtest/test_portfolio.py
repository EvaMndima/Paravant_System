"""Comprehensive unit tests for PortfolioState."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.core.strategy.backtest.portfolio import OpenPosition, PortfolioState
from src.core.strategy.backtest.types import BacktestConfig
from src.data.models.signal import SignalDirection


@pytest.fixture
def portfolio() -> PortfolioState:
    """Create a fresh portfolio with 10k capital."""
    return PortfolioState(initial_capital=10_000.0)


class TestPortfolioStateInit:
    """Tests for portfolio initialization."""

    def test_initial_values(self, portfolio: PortfolioState) -> None:
        """Portfolio should start with correct initial values."""
        assert portfolio.initial_capital == 10_000.0
        assert portfolio.cash == 10_000.0
        assert portfolio.has_position() is False
        assert portfolio.equity_curve == []
        assert portfolio.trade_log == []

    def test_get_total_value_no_position(self, portfolio: PortfolioState) -> None:
        """Total value without position should equal cash."""
        assert portfolio.get_total_value(current_price=50000.0) == 10_000.0

    def test_nan_capital_rejected(self) -> None:
        """NaN capital should raise ValueError."""
        with pytest.raises(ValueError, match="finite"):
            PortfolioState(initial_capital=float("nan"))

    def test_negative_capital_rejected(self) -> None:
        """Negative capital should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            PortfolioState(initial_capital=-100.0)

    def test_zero_capital_rejected(self) -> None:
        """Zero capital should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            PortfolioState(initial_capital=0.0)


class TestOpenPosition:
    """Tests for opening positions."""

    def test_open_long(self, portfolio: PortfolioState) -> None:
        """Opening a long position should deduct cash."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        assert portfolio.has_position() is True
        # cash = 10000 - (0.1 * 42000) - 4.2 = 10000 - 4200 - 4.2 = 5795.8
        assert portfolio.cash == pytest.approx(5795.8, abs=0.01)

    def test_open_short(self, portfolio: PortfolioState) -> None:
        """Opening a short position should deduct cash for margin."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.SHORT,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        assert portfolio.has_position() is True

    def test_cannot_open_when_position_exists(self, portfolio: PortfolioState) -> None:
        """Should raise when trying to open with existing position."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        with pytest.raises(ValueError, match="already have position"):
            portfolio.open_position(
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                quantity=0.1,
                fill_price=42000.0,
                commission=4.2,
                slippage_cost=2.1,
                timestamp=ts + timedelta(hours=1),
            )

    def test_insufficient_cash_rejected(self, portfolio: PortfolioState) -> None:
        """Should raise if cost exceeds available cash."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="Insufficient cash"):
            portfolio.open_position(
                symbol="BTCUSDT",
                direction=SignalDirection.LONG,
                quantity=1.0,
                fill_price=50000.0,
                commission=50.0,
                slippage_cost=25.0,
                timestamp=ts,
            )


class TestClosePosition:
    """Tests for closing positions."""

    def test_close_long_winning(self, portfolio: PortfolioState) -> None:
        """Closing a winning long trade should produce positive PnL."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        trade = portfolio.close_position(
            fill_price=42500.0,
            commission=4.25,
            slippage_cost=2.0,
            timestamp=ts + timedelta(hours=4),
        )
        assert trade.realized_pnl > 0
        assert trade.is_winner is True
        assert portfolio.has_position() is False

    def test_close_long_losing(self, portfolio: PortfolioState) -> None:
        """Closing a losing long trade should produce negative PnL."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        trade = portfolio.close_position(
            fill_price=41000.0,
            commission=4.1,
            slippage_cost=2.0,
            timestamp=ts + timedelta(hours=4),
        )
        assert trade.realized_pnl < 0
        assert trade.is_winner is False

    def test_close_short_winning(self, portfolio: PortfolioState) -> None:
        """Closing a winning short trade should produce positive PnL."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.SHORT,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        trade = portfolio.close_position(
            fill_price=41000.0,
            commission=4.1,
            slippage_cost=2.0,
            timestamp=ts + timedelta(hours=4),
        )
        assert trade.realized_pnl > 0

    def test_cannot_close_without_position(self, portfolio: PortfolioState) -> None:
        """Should raise when closing with no open position."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="no open position"):
            portfolio.close_position(
                fill_price=42000.0,
                commission=4.2,
                slippage_cost=0.0,
                timestamp=ts,
            )

    def test_trade_added_to_log(self, portfolio: PortfolioState) -> None:
        """Closed trade should be added to trade log."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        portfolio.close_position(
            fill_price=42500.0,
            commission=4.25,
            slippage_cost=2.0,
            timestamp=ts + timedelta(hours=2),
        )
        assert len(portfolio.trade_log) == 1
        assert portfolio.trade_log[0].symbol == "BTCUSDT"

    def test_cash_accounting_roundtrip(self, portfolio: PortfolioState) -> None:
        """Cash after a round-trip trade should reflect PnL."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        initial_cash = portfolio.cash
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        trade = portfolio.close_position(
            fill_price=42000.0,  # same price — break even before commissions
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts + timedelta(hours=2),
        )
        # Cash should be less than initial due to commissions
        assert portfolio.cash < initial_cash

    def test_cash_accounting_roundtrip_short_win(self, portfolio: PortfolioState) -> None:
        """Cash after a winning short round-trip must equal initial + realized_pnl."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        initial_cash = portfolio.cash
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.SHORT,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        trade = portfolio.close_position(
            fill_price=41000.0,  # price fell — SHORT profits
            commission=4.1,
            slippage_cost=2.0,
            timestamp=ts + timedelta(hours=4),
        )
        assert trade.realized_pnl > 0
        assert portfolio.cash == pytest.approx(initial_cash + trade.realized_pnl, abs=0.01)

    def test_cash_accounting_roundtrip_short_loss(self, portfolio: PortfolioState) -> None:
        """Cash after a losing short round-trip must equal initial + realized_pnl (negative)."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        initial_cash = portfolio.cash
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.SHORT,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        trade = portfolio.close_position(
            fill_price=43000.0,  # price rose — SHORT loses
            commission=4.3,
            slippage_cost=2.0,
            timestamp=ts + timedelta(hours=4),
        )
        assert trade.realized_pnl < 0
        assert portfolio.cash == pytest.approx(initial_cash + trade.realized_pnl, abs=0.01)


class TestEquityCurve:
    """Tests for equity curve recording."""

    def test_record_equity_no_position(self, portfolio: PortfolioState) -> None:
        """Equity with no position should equal cash."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        point = portfolio.record_equity(current_price=50000.0, timestamp=ts)
        assert point.equity == 10_000.0
        assert point.position_value == 0.0
        assert len(portfolio.equity_curve) == 1

    def test_record_equity_with_position(self, portfolio: PortfolioState) -> None:
        """Equity with position should include mark-to-market value."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        point = portfolio.record_equity(
            current_price=43000.0,
            timestamp=ts + timedelta(hours=1),
        )
        assert point.equity > portfolio.cash
        assert point.position_value > 0


class TestGetTotalValue:
    """Tests for total value calculations."""

    def test_with_long_position_price_up(self, portfolio: PortfolioState) -> None:
        """Total value should increase when price goes up for longs."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        initial_total = portfolio.get_total_value(42000.0)
        higher_total = portfolio.get_total_value(43000.0)
        assert higher_total > initial_total

    def test_with_long_position_price_down(self, portfolio: PortfolioState) -> None:
        """Total value should decrease when price goes down for longs."""
        ts = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        portfolio.open_position(
            symbol="BTCUSDT",
            direction=SignalDirection.LONG,
            quantity=0.1,
            fill_price=42000.0,
            commission=4.2,
            slippage_cost=2.1,
            timestamp=ts,
        )
        initial_total = portfolio.get_total_value(42000.0)
        lower_total = portfolio.get_total_value(41000.0)
        assert lower_total < initial_total

    def test_position_value_no_position(self, portfolio: PortfolioState) -> None:
        """Position value with no position should be 0."""
        assert portfolio.get_position_value(50000.0) == 0.0
