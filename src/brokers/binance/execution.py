"""Binance execution adapter implementing the ExecutionEngine interface.

Translates between internal order conventions (lowercase enums) and
Binance API conventions (UPPERCASE strings), handles quantity/price
rounding, commission extraction, and error mapping.

Decision: DEC-2026-02-10-001 - python-binance SDK wrapper
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging

Phase 4A: Execution Infrastructure
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.brokers.binance.client import BinanceClient
from src.brokers.binance.exceptions import BinanceAPIError
from src.core.exceptions import (InsufficientBalanceError, OrderNotFoundError,
                                 OrderRejectedError, OrderSubmissionError)
from src.core.execution.interface import Balance, ExecutionEngine, OrderResult
from src.core.risk.types import OrderRequest
from src.data.symbol_manager import SymbolManager
from src.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enum translation maps: Binance UPPERCASE <-> internal lowercase
# ---------------------------------------------------------------------------

_SIDE_TO_BINANCE: dict[str, str] = {
    "buy": "BUY",
    "sell": "SELL",
}

_SIDE_FROM_BINANCE: dict[str, str] = {
    "BUY": "buy",
    "SELL": "sell",
}

_ORDER_TYPE_TO_BINANCE: dict[str, str] = {
    "market": "MARKET",
    "limit": "LIMIT",
    "stop_loss": "STOP_LOSS",
    "take_profit": "TAKE_PROFIT",
    "stop_limit": "STOP_LIMIT",
}

_STATUS_FROM_BINANCE: dict[str, str] = {
    "NEW": "submitted",
    "PARTIALLY_FILLED": "partially_filled",
    "FILLED": "filled",
    "CANCELED": "cancelled",
    "REJECTED": "rejected",
    "EXPIRED": "expired",
    "PENDING_CANCEL": "cancelled",
}


class BinanceExecutionAdapter(ExecutionEngine):
    """Binance implementation of the ExecutionEngine interface.

    Wraps BinanceClient with:
    - Enum translation (Binance UPPERCASE <-> internal lowercase)
    - Quantity/price rounding to exchange precision
    - Commission extraction from fill arrays
    - Exchange error code mapping to domain exceptions

    Attributes:
        client: Async Binance API client.
        symbol_manager: Optional symbol metadata for precision rounding.
    """

    def __init__(
        self,
        client: BinanceClient,
        symbol_manager: SymbolManager | None = None,
    ) -> None:
        """Initialize the Binance execution adapter.

        Args:
            client: BinanceClient instance for API calls.
            symbol_manager: Optional SymbolManager for quantity/price rounding.
                If not provided, quantities are submitted as-is.
        """
        self.client = client
        self.symbol_manager = symbol_manager

        logger.info(
            "binance_execution_adapter_initialized",
            testnet=client.testnet,
            has_symbol_manager=symbol_manager is not None,
        )

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        """Submit an order to Binance.

        Translates internal order request to Binance format, handles
        quantity rounding, submits via client, and parses the response
        into an OrderResult.

        Args:
            request: Validated order request from risk pipeline.

        Returns:
            OrderResult with Binance response details.

        Raises:
            OrderSubmissionError: If Binance rejects the order.
            InsufficientBalanceError: If balance is insufficient.
            OrderRejectedError: If exchange rejects with specific reason.
        """
        symbol = request.symbol
        side_binance = _SIDE_TO_BINANCE.get(request.side)
        if side_binance is None:
            raise OrderRejectedError(
                reason=f"Invalid order side: {request.side}",
            )

        order_type_binance = _ORDER_TYPE_TO_BINANCE.get(request.order_type)
        if order_type_binance is None:
            raise OrderRejectedError(
                reason=f"Invalid order type: {request.order_type}",
            )

        # Round quantity to exchange precision if symbol manager available
        quantity = request.quantity
        price = request.price if request.order_type != "market" else None

        if self.symbol_manager:
            try:
                symbol_info = await self.symbol_manager.get_symbol(symbol)
                quantity = symbol_info.round_quantity(quantity)

                if price is not None:
                    price = symbol_info.round_price(price)

                logger.debug(
                    "quantity_rounded",
                    symbol=symbol,
                    original_qty=request.quantity,
                    rounded_qty=quantity,
                )
            except Exception:
                # If symbol lookup fails, proceed with original values
                # The exchange will validate and reject if needed
                logger.warning(
                    "symbol_rounding_failed",
                    symbol=symbol,
                    quantity=request.quantity,
                )

        try:
            logger.info(
                "adapter_submitting_order",
                symbol=symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=quantity,
            )

            response = await self.client.create_order(
                symbol=symbol,
                side=side_binance,
                order_type=order_type_binance,
                quantity=quantity,
                price=price,
            )

            result = self._parse_order_response(
                response=response,
                internal_order_id=request.account_id,
            )

            logger.info(
                "adapter_order_submitted",
                symbol=symbol,
                external_id=result.external_id,
                status=result.status,
                filled_quantity=result.filled_quantity,
                commission=result.commission,
            )

            return result

        except BinanceAPIError as e:
            self._handle_api_error(e, symbol=symbol, context="submit_order")
            raise  # _handle_api_error always raises, this is for type checker

    async def cancel_order(
        self, order_id: str, symbol: str
    ) -> OrderResult:
        """Cancel an order on Binance.

        Args:
            order_id: Exchange-assigned order ID (will be cast to int).
            symbol: Trading pair (e.g., "BTCUSDT").

        Returns:
            OrderResult reflecting cancelled state.

        Raises:
            OrderNotFoundError: If order does not exist on exchange.
        """
        try:
            logger.info(
                "adapter_cancelling_order",
                order_id=order_id,
                symbol=symbol,
            )

            response = await self.client.cancel_order(
                symbol=symbol,
                order_id=int(order_id),
            )

            result = self._parse_order_response(
                response=response,
                internal_order_id="",
            )

            logger.info(
                "adapter_order_cancelled",
                order_id=order_id,
                symbol=symbol,
                status=result.status,
            )

            return result

        except BinanceAPIError as e:
            self._handle_api_error(e, symbol=symbol, context="cancel_order")
            raise

    async def get_order_status(
        self, order_id: str, symbol: str
    ) -> OrderResult:
        """Query order status from Binance.

        Args:
            order_id: Exchange-assigned order ID (will be cast to int).
            symbol: Trading pair (e.g., "BTCUSDT").

        Returns:
            OrderResult with current status.

        Raises:
            OrderNotFoundError: If order does not exist on exchange.
        """
        try:
            logger.debug(
                "adapter_checking_order_status",
                order_id=order_id,
                symbol=symbol,
            )

            response = await self.client.get_order_status(
                symbol=symbol,
                order_id=int(order_id),
            )

            return self._parse_order_response(
                response=response,
                internal_order_id="",
            )

        except BinanceAPIError as e:
            self._handle_api_error(
                e, symbol=symbol, context="get_order_status"
            )
            raise

    async def get_account_balance(self) -> list[Balance]:
        """Get account balances from Binance.

        Returns:
            List of Balance objects for assets with non-zero balance.
        """
        logger.info("adapter_fetching_balances")

        account_info = await self.client.get_account()
        balances: list[Balance] = []

        for asset_data in account_info.get("balances", []):
            free = float(asset_data.get("free", "0"))
            locked = float(asset_data.get("locked", "0"))
            total = free + locked

            # Only include non-zero balances
            if total > 0:
                balances.append(
                    Balance(
                        asset=asset_data["asset"],
                        free=free,
                        locked=locked,
                        total=total,
                    )
                )

        logger.info(
            "adapter_balances_fetched",
            non_zero_assets=len(balances),
        )

        return balances

    async def validate_symbol(self, symbol: str) -> bool:
        """Check if a symbol is valid on Binance.

        Args:
            symbol: Trading pair to validate.

        Returns:
            True if symbol is valid and tradeable.
        """
        if self.symbol_manager:
            try:
                symbol_info = await self.symbol_manager.get_symbol(symbol)
                return symbol_info.is_trading
            except Exception:
                return False

        # Fallback: query exchange directly
        try:
            info = await self.client.get_exchange_info(symbol=symbol)
            return info.get("status") == "TRADING" if info else False
        except Exception:
            return False

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _parse_order_response(
        self,
        response: dict[str, Any],
        internal_order_id: str,
    ) -> OrderResult:
        """Parse a Binance order response into an OrderResult.

        Handles enum translation from Binance UPPERCASE to internal
        lowercase, extracts commission from fills array, and computes
        average fill price.

        Args:
            response: Raw Binance API response dictionary.
            internal_order_id: Internal order ID to attach.

        Returns:
            OrderResult with parsed fields.
        """
        # Extract basic fields
        external_id = str(response.get("orderId", ""))
        symbol = response.get("symbol", "")

        # Translate enums from Binance format
        side_raw = response.get("side", "")
        side = _SIDE_FROM_BINANCE.get(side_raw, side_raw.lower())

        order_type_raw = response.get("type", "")
        order_type = order_type_raw.lower()

        status_raw = response.get("status", "")
        status = _STATUS_FROM_BINANCE.get(status_raw, status_raw.lower())

        # Parse quantities
        quantity = float(response.get("origQty", "0"))
        filled_quantity = float(response.get("executedQty", "0"))

        # Parse price
        price_str = response.get("price", "0")
        price = float(price_str) if float(price_str) > 0 else None

        # Compute average fill price from cummulativeQuoteQty
        cumulative_quote = float(
            response.get("cummulativeQuoteQty", "0")
        )
        filled_price: float | None = None
        if filled_quantity > 0 and cumulative_quote > 0:
            filled_price = cumulative_quote / filled_quantity

        # Extract commission from fills array
        commission = self._extract_commission(response.get("fills", []))

        # Timestamp: use transactTime if available, otherwise now
        transact_time = response.get("transactTime")
        if transact_time:
            timestamp = datetime.fromtimestamp(
                transact_time / 1000, tz=timezone.utc
            )
        else:
            timestamp = datetime.now(timezone.utc)

        return OrderResult(
            order_id=internal_order_id or external_id,
            external_id=external_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            filled_quantity=filled_quantity,
            price=price,
            filled_price=filled_price,
            status=status,
            commission=commission,
            timestamp=timestamp,
            raw_response=response,
        )

    def _extract_commission(
        self, fills: list[dict[str, Any]]
    ) -> float:
        """Extract total commission from Binance fills array.

        Args:
            fills: List of fill dictionaries from Binance response.

        Returns:
            Total commission in quote asset units.
        """
        total_commission = 0.0
        for fill in fills:
            commission_str = fill.get("commission", "0")
            total_commission += float(commission_str)

        return total_commission

    def _handle_api_error(
        self,
        error: BinanceAPIError,
        symbol: str,
        context: str,
    ) -> None:
        """Map Binance API errors to domain exceptions.

        Translates Binance error codes into the appropriate exception
        from our hierarchy.

        Args:
            error: The BinanceAPIError that was raised.
            symbol: The trading pair involved.
            context: Operation context (e.g., "submit_order").

        Raises:
            InsufficientBalanceError: For code -2010.
            OrderNotFoundError: For codes -2011, -2013.
            OrderRejectedError: For code -1013 (invalid quantity).
            OrderSubmissionError: For all other errors.
        """
        api_code = getattr(error, "api_code", 0)
        api_message = getattr(error, "api_message", str(error))

        logger.error(
            "binance_execution_error",
            symbol=symbol,
            context=context,
            api_code=api_code,
            api_message=api_message,
        )

        if api_code == -2010:
            raise InsufficientBalanceError(
                required=0.0,
                available=0.0,
            ) from error

        if api_code in (-2011, -2013):
            raise OrderNotFoundError(
                order_id=f"binance:{symbol}",
                details={"api_code": api_code, "api_message": api_message},
            ) from error

        if api_code == -1013:
            raise OrderRejectedError(
                reason=f"Invalid quantity: {api_message}",
            ) from error

        raise OrderSubmissionError(
            symbol=symbol,
            reason=api_message,
            details={"api_code": api_code, "context": context},
        ) from error
