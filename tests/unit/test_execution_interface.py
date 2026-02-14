"""Tests for ExecutionEngine interface and supporting data types.

Validates OrderResult, Balance frozen dataclasses, and their
validation rules including NaN/Infinity checks, timezone awareness,
and invariant enforcement.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.execution.interface import Balance, ExecutionEngine, OrderResult
from src.core.risk.types import OrderRequest


# ---------------------------------------------------------------------------
# OrderResult tests
# ---------------------------------------------------------------------------


class TestOrderResult:
    """Tests for the OrderResult frozen dataclass."""

    def _make_result(self, **overrides) -> OrderResult:
        """Create a valid OrderResult with optional overrides."""
        defaults = {
            "order_id": "ord_test_123",
            "external_id": "12345",
            "symbol": "BTCUSDT",
            "side": "buy",
            "order_type": "market",
            "quantity": 0.1,
            "filled_quantity": 0.1,
            "price": None,
            "filled_price": 45000.0,
            "status": "filled",
            "commission": 0.5,
            "timestamp": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return OrderResult(**defaults)

    def test_valid_creation(self) -> None:
        """Test creating a valid OrderResult."""
        result = self._make_result()
        assert result.order_id == "ord_test_123"
        assert result.symbol == "BTCUSDT"
        assert result.side == "buy"
        assert result.status == "filled"

    def test_frozen_immutability(self) -> None:
        """Test that OrderResult is immutable."""
        result = self._make_result()
        with pytest.raises(AttributeError):
            result.status = "cancelled"  # type: ignore[misc]

    def test_empty_order_id_rejected(self) -> None:
        """Test that empty order_id raises ValueError."""
        with pytest.raises(ValueError, match="order_id is required"):
            self._make_result(order_id="")

    def test_empty_symbol_rejected(self) -> None:
        """Test that empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="symbol is required"):
            self._make_result(symbol="")

    def test_invalid_side_rejected(self) -> None:
        """Test that invalid side raises ValueError."""
        with pytest.raises(ValueError, match="side must be"):
            self._make_result(side="BUY")  # Must be lowercase

    def test_nan_quantity_rejected(self) -> None:
        """Test that NaN quantity raises ValueError."""
        with pytest.raises(ValueError, match="cannot be NaN"):
            self._make_result(quantity=float("nan"))

    def test_infinity_quantity_rejected(self) -> None:
        """Test that Infinity quantity raises ValueError."""
        with pytest.raises(ValueError, match="cannot be Infinity"):
            self._make_result(quantity=float("inf"))

    def test_negative_quantity_rejected(self) -> None:
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            self._make_result(quantity=-1.0)

    def test_negative_commission_rejected(self) -> None:
        """Test that negative commission raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            self._make_result(commission=-0.01)

    def test_zero_quantity_allowed(self) -> None:
        """Test that zero quantity is allowed (e.g., cancelled order)."""
        result = self._make_result(quantity=0.0, filled_quantity=0.0)
        assert result.quantity == 0.0

    def test_negative_price_rejected(self) -> None:
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="price must be positive"):
            self._make_result(price=-100.0)

    def test_negative_filled_price_rejected(self) -> None:
        """Test that negative filled_price raises ValueError."""
        with pytest.raises(ValueError, match="filled_price must be positive"):
            self._make_result(filled_price=-100.0)

    def test_none_price_allowed(self) -> None:
        """Test that None price is allowed (market orders)."""
        result = self._make_result(price=None)
        assert result.price is None

    def test_naive_timestamp_rejected(self) -> None:
        """Test that naive (non-timezone-aware) timestamp is rejected."""
        with pytest.raises(ValueError, match="timezone-aware"):
            self._make_result(timestamp=datetime(2026, 1, 1))

    def test_timezone_aware_timestamp_required(self) -> None:
        """Test that timezone-aware timestamp is accepted."""
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = self._make_result(timestamp=ts)
        assert result.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Balance tests
# ---------------------------------------------------------------------------


class TestBalance:
    """Tests for the Balance frozen dataclass."""

    def test_valid_creation(self) -> None:
        """Test creating a valid Balance."""
        balance = Balance(asset="BTC", free=1.0, locked=0.5, total=1.5)
        assert balance.asset == "BTC"
        assert balance.free == 1.0
        assert balance.locked == 0.5
        assert balance.total == 1.5

    def test_frozen_immutability(self) -> None:
        """Test that Balance is immutable."""
        balance = Balance(asset="BTC", free=1.0, locked=0.5, total=1.5)
        with pytest.raises(AttributeError):
            balance.free = 2.0  # type: ignore[misc]

    def test_empty_asset_rejected(self) -> None:
        """Test that empty asset raises ValueError."""
        with pytest.raises(ValueError, match="asset is required"):
            Balance(asset="", free=1.0, locked=0.0, total=1.0)

    def test_negative_free_rejected(self) -> None:
        """Test that negative free balance raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            Balance(asset="BTC", free=-1.0, locked=0.0, total=-1.0)

    def test_nan_locked_rejected(self) -> None:
        """Test that NaN locked balance raises ValueError."""
        with pytest.raises(ValueError, match="cannot be NaN"):
            Balance(asset="BTC", free=1.0, locked=float("nan"), total=1.0)

    def test_invariant_total_equals_free_plus_locked(self) -> None:
        """Test that total must equal free + locked."""
        with pytest.raises(ValueError, match="Balance invariant"):
            Balance(asset="BTC", free=1.0, locked=0.5, total=2.0)

    def test_invariant_allows_rounding_tolerance(self) -> None:
        """Test that small rounding differences are tolerated."""
        # 1.0 + 0.5 = 1.5, but total is 1.509 (within 0.01 tolerance)
        balance = Balance(asset="BTC", free=1.0, locked=0.5, total=1.509)
        assert balance.total == 1.509

    def test_zero_balance_allowed(self) -> None:
        """Test that all-zero balance is valid."""
        balance = Balance(asset="USDT", free=0.0, locked=0.0, total=0.0)
        assert balance.total == 0.0


# ---------------------------------------------------------------------------
# ExecutionEngine ABC tests
# ---------------------------------------------------------------------------


class TestExecutionEngineABC:
    """Tests for the ExecutionEngine abstract interface."""

    def test_cannot_instantiate_directly(self) -> None:
        """Test that ExecutionEngine cannot be instantiated."""
        with pytest.raises(TypeError):
            ExecutionEngine()  # type: ignore[abstract]

    def test_subclass_must_implement_all_methods(self) -> None:
        """Test that subclass must implement all abstract methods."""

        class IncompleteEngine(ExecutionEngine):
            pass

        with pytest.raises(TypeError):
            IncompleteEngine()  # type: ignore[abstract]

    def test_complete_subclass_can_instantiate(self) -> None:
        """Test that a complete implementation can be instantiated."""

        class MockEngine(ExecutionEngine):
            async def submit_order(self, request: OrderRequest) -> OrderResult:
                raise NotImplementedError

            async def cancel_order(
                self, order_id: str, symbol: str
            ) -> OrderResult:
                raise NotImplementedError

            async def get_order_status(
                self, order_id: str, symbol: str
            ) -> OrderResult:
                raise NotImplementedError

            async def get_account_balance(self) -> list[Balance]:
                raise NotImplementedError

            async def validate_symbol(self, symbol: str) -> bool:
                raise NotImplementedError

        engine = MockEngine()
        assert isinstance(engine, ExecutionEngine)
