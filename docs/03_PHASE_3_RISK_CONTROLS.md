# PHASE 3: RISK CONTROLS
## Weeks 5-6 | 30 Tasks | ~85 Hours

**Goal:** Bulletproof risk management that protects capital at all costs.

**Start Conditions:** Phase 2 complete (market data and indicators working)  
**Exit Conditions:** Kill switch responds <1s, all limits enforced, circuit breakers tested

---

## 📊 PHASE 3 PROGRESS

```
Section 3.1 Risk Controller   [░░░░░░░░░░] 0/9 tasks
Section 3.2 Kill Switch       [░░░░░░░░░░] 0/7 tasks
Section 3.3 Circuit Breakers  [░░░░░░░░░░] 0/8 tasks
Section 3.4 Volatility Filter [░░░░░░░░░░] 0/6 tasks
───────────────────────────────────────────────────
PHASE 3 TOTAL                 [░░░░░░░░░░] 0/30 tasks
```

---

## SECTION 3.1: RISK CONTROLLER
*Estimated: 20 hours*

### Task 3.1.1: Create Risk Controller Core
- [ ] **Status:** Not Started
- **Description:** Central risk management component
- **Dependencies:** [1.2.12, 1.3.2, 2.3.2]
- **Effort:** 3 hours

**File:** `src/core/risk/controller.py`

**RiskController class:**
```python
class RiskController:
    def __init__(self, data_store, config, symbol_manager):
        self.data_store = data_store
        self.config = config
        self.symbol_manager = symbol_manager
        self.kill_switch = KillSwitch(data_store)
        self._cache = {}  # Runtime state cache
    
    async def check_order(self, order_request: OrderRequest) -> RiskCheckResult:
        """Main entry point - run all risk checks on an order."""
        pass
    
    async def calculate_position_size(self, ...) -> float:
        """Calculate risk-adjusted position size."""
        pass
```

**Acceptance Criteria:**
- [ ] Central coordination of all risk checks
- [ ] Integrates with kill switch
- [ ] Uses risk profiles from config
- [ ] Unit test: basic structure

---

### Task 3.1.2: Create Risk Check Data Types
- [ ] **Status:** Not Started
- **Description:** Data classes for risk check requests/results
- **Dependencies:** [3.1.1]
- **Effort:** 1 hour

**File:** `src/core/risk/types.py`

**Classes:**
```python
@dataclass
class OrderRequest:
    account_id: str
    strategy_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: float  # Expected price
    order_type: str
    reason: str

@dataclass
class RiskCheckResult:
    approved: bool
    order_request: OrderRequest
    adjusted_quantity: Optional[float] = None  # If position was sized down
    rejection_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)

@dataclass
class PortfolioState:
    total_equity: float
    cash_balance: float
    positions_value: float
    open_positions: List[Position]
    daily_pnl: float
    drawdown_pct: float
```

**Acceptance Criteria:**
- [ ] All necessary fields captured
- [ ] Immutable data classes
- [ ] Serializable for logging
- [ ] Unit test: data class creation

---

### Task 3.1.3: Implement Position Size Check
- [ ] **Status:** Not Started
- **Description:** Enforce maximum position size limits
- **Dependencies:** [3.1.1, 3.1.2]
- **Effort:** 2 hours

**Add to:** `src/core/risk/controller.py`

**Check:** `_check_position_size(order_request, portfolio_state) -> (bool, str)`

**Rules (from PRD 3.4.1):**
- Max position size: `max_position_size_pct` of portfolio (default 10%)
- Based on risk profile (conservative=2%, balanced=3%, aggressive=5%)
- Calculate: `position_value = quantity * price`
- Compare: `position_value / total_equity * 100 <= max_position_size_pct`

**Acceptance Criteria:**
- [ ] Rejects orders exceeding max size
- [ ] Returns appropriate error message
- [ ] Respects risk profile settings
- [ ] Unit test: various position sizes

---

### Task 3.1.4: Implement Concentration Check
- [ ] **Status:** Not Started
- **Description:** Prevent over-concentration in single asset
- **Dependencies:** [3.1.1, 3.1.2]
- **Effort:** 1.5 hours

**Add to:** `src/core/risk/controller.py`

**Check:** `_check_concentration(order_request, portfolio_state) -> (bool, str)`

**Rules:**
- Max concentration: `max_concentration_pct` (default 30%)
- Calculate existing + new position value for symbol
- Reject if combined > max_concentration_pct

**Acceptance Criteria:**
- [ ] Considers existing positions
- [ ] Prevents over-concentration
- [ ] Returns remaining capacity
- [ ] Unit test: concentration scenarios

---

### Task 3.1.5: Implement Max Positions Check
- [ ] **Status:** Not Started
- **Description:** Limit number of concurrent positions
- **Dependencies:** [3.1.1, 3.1.2]
- **Effort:** 1 hour

**Add to:** `src/core/risk/controller.py`

**Check:** `_check_max_positions(order_request, portfolio_state) -> (bool, str)`

**Rules:**
- Max open positions: `max_open_positions` (default 10)
- Count only open positions (not pending orders)
- Exception: allow closing existing positions

**Acceptance Criteria:**
- [ ] Counts open positions correctly
- [ ] Allows closing positions
- [ ] Respects profile limits
- [ ] Unit test: position count scenarios

---

### Task 3.1.6: Implement Position Size Calculator
- [ ] **Status:** Not Started
- **Description:** Calculate optimal position size based on risk
- **Dependencies:** [3.1.1, 2.2.4]  # Needs ATR
- **Effort:** 2.5 hours

**Add to:** `src/core/risk/controller.py`

**Method:** `calculate_position_size(account_id, symbol, side, entry_price, stop_loss_price) -> PositionSizeResult`

**Sizing methods:**
1. **Fixed Risk %:** Risk fixed % of equity per trade (e.g., 1%)
   - `size = (equity * risk_pct) / (entry_price - stop_loss_price)`

2. **ATR-based:** Size based on volatility
   - `size = (equity * risk_pct) / (atr * atr_multiplier)`

3. **Kelly Criterion (simplified):** 
   - `kelly_pct = (win_rate * avg_win - (1-win_rate) * avg_loss) / avg_win`
   - Use fractional Kelly (0.25-0.5)

**Result:**
```python
@dataclass
class PositionSizeResult:
    quantity: float
    notional_value: float
    risk_amount: float  # $ at risk
    risk_pct: float
    sizing_method: str
    stop_loss_price: float
```

**Acceptance Criteria:**
- [ ] Fixed risk sizing works
- [ ] ATR-based sizing works
- [ ] Respects max position limits
- [ ] Unit test: sizing calculations

---

### Task 3.1.6a: Implement Capital Allocation Rules
- [ ] **Status:** Not Started
- **Description:** Systematic capital allocation per PRD Feature G
- **Dependencies:** [3.1.6]
- **Effort:** 2.5 hours

**Add to:** `src/core/risk/controller.py`

**CapitalAllocator class:**
```python
class CapitalAllocator:
    """
    Capital allocation rules per PRD Feature G.
    
    Portfolio reserves:
    - Minimum cash reserve: 20%
    - Emergency buffer: 10%
    
    Per-strategy limits:
    - New strategy max: 5%
    - Proven strategy max: 15%
    
    Graduation requirements:
    - 30 days profitable
    - 20+ trades
    - Increase allocation by 5% on graduation
    """
    
    MINIMUM_CASH_RESERVE_PCT = 20
    EMERGENCY_BUFFER_PCT = 10
    NEW_STRATEGY_MAX_PCT = 5
    PROVEN_STRATEGY_MAX_PCT = 15
    GRADUATION_DAYS = 30
    GRADUATION_MIN_TRADES = 20
    GRADUATION_INCREASE_PCT = 5
    
    def __init__(self, data_store):
        self.data_store = data_store
    
    def get_available_capital(self, portfolio: PortfolioState) -> float:
        """Capital available for new positions (excludes reserves)."""
        total = portfolio.total_equity
        reserved_pct = self.MINIMUM_CASH_RESERVE_PCT + self.EMERGENCY_BUFFER_PCT
        reserved = total * reserved_pct / 100
        return max(0, portfolio.cash_balance - reserved)
    
    def get_max_allocation(self, strategy: Strategy) -> float:
        """Max % of portfolio for this strategy."""
        if self._is_proven(strategy):
            return self.PROVEN_STRATEGY_MAX_PCT
        return self.NEW_STRATEGY_MAX_PCT
    
    def _is_proven(self, strategy: Strategy) -> bool:
        """Check if strategy qualifies as proven."""
        # Must be profitable for 30+ days
        # Must have 20+ completed trades
        pass
    
    def check_graduation(self, strategy: Strategy) -> Optional[float]:
        """Check if strategy can increase allocation."""
        if not self._is_proven(strategy):
            return None
        
        current_alloc = self._get_current_allocation(strategy)
        new_alloc = current_alloc + self.GRADUATION_INCREASE_PCT
        
        if new_alloc <= self.PROVEN_STRATEGY_MAX_PCT:
            return new_alloc
        return None
    
    def validate_allocation(
        self, 
        strategy: Strategy, 
        requested_pct: float,
        portfolio: PortfolioState
    ) -> Tuple[bool, str]:
        """Validate a requested allocation."""
        max_allowed = self.get_max_allocation(strategy)
        if requested_pct > max_allowed:
            return False, f"Max allocation is {max_allowed}%"
        
        available = self.get_available_capital(portfolio)
        requested_value = portfolio.total_equity * requested_pct / 100
        if requested_value > available:
            return False, f"Insufficient available capital"
        
        return True, "OK"
```

**Integration:** Call from RiskController before allowing new position

**Acceptance Criteria:**
- [ ] 20% cash reserve enforced
- [ ] 10% emergency buffer enforced
- [ ] New strategies limited to 5%
- [ ] Proven strategies limited to 15%
- [ ] Graduation detection works (30 days + 20 trades)
- [ ] Allocation increase by 5% on graduation
- [ ] Integration with risk checks
- [ ] Unit test: all allocation scenarios

---

### Task 3.1.7: Implement Order Validation Pipeline
- [ ] **Status:** Not Started
- **Description:** Run all checks in sequence
- **Dependencies:** [3.1.3, 3.1.4, 3.1.5]
- **Effort:** 2 hours

**Add to:** `src/core/risk/controller.py`

**Method:** `async check_order(order_request) -> RiskCheckResult`

**Pipeline order:**
1. Kill switch check (immediate rejection if active)
2. Circuit breaker checks (daily loss, drawdown)
3. Position size check
4. Concentration check
5. Max positions check
6. Leverage check
7. Symbol validation

**Logging:** Log each check result for audit trail

**Acceptance Criteria:**
- [ ] All checks run in order
- [ ] First failure short-circuits
- [ ] Results logged for audit
- [ ] Unit test: pipeline flow

---

### Task 3.1.8: Write Risk Controller Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive tests for risk controller
- **Dependencies:** [3.1.1-3.1.7]
- **Effort:** 3 hours

**File:** `tests/unit/test_risk_controller.py`

**Test scenarios:**
- Order within all limits (approved)
- Order exceeds position size (rejected)
- Order exceeds concentration (rejected)
- Order when at max positions (rejected)
- Order when kill switch active (rejected)
- Position sizing calculations
- Edge cases (zero equity, no positions)

**Acceptance Criteria:**
- [ ] All check types tested
- [ ] Rejection reasons verified
- [ ] Edge cases covered
- [ ] >90% coverage for risk module

---

## SECTION 3.2: KILL SWITCH
*Estimated: 12 hours*

### Task 3.2.1: Create Kill Switch Core
- [ ] **Status:** Not Started
- **Description:** Emergency stop mechanism
- **Dependencies:** [1.2.9, 1.2.12]  # SystemState model
- **Effort:** 2 hours

**File:** `src/core/risk/kill_switch.py`

**KillSwitch class:**
```python
class KillSwitch:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self._is_active = False
        self._activated_at = None
        self._reason = None
    
    async def activate(self, reason: str, close_positions: bool = True):
        """Activate kill switch - halt all trading."""
        pass
    
    async def deactivate(self, confirm_code: str):
        """Deactivate kill switch with confirmation."""
        pass
    
    def is_active(self) -> bool:
        """Check if kill switch is active."""
        pass
    
    async def load_state(self):
        """Load state from database on startup."""
        pass
```

**Acceptance Criteria:**
- [ ] Activates immediately (<1 second)
- [ ] Persists state to database
- [ ] Requires confirmation to deactivate
- [ ] Logs all state changes
- [ ] Unit test: activate/deactivate

---

### Task 3.2.2: Implement Kill Switch Triggers
- [ ] **Status:** Not Started
- **Description:** Automatic kill switch triggers
- **Dependencies:** [3.2.1]
- **Effort:** 2 hours

**Add to:** `src/core/risk/kill_switch.py`

**Auto-trigger conditions (from PRD):**
- Daily loss exceeds 5% (configurable)
- Drawdown exceeds 15% (configurable)
- Multiple consecutive losing trades (e.g., 10)
- Exchange connection lost for >5 minutes
- Critical error in execution

**Method:** `async check_triggers(portfolio_state) -> Optional[str]`

Returns trigger reason if any condition met, None otherwise.

**Acceptance Criteria:**
- [ ] All trigger conditions checked
- [ ] Triggers activation automatically
- [ ] Configurable thresholds
- [ ] Unit test: each trigger condition

---

### Task 3.2.3: Implement Position Closing on Kill Switch
- [ ] **Status:** Not Started
- **Description:** Close all positions when kill switch activates
- **Dependencies:** [3.2.1, 4.1.1]  # Needs execution (stub for now)
- **Effort:** 2 hours

**Add to:** `src/core/risk/kill_switch.py`

**Method:** `async _close_all_positions()`

**Behavior:**
- Get all open positions
- Submit market orders to close each
- Wait for fills (with timeout)
- Log results
- Cancel any pending orders first

**Note:** May need stub execution engine for testing.

**Acceptance Criteria:**
- [ ] Cancels pending orders
- [ ] Closes all positions
- [ ] Handles partial fills
- [ ] Timeout handling
- [ ] Integration test: close positions

---

### Task 3.2.4: Create Kill Switch API Endpoints
- [ ] **Status:** Not Started
- **Description:** API to control kill switch
- **Dependencies:** [3.2.1]
- **Effort:** 1.5 hours

**File:** `src/api/routes/risk.py`

**Endpoints:**
- `GET /api/risk/kill-switch/status` - Get current status
- `POST /api/risk/kill-switch/activate` - Activate with reason
- `POST /api/risk/kill-switch/deactivate` - Deactivate with confirmation

**Security:** Require confirmation code for deactivation to prevent accidents.

**Acceptance Criteria:**
- [ ] Status endpoint returns current state
- [ ] Activate requires reason
- [ ] Deactivate requires confirmation
- [ ] Audit log updated

---

### Task 3.2.5: Implement Kill Switch Recovery
- [ ] **Status:** Not Started
- **Description:** Recover kill switch state on system restart
- **Dependencies:** [3.2.1]
- **Effort:** 1 hour

**Add to:** `src/core/risk/kill_switch.py`

**Behavior on startup:**
- Load state from SystemState table
- If was active, remain active
- Notify via alert that system restarted with kill switch active

**Acceptance Criteria:**
- [ ] State persists across restarts
- [ ] Alert sent on restart
- [ ] Audit log on recovery
- [ ] Unit test: state recovery

---

### Task 3.2.6: Write Kill Switch Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive kill switch tests
- **Dependencies:** [3.2.1-3.2.5]
- **Effort:** 2 hours

**File:** `tests/unit/test_kill_switch.py`

**Test scenarios:**
- Manual activation
- Manual deactivation with correct code
- Deactivation with wrong code (rejected)
- Auto-trigger on daily loss
- Auto-trigger on drawdown
- State persistence
- Recovery on restart
- Position closing

**Acceptance Criteria:**
- [ ] All activation paths tested
- [ ] Deactivation security tested
- [ ] Auto-triggers tested
- [ ] >90% coverage

---

### Task 3.2.6a: Implement Dead Man's Switch
- [ ] **Status:** Not Started
- **Description:** Auto-close positions if system stops responding per PRD Feature C
- **Dependencies:** [3.2.1, 6.3.2]
- **Effort:** 3 hours

**File:** `src/core/risk/dead_mans_switch.py`

**DeadMansSwitch class:**
```python
from datetime import datetime, timedelta
from typing import Optional
import asyncio

class DeadMansSwitchTriggered(Exception):
    """Raised when dead man's switch triggers."""
    pass

class DeadMansSwitch:
    """
    Auto-close if system stops responding per PRD Feature C.
    
    DIFFERENT from Kill Switch:
    - Kill Switch: Manual or auto-trigger based on losses
    - Dead Man's Switch: Triggers if system itself becomes unresponsive
    
    Parameters:
    - Heartbeat interval: 5 minutes
    - Max missed heartbeats: 6 (30 minutes total)
    - Action: Close all positions
    - Resume: Requires manual restart
    """
    
    HEARTBEAT_INTERVAL_MINUTES = 5
    MAX_MISSED_HEARTBEATS = 6  # 30 minutes total
    WARNING_BEFORE_CLOSE_SECONDS = 60
    
    def __init__(self, data_store, alert_manager, execution_engine):
        self.data_store = data_store
        self.alert_manager = alert_manager
        self.execution_engine = execution_engine
        self._last_heartbeat = datetime.utcnow()
        self._missed_count = 0
        self._triggered = False
    
    async def record_heartbeat(self):
        """
        Called by orchestrator main loop every cycle.
        Records that system is still alive and responsive.
        """
        self._last_heartbeat = datetime.utcnow()
        self._missed_count = 0
        
        # Persist to database for external watchdog
        await self.data_store.update_system_state(
            'dead_mans_switch_heartbeat',
            self._last_heartbeat.isoformat()
        )
    
    def check_heartbeat(self) -> bool:
        """
        Called by external watchdog process.
        Returns True if system is healthy, False if unresponsive.
        """
        elapsed = datetime.utcnow() - self._last_heartbeat
        max_elapsed = timedelta(minutes=self.HEARTBEAT_INTERVAL_MINUTES)
        
        if elapsed > max_elapsed:
            self._missed_count += 1
            return self._missed_count < self.MAX_MISSED_HEARTBEATS
        return True
    
    async def trigger(self, reason: str = "System unresponsive"):
        """
        Close all positions and require manual restart.
        
        Sequence:
        1. Send Telegram warning (1 minute before closing)
        2. Wait 1 minute
        3. Close all positions with market orders
        4. Mark as triggered
        5. Raise exception to stop system
        """
        if self._triggered:
            return
        
        # Send warning
        await self.alert_manager.send_critical(
            title="⚠️ DEAD MAN'S SWITCH - WARNING",
            message=f"System unresponsive for {self._missed_count * self.HEARTBEAT_INTERVAL_MINUTES} minutes. "
                    f"All positions will be closed in 60 seconds. "
                    f"Reason: {reason}"
        )
        
        # Wait before closing
        await asyncio.sleep(self.WARNING_BEFORE_CLOSE_SECONDS)
        
        # Close all positions
        await self._close_all_positions()
        
        # Send final alert
        await self.alert_manager.send_critical(
            title="🛑 DEAD MAN'S SWITCH TRIGGERED",
            message="All positions closed. Manual restart required."
        )
        
        self._triggered = True
        raise DeadMansSwitchTriggered(reason)
    
    async def _close_all_positions(self):
        """Close all open positions with market orders."""
        positions = await self.data_store.get_open_positions()
        
        for position in positions:
            try:
                await self.execution_engine.close_position(
                    position.symbol,
                    position.quantity,
                    reason="dead_mans_switch"
                )
            except Exception as e:
                await self.alert_manager.send_error(
                    title="Failed to close position",
                    message=f"Symbol: {position.symbol}, Error: {str(e)}"
                )
    
    @property
    def is_triggered(self) -> bool:
        return self._triggered
```

**External Watchdog:** A separate lightweight process that calls `check_heartbeat()` every 5 minutes. If `False` returned for `MAX_MISSED_HEARTBEATS` times, it calls `trigger()`.

**Acceptance Criteria:**
- [ ] Heartbeat recorded in orchestrator main loop
- [ ] Watchdog detects missed heartbeats
- [ ] Telegram warning sent 1 minute before close
- [ ] All positions closed with market orders
- [ ] Manual restart required after trigger
- [ ] State persisted to database
- [ ] Unit test: heartbeat recording
- [ ] Unit test: trigger sequence
- [ ] Integration test: full trigger flow

---

## SECTION 3.3: CIRCUIT BREAKERS
*Estimated: 16 hours*

### Task 3.3.1: Create Circuit Breaker Framework
- [ ] **Status:** Not Started
- **Description:** Base framework for circuit breakers
- **Dependencies:** [3.1.1]
- **Effort:** 1.5 hours

**File:** `src/core/risk/circuit_breakers.py`

**CircuitBreaker ABC:**
```python
class CircuitBreaker(ABC):
    name: str
    
    @abstractmethod
    async def check(self, state: PortfolioState) -> CircuitBreakerResult:
        pass
    
    @abstractmethod
    async def reset(self):
        pass

@dataclass
class CircuitBreakerResult:
    triggered: bool
    breaker_name: str
    reason: str
    current_value: float
    threshold: float
```

**CircuitBreakerManager:**
- Register/unregister breakers
- Check all breakers
- Track breaker states

**Acceptance Criteria:**
- [ ] Base class defined
- [ ] Manager coordinates breakers
- [ ] Results are detailed
- [ ] Unit test: framework

---

### Task 3.3.2: Implement Daily Loss Limit Breaker
- [ ] **Status:** Not Started
- **Description:** Circuit breaker for daily loss limit
- **Dependencies:** [3.3.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/risk/circuit_breakers.py`

**DailyLossBreaker:**
- Threshold: `daily_loss_limit_pct` (default 5%)
- Resets at UTC 00:00
- Tracks realized + unrealized P&L

**Acceptance Criteria:**
- [ ] Triggers at threshold
- [ ] Auto-resets daily
- [ ] Considers unrealized P&L
- [ ] Unit test: trigger scenarios

---

### Task 3.3.3: Implement Weekly Loss Limit Breaker
- [ ] **Status:** Not Started
- **Description:** Circuit breaker for weekly loss
- **Dependencies:** [3.3.1]
- **Effort:** 1 hour

**Add to:** `src/core/risk/circuit_breakers.py`

**WeeklyLossBreaker:**
- Threshold: `weekly_loss_limit_pct` (default 7-10%)
- Resets Monday UTC 00:00
- More conservative than daily

**Acceptance Criteria:**
- [ ] Triggers at threshold
- [ ] Resets weekly
- [ ] Unit test: trigger scenarios

---

### Task 3.3.4: Implement Drawdown Breaker
- [ ] **Status:** Not Started
- **Description:** Circuit breaker for maximum drawdown
- **Dependencies:** [3.3.1]
- **Effort:** 2 hours

**Add to:** `src/core/risk/circuit_breakers.py`

**DrawdownBreaker:**
- Threshold: `max_drawdown_pct` (default 15%)
- Tracks equity peak
- Calculates current drawdown from peak
- Does NOT auto-reset (requires manual intervention)

**Calculation:**
```python
drawdown_pct = (peak_equity - current_equity) / peak_equity * 100
```

**Acceptance Criteria:**
- [ ] Tracks equity peak correctly
- [ ] Calculates drawdown correctly
- [ ] Does not auto-reset
- [ ] Unit test: drawdown scenarios

---

### Task 3.3.5: Implement Consecutive Loss Breaker
- [ ] **Status:** Not Started
- **Description:** Circuit breaker for losing streaks
- **Dependencies:** [3.3.1]
- **Effort:** 1.5 hours

**Add to:** `src/core/risk/circuit_breakers.py`

**ConsecutiveLossBreaker:**
- Threshold: consecutive losing trades (default 5)
- Tracks win/loss sequence
- Resets on winning trade

**Acceptance Criteria:**
- [ ] Counts consecutive losses
- [ ] Triggers at threshold
- [ ] Resets on win
- [ ] Unit test: streak scenarios

---

### Task 3.3.6: Implement Correlation Breaker
- [ ] **Status:** Not Started
- **Description:** Limit exposure to correlated assets per PRD Feature A
- **Dependencies:** [3.3.1, 2.1.7]
- **Effort:** 2.5 hours

**Add to:** `src/core/risk/circuit_breakers.py`

**CorrelationBreaker:**
- Threshold: max correlation exposure (e.g., 3 highly correlated positions)
- Pre-defined correlation groups (BTC/ETH are correlated)
- Warns when adding correlated positions

**Correlation groups (MVP):**
- BTC group: BTCUSDT
- ETH group: ETHUSDT
- Alt Layer 1: SOLUSDT, AVAXUSDT, DOTUSDT
- Exchange tokens: BNBUSDT
- Payment: XRPUSDT, ADAUSDT, LTCUSDT
- Meme/other: DOGEUSDT

**PRD Feature A - Portfolio Correlation Limits:**
```python
CORRELATION_LIMITS = {
    'BTCUSDT': 0.40,         # Max 40% of portfolio in BTC
    'ETHUSDT': 0.30,         # Max 30% of portfolio in ETH
    'correlated_total': 0.60 # Max 60% in any correlated group
}

def check_correlation_limits(
    symbol: str, 
    position_value: float, 
    portfolio: PortfolioState
) -> Tuple[bool, str]:
    """
    Check correlation limits BEFORE allowing new entry.
    """
    # Check individual symbol limits
    if symbol == 'BTCUSDT':
        btc_exposure = get_symbol_exposure(symbol, portfolio)
        if btc_exposure + position_value > portfolio.total_equity * 0.40:
            return False, "Would exceed 40% BTC limit"
    
    if symbol == 'ETHUSDT':
        eth_exposure = get_symbol_exposure(symbol, portfolio)
        if eth_exposure + position_value > portfolio.total_equity * 0.30:
            return False, "Would exceed 30% ETH limit"
    
    # Check correlated group limit
    group = get_correlation_group(symbol)
    group_exposure = get_group_exposure(group, portfolio)
    if group_exposure + position_value > portfolio.total_equity * 0.60:
        return False, f"Would exceed 60% {group} group limit"
    
    return True, "OK"
```

**Acceptance Criteria:**
- [ ] Groups defined correctly
- [ ] Counts positions per group
- [ ] Warns/blocks correlated positions
- [ ] BTC exposure capped at 40% of portfolio
- [ ] ETH exposure capped at 30% of portfolio
- [ ] Combined correlated exposure capped at 60%
- [ ] Check performed BEFORE allowing new entry
- [ ] Unit test: correlation check with specific limits

---

### Task 3.3.7: Implement Circuit Breaker Manager
- [ ] **Status:** Not Started
- **Description:** Coordinate all circuit breakers
- **Dependencies:** [3.3.1-3.3.6]
- **Effort:** 2 hours

**Add to:** `src/core/risk/circuit_breakers.py`

**CircuitBreakerManager:**
```python
class CircuitBreakerManager:
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._states: Dict[str, bool] = {}  # name -> triggered
    
    def register(self, breaker: CircuitBreaker):
        pass
    
    async def check_all(self, state: PortfolioState) -> List[CircuitBreakerResult]:
        pass
    
    def is_any_triggered(self) -> bool:
        pass
    
    def get_triggered_breakers(self) -> List[str]:
        pass
    
    async def reset_breaker(self, name: str):
        pass
```

**Acceptance Criteria:**
- [ ] Registers all breakers
- [ ] Checks all in parallel
- [ ] Tracks triggered states
- [ ] Reset individual breakers
- [ ] Unit test: manager operations

---

### Task 3.3.8: Write Circuit Breaker Tests
- [ ] **Status:** Not Started
- **Description:** Comprehensive circuit breaker tests
- **Dependencies:** [3.3.1-3.3.7]
- **Effort:** 2.5 hours

**File:** `tests/unit/test_circuit_breakers.py`

**Test scenarios:**
- Each breaker in isolation
- Multiple breakers triggering
- Reset behavior
- Edge cases (exactly at threshold)
- Time-based resets

**Acceptance Criteria:**
- [ ] All breakers tested
- [ ] Manager tested
- [ ] Edge cases covered
- [ ] >90% coverage

---

## SECTION 3.4: VOLATILITY FILTER
*Estimated: 12 hours*

### Task 3.4.1: Create Volatility Analyzer
- [ ] **Status:** Not Started
- **Description:** Analyze current market volatility per PRD Safety A
- **Dependencies:** [2.2.4]  # Needs ATR
- **Effort:** 2.5 hours

**File:** `src/core/risk/volatility.py`

**VolatilityAnalyzer class:**
```python
class VolatilityAnalyzer:
    """
    Volatility filter per PRD Safety A.
    
    Volatility measure: ATR(14) / Close price * 100
    
    Thresholds:
    - NORMAL: < 3% ATR → Full trading
    - ELEVATED: 3-5% ATR → Reduce size 50%, widen stops 50%
    - EXTREME: > 5% ATR → Exits only, no new entries
    
    Cooldown: Wait 4 hours after vol drops before resuming
    """
    
    NORMAL_THRESHOLD = 3.0      # Below 3% = normal
    ELEVATED_THRESHOLD = 5.0    # 3-5% = elevated
    # Above 5% = extreme
    
    COOLDOWN_HOURS = 4
    ELEVATED_SIZE_MULTIPLIER = 0.5   # 50% position size
    ELEVATED_STOP_MULTIPLIER = 1.5   # 50% wider stops
    
    def __init__(self, market_data_service):
        self.market_data = market_data_service
        self._cooldown_until: Dict[str, datetime] = {}
    
    async def get_volatility_ratio(self, symbol: str, timeframe: str = "1h") -> float:
        """Current ATR / Close price * 100 as percentage."""
        atr = await self.market_data.get_atr(symbol, timeframe, period=14)
        close = await self.market_data.get_current_price(symbol)
        return (atr / close) * 100
    
    async def get_regime(self, symbol: str) -> VolatilityRegime:
        """Classify current volatility regime."""
        vol_pct = await self.get_volatility_ratio(symbol)
        
        if vol_pct < self.NORMAL_THRESHOLD:
            return VolatilityRegime.NORMAL
        elif vol_pct < self.ELEVATED_THRESHOLD:
            return VolatilityRegime.ELEVATED
        else:
            return VolatilityRegime.EXTREME
    
    async def should_reduce_size(self, symbol: str) -> Tuple[bool, float]:
        """Should position size be reduced? Returns (yes/no, multiplier)."""
        regime = await self.get_regime(symbol)
        
        if regime == VolatilityRegime.ELEVATED:
            return True, self.ELEVATED_SIZE_MULTIPLIER
        elif regime == VolatilityRegime.EXTREME:
            return True, 0.0  # No entries
        return False, 1.0
    
    async def can_enter(self, symbol: str) -> Tuple[bool, str]:
        """Check if new entries are allowed."""
        regime = await self.get_regime(symbol)
        
        # Check cooldown
        if symbol in self._cooldown_until:
            if datetime.utcnow() < self._cooldown_until[symbol]:
                return False, "Volatility cooldown active"
        
        if regime == VolatilityRegime.EXTREME:
            return False, "Extreme volatility - exits only"
        
        return True, "OK"
```

**VolatilityRegime enum:** LOW, NORMAL, ELEVATED, EXTREME

**Acceptance Criteria:**
- [ ] Volatility ratio calculated correctly (ATR / Price * 100)
- [ ] Normal regime: ATR/Price < 3%
- [ ] Elevated regime: ATR/Price 3-5% → 50% size reduction
- [ ] Extreme regime: ATR/Price > 5% → exits only, no new entries
- [ ] Widen stops by 50% in elevated regime
- [ ] Cooldown: 4 hours after vol drops below threshold
- [ ] Regime classification works
- [ ] Size adjustment recommended
- [ ] Unit test: volatility analysis with specific thresholds

---

### Task 3.4.2: Implement Volatility-Based Size Adjustment
- [ ] **Status:** Not Started
- **Description:** Reduce position sizes in high volatility
- **Dependencies:** [3.4.1, 3.1.6]
- **Effort:** 2 hours

**Add to:** `src/core/risk/volatility.py`

**Logic:**
```python
def calculate_size_multiplier(volatility_ratio: float, regime: VolatilityRegime) -> float:
    """
    Returns multiplier for position size.
    - LOW volatility: 1.0 (full size)
    - NORMAL volatility: 1.0 (full size)
    - HIGH volatility: 0.5-0.75 (reduced)
    - EXTREME volatility: 0.25-0.5 or skip trade
    """
```

**Integration:** Call from RiskController.calculate_position_size()

**Acceptance Criteria:**
- [ ] Multiplier reduces size in high vol
- [ ] Extreme vol can block trades
- [ ] Integrates with position sizing
- [ ] Unit test: multiplier values

---

### Task 3.4.3: Implement Trading Hours Filter
- [ ] **Status:** Not Started
- **Description:** Weekend/holiday awareness per PRD Safety B
- **Dependencies:** [3.1.1]
- **Effort:** 2 hours

**File:** `src/core/risk/time_filter.py`

**TradingHoursFilter:**
- Allow/block by hour of day (UTC)
- Weekend awareness (crypto-specific)
- Holiday calendar with reduced trading

**PRD Safety B - Weekend/Holiday Awareness:**
```python
class WeekendHolidayFilter:
    """
    Adjust behavior during low-liquidity periods per PRD Safety B.
    
    Weekend: Saturday 00:00 UTC to Sunday 23:59 UTC
    - Position size multiplier: 0.5 (half size)
    - Volume requirement multiplier: 2.0 (require 2x normal volume)
    - Spread tolerance: 1.5x (accept 50% wider spreads)
    - Max position: 3% of portfolio
    
    Holidays: Apply weekend rules
    - Christmas: Dec 24-26
    - New Year: Dec 31 - Jan 2
    - Chinese New Year: Variable dates
    """
    
    WEEKEND_SIZE_MULTIPLIER = 0.5
    WEEKEND_VOLUME_MULTIPLIER = 2.0
    WEEKEND_SPREAD_TOLERANCE = 1.5
    WEEKEND_MAX_POSITION_PCT = 3.0
    
    HOLIDAYS = [
        ('christmas', [(12, 24), (12, 25), (12, 26)]),
        ('new_year', [(12, 31), (1, 1), (1, 2)]),
        # Chinese New Year dates need yearly update
    ]
    
    def is_weekend(self) -> bool:
        """Check if current time is weekend (Sat 00:00 - Sun 23:59 UTC)."""
        now = datetime.utcnow()
        return now.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    def is_holiday(self) -> bool:
        """Check if current date is a major holiday."""
        now = datetime.utcnow()
        for name, dates in self.HOLIDAYS:
            for month, day in dates:
                if now.month == month and now.day == day:
                    return True
        return False
    
    def is_low_liquidity_period(self) -> bool:
        """Check if weekend or holiday."""
        return self.is_weekend() or self.is_holiday()
    
    def get_adjustments(self) -> Dict[str, float]:
        """Get trading adjustments for current period."""
        if self.is_low_liquidity_period():
            return {
                'size_multiplier': self.WEEKEND_SIZE_MULTIPLIER,
                'volume_multiplier': self.WEEKEND_VOLUME_MULTIPLIER,
                'spread_tolerance': self.WEEKEND_SPREAD_TOLERANCE,
                'max_position_pct': self.WEEKEND_MAX_POSITION_PCT
            }
        return {
            'size_multiplier': 1.0,
            'volume_multiplier': 1.0,
            'spread_tolerance': 1.0,
            'max_position_pct': None  # Use normal limits
        }
```

**Config:**
```yaml
trading_hours:
  enabled: false  # Disabled by default for 24/7 crypto
  allowed_hours: [0, 1, 2, ..., 23]  # UTC hours
  block_weekends: false
  weekend_adjustments: true  # Apply reduced sizing on weekends
```

**Acceptance Criteria:**
- [ ] Hour filtering works
- [ ] Weekend detection: Saturday 00:00 - Sunday 23:59 UTC
- [ ] Position size reduced to 50% on weekends
- [ ] Volume requirement doubled on weekends
- [ ] Spread tolerance increased by 50% on weekends
- [ ] Max position capped at 3% on weekends
- [ ] Holiday calendar: Christmas (Dec 24-26), New Year (Dec 31-Jan 2)
- [ ] Holiday mode applies same rules as weekend
- [ ] Disabled by default (can enable via config)
- [ ] Unit test: weekend/holiday detection
- [ ] Unit test: adjustment calculations

---

### Task 3.4.4: Implement News Event Filter
- [ ] **Status:** Not Started
- **Description:** Block trading during major events
- **Dependencies:** [3.1.1]
- **Effort:** 2 hours

**File:** `src/core/risk/event_filter.py`

**EventFilter:**
- Configurable event calendar
- Block trading X hours before/after events
- Events: Fed meetings, major crypto events, etc.

**MVP:** Simple implementation with manual event list. Future: integrate economic calendar API.

**Config:**
```yaml
events:
  - name: "FOMC Meeting"
    date: "2024-03-20"
    block_hours_before: 2
    block_hours_after: 4
```

**Acceptance Criteria:**
- [ ] Event blocking works
- [ ] Configurable before/after buffer
- [ ] Easy to add events
- [ ] Unit test: event filtering

---

### Task 3.4.5: Integrate Filters into Risk Controller
- [ ] **Status:** Not Started
- **Description:** Add volatility/time filters to order check pipeline
- **Dependencies:** [3.4.1-3.4.4, 3.1.7]
- **Effort:** 1.5 hours

**Update:** `src/core/risk/controller.py`

**Add to pipeline:**
1. Kill switch check
2. Circuit breakers
3. **Volatility filter** (NEW)
4. **Time filter** (NEW)
5. **Event filter** (NEW)
6. Position size check (with volatility adjustment)
7. Concentration check
8. Max positions check

**Acceptance Criteria:**
- [ ] Filters integrated into pipeline
- [ ] Volatility affects position sizing
- [ ] Filters can be disabled via config
- [ ] Unit test: filter integration

---

### Task 3.4.6: Write Volatility Filter Tests
- [ ] **Status:** Not Started
- **Description:** Tests for all filters
- **Dependencies:** [3.4.1-3.4.5]
- **Effort:** 2 hours

**File:** `tests/unit/test_volatility_filter.py`

**Test scenarios:**
- Low/normal/high/extreme volatility
- Size adjustment multipliers
- Time-based filtering
- Event-based filtering
- Filter bypass when disabled

**Acceptance Criteria:**
- [ ] All filters tested
- [ ] Integration tested
- [ ] Edge cases covered
- [ ] >85% coverage

---

## 📋 PHASE 3 COMPLETION CHECKLIST

Before moving to Phase 4, verify:

- [ ] All 30 tasks completed
- [ ] Kill switch activates in <1 second
- [ ] Kill switch persists across restarts
- [ ] Dead man's switch monitors heartbeat correctly
- [ ] All risk limits enforced (position size, concentration, max positions)
- [ ] Capital allocation rules enforced (20% reserve, 5%/15% strategy limits)
- [ ] Circuit breakers trigger correctly (daily loss, drawdown, consecutive losses)
- [ ] Correlation limits enforced (40% BTC, 30% ETH, 60% group)
- [ ] Volatility filter reduces position sizes in high vol (50% at elevated)
- [ ] Weekend/holiday adjustments apply (50% size, 2x volume requirement)
- [ ] Position sizing calculations verified with manual calculations
- [ ] `pytest tests/unit/test_risk_controller.py` passes
- [ ] `pytest tests/unit/test_kill_switch.py` passes
- [ ] `pytest tests/unit/test_circuit_breakers.py` passes
- [ ] No linting errors

**Risk Checklist (PRD Compliance):**
- [ ] Max position size enforced per PRD 3.4.1
- [ ] Max concentration enforced per PRD 3.4.2
- [ ] Daily loss limit implemented per PRD 3.4.3
- [ ] Drawdown limit implemented per PRD 3.4.4
- [ ] Kill switch implemented per PRD 3.4.5
- [ ] Dead man's switch implemented per PRD Feature C
- [ ] Capital allocation rules per PRD Feature G
- [ ] Correlation limits per PRD Feature A
- [ ] Volatility filter thresholds per PRD Safety A
- [ ] Weekend/holiday awareness per PRD Safety B

**Sign-off:** _________________ Date: _________________

---

**Previous Phase:** [02_PHASE_2_DATA_LAYER.md](./02_PHASE_2_DATA_LAYER.md)  
**Next Phase:** [04_PHASE_4_EXECUTION.md](./04_PHASE_4_EXECUTION.md)
