"""Tests for the BinanceExecutionAdapter.

Uses mocked BinanceClient to test enum translation, commission
extraction, error mapping, and quantity rounding without hitting
the exchange.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.brokers.binance.exceptions import BinanceAPIError
from src.core.exceptions import (
    InsufficientBalanceError,
    OrderNotFoundError,
    OrderRejectedError,
)
from src.core.execution.interface import OrderResult
from src.core.risk.types import OrderRequest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock BinanceClient."""
    client = MagicMock()
    client.testnet = True
    # Make all async methods return coroutines
    client.create_order = AsyncMock()
    client.cancel_order = AsyncMock()
    client.get_order_status = AsyncMock()
    client.get_open_orders = AsyncMock()
    client.get_account = AsyncMock()
    client.get_exchange_info = AsyncMock()
    return client


@pytest.fixture
def mock_symbol_manager() -> MagicMock:
    """Create a mock SymbolManager."""
    manager = MagicMock()
    symbol_info = MagicMock()
    symbol_info.round_quantity.side_effect = lambda q: round(q, 5)
    symbol_info.round_price.side_effect = lambda p: round(p, 2)
    symbol_info.is_trading = True
    manager.get_symbol = AsyncMock(return_value=symbol_info)
    return manager


@pytest.fixture
def adapter(mock_client, mock_symbol_manager):
    """Create a BinanceExecutionAdapter with mocked dependencies."""
    from src.brokers.binance.execution import BinanceExecutionAdapter

    return BinanceExecutionAdapter(
        client=mock_client,
        symbol_manager=mock_symbol_manager,
    )


@pytest.fixture
def sample_request() -> OrderRequest:
    """Create a sample OrderRequest."""
    return OrderRequest(
        account_id="acc_test_123",
        strategy_id="strat_test_456",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.1,
        price=45000.0,
    )


def _binance_order_response(**overrides: Any) -> dict[str, Any]:
    """Create a Binance-like order response."""
    defaults = {
        "orderId": 12345,
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "status": "FILLED",
        "origQty": "0.1",
        "executedQty": "0.1",
        "cummulativeQuoteQty": "4500.0",
        "price": "0.00000000",
        "transactTime": int(datetime.now(timezone.utc).timestamp() * 1000),
        "fills": [
            {
                "price": "45000.0",
                "qty": "0.1",
                "commission": "0.5",
                "commissionAsset": "USDT",
            }
        ],
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Submit order tests
# ---------------------------------------------------------------------------


class TestSubmitOrder:
    """Tests for BinanceExecutionAdapter.submit_order()."""

    @pytest.mark.asyncio
    async def test_successful_market_order(
        self, adapter, mock_client, sample_request
    ) -> None:
        """Test successful market order submission."""
        mock_client.create_order.return_value = _binance_order_response()

        result = await adapter.submit_order(sample_request)

        assert isinstance(result, OrderResult)
        assert result.external_id == "12345"
        assert result.symbol == "BTCUSDT"
        assert result.side == "buy"  # Translated from BUY
        assert result.status == "filled"  # Translated from FILLED
        assert result.filled_quantity == 0.1
        assert result.commission == 0.5

    @pytest.mark.asyncio
    async def test_side_translated_to_binance_format(
        self, adapter, mock_client, sample_request
    ) -> None:
        """Test that side is translated to Binance uppercase."""
        mock_client.create_order.return_value = _binance_order_response()

        await adapter.submit_order(sample_request)

        # Verify the client was called with uppercase side
        call_kwargs = mock_client.create_order.call_args.kwargs
        assert call_kwargs["side"] == "BUY"
        assert call_kwargs["order_type"] == "MARKET"

    @pytest.mark.asyncio
    async def test_commission_extracted_from_fills(
        self, adapter, mock_client, sample_request
    ) -> None:
        """Test that commission is summed from fills array."""
        response = _binance_order_response(
            fills=[
                {"price": "45000", "qty": "0.05", "commission": "0.25", "commissionAsset": "USDT"},
                {"price": "45010", "qty": "0.05", "commission": "0.25", "commissionAsset": "USDT"},
            ]
        )
        mock_client.create_order.return_value = response

        result = await adapter.submit_order(sample_request)
        assert abs(result.commission - 0.5) < 0.001

    @pytest.mark.asyncio
    async def test_quantity_rounded_via_symbol_manager(
        self, adapter, mock_client, mock_symbol_manager, sample_request
    ) -> None:
        """Test that quantity is rounded using SymbolManager."""
        mock_client.create_order.return_value = _binance_order_response()

        await adapter.submit_order(sample_request)

        # SymbolManager.get_symbol should have been called
        mock_symbol_manager.get_symbol.assert_called_once_with("BTCUSDT")

    @pytest.mark.asyncio
    async def test_invalid_side_raises_rejected(self, adapter) -> None:
        """Test that invalid side raises OrderRejectedError."""
        OrderRequest(
            account_id="acc_test",
            strategy_id="strat_test",
            symbol="BTCUSDT",
            side="buy",  # Valid for OrderRequest
            quantity=0.1,
            price=45000.0,
        )
        # Monkey-patch side to an invalid value after creation
        # (OrderRequest validates at creation, so we test adapter logic)
        mock_request = MagicMock(spec=OrderRequest)
        mock_request.side = "INVALID"
        mock_request.symbol = "BTCUSDT"
        mock_request.order_type = "market"
        mock_request.quantity = 0.1
        mock_request.price = 45000.0
        mock_request.account_id = "acc_test"

        with pytest.raises(OrderRejectedError):
            await adapter.submit_order(mock_request)

    @pytest.mark.asyncio
    async def test_insufficient_balance_mapped(
        self, adapter, mock_client, sample_request
    ) -> None:
        """Test that Binance -2010 error maps to InsufficientBalanceError."""
        mock_client.create_order.side_effect = BinanceAPIError(
            symbol="BTCUSDT",
            api_code=-2010,
            api_message="Account has insufficient balance",
        )

        with pytest.raises(InsufficientBalanceError):
            await adapter.submit_order(sample_request)


# ---------------------------------------------------------------------------
# Cancel order tests
# ---------------------------------------------------------------------------


class TestCancelOrder:
    """Tests for BinanceExecutionAdapter.cancel_order()."""

    @pytest.mark.asyncio
    async def test_successful_cancellation(
        self, adapter, mock_client
    ) -> None:
        """Test successful order cancellation."""
        mock_client.cancel_order.return_value = _binance_order_response(
            status="CANCELED"
        )

        result = await adapter.cancel_order("12345", "BTCUSDT")

        assert result.status == "cancelled"  # CANCELED -> cancelled
        mock_client.cancel_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_order_mapped(
        self, adapter, mock_client
    ) -> None:
        """Test that Binance -2011 maps to OrderNotFoundError."""
        mock_client.cancel_order.side_effect = BinanceAPIError(
            symbol="BTCUSDT",
            api_code=-2011,
            api_message="Unknown order sent",
        )

        with pytest.raises(OrderNotFoundError):
            await adapter.cancel_order("99999", "BTCUSDT")


# ---------------------------------------------------------------------------
# Get order status tests
# ---------------------------------------------------------------------------


class TestGetOrderStatus:
    """Tests for BinanceExecutionAdapter.get_order_status()."""

    @pytest.mark.asyncio
    async def test_status_translation(
        self, adapter, mock_client
    ) -> None:
        """Test that all Binance statuses are correctly translated."""
        test_cases = [
            ("NEW", "submitted"),
            ("PARTIALLY_FILLED", "partially_filled"),
            ("FILLED", "filled"),
            ("CANCELED", "cancelled"),
            ("REJECTED", "rejected"),
            ("EXPIRED", "expired"),
        ]

        for binance_status, expected_status in test_cases:
            mock_client.get_order_status.return_value = (
                _binance_order_response(status=binance_status)
            )
            result = await adapter.get_order_status("12345", "BTCUSDT")
            assert result.status == expected_status, (
                f"Expected {binance_status} -> {expected_status}, got {result.status}"
            )

    @pytest.mark.asyncio
    async def test_average_fill_price_computed(
        self, adapter, mock_client
    ) -> None:
        """Test that average fill price is computed from cumulative quote qty."""
        mock_client.get_order_status.return_value = _binance_order_response(
            executedQty="0.5",
            cummulativeQuoteQty="22500.0",  # 0.5 * 45000
        )

        result = await adapter.get_order_status("12345", "BTCUSDT")
        assert result.filled_price is not None
        assert abs(result.filled_price - 45000.0) < 0.01


# ---------------------------------------------------------------------------
# Get account balance tests
# ---------------------------------------------------------------------------


class TestGetAccountBalance:
    """Tests for BinanceExecutionAdapter.get_account_balance()."""

    @pytest.mark.asyncio
    async def test_non_zero_balances_returned(
        self, adapter, mock_client
    ) -> None:
        """Test that only non-zero balances are returned."""
        mock_client.get_account.return_value = {
            "balances": [
                {"asset": "BTC", "free": "1.0", "locked": "0.5"},
                {"asset": "ETH", "free": "0.0", "locked": "0.0"},
                {"asset": "USDT", "free": "10000.0", "locked": "0.0"},
            ]
        }

        balances = await adapter.get_account_balance()

        assert len(balances) == 2  # ETH excluded (zero balance)
        assets = {b.asset for b in balances}
        assert "BTC" in assets
        assert "USDT" in assets
        assert "ETH" not in assets

    @pytest.mark.asyncio
    async def test_balance_total_computed(
        self, adapter, mock_client
    ) -> None:
        """Test that total = free + locked."""
        mock_client.get_account.return_value = {
            "balances": [
                {"asset": "BTC", "free": "1.0", "locked": "0.5"},
            ]
        }

        balances = await adapter.get_account_balance()
        btc = balances[0]
        assert btc.free == 1.0
        assert btc.locked == 0.5
        assert btc.total == 1.5


# ---------------------------------------------------------------------------
# Validate symbol tests
# ---------------------------------------------------------------------------


class TestValidateSymbol:
    """Tests for BinanceExecutionAdapter.validate_symbol()."""

    @pytest.mark.asyncio
    async def test_valid_symbol(
        self, adapter, mock_symbol_manager
    ) -> None:
        """Test that a valid, trading symbol returns True."""
        result = await adapter.validate_symbol("BTCUSDT")
        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_symbol_returns_false(
        self, adapter, mock_symbol_manager
    ) -> None:
        """Test that an exception from symbol manager returns False."""
        mock_symbol_manager.get_symbol.side_effect = Exception("Not found")
        result = await adapter.validate_symbol("INVALIDPAIR")
        assert result is False
