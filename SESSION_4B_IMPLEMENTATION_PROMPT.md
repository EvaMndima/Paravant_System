# SESSION 4B: POSITION TRACKING & EXECUTION QUALITY
## Position Management & Execution Monitoring
**Production Grade | Zero Technical Debt | 90%+ Test Coverage**

---

## Executive Summary

**Session 4B** implements position tracking and execution quality monitoring. Positions represent open trades and the foundation for P&L calculations. This session follows Session 4A completion.

- **Duration:** ~43 hours
- **Tasks:** 16 (Sections 4.3 + 4.4)
- **Deliverables:** PositionTracker, P&L calculations, slippage tracking, execution quality metrics
- **Quality Gates:** 100% type hints, zero technical debt, >90% test coverage, Grade A- production audit

---

## CRITICAL DEPENDENCIES

**Must Complete BEFORE Starting Session 4B:**
- ✅ Session 4A: ExecutionEngine, OrderManager, order submission/tracking/fill handling
- ✅ Phase 1: Position model, Trade model, Account model
- ✅ Phase 2: MarketDataService, SymbolManager, DataStore
- ✅ Phase 3: RiskController (for volatility metrics, if used)

**Session 4B Feeds Into:**
- Session 4A (already done)
- Phase 5: Strategy execution and backtesting

---

## IMPLEMENTATION SEQUENCE

The strict execution order prevents circular dependencies and ensures proper integration:

### **Stage 1: Position Tracker Foundation (8-10 hours)**
**Tasks:** 4.3.1 through 4.3.3
**Deliverable:** Complete position lifecycle management (open, update, close)

1. **Task 4.3.1 - Create Position Tracker**
   - File: `src/core/execution/position_tracker.py`
   - Class: `PositionTracker`
   - Dependencies:
     - `data_store: DataStore` (persistent storage)
     - `market_data: MarketDataService` (real-time prices)
   - Core attributes:
     - `_positions: Dict[str, Position]` (symbol → Position cache)
     - `_trade_cache: List[Trade]` (recent trades for debugging)
   - Core methods (abstract signatures):
     ```python
     async def open_position(
         self,
         account_id: str,
         strategy_id: str,
         fill: Trade
     ) -> Position:
         """Open new position from trade fill."""

     async def update_position(
         self,
         symbol: str,
         fill: Trade
     ) -> Position:
         """Add to or close position based on side."""

     async def close_position(
         self,
         symbol: str,
         fill: Trade
     ) -> Position:
         """Close entire position."""

     async def get_position(self, symbol: str) -> Optional[Position]:
         """Get position by symbol."""

     async def get_all_positions(self) -> List[Position]:
         """Get all open positions."""

     async def calculate_unrealized_pnl(self, symbol: str) -> float:
         """Calculate P&L for open position."""
     ```
   - Initialization: Load all open positions from database on startup
   - 100% type hints, full docstrings with examples
   - Unit test: Position creation, retrieval

**Acceptance Criteria:**
- [ ] PositionTracker class created
- [ ] Loads positions from database on init
- [ ] Tracks open positions in cache
- [ ] All methods have full type hints
- [ ] Unit test: basic operations

---

2. **Task 4.3.2 - Implement Position Opening**
   - Add to: `src/core/execution/position_tracker.py`
   - Method: `async open_position(account_id: str, strategy_id: str, fill: Trade) -> Position`
   - **Workflow:**
     1. Create Position record:
        - symbol, account_id, strategy_id
        - entry_price = fill.price
        - quantity = fill.quantity
        - side = BUY (long) or SELL (short)
        - opened_at = datetime.now(timezone.utc)
     2. Initialize optional fields (if provided in fill):
        - stop_loss_price (if bracket order)
        - take_profit_price (if bracket order)
     3. Add to cache: `_positions[symbol] = position`
     4. Persist to database via data_store
     5. Return Position object
   - **Error Handling:**
     - Database error → Log and raise PositionStorageError
     - Invalid fill data (NaN, Infinity) → Raise ValueError with validation message
   - **Validation:**
     - Check for NaN/Infinity in entry_price and quantity
     - Verify side is BUY or SELL
     - Verify symbol is valid
   - Unit test: Position creation with BUY and SELL
   - Unit test: Optional stop/take profit fields

**Acceptance Criteria:**
- [ ] Position created from fill
- [ ] All fields populated correctly
- [ ] Persisted to database
- [ ] Added to cache
- [ ] Input validation prevents NaN/Infinity
- [ ] Unit test: open position

---

3. **Task 4.3.3 - Implement Position Updates**
   - Add to: `src/core/execution/position_tracker.py`
   - Method: `async update_position(symbol: str, fill: Trade) -> Position`
   - **Purpose:** Handle adding to position, partial closes, or full closes
   - **Scenarios (determined by position.side vs fill.side):**

     **Scenario 1: Adding to Position (same direction)**
     - position.side = BUY, fill.side = BUY (or SELL, SELL)
     - Calculate new average entry:
       ```python
       new_avg = (old_qty * old_avg + new_qty * new_price) / (old_qty + new_qty)
       ```
     - Update: position.entry_price, position.quantity
     - Save to database

     **Scenario 2: Partial Close (opposite direction, fill_qty < position_qty)**
     - position.side = BUY, fill.side = SELL (or opposite)
     - Calculate realized P&L:
       ```python
       realized_pnl = (fill.price - position.entry_price) * fill.quantity - commission
       ```
     - Update: position.quantity -= fill.quantity
     - Add realized_pnl to position.total_realized_pnl
     - Save to database

     **Scenario 3: Full Close (opposite direction, fill_qty >= position_qty)**
     - position.side = BUY, fill.side = SELL with fill_qty >= position_qty
     - Calculate realized P&L (same as scenario 2)
     - Set: position.closed_at = datetime.now(timezone.utc)
     - Set: position.status = CLOSED
     - Remove from cache: `del _positions[symbol]`
     - Save to database
     - Log: `logger.info("position_closed", symbol=symbol, entry=entry_price, exit=fill.price, pnl=realized_pnl)`

   - **Error Handling:**
     - Database error → Log and raise
     - Invalid quantity (would result in negative position) → Raise ValueError
     - Invalid scenario (unhandled combination) → Log critical
   - **Validation:**
     - Check for NaN/Infinity in fill price/quantity
     - Verify symbol matches position symbol
   - Unit test: Add to position (average entry calculation)
   - Unit test: Partial close (realized P&L calculation)
   - Unit test: Full close (position closure, cache removal)

**Acceptance Criteria:**
- [ ] Average entry calculation correct (adding to position)
- [ ] Partial closes work (update quantity, calculate P&L)
- [ ] Full closes work (set closed_at, status=CLOSED)
- [ ] Realized P&L calculated including commission
- [ ] Unit test: all update scenarios

---

### **Stage 2: P&L Calculations (6-8 hours)**
**Tasks:** 4.3.4, 4.3.5, 4.3.5a
**Deliverable:** Complete P&L tracking (realized + unrealized) and position staleness monitoring

4. **Task 4.3.4 - Implement P&L Calculator**
   - Add to: `src/core/execution/position_tracker.py`
   - Methods:
     - `calculate_unrealized_pnl(position: Position, current_price: float) -> float`
     - `calculate_realized_pnl(position: Position) -> float`
     - `calculate_return_pct(position: Position, current_price: float) -> float`

   **DETAILED FINANCIAL FORMULAS WITH WORKED EXAMPLES:**

   **Formula 1: Unrealized P&L for LONG Position**
   ```
   unrealized_pnl = (current_price - entry_price) * quantity - commission_paid

   Example:
   - Entry: Bought 0.5 BTC @ $45,000 = $22,500 investment
   - Commission paid: $5 (on entry)
   - Current price: $46,000
   - Calculation:
     unrealized = (46000 - 45000) * 0.5 - 5
     unrealized = 1000 * 0.5 - 5
     unrealized = 500 - 5
     unrealized = $495

   Key insight: Commission reduces profit (or increases loss)
   ```

   **Formula 2: Unrealized P&L for SHORT Position**
   ```
   unrealized_pnl = (entry_price - current_price) * quantity - commission_paid

   Example:
   - Entry: Sold 0.5 BTC @ $46,000 (short) = $23,000 potential proceeds
   - Commission paid: $5 (on entry)
   - Current price: $45,000
   - Calculation:
     unrealized = (46000 - 45000) * 0.5 - 5
     unrealized = 1000 * 0.5 - 5
     unrealized = 500 - 5
     unrealized = $495

   Key insight: Short profits when price falls, same commission deduction
   ```

   **Formula 3: Return Percentage**
   ```
   return_pct = (unrealized_pnl / (entry_price * quantity)) * 100

   Example:
   - Unrealized P&L: $495
   - Entry investment: 45000 * 0.5 = $22,500
   - Return: (495 / 22500) * 100 = 2.20%

   Verification:
   - Price moved 1000 / 45000 = 2.222% = 2.22% ✓
   - Less commission impact: 5 / 22500 = 0.022%
   - Net return: 2.22% - 0.022% = 2.198% ≈ 2.20% ✓
   ```

   **Formula 4: Average Entry Price (for adding to position)**
   ```
   new_avg_entry = (old_qty * old_avg + new_qty * new_price) / (old_qty + new_qty)

   Example - Averaging down:
   - Own: 0.5 BTC @ $45,000 (cost basis $22,500)
   - Add: 0.5 BTC @ $44,000 (cost $22,000)
   - New average: (0.5 * 45000 + 0.5 * 44000) / (0.5 + 0.5)
   - New average: (22500 + 22000) / 1.0
   - New average: $44,500

   Verification:
   - Total cost: $22,500 + $22,000 = $44,500
   - Total qty: 1.0 BTC
   - Cost per unit: $44,500 / 1.0 = $44,500 ✓
   ```

   **Formula 5: Realized P&L (on close)**
   ```
   realized_pnl = (exit_price - entry_price) * quantity - total_commission

   Example - Close position:
   - Entry: 0.5 BTC @ $45,000
   - Commission on entry: $5
   - Exit: 0.5 BTC @ $46,000
   - Commission on exit: $5
   - Calculation:
     realized = (46000 - 45000) * 0.5 - (5 + 5)
     realized = 500 - 10
     realized = $490

   Key insight: Commission paid on BOTH entry and exit
   ```

   **Implementation Guide:**

   ```python
   @staticmethod
   def calculate_unrealized_pnl(
       position: Position,
       current_price: float
   ) -> float:
       """Calculate unrealized P&L for open position."""
       # Input validation
       if math.isnan(current_price) or math.isinf(current_price):
           logger.warning(
               "unrealized_pnl_invalid_price",
               position_id=position.id,
               current_price=current_price
           )
           return float('nan')

       if position.quantity <= 0:
           return 0.0

       # Calculate based on side
       if position.side == "BUY":
           # Long: profit when price rises
           price_diff = current_price - position.entry_price
       else:
           # Short: profit when price falls
           price_diff = position.entry_price - current_price

       # Unrealized = price move * quantity - commission
       unrealized = (price_diff * position.quantity) - position.commission_paid

       logger.debug(
           "unrealized_pnl_calculated",
           position_id=position.id,
           side=position.side,
           entry_price=position.entry_price,
           current_price=current_price,
           quantity=position.quantity,
           commission=position.commission_paid,
           unrealized=unrealized
       )

       return unrealized

   @staticmethod
   def calculate_return_pct(
       position: Position,
       current_price: float
   ) -> float:
       """Calculate return % for position."""
       if position.entry_price <= 0 or position.quantity <= 0:
           return 0.0

       # Investment = entry_price * quantity
       investment = position.entry_price * position.quantity

       # Unrealized P&L
       unrealized = PositionTracker.calculate_unrealized_pnl(position, current_price)

       # Return % = (unrealized / investment) * 100
       return_pct = (unrealized / investment) * 100

       logger.debug(
           "return_pct_calculated",
           position_id=position.id,
           unrealized=unrealized,
           investment=investment,
           return_pct=return_pct
       )

       return return_pct
   ```

   **Test Cases (MANDATORY - must pass):**

   ```python
   # Test 1: Simple long position
   position = Position(
       id="1", symbol="BTCUSDT", side="BUY",
       entry_price=45000.0, quantity=0.5,
       commission_paid=5.0
   )
   unrealized = calculate_unrealized_pnl(position, 46000.0)
   assert abs(unrealized - 495.0) < 0.01, f"Expected 495, got {unrealized}"
   return_pct = calculate_return_pct(position, 46000.0)
   assert abs(return_pct - 2.20) < 0.01, f"Expected 2.20%, got {return_pct}%"

   # Test 2: Short position
   position = Position(
       id="2", symbol="ETHUSDT", side="SELL",
       entry_price=2500.0, quantity=1.0,
       commission_paid=2.5
   )
   unrealized = calculate_unrealized_pnl(position, 2400.0)
   assert abs(unrealized - 97.5) < 0.01, f"Expected 97.5, got {unrealized}"

   # Test 3: Losing position
   position = Position(
       id="3", symbol="BTCUSDT", side="BUY",
       entry_price=45000.0, quantity=0.5,
       commission_paid=5.0
   )
   unrealized = calculate_unrealized_pnl(position, 44000.0)
   assert abs(unrealized - (-505.0)) < 0.01, f"Expected -505, got {unrealized}"

   # Test 4: High commission impact
   position = Position(
       id="4", symbol="BTCUSDT", side="BUY",
       entry_price=45000.0, quantity=0.01,
       commission_paid=50.0  # High commission on tiny position
   )
   unrealized = calculate_unrealized_pnl(position, 46000.0)
   # Should be: (46000-45000)*0.01 - 50 = 100 - 50 = 50
   assert abs(unrealized - 50.0) < 0.01, f"Expected 50, got {unrealized}"

   # Test 5: Edge case - zero quantity
   position = Position(
       id="5", symbol="BTCUSDT", side="BUY",
       entry_price=45000.0, quantity=0.0,
       commission_paid=0.0
   )
   unrealized = calculate_unrealized_pnl(position, 46000.0)
   assert unrealized == 0.0, f"Expected 0 for zero qty, got {unrealized}"

   # Test 6: NaN handling
   position = Position(
       id="6", symbol="BTCUSDT", side="BUY",
       entry_price=45000.0, quantity=0.5,
       commission_paid=5.0
   )
   unrealized = calculate_unrealized_pnl(position, float('nan'))
   assert math.isnan(unrealized), "Expected NaN, got finite value"
   ```

   **Common Pitfalls to Avoid:**
   - ❌ Forgetting commission in unrealized P&L (makes results wrong)
   - ❌ Using wrong formula for SHORT positions (same formula as LONG)
   - ❌ Not validating NaN/Infinity inputs (crashes on invalid data)
   - ❌ Division by zero in return % (check entry_price > 0)
   - ❌ Using quantity in denominator instead of investment (wrong units)
   - ✅ Always include commission in P&L calculations
   - ✅ Use different formulas for LONG vs SHORT
   - ✅ Validate inputs before using them
   - ✅ Return 0 or NaN for invalid cases, don't raise
   - ✅ Test with actual numbers from the test cases

   - Unit test: Unrealized P&L for long position (test 1 above)
   - Unit test: Unrealized P&L for short position (test 2 above)
   - Unit test: Return % calculation (test 1 above)
   - Unit test: Losing position P&L (test 3 above)
   - Unit test: Commission impact (test 4 above)
   - Unit test: Edge cases (test 5-6 above)
   - Manual verification: Run all 6 test cases, verify exact values

**Acceptance Criteria:**
- [ ] Unrealized P&L correct for long/short positions (verified with test cases)
- [ ] Realized P&L includes commission (formula correct)
- [ ] Return % calculation correct (verified with test cases)
- [ ] All numeric inputs validated (NaN/Infinity checks)
- [ ] Commission impact verified (test cases show commission reducing profit)
- [ ] All 6 unit tests pass with exact value matching (±0.01 tolerance)
- [ ] Manual calculations match code calculations
- [ ] Edge cases handled gracefully (return 0 or NaN, never crash)

---

5. **Task 4.3.5 - Implement Position Sync**
   - Add to: `src/core/execution/position_tracker.py`
   - Method: `async sync_positions() -> PositionSyncResult`
   - **Purpose:** Reconcile local position state with exchange balance state
   - **Approach (Binance Spot):**
     - Binance spot trading doesn't have "positions" like futures
     - Instead, track via balance changes
     - For each symbol with open position:
       1. Get balance from exchange: `balance = execution_engine.get_balance(symbol)`
       2. Compare with local position quantity
       3. If mismatch, log discrepancy and update local
   - **Workflow:**
     1. Get all open positions from local cache
     2. For each position:
        - Get exchange balance for position symbol
        - Expected balance = position.quantity
        - Actual balance = exchange balance
        - If actual != expected:
          - Discrepancy = actual - expected
          - Log: `logger.warning("position_discrepancy", symbol=symbol, expected=expected, actual=actual)`
          - Update position.quantity = actual
     3. Return PositionSyncResult:
        ```python
        @dataclass
        class PositionSyncResult:
            total_positions: int
            synced_positions: int  # No discrepancy
            corrected_positions: int  # Had discrepancy, corrected
            discrepancies: List[Dict]  # Details of each discrepancy
        ```
   - **Error Handling:**
     - Exchange API error → Log error, skip this position, continue
     - Database error → Log critical, raise after syncing all
   - **Triggered By:**
     - Startup: Called on PositionTracker initialization
     - Periodic: Scheduled task every 5 minutes
     - Manual: Called by reconciliation process
   - Unit test: Position sync with matching balances
   - Unit test: Position sync with discrepancies
   - Integration test: Sync on real testnet account

**Acceptance Criteria:**
- [ ] Detects balance mismatches
- [ ] Updates local position quantity
- [ ] Logs discrepancies for audit
- [ ] Integration test: sync with testnet

---

6. **Task 4.3.5a - Implement Position Staleness Monitor (PRD Feature K)**
   - Add to: `src/core/execution/position_tracker.py`
   - Class: `PositionStalenessMonitor`
   - **Purpose:** Per PRD Feature K - Monitor and act on positions held too long
   - **Thresholds by Strategy Type:**
     ```python
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
         },
         'position_trading': {
             'warning_days': 30,
             'force_review_days': 60,
             'max_hold_days': 90
         }
     }
     ```
   - **Profitable Position Extension:**
     - If position.unrealized_pnl > 0: Extend all thresholds by 1.5x (50% longer)
     - Rationale: Let winners run, be stricter on losers
   - **Core Method: `async check_staleness(position: Position) -> StalenessResult`**
     1. Get strategy type from database: `strategy = data_store.get_strategy(position.strategy_id)`
     2. Get thresholds for strategy type
     3. Calculate hold_duration = now - position.opened_at
     4. Get unrealized_pnl and apply extension if profitable
     5. Return StalenessResult:
        ```python
        @dataclass
        class StalenessResult:
            position_id: str
            hold_duration: timedelta
            should_warn: bool  # Exceeded warning threshold
            should_review: bool  # Exceeded force_review threshold
            should_close: bool  # Exceeded max_hold threshold
            days_remaining: float  # Days until max_hold
            status: str  # "OK", "WARNING", "REVIEW_REQUIRED", "MAX_HOLD_EXCEEDED"
        ```
   - **Core Method: `async process_stale_positions()`**
     1. Get all open positions from position_tracker
     2. For each position:
        - Skip if position has operator override (marked "intentionally long-term")
        - Call check_staleness(position)
        - If should_close:
          - If auto_close_enabled: Close position immediately via market order
          - Else: Send max_hold_exceeded alert to operator
        - Elif should_review:
          - Add to review_queue
          - Send review_required alert
        - Elif should_warn:
          - Send warning alert: "Position held for {days}, approaching review threshold"
     3. Log all actions
   - **Alert Manager Integration:**
     - Send alerts via Telegram (implementation in Phase 5)
     - Include position details: symbol, entry_price, current_price, unrealized_pnl, hold_duration
   - **Configuration:**
     - `AUTO_CLOSE_ENABLED: bool` (config.yaml) - Whether to auto-close max_hold positions
     - `SEND_ALERTS: bool` - Whether to send alerts (always true in production)
   - **Scheduled Task:** Runs every hour
   - **Operator Override:**
     - Method: `async override_position(position_id: str, reason: str) -> bool`
     - Stores in database: PositionOverride table
     - Exempts position from staleness checks indefinitely
   - Unit test: Staleness calculation for different strategy types
   - Unit test: Profitable position extension (1.5x threshold)
   - Unit test: Warning/review/close alerts triggered
   - Unit test: Operator override working
   - Unit test: Auto-close functionality (if enabled)

**Acceptance Criteria:**
- [ ] Day trading thresholds: warn 24h, review 48h, max 72h
- [ ] Swing trading thresholds: warn 7d, review 14d, max 30d
- [ ] Profitable positions get 50% extended threshold
- [ ] Warning alerts sent at warning threshold
- [ ] Review alerts sent at force_review threshold
- [ ] Auto-close at max_hold (if enabled in config)
- [ ] Operator can override with reason
- [ ] Unit test: all staleness scenarios
- [ ] Unit test: profitable extension calculation
- [ ] Scheduled task runs every hour

---

### **Stage 3: Position API & Tests (4-5 hours)**
**Tasks:** 4.3.6, 4.3.7
**Deliverable:** API endpoints for position data and comprehensive test coverage

7. **Task 4.3.6 - Create Position API Endpoints**
   - File: `src/api/routes/positions.py`
   - Create FastAPI router with position management endpoints
   - **Endpoints:**
     - `GET /api/positions` - List all open positions
       - Response: `List[Position]` with P&L, unrealized P&L, return %
       - Query params: Optional `symbol` filter, `status` filter (OPEN/CLOSED)
     - `GET /api/positions/{symbol}` - Get position for symbol
       - Response: Single Position with full details
       - 404 if not found
     - `DELETE /api/positions/{symbol}` - Close position immediately (market order)
       - Response: `{success: bool, message: str, order_id: str}`
       - Calls OrderManager to submit close order
     - `GET /api/positions/analysis/staleness` - Check staleness for all positions
       - Response: List of positions with staleness status and time remaining
   - **Response Format:**
     ```python
     {
       "symbol": "BTCUSDT",
       "side": "BUY",
       "quantity": 0.5,
       "entry_price": 45000.0,
       "current_price": 46000.0,
       "unrealized_pnl": 500.0,
       "return_pct": 2.22,
       "opened_at": "2026-02-13T10:30:00Z",
       "realized_pnl": 0.0
     }
     ```
   - **Error Responses:**
     - 404: Position not found
     - 400: Invalid symbol
     - 422: Cannot close position (no market)
     - 500: Server error
   - **Authorization:** All endpoints protected (implementation in Phase 5)
   - Unit test: All endpoints
   - Integration test: Full position lifecycle via API

**Acceptance Criteria:**
- [ ] GET endpoint lists positions with P&L
- [ ] GET single position works
- [ ] DELETE endpoint closes position
- [ ] Proper HTTP status codes
- [ ] Staleness analysis endpoint
- [ ] Integration test: full API lifecycle

---

8. **Task 4.3.7 - Write Position Tracker Tests**
   - Files:
     - `tests/unit/test_position_tracker.py`
     - `tests/integration/test_position_tracker_integration.py`
   - **Unit Tests (use mock market data):**
     - Open long position
     - Open short position
     - Add to position (average entry calculation)
     - Partial close (half position)
     - Full close (entire position)
     - Unrealized P&L calculation (long/short)
     - Realized P&L calculation
     - Return % calculation
     - Position sync (balance mismatch detection)
     - Staleness check (warning, review, max_hold)
     - Profitable position extension (1.5x)
     - Operator override
     - API endpoints (all CRUD operations)
   - **Integration Tests (use real prices):**
     - Open position, check current price, verify unrealized P&L
     - Close position, verify final P&L
     - Multiple positions, verify total portfolio P&L
     - Position sync on real account
   - **Test Data:**
     - Fixtures for positions at different entry prices
     - Fixtures for different strategy types (day_trading, swing_trading)
     - Fixtures for market prices (for unrealized P&L calculation)
   - **Manual Verification (for P&L calculations):**
     - Use known values:
       - Entry: 45000 @ 0.5 BTC = 22,500 USDT investment
       - Current: 46000
       - Unrealized: (46000 - 45000) * 0.5 = 500 USDT
       - Return %: (500 / 22500) * 100 = 2.22%
   - **Coverage Target:** >90% (unit), >85% (integration)

**Acceptance Criteria:**
- [ ] All position lifecycle scenarios tested
- [ ] P&L verified with manual calculations
- [ ] Staleness logic tested
- [ ] API endpoints tested
- [ ] >90% code coverage (unit)
- [ ] All tests passing

---

### **Stage 4: Execution Quality Tracking (10-12 hours)**
**Tasks:** 4.4.1 through 4.4.5
**Deliverable:** Complete execution quality monitoring (slippage, fill rates, reports)

9. **Task 4.4.1 - Create Slippage Tracker**
   - File: `src/core/execution/quality.py`
   - Class: `SlippageTracker`
   - **Purpose:** Track execution slippage on all fills
   - **Slippage Definition:**
     ```
     For BUY order:
       slippage_pct = ((actual_fill_price - expected_price) / expected_price) * 100
       (positive slippage = worse fill, negative = better fill)

     For SELL order:
       slippage_pct = ((expected_price - actual_fill_price) / expected_price) * 100
       (positive slippage = worse fill, negative = better fill)
     ```
   - **SlippageRecord dataclass:**
     ```python
     @dataclass
     class SlippageRecord:
         order_id: str
         symbol: str
         side: str  # BUY/SELL
         expected_price: float  # Entry signal price or average price
         actual_price: float    # Actual fill price
         slippage_pct: float    # Percentage slippage
         slippage_bps: float    # Basis points (slippage_pct * 100)
         recorded_at: datetime
     ```
   - **Core Methods:**
     - `record(order_id: str, symbol: str, side: str, expected_price: float, actual_price: float) -> SlippageRecord`
     - `get_average_slippage(symbol: str = None) -> float` (average % slippage, overall or by symbol)
     - `get_slippage_stats() -> SlippageStats`:
       ```python
       @dataclass
       class SlippageStats:
           total_orders: int
           average_slippage_pct: float
           average_slippage_bps: float
           best_slippage: float
           worst_slippage: float
           slippage_by_symbol: Dict[str, float]  # Symbol → avg slippage
           slippage_by_side: Dict[str, float]    # BUY/SELL → avg slippage
       ```
   - **Storage:** Store records in database for historical analysis
   - **Error Handling:**
     - NaN/Infinity in prices: Log warning, skip recording
     - Invalid symbol: Log error, skip
   - Unit test: Slippage calculation (positive, negative, zero)
   - Unit test: Statistics calculation
   - Unit test: By-symbol breakdown

**Acceptance Criteria:**
- [ ] Records all fills with slippage
- [ ] Calculates statistics correctly
- [ ] Per-symbol breakdown available
- [ ] Unit test: slippage calculations

---

10. **Task 4.4.1a - Implement Pre-Trade Slippage Estimation (PRD Feature F)**
    - Add to: `src/core/execution/quality.py`
    - Class: `SlippageEstimator`
    - **Purpose:** Per PRD Feature F - Estimate slippage BEFORE placing order
    - **Estimation Model:**
      ```
      Components:
      - base_slippage = 0.05% (minimum for market orders)
      - size_factor = (order_size / avg_daily_volume) * 0.5%
      - volatility_factor = (current_ATR / avg_ATR) * 0.1%
      - spread_factor = current_spread / 2

      Total estimated slippage = base + size + volatility + spread
      ```
    - **Configuration Constants:**
      ```python
      BASE_SLIPPAGE_PCT = 0.05
      SIZE_FACTOR_MULTIPLIER = 0.5
      VOLATILITY_FACTOR_MULTIPLIER = 0.1

      WARN_THRESHOLD_PCT = 0.3    # Warn if estimated slippage > 0.3%
      BLOCK_THRESHOLD_PCT = 1.0   # Block if estimated slippage > 1.0%
      ```
    - **Core Method: `async estimate_slippage(symbol: str, order_size: float, side: str) -> SlippageEstimate`**
      1. Get base slippage: 0.05%
      2. Get average daily volume from market data
      3. Calculate size factor: (order_size / avg_volume) * 0.5%
         - Validates that size factor doesn't go negative/NaN
      4. Get current ATR (14-period) and average ATR from market data
      5. Calculate volatility factor: (current_ATR / avg_ATR) * 0.1%
         - Handle division by zero (avg_ATR could be 0)
      6. Get current bid-ask spread (if available)
      7. Calculate spread factor: spread / 2
      8. Sum all components: total = base + size + volatility + spread
      9. Determine action:
         - If total > BLOCK_THRESHOLD (1.0%): should_block=True, action="BLOCK - Slippage too high"
         - Else if total > WARN_THRESHOLD (0.3%): should_warn=True, action="WARN - Consider smaller size"
         - Else: action="OK"
      10. Return SlippageEstimate:
          ```python
          @dataclass
          class SlippageEstimate:
              estimated_slippage_pct: float
              components: Dict[str, float]  # {base, size, volatility, spread}
              should_warn: bool
              should_block: bool
              recommended_action: str
              recommendation: str  # "PROCEED", "REDUCE_SIZE", "CANCEL"
          ```
    - **Integration into Order Submission:**
      - Called in OrderManager.submit_order() BEFORE risk controller check
      - If should_block: Block order, send alert
      - If should_warn: Log warning, allow order but alert operator
      - If OK: Proceed normally
    - **Post-Trade Comparison: `async compare_estimate_vs_actual(order_id: str) -> ComparisonResult`**
      - Called after order fills
      - Compare estimated slippage to actual slippage (from SlippageTracker)
      - Calculate estimation error: actual - estimated
      - Store for model recalibration
      ```python
      @dataclass
      class ComparisonResult:
          estimated: float
          actual: float
          error: float
          error_direction: str  # "OVERESTIMATED", "UNDERESTIMATED", "ACCURATE"
      ```
    - **Weekly Recalibration: `async recalibrate_model()`**
      - Run weekly (e.g., Sunday 00:00 UTC)
      - Analyze recent estimation errors
      - If systematic overestimation: Reduce multipliers slightly
      - If systematic underestimation: Increase multipliers slightly
      - Store adjustment factors for next week
      - Log: `logger.info("slippage_recalibration", old_multiplier=old, new_multiplier=new, reason=reason)`
    - **Error Handling:**
      - Missing market data (avg_volume, ATR): Use fallback values (1% for size_factor if volume unknown)
      - NaN/Infinity in calculations: Clamp to max reasonable value (e.g., 5% max estimated slippage)
    - Unit test: Estimation calculation with known inputs
    - Unit test: Warn threshold (>0.3%)
    - Unit test: Block threshold (>1.0%)
    - Unit test: Component breakdown
    - Unit test: Post-trade comparison
    - Unit test: Recalibration logic

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

11. **Task 4.4.2 - Create Fill Rate Tracker**
    - Add to: `src/core/execution/quality.py`
    - Class: `FillRateTracker`
    - **Purpose:** Track execution quality metrics (time to fill, fill rates, rejections)
    - **Core Metrics:**
      - Total orders (filled, cancelled, rejected)
      - Fill rate: filled_orders / total_orders
      - Time to fill: average time from submission to fill
      - Partial fills: Orders with partial fills
      - Cancellation rate: cancelled_orders / total_orders
      - Rejection rate: rejected_orders / total_orders
    - **FillRateStats dataclass:**
      ```python
      @dataclass
      class FillRateStats:
          total_orders: int
          filled_orders: int
          cancelled_orders: int
          rejected_orders: int
          partial_fills: int

          fill_rate_pct: float  # filled / total * 100
          cancellation_rate_pct: float  # cancelled / total * 100
          rejection_rate_pct: float  # rejected / total * 100

          average_fill_time_seconds: float
          min_fill_time_seconds: float
          max_fill_time_seconds: float

          stats_by_order_type: Dict[str, FillRateStats]  # MARKET, LIMIT, STOP_LOSS, etc.
          stats_by_symbol: Dict[str, FillRateStats]
      ```
    - **Core Methods:**
      - `track_order_fill(order: Order) -> None` - Called when order fills
      - `track_order_cancellation(order: Order) -> None` - Called when order cancelled
      - `track_order_rejection(order: Order) -> None` - Called when order rejected
      - `get_stats() -> FillRateStats` - Get all statistics
      - `get_stats_by_type(order_type: str) -> FillRateStats` - Stats for specific order type
      - `get_stats_by_symbol(symbol: str) -> FillRateStats` - Stats for specific symbol
    - **Breakdowns:**
      - By order type: MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT, BRACKET
      - By symbol: BTCUSDT, ETHUSDT, etc.
    - **Storage:** Store metrics in database for historical analysis
    - Unit test: Fill rate calculation
    - Unit test: Cancellation and rejection rates
    - Unit test: By-type and by-symbol breakdowns

**Acceptance Criteria:**
- [ ] Time to fill tracked
- [ ] Fill rate statistics calculated
- [ ] By order type breakdown
- [ ] By symbol breakdown
- [ ] Unit test: fill rate calcs

---

12. **Task 4.4.3 - Create Execution Report Generator**
    - Add to: `src/core/execution/quality.py`
    - Class: `ExecutionReportGenerator`
    - **Purpose:** Generate comprehensive execution quality reports
    - **Core Method: `generate_report(start_date: datetime, end_date: datetime) -> ExecutionReport`**
      - Aggregates data from SlippageTracker and FillRateTracker
      - Returns ExecutionReport:
        ```python
        @dataclass
        class ExecutionReport:
            period_start: datetime
            period_end: datetime

            # Order metrics
            total_orders: int
            filled_orders: int
            cancelled_orders: int
            rejected_orders: int
            fill_rate_pct: float

            # Slippage metrics
            average_slippage_pct: float
            average_slippage_bps: float
            best_slippage_pct: float
            worst_slippage_pct: float

            # Timing metrics
            average_fill_time_seconds: float
            min_fill_time_seconds: float
            max_fill_time_seconds: float

            # Breakdown by order type
            orders_by_type: Dict[str, int]
            slippage_by_type: Dict[str, float]
            fill_rate_by_type: Dict[str, float]

            # Breakdown by symbol
            slippage_by_symbol: Dict[str, float]
            fill_rate_by_symbol: Dict[str, float]

            # Recommendations
            symbols_with_high_slippage: List[str]  # >0.5%
            symbols_with_low_fill_rate: List[str]  # <95%
            recommendations: List[str]
        ```
    - **Report Generation Steps:**
      1. Query all orders from database in date range
      2. Filter for FILLED, CANCELLED, REJECTED statuses
      3. Get slippage data from SlippageTracker
      4. Get fill rate data from FillRateTracker
      5. Aggregate by type and symbol
      6. Identify problematic symbols (high slippage, low fill rates)
      7. Generate recommendations
      8. Return complete ExecutionReport
    - **Export Formats:**
      - JSON: For API responses
      - CSV: For spreadsheet analysis (future: Phase 5)
      - PDF: For reporting (future: Phase 5)
    - Unit test: Report generation with sample data
    - Unit test: Recommendations logic

**Acceptance Criteria:**
- [ ] Comprehensive report aggregates order and slippage data
- [ ] Date range filtering works
- [ ] Breakdowns by type and symbol
- [ ] Recommendations generated
- [ ] Unit test: report generation

---

13. **Task 4.4.4 - Create Execution Quality API**
    - File: `src/api/routes/execution.py`
    - Create FastAPI router with execution quality endpoints
    - **Endpoints:**
      - `GET /api/execution/stats` - Current execution statistics
        - Response: FillRateStats (current session or last 24 hours)
      - `GET /api/execution/slippage` - Slippage analysis
        - Query params: `symbol` (optional), `period_days` (optional, default 7)
        - Response: SlippageStats with by-symbol breakdown
      - `GET /api/execution/report` - Full execution report
        - Query params: `start_date`, `end_date` (ISO format)
        - Response: ExecutionReport (detailed metrics and recommendations)
    - **Response Examples:**
      - `GET /api/execution/stats`:
        ```json
        {
          "total_orders": 150,
          "filled_orders": 148,
          "fill_rate_pct": 98.67,
          "average_fill_time_seconds": 5.3,
          "average_slippage_bps": 15.2
        }
        ```
      - `GET /api/execution/report?start_date=2026-02-01&end_date=2026-02-13`:
        ```json
        {
          "period_start": "2026-02-01",
          "period_end": "2026-02-13",
          "total_orders": 500,
          "fill_rate_pct": 97.5,
          "average_slippage_pct": 0.152,
          "symbols_with_high_slippage": ["BNBUSDT", "ADAUSDT"],
          "recommendations": [
            "BNBUSDT has high slippage (0.5%), consider reducing order size",
            "Overall fill rate is excellent (97.5%)"
          ]
        }
        ```
    - **Error Responses:**
      - 400: Invalid date range
      - 422: Invalid query parameters
      - 500: Server error
    - **Authorization:** All endpoints protected (implementation in Phase 5)
    - Unit test: All endpoints
    - Integration test: API calls with real data

**Acceptance Criteria:**
- [ ] Stats endpoint works
- [ ] Report generation works
- [ ] Slippage breakdown available
- [ ] Proper error responses
- [ ] Integration test: API calls

---

14. **Task 4.4.5 - Write Execution Quality Tests**
    - Files:
      - `tests/unit/test_execution_quality.py`
      - `tests/integration/test_execution_quality_integration.py`
    - **Unit Tests:**
      - Slippage calculation (positive, negative, zero)
      - Slippage estimation (all components)
      - Estimation accuracy comparison
      - Fill rate statistics
      - Fill rate breakdowns (by type, symbol)
      - Report generation
      - API responses
    - **Integration Tests (if possible):**
      - Generate report with real historical data
      - Verify calculations match manual calculations
      - Check API endpoint responses
    - **Test Data:**
      - Known fills with known slippage values
      - Multiple order types for breakdown testing
      - Multiple symbols for symbol breakdown testing
    - **Coverage Target:** >85%

**Acceptance Criteria:**
- [ ] All metrics tested
- [ ] Edge cases covered
- [ ] >85% code coverage
- [ ] All tests passing

---

## PRODUCTION QUALITY GATES

### **Automated Gates**
Before submission, ALL must pass with 0 errors:

```bash
# 1. Type Safety (MANDATORY: 100% coverage)
mypy src/core/execution/ --strict
# Result: "Success: no issues found"

# 2. Code Linting
ruff check src/core/execution/
# Result: No violations

# 3. Import Organization
isort src/core/execution/ --check --diff
# Result: "All done! No files would be modified"

# 4. Unit Tests (MANDATORY: all pass)
pytest tests/unit/test_position_tracker.py tests/unit/test_execution_quality.py -v
# Result: All tests passing

# 5. Integration Tests
pytest tests/integration/test_position_tracker_integration.py -v
# Result: All tests passing

# 6. Coverage Report
pytest tests/unit/ tests/integration/ \
  --cov=src/core/execution \
  --cov-report=term-missing | grep -E "^(src/|TOTAL)"
# Result: All files >90%, TOTAL >90%

# 7. Production Audit
@production-code-audit audit src/core/execution/
# Result: Grade A- or higher
```

---

## CODE QUALITY STANDARDS

### **Type Hints (100% Required)**
```python
# CORRECT - Full type hints
async def calculate_unrealized_pnl(
    self,
    symbol: str,
    current_price: float
) -> float:
    """Calculate unrealized P&L for position.

    Args:
        symbol: Trading symbol
        current_price: Current market price

    Returns:
        Unrealized P&L in quote asset
    """

# INCORRECT - Missing return type
async def calculate_unrealized_pnl(self, symbol: str, current_price: float):
    pass
```

### **Financial Calculation Validation**
```python
# CORRECT - Validate all inputs
def calculate_unrealized_pnl(self, entry_price: float, current_price: float, quantity: float) -> float:
    if math.isnan(entry_price) or math.isnan(current_price) or math.isnan(quantity):
        raise ValueError("Prices and quantity cannot be NaN")
    if math.isinf(entry_price) or math.isinf(current_price) or math.isinf(quantity):
        raise ValueError("Prices and quantity cannot be Infinity")

    return (current_price - entry_price) * quantity

# INCORRECT - No validation
def calculate_unrealized_pnl(self, entry_price, current_price, quantity):
    return (current_price - entry_price) * quantity
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

**Session 4B is complete when:**

✅ **Section 4.3 (Position Tracker):**
- [ ] All 8 tasks completed
- [ ] Positions open/close correctly
- [ ] P&L calculations accurate (verified with manual calculations)
- [ ] Position staleness monitoring working
- [ ] Position sync detecting discrepancies
- [ ] API endpoints for position management
- [ ] All tests passing (>90% coverage)

✅ **Section 4.4 (Execution Quality):**
- [ ] All 6 tasks completed
- [ ] Slippage tracked for all fills
- [ ] Pre-trade slippage estimation working (warn at 0.3%, block at 1.0%)
- [ ] Fill rate statistics calculated
- [ ] Execution reports generated
- [ ] API endpoints for execution metrics
- [ ] All tests passing (>85% coverage)

✅ **PRD Compliance:**
- [ ] Feature F: Pre-trade slippage estimation
- [ ] Feature K: Position staleness monitor

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
  ├── position_tracker.py        # PositionTracker + staleness (Tasks 4.3.1-4.3.5a)
  └── quality.py                 # Slippage + fill rate + reports (Tasks 4.4.1-4.4.4)

src/api/routes/
  ├── positions.py               # Position API endpoints (Task 4.3.6)
  └── execution.py               # Execution quality API (Task 4.4.4)

tests/unit/
  ├── test_position_tracker.py   # Position tracker tests (Task 4.3.7)
  └── test_execution_quality.py  # Execution quality tests (Task 4.4.5)

tests/integration/
  └── test_position_tracker_integration.py  # Integration tests (Task 4.3.7)
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
- pytest-asyncio (async test support)
- pytest-cov (coverage reporting)

---

## SIGN-OFF

**Session 4B is COMPLETE and PRODUCTION READY when:**

```
✅ Type Safety: mypy --strict passes
✅ Code Quality: ruff/isort pass
✅ Tests: All unit and integration tests pass
✅ Coverage: >90% overall, no file <90%
✅ Production Audit: Grade A- or higher
✅ Decision Consistency: All decisions verified

READY FOR: Phase 5 (Strategy Execution & Backtesting)
```

---

**Last Updated:** 2026-02-13
**Format:** Production Grade Implementation Prompt
**Applies To:** Phase 4 Session B (Sections 4.3 + 4.4)
