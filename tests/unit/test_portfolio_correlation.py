"""Unit tests for portfolio correlation limit checks (PRD §2.2.1 Feature A).

Tests the check_portfolio_correlation() pure function and the
CorrelationCircuitBreaker class.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.risk.checks import (
    _extract_base_asset,
    check_portfolio_correlation,
)
from src.core.risk.types import OrderRequest, PortfolioState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_portfolio(
    equity: float = 100_000.0,
    positions: list | None = None,
) -> PortfolioState:
    """Build a minimal PortfolioState for testing."""
    mock = MagicMock(spec=PortfolioState)
    mock.total_equity = equity
    mock.open_positions = positions or []
    mock.daily_pnl = 0.0
    mock.weekly_pnl = 0.0
    mock.drawdown_pct = 0.0
    mock.cash_balance = equity
    return mock


def _make_order(
    symbol: str = "BTCUSDT",
    side: str = "buy",
    quantity: float = 1.0,
    price: float = 40_000.0,
) -> OrderRequest:
    """Build a minimal OrderRequest for testing."""
    mock = MagicMock(spec=OrderRequest)
    mock.symbol = symbol
    mock.side = side
    mock.quantity = quantity
    mock.price = price
    return mock


def _make_position(
    symbol: str,
    size: float,
    price: float,
    side_value: str = "long",
) -> MagicMock:
    """Build a mock open position."""
    pos = MagicMock()
    pos.symbol = symbol
    pos.size = size
    pos.current_price = price
    pos.side = MagicMock()
    pos.side.value = side_value
    return pos


# ---------------------------------------------------------------------------
# _extract_base_asset tests
# ---------------------------------------------------------------------------


class TestExtractBaseAsset:
    def test_btcusdt(self) -> None:
        assert _extract_base_asset("BTCUSDT") == "BTC"

    def test_ethusdt(self) -> None:
        assert _extract_base_asset("ETHUSDT") == "ETH"

    def test_bnbusdt(self) -> None:
        assert _extract_base_asset("BNBUSDT") == "BNB"

    def test_lowercase(self) -> None:
        assert _extract_base_asset("btcusdt") == "BTC"

    def test_busd_suffix(self) -> None:
        assert _extract_base_asset("ETHBUSD") == "ETH"

    def test_unknown_suffix(self) -> None:
        # Symbol without known quote currency returns as-is (uppercased)
        assert _extract_base_asset("SOLUSDC") == "SOLUSDC"


# ---------------------------------------------------------------------------
# check_portfolio_correlation tests
# ---------------------------------------------------------------------------


class TestCheckPortfolioCorrelation:
    def test_zero_equity_rejected(self) -> None:
        """Zero equity should immediately reject."""
        portfolio = _make_portfolio(equity=0.0)
        order = _make_order()
        result = check_portfolio_correlation(order, portfolio)
        assert not result.approved
        assert "zero equity" in result.rejection_reason.lower()

    def test_no_positions_buy_within_btc_limit(self) -> None:
        """BUY order that stays within 40% BTC limit should pass."""
        portfolio = _make_portfolio(equity=100_000.0)
        # Buying 0.5 BTC at $40k = $20k = 20% of equity (under 40% limit)
        order = _make_order(symbol="BTCUSDT", side="buy", quantity=0.5, price=40_000.0)
        result = check_portfolio_correlation(order, portfolio)
        assert result.approved

    def test_btc_exposure_exceeds_40pct(self) -> None:
        """BUY order that would push BTC exposure above 40% should fail."""
        # Existing: 0.5 BTC at $40k = $20k = 20% of $100k equity
        existing_btc_pos = _make_position("BTCUSDT", size=0.5, price=40_000.0)
        portfolio = _make_portfolio(equity=100_000.0, positions=[existing_btc_pos])
        # New order: 1.2 BTC at $40k = $48k additional
        # Total BTC = $20k + $48k = $68k = 68% > 40% limit
        order = _make_order(symbol="BTCUSDT", side="buy", quantity=1.2, price=40_000.0)
        result = check_portfolio_correlation(order, portfolio)
        assert not result.approved
        assert "BTC" in result.rejection_reason

    def test_eth_exposure_exceeds_30pct(self) -> None:
        """BUY order that would push ETH exposure above 30% should fail."""
        portfolio = _make_portfolio(equity=100_000.0)
        # Buying 10 ETH at $3200 = $32k = 32% > 30% limit
        order = _make_order(symbol="ETHUSDT", side="buy", quantity=10.0, price=3_200.0)
        result = check_portfolio_correlation(order, portfolio)
        assert not result.approved
        assert "ETH" in result.rejection_reason

    def test_total_correlated_exceeds_60pct(self) -> None:
        """Total long exposure above 60% should fail even if per-asset limits pass."""
        # BTC: $25k = 25% (under 40%)
        btc_pos = _make_position("BTCUSDT", size=0.625, price=40_000.0)
        # ETH: $25k = 25% (under 30%)
        eth_pos = _make_position("ETHUSDT", size=7.8125, price=3_200.0)
        portfolio = _make_portfolio(equity=100_000.0, positions=[btc_pos, eth_pos])
        # New BNB buy: $15k = 15%. Total = 25+25+15 = 65% > 60%
        order = _make_order(symbol="BNBUSDT", side="buy", quantity=50.0, price=300.0)
        result = check_portfolio_correlation(order, portfolio)
        assert not result.approved
        assert "60" in result.rejection_reason

    def test_sell_order_passes_through(self) -> None:
        """SELL orders are not subject to correlation limits (closing positions)."""
        # Even with massive existing positions, sells pass through
        btc_pos = _make_position("BTCUSDT", size=10.0, price=40_000.0)
        portfolio = _make_portfolio(equity=100_000.0, positions=[btc_pos])
        order = _make_order(symbol="BTCUSDT", side="sell", quantity=5.0, price=40_000.0)
        result = check_portfolio_correlation(order, portfolio)
        assert result.approved

    def test_short_position_not_counted_in_long_exposure(self) -> None:
        """Short positions should not count toward long exposure totals."""
        # Short BTC position - should not add to long exposure
        btc_short = _make_position("BTCUSDT", size=1.0, price=40_000.0, side_value="short")
        portfolio = _make_portfolio(equity=100_000.0, positions=[btc_short])
        # Buy BTC within 40% limit
        order = _make_order(symbol="BTCUSDT", side="buy", quantity=0.5, price=40_000.0)
        result = check_portfolio_correlation(order, portfolio)
        assert result.approved
