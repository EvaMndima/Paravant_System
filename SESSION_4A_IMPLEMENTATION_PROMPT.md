# SESSION 4A: EXECUTION INFRASTRUCTURE IMPLEMENTATION
## Order Execution Engine & Order Management
**Production Grade | Zero Technical Debt | 90%+ Test Coverage**

---

## Executive Summary

**Session 4A** implements the execution infrastructure: reliable order placement on Binance and complete order lifecycle management. This is the bridge between risk controls (Phase 3) and position tracking (Session 4B).

- **Duration:** ~45 hours
- **Tasks:** 18 (Sections 4.1 + 4.2)
- **Deliverables:** ExecutionEngine adapter, OrderManager, complete order workflows
- **Quality Gates:** 100% type hints, zero technical debt, >90% test coverage, Grade A- production audit

---

## CRITICAL DEPENDENCIES

**Must Complete BEFORE Starting Session 4A:**
- ✅ Phase 1: Database models (Account, Order, Trade, Position)
- ✅ Phase 2: Data layer (DataStore, SymbolManager, MarketDataService)
- ✅ Phase 3: Risk controls (RiskController, kill switch, circuit breakers)

**Session 4A Must Complete BEFORE Starting Session 4B:**
- Order submission flow (4.2.2)
- Order status tracking (4.2.3)
- Fill handling (4.2.4)

---

## IMPLEMENTATION SEQUENCE

The strict execution order prevents integration failures and circular dependencies:

### **Stage 1: Execution Engine Interface (3-4 hours)**
**Tasks:** 4.1.1
**Deliverable:** Abstract ExecutionEngine interface with all broker-agnostic methods

1. **Task 4.1.1 - Create Execution Engine Interface**
   - File: `src/core/execution/interface.py`
   - Define `ExecutionEngine` ABC with methods:
     - `async submit_order(order: Order) -> OrderResult`
     - `async cancel_order(order_id: str) -> bool`
     - `async get_order_status(order_id: str) -> OrderStatus`
     - `async get_positions() -> List[Position]`
     - `async get_balance(asset: str) -> float`
     - `async get_all_balances() -> Dict[str, Balance]`
     - `async get_open_orders() -> List[Order]`
   - Define result types: `OrderResult`, `OrderStatus`, `Balance`
   - 100% type hints, full docstrings
   - Unit test: Interface contract verification

   **Detailed Implementation Guide:**

   ```python
   # File: src/core/execution/interface.py
   from abc import ABC, abstractmethod
   from dataclasses import dataclass
   from datetime import datetime
   from typing import Dict, List, Optional
   from enum import Enum
   import math

   class OrderStatus(Enum):
       """Order lifecycle states - matches Binance + internal states."""
       SUBMITTED = "SUBMITTED"      # Sent to exchange, awaiting response
       PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Some quantity filled
       FILLED = "FILLED"            # All quantity filled
       CANCELLED = "CANCELLED"      # User cancelled
       REJECTED = "REJECTED"        # Exchange rejected
       EXPIRED = "EXPIRED"          # Order timed out

   @dataclass
   class OrderResult:
       """Result of order submission."""
       order_id: str                # Exchange order ID
       symbol: str
       side: str                    # BUY or SELL
       quantity: float
       price: Optional[float]       # None for market orders
       filled_quantity: float = 0.0
       average_fill_price: float = 0.0
       commission: float = 0.0      # Fee paid
       status: OrderStatus = OrderStatus.SUBMITTED
       created_at: datetime = None  # Will be set by implementation

       def __post_init__(self):
           # Validate financial values
           if math.isnan(self.quantity) or math.isinf(self.quantity):
               raise ValueError("quantity cannot be NaN or Infinity")
           if self.quantity <= 0:
               raise ValueError("quantity must be positive")
           if self.price is not None:
               if math.isnan(self.price) or math.isinf(self.price):
                   raise ValueError("price cannot be NaN or Infinity")
               if self.price <= 0:
                   raise ValueError("price must be positive")
           if self.created_at is None:
               from datetime import timezone
               self.created_at = datetime.now(timezone.utc)

   @dataclass
   class Balance:
       """Account balance for an asset."""
       asset: str
       free: float        # Available balance
       locked: float      # Balance in open orders

       @property
       def total(self) -> float:
           """Total = free + locked."""
           return self.free + self.locked

       def __post_init__(self):
           if math.isnan(self.free) or math.isinf(self.free):
               raise ValueError(f"{self.asset} free balance cannot be NaN or Infinity")
           if math.isnan(self.locked) or math.isinf(self.locked):
               raise ValueError(f"{self.asset} locked balance cannot be NaN or Infinity")
           if self.free < 0 or self.locked < 0:
               raise ValueError(f"{self.asset} balances cannot be negative")

   class ExecutionEngine(ABC):
       """
       Abstract execution engine interface.

       All brokers implement this contract. Binance is the MVP implementation.

       Key principles:
       - All numeric values validated (no NaN/Infinity)
       - All timestamps timezone-aware (UTC)
       - All methods async
       - All errors raised as specific exceptions
       """

       @abstractmethod
       async def submit_order(
           self,
           symbol: str,
           side: str,           # BUY or SELL
           quantity: float,
           order_type: str,     # MARKET, LIMIT, STOP_LOSS, etc.
           price: Optional[float] = None,  # For LIMIT and STOP orders
           stop_price: Optional[float] = None,  # For STOP orders
           time_in_force: Optional[str] = None  # For LIMIT orders
       ) -> OrderResult:
           """
           Submit order to exchange.

           Args:
               symbol: e.g., "BTCUSDT"
               side: "BUY" or "SELL"
               quantity: Amount in base asset
               order_type: "MARKET", "LIMIT", "STOP_LOSS", "TAKE_PROFIT"
               price: Price for LIMIT orders
               stop_price: Trigger price for STOP orders
               time_in_force: "GTC", "IOC", "FOK" for LIMIT orders

           Returns:
               OrderResult with order_id and status

           Raises:
               ValueError: Invalid input
               InsufficientBalanceError: Not enough balance
               InvalidSymbolError: Symbol not found
               OrderSubmissionError: Exchange error
           """
           pass

       @abstractmethod
       async def cancel_order(self, symbol: str, order_id: str) -> bool:
           """
           Cancel order.

           Returns:
               True if cancelled, False if already filled/cancelled

           Raises:
               OrderNotFoundError: Order doesn't exist
               OrderCancellationError: Exchange error
           """
           pass

       @abstractmethod
       async def get_order_status(
           self,
           symbol: str,
           order_id: str
       ) -> OrderResult:
           """
           Get current order status and fill information.

           For partially filled orders, includes filled_quantity and average_fill_price.
           For filled orders, includes commission paid.

           Returns:
               Updated OrderResult with current status

           Raises:
               OrderNotFoundError: Order doesn't exist
               OrderStatusError: Exchange error
           """
           pass

       @abstractmethod
       async def get_balance(self, asset: str) -> Balance:
           """
           Get single asset balance.

           Args:
               asset: e.g., "USDT", "BTC"

           Returns:
               Balance with free, locked, total

           Raises:
               AssetNotFoundError: Asset not recognized
               BalanceError: Exchange error
           """
           pass

       @abstractmethod
       async def get_all_balances(self) -> Dict[str, Balance]:
           """
           Get all asset balances.

           Returns:
               Dict of asset → Balance (only non-zero balances)

           Raises:
               BalanceError: Exchange error
           """
           pass

       @abstractmethod
       async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResult]:
           """
           Get all open orders.

           Args:
               symbol: Optional filter to specific symbol

           Returns:
               List of all open orders (status in [SUBMITTED, PARTIALLY_FILLED])

           Raises:
               OrderError: Exchange error
           """
           pass
   ```

   **Common Pitfalls to Avoid:**
   - ❌ Not validating NaN/Infinity in dataclass __post_init__
   - ❌ Missing timezone on datetime fields (use `timezone.utc`)
   - ❌ Allowing negative or zero quantities (should raise ValueError)
   - ❌ Not documenting parameter meanings (BUY/SELL, order type enum, etc.)
   - ✅ Always include examples in docstrings
   - ✅ Always validate in __post_init__ for dataclasses
   - ✅ Use specific exception types (not generic Exception)

**Acceptance Criteria:**
- [ ] ExecutionEngine ABC defined with all 6 abstract methods
- [ ] All result dataclasses (OrderResult, Balance) have __post_init__ validation
- [ ] All numeric fields checked for NaN/Infinity
- [ ] All timestamps use `datetime.now(timezone.utc)`
- [ ] Full docstrings with Args, Returns, Raises sections
- [ ] Docstrings include concrete examples (e.g., "symbol: 'BTCUSDT'")
- [ ] Unit test: Can instantiate mock implementation of ExecutionEngine
- [ ] Unit test: OrderResult and Balance validation works
- [ ] Unit test: Invalid values raise ValueError with descriptive message

---

### **Stage 2: Binance Adapter Implementation (18-20 hours)**
**Tasks:** 4.1.2 through 4.1.10
**Deliverable:** Complete Binance-specific ExecutionEngine implementation

2. **Task 4.1.2 - Create Binance Execution Adapter**
   - File: `src/brokers/binance/execution.py`
   - Class: `BinanceExecutionAdapter(ExecutionEngine)`
   - Requires: BinanceClient (from Phase 1), SymbolManager
   - Testnet/mainnet switching via config
   - 100% type hints, full docstrings
   - Integration test: Adapter initialization and testnet connectivity

   **Detailed Implementation Guide:**

   ```python
   # File: src/brokers/binance/execution.py
   import asyncio
   import math
   from typing import Dict, List, Optional
   from datetime import datetime, timezone
   from logging import getLogger

   from src.core.execution.interface import ExecutionEngine, OrderResult, OrderStatus, Balance
   from src.brokers.binance.client import BinanceClient
   from src.data.symbol_manager import SymbolManager

   logger = getLogger(__name__)

   class BinanceExecutionError(Exception):
       """Binance-specific execution error."""
       pass

   class BinanceExecutionAdapter(ExecutionEngine):
       """
       Binance-specific order execution implementation.

       Handles:
       - API requests to Binance (testnet or mainnet)
       - Order type mapping (market, limit, stop loss, take profit)
       - Quantity/price rounding to Binance requirements
       - Status translation (Binance status → internal status)
       - Error handling and logging
       - Commission tracking

       Configuration:
           use_testnet: bool = True  # Use testnet by default
           api_key: str = os.getenv("BINANCE_API_KEY")
           api_secret: str = os.getenv("BINANCE_API_SECRET")
       """

       def __init__(
           self,
           binance_client: BinanceClient,
           symbol_manager: SymbolManager,
           use_testnet: bool = True
       ):
           """
           Initialize Binance adapter.

           Args:
               binance_client: Configured BinanceClient instance
               symbol_manager: SymbolManager for symbol validation
               use_testnet: Whether to use testnet (True) or mainnet (False)

           Raises:
               ValueError: If BinanceClient not properly configured
           """
           self._client: BinanceClient = binance_client
           self._symbol_manager: SymbolManager = symbol_manager
           self._use_testnet: bool = use_testnet

           # Verify connectivity on init
           if not self._client.is_connected:
               raise BinanceExecutionError(
                   f"BinanceClient not connected. "
                   f"use_testnet={use_testnet}, "
                   f"check API credentials"
               )

           logger.info(
               "binance_adapter_initialized",
               use_testnet=use_testnet,
               api_mode="testnet" if use_testnet else "mainnet"
           )

       def _validate_symbol(self, symbol: str) -> None:
           """Validate symbol is recognized by Binance."""
           if not self._symbol_manager.is_valid_symbol(symbol):
               raise ValueError(f"Invalid symbol: {symbol}")

       def _round_quantity(self, symbol: str, quantity: float) -> float:
           """
           Round quantity to Binance step size.

           Example: If BTCUSDT step size is 0.00001 BTC:
               quantity = 0.123456 → rounded to 0.12345
           """
           if math.isnan(quantity) or math.isinf(quantity):
               raise ValueError("quantity cannot be NaN or Infinity")
           if quantity <= 0:
               raise ValueError("quantity must be positive")

           step_size = self._symbol_manager.get_step_size(symbol)
           if step_size <= 0:
               raise ValueError(f"Invalid step size for {symbol}: {step_size}")

           # Round down to step size
           rounded = (quantity // step_size) * step_size
           logger.debug(
               "quantity_rounded",
               symbol=symbol,
               original=quantity,
               rounded=rounded,
               step_size=step_size
           )
           return rounded

       def _round_price(self, symbol: str, price: float) -> float:
           """
           Round price to Binance tick size.

           Example: If BTCUSDT tick size is 0.01 USDT:
               price = 45123.456 → rounded to 45123.45
           """
           if math.isnan(price) or math.isinf(price):
               raise ValueError("price cannot be NaN or Infinity")
           if price <= 0:
               raise ValueError("price must be positive")

           tick_size = self._symbol_manager.get_tick_size(symbol)
           if tick_size <= 0:
               raise ValueError(f"Invalid tick size for {symbol}: {tick_size}")

           # Round down to tick size
           rounded = (price // tick_size) * tick_size
           logger.debug(
               "price_rounded",
               symbol=symbol,
               original=price,
               rounded=rounded,
               tick_size=tick_size
           )
           return rounded

       async def submit_order(
           self,
           symbol: str,
           side: str,
           quantity: float,
           order_type: str,
           price: Optional[float] = None,
           stop_price: Optional[float] = None,
           time_in_force: Optional[str] = None
       ) -> OrderResult:
           """Submit order to Binance."""
           # Validation
           self._validate_symbol(symbol)
           if side not in ["BUY", "SELL"]:
               raise ValueError(f"Invalid side: {side} (must be BUY or SELL)")

           quantity = self._round_quantity(symbol, quantity)

           logger.info(
               "order_submission_started",
               symbol=symbol,
               side=side,
               quantity=quantity,
               order_type=order_type
           )

           try:
               # Call Binance API
               response = await self._client.place_order(
                   symbol=symbol,
                   side=side,
                   type=order_type,
                   quantity=quantity,
                   price=price,
                   stopPrice=stop_price,
                   timeInForce=time_in_force
               )

               # Parse response
               order_result = OrderResult(
                   order_id=str(response["orderId"]),
                   symbol=symbol,
                   side=side,
                   quantity=quantity,
                   price=price,
                   filled_quantity=float(response.get("executedQty", 0)),
                   average_fill_price=float(response.get("cummulativeQuoteQty", 0)) / float(response.get("executedQty", 1)) if response.get("executedQty") else 0,
                   commission=float(response.get("commission", 0)),
                   status=self._map_binance_status(response["status"])
               )

               logger.info(
                   "order_submitted",
                   order_id=order_result.order_id,
                   symbol=symbol,
                   status=order_result.status.value
               )
               return order_result

           except Exception as e:
               logger.error(
                   "order_submission_failed",
                   symbol=symbol,
                   side=side,
                   error=str(e),
                   exc_info=True
               )
               raise BinanceExecutionError(f"Failed to submit order: {str(e)}")

       def _map_binance_status(self, binance_status: str) -> OrderStatus:
           """Map Binance status to internal OrderStatus."""
           mapping = {
               "NEW": OrderStatus.SUBMITTED,
               "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
               "FILLED": OrderStatus.FILLED,
               "CANCELED": OrderStatus.CANCELLED,
               "REJECTED": OrderStatus.REJECTED,
               "EXPIRED": OrderStatus.EXPIRED,
           }
           if binance_status not in mapping:
               logger.warning(f"Unknown Binance status: {binance_status}")
               return OrderStatus.SUBMITTED
           return mapping[binance_status]

       async def cancel_order(self, symbol: str, order_id: str) -> bool:
           """Cancel order on Binance."""
           self._validate_symbol(symbol)

           try:
               response = await self._client.cancel_order(
                   symbol=symbol,
                   orderId=order_id
               )
               logger.info(
                   "order_cancelled",
                   order_id=order_id,
                   symbol=symbol
               )
               return True
           except Exception as e:
               if "Order does not exist" in str(e):
                   logger.warning(
                       "order_already_filled",
                       order_id=order_id,
                       symbol=symbol
                   )
                   return False
               logger.error(
                   "order_cancellation_failed",
                   order_id=order_id,
                   error=str(e)
               )
               raise BinanceExecutionError(f"Failed to cancel order: {str(e)}")

       # ... Additional methods in next steps ...
   ```

   **Key Implementation Details:**

   | Item | Detail |
   |------|--------|
   | **Quantity Rounding** | Always round DOWN to step size (safer than rounding up) |
   | **Price Rounding** | Always round DOWN to tick size (buyer-favorable, seller-disadvantageous) |
   | **Status Mapping** | Create mapping dict, log unknown statuses |
   | **Error Handling** | Catch specific API errors, re-raise as BinanceExecutionError |
   | **Logging** | Log order_id, symbol, status for traceability |
   | **Commission** | Extract from Binance response, may be in BNB or USDT |
   | **Validation** | Check symbol validity, numeric ranges at entry point |

   **Common Pitfalls to Avoid:**
   - ❌ Not validating symbol before API call (wastes API calls)
   - ❌ Rounding UP quantity (exceeds intended amount)
   - ❌ Rounding UP price (worse fill on BUY, better on SELL)
   - ❌ Not logging order_id (impossible to debug)
   - ❌ Silent failures (always log errors with full context)
   - ✅ Always validate at entry point
   - ✅ Test rounding with specific values (0.123456 → 0.12345)
   - ✅ Log both original and rounded values
   - ✅ Re-raise specific exceptions for caller to handle

**Acceptance Criteria:**
- [ ] BinanceExecutionAdapter implements all ExecutionEngine abstract methods
- [ ] Testnet/mainnet switching works via config (verified in __init__)
- [ ] Connectivity check on initialization (fails fast if not connected)
- [ ] All API errors caught and re-raised as BinanceExecutionError
- [ ] Quantity and price rounding methods implemented and tested
- [ ] Status mapping Binance → OrderStatus complete for all statuses
- [ ] All logging includes order_id, symbol for traceability
- [ ] Commission extraction from Binance response
- [ ] Unit test: Quantity rounding (test with edge values like 0.00001)
- [ ] Unit test: Price rounding (test with tick sizes)
- [ ] Unit test: Status mapping for all Binance statuses
- [ ] Integration test: Connect to testnet and verify connectivity
- [ ] Integration test: Real testnet order (if API keys available)

---

3. **Task 4.1.3 - Implement Market Order Submission**
   - Add to: `src/brokers/binance/execution.py`
   - Method: `async submit_market_order(symbol: str, side: str, quantity: float) -> OrderResult`
   - Steps:
     1. Validate symbol with SymbolManager
     2. Round quantity to Binance step size
     3. Submit to Binance API
     4. Poll for fill confirmation
     5. Return filled details (order_id, fill_price, fill_qty, commission)
   - Input validation: Check for NaN/Infinity, negative quantities
   - Error handling: API errors, insufficient balance, invalid symbol
   - Unit test: Quantity rounding, fill details
   - Integration test: Market order on testnet

**Acceptance Criteria:**
- [ ] Quantity rounded to step size correctly
- [ ] Order submitted and filled successfully
- [ ] Fill details (price, quantity, commission) returned
- [ ] Input validation prevents NaN/Infinity
- [ ] Integration test: Market buy/sell on testnet

---

4. **Task 4.1.4 - Implement Limit Order Submission**
   - Add to: `src/brokers/binance/execution.py`
   - Method: `async submit_limit_order(symbol: str, side: str, quantity: float, price: float, time_in_force: str) -> OrderResult`
   - Time in force options: GTC (Good Till Cancelled), IOC (Immediate or Cancel), FOK (Fill or Kill)
   - Round price to Binance tick size
   - Input validation: Check for NaN/Infinity on both price and quantity
   - Error handling: Invalid TIF option, price rounding issues
   - Unit test: Price rounding, TIF options
   - Integration test: Limit order submission/cancellation on testnet

**Acceptance Criteria:**
- [ ] All TIF options work (GTC, IOC, FOK)
- [ ] Price rounded to tick size
- [ ] Unfilled limit orders tracked
- [ ] Integration test: Limit order lifecycle

---

5. **Task 4.1.5 - Implement Stop Loss Order**
   - Add to: `src/brokers/binance/execution.py`
   - Method: `async submit_stop_loss(symbol: str, side: str, quantity: float, stop_price: float) -> OrderResult`
   - Note: Binance uses STOP_LOSS_LIMIT, requires both stop_price and limit_price (set limit ~0.5% beyond stop)
   - Input validation: stop_price below entry for long, above entry for short
   - Unit test: Stop price validation
   - Integration test: Stop loss creation and trigger verification

**Acceptance Criteria:**
- [ ] Stop loss order created correctly
- [ ] Limit price calculated appropriately
- [ ] Integration test: Stop loss on testnet

---

6. **Task 4.1.6 - Implement Take Profit Order**
   - Add to: `src/brokers/binance/execution.py`
   - Method: `async submit_take_profit(symbol: str, side: str, quantity: float, price: float) -> OrderResult`
   - Binance: Use TAKE_PROFIT_LIMIT with calculated limit price
   - Input validation: TP price above entry for long, below entry for short
   - Unit test: TP price validation
   - Integration test: Take profit creation and trigger verification

**Acceptance Criteria:**
- [ ] Take profit order created
- [ ] Price rounded to tick size
- [ ] Integration test: Take profit on testnet

---

7. **Task 4.1.7 - Implement Order Cancellation**
   - Add to: `src/brokers/binance/execution.py`
   - Methods:
     - `async cancel_order(symbol: str, order_id: str) -> bool`
     - `async cancel_all_orders(symbol: str) -> List[str]` (returns cancelled order IDs)
   - Error handling: Already-filled orders (graceful), already-cancelled orders (idempotent)
   - Unit test: Single and bulk cancellation
   - Integration test: Cancel orders on testnet

**Acceptance Criteria:**
- [ ] Single order cancellation works
- [ ] Bulk cancellation works
- [ ] Handles already-filled orders gracefully (no error)
- [ ] Integration test: Cancellation scenarios

---

8. **Task 4.1.8 - Implement Order Status Polling**
   - Add to: `src/brokers/binance/execution.py`
   - Method: `async get_order_status(symbol: str, order_id: str) -> Order`
   - Status mapping (Binance → internal):
     - NEW → SUBMITTED
     - PARTIALLY_FILLED → PARTIALLY_FILLED
     - FILLED → FILLED
     - CANCELED → CANCELLED
     - REJECTED → REJECTED
     - EXPIRED → EXPIRED
   - Track: partial fills, average fill price, commission
   - Unit test: Status mappings for all states
   - Unit test: Commission capture from Binance response

**Acceptance Criteria:**
- [ ] All status mappings correct
- [ ] Partial fills tracked accurately
- [ ] Commission captured in order response
- [ ] Unit test: Status transition coverage

---

9. **Task 4.1.9 - Implement Account Balance Fetching**
   - Add to: `src/brokers/binance/execution.py`
   - Methods:
     - `async get_balance(asset: str) -> Balance` (single asset)
     - `async get_all_balances() -> Dict[str, Balance]` (all assets)
   - Balance dataclass: `free` (available), `locked` (in orders), `total` (sum)
   - Input validation: asset code validation against SymbolManager
   - Error handling: Unknown asset (return zero), API errors
   - Unit test: Single and all balances
   - Integration test: Get balances on testnet

**Acceptance Criteria:**
- [ ] Single asset balance retrieval
- [ ] All balances retrieval
- [ ] Free vs locked balance tracked
- [ ] Integration test: Get balances on testnet

---

10. **Task 4.1.10 - Write Binance Adapter Tests**
    - Files:
      - `tests/unit/test_binance_execution.py` (unit tests)
      - `tests/integration/test_binance_orders.py` (integration tests on testnet)
    - Unit test coverage:
      - Market order: submit, fill, error handling
      - Limit order: submit, cancel, timeout handling
      - Stop loss: submit, validation
      - Take profit: submit, validation
      - Balance: single, all, error handling
      - Status mapping: all status types
      - Input validation: NaN, Infinity, negative values
    - Integration tests (require testnet API keys):
      - Submit and fill market order (buy and sell)
      - Submit limit order, cancel it
      - Submit stop loss order
      - Get balances (verify format)
    - Mocking: Use pytest-asyncio, mock BinanceClient for unit tests
    - Coverage: >85% (can't test all edge cases on testnet)

**Acceptance Criteria:**
- [ ] All adapter methods unit tested
- [ ] Market, limit, SL/TP orders tested
- [ ] Integration tests pass on testnet
- [ ] Error scenarios tested
- [ ] >85% code coverage

---

### **Stage 3: Order Manager Implementation (18-20 hours)**
**Tasks:** 4.2.1 through 4.2.9
**Deliverable:** Complete order lifecycle management with risk checks and reconciliation

---

## 📊 ORDER STATE MACHINE (CRITICAL REFERENCE)

This diagram shows all possible order state transitions. Understanding this prevents bugs:

```
┌─────────────┐
│   PENDING   │  (Order created, not yet submitted to exchange)
└──────┬──────┘
       │
       ├─ risk check FAILS ────────┐
       │                           │
       │                           v
       │                      ❌ REJECTED (End state)
       │
       └─ risk check PASSES
              │
              v
       ┌──────────────┐
       │  SUBMITTED   │  (Sent to exchange, awaiting fill)
       └──────┬───────┘
              │
              ├─ cancel → CANCELLED (End state)
              ├─ timeout → CANCELLED (End state)
              ├─ fill some → PARTIALLY_FILLED
              │              │
              │              ├─ fill rest → FILLED (End state)
              │              ├─ cancel → CANCELLED (End state)
              │              └─ timeout → CANCELLED (End state)
              │
              └─ fill all → FILLED (End state)

Terminal States (monitoring stops):
- FILLED: All quantity filled
- CANCELLED: User cancelled or timeout
- REJECTED: Exchange rejected
- EXPIRED: Order timed out on exchange
```

**Key Invariants:**
- Order can only move FORWARD in states (no backwards moves)
- SUBMITTED → PARTIALLY_FILLED is optional (market orders often skip)
- Only terminal states stop monitoring
- Once in terminal state, order cannot be modified

---

11. **Task 4.2.1 - Create Order Manager**
    - File: `src/core/execution/order_manager.py`
    - Class: `OrderManager`
    - Dependencies:
      - `execution_engine: ExecutionEngine` (from 4.1.2)
      - `risk_controller: RiskController` (from Phase 3)
      - `data_store: DataStore` (from Phase 1)
    - Core attributes:
      - `_pending_orders: Dict[str, Order]` (in-memory cache)
      - `_order_queue: asyncio.Queue` (async order processing)
      - `_monitoring_tasks: Dict[str, asyncio.Task]` (status monitoring)
    - Core methods (abstract signatures):
      ```python
      async def submit_order(self, request: OrderRequest) -> Order:
          """Submit order through risk checks."""

      async def cancel_order(self, order_id: str) -> bool:
          """Cancel pending order."""

      async def get_order(self, order_id: str) -> Optional[Order]:
          """Get order by ID."""

      async def get_pending_orders(self) -> List[Order]:
          """Get all pending orders."""

      async def get_order_history(self, symbol: str = None) -> List[Order]:
          """Get completed/cancelled orders."""
      ```
    - Initialization: Load pending orders from database on startup
    - 100% type hints, full docstrings with examples
    - Unit test: Order creation, pending order tracking

**Acceptance Criteria:**
- [ ] OrderManager class created
- [ ] Integrates RiskController
- [ ] Tracks pending orders in-memory and database
- [ ] Core methods defined with full type hints
- [ ] Unit test: order tracking

---

12. **Task 4.2.2 - Implement Order Submission Flow**
    - Add to: `src/core/execution/order_manager.py`
    - Method: `async submit_order(request: OrderRequest) -> Order`

    **STRICT SEQUENCE (CANNOT SKIP STEPS - Order matters):**

    ```python
    async def submit_order(self, request: OrderRequest) -> Order:
        """
        Submit order with full risk checks and state persistence.

        Flow diagram:
        1. Risk Check    (memory, no side effects)
        2. Create Record (memory only)
        3. Persist DB    (first irreversible step)
        4. Submit API    (can fail, but we have record)
        5. Update DB     (persist submission)
        6. Start Monitor (background tracking)

        Key invariant: Order exists in DB before going to exchange
        """
        order_id = generate_order_id()
        logger.info(
            "order_submission_initiated",
            order_id=order_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity
        )

        # ============ STEP 1: RISK CONTROLLER CHECK ============
        # Run first, before any side effects
        # This is memory-only, no database changes
        try:
            risk_result = await self._risk_controller.check_order(request)
            if not risk_result.approved:
                logger.warning(
                    "order_rejected_by_risk",
                    order_id=order_id,
                    reason=risk_result.reason,
                    symbol=request.symbol,
                    details=risk_result.details  # e.g., "Daily loss would be $500"
                )
                raise OrderRejectedError(risk_result.reason)
        except OrderRejectedError:
            # Re-raise after logging
            raise
        except Exception as e:
            logger.error(
                "risk_check_error",
                order_id=order_id,
                error=str(e),
                exc_info=True
            )
            raise RiskControllerError(f"Risk check failed: {str(e)}")

        # ============ STEP 2: CREATE ORDER RECORD ============
        # This is in-memory only, not persisted yet
        order = Order(
            id=order_id,
            account_id=request.account_id,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            type=request.type,
            price=request.price,  # None for market orders
            stop_price=request.stop_price,  # None for non-stop orders
            status=OrderStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            submitted_at=None,  # Will be set in step 5
            filled_quantity=0.0,
            average_fill_price=0.0,
            commission=0.0
        )

        logger.debug(
            "order_record_created",
            order_id=order_id,
            status=order.status.value,
            in_memory=True
        )

        # ============ STEP 3: PERSIST TO DATABASE ============
        # FIRST IRREVERSIBLE STEP - Now we have a record
        # If anything fails after this, we need to mark order as REJECTED
        try:
            await self._data_store.create_order(order)
            logger.info(
                "order_persisted",
                order_id=order_id,
                symbol=request.symbol,
                status=order.status.value
            )
        except IntegrityError as e:
            # Duplicate order_id (unlikely but possible)
            logger.error(
                "order_persistence_integrity_error",
                order_id=order_id,
                error=str(e)
            )
            raise OrderStorageError(f"Order already exists: {str(e)}")
        except Exception as e:
            # Database connection error, permission error, etc.
            logger.error(
                "order_persistence_failed",
                order_id=order_id,
                error=str(e),
                exc_info=True
            )
            raise OrderStorageError(f"Failed to save order to database: {str(e)}")

        # ============ STEP 4: SUBMIT TO EXECUTION ENGINE ============
        # Can fail, but order record is safe in database
        # On failure, mark order as REJECTED
        try:
            submission_result = await self._execution_engine.submit_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                order_type=order.type,
                price=order.price,
                stop_price=order.stop_price
            )
            logger.info(
                "order_submitted_to_exchange",
                order_id=order_id,
                exchange_order_id=submission_result.order_id,
                symbol=order.symbol
            )
        except Exception as e:
            # Execution engine failed - order is in DB but never reached exchange
            logger.error(
                "order_submission_to_exchange_failed",
                order_id=order_id,
                symbol=order.symbol,
                error=str(e),
                exc_info=True
            )
            # Update database to REJECTED
            order.status = OrderStatus.REJECTED
            try:
                await self._data_store.update_order(order)
            except Exception as db_error:
                logger.critical(
                    "failed_to_mark_order_rejected",
                    order_id=order_id,
                    error=str(db_error)
                )
            # Re-raise the original error
            raise OrderSubmissionError(f"Failed to submit to exchange: {str(e)}")

        # ============ STEP 5: UPDATE STATUS IN DATABASE ============
        # Mark order as SUBMITTED now that it's on the exchange
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.now(timezone.utc)
        # Use exchange order_id if available (for reconciliation)
        if hasattr(submission_result, 'order_id'):
            order.exchange_order_id = submission_result.order_id

        try:
            await self._data_store.update_order(order)
            logger.info(
                "order_status_updated",
                order_id=order_id,
                new_status=order.status.value,
                exchange_order_id=order.exchange_order_id
            )
        except Exception as e:
            logger.error(
                "order_status_update_failed",
                order_id=order_id,
                error=str(e)
            )
            # Order is already on exchange but we can't mark it as SUBMITTED
            # This is a critical issue - we've lost sync
            raise OrderStorageError(f"Failed to update order status: {str(e)}")

        # ============ STEP 6: START MONITORING TASK ============
        # Spawn background task to monitor this order
        # Failure here doesn't fail the submission (order is already submitted)
        try:
            task = asyncio.create_task(self._monitor_order(order))
            self._monitoring_tasks[order.id] = task
            logger.debug(
                "order_monitoring_started",
                order_id=order.id,
                task_id=id(task)
            )
        except Exception as e:
            logger.error(
                "order_monitoring_startup_failed",
                order_id=order.id,
                error=str(e)
            )
            # Don't re-raise - monitoring is not critical for submission

        # ============ STEP 7: RETURN ORDER ============
        logger.info(
            "order_submission_complete",
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            status=order.status.value
        )
        return order
    ```

    **Critical Details:**

    | Aspect | Implementation |
    |--------|-----------------|
    | **Risk Check Timing** | FIRST, before any database changes |
    | **DB Persistence Timing** | BEFORE exchange submission (order must exist in DB) |
    | **Atomic Transactions** | Use `async with session.begin():` for PENDING persist |
    | **Failure Recovery** | If submit fails, mark order REJECTED in DB (synchronization) |
    | **Monitoring Spawn** | After all DB ops complete, spawn as asyncio.create_task() |
    | **Logging Strategy** | Log at start (initiated), each step (persisted, submitted), end (complete) |
    | **Status Transitions** | PENDING → SUBMITTED (never skip, never go backwards) |

    **Error Handling:**
    - Risk check failed → `OrderRejectedError` (log warning, don't persist)
    - Database error → `OrderStorageError` (critical, may need retry)
    - Execution engine error → `OrderSubmissionError` (order marked REJECTED in DB)
    - Monitoring task error → Log but don't raise (order already submitted)

    **Common Pitfalls to Avoid:**
    - ❌ Risk checking AFTER database persist (wrong order)
    - ❌ Not marking order REJECTED if submission fails (sync lost)
    - ❌ Not waiting for database persist before returning (race condition)
    - ❌ Failing submission if monitoring task fails (they're independent)
    - ❌ Not logging order_id at each step (impossible to debug)
    - ✅ Risk check first (no side effects)
    - ✅ Persist before submit (order safety first)
    - ✅ Update status immediately after submit (state accuracy)
    - ✅ Spawn monitoring as background task (don't block submission)

    - Unit test: Success path (all 7 steps execute, order in DB with SUBMITTED status)
    - Unit test: Risk rejection path (order not persisted, OrderRejectedError raised)
    - Unit test: Database failure path (OrderStorageError raised, order not submitted)
    - Unit test: Execution engine failure path (order marked REJECTED in DB, OrderSubmissionError raised)
    - Unit test: Monitoring task startup failure (submission succeeds despite monitoring error)

**Acceptance Criteria:**
- [ ] Risk checks run FIRST (before any database changes)
- [ ] Order saved to database BEFORE submission to exchange (verify ordering with debug logs)
- [ ] Status transitions: PENDING → SUBMITTED correctly
- [ ] Rejections logged with reason and details
- [ ] Database failures trigger OrderStorageError
- [ ] Execution engine failures trigger OrderSubmissionError and mark order REJECTED in DB
- [ ] Monitoring task spawned as asyncio.create_task() (non-blocking)
- [ ] All logging includes order_id for traceability
- [ ] Unit test: Success path (verify all 7 steps)
- [ ] Unit test: Risk rejection path (order never reaches DB)
- [ ] Unit test: Database failure path (synced with exchange attempt)
- [ ] Unit test: Execution engine failure path (order marked REJECTED)
- [ ] Integration test: Real order submission on testnet (verify flow end-to-end)

---

13. **Task 4.2.3 - Implement Order Status Tracking**
    - Add to: `src/core/execution/order_manager.py`
    - Method: `async _monitor_order(order: Order) -> None`

    **Detailed Polling Strategy with Backoff:**

    ```python
    async def _monitor_order(self, order: Order) -> None:
        """
        Monitor order status with exponential backoff.

        Polling timeline:
        0-30s:     Every 1 second (fast feedback for immediate fills)
        30-300s:   Every 5 seconds (normal execution phase)
        300s+:     Every 10 seconds (slow for limit orders waiting)
        Max: 1000 polls (~30 minutes total) then give up

        This strategy balances:
        - Fast detection of quick fills (market orders)
        - Responsiveness to cancellations
        - Low API load for slow orders (limit, stop)
        - Clean exit after reasonable timeout
        """
        logger.info(
            "order_monitoring_started",
            order_id=order.id,
            symbol=order.symbol,
            initial_status=order.status.value
        )

        poll_count = 0
        consecutive_errors = 0
        last_update = order.submitted_at or datetime.now(timezone.utc)

        while poll_count < 1000:  # Max 1000 polls
            # Determine polling interval based on elapsed time
            elapsed = (datetime.now(timezone.utc) - last_update).total_seconds()

            if elapsed < 30:
                poll_interval = 1.0  # Every second (first 30s)
            elif elapsed < 300:
                poll_interval = 5.0  # Every 5 seconds (up to 5 min)
            else:
                poll_interval = 10.0  # Every 10 seconds (after 5 min)

            poll_count += 1

            try:
                # Poll exchange for current status
                exchange_order = await self._execution_engine.get_order_status(
                    symbol=order.symbol,
                    order_id=order.id
                )

                # Check if status changed
                if exchange_order.status != order.status:
                    old_status = order.status.value
                    new_status = exchange_order.status.value

                    logger.info(
                        "order_status_changed",
                        order_id=order.id,
                        symbol=order.symbol,
                        from_status=old_status,
                        to_status=new_status,
                        poll_count=poll_count,
                        elapsed_seconds=elapsed
                    )

                    # Update local order object
                    order.status = exchange_order.status
                    order.filled_quantity = exchange_order.filled_quantity
                    order.average_fill_price = exchange_order.average_fill_price
                    order.commission = exchange_order.commission

                    # Persist status change to database
                    try:
                        await self._data_store.update_order(order)
                    except Exception as e:
                        logger.error(
                            "order_status_persistence_failed",
                            order_id=order.id,
                            new_status=new_status,
                            error=str(e)
                        )
                        # Continue monitoring despite DB error

                    # On partial fill: Log but keep monitoring
                    if order.status == OrderStatus.PARTIALLY_FILLED:
                        logger.info(
                            "order_partially_filled",
                            order_id=order.id,
                            filled_quantity=order.filled_quantity,
                            avg_price=order.average_fill_price,
                            remaining=order.quantity - order.filled_quantity
                        )

                    # On fill or cancel: Handle and stop monitoring
                    if order.status == OrderStatus.FILLED:
                        logger.info(
                            "order_filled",
                            order_id=order.id,
                            filled_quantity=order.filled_quantity,
                            total_commission=order.commission
                        )
                        # Create Trade record and update Position (see Task 4.2.4)
                        await self._handle_fill(order)
                        break  # Stop monitoring

                    elif order.status in [OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
                        logger.info(
                            "order_terminal_state",
                            order_id=order.id,
                            terminal_status=order.status.value,
                            filled_quantity=order.filled_quantity
                        )
                        # No _handle_fill() for cancellations/rejections
                        break  # Stop monitoring

                # Reset error counter on successful poll
                consecutive_errors = 0
                last_update = datetime.now(timezone.utc)

            except asyncio.CancelledError:
                # Task was cancelled externally (e.g., app shutdown)
                logger.info(
                    "order_monitoring_cancelled",
                    order_id=order.id,
                    poll_count=poll_count
                )
                break

            except Exception as e:
                consecutive_errors += 1
                logger.warning(
                    "order_status_poll_failed",
                    order_id=order.id,
                    poll_count=poll_count,
                    error=str(e),
                    consecutive_errors=consecutive_errors
                )

                # Give up after 3 consecutive errors
                if consecutive_errors >= 3:
                    logger.error(
                        "order_monitoring_gave_up",
                        order_id=order.id,
                        poll_count=poll_count,
                        reason="Too many consecutive errors"
                    )
                    break

            # Wait before next poll
            try:
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                logger.info(
                    "order_monitoring_cancelled_during_sleep",
                    order_id=order.id
                )
                break

        # Final cleanup
        logger.info(
            "order_monitoring_stopped",
            order_id=order.id,
            final_status=order.status.value,
            poll_count=poll_count,
            final_filled_qty=order.filled_quantity
        )

        # Remove from monitoring dictionary
        if order.id in self._monitoring_tasks:
            del self._monitoring_tasks[order.id]
    ```

    **Polling Interval Strategy:**

    | Period | Interval | Rationale |
    |--------|----------|-----------|
    | 0-30s | 1 second | Market orders fill immediately, need fast feedback |
    | 30-300s | 5 seconds | Normal execution window, reasonable trade-off |
    | 300s+ | 10 seconds | Limit/stop orders waiting, no rush |
    | Max 1000 polls | ~30 min total | Give up after reasonable timeout |

    **State Transition Rules:**
    - SUBMITTED → PARTIALLY_FILLED → FILLED (normal flow)
    - SUBMITTED → FILLED (skip partial, market orders often do this)
    - Any state → CANCELLED (user cancellation or timeout)
    - SUBMITTED → REJECTED (exchange rejection)
    - PARTIALLY_FILLED → CANCELLED (partially filled then cancelled)

    **Critical Implementation Details:**
    1. **Compare Status:** Use `!=` operator, not string comparison
    2. **Update All Fields:** filled_quantity, average_fill_price, commission
    3. **Partial Fills:** Log but DON'T call _handle_fill() yet
    4. **Terminal States:** FILLED, CANCELLED, REJECTED, EXPIRED all stop monitoring
    5. **Error Recovery:** Continue polling on transient errors, give up after 3 consecutive
    6. **Cancellation Safety:** Catch `asyncio.CancelledError` for graceful shutdown
    7. **Cleanup:** Always remove from _monitoring_tasks dict

    **Test Scenarios:**

    ```python
    # Test 1: Market order fills immediately
    # Expected: SUBMITTED → FILLED in first poll
    order = await order_manager.submit_order(market_buy_request)
    await asyncio.sleep(1.5)  # Wait for monitoring
    assert order.status == OrderStatus.FILLED

    # Test 2: Limit order fills after 2 polls
    # Expected: SUBMITTED → SUBMITTED → PARTIALLY_FILLED → FILLED
    order = await order_manager.submit_order(limit_buy_request)
    await asyncio.sleep(2.5)  # Wait 2+ seconds = 3+ polls
    assert order.status == OrderStatus.FILLED

    # Test 3: User cancels order
    # Expected: SUBMITTED → SUBMITTED → CANCELLED
    order = await order_manager.submit_order(limit_order)
    await asyncio.sleep(2.5)  # Let it submit
    await order_manager.cancel_order(order.id)  # Cancel
    assert order.status == OrderStatus.CANCELLED
    ```

    **Common Pitfalls to Avoid:**
    - ❌ Polling too fast (wastes API calls)
    - ❌ Polling too slow (slow fill detection for market orders)
    - ❌ Not persisting partial fills to database (lost on crash)
    - ❌ Calling _handle_fill() on PARTIALLY_FILLED (premature)
    - ❌ Continuing to monitor after terminal state (wastes API calls)
    - ❌ Not handling asyncio.CancelledError (ungraceful shutdown)
    - ✅ Use exponential backoff (fast at first, slower over time)
    - ✅ Persist every status change to database
    - ✅ Only call _handle_fill() on FILLED status
    - ✅ Stop monitoring on any terminal state
    - ✅ Log poll count and elapsed time for debugging

    - Unit test: Status transitions (SUBMITTED → FILLED)
    - Unit test: Partial fill tracking (quantity and price updates)
    - Unit test: Terminal state detection (stops monitoring)
    - Unit test: Polling backoff (verify intervals increase with time)
    - Unit test: Error handling (continues on transient errors, gives up after 3)
    - Unit test: Cancellation safety (CancelledError caught gracefully)
    - Integration test: Real order monitoring on testnet

**Acceptance Criteria:**
- [ ] Polling starts immediately after submission
- [ ] Polling interval increases with elapsed time (1s → 5s → 10s)
- [ ] Status updates persist to database immediately
- [ ] Partial fills tracked (filled_quantity, average_fill_price)
- [ ] Terminal states detected and monitoring stopped
- [ ] Consecutive errors tracked, give up after 3
- [ ] asyncio.CancelledError caught for graceful shutdown
- [ ] Monitoring task removed from _monitoring_tasks dict on completion
- [ ] All status transitions logged with timestamps
- [ ] Unit test: All transition scenarios
- [ ] Integration test: Real testnet order monitoring

---

14. **Task 4.2.4 - Implement Order Fill Handling**
    - Add to: `src/core/execution/order_manager.py`
    - Method: `async _handle_fill(order: Order, fill_info: FillInfo) -> None`
    - Called by: `_monitor_order()` when status changes to FILLED or after partial fill completion
    - **Steps:**
      1. **Create Trade Record:**
         - Trade(order_id=order.id, symbol=symbol, side=side, quantity=filled_qty, price=fill_price, commission=commission)
         - Set: executed_at=datetime.now(timezone.utc)
         - Save to database
      2. **Update Order:**
         - Set: filled_quantity, average_fill_price, status=FILLED
         - Calculate total_commission from all partial fills
         - Save to database
      3. **Update Position:**
         - For BUY: Call `position_tracker.open_position()` or `position_tracker.update_position()`
         - For SELL: Call `position_tracker.close_position()` or `position_tracker.update_position()`
         - Pass trade details to position tracker
      4. **Log Fill:**
         ```python
         logger.info("order_filled",
             order_id=order.id, symbol=symbol, side=side,
             filled_qty=filled_qty, fill_price=fill_price,
             commission=commission)
         ```
      5. **Send Notification:** Alert system (implementation in Phase 5)
    - **Commission Handling:**
      - Extract from Binance response (usually BNB or USDT)
      - Convert to USDT equivalent if needed
      - Track in Trade record
    - **Error Handling:**
      - Database error → Log critical, retry once, then skip notification
      - Position tracker error → Log warning (don't fail fill), still send alert
    - Unit test: Trade creation
    - Unit test: Order update
    - Unit test: Commission capture
    - Unit test: Error handling

**Acceptance Criteria:**
- [ ] Trade records created for each fill
- [ ] Order updated with filled quantity and average price
- [ ] Positions updated (delegation to position_tracker)
- [ ] Commission tracked
- [ ] Unit test: fill handling

---

15. **Task 4.2.5 - Implement Bracket Orders**
    - Add to: `src/core/execution/order_manager.py`
    - Method: `async submit_bracket_order(entry_request: OrderRequest, stop_loss_price: float, take_profit_price: float) -> BracketOrder`
    - **BracketOrder dataclass:**
      ```python
      @dataclass
      class BracketOrder:
          entry_order: Order
          stop_loss_order: Order
          take_profit_order: Order
          oco_linked: bool = True  # One Cancels Other
      ```
    - **Workflow:**
      1. Submit entry order via `submit_order(entry_request)` → get entry_order
      2. Wait for entry_order to be SUBMITTED (not necessarily filled)
      3. If entry_request is MARKET: Entry will fill immediately, SL/TP will work on fill
      4. If entry_request is LIMIT: Entry may not fill, SL/TP will be "ready" but not submitted yet
      5. On entry fill (via `_handle_fill()`):
         - Submit stop loss order: `execution_engine.submit_stop_loss(symbol, opposite_side, quantity, stop_loss_price)`
         - Submit take profit order: `execution_engine.submit_take_profit(symbol, opposite_side, quantity, take_profit_price)`
         - Link orders in database: `BracketOrderLink(entry_id=entry, sl_id=sl, tp_id=tp, oco=True)`
      6. On SL or TP fill:
         - Cancel the other leg: `cancel_order(other_leg_id)`
         - Log OCO execution: `logger.info("oco_executed", filled_leg=filled_id, cancelled_leg=cancelled_id)`
    - **OCO Implementation:**
      - After entry fills, monitor both SL and TP orders
      - When one fills, immediately cancel the other
      - Handle race conditions: If both fill simultaneously, accept first, cancel second (will be "already filled")
    - Error handling:
      - Entry submission failure → Raise error
      - SL/TP submission failure → Log critical, attempt to cancel entry
      - Both legs filled → Log warning, accept both (unusual but possible)
    - Unit test: Bracket order creation
    - Unit test: OCO cancellation logic
    - Integration test: Bracket order on testnet (may not fully test OCO due to testnet limitations)

**Acceptance Criteria:**
- [ ] Bracket order structure created
- [ ] Entry, SL, and TP orders submitted
- [ ] OCO linking works (one cancels other)
- [ ] Integration test: bracket order submission

---

16. **Task 4.2.6 - Implement Order Timeout Handling**
    - Add to: `src/core/execution/order_manager.py`
    - Method: `async _handle_timeouts()` (runs periodically, e.g., every 5 seconds)
    - **Timeout Configuration (configurable per order type):**
      ```python
      TIMEOUT_SECONDS = {
          'MARKET': 30,        # Market orders usually fill in seconds
          'LIMIT': 3600,       # 1 hour for limit orders
          'STOP_LOSS': None,   # Never timeout (keep until triggered or manually cancelled)
          'TAKE_PROFIT': None, # Never timeout
      }
      ```
    - **Logic:**
      1. Get all SUBMITTED or PARTIALLY_FILLED orders
      2. For each order:
         - Calculate age: `now - order.submitted_at`
         - If age > timeout threshold AND order.type in TIMEOUT_SECONDS:
           - Call `cancel_order(order.id)` → Cancel on exchange
           - Update order status to CANCELLED in database
           - Log: `logger.info("order_expired", order_id=id, type=type, age_seconds=age)`
    - **Exception:** Stop orders keep `TIMEOUT = None` (keep indefinitely)
    - **Scheduled Task:** Start background task in OrderManager.__init__() to run every 5 seconds
    - Unit test: Timeout calculation for different order types
    - Unit test: Timeout cancellation trigger

**Acceptance Criteria:**
- [ ] Configurable timeout per order type
- [ ] Auto-cancellation on timeout (LIMIT orders)
- [ ] Stop orders never timeout
- [ ] Logging for expired orders
- [ ] Unit test: timeout scenarios

---

17. **Task 4.2.7 - Implement Order Reconciliation**
    - Add to: `src/core/execution/order_manager.py`
    - Class: `OrderReconciler`
    - Method: `async reconcile_orders() -> ReconciliationResult`
    - **Purpose:** Detect and fix discrepancies between local order state and exchange state
    - **Reconciliation Checks:**
      1. **Get local pending orders:** All orders with status SUBMITTED or PARTIALLY_FILLED
      2. **Get exchange open orders:** Call `execution_engine.get_open_orders()`
      3. **Compare Sets:**
         - For each exchange order: Check if it exists in local pending orders
           - If NOT found: Log warning, add to local with "FOUND_ON_EXCHANGE" status
         - For each local order: Check if it exists on exchange
           - If NOT found AND order.submitted_at > 5 minutes ago: Mark as FILLED or CANCELLED
      4. **Reconciliation Result:**
         ```python
         @dataclass
         class ReconciliationResult:
             total_local: int
             total_exchange: int
             missing_locally: int  # On exchange but not local
             missing_on_exchange: int  # Local but not exchange
             status: str  # "OK", "MINOR_MISMATCH", "MAJOR_MISMATCH"
         ```
    - **Thresholds:**
      - Minor mismatch: 1-2 orders missing (auto-correct)
      - Major mismatch: 3+ orders missing (alert operator, don't auto-correct)
    - **Action on Mismatch:**
      - Minor: Auto-update local database to match exchange
      - Major: Log critical, send alert, pause new order submission
    - **Scheduled Execution:**
      - Run on startup: `await reconcile_orders()`
      - Run periodically: Every 5 minutes in background task
    - **Error Handling:**
      - Exchange API error → Log error, skip reconciliation this cycle, retry next cycle
    - Unit test: Order reconciliation scenarios (missing locally, missing on exchange)
    - Integration test: Reconciliation on testnet

**Acceptance Criteria:**
- [ ] Detects orphan orders (on exchange but not local)
- [ ] Detects stale orders (local but not on exchange)
- [ ] Updates local state on discrepancy
- [ ] Logs reconciliation results
- [ ] Integration test: reconciliation with testnet

---

18. **Task 4.2.8a - Implement Order State Reconciliation (PRD Feature I)**
    - Add to: `src/core/execution/order_manager.py`
    - Class: `OrderStateReconciler` (enhanced version of task 4.2.7)
    - **Purpose:** Per PRD Feature I - Reconcile local state with exchange state
    - **Frequency:** Every 60 seconds
    - **Reconciliation Checks:**
      1. **Open Orders Check:**
         - Local pending orders vs. exchange open orders
         - Same logic as Task 4.2.7
      2. **Positions Check:**
         - Local positions vs. exchange balance/positions (delegated to PositionTracker.sync_positions in Session 4B)
      3. **Balances Check:**
         - Local account balances vs. exchange balances
         - Call `execution_engine.get_all_balances()`
         - Compare free + locked with local tracking
      4. **Mismatch Handling:**
         - Minor difference (<1%): Auto-correct, log as info
         - Major difference (>=1%): Alert operator, pause trading (via kill switch signal)
    - **Minor Difference Threshold:** 1% (e.g., 1000 USDT difference on 100k account)
    - **Auto-Correction Logic:**
      - For minor mismatches: Update local database to match exchange
      - Log correction: `logger.info("reconciliation_corrected", type="balance", actual=actual, local=local, diff_pct=diff_pct)`
    - **Major Difference Alert:**
      ```python
      if diff_pct >= 0.01:  # >= 1%
          await alert_manager.send_critical(
              title="Order State Mismatch",
              message=f"Major difference in {category}: {diff_pct*100:.2f}%",
              action="Pause trading and investigate"
          )
          # Signal to pause new orders (via RiskController flag or direct to OrderManager)
      ```
    - **Tracking:**
      - Track mismatch frequency: Count mismatches per day
      - Log for audit trail: Store all reconciliation results in database
    - **Scheduled Task:** Background task runs every 60 seconds starting on OrderManager init
    - Unit test: All mismatch scenarios (minor <1%, major >=1%)
    - Unit test: Auto-correction logic
    - Integration test: Reconciliation with testnet

**Acceptance Criteria:**
- [ ] Runs every 60 seconds
- [ ] Compares local orders to exchange
- [ ] Compares local positions to exchange
- [ ] Compares local balances to exchange
- [ ] Auto-corrects minor differences (<1%)
- [ ] Alerts operator on major differences (>=1%)
- [ ] Pauses trading on major difference (signals stop)
- [ ] Logs all mismatches for audit
- [ ] Unit test: all mismatch scenarios
- [ ] Integration test: reconciliation with testnet

---

19. **Task 4.2.8 - Create Order Manager API Endpoints**
    - File: `src/api/routes/orders.py`
    - Create FastAPI router with order management endpoints
    - **Endpoints:**
      - `POST /api/orders` - Submit order
        - Request: `{symbol, side, quantity, type, ...}`
        - Response: `{order_id, status, created_at, ...}`
      - `GET /api/orders` - List orders
        - Query params: `symbol` (optional), `status` (optional), `limit`, `offset`
        - Response: `List[Order]` with full details
      - `GET /api/orders/{id}` - Get order details
        - Response: Single Order with all fields
      - `DELETE /api/orders/{id}` - Cancel order
        - Response: `{success: bool, message: str}`
    - **Error Responses:**
      - 400: Invalid request (missing field, invalid value)
      - 404: Order not found
      - 422: Order cannot be cancelled (already filled)
      - 500: Server error
    - **Authorization:** All endpoints protected (implementation in Phase 5)
    - Unit test: All CRUD operations
    - Integration test: Full API workflow

**Acceptance Criteria:**
- [ ] POST endpoint submits orders
- [ ] GET endpoints retrieve orders
- [ ] DELETE endpoint cancels orders
- [ ] Proper HTTP status codes
- [ ] Integration test: API calls

---

### **Stage 4: Testing & Integration (4-5 hours)**
**Task:** 4.2.9

20. **Task 4.2.9 - Write Order Manager Tests**
    - Files:
      - `tests/unit/test_order_manager.py`
      - `tests/integration/test_order_manager_integration.py`
    - **Unit Tests (use mock execution engine):**
      - Order submission success
      - Order submission with risk rejection
      - Order status transitions (SUBMITTED → FILLED → complete flow)
      - Fill handling (trade creation, position update)
      - Bracket order creation and OCO logic
      - Order timeout handling
      - Order reconciliation (missing locally, missing on exchange)
      - API endpoints (all CRUD operations)
    - **Integration Tests (use testnet):**
      - Submit market order, wait for fill, verify in database
      - Submit limit order, cancel it
      - Bracket order flow (if possible on testnet)
      - Reconciliation on real testnet account
    - **Mocking Strategy:**
      - Mock ExecutionEngine in unit tests
      - Mock RiskController to return approved/rejected results
      - Real execution engine on testnet for integration tests
    - **Coverage Target:** >90% (unit), >85% (integration)
    - Test utilities:
      - Fixtures for OrderManager setup
      - Fixtures for mock execution engine
      - Helper functions for order creation

**Acceptance Criteria:**
- [ ] All order manager flows tested
- [ ] Unit tests with mocks
- [ ] Integration tests on testnet
- [ ] >90% code coverage (unit)
- [ ] All tests passing

---

## PRODUCTION QUALITY GATES

### **Automated Gates**
Before submission, ALL must pass with 0 errors:

```bash
# 1. Type Safety (MANDATORY: 100% coverage)
mypy src/core/execution/ src/brokers/binance/ --strict
# Result: "Success: no issues found"

# 2. Code Linting
ruff check src/core/execution/ src/brokers/binance/
# Result: No violations

# 3. Import Organization
isort src/core/execution/ src/brokers/binance/ --check --diff
# Result: "All done! No files would be modified"

# 4. Unit Tests (MANDATORY: all pass)
pytest tests/unit/test_binance_execution.py tests/unit/test_order_manager.py -v
# Result: All tests passing

# 5. Integration Tests
pytest tests/integration/test_binance_orders.py tests/integration/test_order_manager_integration.py -v
# Result: All tests passing (requires testnet API keys)

# 6. Coverage Report
pytest tests/unit/ tests/integration/ \
  --cov=src/core/execution --cov=src/brokers/binance \
  --cov-report=term-missing | grep -E "^(src/|TOTAL)"
# Result: All files >90%, TOTAL >90%

# 7. Production Audit
@production-code-audit audit src/core/execution/ src/brokers/binance/
# Result: Grade A- or higher
```

---

## CODE QUALITY STANDARDS

### **Type Hints (100% Required)**
```python
# CORRECT - Full type hints
async def submit_order(
    self,
    request: OrderRequest
) -> Order:
    """Submit order with risk checks.

    Args:
        request: Order request details

    Returns:
        Created Order with status=SUBMITTED
    """

# INCORRECT - Missing return type
async def submit_order(self, request: OrderRequest):
    pass
```

### **Timezone-Aware Timestamps (ALWAYS)**
```python
# CORRECT
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc),
    nullable=False
)

# INCORRECT
created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.utcnow,  # NEVER USE THIS
)
```

### **Input Validation (All Numeric Fields)**
```python
# CORRECT - Comprehensive validation
@validates("quantity", "price")
def validate_positive_numbers(self, key: str, value: float) -> float:
    if value is None:
        raise ValueError(f"{key} cannot be None")
    if math.isnan(value):
        raise ValueError(f"{key} cannot be NaN")
    if math.isinf(value):
        raise ValueError(f"{key} cannot be Infinity")
    if value <= 0:
        raise ValueError(f"{key} must be positive")
    return value
```

### **Structured Logging (MANDATORY)**
```python
# CORRECT
logger.info(
    "order_submitted",
    order_id=order.id,
    symbol=order.symbol,
    side=order.side,
    quantity=order.quantity,
    price=order.price if order.type == OrderType.LIMIT else None
)

# INCORRECT
logger.info(f"Order {order.id} submitted for {order.symbol}")
```

---

## DECISION CONSISTENCY

**BEFORE implementing, read** `.claude/DECISIONS.md` and verify consistency with:
- DEC-2026-02-08-002: SQLAlchemy 2.0 with Mapped[T]
- DEC-2026-02-08-003: Timezone-aware timestamps
- DEC-2026-02-08-006: Type hints 100%
- DEC-2026-02-08-007: Input validation at model layer
- DEC-2026-02-08-008: Structured logging
- Any other applicable decisions

---

## ACCEPTANCE CRITERIA SUMMARY

**Session 4A is complete when:**

✅ **Section 4.1 (Binance Adapter):**
- [ ] All 10 tasks completed
- [ ] Can submit market orders on testnet
- [ ] Can submit limit orders on testnet
- [ ] Can submit stop loss/take profit orders
- [ ] Can cancel orders
- [ ] Can poll order status
- [ ] Can get balances
- [ ] All tests passing (>85% coverage)

✅ **Section 4.2 (Order Manager):**
- [ ] All 9 tasks completed
- [ ] Order submission flow with risk checks working
- [ ] Order status tracking functioning
- [ ] Fill handling creating trades correctly
- [ ] Bracket orders with OCO logic
- [ ] Order timeout handling
- [ ] Order reconciliation detecting discrepancies
- [ ] PRD Feature I: Order state reconciliation every 60 seconds
- [ ] API endpoints for order management
- [ ] All tests passing (>90% coverage)

✅ **Production Quality:**
- [ ] mypy --strict: 0 errors
- [ ] ruff check: 0 violations
- [ ] isort: 0 changes needed
- [ ] pytest: 100% pass rate
- [ ] Coverage: >90% overall
- [ ] Production audit: Grade A- or higher
- [ ] Decision consistency verified

---

## FILE STRUCTURE

```
src/core/execution/
  ├── __init__.py
  ├── interface.py           # ExecutionEngine ABC (Task 4.1.1)
  └── order_manager.py       # OrderManager + reconciliation (Tasks 4.2.1-4.2.8a)

src/brokers/binance/
  ├── __init__.py
  └── execution.py           # BinanceExecutionAdapter (Tasks 4.1.2-4.1.9)

src/api/routes/
  └── orders.py             # Order API endpoints (Task 4.2.8)

tests/unit/
  ├── test_binance_execution.py      # Adapter unit tests (Task 4.1.10)
  └── test_order_manager.py          # Order manager tests (Task 4.2.9)

tests/integration/
  ├── test_binance_orders.py         # Adapter integration tests (Task 4.1.10)
  └── test_order_manager_integration.py  # Integration tests (Task 4.2.9)
```

---

## ENVIRONMENT & DEPENDENCIES

**Virtual Environment:** Must be activated before running ANY Python code
```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

**Required Packages (verify in requirements.txt):**
- sqlalchemy>=2.0 (SQLAlchemy 2.0 syntax required)
- aiohttp (async HTTP for Binance API)
- pytest-asyncio (async test support)
- pytest-cov (coverage reporting)
- python-binance (if not already installed)

**Binance Testnet Setup:**
- API keys required for integration tests
- Set in `.env`:
  ```
  BINANCE_TESTNET_API_KEY=...
  BINANCE_TESTNET_API_SECRET=...
  ```

---

## SIGN-OFF

**Session 4A is COMPLETE and PRODUCTION READY when:**

```
✅ Type Safety: mypy --strict passes
✅ Code Quality: ruff/isort pass
✅ Tests: All unit and integration tests pass
✅ Coverage: >90% overall, no file <90%
✅ Production Audit: Grade A- or higher
✅ Decision Consistency: All decisions verified

READY FOR: Session 4B (Position Tracking & Execution Quality)
```

---

**Last Updated:** 2026-02-13
**Format:** Production Grade Implementation Prompt
**Applies To:** Phase 4 Session A (Sections 4.1 + 4.2)
