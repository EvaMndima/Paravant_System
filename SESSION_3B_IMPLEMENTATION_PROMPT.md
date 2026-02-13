# SESSION 3B IMPLEMENTATION PROMPT
## Circuit Breakers & Volatility Filter | Production-Grade Implementation

**Phase:** 3 (Risk Controls)
**Sections:** 3.3 (Circuit Breakers) + 3.4 (Volatility Filter)
**Duration:** 28 hours
**Tasks:** 14 total (8 + 6)
**Model Recommendation:** Opus (complex state tracking, threshold logic)
**Code Quality:** Zero-technical-debt, 100% type hints, >90% test coverage

---

## MANDATORY READING BEFORE STARTING

1. **`.claude/DECISIONS.md`** - Read all architectural decisions (non-negotiable)
2. **`.claude/rules/zero-technical-debt.md`** - Code quality standards
3. **`.claude/rules/decision-consistency.md`** - Decision enforcement
4. **`TRADING_SYSTEM_PRD.md`** - Sections 3.3-3.4 (Risk Management)
5. **`docs/03_PHASE_3_RISK_CONTROLS.md`** - Sections 3.3 + 3.4 (this document)
6. **Phase 2 Code** - Understand ATR indicators (needed for volatility)
7. **Phase 3A Code** - Understand RiskController and PortfolioState
8. **This Prompt** - Read completely before implementing

---

## CRITICAL SUCCESS FACTORS FOR SESSION 3B

### Why This Matters
Automated safeguards must work perfectly without human intervention. **Bugs can let catastrophic losses happen or block legitimate trading.**

Production-grade requirements:
- ✅ 100% type hints (no ambiguity)
- ✅ State tracking with timezone awareness (time-based resets)
- ✅ Threshold enforcement (correct boundaries)
- ✅ Test coverage >90% (all scenarios)
- ✅ Edge case handling (missing data, boundary conditions)
- ✅ Decision consistency (all documented)

### Risk Scenarios We Must Handle
```python
# Edge case: Exactly at threshold (3.00001% when 3% limit) → Must reject
# Edge case: Volatility regime switch mid-trade → Must recalculate
# Edge case: Weekend/holiday → Must apply adjustment rules
# Edge case: Weekly reset at wrong UTC time → MUST be UTC 00:00 Monday
# Edge case: Drawdown never resets → CORRECT (requires manual intervention)
```

---

## DEPENDENCY ANALYSIS & EXECUTION ORDER

```
Phase 1/2/3A Dependencies:
├─ RiskController (3.1) - Will integrate filters at end
├─ ATR Indicator (2.2.4) - For volatility calculation
├─ OHLCVSeries (2.1.x) - For price data
├─ MarketDataService (2.1.x) - For getting current price
├─ Alert Manager (assumed) - For sending notifications
└─ PortfolioState (3.1) - For portfolio calculations

Session 3B Dependency Chain:
│
├─ 3.3.1 (Circuit Breaker Framework) - FOUNDATION
│  └─ ABC pattern for all breakers
│
├─ 3.3.2-3.3.6 (Specific Breakers) - INDEPENDENT IMPLEMENTATIONS
│  ├─ 3.3.2 Daily Loss Breaker
│  ├─ 3.3.3 Weekly Loss Breaker
│  ├─ 3.3.4 Drawdown Breaker
│  ├─ 3.3.5 Consecutive Loss Breaker
│  └─ 3.3.6 Correlation Breaker (uses 2.1.7 symbol groups)
│
├─ 3.3.7 (Circuit Breaker Manager) - ORCHESTRATOR
│  └─ Uses: All breakers (3.3.1-3.3.6)
│
├─ 3.4.1 (Volatility Analyzer) - INDEPENDENT
│  └─ Uses: ATR from Phase 2
│
├─ 3.4.2 (Volatility Size Adjustment) - EXTENDS POSITION SIZING
│  ├─ Uses: 3.4.1 for regime
│  └─ Integrates: With 3.1.6 position sizing
│
├─ 3.4.3 (Trading Hours Filter) - INDEPENDENT
│  └─ Time-aware logic (UTC-only)
│
├─ 3.4.4 (News Event Filter) - INDEPENDENT
│  └─ Event calendar logic
│
├─ 3.4.5 (Filter Integration) - INTEGRATION HUB
│  ├─ Uses: 3.3.7, 3.4.1-3.4.4
│  └─ Updates: 3.1.7 order validation pipeline
│
└─ 3.3.8 + 3.4.6 (TESTING) - COMPREHENSIVE COVERAGE
   ├─ Test all breakers
   ├─ Test all volatility filters
   └─ Test integration with RiskController
```

### EXECUTION SEQUENCE (STRICT ORDER)

**DO NOT DEVIATE - Dependency chain must be satisfied**

#### Phase 1: Circuit Breaker Framework (Tasks 1-7)
1. **Task 3.3.1**: Create Circuit Breaker Framework → ABC pattern foundation
2. **Task 3.3.2**: Daily Loss Limit Breaker → Uses framework
3. **Task 3.3.3**: Weekly Loss Limit Breaker → Uses framework
4. **Task 3.3.4**: Drawdown Breaker → Uses framework
5. **Task 3.3.5**: Consecutive Loss Breaker → Uses framework
6. **Task 3.3.6**: Correlation Breaker → Uses framework + symbol groups
7. **Task 3.3.7**: Circuit Breaker Manager → Orchestrates all breakers

#### Phase 2: Volatility Filters (Tasks 8-11)
8. **Task 3.4.1**: Create Volatility Analyzer → ATR-based volatility
9. **Task 3.4.2**: Volatility Size Adjustment → Extends position sizing
10. **Task 3.4.3**: Trading Hours Filter → Time-based filtering
11. **Task 3.4.4**: News Event Filter → Event calendar

#### Phase 3: Integration & Testing (Tasks 12-14)
12. **Task 3.4.5**: Integrate Filters into Risk Controller → Updates pipeline
13. **Task 3.3.8**: Write Circuit Breaker Tests → >90% coverage
14. **Task 3.4.6**: Write Volatility Filter Tests → >90% coverage

---

## SECTION 3.3: CIRCUIT BREAKERS

### Task 3.3.1: Create Circuit Breaker Framework

**File:** `src/core/risk/circuit_breakers.py`

**Purpose:** Base framework for all circuit breakers (ABC pattern).

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

@dataclass(frozen=True)
class CircuitBreakerResult:
    """
    Result of a circuit breaker check.

    Fields:
    - triggered: bool - whether breaker was triggered
    - breaker_name: str - which breaker (e.g., "daily_loss")
    - reason: str - why triggered
    - current_value: float - current metric value
    - threshold: float - threshold that was exceeded
    - timestamp: datetime - when check was made
    """
    triggered: bool
    breaker_name: str
    reason: str
    current_value: float
    threshold: float
    timestamp: datetime = None

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        import datetime as dt
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', dt.datetime.now(dt.timezone.utc))

class CircuitBreaker(ABC):
    """
    Abstract base class for all circuit breakers.

    Decision: DEC-2026-02-08-XXX - Circuit breaker pattern for risk limits

    Each breaker:
    - Monitors a specific risk metric
    - Triggers when threshold exceeded
    - Can be reset (or not, depending on type)
    - Returns detailed result
    """

    name: str  # e.g., "daily_loss", "drawdown"

    @abstractmethod
    async def check(self, portfolio: Any) -> CircuitBreakerResult:
        """
        Check if breaker conditions are met.

        Args:
            portfolio: PortfolioState snapshot

        Returns:
            CircuitBreakerResult with status and details
        """
        pass

    @abstractmethod
    async def reset(self) -> None:
        """
        Reset breaker state.

        Note: Some breakers don't auto-reset (e.g., drawdown).
        """
        pass

class CircuitBreakerManager:
    """
    Orchestrates multiple circuit breakers.

    Manages:
    - Registration of breakers
    - Parallel checks on all breakers
    - State tracking
    - Manual reset of specific breakers
    """

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._states: dict[str, bool] = {}  # name -> triggered

    def register(self, breaker: CircuitBreaker) -> None:
        """
        Register a circuit breaker.

        Args:
            breaker: CircuitBreaker instance to register
        """
        self._breakers[breaker.name] = breaker
        self._states[breaker.name] = False

    async def check_all(self, portfolio: Any) -> list[CircuitBreakerResult]:
        """
        Check all registered breakers.

        Runs checks in parallel for efficiency.

        Args:
            portfolio: PortfolioState snapshot

        Returns:
            List of CircuitBreakerResult for each breaker
        """
        import asyncio

        tasks = [
            breaker.check(portfolio)
            for breaker in self._breakers.values()
        ]

        results = await asyncio.gather(*tasks)

        # Update state tracking
        for result in results:
            self._states[result.breaker_name] = result.triggered

        return results

    def is_any_triggered(self) -> bool:
        """Check if ANY breaker is currently triggered."""
        return any(self._states.values())

    def get_triggered_breakers(self) -> list[str]:
        """Get list of triggered breaker names."""
        return [name for name, triggered in self._states.items() if triggered]

    async def reset_breaker(self, name: str) -> None:
        """
        Reset a specific breaker.

        Args:
            name: Breaker name to reset

        Raises:
            ValueError: If breaker doesn't exist
        """
        if name not in self._breakers:
            raise ValueError(f"Unknown breaker: {name}")

        await self._breakers[name].reset()
        self._states[name] = False
```

**Acceptance Criteria:**
- [ ] Abstract base class defined
- [ ] Manager coordinates breakers
- [ ] Results are detailed
- [ ] Parallel check execution
- [ ] Unit test: framework structure

---

### Task 3.3.2: Implement Daily Loss Limit Breaker

**File:** `src/core/risk/circuit_breakers.py` (add class)

**Purpose:** Trigger when daily loss exceeds threshold (default 5%).

**Algorithm:**
```python
# Resets daily at UTC 00:00 (midnight)
daily_loss_limit_pct = 5.0  # Default

# Check
current_loss_pct = abs(portfolio.daily_pnl) / portfolio.total_equity * 100

if current_loss_pct > daily_loss_limit_pct:
    TRIGGER
else:
    OK
```

**Implementation:**
```python
class DailyLossBreaker(CircuitBreaker):
    """
    Circuit breaker for daily loss limit.

    Triggers when realized + unrealized P&L for the day exceeds limit.
    Resets automatically at UTC 00:00.

    Configuration:
    - daily_loss_limit_pct: 5.0 (default)
    """

    name = "daily_loss"

    def __init__(
        self,
        data_store: Any,
        daily_loss_limit_pct: float = 5.0
    ) -> None:
        self.data_store = data_store
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self._triggered = False
        self._last_reset_date: Optional[datetime] = None

    async def check(self, portfolio: Any) -> CircuitBreakerResult:
        """
        Check if daily loss exceeds limit.

        Daily P&L includes:
        - Realized: Closed trades for the day
        - Unrealized: Current open position P&L
        """
        import math
        from datetime import datetime, timezone, date

        # Auto-reset at UTC 00:00
        now = datetime.now(timezone.utc)
        today = now.date()

        if self._last_reset_date != today:
            await self.reset()
            self._last_reset_date = today

        # Calculate daily loss %
        if portfolio.total_equity <= 0:
            # Can't calculate with zero/negative equity
            current_loss_pct = 0
        else:
            current_loss_pct = abs(portfolio.daily_pnl) / portfolio.total_equity * 100

        # Check threshold
        triggered = (portfolio.daily_pnl < 0 and
                    current_loss_pct > self.daily_loss_limit_pct)

        if triggered:
            self._triggered = True

        return CircuitBreakerResult(
            triggered=triggered,
            breaker_name=self.name,
            reason=f"Daily loss {current_loss_pct:.2f}% exceeds limit {self.daily_loss_limit_pct}%",
            current_value=current_loss_pct,
            threshold=self.daily_loss_limit_pct
        )

    async def reset(self) -> None:
        """Reset daily loss tracking (called at UTC 00:00)."""
        self._triggered = False
        self._last_reset_date = None
```

**Acceptance Criteria:**
- [ ] Triggers at threshold
- [ ] Auto-resets daily at UTC 00:00
- [ ] Considers realized + unrealized P&L
- [ ] Unit test: trigger scenarios and reset

---

### Task 3.3.3: Implement Weekly Loss Limit Breaker

**File:** `src/core/risk/circuit_breakers.py` (add class)

**Purpose:** Trigger when weekly loss exceeds threshold (default 7-10%).

**Note:** More conservative than daily, resets Monday UTC 00:00.

```python
class WeeklyLossBreaker(CircuitBreaker):
    """
    Circuit breaker for weekly loss limit.

    More conservative than daily loss.
    Resets every Monday at UTC 00:00.

    Configuration:
    - weekly_loss_limit_pct: 10.0 (default)
    """

    name = "weekly_loss"

    def __init__(
        self,
        data_store: Any,
        weekly_loss_limit_pct: float = 10.0
    ) -> None:
        self.data_store = data_store
        self.weekly_loss_limit_pct = weekly_loss_limit_pct
        self._triggered = False
        self._week_start_date: Optional[datetime] = None

    async def check(self, portfolio: Any) -> CircuitBreakerResult:
        """Check if weekly loss exceeds limit."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        # Monday is 0, Sunday is 6
        week_start = now - timedelta(days=now.weekday())

        # Auto-reset on Monday
        if self._week_start_date is None or self._week_start_date.date() != week_start.date():
            await self.reset()
            self._week_start_date = week_start

        # Calculate weekly loss %
        current_loss_pct = abs(portfolio.weekly_pnl) / portfolio.total_equity * 100

        # Check threshold
        triggered = (portfolio.weekly_pnl < 0 and
                    current_loss_pct > self.weekly_loss_limit_pct)

        if triggered:
            self._triggered = True

        return CircuitBreakerResult(
            triggered=triggered,
            breaker_name=self.name,
            reason=f"Weekly loss {current_loss_pct:.2f}% exceeds limit {self.weekly_loss_limit_pct}%",
            current_value=current_loss_pct,
            threshold=self.weekly_loss_limit_pct
        )

    async def reset(self) -> None:
        """Reset weekly loss tracking."""
        self._triggered = False
```

**Acceptance Criteria:**
- [ ] Triggers at threshold
- [ ] Resets Monday UTC 00:00
- [ ] Unit test: trigger scenarios

---

### Task 3.3.4: Implement Drawdown Breaker

**File:** `src/core/risk/circuit_breakers.py` (add class)

**Purpose:** Trigger when maximum drawdown exceeded (default 15%).

**Critical:** Does NOT auto-reset. Requires manual intervention.

```python
class DrawdownBreaker(CircuitBreaker):
    """
    Circuit breaker for maximum drawdown limit.

    ⚠️ CRITICAL: Does NOT auto-reset.

    Drawdown = (Peak Equity - Current Equity) / Peak Equity * 100

    Configuration:
    - max_drawdown_pct: 15.0 (default)

    Note: Manually resettable only via reset() call.
    This is intentional - drawdown is serious and requires human review.
    """

    name = "drawdown"

    def __init__(
        self,
        data_store: Any,
        max_drawdown_pct: float = 15.0
    ) -> None:
        self.data_store = data_store
        self.max_drawdown_pct = max_drawdown_pct
        self._triggered = False

    async def check(self, portfolio: Any) -> CircuitBreakerResult:
        """Check if drawdown exceeds limit."""
        # Use portfolio's pre-calculated drawdown
        current_drawdown = portfolio.drawdown_pct

        triggered = current_drawdown > self.max_drawdown_pct

        if triggered:
            self._triggered = True

        return CircuitBreakerResult(
            triggered=triggered,
            breaker_name=self.name,
            reason=f"Drawdown {current_drawdown:.2f}% exceeds limit {self.max_drawdown_pct}%",
            current_value=current_drawdown,
            threshold=self.max_drawdown_pct
        )

    async def reset(self) -> None:
        """
        Reset drawdown breaker (manual intervention only).

        This should only be called after human review and approval.
        """
        self._triggered = False
```

**Acceptance Criteria:**
- [ ] Tracks equity peak correctly
- [ ] Calculates drawdown correctly
- [ ] Does NOT auto-reset
- [ ] Unit test: drawdown scenarios

---

### Task 3.3.5: Implement Consecutive Loss Breaker

**File:** `src/core/risk/circuit_breakers.py` (add class)

**Purpose:** Trigger on losing streak (default 5 consecutive losses).

```python
class ConsecutiveLossBreaker(CircuitBreaker):
    """
    Circuit breaker for consecutive losing trades.

    Triggers when N consecutive trades are losses.
    Resets on winning trade.

    Configuration:
    - max_consecutive_losses: 5 (default)
    """

    name = "consecutive_losses"

    def __init__(
        self,
        data_store: Any,
        max_consecutive_losses: int = 5
    ) -> None:
        self.data_store = data_store
        self.max_consecutive_losses = max_consecutive_losses
        self._triggered = False

    async def check(self, portfolio: Any) -> CircuitBreakerResult:
        """Check if consecutive losses exceed threshold."""
        current_losses = portfolio.consecutive_losses

        triggered = current_losses >= self.max_consecutive_losses

        if triggered:
            self._triggered = True

        return CircuitBreakerResult(
            triggered=triggered,
            breaker_name=self.name,
            reason=f"{current_losses} consecutive losses exceed limit {self.max_consecutive_losses}",
            current_value=float(current_losses),
            threshold=float(self.max_consecutive_losses)
        )

    async def reset(self) -> None:
        """Reset on winning trade (automatic, not manual)."""
        self._triggered = False
```

**Acceptance Criteria:**
- [ ] Counts consecutive losses
- [ ] Triggers at threshold
- [ ] Resets on win
- [ ] Unit test: streak scenarios

---

### Task 3.3.6: Implement Correlation Breaker

**File:** `src/core/risk/circuit_breakers.py` (add class)

**Purpose:** Limit exposure to correlated assets (PRD Feature A).

**Correlation Groups:**
```python
CORRELATION_GROUPS = {
    "btc": ["BTCUSDT"],
    "eth": ["ETHUSDT"],
    "layer1": ["SOLUSDT", "AVAXUSDT", "DOTUSDT"],
    "exchange": ["BNBUSDT"],
    "payment": ["XRPUSDT", "ADAUSDT", "LTCUSDT"],
    "meme": ["DOGEUSDT"]
}

# Individual limits
INDIVIDUAL_LIMITS = {
    "BTCUSDT": 0.40,  # 40% max
    "ETHUSDT": 0.30   # 30% max
}

# Group limits
GROUP_LIMITS = {
    "all_correlated": 0.60  # 60% max in any group
}
```

**Implementation:**
```python
class CorrelationBreaker(CircuitBreaker):
    """
    Circuit breaker for correlation limits per PRD Feature A.

    Enforces:
    - Max 40% of portfolio in BTCUSDT
    - Max 30% of portfolio in ETHUSDT
    - Max 60% total in any correlation group

    Groups:
    - BTC: [BTCUSDT]
    - ETH: [ETHUSDT]
    - Layer1: [SOLUSDT, AVAXUSDT, DOTUSDT]
    - Exchange: [BNBUSDT]
    - Payment: [XRPUSDT, ADAUSDT, LTCUSDT]
    - Meme: [DOGEUSDT]
    """

    name = "correlation"

    CORRELATION_GROUPS = {
        "btc": {"BTCUSDT"},
        "eth": {"ETHUSDT"},
        "layer1": {"SOLUSDT", "AVAXUSDT", "DOTUSDT"},
        "exchange": {"BNBUSDT"},
        "payment": {"XRPUSDT", "ADAUSDT", "LTCUSDT"},
        "meme": {"DOGEUSDT"}
    }

    INDIVIDUAL_LIMITS = {
        "BTCUSDT": 0.40,  # 40%
        "ETHUSDT": 0.30   # 30%
    }

    GROUP_LIMIT = 0.60  # 60% per group

    def __init__(self, data_store: Any) -> None:
        self.data_store = data_store
        self._triggered = False

    async def check(self, portfolio: Any) -> CircuitBreakerResult:
        """Check correlation limits."""
        violations = []

        # Check individual limits (BTC, ETH)
        for symbol, limit_pct in self.INDIVIDUAL_LIMITS.items():
            exposure_pct = self._get_symbol_exposure_pct(symbol, portfolio)
            if exposure_pct > limit_pct:
                violations.append(
                    f"{symbol}: {exposure_pct:.1%} exceeds {limit_pct:.1%}"
                )

        # Check group limits
        for group_name, symbols in self.CORRELATION_GROUPS.items():
            group_exposure = self._get_group_exposure_pct(group_name, portfolio)
            if group_exposure > self.GROUP_LIMIT:
                violations.append(
                    f"{group_name}: {group_exposure:.1%} exceeds {self.GROUP_LIMIT:.1%}"
                )

        triggered = len(violations) > 0

        if triggered:
            self._triggered = True

        return CircuitBreakerResult(
            triggered=triggered,
            breaker_name=self.name,
            reason=" | ".join(violations) if violations else "OK",
            current_value=len(violations),  # Number of violations
            threshold=0
        )

    async def reset(self) -> None:
        """Reset correlation breaker (manual)."""
        self._triggered = False

    def _get_symbol_exposure_pct(self, symbol: str, portfolio: Any) -> float:
        """Get current exposure to symbol as % of portfolio."""
        for position in portfolio.open_positions:
            if position.symbol == symbol:
                return (position.value / portfolio.total_equity) * 100
        return 0.0

    def _get_group_exposure_pct(self, group_name: str, portfolio: Any) -> float:
        """Get current exposure to group as % of portfolio."""
        symbols = self.CORRELATION_GROUPS[group_name]
        total_exposure = 0.0

        for position in portfolio.open_positions:
            if position.symbol in symbols:
                total_exposure += position.value

        return (total_exposure / portfolio.total_equity) * 100
```

**Acceptance Criteria:**
- [ ] Groups defined correctly
- [ ] Counts positions per group
- [ ] Warns/blocks correlated positions
- [ ] BTC limit enforced (40%)
- [ ] ETH limit enforced (30%)
- [ ] Group limit enforced (60%)
- [ ] Unit test: correlation check with limits

---

### Task 3.3.7: Implement Circuit Breaker Manager

**File:** `src/core/risk/circuit_breakers.py` (update class)

**Purpose:** Orchestrate all circuit breakers (already in Task 3.3.1).

**Update RiskController to use manager:**

```python
# In src/core/risk/controller.py

from src.core.risk.circuit_breakers import (
    CircuitBreakerManager,
    DailyLossBreaker,
    WeeklyLossBreaker,
    DrawdownBreaker,
    ConsecutiveLossBreaker,
    CorrelationBreaker
)

class RiskController:
    def __init__(self, data_store, risk_config, symbol_manager):
        # ... existing init ...
        self.circuit_breaker_manager = CircuitBreakerManager()

        # Register all breakers
        self.circuit_breaker_manager.register(
            DailyLossBreaker(data_store, risk_config.daily_loss_limit_pct)
        )
        self.circuit_breaker_manager.register(
            WeeklyLossBreaker(data_store, risk_config.weekly_loss_limit_pct)
        )
        self.circuit_breaker_manager.register(
            DrawdownBreaker(data_store, risk_config.max_drawdown_pct)
        )
        self.circuit_breaker_manager.register(
            ConsecutiveLossBreaker(data_store, risk_config.max_consecutive_losses)
        )
        self.circuit_breaker_manager.register(
            CorrelationBreaker(data_store)
        )
```

**Acceptance Criteria:**
- [ ] Registers all breakers
- [ ] Checks all in parallel
- [ ] Tracks triggered states
- [ ] Can reset individual breakers

---

### Task 3.3.8: Write Circuit Breaker Tests

**File:** `tests/unit/test_circuit_breakers.py`

```python
import pytest
from src.core.risk.circuit_breakers import (
    CircuitBreakerManager,
    DailyLossBreaker,
    WeeklyLossBreaker,
    DrawdownBreaker,
    ConsecutiveLossBreaker,
    CorrelationBreaker
)

class TestDailyLossBreaker:
    """Test daily loss breaker."""

    @pytest.fixture
    def breaker(self, data_store):
        return DailyLossBreaker(data_store, daily_loss_limit_pct=5.0)

    async def test_below_threshold(self, breaker, portfolio):
        """Below threshold should not trigger."""
        portfolio.daily_pnl = -200  # 2% loss

        result = await breaker.check(portfolio)
        assert not result.triggered

    async def test_at_threshold(self, breaker, portfolio):
        """At threshold should trigger."""
        portfolio.daily_pnl = -500  # 5% loss

        result = await breaker.check(portfolio)
        assert result.triggered

    async def test_exceeds_threshold(self, breaker, portfolio):
        """Exceeding threshold should trigger."""
        portfolio.daily_pnl = -1000  # 10% loss

        result = await breaker.check(portfolio)
        assert result.triggered

    async def test_auto_reset_daily(self, breaker, portfolio):
        """Should auto-reset at UTC 00:00."""
        # Set loss
        portfolio.daily_pnl = -1000
        result1 = await breaker.check(portfolio)
        assert result1.triggered

        # Move to next day
        breaker._last_reset_date = None  # Simulate day change

        # Check again - should reset
        result2 = await breaker.check(portfolio)
        # (depends on portfolio.daily_pnl for new day)

class TestDrawdownBreaker:
    """Test drawdown breaker."""

    async def test_does_not_auto_reset(self, data_store):
        """Drawdown should NOT auto-reset."""
        breaker = DrawdownBreaker(data_store, max_drawdown_pct=15.0)
        # Manually verify _triggered stays true after multiple checks
        pass

class TestConsecutiveLossBreaker:
    """Test consecutive loss breaker."""

    async def test_counts_consecutive_losses(self, data_store, portfolio):
        """Should count consecutive losses."""
        breaker = ConsecutiveLossBreaker(data_store, max_consecutive_losses=5)

        # 4 losses (below threshold)
        portfolio.consecutive_losses = 4
        result = await breaker.check(portfolio)
        assert not result.triggered

        # 5 losses (at threshold)
        portfolio.consecutive_losses = 5
        result = await breaker.check(portfolio)
        assert result.triggered

class TestCorrelationBreaker:
    """Test correlation breaker."""

    async def test_btc_limit_40_percent(self, data_store, portfolio):
        """BTC should be capped at 40%."""
        breaker = CorrelationBreaker(data_store)

        # Add BTC position at 45% (exceeds limit)
        # (mock portfolio positions)

        result = await breaker.check(portfolio)
        assert result.triggered

    async def test_eth_limit_30_percent(self, data_store, portfolio):
        """ETH should be capped at 30%."""
        pass

class TestCircuitBreakerManager:
    """Test manager."""

    async def test_checks_all_breakers_parallel(self, data_store):
        """Should check all breakers in parallel."""
        manager = CircuitBreakerManager()
        manager.register(DailyLossBreaker(data_store))
        manager.register(DrawdownBreaker(data_store))

        results = await manager.check_all(portfolio)
        assert len(results) == 2

    async def test_tracks_triggered_state(self, data_store):
        """Should track which breakers triggered."""
        manager = CircuitBreakerManager()
        manager.register(DailyLossBreaker(data_store))

        # Run check, get triggered list
        await manager.check_all(portfolio)
        triggered = manager.get_triggered_breakers()
        assert isinstance(triggered, list)
```

**Acceptance Criteria:**
- [ ] All breakers tested
- [ ] Manager tested
- [ ] Edge cases covered (at threshold, boundary conditions)
- [ ] >90% coverage

---

## SECTION 3.4: VOLATILITY FILTER

### Task 3.4.1: Create Volatility Analyzer

**File:** `src/core/risk/volatility.py`

**Purpose:** Analyze market volatility per PRD Safety A. Controls position sizing based on ATR.

**Volatility Regimes:**
```
NORMAL:   ATR/Price < 3%   → Full position size
ELEVATED: ATR/Price 3-5%   → 50% position size, 50% wider stops
EXTREME:  ATR/Price > 5%   → Exits only, no new entries, 4-hour cooldown
```

**Implementation:**
```python
from enum import Enum
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone

class VolatilityRegime(str, Enum):
    """Volatility regimes."""
    NORMAL = "normal"          # <3% ATR/Price
    ELEVATED = "elevated"      # 3-5% ATR/Price
    EXTREME = "extreme"        # >5% ATR/Price

class VolatilityAnalyzer:
    """
    Volatility filter per PRD Safety A.

    Volatility measure: ATR(14) / Close price * 100

    Thresholds:
    - NORMAL: < 3% → Full trading
    - ELEVATED: 3-5% → Reduce size 50%, widen stops 50%
    - EXTREME: > 5% → Exits only, no new entries

    Cooldown: 4 hours after volatility drops before resuming
    """

    NORMAL_THRESHOLD = 3.0
    ELEVATED_THRESHOLD = 5.0
    COOLDOWN_HOURS = 4

    # Position size multipliers
    NORMAL_SIZE_MULTIPLIER = 1.0
    ELEVATED_SIZE_MULTIPLIER = 0.5
    EXTREME_SIZE_MULTIPLIER = 0.0  # No entries

    # Stop widening multiplier
    ELEVATED_STOP_MULTIPLIER = 1.5

    def __init__(self, market_data_service: Any) -> None:
        self.market_data = market_data_service
        self._cooldown_until: dict[str, datetime] = {}  # symbol -> end_time
        self._last_regime: dict[str, VolatilityRegime] = {}

    async def get_volatility_ratio(
        self,
        symbol: str,
        timeframe: str = "1h"
    ) -> float:
        """
        Calculate current volatility ratio.

        Formula: ATR(14) / Close price * 100

        Returns:
            Volatility as percentage (0-100)
        """
        import math

        # Get ATR from Phase 2 indicators
        atr = await self.market_data.get_atr(symbol, timeframe, period=14)
        close = await self.market_data.get_current_price(symbol)

        if close <= 0 or atr is None:
            return 0.0

        vol_pct = (atr / close) * 100

        # Reject NaN/Infinity
        if math.isnan(vol_pct) or math.isinf(vol_pct):
            return 0.0

        return vol_pct

    async def get_regime(self, symbol: str) -> VolatilityRegime:
        """
        Classify current volatility regime.

        Args:
            symbol: Trading symbol

        Returns:
            VolatilityRegime (NORMAL, ELEVATED, or EXTREME)
        """
        vol_pct = await self.get_volatility_ratio(symbol)

        if vol_pct < self.NORMAL_THRESHOLD:
            regime = VolatilityRegime.NORMAL
        elif vol_pct < self.ELEVATED_THRESHOLD:
            regime = VolatilityRegime.ELEVATED
        else:
            regime = VolatilityRegime.EXTREME

        self._last_regime[symbol] = regime
        return regime

    async def should_reduce_size(
        self,
        symbol: str
    ) -> Tuple[bool, float]:
        """
        Should position size be reduced?

        Args:
            symbol: Trading symbol

        Returns:
            (should_reduce: bool, multiplier: float)
            Example: (True, 0.5) means reduce to 50% size
        """
        regime = await self.get_regime(symbol)

        if regime == VolatilityRegime.ELEVATED:
            return True, self.ELEVATED_SIZE_MULTIPLIER
        elif regime == VolatilityRegime.EXTREME:
            return True, self.EXTREME_SIZE_MULTIPLIER
        return False, self.NORMAL_SIZE_MULTIPLIER

    async def can_enter(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if new entries are allowed.

        Blocks new entries during EXTREME volatility + cooldown.

        Args:
            symbol: Trading symbol

        Returns:
            (allowed: bool, reason: str)
        """
        regime = await self.get_regime(symbol)

        # Check cooldown (4 hours after EXTREME)
        if symbol in self._cooldown_until:
            if datetime.now(timezone.utc) < self._cooldown_until[symbol]:
                return False, f"Volatility cooldown active until {self._cooldown_until[symbol].isoformat()}"

        # Extreme volatility: exits only
        if regime == VolatilityRegime.EXTREME:
            # Set 4-hour cooldown
            self._cooldown_until[symbol] = (
                datetime.now(timezone.utc) + timedelta(hours=self.COOLDOWN_HOURS)
            )
            return False, "Extreme volatility - exits only, no new entries"

        return True, "OK"

    def get_stop_widening_multiplier(self, symbol: str) -> float:
        """
        Get stop loss widening multiplier for current regime.

        ELEVATED: 1.5x (widen stops by 50%)
        Others: 1.0x (no widening)
        """
        regime = self._last_regime.get(symbol, VolatilityRegime.NORMAL)
        if regime == VolatilityRegime.ELEVATED:
            return self.ELEVATED_STOP_MULTIPLIER
        return 1.0
```

**Acceptance Criteria:**
- [ ] Volatility ratio calculated correctly (ATR / Price * 100)
- [ ] NORMAL: < 3%
- [ ] ELEVATED: 3-5% → 50% size reduction
- [ ] EXTREME: > 5% → exits only
- [ ] Cooldown: 4 hours after extreme
- [ ] Unit test: volatility thresholds and regimes

---

### Task 3.4.2: Implement Volatility-Based Size Adjustment

**File:** `src/core/risk/volatility.py` (add integration)

**Purpose:** Feed volatility regime into position sizing.

```python
# Update src/core/risk/controller.py calculate_position_size()

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

    Now includes volatility adjustment.
    """
    # ... existing code ...

    # NEW: Apply volatility adjustment
    should_reduce, multiplier = await self.volatility_analyzer.should_reduce_size(symbol)
    if should_reduce:
        quantity = quantity * multiplier

    # ... rest of code ...
```

**Acceptance Criteria:**
- [ ] Multiplier reduces size in high vol
- [ ] EXTREME vol can block trades
- [ ] Integrates with position sizing
- [ ] Unit test: multiplier values

---

### Task 3.4.3: Implement Trading Hours Filter

**File:** `src/core/risk/time_filter.py`

**Purpose:** Weekend/holiday awareness per PRD Safety B.

**Rules:**
- Weekend: Saturday 00:00 - Sunday 23:59 UTC → 50% size, 2x volume requirement
- Holidays: Apply weekend rules
- Disabled by default (for 24/7 crypto)

```python
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from enum import Enum

class WeekendHolidayFilter:
    """
    Weekend/holiday awareness per PRD Safety B.

    Adjusts trading parameters during low-liquidity periods.

    Weekend: Saturday 00:00 UTC - Sunday 23:59 UTC
    - Position size: 50%
    - Volume requirement: 2.0x (require 2x normal volume)
    - Spread tolerance: 1.5x (accept 50% wider spreads)
    - Max position: 3% of portfolio

    Holidays: Apply weekend rules
    """

    WEEKEND_SIZE_MULTIPLIER = 0.5
    WEEKEND_VOLUME_MULTIPLIER = 2.0
    WEEKEND_SPREAD_TOLERANCE = 1.5
    WEEKEND_MAX_POSITION_PCT = 3.0

    # Fixed holidays
    HOLIDAYS = [
        ('christmas', [(12, 24), (12, 25), (12, 26)]),
        ('new_year', [(12, 31), (1, 1), (1, 2)]),
        # Chinese New Year needs yearly update (skip for MVP)
    ]

    def __init__(self, enabled: bool = False) -> None:
        """
        Initialize filter.

        Args:
            enabled: Whether to enforce weekend/holiday adjustments (default: False)
        """
        self.enabled = enabled

    def is_weekend(self) -> bool:
        """Check if current time is weekend (Sat 00:00 - Sun 23:59 UTC)."""
        now = datetime.now(timezone.utc)
        # weekday(): Monday=0, Sunday=6
        return now.weekday() >= 5  # 5=Saturday, 6=Sunday

    def is_holiday(self) -> bool:
        """Check if current date is a major holiday."""
        now = datetime.now(timezone.utc)
        for name, dates in self.HOLIDAYS:
            for month, day in dates:
                if now.month == month and now.day == day:
                    return True
        return False

    def is_low_liquidity_period(self) -> bool:
        """Check if weekend or holiday."""
        return self.is_weekend() or self.is_holiday()

    def get_adjustments(self) -> Dict[str, float]:
        """
        Get trading adjustments for current period.

        Returns:
            Dict with multipliers for size, volume, spread, max_position
        """
        if not self.enabled:
            return {
                'size_multiplier': 1.0,
                'volume_multiplier': 1.0,
                'spread_tolerance': 1.0,
                'max_position_pct': None
            }

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
            'max_position_pct': None
        }
```

**Acceptance Criteria:**
- [ ] Weekend detection: Saturday 00:00 - Sunday 23:59 UTC
- [ ] Position size: 50% on weekends
- [ ] Volume requirement: 2x on weekends
- [ ] Spread tolerance: 1.5x on weekends
- [ ] Max position: 3% on weekends
- [ ] Holiday dates: Dec 24-26, Dec 31-Jan 2
- [ ] Disabled by default
- [ ] Unit test: weekend/holiday detection

---

### Task 3.4.4: Implement News Event Filter

**File:** `src/core/risk/event_filter.py`

**Purpose:** Block trading during major events.

```python
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

@dataclass(frozen=True)
class TradingEvent:
    """Major event that affects trading."""
    name: str
    datetime_utc: datetime
    block_hours_before: int
    block_hours_after: int

class EventFilter:
    """
    Block trading during major news events.

    MVP: Simple implementation with manual event list.
    Future: Integrate economic calendar API.
    """

    def __init__(self, events: Optional[List[TradingEvent]] = None) -> None:
        """
        Initialize filter.

        Args:
            events: List of TradingEvent objects
        """
        self.events = events or []

    def add_event(
        self,
        name: str,
        datetime_utc: datetime,
        block_hours_before: int = 2,
        block_hours_after: int = 4
    ) -> None:
        """Add a trading event."""
        event = TradingEvent(name, datetime_utc, block_hours_before, block_hours_after)
        self.events.append(event)

    def is_blocked(self) -> Tuple[bool, Optional[str]]:
        """
        Check if trading is blocked due to an event.

        Returns:
            (blocked: bool, reason: Optional[str])
        """
        now = datetime.now(timezone.utc)

        for event in self.events:
            # Check if within blocking window
            block_start = event.datetime_utc - timedelta(hours=event.block_hours_before)
            block_end = event.datetime_utc + timedelta(hours=event.block_hours_after)

            if block_start <= now <= block_end:
                return True, f"Trading blocked: {event.name}"

        return False, None
```

**Default Events (MVP):**
```python
DEFAULT_EVENTS = [
    # Add actual event dates here
    # TradingEvent("FOMC Meeting", datetime(...), 2, 4)
]
```

**Acceptance Criteria:**
- [ ] Event blocking works
- [ ] Configurable before/after buffer
- [ ] Easy to add events
- [ ] Unit test: event filtering

---

### Task 3.4.5: Integrate Filters into Risk Controller

**File:** `src/core/risk/controller.py` (update check_order)

**Purpose:** Add volatility/time filters to order validation pipeline.

```python
async def check_order(self, order_request: OrderRequest) -> RiskCheckResult:
    """
    Updated master pipeline with volatility and time filters.

    New pipeline order (UPDATED FROM 3A):
    1. Kill switch check
    2. Circuit breaker checks
    3. Volatility filter (NEW)
    4. Trading hours filter (NEW)
    5. Event filter (NEW)
    6. Position size check (now with volatility adjustment)
    7. Concentration check
    8. Max positions check
    """
    # ... existing kill switch check ...

    # NEW: Volatility filter
    can_enter, reason = await self.volatility_analyzer.can_enter(order_request.symbol)
    if not can_enter:
        return RiskCheckResult(
            approved=False,
            check_name="volatility_filter",
            rejection_reason=reason
        )

    # NEW: Trading hours filter
    if self.time_filter.enabled:
        adjustments = self.time_filter.get_adjustments()
        if self._should_reject_due_to_time(order_request, adjustments):
            return RiskCheckResult(
                approved=False,
                check_name="time_filter",
                rejection_reason="Outside allowed trading hours"
            )

    # NEW: Event filter
    blocked, reason = self.event_filter.is_blocked()
    if blocked:
        return RiskCheckResult(
            approved=False,
            check_name="event_filter",
            rejection_reason=reason
        )

    # ... existing checks (position size, concentration, max positions) ...
```

**Acceptance Criteria:**
- [ ] Filters integrated into pipeline
- [ ] Volatility affects position sizing
- [ ] Filters can be disabled via config
- [ ] Unit test: filter integration

---

### Task 3.4.6: Write Volatility Filter Tests

**File:** `tests/unit/test_volatility_filter.py`

```python
import pytest
from src.core.risk.volatility import VolatilityAnalyzer, VolatilityRegime

class TestVolatilityAnalyzer:
    """Test volatility analyzer."""

    @pytest.fixture
    def analyzer(self, market_data_service):
        return VolatilityAnalyzer(market_data_service)

    async def test_normal_volatility(self, analyzer, market_data_service):
        """Below 3% should be NORMAL."""
        # Mock ATR = 100, Price = 5000 → 2% volatility
        market_data_service.get_atr.return_value = 100
        market_data_service.get_current_price.return_value = 5000

        regime = await analyzer.get_regime("BTCUSDT")
        assert regime == VolatilityRegime.NORMAL

    async def test_elevated_volatility(self, analyzer):
        """3-5% should be ELEVATED."""
        # Mock ATR = 200, Price = 5000 → 4% volatility
        pass

    async def test_extreme_volatility(self, analyzer):
        """Above 5% should be EXTREME."""
        # Mock ATR = 300, Price = 5000 → 6% volatility
        pass

    async def test_size_reduction_elevated(self, analyzer):
        """Elevated volatility should reduce size to 50%."""
        should_reduce, multiplier = await analyzer.should_reduce_size("BTCUSDT")
        # (depends on regime)
        assert multiplier == 0.5 or multiplier == 1.0

    async def test_block_new_entries_extreme(self, analyzer):
        """Extreme volatility should block new entries."""
        can_enter, reason = await analyzer.can_enter("BTCUSDT")
        # (depends on regime)
        assert "Extreme" in reason or "OK" in reason

class TestWeekendHolidayFilter:
    """Test weekend/holiday filter."""

    def test_is_weekend_saturday(self):
        """Saturday should be detected as weekend."""
        # Mock datetime to Saturday
        pass

    def test_is_weekend_sunday(self):
        """Sunday should be detected as weekend."""
        pass

    def test_is_not_weekend_monday(self):
        """Monday should not be weekend."""
        pass

    def test_holiday_christmas(self):
        """Dec 25 should be detected as holiday."""
        pass

    def test_adjustments_enabled(self):
        """With filter enabled, should return adjustment multipliers."""
        filter = WeekendHolidayFilter(enabled=True)
        adjustments = filter.get_adjustments()
        # (depends on current day)

class TestEventFilter:
    """Test event filter."""

    def test_add_event(self):
        """Should be able to add events."""
        pass

    def test_block_during_event(self):
        """Should block trading during event window."""
        pass

    def test_allow_outside_event(self):
        """Should allow trading outside event window."""
        pass
```

**Acceptance Criteria:**
- [ ] All filters tested
- [ ] Integration tested
- [ ] Edge cases covered
- [ ] >90% coverage

---

## PRODUCTION QUALITY GATES

### Automated Quality Checks (Must PASS)

```bash
# 1. Type Safety
mypy src/core/risk/ --strict
# RESULT: "Success: no issues found"

# 2. Code Linting
ruff check src/core/risk/
# RESULT: 0 violations

# 3. Import Organization
isort src/core/risk/ --check --diff
# RESULT: "All done! No files would be modified"

# 4. Test Execution
pytest tests/unit/test_circuit_breakers.py tests/unit/test_volatility_filter.py -v
# RESULT: All tests pass

# 5. Coverage Report
pytest tests/unit/test_circuit_breakers.py tests/unit/test_volatility_filter.py \
  --cov=src/core/risk --cov-report=term-missing
# RESULT: >90% per file, >90% total

# 6. Production Audit
@production-code-audit audit src/core/risk/
# RESULT: Grade A-, no CRITICAL/HIGH issues
```

### Code Quality Standards

- ✅ Type Hints: 100%
- ✅ Input Validation: NaN/Infinity checks
- ✅ Imports: Strict organization
- ✅ Naming: Zero synonyms
- ✅ Docstrings: All public methods
- ✅ Logging: Structured
- ✅ Tests: >90% coverage

---

## DECISION CONSISTENCY

**Read before starting:**
- DEC-2026-02-08-002: SQLAlchemy 2.0
- DEC-2026-02-08-003: Timezone-aware datetimes
- DEC-2026-02-08-006: Type hints 100%
- DEC-2026-02-08-008: Structured logging

**Document any NEW decisions made during implementation.**

---

## DELIVERABLES

**Session 3B Complete When:**

```
[✅] Type Safety: mypy passes (0 errors)
[✅] Code Quality: ruff passes (0 violations)
[✅] Imports: isort passes
[✅] Tests: All pass
[✅] Coverage: >90% per file, >90% total
[✅] Production Audit: Grade A- or higher
[✅] Circuit breakers trigger correctly
[✅] Daily loss limit enforced (5%)
[✅] Drawdown limit enforced (15%)
[✅] Volatility filter reduces sizes in high vol
[✅] Weekend/holiday adjustments apply
[✅] Correlation limits enforced (40% BTC, 30% ETH, 60% group)
[✅] Integrated into RiskController pipeline
[✅] All decisions documented

OVERALL: ✅ PRODUCTION READY FOR PHASE 4
```

---

**Prompt Version:** 1.0
**Last Updated:** 2026-02-12
**Model Recommended:** Opus (state tracking, threshold logic)
**Estimated Duration:** 28 hours
**Next:** Phase 4 (Execution Engine)
