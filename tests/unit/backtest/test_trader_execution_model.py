"""Tests for SimulatedTrader execution-model behavior (spot long-only vs futures).

Covers DEC-2026-05-28-001:
  - allow_shorts=False (spot): SHORT signals never open a position.
  - allow_shorts=True (futures): SHORT signals open a short.
  - funding_rate_per_8h: reduces realized P&L over the hold period.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


from src.core.strategy.backtest.portfolio import PortfolioState
from src.core.strategy.backtest.trader import SimulatedTrader
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.signals import TradingSignal
from src.data.market_data import OHLCV
from src.data.models.signal import SignalDirection


def _bar(price: float, ts: datetime) -> OHLCV:
    """Build a flat OHLCV bar at a single price."""
    return OHLCV(
        timestamp=ts, open=price, high=price, low=price, close=price, volume=1000.0,
    )


def _signal(direction: SignalDirection, price: float, ts: datetime) -> TradingSignal:
    """Build a minimal trading signal."""
    return TradingSignal(
        direction=direction, symbol="BTCUSDT", price=price, timestamp=ts,
    )


TS = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)


class TestSpotLongOnly:
    """allow_shorts=False — spot can't short."""

    def test_short_signal_does_not_open_when_flat(self) -> None:
        """A SHORT signal in spot mode must NOT open a position."""
        trader = SimulatedTrader()
        portfolio = PortfolioState(initial_capital=10_000.0)
        config = BacktestConfig(allow_shorts=False)

        trader.execute_signal(
            signal=_signal(SignalDirection.SHORT, 42_000.0, TS),
            portfolio=portfolio,
            next_bar=_bar(42_000.0, TS + timedelta(hours=1)),
            config=config,
            allow_flip=False,
        )
        assert portfolio.has_position() is False

    def test_long_signal_still_opens(self) -> None:
        """A LONG signal in spot mode opens a long normally."""
        trader = SimulatedTrader()
        portfolio = PortfolioState(initial_capital=10_000.0)
        config = BacktestConfig(allow_shorts=False)

        trader.execute_signal(
            signal=_signal(SignalDirection.LONG, 42_000.0, TS),
            portfolio=portfolio,
            next_bar=_bar(42_000.0, TS + timedelta(hours=1)),
            config=config,
            allow_flip=False,
        )
        assert portfolio.has_position() is True
        assert portfolio.position is not None
        assert portfolio.position.direction == SignalDirection.LONG

    def test_short_signal_closes_existing_long(self) -> None:
        """A SHORT signal in spot mode exits a held long (close-only)."""
        trader = SimulatedTrader()
        portfolio = PortfolioState(initial_capital=10_000.0)
        config = BacktestConfig(allow_shorts=False)

        trader.execute_signal(
            signal=_signal(SignalDirection.LONG, 42_000.0, TS),
            portfolio=portfolio,
            next_bar=_bar(42_000.0, TS + timedelta(hours=1)),
            config=config,
            allow_flip=False,
        )
        assert portfolio.has_position() is True

        # SHORT signal should close the long and leave the book flat
        trader.execute_signal(
            signal=_signal(SignalDirection.SHORT, 43_000.0, TS + timedelta(hours=2)),
            portfolio=portfolio,
            next_bar=_bar(43_000.0, TS + timedelta(hours=3)),
            config=config,
            allow_flip=False,
        )
        assert portfolio.has_position() is False


class TestFuturesLongShort:
    """allow_shorts=True — futures can short."""

    def test_short_signal_opens_short(self) -> None:
        """A SHORT signal in futures mode opens a short position."""
        trader = SimulatedTrader()
        portfolio = PortfolioState(initial_capital=10_000.0)
        config = BacktestConfig(allow_shorts=True)

        trader.execute_signal(
            signal=_signal(SignalDirection.SHORT, 42_000.0, TS),
            portfolio=portfolio,
            next_bar=_bar(42_000.0, TS + timedelta(hours=1)),
            config=config,
            allow_flip=False,
        )
        assert portfolio.has_position() is True
        assert portfolio.position is not None
        assert portfolio.position.direction == SignalDirection.SHORT


class TestFundingCost:
    """funding_rate_per_8h reduces realized P&L over the hold period."""

    def _round_trip_pnl(self, funding_rate: float, hold_hours: int) -> float:
        """Open a long, hold, close at the same price; return realized P&L."""
        trader = SimulatedTrader()
        portfolio = PortfolioState(initial_capital=10_000.0)
        config = BacktestConfig(
            allow_shorts=True, funding_rate_per_8h=funding_rate,
        )
        trader.execute_signal(
            signal=_signal(SignalDirection.LONG, 100.0, TS),
            portfolio=portfolio,
            next_bar=_bar(100.0, TS + timedelta(hours=1)),
            config=config,
            allow_flip=True,
        )
        # Close at same price after hold_hours via an opposite signal
        trader.execute_signal(
            signal=_signal(SignalDirection.CLOSE, 100.0, TS + timedelta(hours=hold_hours)),
            portfolio=portfolio,
            next_bar=_bar(100.0, TS + timedelta(hours=hold_hours + 1)),
            config=config,
        )
        assert len(portfolio.trade_log) == 1
        return portfolio.trade_log[0].realized_pnl

    def test_funding_reduces_pnl(self) -> None:
        """A held position with funding > 0 realizes less than with funding = 0."""
        pnl_no_funding = self._round_trip_pnl(funding_rate=0.0, hold_hours=24)
        pnl_with_funding = self._round_trip_pnl(funding_rate=0.0001, hold_hours=24)
        assert pnl_with_funding < pnl_no_funding

    def test_longer_hold_costs_more_funding(self) -> None:
        """Funding scales with hold duration."""
        pnl_8h = self._round_trip_pnl(funding_rate=0.0001, hold_hours=8)
        pnl_48h = self._round_trip_pnl(funding_rate=0.0001, hold_hours=48)
        assert pnl_48h < pnl_8h
