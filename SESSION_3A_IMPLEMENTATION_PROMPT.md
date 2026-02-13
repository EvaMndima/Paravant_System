# SESSION 3A IMPLEMENTATION PROMPT
## Risk Controller & Kill Switch | Production-Grade Implementation

**Phase:** 3 (Risk Controls)
**Sections:** 3.1 (Risk Controller) + 3.2 (Kill Switch)
**Duration:** 32 hours
**Tasks:** 16 total (9 + 7)
**Model Recommendation:** Opus (complex financial logic, state management)
**Code Quality:** Zero-technical-debt, 100% type hints, >90% test coverage

---

## MANDATORY READING BEFORE STARTING

1. **`.claude/DECISIONS.md`** - Read all architectural decisions (decision consistency is non-negotiable)
2. **`.claude/rules/zero-technical-debt.md`** - Code quality standards
3. **`.claude/rules/decision-consistency.md`** - Decision enforcement
4. **`TRADING_SYSTEM_PRD.md`** - Section 3 (Risk Management)
5. **`docs/03_PHASE_3_RISK_CONTROLS.md`** - Sections 3.1 + 3.2 (this document)
6. **Phase 1 & 2 Code** - Understand OHLCVSeries, Account, Position, Order models
7. **This Prompt** - Read completely before implementing

---

## CRITICAL SUCCESS FACTORS FOR SESSION 3A

### Why This Matters
Risk controllers are safety-critical code. **A single bug can lose capital or fail to prevent losses.** This session enforces:

- ✅ 100% type hints (no `Any` without justification)
- ✅ Input validation at all boundaries (reject NaN, Infinity, invalid values)
- ✅ State persistence (kill switch survives restarts)
- ✅ Decision consistency (all decisions documented and followed)
- ✅ Financial correctness (no precision loss, proper rounding)
- ✅ Test coverage >90% per file (critical paths fully tested)
- ✅ Integration safety (no breaking changes to Phase 1/2)

### Risk Scenarios We Must Handle
```python
# Edge case: NaN from missing data → Must reject, not propagate
# Edge case: Negative equity (liquidation) → Must trigger kill switch
# Edge case: Account deleted mid-trade → Must handle gracefully
# Edge case: Kill switch persists across restart → State must survive
# Edge case: Position sized at 0 due to volatility → Must accept (exit only)
```

---

## DEPENDENCY ANALYSIS & EXECUTION ORDER

```
Phase 1/2 Dependencies:
├─ Account model (1.2.2)
├─ Position model (1.2.4)
├─ Order model (1.2.5)
├─ Indicator calculations (2.2.x) - ATR needed for position sizing
├─ SystemState model (1.2.12) - for kill switch persistence
└─ OHLCVSeries (2.1.x) - for portfolio calculations

Session 3A Dependency Chain:
│
├─ 3.1.2 (Data Types) - FOUNDATION
│  └─ Used by all risk checks
│
├─ 3.1.1 (RiskController Core) - INFRASTRUCTURE
│  ├─ Uses: 3.1.2 data types
│  └─ Used by: 3.1.3-3.1.7
│
├─ 3.1.3 (Position Size Check) - INDEPENDENT CHECKS
├─ 3.1.4 (Concentration Check)
├─ 3.1.5 (Max Positions Check)
└─ 3.1.6 (Position Size Calculator)
     └─ Used by 3.1.6a
     └─ Uses ATR from Phase 2

├─ 3.1.6a (Capital Allocation) - EXTENDS POSITION SIZING
│  ├─ Uses: 3.1.6 for integration
│  └─ Must track strategy state
│
├─ 3.2.1 (Kill Switch Core) - EMERGENCY MECHANISM
│  ├─ Independent from 3.1.3-3.1.5
│  └─ Used by 3.1.7 order pipeline
│
├─ 3.2.2 (Kill Switch Triggers) - AUTO-ACTIVATION
│  └─ Uses: 3.2.1
│
├─ 3.2.3 (Position Closing) - DEPENDS ON EXECUTION
│  └─ Uses: 3.2.1, assumes execution layer exists
│
├─ 3.2.4 (Kill Switch API) - USER INTERFACE
│  └─ Uses: 3.2.1
│
├─ 3.2.5 (Kill Switch Recovery) - STATE PERSISTENCE
│  └─ Uses: 3.2.1, database
│
├─ 3.2.6a (Dead Man's Switch) - ADVANCED SAFETY
│  └─ Uses: 3.2.1, alert manager
│
├─ 3.1.7 (Order Validation Pipeline) - INTEGRATION HUB
│  ├─ Uses: 3.1.1, 3.1.3-3.1.5, 3.2.1
│  └─ MUST RUN ALL CHECKS IN SEQUENCE (order matters!)
│
└─ 3.1.8 + 3.2.6 (TESTING) - COMPREHENSIVE COVERAGE
   ├─ Test all risk checks
   ├─ Test kill switch paths
   ├─ Test pipeline ordering
   └─ Test edge cases (zero equity, missing positions, etc.)
```

### EXECUTION SEQUENCE (STRICT ORDER)

**DO NOT DEVIATE FROM THIS ORDER - Dependencies must be satisfied first**

#### Phase 1: Foundation (Tasks 1-2)
1. **Task 3.1.2**: Create Risk Check Data Types → Establishes RiskCheckResult, OrderRequest, PortfolioState
2. **Task 3.1.1**: Create Risk Controller Core → Infrastructure that will use 3.1.2

#### Phase 2: Independent Checks (Tasks 3-5, can parallelize)
3. **Task 3.1.3**: Implement Position Size Check
4. **Task 3.1.4**: Implement Concentration Check
5. **Task 3.1.5**: Implement Max Positions Check

#### Phase 3: Position Sizing (Tasks 6-7)
6. **Task 3.1.6**: Implement Position Size Calculator → Uses ATR from Phase 2
7. **Task 3.1.6a**: Implement Capital Allocation Rules → Extends 3.1.6

#### Phase 4: Kill Switch (Tasks 8-13, can parallelize some)
8. **Task 3.2.1**: Create Kill Switch Core → Foundation for all kill switch features
9. **Task 3.2.2**: Implement Kill Switch Triggers
10. **Task 3.2.3**: Implement Position Closing
11. **Task 3.2.4**: Create Kill Switch API
12. **Task 3.2.5**: Implement Kill Switch Recovery
13. **Task 3.2.6a**: Implement Dead Man's Switch

#### Phase 5: Integration & Testing (Tasks 14-16)
14. **Task 3.1.7**: Implement Order Validation Pipeline → INTEGRATES all checks (3.1.3-3.1.5, 3.2.1)
15. **Task 3.1.8**: Write Risk Controller Tests
16. **Task 3.2.6**: Write Kill Switch Tests

---

## SECTION 3.1: RISK CONTROLLER

### Task 3.1.1: Create Risk Controller Core

**File:** `src/core/risk/controller.py`

**Purpose:** Central orchestration point for all risk checks. All orders flow through this before execution.

**Key Type Definitions:**
```python
from dataclasses import dataclass, field
from typing import Optional, List, Any
from datetime import datetime, timezone
import math

@dataclass
class RiskCheckResult:
    """Result of a risk check operation."""
    approved: bool
    check_name: str  # Name of check that processed this
    reason: Optional[str] = None  # Rejection reason
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

**RiskController Class Structure:**
```python
from src.data.store import DataStore
from src.core.config import RiskConfig
from src.core.risk.kill_switch import KillSwitch

class RiskController:
    """
    Central risk management orchestrator.

    Coordinates all risk checks:
    - Kill switch (emergency stop)
    - Circuit breakers (auto-limits)
    - Position sizing (risk-adjusted)
    - Concentration (portfolio balance)
    - Capital allocation (per-strategy)

    Decision: DEC-2026-02-08-XXX - Centralized risk orchestration
    """

    def __init__(
        self,
        data_store: DataStore,
        risk_config: RiskConfig,
        symbol_manager: Any  # SymbolManager from Phase 2
    ) -> None:
        self.data_store = data_store
        self.risk_config = risk_config
        self.symbol_manager = symbol_manager
        self.kill_switch = KillSwitch(data_store)
        self._check_cache: dict[str, Any] = {}  # Runtime cache

    async def check_order(self, order_request: OrderRequest) -> RiskCheckResult:
        """
        Main entry point - run all risk checks on an order.

        Pipeline order (STRICT - do NOT reorder):
        1. Kill switch check (immediate rejection if active)
        2. Circuit breaker checks
        3. Position size check
        4. Concentration check
        5. Max positions check

        Args:
            order_request: Order details to validate

        Returns:
            RiskCheckResult with approval status

        Raises:
            ValueError: If order_request contains invalid data (NaN, Infinity)
        """
        # Validate input
        self._validate_order_request(order_request)

        # Run all checks in pipeline
        pass

    async def calculate_position_size(
        self,
        account_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss_price: float
    ) -> PositionSizeResult:
        """
        Calculate risk-adjusted position size.

        Uses multiple sizing methods:
        - Fixed risk %: Risk fixed % of equity per trade
        - ATR-based: Size based on volatility
        - Kelly Criterion: Probability-adjusted sizing

        Args:
            account_id: Account identifier
            symbol: Trading symbol (e.g., "BTCUSDT")
            side: "buy" or "sell"
            entry_price: Entry price in USDT
            stop_loss_price: Stop loss price in USDT

        Returns:
            PositionSizeResult with quantity, risk amount, and method used

        Raises:
            ValueError: If stop_loss_price >= entry_price
        """
        pass

    def _validate_order_request(self, order_request: OrderRequest) -> None:
        """
        Validate order request for NaN, Infinity, invalid values.

        ⚠️ CRITICAL: Reject requests with:
        - NaN in price, quantity
        - Infinity in price, quantity
        - Negative prices or quantities
        - Zero quantity
        - Invalid side (not "buy" or "sell")
        """
        if order_request.price is None or math.isnan(order_request.price):
            raise ValueError("Order price cannot be NaN")
        if math.isinf(order_request.price):
            raise ValueError("Order price cannot be Infinity")
        if order_request.price <= 0:
            raise ValueError("Order price must be positive")

        if order_request.quantity is None or math.isnan(order_request.quantity):
            raise ValueError("Order quantity cannot be NaN")
        if math.isinf(order_request.quantity):
            raise ValueError("Order quantity cannot be Infinity")
        if order_request.quantity <= 0:
            raise ValueError("Order quantity must be positive")

        if order_request.side not in ("buy", "sell"):
            raise ValueError(f"Invalid side: {order_request.side}")
```

**Acceptance Criteria:**
- [ ] Central orchestration of all risk checks
- [ ] Integrates with kill switch
- [ ] Input validation rejects NaN/Infinity/invalid values
- [ ] Uses risk profiles from config
- [ ] Structured logging for all decisions
- [ ] Unit test: basic structure and validation

---

### Task 3.1.2: Create Risk Check Data Types

**File:** `src/core/risk/types.py`

**Purpose:** Immutable data classes for type safety. These are used throughout risk checking.

```python
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum

class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    """Order type enumeration (MVP: market only)."""
    MARKET = "market"
    # LIMIT = "limit"  # V1 feature

@dataclass(frozen=True)
class OrderRequest:
    """
    Order request for risk checking.

    Immutable - cannot be modified after creation.
    All fields validated at creation time.
    """
    account_id: str
    strategy_id: str
    symbol: str  # e.g., "BTCUSDT"
    side: str  # "buy" or "sell"
    quantity: float  # Base currency units
    price: float  # USDT price
    order_type: str  # "market" (MVP only)
    reason: str  # Why this order (e.g., "trend_signal")

    def __post_init__(self) -> None:
        """Validate all fields are present and valid."""
        if not self.account_id:
            raise ValueError("account_id required")
        if not self.symbol:
            raise ValueError("symbol required")
        if self.side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {self.side}")

@dataclass(frozen=True)
class RiskCheckResult:
    """
    Result of a risk check.

    Fields:
    - approved: bool - whether order was approved
    - check_name: str - which check ran (e.g., "position_size", "concentration")
    - adjusted_quantity: Optional[float] - if position was sized down, new size
    - rejection_reason: Optional[str] - if rejected, why
    - warnings: List[str] - non-blocking warnings
    - checks_passed: List[str] - checks that passed
    - checks_failed: List[str] - checks that failed
    """
    approved: bool
    check_name: str
    adjusted_quantity: Optional[float] = None
    rejection_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class PortfolioState:
    """
    Current portfolio state snapshot.

    Used for risk calculations. All values frozen at creation time.
    Must be reconstructed for each check (immutable pattern).
    """
    account_id: str
    total_equity: float  # Total account value in USDT
    cash_balance: float  # Available cash in USDT
    positions_value: float  # Sum of all open position values
    open_positions: List[Any]  # List of Position objects
    daily_pnl: float  # Realized P&L since UTC 00:00
    weekly_pnl: float  # Realized P&L since Monday UTC 00:00
    drawdown_pct: float  # Current drawdown from peak (%)
    peak_equity: float  # Highest equity this session
    consecutive_losses: int  # Count of consecutive losing trades

    def __post_init__(self) -> None:
        """Validate portfolio state is internally consistent."""
        import math

        # Reject NaN/Infinity
        for field_name in ['total_equity', 'cash_balance', 'positions_value', 'daily_pnl', 'drawdown_pct']:
            value = getattr(self, field_name)
            if math.isnan(value):
                raise ValueError(f"{field_name} cannot be NaN")
            if math.isinf(value):
                raise ValueError(f"{field_name} cannot be Infinity")

        # Equity invariant: total = cash + positions
        expected_total = self.cash_balance + self.positions_value
        if abs(self.total_equity - expected_total) > 0.01:  # Allow 1 cent rounding
            raise ValueError(
                f"Equity mismatch: total_equity={self.total_equity}, "
                f"but cash({self.cash_balance}) + positions({self.positions_value}) = {expected_total}"
            )

        # Drawdown must be 0-100%
        if not 0 <= self.drawdown_pct <= 100:
            raise ValueError(f"Drawdown must be 0-100%, got {self.drawdown_pct}%")

@dataclass(frozen=True)
class PositionSizeResult:
    """
    Result of position sizing calculation.

    Returned by calculate_position_size().
    """
    quantity: float  # Position size in base currency
    notional_value: float  # Position value in USDT (quantity * price)
    risk_amount: float  # $ at risk (equity * risk_pct)
    risk_pct: float  # Risk as % of equity
    sizing_method: str  # "fixed_risk", "atr_based", "kelly"
    stop_loss_price: float  # Stop loss price used
    entry_price: float  # Entry price used
```

**Acceptance Criteria:**
- [ ] All necessary fields captured
- [ ] Dataclasses frozen (immutable)
- [ ] Serializable to JSON for logging
- [ ] Validation in __post_init__ prevents invalid states
- [ ] Unit test: create valid and invalid instances

---

### Task 3.1.3: Implement Position Size Check

**File:** `src/core/risk/controller.py` (add method)

**Purpose:** Enforce maximum position size limits (% of account equity).

**Algorithm:**
```python
# Configuration (per risk profile)
max_position_size_pct = {
    "conservative": 2.0,   # 2% of equity max
    "balanced": 5.0,       # 5% of equity max
    "aggressive": 10.0     # 10% of equity max
}

# Check
position_value = quantity * price
position_pct = (position_value / total_equity) * 100

if position_pct > max_position_size_pct:
    REJECT
else:
    APPROVE
```

**Implementation:**
```python
async def _check_position_size(
    self,
    order_request: OrderRequest,
    portfolio_state: PortfolioState
) -> tuple[bool, Optional[str]]:
    """
    Check if order would exceed max position size limit.

    Args:
        order_request: Order to validate
        portfolio_state: Current portfolio state

    Returns:
        (approved: bool, rejection_reason: Optional[str])

    Raises:
        ValueError: If calculation results in NaN or invalid math
    """
    import math

    # Get risk profile from config
    risk_profile = self.risk_config.risk_profile  # "conservative", "balanced", "aggressive"
    max_pct_map = {
        "conservative": 2.0,
        "balanced": 5.0,
        "aggressive": 10.0
    }
    max_position_pct = max_pct_map.get(risk_profile, 5.0)

    # Calculate position value
    position_value = order_request.quantity * order_request.price

    # Reject if NaN/Infinity
    if math.isnan(position_value) or math.isinf(position_value):
        raise ValueError(f"Position value is invalid: {position_value}")

    # Calculate as % of equity
    if portfolio_state.total_equity <= 0:
        raise ValueError("Cannot check position size with zero/negative equity")

    position_pct = (position_value / portfolio_state.total_equity) * 100

    # Check against limit
    if position_pct > max_position_pct:
        reason = (
            f"Position size {position_pct:.2f}% exceeds max {max_position_pct}% "
            f"(order value: ${position_value:,.2f}, equity: ${portfolio_state.total_equity:,.2f})"
        )
        return False, reason

    return True, None
```

**Acceptance Criteria:**
- [ ] Rejects orders exceeding max size
- [ ] Returns appropriate error message
- [ ] Respects risk profile settings
- [ ] Handles edge cases: zero equity, negative quantity
- [ ] Unit test: multiple position sizes and risk profiles

---

### Task 3.1.4: Implement Concentration Check

**File:** `src/core/risk/controller.py` (add method)

**Purpose:** Prevent over-concentration in single asset (too much money in one symbol).

**Algorithm:**
```python
# Configuration
max_concentration_pct = 30.0  # Default: 30% of equity in single symbol

# Check
existing_position = portfolio.get_position(symbol)
existing_value = existing_position.quantity * current_price if existing_position else 0
new_position_value = quantity * price
combined_value = existing_value + new_position_value
combined_pct = (combined_value / total_equity) * 100

if combined_pct > max_concentration_pct:
    REJECT
else:
    APPROVE
```

**Implementation:**
```python
async def _check_concentration(
    self,
    order_request: OrderRequest,
    portfolio_state: PortfolioState
) -> tuple[bool, Optional[str]]:
    """
    Check if order would exceed max concentration limit for symbol.

    Args:
        order_request: Order to validate
        portfolio_state: Current portfolio state

    Returns:
        (approved: bool, rejection_reason: Optional[str])
    """
    import math

    max_concentration_pct = self.risk_config.max_concentration_pct  # Default: 30%

    # Find existing position for this symbol
    existing_position = None
    for position in portfolio_state.open_positions:
        if position.symbol == order_request.symbol:
            existing_position = position
            break

    # Calculate existing value
    existing_value = 0.0
    if existing_position:
        # Get current price for the symbol
        current_price = await self.data_store.get_current_price(order_request.symbol)
        existing_value = existing_position.quantity * current_price

    # Calculate new position value
    new_value = order_request.quantity * order_request.price

    # Combined concentration
    combined_value = existing_value + new_value
    combined_pct = (combined_value / portfolio_state.total_equity) * 100

    # Check against limit
    if combined_pct > max_concentration_pct:
        remaining_capacity = max_concentration_pct - (existing_value / portfolio_state.total_equity * 100)
        reason = (
            f"Position {order_request.symbol} would be {combined_pct:.2f}% of portfolio. "
            f"Max allowed: {max_concentration_pct}%. "
            f"Remaining capacity: ${remaining_capacity * portfolio_state.total_equity / 100:,.2f}"
        )
        return False, reason

    return True, None
```

**Acceptance Criteria:**
- [ ] Considers existing positions in symbol
- [ ] Prevents over-concentration
- [ ] Returns remaining capacity info
- [ ] Unit test: various concentration scenarios

---

### Task 3.1.5: Implement Max Positions Check

**File:** `src/core/risk/controller.py` (add method)

**Purpose:** Limit number of concurrent open positions.

**Algorithm:**
```python
# Configuration
max_open_positions = 10  # Default

# Check
open_count = len([p for p in portfolio.open_positions if p.status == "open"])

# Exception: if this is a closing trade (opposite side to existing)
if side == opposite_of(existing_position.side):
    # Allow closing existing position (doesn't increase position count)
    APPROVE
elif open_count < max_open_positions:
    APPROVE
else:
    REJECT
```

**Implementation:**
```python
async def _check_max_positions(
    self,
    order_request: OrderRequest,
    portfolio_state: PortfolioState
) -> tuple[bool, Optional[str]]:
    """
    Check if we can open new positions (don't exceed max count).

    Exception: always allow closing existing positions.

    Args:
        order_request: Order to validate
        portfolio_state: Current portfolio state

    Returns:
        (approved: bool, rejection_reason: Optional[str])
    """
    max_positions = self.risk_config.max_open_positions  # Default: 10

    # Count open positions
    open_count = len([p for p in portfolio_state.open_positions if p.status == "open"])

    # Check if this is a closing trade
    existing_position = None
    for position in portfolio_state.open_positions:
        if position.symbol == order_request.symbol:
            existing_position = position
            break

    # Allow closing positions (opposite side of existing)
    if existing_position:
        is_closing = (
            (existing_position.side == "long" and order_request.side == "sell") or
            (existing_position.side == "short" and order_request.side == "buy")
        )
        if is_closing:
            return True, None  # Always allow closing

    # Check if we're at max positions
    if open_count >= max_positions:
        reason = (
            f"Already at max positions ({max_positions}). "
            f"Current: {open_count}. "
            f"Close a position to open a new one."
        )
        return False, reason

    return True, None
```

**Acceptance Criteria:**
- [ ] Counts open positions correctly
- [ ] Allows closing positions (doesn't count against limit)
- [ ] Respects profile limits
- [ ] Unit test: position count scenarios

---

### Task 3.1.6: Implement Position Size Calculator

**File:** `src/core/risk/controller.py` (add method)

**Purpose:** Calculate optimal position size based on risk and volatility (ATR).

**Three Sizing Methods:**

1. **Fixed Risk %:**
   ```
   size = (equity * risk_pct) / (entry_price - stop_loss)
   ```

2. **ATR-Based:**
   ```
   atr = get_atr(symbol)  # From Phase 2 indicators
   size = (equity * risk_pct) / (atr * atr_multiplier)
   ```

3. **Kelly Criterion:**
   ```
   kelly_pct = (win_rate * avg_win - (1-win_rate) * avg_loss) / avg_win
   fractional_kelly = kelly_pct * 0.25  # Use 25% of Kelly for safety
   size = equity * fractional_kelly / (entry_price - stop_loss)
   ```

**Implementation:**
```python
async def calculate_position_size(
    self,
    account_id: str,
    symbol: str,
    side: str,
    entry_price: float,
    stop_loss_price: float
) -> PositionSizeResult:
    """
    Calculate risk-adjusted position size.

    ⚠️ CRITICAL: Stop loss MUST be below entry for long, above for short.
    """
    import math

    # Validate inputs
    if side not in ("buy", "sell"):
        raise ValueError(f"Invalid side: {side}")

    if side == "buy" and stop_loss_price >= entry_price:
        raise ValueError(
            f"For BUY: stop_loss ({stop_loss_price}) must be BELOW entry ({entry_price})"
        )

    if side == "sell" and stop_loss_price <= entry_price:
        raise ValueError(
            f"For SELL: stop_loss ({stop_loss_price}) must be ABOVE entry ({entry_price})"
        )

    # Get portfolio state
    portfolio = await self._get_portfolio_state(account_id)

    # Get account config
    account = await self.data_store.get_account(account_id)
    risk_pct = account.risk_per_trade / 100  # Convert from % to decimal

    # Fixed risk sizing (default)
    risk_per_unit = abs(entry_price - stop_loss_price)
    risk_amount = portfolio.total_equity * risk_pct
    fixed_quantity = risk_amount / risk_per_unit

    # Also calculate ATR-based (for comparison)
    atr_quantity = None
    try:
        atr = await self._get_atr(symbol)  # From Phase 2 indicators
        if atr and atr > 0:
            atr_multiplier = self.risk_config.atr_multiplier  # e.g., 2.0
            atr_quantity = (portfolio.total_equity * risk_pct) / (atr * atr_multiplier)
    except Exception:
        pass  # ATR not available, use fixed risk

    # Select quantity (prefer ATR if available, otherwise fixed)
    quantity = atr_quantity if atr_quantity else fixed_quantity

    # Calculate notional value
    notional_value = quantity * entry_price

    # Respect max position size limit
    max_position_value = portfolio.total_equity * (self.risk_config.max_position_size_pct / 100)
    if notional_value > max_position_value:
        quantity = max_position_value / entry_price
        notional_value = quantity * entry_price

    return PositionSizeResult(
        quantity=quantity,
        notional_value=notional_value,
        risk_amount=risk_amount,
        risk_pct=risk_pct * 100,
        sizing_method="atr_based" if atr_quantity else "fixed_risk",
        stop_loss_price=stop_loss_price,
        entry_price=entry_price
    )

async def _get_atr(self, symbol: str) -> Optional[float]:
    """Get current ATR for symbol from Phase 2 indicators."""
    # Calls Phase 2 indicator system to get ATR(14)
    pass
```

**Acceptance Criteria:**
- [ ] Fixed risk sizing works
- [ ] ATR-based sizing works
- [ ] Respects max position size
- [ ] Validates stop loss placement (buy: below, sell: above)
- [ ] Unit test: sizing calculations with real ATR values

---

### Task 3.1.6a: Implement Capital Allocation Rules

**File:** `src/core/risk/controller.py` (add class)

**Purpose:** Enforce systematic capital allocation per strategy (PRD Feature G).

**Rules:**
- Minimum cash reserve: 20% of portfolio
- Emergency buffer: 10% of portfolio
- New strategy max: 5% of portfolio
- Proven strategy max: 15% of portfolio
- Graduation: 30+ days profitable + 20+ trades = increase allocation by 5%

**Implementation:**
```python
class CapitalAllocator:
    """
    Capital allocation rules per PRD Feature G.

    Ensures capital is managed systematically:
    - Minimum cash reserve maintained
    - Strategies graduated from new → proven
    - Per-strategy limits enforced
    """

    MINIMUM_CASH_RESERVE_PCT = 20  # Must keep 20% cash
    EMERGENCY_BUFFER_PCT = 10      # Additional 10% emergency buffer
    NEW_STRATEGY_MAX_PCT = 5        # New strategies: max 5%
    PROVEN_STRATEGY_MAX_PCT = 15    # Proven strategies: max 15%
    GRADUATION_DAYS = 30            # Days must be profitable
    GRADUATION_MIN_TRADES = 20      # Minimum trades to graduate
    GRADUATION_INCREASE_PCT = 5     # Increase by 5% on graduation

    def __init__(self, data_store: DataStore) -> None:
        self.data_store = data_store

    def get_available_capital(self, portfolio: PortfolioState) -> float:
        """
        Calculate capital available for new positions.

        Available = Cash - (Minimum Reserve + Emergency Buffer)
        """
        total = portfolio.total_equity
        reserved_pct = self.MINIMUM_CASH_RESERVE_PCT + self.EMERGENCY_BUFFER_PCT
        reserved_amount = total * reserved_pct / 100

        available = max(0, portfolio.cash_balance - reserved_amount)
        return available

    def get_max_allocation(self, strategy: Any) -> float:
        """
        Get max % of portfolio for a strategy.

        Args:
            strategy: Strategy object

        Returns:
            Max allocation as % of portfolio
        """
        if self._is_proven(strategy):
            return self.PROVEN_STRATEGY_MAX_PCT
        return self.NEW_STRATEGY_MAX_PCT

    def _is_proven(self, strategy: Any) -> bool:
        """
        Check if strategy qualifies as proven.

        Requirements:
        - Profitable for 30+ consecutive days
        - 20+ completed trades
        """
        # Query strategy stats from database
        # Return True only if BOTH requirements met
        pass

    def check_graduation(self, strategy: Any) -> Optional[float]:
        """
        Check if strategy can increase allocation.

        Returns:
            New allocation % if eligible, None otherwise
        """
        if not self._is_proven(strategy):
            return None

        current_alloc = self._get_current_allocation(strategy)
        new_alloc = current_alloc + self.GRADUATION_INCREASE_PCT

        if new_alloc <= self.PROVEN_STRATEGY_MAX_PCT:
            return new_alloc
        return None

    def validate_allocation(
        self,
        strategy: Any,
        requested_pct: float,
        portfolio: PortfolioState
    ) -> tuple[bool, str]:
        """
        Validate requested strategy allocation.

        Args:
            strategy: Strategy requesting capital
            requested_pct: Requested allocation as % of portfolio
            portfolio: Current portfolio state

        Returns:
            (approved: bool, reason: str)
        """
        # Check against max for this strategy
        max_allowed = self.get_max_allocation(strategy)
        if requested_pct > max_allowed:
            return False, f"Max allocation for this strategy is {max_allowed}%"

        # Check available capital
        available = self.get_available_capital(portfolio)
        requested_value = portfolio.total_equity * requested_pct / 100

        if requested_value > available:
            return False, (
                f"Insufficient available capital. "
                f"Requested: ${requested_value:,.2f}, "
                f"Available: ${available:,.2f}"
            )

        return True, "OK"

    def _get_current_allocation(self, strategy: Any) -> float:
        """Get current allocation % for strategy."""
        # Query database for strategy's current allocated capital
        pass
```

**Add to RiskController:**
```python
def __init__(self, ...):
    # ... existing init ...
    self.capital_allocator = CapitalAllocator(data_store)
```

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

**File:** `src/core/risk/controller.py` (update method)

**Purpose:** Run all checks in strict sequence. First failure short-circuits (fast rejection).

**Pipeline Order (CRITICAL - DO NOT CHANGE):**
```python
async def check_order(self, order_request: OrderRequest) -> RiskCheckResult:
    """
    Master pipeline for order validation.

    Order MATTERS - earlier checks are faster rejections.

    1. Kill switch check (return in <1ms if active)
    2. Circuit breaker checks (immediate rejection if triggered)
    3. Position size check (quick % calculation)
    4. Concentration check (single symbol check)
    5. Max positions check (count open positions)
    6. Leverage check (if implemented)
    7. Capital allocation check (if strategy-based)
    8. Symbol validation (does symbol exist?)

    Returns on FIRST failure. On success, all checks pass.
    """
    import logging

    logger = logging.getLogger(__name__)

    # Get current portfolio state (snapshot at this moment)
    portfolio = await self._get_portfolio_state(order_request.account_id)

    # 1. KILL SWITCH CHECK (FASTEST - immediate rejection)
    if self.kill_switch.is_active():
        return RiskCheckResult(
            approved=False,
            check_name="kill_switch",
            rejection_reason="Kill switch is active - all trading halted"
        )

    # 2. CIRCUIT BREAKER CHECKS
    # (Will implement in Session 3B, stub for now)
    # breaker_result = await self.circuit_breaker_manager.check_all(portfolio)
    # if breaker_result.triggered:
    #     return RiskCheckResult(approved=False, check_name="circuit_breaker", ...)

    # 3. POSITION SIZE CHECK
    approved, reason = await self._check_position_size(order_request, portfolio)
    if not approved:
        return RiskCheckResult(
            approved=False,
            check_name="position_size",
            rejection_reason=reason,
            checks_failed=["position_size"]
        )

    # 4. CONCENTRATION CHECK
    approved, reason = await self._check_concentration(order_request, portfolio)
    if not approved:
        return RiskCheckResult(
            approved=False,
            check_name="concentration",
            rejection_reason=reason,
            checks_failed=["concentration"]
        )

    # 5. MAX POSITIONS CHECK
    approved, reason = await self._check_max_positions(order_request, portfolio)
    if not approved:
        return RiskCheckResult(
            approved=False,
            check_name="max_positions",
            rejection_reason=reason,
            checks_failed=["max_positions"]
        )

    # ALL CHECKS PASSED
    return RiskCheckResult(
        approved=True,
        check_name="order_validation_pipeline",
        checks_passed=["kill_switch", "position_size", "concentration", "max_positions"]
    )
```

**Acceptance Criteria:**
- [ ] All checks run in order
- [ ] First failure short-circuits
- [ ] Results logged for audit
- [ ] Pipeline order documented (DO NOT REORDER)
- [ ] Unit test: pipeline flow and short-circuit behavior

---

### Task 3.1.8: Write Risk Controller Tests

**File:** `tests/unit/test_risk_controller.py`

**Test Coverage: >90% for risk controller module**

**Test Scenarios:**
```python
import pytest
from src.core.risk.types import OrderRequest, PortfolioState
from src.core.risk.controller import RiskController

class TestRiskController:
    """Test all risk controller functionality."""

    @pytest.fixture
    def risk_controller(self, data_store, risk_config):
        """Fixture providing a RiskController."""
        return RiskController(data_store, risk_config, symbol_manager=None)

    # POSITION SIZE TESTS
    def test_position_size_within_limit(self, risk_controller, portfolio, order_request):
        """Order within position size limit should be approved."""
        pass

    def test_position_size_exceeds_limit(self, risk_controller, portfolio):
        """Order exceeding position size limit should be rejected."""
        pass

    def test_position_size_risk_profile_conservative(self, risk_controller, portfolio):
        """Conservative profile should enforce 2% max."""
        pass

    def test_position_size_with_zero_equity(self, risk_controller):
        """Should raise error for zero equity."""
        pass

    # CONCENTRATION TESTS
    def test_concentration_single_position(self, risk_controller):
        """Single position under 30% should be approved."""
        pass

    def test_concentration_exceeds_limit(self, risk_controller):
        """Concentration exceeding 30% should be rejected."""
        pass

    def test_concentration_with_existing_position(self, risk_controller):
        """Should sum existing + new position."""
        pass

    # MAX POSITIONS TESTS
    def test_max_positions_below_limit(self, risk_controller):
        """Below max positions should be approved."""
        pass

    def test_max_positions_at_limit(self, risk_controller):
        """At max positions should be rejected (unless closing)."""
        pass

    def test_max_positions_allow_closing(self, risk_controller):
        """Should allow closing positions even at max."""
        pass

    # POSITION SIZING TESTS
    def test_calculate_position_size_fixed_risk(self, risk_controller):
        """Fixed risk sizing should calculate correctly."""
        pass

    def test_calculate_position_size_invalid_stop_loss(self, risk_controller):
        """Stop loss >= entry should raise ValueError."""
        pass

    def test_calculate_position_size_respects_max(self, risk_controller):
        """Should not exceed max position size."""
        pass

    # ORDER VALIDATION PIPELINE TESTS
    async def test_check_order_all_pass(self, risk_controller):
        """Order passing all checks should be approved."""
        pass

    async def test_check_order_fails_position_size(self, risk_controller):
        """Should fail on first check (position size)."""
        pass

    async def test_check_order_fails_concentration(self, risk_controller):
        """Should fail on concentration check."""
        pass

    async def test_check_order_fails_max_positions(self, risk_controller):
        """Should fail on max positions check."""
        pass

    # INPUT VALIDATION TESTS
    def test_validate_order_request_nan_price(self, risk_controller):
        """NaN price should raise ValueError."""
        pass

    def test_validate_order_request_infinity_quantity(self, risk_controller):
        """Infinity quantity should raise ValueError."""
        pass

    def test_validate_order_request_negative_price(self, risk_controller):
        """Negative price should raise ValueError."""
        pass

    # CAPITAL ALLOCATION TESTS
    async def test_capital_allocation_new_strategy(self, risk_controller):
        """New strategy should be limited to 5%."""
        pass

    async def test_capital_allocation_proven_strategy(self, risk_controller):
        """Proven strategy should be limited to 15%."""
        pass

    async def test_capital_allocation_graduation(self, risk_controller):
        """Should graduate strategy after 30 days + 20 trades."""
        pass

# EDGE CASES
class TestRiskControllerEdgeCases:
    """Test edge cases and error conditions."""

    def test_portfolio_equity_mismatch(self):
        """PortfolioState with inconsistent equity should raise error."""
        pass

    def test_order_request_zero_quantity(self):
        """OrderRequest with zero quantity should raise error."""
        pass

    def test_empty_portfolio(self):
        """Portfolio with no positions should handle correctly."""
        pass
```

**Acceptance Criteria:**
- [ ] All check types tested
- [ ] Rejection reasons verified
- [ ] Edge cases covered
- [ ] >90% coverage for risk module

---

## SECTION 3.2: KILL SWITCH

### Task 3.2.1: Create Kill Switch Core

**File:** `src/core/risk/kill_switch.py`

**Purpose:** Emergency stop mechanism. Must activate in <1 second.

```python
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

class KillSwitchState(str, Enum):
    """Kill switch states."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    RECOVERING = "recovering"  # After restart with switch active

class KillSwitch:
    """
    Emergency trading halt mechanism.

    Properties:
    - Activates in <1 second
    - Persists state across restarts
    - Requires confirmation code to deactivate
    - Logs all state changes

    Decision: DEC-2026-02-08-XXX - Kill switch for emergency safety
    """

    def __init__(self, data_store: Any) -> None:
        self.data_store = data_store
        self._is_active = False
        self._activated_at: Optional[datetime] = None
        self._reason: Optional[str] = None
        self._confirmed_code: str = "RESTART_TRADING_SYSTEM"

    async def activate(self, reason: str, close_positions: bool = True) -> None:
        """
        Activate kill switch immediately.

        ⚠️ CRITICAL: This MUST complete in <1 second

        Args:
            reason: Why kill switch was activated
            close_positions: Whether to close all open positions

        Side Effects:
        - Blocks all new orders immediately
        - Logs event to database
        - Optionally closes existing positions
        - Sends critical alert
        """
        import logging
        logger = logging.getLogger(__name__)

        if self._is_active:
            return  # Already active

        # Activate immediately (no delay)
        self._is_active = True
        self._activated_at = datetime.now(timezone.utc)
        self._reason = reason

        # Log to database (async, non-blocking for activation)
        try:
            await self.data_store.log_kill_switch_event(
                event_type="activated",
                reason=reason,
                timestamp=self._activated_at
            )
        except Exception as e:
            logger.error("Failed to log kill switch event", extra={"error": str(e)})

        # Close positions if requested
        if close_positions:
            try:
                await self._close_all_positions()
            except Exception as e:
                logger.error("Failed to close positions on kill switch", extra={"error": str(e)})

        logger.critical(
            "kill_switch_activated",
            extra={"reason": reason, "close_positions": close_positions}
        )

    async def deactivate(self, confirm_code: str) -> bool:
        """
        Deactivate kill switch with confirmation code.

        Args:
            confirm_code: Confirmation code (must match)

        Returns:
            True if deactivated successfully, False if code incorrect
        """
        import logging
        logger = logging.getLogger(__name__)

        if not self._is_active:
            return True  # Already inactive

        if confirm_code != self._confirmed_code:
            logger.warning(
                "kill_switch_deactivation_rejected",
                extra={"provided_code": confirm_code[:3] + "***"}  # Log partially
            )
            return False

        # Deactivate
        self._is_active = False
        deactivated_at = datetime.now(timezone.utc)

        # Log to database
        try:
            await self.data_store.log_kill_switch_event(
                event_type="deactivated",
                reason=f"Manual deactivation after {deactivated_at - self._activated_at}",
                timestamp=deactivated_at
            )
        except Exception as e:
            logger.error("Failed to log deactivation", extra={"error": str(e)})

        logger.critical(
            "kill_switch_deactivated",
            extra={"duration_seconds": (deactivated_at - self._activated_at).total_seconds()}
        )

        return True

    def is_active(self) -> bool:
        """Check if kill switch is currently active."""
        return self._is_active

    def get_status(self) -> dict[str, Any]:
        """
        Get kill switch status for API/monitoring.

        Returns:
            Status dict with active state, reason, timestamp
        """
        return {
            "active": self._is_active,
            "activated_at": self._activated_at.isoformat() if self._activated_at else None,
            "reason": self._reason,
            "duration_seconds": (
                (datetime.now(timezone.utc) - self._activated_at).total_seconds()
                if self._is_active else None
            )
        }

    async def load_state(self) -> None:
        """
        Load kill switch state from database on startup.

        If system was shutdown with kill switch active, it remains active.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            state = await self.data_store.get_kill_switch_state()
            if state and state.get("active"):
                self._is_active = True
                self._activated_at = state.get("activated_at")
                self._reason = state.get("reason")
                logger.warning(
                    "kill_switch_recovered_active",
                    extra={"reason": self._reason, "was_active_for": state.get("duration")}
                )
        except Exception as e:
            logger.error("Failed to load kill switch state", extra={"error": str(e)})
            # Default to safe state (don't activate on load failure)

    async def _close_all_positions(self) -> None:
        """
        Close all open positions with market orders.

        Called by activate() if close_positions=True.
        """
        import logging
        logger = logging.getLogger(__name__)

        # Stub - actual implementation requires execution engine from Phase 4
        logger.info("close_all_positions_stub")
        # This will be implemented in Task 3.2.3
```

**Acceptance Criteria:**
- [ ] Activates in <1 second
- [ ] Persists state to database
- [ ] Requires confirmation code to deactivate
- [ ] Logs all state changes
- [ ] Unit test: activate/deactivate scenarios

---

### Task 3.2.2: Implement Kill Switch Triggers

**File:** `src/core/risk/kill_switch.py` (add method)

**Purpose:** Auto-activate kill switch on loss/drawdown triggers.

**Trigger Conditions:**
- Daily loss exceeds 5% of equity (configurable)
- Drawdown exceeds 15% of equity (configurable)
- 10+ consecutive losing trades
- Exchange connection lost >5 minutes
- Critical error in execution

```python
async def check_triggers(self, portfolio: PortfolioState) -> Optional[str]:
    """
    Check if any auto-trigger conditions are met.

    Args:
        portfolio: Current portfolio state

    Returns:
        Trigger reason if any condition met, None otherwise
    """
    # Daily loss trigger
    if portfolio.daily_pnl < 0:
        daily_loss_pct = abs(portfolio.daily_pnl) / portfolio.total_equity * 100
        if daily_loss_pct > self.daily_loss_limit_pct:
            return f"Daily loss {daily_loss_pct:.2f}% exceeds limit {self.daily_loss_limit_pct}%"

    # Drawdown trigger
    if portfolio.drawdown_pct > self.max_drawdown_pct:
        return f"Drawdown {portfolio.drawdown_pct:.2f}% exceeds limit {self.max_drawdown_pct}%"

    # Consecutive losses trigger
    if portfolio.consecutive_losses >= self.max_consecutive_losses:
        return f"{portfolio.consecutive_losses} consecutive losing trades"

    return None
```

**Acceptance Criteria:**
- [ ] All trigger conditions checked
- [ ] Triggers activation automatically
- [ ] Configurable thresholds
- [ ] Unit test: each trigger condition

---

### Task 3.2.3: Implement Position Closing on Kill Switch

**File:** `src/core/risk/kill_switch.py` (add method)

**Purpose:** Close all positions when kill switch activates (Phase 4 integration).

```python
async def _close_all_positions(self) -> None:
    """
    Close all open positions with market orders.

    Called by activate() if close_positions=True.

    Note: Execution engine is from Phase 4.
    For now, this logs intent; actual implementation requires Phase 4.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Get all open positions
        positions = await self.data_store.get_open_positions()

        # Close each position
        for position in positions:
            try:
                # This call will exist in Phase 4 (execution engine)
                # await self.execution_engine.close_position(
                #     symbol=position.symbol,
                #     quantity=position.quantity,
                #     reason="kill_switch_triggered"
                # )

                # For now, just log
                logger.info(
                    "kill_switch_close_position",
                    extra={"symbol": position.symbol, "quantity": position.quantity}
                )
            except Exception as e:
                logger.error(
                    "kill_switch_close_position_failed",
                    extra={"symbol": position.symbol, "error": str(e)}
                )
    except Exception as e:
        logger.error("kill_switch_close_all_positions_failed", extra={"error": str(e)})
```

**Acceptance Criteria:**
- [ ] Cancels pending orders
- [ ] Closes all positions (or logs intent for Phase 4)
- [ ] Handles partial fills (or logs for Phase 4)
- [ ] Timeout handling (or documented for Phase 4)

---

### Task 3.2.4: Create Kill Switch API Endpoints

**File:** `src/api/routes/risk.py`

**Purpose:** HTTP endpoints for kill switch control.

```python
from fastapi import APIRouter, HTTPException, Depends
from src.core.risk.kill_switch import KillSwitch

router = APIRouter(prefix="/api/risk", tags=["risk"])

@router.get("/kill-switch/status")
async def get_kill_switch_status(kill_switch: KillSwitch = Depends()) -> dict:
    """
    Get current kill switch status.

    Returns:
        Status dict with active state, reason, timestamp
    """
    return kill_switch.get_status()

@router.post("/kill-switch/activate")
async def activate_kill_switch(
    reason: str,
    kill_switch: KillSwitch = Depends()
) -> dict:
    """
    Activate kill switch immediately.

    ⚠️ WARNING: This will halt all trading. Use with caution.

    Args:
        reason: Reason for activation (e.g., "manual emergency", "api_error")

    Returns:
        Confirmation of activation
    """
    await kill_switch.activate(reason=reason, close_positions=True)
    return {"status": "activated", "reason": reason}

@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(
    confirm_code: str,
    kill_switch: KillSwitch = Depends()
) -> dict:
    """
    Deactivate kill switch with confirmation code.

    Args:
        confirm_code: Confirmation code (prevents accidents)

    Returns:
        Success/failure of deactivation
    """
    success = await kill_switch.deactivate(confirm_code)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid confirmation code")
    return {"status": "deactivated"}
```

**Acceptance Criteria:**
- [ ] Status endpoint returns current state
- [ ] Activate requires reason
- [ ] Deactivate requires confirmation
- [ ] Audit log updated

---

### Task 3.2.5: Implement Kill Switch Recovery

**File:** `src/core/risk/kill_switch.py` (update load_state)

**Purpose:** Recover kill switch state on system restart.

```python
async def load_state(self) -> None:
    """
    Load kill switch state from database on startup.

    If system was shutdown with kill switch active, it remains active.
    Sends alert notification.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        state = await self.data_store.get_kill_switch_state()
        if state and state.get("active"):
            self._is_active = True
            self._activated_at = state.get("activated_at")
            self._reason = state.get("reason")

            # Send recovery alert
            await self.alert_manager.send_critical(
                title="⚠️ SYSTEM RESTART WITH KILL SWITCH ACTIVE",
                message=f"Kill switch was active when system restarted. "
                        f"Reason: {self._reason}. "
                        f"Manual restart required to resume trading. "
                        f"Confirmation code: RESTART_TRADING_SYSTEM"
            )

            logger.warning(
                "kill_switch_recovered_active",
                extra={"reason": self._reason}
            )
    except Exception as e:
        logger.error("Failed to load kill switch state", extra={"error": str(e)})
```

**Acceptance Criteria:**
- [ ] State persists across restarts
- [ ] Alert sent on restart
- [ ] Audit log on recovery

---

### Task 3.2.6: Write Kill Switch Tests

**File:** `tests/unit/test_kill_switch.py`

```python
import pytest
from src.core.risk.kill_switch import KillSwitch, KillSwitchState

class TestKillSwitch:
    """Test kill switch functionality."""

    @pytest.fixture
    async def kill_switch(self, data_store):
        """Fixture providing a KillSwitch."""
        switch = KillSwitch(data_store)
        await switch.load_state()
        return switch

    async def test_activate_immediate(self, kill_switch):
        """Kill switch should activate immediately."""
        import time
        start = time.time()
        await kill_switch.activate("test")
        elapsed = time.time() - start

        assert kill_switch.is_active()
        assert elapsed < 0.001  # <1ms

    async def test_deactivate_with_correct_code(self, kill_switch):
        """Deactivation with correct code should work."""
        await kill_switch.activate("test")
        success = await kill_switch.deactivate("RESTART_TRADING_SYSTEM")

        assert success
        assert not kill_switch.is_active()

    async def test_deactivate_with_wrong_code(self, kill_switch):
        """Deactivation with wrong code should fail."""
        await kill_switch.activate("test")
        success = await kill_switch.deactivate("wrong_code")

        assert not success
        assert kill_switch.is_active()

    async def test_state_persistence(self, kill_switch, data_store):
        """State should persist to database."""
        await kill_switch.activate("test_reason")

        # Create new instance and load state
        new_switch = KillSwitch(data_store)
        await new_switch.load_state()

        assert new_switch.is_active()
        assert new_switch._reason == "test_reason"

    async def test_get_status(self, kill_switch):
        """Status should return current state."""
        await kill_switch.activate("test")
        status = kill_switch.get_status()

        assert status["active"]
        assert status["reason"] == "test"
        assert status["activated_at"] is not None

class TestKillSwitchTriggers:
    """Test auto-trigger conditions."""

    async def test_trigger_daily_loss(self, kill_switch, portfolio):
        """Should trigger on daily loss threshold."""
        portfolio.daily_pnl = -500  # 5% loss

        reason = await kill_switch.check_triggers(portfolio)
        assert reason is not None
        assert "Daily loss" in reason

    async def test_trigger_drawdown(self, kill_switch, portfolio):
        """Should trigger on drawdown threshold."""
        portfolio.drawdown_pct = 20.0  # 20% drawdown

        reason = await kill_switch.check_triggers(portfolio)
        assert reason is not None
        assert "Drawdown" in reason

    async def test_trigger_consecutive_losses(self, kill_switch, portfolio):
        """Should trigger on consecutive losses."""
        portfolio.consecutive_losses = 12  # 12 consecutive losses

        reason = await kill_switch.check_triggers(portfolio)
        assert reason is not None
        assert "consecutive" in reason
```

**Acceptance Criteria:**
- [ ] Activation/deactivation paths tested
- [ ] Deactivation security tested
- [ ] Auto-triggers tested
- [ ] >90% coverage

---

### Task 3.2.6a: Implement Dead Man's Switch

**File:** `src/core/risk/dead_mans_switch.py`

**Purpose:** Auto-close positions if system stops responding (PRD Feature C).

**Design:** Separate from Kill Switch
- Kill Switch: Manual or auto-trigger based on losses
- Dead Man's Switch: Triggers if SYSTEM becomes unresponsive

```python
from datetime import datetime, timedelta, timezone
from typing import Optional
import asyncio

class DeadMansSwitchTriggered(Exception):
    """Exception raised when dead man's switch triggers."""
    pass

class DeadMansSwitch:
    """
    Auto-close if system stops responding per PRD Feature C.

    Heartbeat-based mechanism:
    - Orchestrator records heartbeat every cycle
    - External watchdog checks heartbeat every 5 minutes
    - If 6 missed heartbeats (30 minutes), trigger
    - Sequence: warn (Telegram) → wait 60s → close all positions → raise exception
    """

    HEARTBEAT_INTERVAL_MINUTES = 5
    MAX_MISSED_HEARTBEATS = 6  # 30 minutes total
    WARNING_BEFORE_CLOSE_SECONDS = 60

    def __init__(
        self,
        data_store: Any,
        alert_manager: Any,
        execution_engine: Optional[Any] = None
    ) -> None:
        self.data_store = data_store
        self.alert_manager = alert_manager
        self.execution_engine = execution_engine
        self._last_heartbeat = datetime.now(timezone.utc)
        self._missed_count = 0
        self._triggered = False

    async def record_heartbeat(self) -> None:
        """
        Record that system is alive and responsive.

        Called by orchestrator main loop every cycle.
        """
        self._last_heartbeat = datetime.now(timezone.utc)
        self._missed_count = 0

        # Persist to database for external watchdog
        await self.data_store.update_system_state(
            'dead_mans_switch_heartbeat',
            self._last_heartbeat.isoformat()
        )

    def check_heartbeat(self) -> bool:
        """
        Check if heartbeat is still active.

        Called by external watchdog process.

        Returns:
            True if system is healthy, False if too many missed beats
        """
        elapsed = datetime.now(timezone.utc) - self._last_heartbeat
        max_elapsed = timedelta(minutes=self.HEARTBEAT_INTERVAL_MINUTES)

        if elapsed > max_elapsed:
            self._missed_count += 1
            return self._missed_count < self.MAX_MISSED_HEARTBEATS
        return True

    async def trigger(self, reason: str = "System unresponsive") -> None:
        """
        Close all positions and require manual restart.

        Sequence:
        1. Send Telegram warning (1 minute before closing)
        2. Wait 1 minute for operator intervention
        3. Close all positions with market orders
        4. Mark as triggered
        5. Raise exception to stop system
        """
        import logging
        logger = logging.getLogger(__name__)

        if self._triggered:
            return

        # Send warning
        await self.alert_manager.send_critical(
            title="⚠️ DEAD MAN'S SWITCH - WARNING",
            message=(
                f"System unresponsive for {self._missed_count * self.HEARTBEAT_INTERVAL_MINUTES} minutes. "
                f"All positions will be closed in {self.WARNING_BEFORE_CLOSE_SECONDS} seconds. "
                f"Reason: {reason}. "
                f"Manual restart required."
            )
        )

        logger.warning(
            "dead_mans_switch_warning",
            extra={"missed_heartbeats": self._missed_count, "reason": reason}
        )

        # Wait before closing
        await asyncio.sleep(self.WARNING_BEFORE_CLOSE_SECONDS)

        # Close all positions
        try:
            await self._close_all_positions()
        except Exception as e:
            logger.error("Failed to close positions", extra={"error": str(e)})

        # Send final alert
        await self.alert_manager.send_critical(
            title="🛑 DEAD MAN'S SWITCH TRIGGERED",
            message="All positions closed. Manual restart required."
        )

        self._triggered = True
        logger.critical("dead_mans_switch_triggered")

        raise DeadMansSwitchTriggered(reason)

    async def _close_all_positions(self) -> None:
        """Close all open positions with market orders."""
        # Stub - requires Phase 4 execution engine
        import logging
        logger = logging.getLogger(__name__)

        logger.info("dead_mans_switch_close_all_positions_stub")

    @property
    def is_triggered(self) -> bool:
        """Check if dead man's switch has been triggered."""
        return self._triggered
```

**Acceptance Criteria:**
- [ ] Heartbeat recorded in orchestrator
- [ ] Watchdog detects missed heartbeats
- [ ] Telegram warning sent 1 minute before close
- [ ] All positions closed with market orders
- [ ] Manual restart required after trigger
- [ ] State persisted to database

---

## PRODUCTION QUALITY GATES

### Automated Quality Checks (Must PASS)

```bash
# 1. Type Safety (Strict Mode)
mypy src/core/risk/ --strict
# RESULT: Must show "Success: no issues found"

# 2. Code Linting
ruff check src/core/risk/
# RESULT: Must output nothing (0 violations)

# 3. Import Organization
isort src/core/risk/ --check --diff
# RESULT: Must show "All done! No files would be modified"

# 4. Test Execution
pytest tests/unit/test_risk_controller.py tests/unit/test_kill_switch.py -v
# RESULT: Must show "passed" for ALL tests, no failures

# 5. Coverage Report
pytest tests/unit/test_risk_controller.py tests/unit/test_kill_switch.py \
  --cov=src/core/risk --cov-report=term-missing
# RESULT: All files >90%, TOTAL >90%

# 6. Production Audit
@production-code-audit audit src/core/risk/
# RESULT: Grade A- or higher, no CRITICAL or HIGH issues
```

### Code Quality Standards (MANDATORY)

- ✅ **Type Hints:** 100% coverage (all functions/methods typed)
- ✅ **Input Validation:** All numeric fields checked for NaN/Infinity
- ✅ **Imports:** Strict organization (stdlib → third-party → local)
- ✅ **Naming:** Zero synonyms (consistent across all files)
- ✅ **Docstrings:** All public methods documented
- ✅ **Logging:** Structured logging for all decisions
- ✅ **Tests:** >90% coverage per file, critical paths fully tested

---

## DECISION CONSISTENCY

**BEFORE STARTING:** Read `.claude/DECISIONS.md` and verify these decisions are relevant:

- DEC-2026-02-08-002: SQLAlchemy 2.0 with Mapped[T]
- DEC-2026-02-08-003: Timezone-aware datetimes
- DEC-2026-02-08-006: Type hints 100%
- DEC-2026-02-08-007: Input validation at model layer
- DEC-2026-02-08-008: Structured logging
- DEC-2026-02-08-010: Lambda functions for mutable defaults

**AFTER COMPLETION:** Verify all decisions were followed and document any NEW decisions made.

---

## DELIVERABLES

**Session 3A Complete When:**

```
[✅] Type Safety: mypy --strict passes (0 errors)
[✅] Code Quality: ruff check passes (0 violations)
[✅] Imports: isort passes (0 changes needed)
[✅] Tests: All pass (pytest shows 100% pass rate)
[✅] Coverage: >90% per file, >90% total
[✅] Production Audit: Grade A- or higher
[✅] Risk checks enforce all limits correctly
[✅] Kill switch activates in <1 second
[✅] Kill switch state persists across restarts
[✅] All decisions documented and followed

OVERALL: ✅ PRODUCTION READY FOR SESSION 3B
```

---

**Prompt Version:** 1.0
**Last Updated:** 2026-02-12
**Model Recommended:** Opus (financial logic complexity)
**Estimated Duration:** 32 hours
**Next:** SESSION_3B_IMPLEMENTATION_PROMPT.md (Circuit Breakers + Volatility)
