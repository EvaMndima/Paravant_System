# PHASE 4: EXECUTION
## Weeks 7-8 | 34 Tasks | ~88 Hours

**Goal:** Reliable order execution with accurate position tracking.

**Start Conditions:** Phase 3 complete (risk controls working)  
**Exit Conditions:** Orders execute on testnet, positions track correctly, P&L accurate to 0.1%

---

## 📊 PHASE 4 PROGRESS

```
Section 4.1 Binance Adapter   [░░░░░░░░░░] 0/10 tasks
Section 4.2 Order Manager     [░░░░░░░░░░] 0/10 tasks
Section 4.3 Position Tracker  [░░░░░░░░░░] 0/8 tasks
Section 4.4 Execution Quality [░░░░░░░░░░] 0/6 tasks
───────────────────────────────────────────────────
PHASE 4 TOTAL                 [░░░░░░░░░░] 0/34 tasks
```

---

## SECTION 4.1: BINANCE ADAPTER
*Estimated: 20 hours*

### Task 4.1.1: Create Execution Engine Interface
- [ ] **Status:** Not Started
- **Description:** Abstract interface for execution engines
- **Dependencies:** [2.1.1]
- **Effort:** 1.5 hours

**File:** `src/core/execution/interface.py`

**ExecutionEngine ABC:**
```python
class ExecutionEngine(ABC):
    @abstractmethod
    async def submit_order(self, order: Order) -> OrderResult:
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str) -> float:
        pass
```

**Acceptance Criteria:**
- [ ] Abstract interface defined
- [ ] All necessary methods specified
- [ ] Result types defined
- [ ] Unit test: interface contract

---

### Task 4.1.2: Create Binance Execution Adapter
- [ ] **Status:** Not Started
- **Description:** Binance-specific execution implementation
- **Dependencies:** [4.1.1, 2.1.1]
- **Effort:** 3 hours

**File:** `src/brokers/binance/execution.py`

**BinanceExecutionAdapter implements ExecutionEngine:**
- Uses BinanceClient for API calls
- Maps internal order types to Binance types
- Handles Binance-specific responses
- Testnet support

**Acceptance Criteria:**
- [ ] Implements all interface methods
- [ ] Testnet/mainnet switching
- [ ] Error handling for API errors
- [ ] Integration test: submit order on testnet

---

### Task 4.1.3: Implement Market Order Submission
- [ ] **Status:** Not Started
- **Description:** Submit market orders to Binance
- **Dependencies:** [4.1.2, 2.3.2]
- **Effort:** 2 hours

**Add to:** `src/brokers/binance/execution.py`

**Method:** `async submit_market_order(symbol, side, quantity) -> OrderResult`

**Steps:**
1. Validate symbol with SymbolManager
2. Round quantity to step size
3. Submit to Binance
4. Wait for fill confirmation
5. Return filled details

**Acceptance Criteria:**
- [ ] Quantity rounded correctly
- [ ] Order submitted successfully
- [ ] Fill details returned
- [ ] Integration test: market order on testnet

---

### Task 4.1.4: Implement Limit Order Submission
- [ ] **Status:** Not Started
- **Description:** Submit limit orders with price
- **Dependencies:** [4.1.2]
- **Effort:** 2 hours

**Add to:** `src/brokers/binance/execution.py`

**Method:** `async submit_limit_order(symbol, side, quantity, price, time_in_force) -> OrderResult`

**Time in force options:**
- GTC (Good Till Cancelled)
- IOC (Immediate or Cancel)
- FOK (Fill or Kill)

**Acceptance Criteria:**
- [ ] Price rounded to tick size
- [ ] All TIF options work
- [ ] Unfilled orders tracked
- [ ] Integration test: limit order on testnet

---

### Task 4.1.5: Implement Stop Loss Order
- [ ] **Status:** Not Started
- **Description:** Submit stop loss orders
- **Dependencies:** [4.1.2]
- **Effort:** 2 hours

**Add to:** `src/brokers/binance/execution.py`

**Method:** `async submit_stop_loss(symbol, side, quantity, stop_price) -> OrderResult`

**Note:** Binance uses STOP_LOSS_LIMIT, so need stop_price AND limit_price.

**Acceptance Criteria:**
- [ ] Stop loss created correctly
- [ ] Triggers at stop price
- [ ] Integration test: stop loss on testnet

---

### Task 4.1.6: Implement Take Profit Order
- [ ] **Status:** Not Started
- **Description:** Submit take profit orders
- **Dependencies:** [4.1.2]
- **Effort:** 1.5 hours

**Add to:** `src/brokers/binance/execution.py`

**Method:** `async submit_take_profit(symbol, side, quantity, price) -> OrderResult`

**Acceptance Criteria:**
- [ ] Take profit created
- [ ] Triggers at target price
- [ ] Integration test: take profit on testnet

---

### Task 4.1.7: Implement Order Cancellation
- [ ] **Status:** Not Started
- **Description:** Cancel open orders
- **Dependencies:** [4.1.2]
- **Effort:** 1.5 hours

**Add to:** `src/brokers/binance/execution.py`

**Methods:**
- `async cancel_order(symbol, order_id) -> bool`
- `async cancel_all_orders(symbol) -> List[str]` (returns cancelled IDs)

**Acceptance Criteria:**
- [ ] Single order cancellation
- [ ] Bulk cancellation
- [ ] Handles already-filled orders gracefully
- [ ] Integration test: cancel orders

---

### Task 4.1.8: Implement Order Status Polling
- [ ] **Status:** Not Started
- **Description:** Poll and update order status
- **Dependencies:** [4.1.2]
- **Effort:** 2 hours

**Add to:** `src/brokers/binance/execution.py`

**Method:** `async poll_order_status(symbol, order_id) -> Order`

**Status mapping:**
- NEW → SUBMITTED
- PARTIALLY_FILLED → PARTIALLY_FILLED
- FILLED → FILLED
- CANCELED → CANCELLED
- REJECTED → REJECTED
- EXPIRED → EXPIRED

**Acceptance Criteria:**
- [ ] All statuses mapped correctly
- [ ] Partial fills tracked
- [ ] Commission captured
- [ ] Unit test: status mapping

---

### Task 4.1.9: Implement Account Balance Fetching
- [ ] **Status:** Not Started
- **Description:** Fetch current account balances
- **Dependencies:** [4.1.2]
- **Effort:** 1.5 hours

**Add to:** `src/brokers/binance/execution.py`

**Methods:**
- `async get_balance(asset: str) -> Balance`
- `async get_all_balances() -> Dict[str, Balance]`

**Balance includes:** free, locked, total

**Acceptance Criteria:**
- [ ] Single asset balance
- [ ] All balances
- [ ] Free vs locked tracked
- [ ] Integration test: get balances

---

### Task 4.1.10: Write Binance Adapter Tests
- [ ] **Status:** Not Started
- **Description:** Unit and integration tests
- **Dependencies:** [4.1.1-4.1.9]
- **Effort:** 3 hours

**Files:**
- `tests/unit/test_binance_execution.py`
- `tests/integration/test_binance_orders.py`

**Integration tests (testnet):**
- Submit and fill market order
- Submit limit order, cancel it
- Submit stop loss, verify creation
- Get balances

**Acceptance Criteria:**
- [ ] All methods unit tested
- [ ] Integration tests pass on testnet
- [ ] Error scenarios tested
- [ ] >85% coverage

---

## SECTION 4.2: ORDER MANAGER
*Estimated: 18 hours*

### Task 4.2.1: Create Order Manager
- [ ] **Status:** Not Started
- **Description:** Manage order lifecycle
- **Dependencies:** [4.1.1, 1.2.4, 3.1.1]
- **Effort:** 3 hours

**File:** `src/core/execution/order_manager.py`

**OrderManager class:**
```python
class OrderManager:
    def __init__(
        self,
        execution_engine: ExecutionEngine,
        risk_controller: RiskController,
        data_store: DataStore
    ):
        self._pending_orders: Dict[str, Order] = {}
        self._order_queue: asyncio.Queue = asyncio.Queue()
    
    async def submit_order(self, request: OrderRequest) -> Order:
        """Submit order through risk checks."""
        pass
    
    async def cancel_order(self, order_id: str) -> bool:
        pass
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        pass
    
    async def get_pending_orders(self) -> List[Order]:
        pass
```

**Acceptance Criteria:**
- [ ] Integrates risk checks before submission
- [ ] Tracks pending orders
- [ ] Persists to database
- [ ] Unit test: order flow

---

### Task 4.2.2: Implement Order Submission Flow
- [ ] **Status:** Not Started
- **Description:** Full order submission with risk checks
- **Dependencies:** [4.2.1]
- **Effort:** 2.5 hours

**Add to:** `src/core/execution/order_manager.py`

**Flow:**
1. Receive OrderRequest
2. Run risk controller checks
3. If approved:
   - Create Order record
   - Save to database (PENDING status)
   - Submit to execution engine
   - Update status (SUBMITTED)
4. If rejected:
   - Log rejection
   - Raise OrderRejectedError

**Acceptance Criteria:**
- [ ] Risk checks run first
- [ ] Order saved before submission
- [ ] Status updates correctly
- [ ] Rejections logged
- [ ] Unit test: submission flow

---

### Task 4.2.3: Implement Order Status Tracking
- [ ] **Status:** Not Started
- **Description:** Track and update order status
- **Dependencies:** [4.2.1, 4.1.8]
- **Effort:** 2 hours

**Add to:** `src/core/execution/order_manager.py`

**Method:** `async _monitor_order(order: Order)`

**Behavior:**
- Poll execution engine for status
- Update database on changes
- Handle partial fills
- Notify on terminal states (FILLED, CANCELLED, REJECTED)

**Polling interval:** 1 second for pending, exponential backoff

**Acceptance Criteria:**
- [ ] Status updates in real-time
- [ ] Partial fills tracked
- [ ] Terminal states detected
- [ ] Unit test: status transitions

---

### Task 4.2.4: Implement Order Fill Handling
- [ ] **Status:** Not Started
- **Description:** Process filled orders, create trades
- **Dependencies:** [4.2.3, 1.2.6]
- **Effort:** 2 hours

**Add to:** `src/core/execution/order_manager.py`

**Method:** `async _handle_fill(order: Order, fill_info: FillInfo)`

**Behavior:**
- Create Trade record for each fill
- Update order filled_quantity, average_fill_price
- Update position (open or close)
- Calculate commission

**Acceptance Criteria:**
- [ ] Trade records created
- [ ] Order updated correctly
- [ ] Positions updated
- [ ] Commission tracked
- [ ] Unit test: fill handling

---

### Task 4.2.5: Implement Bracket Orders
- [ ] **Status:** Not Started
- **Description:** Entry + stop loss + take profit as a unit
- **Dependencies:** [4.2.1, 4.1.5, 4.1.6]
- **Effort:** 2.5 hours

**Add to:** `src/core/execution/order_manager.py`

**Method:** `async submit_bracket_order(entry: OrderRequest, stop_loss: float, take_profit: float) -> BracketOrder`

**BracketOrder:**
- Entry order
- Stop loss order (OCO with take profit)
- Take profit order

**OCO behavior:** When one hits, cancel the other.

**Acceptance Criteria:**
- [ ] All three orders created
- [ ] OCO linking works
- [ ] Cancellation cascades
- [ ] Integration test: bracket order

---

### Task 4.2.6: Implement Order Timeout Handling
- [ ] **Status:** Not Started
- **Description:** Handle orders that don't fill
- **Dependencies:** [4.2.3]
- **Effort:** 1.5 hours

**Add to:** `src/core/execution/order_manager.py`

**Behavior:**
- Configurable timeout per order type
- Limit orders: cancel after timeout (default 1 hour)
- Stop orders: keep until triggered or cancelled
- Log expired orders

**Acceptance Criteria:**
- [ ] Timeout per order type
- [ ] Auto-cancellation works
- [ ] Logging for expired orders
- [ ] Unit test: timeout scenarios

---

### Task 4.2.7: Implement Order Reconciliation
- [ ] **Status:** Not Started
- **Description:** Reconcile local state with exchange
- **Dependencies:** [4.2.1, 4.1.8]
- **Effort:** 2 hours

**Add to:** `src/core/execution/order_manager.py`

**Method:** `async reconcile_orders()`

**Behavior:**
- Get all open orders from exchange
- Compare with local pending orders
- Update any discrepancies
- Log reconciliation results

**Run:** On startup and periodically (every 5 minutes)

**Acceptance Criteria:**
- [ ] Detects orphan orders
- [ ] Updates local state
- [ ] Logs discrepancies
- [ ] Integration test: reconciliation

---

### Task 4.2.8: Create Order Manager API Endpoints
- [ ] **Status:** Not Started
- **Description:** API for order management
- **Dependencies:** [4.2.1]
- **Effort:** 1.5 hours

**File:** `src/api/routes/orders.py`

**Endpoints:**
- `POST /api/orders` - Submit order
- `GET /api/orders` - List orders (with filters)
- `GET /api/orders/{id}` - Get order details
- `DELETE /api/orders/{id}` - Cancel order

**Acceptance Criteria:**
- [ ] All CRUD operations
- [ ] Proper error responses
- [ ] Order status in response
- [ ] Integration test: API calls

---

### Task 4.2.8a: Implement Order State Reconciliation (PRD Feature I)
- [ ] **Status:** Not Started
- **Description:** Enhanced order reconciliation per PRD Feature I
- **Dependencies:** [4.2.7, 4.2.8]
- **Effort:** 2 hours

**Add to:** `src/core/execution/order_manager.py`

**PRD Feature I - Order State Reconciliation:**
```python
class OrderReconciler:
    """
    Reconcile local order state with exchange per PRD Feature I.
    
    Frequency: Every 60 seconds
    
    Checks:
    - Open orders: local vs exchange
    - Positions: local vs exchange (via 4.3.5)
    - Balances: local vs exchange
    
    On mismatch:
    - Minor (<1%): Auto-correct, log
    - Major (>=1%): Alert operator, pause trading
    """
    
    RECONCILIATION_INTERVAL_SECONDS = 60
    MINOR_DIFFERENCE_THRESHOLD = 0.01  # 1%
    
    def __init__(self, order_manager, data_store, alert_manager):
        self.order_manager = order_manager
        self.data_store = data_store
        self.alert_manager = alert_manager
        self._mismatch_count = 0
    
    async def reconcile(self) -> ReconciliationResult:
        """Full reconciliation check."""
        results = {
            'orders': await self._reconcile_orders(),
            'positions': await self._reconcile_positions(),
            'balances': await self._reconcile_balances()
        }
        
        await self._handle_mismatches(results)
        return ReconciliationResult(**results)
    
    async def _reconcile_orders(self) -> OrderReconcileResult:
        """Compare local open orders to exchange."""
        local_orders = await self.order_manager.get_pending_orders()
        exchange_orders = await self.order_manager.execution_engine.get_open_orders()
        
        mismatches = []
        
        # Check for orders on exchange not in local
        for ex_order in exchange_orders:
            if not self._find_local(ex_order, local_orders):
                mismatches.append({
                    'type': 'exchange_only',
                    'order_id': ex_order.id,
                    'action': 'add_to_local'
                })
        
        # Check for orders in local not on exchange
        for local_order in local_orders:
            if not self._find_exchange(local_order, exchange_orders):
                mismatches.append({
                    'type': 'local_only',
                    'order_id': local_order.id,
                    'action': 'mark_as_filled_or_cancelled'
                })
        
        return OrderReconcileResult(mismatches=mismatches)
    
    async def _handle_mismatches(self, results: Dict):
        """Handle detected mismatches."""
        all_mismatches = []
        for category, result in results.items():
            all_mismatches.extend(result.mismatches)
        
        for mismatch in all_mismatches:
            if self._is_minor(mismatch):
                # Auto-correct
                await self._auto_correct(mismatch)
                await self._log_correction(mismatch)
            else:
                # Major difference - alert and pause
                await self.alert_manager.send_warning(
                    title="Order Reconciliation Mismatch",
                    message=f"Major difference detected: {mismatch}"
                )
                self._mismatch_count += 1
        
        # Track mismatch frequency for root cause analysis
        await self._track_mismatch_frequency()
```

**Acceptance Criteria:**
- [ ] Runs every 60 seconds
- [ ] Compares local open orders to exchange
- [ ] Compares local positions to exchange
- [ ] Compares local balances to exchange
- [ ] Auto-corrects minor differences (<1%)
- [ ] Alerts operator on major differences (>=1%)
- [ ] Pauses trading on major differences
- [ ] Logs all mismatches for audit
- [ ] Tracks mismatch frequency for root cause analysis
- [ ] Unit test: all mismatch scenarios
- [ ] Integration test: reconciliation with testnet

---

### Task 4.2.9: Write Order Manager Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive order manager tests
- **Dependencies:** [4.2.1-4.2.8]
- **Effort:** 2.5 hours

**File:** `tests/unit/test_order_manager.py`

**Test scenarios:**
- Submit order (success path)
- Submit order (risk rejection)
- Order status transitions
- Fill handling
- Bracket orders
- Timeout handling
- Reconciliation

**Acceptance Criteria:**
- [ ] All flows tested
- [ ] Edge cases covered
- [ ] Mock execution engine
- [ ] >85% coverage

---

## SECTION 4.3: POSITION TRACKER
*Estimated: 14 hours*

### Task 4.3.1: Create Position Tracker
- [ ] **Status:** Not Started
- **Description:** Track open positions and P&L
- **Dependencies:** [1.2.5, 2.1.7]
- **Effort:** 2.5 hours

**File:** `src/core/execution/position_tracker.py`

**PositionTracker class:**
```python
class PositionTracker:
    def __init__(
        self,
        data_store: DataStore,
        market_data: MarketDataService
    ):
        self._positions: Dict[str, Position] = {}  # symbol -> Position
    
    async def open_position(self, fill: Trade) -> Position:
        pass
    
    async def update_position(self, fill: Trade) -> Position:
        pass
    
    async def close_position(self, symbol: str, fill: Trade) -> Position:
        pass
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        pass
    
    async def get_all_positions(self) -> List[Position]:
        pass
    
    async def calculate_unrealized_pnl(self, symbol: str) -> float:
        pass
```

**Acceptance Criteria:**
- [ ] Tracks open positions
- [ ] Handles partial closes
- [ ] Calculates P&L
- [ ] Unit test: position tracking

---

### Task 4.3.2: Implement Position Opening
- [ ] **Status:** Not Started
- **Description:** Open new position from fill
- **Dependencies:** [4.3.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/execution/position_tracker.py`

**Method:** `async open_position(account_id, strategy_id, fill) -> Position`

**Behavior:**
- Create Position record
- Set entry price, quantity
- Set stop loss / take profit if provided
- Save to database
- Add to cache

**Acceptance Criteria:**
- [ ] Position created correctly
- [ ] All fields populated
- [ ] Persisted to database
- [ ] Unit test: open position

---

### Task 4.3.3: Implement Position Updates
- [ ] **Status:** Not Started
- **Description:** Update position on additional fills
- **Dependencies:** [4.3.1]
- **Effort:** 2 hours

**Add to:** `src/core/execution/position_tracker.py`

**Scenarios:**
1. **Adding to position:** Recalculate average entry price
2. **Partial close:** Reduce quantity, calculate realized P&L
3. **Full close:** Set closed_at, calculate final P&L

**Average entry calculation:**
```python
new_avg = (old_qty * old_avg + new_qty * new_price) / (old_qty + new_qty)
```

**Acceptance Criteria:**
- [ ] Average entry correct
- [ ] Partial closes work
- [ ] Realized P&L calculated
- [ ] Unit test: update scenarios

---

### Task 4.3.4: Implement P&L Calculator
- [ ] **Status:** Not Started
- **Description:** Calculate unrealized and realized P&L
- **Dependencies:** [4.3.1, 2.1.7]
- **Effort:** 2 hours

**Add to:** `src/core/execution/position_tracker.py`

**Methods:**
- `calculate_unrealized_pnl(position, current_price) -> float`
- `calculate_realized_pnl(position) -> float`
- `calculate_return_pct(position, current_price) -> float`

**Include commission in P&L calculations.**

**Acceptance Criteria:**
- [ ] Unrealized P&L correct for long/short
- [ ] Realized P&L includes commission
- [ ] Return % calculation correct
- [ ] Unit test: P&L calculations with known values

---

### Task 4.3.5: Implement Position Sync
- [ ] **Status:** Not Started
- **Description:** Sync positions with exchange
- **Dependencies:** [4.3.1, 4.1.9]
- **Effort:** 2 hours

**Add to:** `src/core/execution/position_tracker.py`

**Method:** `async sync_positions()`

**Behavior:**
- Get balances from exchange
- Compare with local positions
- Reconcile discrepancies
- Log any differences

**Note:** Binance spot doesn't have "positions" in futures sense, so track via balances.

**Acceptance Criteria:**
- [ ] Detects balance mismatches
- [ ] Updates local state
- [ ] Logs discrepancies
- [ ] Integration test: sync

---

### Task 4.3.5a: Implement Position Staleness Monitor
- [ ] **Status:** Not Started
- **Description:** Monitor and act on stale positions per PRD Feature K
- **Dependencies:** [4.3.5]
- **Effort:** 2 hours

**Add to:** `src/core/execution/position_tracker.py`

**PositionStalenessMonitor class:**
```python
class PositionStalenessMonitor:
    """
    Track and act on positions held too long per PRD Feature K.
    
    Thresholds by strategy type:
    
    Day Trading:
    - Warning: 24 hours
    - Force review: 48 hours
    - Max hold: 72 hours
    
    Swing Trading:
    - Warning: 7 days
    - Force review: 14 days
    - Max hold: 30 days
    
    Exceptions:
    - Profitable positions: 50% extended threshold
    - Operator override: Can mark as "intentionally long-term"
    """
    
    THRESHOLDS = {
        'day_trading': {
            'warning_hours': 24,
            'force_review_hours': 48,
            'max_hold_hours': 72
        },
        'swing_trading': {
            'warning_days': 7,
            'force_review_days': 14,
            'max_hold_days': 30
        }
    }
    
    PROFITABLE_EXTENSION = 1.5  # 50% longer threshold
    
    def __init__(self, position_tracker, data_store, alert_manager):
        self.position_tracker = position_tracker
        self.data_store = data_store
        self.alert_manager = alert_manager
        self._review_queue: List[str] = []
    
    async def check_staleness(self, position: Position) -> StalenessResult:
        """Check if position is stale based on strategy type."""
        strategy = await self.data_store.get_strategy(position.strategy_id)
        thresholds = self._get_thresholds(strategy.type)
        
        hold_duration = datetime.utcnow() - position.opened_at
        
        # Profitable positions get 50% extension
        if position.unrealized_pnl > 0:
            thresholds = self._extend_thresholds(thresholds)
        
        return StalenessResult(
            position_id=position.id,
            hold_duration=hold_duration,
            should_warn=hold_duration > thresholds['warning'],
            should_review=hold_duration > thresholds['force_review'],
            should_close=hold_duration > thresholds['max_hold']
        )
    
    async def process_stale_positions(self):
        """Check all positions, alert or close as needed."""
        positions = await self.position_tracker.get_all_positions()
        
        for position in positions:
            # Skip overridden positions
            if await self._is_overridden(position.id):
                continue
            
            result = await self.check_staleness(position)
            
            if result.should_close:
                # Auto-close (if enabled in config)
                if self._auto_close_enabled():
                    await self._auto_close(position)
                else:
                    await self._send_max_hold_alert(position)
            elif result.should_review:
                await self._add_to_review_queue(position)
            elif result.should_warn:
                await self._send_warning(position)
    
    async def override_position(self, position_id: str, reason: str):
        """Mark position as intentionally long-term."""
        await self.data_store.add_position_override(position_id, reason)
```

**Acceptance Criteria:**
- [ ] Day trading thresholds: warn 24h, review 48h, max 72h
- [ ] Swing trading thresholds: warn 7d, review 14d, max 30d
- [ ] Profitable positions get 50% extended threshold
- [ ] Warning alerts sent at warning threshold
- [ ] Positions added to review queue at force_review threshold
- [ ] Auto-close at max_hold (if enabled)
- [ ] Operator can override with "intentionally long-term"
- [ ] Unit test: all staleness scenarios
- [ ] Unit test: profitable extension calculation

---

### Task 4.3.6: Create Position API Endpoints
- [ ] **Status:** Not Started
- **Description:** API for position data
- **Dependencies:** [4.3.1]
- **Effort:** 1.5 hours

**File:** `src/api/routes/positions.py`

**Endpoints:**
- `GET /api/positions` - List all positions
- `GET /api/positions/{symbol}` - Get position for symbol
- `DELETE /api/positions/{symbol}` - Close position (market order)

**Acceptance Criteria:**
- [ ] List positions with P&L
- [ ] Single position details
- [ ] Close position works
- [ ] Integration test: API calls

---

### Task 4.3.7: Write Position Tracker Tests
- [ ] **Status:** Not Started
- **Description:** Position tracker tests
- **Dependencies:** [4.3.1-4.3.6]
- **Effort:** 2 hours

**File:** `tests/unit/test_position_tracker.py`

**Test scenarios:**
- Open long position
- Open short position
- Add to position
- Partial close
- Full close
- P&L calculations
- Position sync

**Acceptance Criteria:**
- [ ] All scenarios tested
- [ ] P&L verified with manual calculations
- [ ] >85% coverage

---

## SECTION 4.4: EXECUTION QUALITY
*Estimated: 10 hours*

### Task 4.4.1: Create Slippage Tracker
- [ ] **Status:** Not Started
- **Description:** Track execution slippage
- **Dependencies:** [4.2.4]
- **Effort:** 2 hours

**File:** `src/core/execution/quality.py`

**SlippageTracker:**
```python
@dataclass
class SlippageRecord:
    order_id: str
    expected_price: float
    actual_price: float
    slippage_pct: float
    slippage_bps: float  # basis points

class SlippageTracker:
    def record(self, order: Order, expected_price: float, actual_price: float):
        pass
    
    def get_average_slippage(self, symbol: str = None) -> float:
        pass
    
    def get_slippage_stats(self) -> SlippageStats:
        pass
```

**Acceptance Criteria:**
- [ ] Records all fills with slippage
- [ ] Calculates statistics
- [ ] Per-symbol breakdown
- [ ] Unit test: slippage calculations

---

### Task 4.4.1a: Implement Pre-Trade Slippage Estimation
- [ ] **Status:** Not Started
- **Description:** Estimate slippage BEFORE order placement per PRD Feature F
- **Dependencies:** [4.4.1, 2.2.4]
- **Effort:** 2.5 hours

**Add to:** `src/core/execution/quality.py`

**SlippageEstimator class:**
```python
@dataclass
class SlippageEstimate:
    estimated_slippage_pct: float
    components: Dict[str, float]  # base, size, volatility, spread
    should_warn: bool  # > 0.3%
    should_block: bool  # > 1.0%
    recommended_action: str

class SlippageEstimator:
    """
    Estimate slippage BEFORE placing order per PRD Feature F.
    
    Estimation model:
    - base_slippage = 0.05%
    - size_factor = (order_size / avg_daily_volume) * 0.5%
    - volatility_factor = (current_ATR / avg_ATR) * 0.1%
    - spread_factor = current_spread / 2
    
    Total estimated slippage = sum of all factors
    
    Thresholds:
    - Warn: > 0.3%
    - Block: > 1.0%
    """
    
    BASE_SLIPPAGE_PCT = 0.05
    SIZE_FACTOR_MULTIPLIER = 0.5
    VOLATILITY_FACTOR_MULTIPLIER = 0.1
    
    WARN_THRESHOLD_PCT = 0.3
    BLOCK_THRESHOLD_PCT = 1.0
    
    def __init__(self, market_data, slippage_tracker):
        self.market_data = market_data
        self.slippage_tracker = slippage_tracker
    
    async def estimate_slippage(
        self,
        symbol: str,
        order_size: float,
        side: str
    ) -> SlippageEstimate:
        """
        Estimate expected slippage before placing order.
        """
        # Base slippage
        base = self.BASE_SLIPPAGE_PCT
        
        # Size factor
        avg_volume = await self.market_data.get_avg_daily_volume(symbol)
        size_factor = (order_size / avg_volume) * self.SIZE_FACTOR_MULTIPLIER
        
        # Volatility factor
        current_atr = await self.market_data.get_current_atr(symbol)
        avg_atr = await self.market_data.get_avg_atr(symbol)
        volatility_factor = (current_atr / avg_atr) * self.VOLATILITY_FACTOR_MULTIPLIER
        
        # Spread factor
        spread = await self.market_data.get_current_spread(symbol)
        spread_factor = spread / 2
        
        # Total estimate
        total = base + size_factor + volatility_factor + spread_factor
        
        # Determine action
        should_warn = total > self.WARN_THRESHOLD_PCT
        should_block = total > self.BLOCK_THRESHOLD_PCT
        
        if should_block:
            action = "BLOCK - Slippage too high"
        elif should_warn:
            action = "WARN - Consider smaller size"
        else:
            action = "OK"
        
        return SlippageEstimate(
            estimated_slippage_pct=total,
            components={
                'base': base,
                'size': size_factor,
                'volatility': volatility_factor,
                'spread': spread_factor
            },
            should_warn=should_warn,
            should_block=should_block,
            recommended_action=action
        )
    
    async def compare_estimate_vs_actual(self, order_id: str):
        """
        After order fills, compare estimate to actual for model improvement.
        Called after order fill to track accuracy.
        """
        estimate = await self._get_estimate(order_id)
        actual = await self.slippage_tracker.get_slippage(order_id)
        
        error = actual - estimate.estimated_slippage_pct
        
        # Store for weekly recalibration
        await self._record_estimation_error(order_id, estimate, actual, error)
    
    async def recalibrate_model(self):
        """Weekly recalibration based on estimated vs actual."""
        errors = await self._get_recent_errors()
        # Adjust multipliers based on systematic over/under-estimation
        pass
```

**Integration:** Call before order submission in OrderManager

**Acceptance Criteria:**
- [ ] Base slippage of 0.05% applied
- [ ] Size factor calculated: (size / avg_volume) * 0.5%
- [ ] Volatility factor calculated: (current_ATR / avg_ATR) * 0.1%
- [ ] Spread factor calculated: spread / 2
- [ ] Warning at > 0.3% estimated slippage
- [ ] Block order at > 1.0% estimated slippage
- [ ] Comparison of estimated vs actual recorded
- [ ] Weekly recalibration based on errors
- [ ] Unit test: estimation calculations
- [ ] Unit test: warn/block thresholds

---

### Task 4.4.2: Create Fill Rate Tracker
- [ ] **Status:** Not Started
- **Description:** Track order fill rates
- **Dependencies:** [4.2.3]
- **Effort:** 1.5 hours

**Add to:** `src/core/execution/quality.py`

**FillRateTracker:**
- Track time to fill
- Track partial vs full fills
- Track cancellation rate
- Track rejection rate

**Acceptance Criteria:**
- [ ] Time to fill tracked
- [ ] Fill rate statistics
- [ ] By order type breakdown
- [ ] Unit test: fill rate calcs

---

### Task 4.4.3: Create Execution Report Generator
- [ ] **Status:** Not Started
- **Description:** Generate execution quality reports
- **Dependencies:** [4.4.1, 4.4.2]
- **Effort:** 2 hours

**Add to:** `src/core/execution/quality.py`

**ExecutionReportGenerator:**
```python
def generate_report(start_date, end_date) -> ExecutionReport:
    """Generate execution quality report."""
    return ExecutionReport(
        total_orders=...,
        fill_rate=...,
        average_slippage_bps=...,
        average_fill_time_seconds=...,
        orders_by_type=...,
        slippage_by_symbol=...,
    )
```

**Acceptance Criteria:**
- [ ] Comprehensive report
- [ ] Date range filtering
- [ ] Exportable format
- [ ] Unit test: report generation

---

### Task 4.4.4: Create Execution Quality API
- [ ] **Status:** Not Started
- **Description:** API endpoints for execution metrics
- **Dependencies:** [4.4.1-4.4.3]
- **Effort:** 1.5 hours

**Add to:** `src/api/routes/orders.py`

**Endpoints:**
- `GET /api/execution/stats` - Current execution statistics
- `GET /api/execution/report` - Full execution report (date range)
- `GET /api/execution/slippage` - Slippage analysis

**Acceptance Criteria:**
- [ ] Stats endpoint works
- [ ] Report generation works
- [ ] Slippage breakdown available
- [ ] Integration test: API calls

---

### Task 4.4.5: Write Execution Quality Tests
- [ ] **Status:** Not Started
- **Description:** Tests for execution quality tracking
- **Dependencies:** [4.4.1-4.4.4]
- **Effort:** 2 hours

**File:** `tests/unit/test_execution_quality.py`

**Test scenarios:**
- Slippage calculation (positive, negative, zero)
- Fill rate statistics
- Report generation
- API responses

**Acceptance Criteria:**
- [ ] All metrics tested
- [ ] Edge cases covered
- [ ] >80% coverage

---

## 📋 PHASE 4 COMPLETION CHECKLIST

Before moving to Phase 5, verify:

- [ ] All 34 tasks completed
- [ ] Can submit market orders on Binance testnet
- [ ] Can submit limit orders on Binance testnet
- [ ] Can submit stop loss orders on Binance testnet
- [ ] Orders tracked through full lifecycle
- [ ] Positions open/close correctly
- [ ] P&L calculations accurate (verify with manual calculation)
- [ ] Slippage tracked for all fills
- [ ] Pre-trade slippage estimation working (warn at 0.3%, block at 1.0%)
- [ ] Order state reconciliation runs every 60 seconds
- [ ] Position staleness monitor alerts on stale positions
- [ ] Order reconciliation detects discrepancies
- [ ] `pytest tests/unit/test_order_manager.py` passes
- [ ] `pytest tests/unit/test_position_tracker.py` passes
- [ ] `pytest tests/integration/test_binance_orders.py` passes
- [ ] No linting errors

**PRD Compliance Checklist:**
- [ ] Feature F: Pre-trade slippage estimation
- [ ] Feature I: Order state reconciliation every 60s
- [ ] Feature K: Position staleness monitor

**Integration Test Checklist:**
- [ ] Submit market buy → fills → position opens
- [ ] Submit market sell → fills → position closes
- [ ] Submit limit buy → wait → cancel
- [ ] Submit bracket order → entry fills → SL/TP created
- [ ] Position P&L updates with market price

**Sign-off:** _________________ Date: _________________

---

**Previous Phase:** [03_PHASE_3_RISK_CONTROLS.md](./03_PHASE_3_RISK_CONTROLS.md)  
**Next Phase:** [05_PHASE_5_STRATEGY.md](./05_PHASE_5_STRATEGY.md)
