# SESSION 5A: STRATEGY FOUNDATION
## Template System + Signal Generation
**Duration:** ~44 hours | **Tasks:** 20 | **Sections:** 5.1 + 5.2

**Goal:** Build strategy template system and signal generation pipeline. All 7 templates functional with real-time signal generation.

**Start Conditions:** Phase 4 complete (execution infrastructure working)
**Exit Conditions:** All templates load, all 7 signal generators working, signals generated for all templates

---

## 📊 SESSION 5A OVERVIEW

```
Section 5.1: Template System (22h, 10 tasks)
- Strategy engine core
- Parameter validation & similarity checking
- Status transitions & regime manager
- 7 template YAML files
- API endpoints

Section 5.2: Signal Generation (22h, 10 tasks)
- Signal interface & types
- 7 signal generators (one per template)
- Factory pattern for generator creation
- Comprehensive tests
```

**Effort Distribution:**
- 5.1 Template System: 22 hours
- 5.2 Signal Generation: 22 hours
- **Total: 44 hours**

---

## CRITICAL CONCEPT: Strategy Lifecycle

Every strategy goes through these states:
```
[DRAFT] → [BACKTEST] → [SIMULATED_PAPER] → [LIVE_PAPER] → [PENDING_APPROVAL] → [LIVE]
   ↓           ↓            ↓
[BACKTEST fails → returns to DRAFT]
[PAUSED] ← any state (manual or auto)
[UNDERPERFORMING] (auto-detected)
[RETIRED] ← any state (manual)
```

**Key Invariants:**
- States move FORWARD only (never backward except DRAFT ← BACKTEST)
- Status transitions require explicit approval
- Each transition has specific conditions (days elapsed, validation passed, etc.)

---

## SECTION 5.1: TEMPLATE SYSTEM (22 hours)

### Task 5.1.1: Create Strategy Engine Core (2.5 hours)

**File:** `src/core/strategy/engine.py`

**Purpose:** Central registry and manager for all strategies. Acts as the command center for strategy operations.

**Core Interface:**
```python
class StrategyEngine:
    """Central strategy management component.

    Responsibilities:
    - Create strategies from templates
    - Manage strategy lifecycle (draft → live → retired)
    - Validate parameters
    - Check strategy similarity (prevent clones)
    - Assign strategies to accounts
    - Query strategy state
    """

    def __init__(
        self,
        template_manager: TemplateManager,
        data_store: DataStore,
        market_data: MarketDataService,
        regime_manager: MarketRegimeManager
    ):
        """Initialize Strategy Engine with dependencies."""
        pass

    async def create_strategy(
        self,
        template_id: str,
        name: str,
        params: Dict[str, Any],
        symbols: List[str],
        preferred_regimes: List[str] = None,
        avoid_regimes: List[str] = None
    ) -> Strategy:
        """
        Create new strategy from template.

        CRITICAL SEQUENCE:
        1. Load template from template_manager
        2. Validate parameters against template spec
        3. Check strategy similarity (reject if >70% similar)
        4. Create Strategy object with PENDING_CREATION status
        5. Persist to database
        6. Return strategy

        Raises:
        - StrategyValidationError: Parameters invalid
        - TemplateNotFoundError: Template doesn't exist
        - DuplicateStrategyError: Strategy >70% similar to existing
        """
        pass

    async def get_strategy(self, strategy_id: str) -> Strategy:
        """Get strategy with full metadata."""
        pass

    async def update_strategy_params(
        self,
        strategy_id: str,
        params: Dict[str, Any]
    ) -> Strategy:
        """Update parameters, only if strategy in DRAFT status."""
        pass

    async def transition_status(
        self,
        strategy_id: str,
        new_status: StrategyStatus,
        reason: str
    ) -> Strategy:
        """Change strategy status with validation."""
        pass

    async def list_strategies(
        self,
        status: StrategyStatus = None,
        template_id: str = None
    ) -> List[Strategy]:
        """List strategies with optional filters."""
        pass
```

**Acceptance Criteria:**
- ✓ Creates strategy from template
- ✓ Validates parameters against template spec
- ✓ Calls similarity checker (don't inline it)
- ✓ Persists to database
- ✓ Returns fully initialized Strategy object
- ✓ Unit test: strategy creation with valid params
- ✓ Unit test: rejects invalid parameters

---

### Task 5.1.2: Implement Parameter Validation (2 hours)

**Add to:** `src/core/strategy/engine.py`

**Purpose:** Ensure strategy parameters conform to template specification. Prevents invalid configurations before they reach execution.

**Method Signature:**
```python
async def _validate_parameters(
    self,
    template: StrategyTemplate,
    params: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validate parameters against template spec.

    Returns:
    - (True, []) if all valid
    - (False, [error1, error2, ...]) if invalid

    Validations:
    1. All required parameters present
    2. All values have correct type (int, float, bool, str)
    3. Values within min/max bounds
    4. Values match step size (if defined)
    5. Enum/choice values in allowed list
    6. Cross-parameter validations

    Example:
    - Template says: fast_ma_period (int, min=5, max=50, step=1)
    - Param value: 10.5 (float)
    - Error: "fast_ma_period must be integer, got float"

    Example 2:
    - Template says: slow_ma > fast_ma
    - Param values: fast=20, slow=15
    - Error: "slow_ma_period must be > fast_ma_period"
    """
    pass
```

**Validation Examples:**

```python
# Test 1: Missing required parameter
template = StrategyTemplate(
    parameters={
        'fast_ma': {'required': True, 'type': 'int', 'min': 5, 'max': 20},
        'slow_ma': {'required': True, 'type': 'int', 'min': 20, 'max': 100}
    }
)
params = {'fast_ma': 10}  # Missing slow_ma
result = validate_parameters(template, params)
# Expected: (False, ["slow_ma_period is required"])

# Test 2: Value outside bounds
params = {'fast_ma': 50, 'slow_ma': 75}  # fast_ma > max (20)
result = validate_parameters(template, params)
# Expected: (False, ["fast_ma_period must be <= 20, got 50"])

# Test 3: Invalid type
params = {'fast_ma': "10", 'slow_ma': 75}  # fast_ma is string
result = validate_parameters(template, params)
# Expected: (False, ["fast_ma_period must be int, got str"])

# Test 4: Step size violation
template.parameters['fast_ma']['step'] = 0.5
params = {'fast_ma': 10.25, 'slow_ma': 75}  # 10.25 % 0.5 != 0
result = validate_parameters(template, params)
# Expected: (False, ["fast_ma_period must be multiple of 0.5"])

# Test 5: Cross-parameter validation
template.validation_rules = [
    "slow_ma > fast_ma"  # Custom rule
]
params = {'fast_ma': 20, 'slow_ma': 15}
result = validate_parameters(template, params)
# Expected: (False, ["slow_ma_period must be > fast_ma_period"])
```

**Acceptance Criteria:**
- ✓ Required parameters validation
- ✓ Type checking (int, float, bool, str, enum)
- ✓ Min/max bounds checking
- ✓ Step size validation
- ✓ Enum/choice validation
- ✓ Cross-parameter validation (custom rules)
- ✓ Returns ALL errors (not just first)
- ✓ Clear, actionable error messages
- ✓ Unit test: each validation type

---

### Task 5.1.2a: Implement Strategy Similarity Check (2.5 hours)

**Add to:** `src/core/strategy/engine.py`

**CRITICAL FOR MVP:** Per PRD Feature D - prevent strategy cloning. Learned from Phase 3: clones don't add diversification.

**Similarity Scoring Formula:**

```
Total Similarity = (template_score) + (param_score) + (symbol_score) + (logic_score)

WEIGHTS:
- Same template_id: +40%
- Parameter distance < 20%: +30%
- Symbol overlap > 50%: +20%
- Same entry conditions: +10%

THRESHOLD: Reject if > 70% similar
```

**Implementation:**
```python
class StrategySimilarityChecker:
    """
    Reject strategies too similar to existing ones per PRD Feature D.

    Prevents clustering of nearly-identical strategies which:
    - Don't add diversification
    - Increase correlation risk
    - Waste capital allocation
    """

    SIMILARITY_THRESHOLD = 0.70

    WEIGHTS = {
        'template': 0.40,
        'parameters': 0.30,
        'symbols': 0.20,
        'entry_logic': 0.10
    }

    def __init__(self, data_store: DataStore):
        self.data_store = data_store

    async def check_similarity(
        self,
        new_strategy: Strategy,
        existing_strategies: List[Strategy] = None
    ) -> SimilarityResult:
        """
        Check if new strategy is too similar to existing strategies.

        Returns:
        SimilarityResult(
            is_too_similar=False,  # or True if > threshold
            similarity_pct=67.5,  # 0-100
            most_similar_strategy_id="str_001",  # or None
            breakdown={  # Component scores
                'template': 0.40,
                'parameters': 0.225,  # 0.75 of 30%
                'symbols': 0.10,
                'entry_logic': 0.0
            }
        )
        """
        if existing_strategies is None:
            existing_strategies = await self.data_store.get_active_strategies()

        max_similarity = 0.0
        most_similar_id = None
        best_breakdown = {}

        for existing in existing_strategies:
            similarity, breakdown = self._calculate_similarity(new_strategy, existing)

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_id = existing.id
                best_breakdown = breakdown

        return SimilarityResult(
            is_too_similar=max_similarity > self.SIMILARITY_THRESHOLD,
            similarity_pct=max_similarity * 100,
            most_similar_strategy_id=most_similar_id,
            breakdown=best_breakdown
        )

    def _calculate_similarity(
        self,
        new: Strategy,
        existing: Strategy
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate similarity score between two strategies."""
        breakdown = {}

        # 1. Template type similarity (40%)
        if new.template_id == existing.template_id:
            breakdown['template'] = self.WEIGHTS['template']  # +40%
        else:
            breakdown['template'] = 0.0

        # 2. Parameter distance (30%)
        param_sim = self._calculate_parameter_similarity(
            new.parameters,
            existing.parameters
        )
        # If params within 20% similarity, add full 30%
        if param_sim > 0.80:
            breakdown['parameters'] = self.WEIGHTS['parameters']  # +30%
        else:
            # Partial credit for some parameter similarity
            breakdown['parameters'] = param_sim * self.WEIGHTS['parameters']

        # 3. Symbol overlap (20%)
        symbol_overlap = self._calculate_symbol_overlap(
            new.symbols,
            existing.symbols
        )
        # If > 50% symbol overlap, add full 20%
        if symbol_overlap > 0.50:
            breakdown['symbols'] = self.WEIGHTS['symbols']  # +20%
        else:
            breakdown['symbols'] = symbol_overlap * self.WEIGHTS['symbols']

        # 4. Entry logic similarity (10%)
        if self._same_entry_conditions(new, existing):
            breakdown['entry_logic'] = self.WEIGHTS['entry_logic']  # +10%
        else:
            breakdown['entry_logic'] = 0.0

        total = sum(breakdown.values())
        return total, breakdown

    def _calculate_parameter_similarity(
        self,
        params1: Dict[str, Any],
        params2: Dict[str, Any]
    ) -> float:
        """
        Calculate normalized parameter distance.

        Returns 1.0 if identical, 0.0 if completely different.
        Uses normalized Euclidean distance.

        Example:
        params1 = {'fast_ma': 10, 'slow_ma': 50}
        params2 = {'fast_ma': 9,  'slow_ma': 49}
        distance = sqrt((|10-9|/20)^2 + (|50-49|/100)^2) = 0.032
        similarity = 1.0 - 0.032 = 0.968 (96.8% similar)
        """
        pass

    def _calculate_symbol_overlap(
        self,
        symbols1: List[str],
        symbols2: List[str]
    ) -> float:
        """
        Calculate percentage of symbol overlap (Jaccard similarity).

        Example:
        symbols1 = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        symbols2 = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']

        intersection = {'BTCUSDT', 'ETHUSDT'} = 2
        union = {'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT'} = 4

        overlap = 2 / 4 = 0.50 (50% overlap)
        """
        set1 = set(symbols1)
        set2 = set(symbols2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _same_entry_conditions(
        self,
        s1: Strategy,
        s2: Strategy
    ) -> bool:
        """
        Check if strategies have same entry conditions.

        Compare entry logic definitions from template.
        For EMA strategy: both have "Fast EMA > Slow EMA"?
        """
        pass
```

**Test Cases:**

```python
# Test 1: Identical strategy (should reject at 100%)
new = Strategy(
    template_id="ema_trend_rsi",
    parameters={'fast_ma': 10, 'slow_ma': 50},
    symbols=['BTCUSDT']
)
existing = Strategy(
    template_id="ema_trend_rsi",
    parameters={'fast_ma': 10, 'slow_ma': 50},
    symbols=['BTCUSDT']
)
result = check_similarity(new, [existing])
# Expected: is_too_similar=True, similarity_pct=100.0

# Test 2: Different template (should pass - 0% similar)
new = Strategy(template_id="bb_squeeze", symbols=['BTCUSDT'])
existing = Strategy(template_id="ema_trend_rsi", symbols=['BTCUSDT'])
result = check_similarity(new, [existing])
# Expected: is_too_similar=False, similarity_pct=0.0

# Test 3: Borderline similar (67% - should pass)
new = Strategy(
    template_id="ema_trend_rsi",  # +40%
    parameters={'fast_ma': 10, 'slow_ma': 51},  # slight diff = +22.5%
    symbols=['BTCUSDT', 'ETHUSDT']  # overlap 50% = +10%
)
result = check_similarity(new, [existing])
# Expected: is_too_similar=False (67.5% < 70%)

# Test 4: Too similar (75% - should reject)
new = Strategy(
    template_id="ema_trend_rsi",  # +40%
    parameters={'fast_ma': 10, 'slow_ma': 50},  # identical = +30%
    symbols=['BTCUSDT', 'ETHUSDT']  # 50% overlap = +10%
)
result = check_similarity(new, [existing])
# Expected: is_too_similar=True (80% > 70%)
```

**Acceptance Criteria:**
- ✓ Template type adds 40% if same
- ✓ Parameter distance adds up to 30% if within 20%
- ✓ Symbol overlap adds up to 20% if > 50%
- ✓ Entry logic adds 10% if same
- ✓ Rejects if total > 70%
- ✓ Returns complete breakdown showing each component
- ✓ Rejection includes explanation (e.g., "75% similar to str_001 - same template + same symbols")
- ✓ Compares against ALL active strategies
- ✓ Unit test: parameter similarity calculation
- ✓ Unit test: symbol overlap calculation
- ✓ Unit test: all rejection scenarios

---

### Task 5.1.3: Implement Strategy Status Transitions (2 hours)

**Add to:** `src/core/strategy/engine.py`

**Critical Invariant:** Only valid transitions allowed. State machine is strictly defined.

```python
async def transition_status(
    self,
    strategy_id: str,
    new_status: StrategyStatus,
    reason: str
) -> Strategy:
    """
    Change strategy status with validation.

    ALLOWED TRANSITIONS:
    ✓ DRAFT → BACKTEST (manual)
    ✓ BACKTEST → SIMULATED_PAPER (if passes validation)
    ✓ BACKTEST → DRAFT (if fails validation)
    ✓ SIMULATED_PAPER → LIVE_PAPER (after 21 days)
    ✓ LIVE_PAPER → PENDING_APPROVAL (after 7 days)
    ✓ PENDING_APPROVAL → LIVE (on operator approval)
    ✓ PENDING_APPROVAL → LIVE_PAPER (if rejected)
    ✓ LIVE → PAUSED (manual or auto)
    ✓ LIVE → UNDERPERFORMING (auto-detected)
    ✓ PAUSED → LIVE (manual resume)
    ✓ UNDERPERFORMING → PAUSED (auto)
    ✓ ANY → RETIRED (manual retirement)

    DISALLOWED (will raise error):
    ✗ BACKTEST → LIVE (skip phases)
    ✗ FILLED → PENDING (backward move)
    ✗ RETIRED → any (final state)

    Args:
        strategy_id: Strategy to update
        new_status: Target status
        reason: Why changing (logged and persisted)

    Raises:
        InvalidStatusTransitionError: If transition not allowed
        StrategyNotFoundError: If strategy doesn't exist
    """
    pass
```

**Validation Logic:**

```python
VALID_TRANSITIONS = {
    StrategyStatus.DRAFT: [
        StrategyStatus.BACKTEST
    ],
    StrategyStatus.BACKTEST: [
        StrategyStatus.DRAFT,  # If validation fails
        StrategyStatus.SIMULATED_PAPER  # If passes
    ],
    StrategyStatus.SIMULATED_PAPER: [
        StrategyStatus.LIVE_PAPER
    ],
    StrategyStatus.LIVE_PAPER: [
        StrategyStatus.PENDING_APPROVAL
    ],
    StrategyStatus.PENDING_APPROVAL: [
        StrategyStatus.LIVE,
        StrategyStatus.LIVE_PAPER
    ],
    StrategyStatus.LIVE: [
        StrategyStatus.PAUSED,
        StrategyStatus.UNDERPERFORMING,
        StrategyStatus.RETIRED
    ],
    StrategyStatus.PAUSED: [
        StrategyStatus.LIVE,
        StrategyStatus.RETIRED
    ],
    StrategyStatus.UNDERPERFORMING: [
        StrategyStatus.PAUSED,
        StrategyStatus.RETIRED
    ],
    StrategyStatus.RETIRED: []  # Terminal state
}
```

**Acceptance Criteria:**
- ✓ Only valid transitions allowed
- ✓ Throws InvalidStatusTransitionError for disallowed
- ✓ Records lifecycle event with timestamp and reason
- ✓ Persists to database
- ✓ Unit test: all valid transitions
- ✓ Unit test: all invalid transitions rejected

---

### Task 5.1.3a: Implement Market Regime Manager (2.5 hours)

**File:** `src/core/strategy/regime.py`

**PURPOSE:** Per PRD Feature B - Manual regime tagging. Allows operator to tag market conditions, strategies adjust position size accordingly.

**Complete Implementation:**

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class MarketRegime(str, Enum):
    """Market regime classification."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"  # Default

@dataclass
class RegimeChange:
    """Record of regime change."""
    previous_regime: MarketRegime
    new_regime: MarketRegime
    changed_at: datetime
    changed_by: str  # Operator name
    note: str


class MarketRegimeManager:
    """
    Manual regime tagging system per PRD Feature B.

    Operator tags current market condition via dashboard dropdown.
    Strategies define preferred/avoid regimes.
    On mismatch: reduce position size by 50%.

    Integration:
    - Set via API endpoint: POST /api/regime/set
    - Strategies read via: regime_manager.check_strategy_compatibility(strategy)
    - Returns (is_compatible: bool, size_multiplier: float)
    """

    MISMATCH_SIZE_REDUCTION = 0.5  # 50% reduction for mismatches

    def __init__(self, data_store):
        self.data_store = data_store
        self._current_regime = MarketRegime.UNKNOWN
        self._history: List[RegimeChange] = []

    def get_current_regime(self) -> MarketRegime:
        """Get the current market regime."""
        return self._current_regime

    async def set_regime(
        self,
        regime: MarketRegime,
        operator: str,
        note: str = ""
    ) -> None:
        """
        Set current market regime (manual, via dashboard).

        Args:
            regime: One of TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, UNKNOWN
            operator: Operator name or ID
            note: Optional note explaining the change

        Example:
            await regime_manager.set_regime(
                MarketRegime.TRENDING_UP,
                operator="user_1",
                note="Price above 200 SMA with strong volume"
            )
        """
        change = RegimeChange(
            previous_regime=self._current_regime,
            new_regime=regime,
            changed_at=datetime.now(timezone.utc),
            changed_by=operator,
            note=note
        )

        self._history.append(change)
        self._current_regime = regime

        logger.info(
            "regime_changed",
            from_regime=change.previous_regime.value,
            to_regime=regime.value,
            operator=operator,
            note=note
        )

        # Persist to database
        await self.data_store.update_system_state('market_regime', regime.value)
        await self.data_store.add_regime_change(change)

    def get_regime_history(self, limit: int = 20) -> List[RegimeChange]:
        """Get recent regime changes (last N)."""
        return self._history[-limit:]

    def check_strategy_compatibility(
        self,
        strategy: Strategy
    ) -> Tuple[bool, float]:
        """
        Check if current regime is compatible with strategy.

        Returns:
        - (True, 1.0) if compatible (full size)
        - (True, 0.5) if mismatch (reduce size 50%)
        - (False, 0.0) if in avoid_regimes (don't trade)

        Example:
        regime = TRENDING_UP
        strategy.preferred_regimes = [TRENDING_UP, TRENDING_DOWN]

        Result: (True, 1.0) - full size

        Example 2:
        regime = TRENDING_UP
        strategy.avoid_regimes = [TRENDING_UP]

        Result: (False, 0.0) - don't trade

        Example 3:
        regime = VOLATILE
        strategy.preferred_regimes = [TRENDING_UP, TRENDING_DOWN]
        strategy.avoid_regimes = []

        Result: (True, 0.5) - reduce size 50%
        """
        preferred = getattr(strategy, 'preferred_regimes', [])
        avoid = getattr(strategy, 'avoid_regimes', [])

        current = self._current_regime

        logger.debug(
            "regime_compatibility_check",
            current_regime=current.value,
            strategy_id=strategy.id,
            preferred=preferred,
            avoid=avoid
        )

        # BLOCKING: In avoid list, don't trade
        if current in avoid:
            logger.info(
                "strategy_blocked_by_regime",
                strategy_id=strategy.id,
                current_regime=current.value,
                reason="in avoid_regimes"
            )
            return False, 0.0

        # UNKNOWN regime: Trade with caution (full size but operator aware)
        if current == MarketRegime.UNKNOWN:
            return True, 1.0

        # COMPATIBLE: In preferred list OR no preferences specified
        if current in preferred or len(preferred) == 0:
            logger.debug(
                "regime_compatible",
                strategy_id=strategy.id,
                current_regime=current.value
            )
            return True, 1.0

        # MISMATCH: Not in preferred list, not blocked
        logger.info(
            "regime_mismatch",
            strategy_id=strategy.id,
            current_regime=current.value,
            preferred=preferred,
            reduction="50%"
        )
        return True, self.MISMATCH_SIZE_REDUCTION

    async def load_from_database(self) -> None:
        """Load regime state from database on startup."""
        regime_str = await self.data_store.get_system_state('market_regime')
        if regime_str:
            self._current_regime = MarketRegime(regime_str)

        self._history = await self.data_store.get_regime_history()

        logger.info(
            "regime_manager_initialized",
            current_regime=self._current_regime.value,
            history_size=len(self._history)
        )
```

**Template Usage:**

Each template can specify regime preferences:
```yaml
template_id: "ema_trend_rsi"
preferred_regimes:
  - "trending_up"
  - "trending_down"
avoid_regimes:
  - "ranging"  # Trend followers suffer in ranges
```

**Dashboard Integration:**

API endpoint to set regime:
```python
@router.post("/api/regime/set")
async def set_market_regime(
    regime: MarketRegime,
    operator: str,
    note: str = ""
):
    """Set current market regime via dashboard dropdown."""
    await regime_manager.set_regime(regime, operator, note)
    return {"current_regime": regime.value}
```

**Acceptance Criteria:**
- ✓ MarketRegime enum with 5 values
- ✓ Operator can set regime via API
- ✓ Regime changes logged with timestamp, operator, note
- ✓ Strategies can define preferred_regimes and avoid_regimes
- ✓ Size reduced by 50% on regime mismatch
- ✓ Trading completely blocked if in avoid_regimes
- ✓ Regime persists across restarts (load from DB)
- ✓ History available for audit
- ✓ Unit test: regime setting and persistence
- ✓ Unit test: compatibility checking with all scenarios

---

### Task 5.1.4: Create All 7 Template YAML Files (4 hours)

**Location:** `config/templates/`

**Files to Create:**

1. **ema_trend_rsi.yaml** - EMA Trend + RSI Filter
2. **donchian_atr.yaml** - Donchian Breakout + ATR
3. **bb_squeeze_breakout.yaml** - Bollinger Band Squeeze
4. **rsi_bb_mean_reversion.yaml** - RSI + BB Mean Reversion
5. **supertrend_volume_macd.yaml** - SuperTrend + Volume/MACD
6. **macd_pullback.yaml** - MACD Trend + Pullback
7. **vwap_pullback_volume.yaml** - VWAP Pullback + Volume

**Template Structure (each file):**

```yaml
id: "ema_trend_rsi"
name: "EMA Trend + RSI Filter"
version: "1.0.0"
type: "trend_following"
description: "Trend-following strategy using dual moving average crossover with RSI momentum confirmation"

# Strategy regime compatibility
preferred_regimes:
  - "trending_up"
  - "trending_down"
avoid_regimes:
  - "ranging"

# Entry/Exit Logic (human-readable)
entry_logic:
  long:
    - "Fast EMA > Slow EMA"
    - "Price > both EMAs"
    - "RSI between 40-60 (momentum confirmation)"
    - "Entry on next bar open"
  short:
    - "Fast EMA < Slow EMA"
    - "Price < both EMAs"
    - "RSI between 40-60"

exit_logic:
  take_profit: "3.0%"
  stop_loss: "ATR-based trailing"
  signal_exit: "Opposite EMA crossover"

# Parameters (all customizable by user)
parameters:
  fast_ema_period:
    type: "integer"
    min: 5
    max: 20
    default: 10
    step: 1
    description: "Fast EMA period"
    ui_group: "Moving Averages"

  slow_ema_period:
    type: "integer"
    min: 20
    max: 100
    default: 50
    step: 1
    description: "Slow EMA period"
    ui_group: "Moving Averages"

  rsi_period:
    type: "integer"
    min: 7
    max: 21
    default: 14
    step: 1
    description: "RSI calculation period"
    ui_group: "RSI Settings"

  rsi_filter_level:
    type: "integer"
    min: 40
    max: 60
    default: 50
    step: 5
    description: "RSI level for momentum confirmation"
    ui_group: "RSI Settings"

  atr_period:
    type: "integer"
    min: 10
    max: 20
    default: 14
    step: 1
    description: "ATR period for stop loss"
    ui_group: "Risk Management"

  atr_stop_multiplier:
    type: "float"
    min: 1.5
    max: 3.5
    default: 2.0
    step: 0.25
    description: "ATR multiplier for stop distance"
    ui_group: "Risk Management"

  take_profit_pct:
    type: "float"
    min: 1.5
    max: 8.0
    default: 3.0
    step: 0.5
    description: "Take profit percentage"
    ui_group: "Risk Management"

# Validation rules
validation_rules:
  - "fast_ema_period < slow_ema_period"
  - "min_difference: slow_ema_period - fast_ema_period >= 5"

# Expected performance (from backtests)
expected_performance:
  min_sharpe_ratio: 1.0
  max_drawdown_pct: 15
  min_win_rate_pct: 50
  avg_trades_per_month: "5-15"

recommended_for:
  - "Trending markets"
  - "BTC, ETH, major altcoins"
  - "1H and 4H timeframes"
  - "Swing trading (hours to days)"

not_recommended_for:
  - "Ranging/choppy markets"
  - "Very short timeframes (< 15m)"
  - "Low liquidity tokens"
```

**All 7 Templates Required:**

Each template file should follow the same structure above. Use the PRD Section 3.3.2 for detailed parameter specifications for each template.

**Acceptance Criteria:**
- ✓ All 7 YAML files created
- ✓ All parameters from PRD included
- ✓ YAML syntax valid (no parsing errors)
- ✓ All required fields present (id, name, version, parameters)
- ✓ Parameter specs complete (type, min, max, default, step)
- ✓ Templates load without errors
- ✓ Unit test: load each template and verify structure

---

### Task 5.1.5: Implement Template Loading Verification (1 hour)

**Add to:** `src/core/strategy/engine.py`

```python
async def verify_templates(self) -> TemplateVerificationResult:
    """
    Verify all templates load correctly on startup.

    Checks:
    1. All 7 templates load from YAML files
    2. No duplicate IDs
    3. All required fields present
    4. Parameter specs valid
    5. Validation rules parseable
    6. No missing dependencies

    Returns:
    TemplateVerificationResult(
        success=True,
        total_templates=7,
        valid_templates=7,
        errors=[]
    )

    OR if failures:
    TemplateVerificationResult(
        success=False,
        errors=[
            "Template donchian_atr.yaml: Missing required field 'name'",
            "Duplicate template ID: bb_squeeze_breakout"
        ]
    )

    Call on startup (before accepting requests).
    """
    pass
```

**Acceptance Criteria:**
- ✓ Runs on startup before serving requests
- ✓ Fails fast if templates invalid
- ✓ Clear error messages for each issue
- ✓ Returns all errors (not just first)
- ✓ Unit test: verification with valid templates
- ✓ Unit test: verification with missing fields
- ✓ Unit test: duplicate IDs detected

---

### Task 5.1.6: Create Strategy API Endpoints (2 hours)

**File:** `src/api/routes/strategies.py`

```python
@router.get("/api/templates")
async def list_templates() -> List[StrategyTemplate]:
    """List all available templates."""
    pass

@router.get("/api/templates/{template_id}")
async def get_template(template_id: str) -> StrategyTemplate:
    """Get template details."""
    pass

@router.post("/api/strategies")
async def create_strategy(request: CreateStrategyRequest) -> Strategy:
    """
    Create strategy from template.

    Request:
    {
        "template_id": "ema_trend_rsi",
        "name": "My EMA Strategy",
        "parameters": {
            "fast_ema_period": 10,
            "slow_ema_period": 50,
            ...
        },
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "preferred_regimes": ["trending_up"],
        "avoid_regimes": ["ranging"]
    }
    """
    pass

@router.get("/api/strategies")
async def list_strategies(
    status: StrategyStatus = None,
    template_id: str = None
) -> List[Strategy]:
    """List strategies with optional filters."""
    pass

@router.get("/api/strategies/{strategy_id}")
async def get_strategy(strategy_id: str) -> Strategy:
    """Get strategy details."""
    pass

@router.put("/api/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    params: Dict[str, Any]
) -> Strategy:
    """Update strategy parameters (only if DRAFT)."""
    pass

@router.put("/api/strategies/{strategy_id}/status")
async def change_status(
    strategy_id: str,
    new_status: StrategyStatus,
    reason: str
) -> Strategy:
    """Change strategy status."""
    pass

@router.delete("/api/strategies/{strategy_id}")
async def retire_strategy(strategy_id: str) -> Strategy:
    """Retire strategy (final status)."""
    pass
```

**Acceptance Criteria:**
- ✓ All CRUD operations (create, read, update, delete)
- ✓ Template listing and details
- ✓ Status transitions with validation
- ✓ Proper HTTP error codes (400, 404, 409, etc.)
- ✓ Request validation
- ✓ Integration test: full CRUD flow

---

### Task 5.1.7: Implement Strategy Assignment to Account (1.5 hours)

**Add to:** `src/core/strategy/engine.py`

```python
async def assign_to_account(
    self,
    strategy_id: str,
    account_id: str,
    allocation_pct: float
) -> StrategyAssignment:
    """
    Assign strategy to trading account.

    Args:
        strategy_id: Strategy to assign
        account_id: Account to assign to
        allocation_pct: Percentage of account capital (0-100)

    Returns:
        StrategyAssignment record

    Validation:
    - allocation_pct must be 0-100
    - strategy must exist
    - account must exist
    - allocation_pct must allow room for other strategies
    """
    pass

async def unassign_from_account(
    self,
    strategy_id: str,
    account_id: str
) -> None:
    """Remove strategy from account."""
    pass

async def get_account_strategies(
    self,
    account_id: str
) -> List[Tuple[Strategy, StrategyAssignment]]:
    """Get all strategies assigned to account."""
    pass
```

**Acceptance Criteria:**
- ✓ Creates StrategyAssignment record
- ✓ Allocation percentage tracked
- ✓ Multiple strategies per account supported
- ✓ Validates allocation doesn't exceed 100%
- ✓ Unit test: assignment creation
- ✓ Unit test: multiple assignments per account

---

### Task 5.1.8: Write Template System Tests (2 hours)

**File:** `tests/unit/strategy/test_template_system.py`

**Test Coverage:**

```python
# Strategy creation tests
def test_create_strategy_from_template()
def test_create_strategy_invalid_params()
def test_create_strategy_missing_required_param()

# Parameter validation tests
def test_validate_parameters_type_checking()
def test_validate_parameters_bounds_checking()
def test_validate_parameters_step_size()
def test_validate_parameters_enum_values()
def test_validate_parameters_cross_field_validation()

# Strategy similarity tests
def test_strategy_similarity_identical()
def test_strategy_similarity_different_template()
def test_strategy_similarity_same_template_different_params()
def test_strategy_similarity_reject_threshold()
def test_strategy_similarity_accept_threshold()

# Status transition tests
def test_status_transition_draft_to_backtest()
def test_status_transition_invalid()
def test_status_transition_retired_is_terminal()

# Regime manager tests
def test_regime_set_and_get()
def test_regime_compatibility_preferred()
def test_regime_compatibility_avoid()
def test_regime_compatibility_mismatch_size_reduction()
def test_regime_persistence()

# API endpoint tests
async def test_create_strategy_api()
async def test_list_strategies_api()
async def test_update_strategy_api()
async def test_change_status_api()

# Template loading tests
def test_load_all_templates()
def test_verify_templates_valid()
def test_verify_templates_missing_file()
def test_verify_templates_invalid_yaml()
```

**Acceptance Criteria:**
- ✓ All templates tested (creation from each)
- ✓ Parameter validation tested
- ✓ Status transitions tested
- ✓ Template loading tested
- ✓ Account assignment tested
- ✓ Regime manager tested
- ✓ >85% code coverage
- ✓ All tests pass

---

## SECTION 5.2: SIGNAL GENERATION (22 hours)

### Task 5.2.1: Create Signal Generator Interface (1.5 hours)

**File:** `src/core/strategy/signals.py`

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class SignalType(Enum):
    """Signal types - entry and exit."""
    LONG_ENTRY = "long_entry"
    LONG_EXIT = "long_exit"
    SHORT_ENTRY = "short_entry"  # Future
    SHORT_EXIT = "short_exit"    # Future
    NO_SIGNAL = "no_signal"

@dataclass
class Signal:
    """
    Trading signal from strategy.

    Attributes:
        type: Entry/exit signal
        symbol: Crypto symbol (e.g., BTCUSDT)
        strategy_id: Strategy that generated signal
        timestamp: When signal generated (UTC)
        price: Current price when signal generated
        stop_loss: Suggested stop loss (optional)
        take_profit: Suggested take profit (optional)
        confidence: Signal confidence 0.0-1.0 (optional)
        metadata: Additional data (indicator values, etc.)
    """
    type: SignalType
    symbol: str
    strategy_id: str
    timestamp: datetime
    price: float  # Current price when signal generated
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate signal data."""
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")

        if math.isnan(self.price) or math.isinf(self.price):
            raise ValueError("price cannot be NaN or Infinity")

        if self.stop_loss is not None:
            if math.isnan(self.stop_loss) or math.isinf(self.stop_loss):
                raise ValueError("stop_loss cannot be NaN or Infinity")

        if self.take_profit is not None:
            if math.isnan(self.take_profit) or math.isinf(self.take_profit):
                raise ValueError("take_profit cannot be NaN or Infinity")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be 0.0-1.0")

class SignalGenerator(ABC):
    """
    Abstract base class for signal generators.

    Each template has one generator that:
    - Reads market data
    - Evaluates entry conditions
    - Evaluates exit conditions
    - Returns Signal objects
    """

    @abstractmethod
    async def generate_signal(
        self,
        strategy: Strategy,
        symbol: str,
        data: pd.DataFrame  # OHLCV dataframe
    ) -> Signal:
        """
        Generate trading signal for symbol.

        Args:
            strategy: Strategy with parameters
            symbol: Symbol to analyze
            data: OHLCV dataframe with indicators

        Returns:
            Signal(type=LONG_ENTRY/LONG_EXIT/NO_SIGNAL, ...)

        Must return NO_SIGNAL if conditions not met.
        Never return None or raise exception for normal conditions.
        """
        pass
```

**Acceptance Criteria:**
- ✓ SignalType enum with entry/exit types
- ✓ Signal dataclass with validation
- ✓ Timezone-aware timestamp required
- ✓ NaN/Infinity validation on numeric fields
- ✓ Abstract SignalGenerator interface
- ✓ Unit test: signal creation with valid data
- ✓ Unit test: signal creation rejects invalid data

---

### Task 5.2.2 through 5.2.8: Implement 7 Signal Generators (14 hours total)

**General Pattern for Each Generator:**

```python
# File: src/core/strategy/generators/ema_trend_rsi.py

class EMATrendRSIGenerator(SignalGenerator):
    """Signal generator for EMA Trend + RSI template."""

    def __init__(self):
        self.name = "EMA Trend + RSI"

    async def generate_signal(
        self,
        strategy: Strategy,
        symbol: str,
        data: pd.DataFrame
    ) -> Signal:
        """
        Generate signal based on EMA and RSI.

        ENTRY LOGIC:
        1. Fast EMA > Slow EMA (uptrend)
        2. RSI between 40-60 (momentum confirmation)
        3. Price above both EMAs

        EXIT LOGIC:
        1. Fast EMA < Slow EMA (trend reversal)
        2. Or RSI > 70 (overbought)
        3. Or ATR-based stop loss

        Returns:
        - Signal(type=LONG_ENTRY, ...) if entry conditions met
        - Signal(type=LONG_EXIT, ...) if exit conditions met
        - Signal(type=NO_SIGNAL) otherwise
        """

        # Extract parameters from strategy
        fast_period = strategy.parameters['fast_ema_period']
        slow_period = strategy.parameters['slow_ema_period']
        rsi_period = strategy.parameters['rsi_period']
        rsi_filter = strategy.parameters['rsi_filter_level']

        # Calculate indicators
        fast_ema = ta.ema(data['close'], fast_period)
        slow_ema = ta.ema(data['close'], slow_period)
        rsi = ta.rsi(data['close'], rsi_period)
        atr = ta.atr(data['high'], data['low'], data['close'])

        # Get current values
        current_close = data['close'].iloc[-1]
        current_fast = fast_ema.iloc[-1]
        current_slow = slow_ema.iloc[-1]
        current_rsi = rsi.iloc[-1]

        # Previous values for transitions
        prev_fast = fast_ema.iloc[-2]
        prev_slow = slow_ema.iloc[-2]

        # Entry signal
        if (prev_fast <= prev_slow and  # Was not in uptrend
            current_fast > current_slow and  # Now in uptrend
            current_close > current_fast and  # Price above fast EMA
            current_rsi >= rsi_filter and  # RSI confirms (not oversold)
            current_rsi <= 100 - rsi_filter):  # Not overbought either

            stop_loss = current_fast - (atr.iloc[-1] * 2.0)
            take_profit = current_close + (atr.iloc[-1] * 3.0)

            return Signal(
                type=SignalType.LONG_ENTRY,
                symbol=symbol,
                strategy_id=strategy.id,
                timestamp=datetime.now(timezone.utc),
                price=current_close,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=0.95,
                metadata={
                    'fast_ema': float(current_fast),
                    'slow_ema': float(current_slow),
                    'rsi': float(current_rsi),
                    'atr': float(atr.iloc[-1])
                }
            )

        # Exit signal
        if (prev_fast > prev_slow and  # Was in uptrend
            current_fast < current_slow):  # Trend reversed

            return Signal(
                type=SignalType.LONG_EXIT,
                symbol=symbol,
                strategy_id=strategy.id,
                timestamp=datetime.now(timezone.utc),
                price=current_close,
                metadata={'reason': 'EMA crossover'}
            )

        # No signal
        return Signal(
            type=SignalType.NO_SIGNAL,
            symbol=symbol,
            strategy_id=strategy.id,
            timestamp=datetime.now(timezone.utc),
            price=current_close
        )
```

**Each Generator Implements:** (2-2.5 hours each)
1. **Donchian + ATR** (Breakout-style)
2. **BB Squeeze** (Volatility-based)
3. **RSI + BB Mean Reversion** (Counter-trend)
4. **SuperTrend + Volume/MACD** (Trend confirmation)
5. **MACD Pullback** (Trend continuation)
6. **VWAP Pullback** (Support/resistance)
7. **EMA Trend + RSI** (Template 1 - already shown)

**Acceptance Criteria (per generator):**
- ✓ Entry signal generated correctly
- ✓ Exit signal generated correctly
- ✓ Stop loss and take profit calculated
- ✓ NO_SIGNAL returned when conditions not met
- ✓ Timestamp timezone-aware
- ✓ Unit test: known data triggers correct signals

---

### Task 5.2.9: Create Signal Generator Factory (1 hour)

**File:** `src/core/strategy/generators/__init__.py`

```python
class SignalGeneratorFactory:
    """
    Factory pattern for creating signal generators.

    Maps template_id to generator class.
    """

    _generators = {
        "ema_trend_rsi": EMATrendRSIGenerator,
        "donchian_atr": DonchianATRGenerator,
        "bb_squeeze_breakout": BBSqueezeGenerator,
        "rsi_bb_mean_reversion": RSIBBMeanReversionGenerator,
        "supertrend_volume_macd": SuperTrendGenerator,
        "macd_pullback": MACDPullbackGenerator,
        "vwap_pullback_volume": VWAPPullbackGenerator,
    }

    @classmethod
    def create(cls, template_id: str) -> SignalGenerator:
        """
        Create signal generator by template ID.

        Args:
            template_id: e.g., "ema_trend_rsi"

        Returns:
            SignalGenerator instance

        Raises:
            ValueError: If template_id not found
        """
        if template_id not in cls._generators:
            raise ValueError(
                f"Unknown template: {template_id}. "
                f"Available: {list(cls._generators.keys())}"
            )

        generator_class = cls._generators[template_id]
        return generator_class()
```

**Acceptance Criteria:**
- ✓ All 7 generators registered
- ✓ Create by template ID
- ✓ Raises ValueError for unknown template
- ✓ Unit test: factory creation for all templates

---

### Task 5.2.10: Write Signal Generator Tests (3 hours)

**File:** `tests/unit/strategy/test_signal_generators.py`

```python
# Fixtures
@pytest.fixture
def sample_ohlcv_uptrend():
    """OHLCV data in uptrend for EMA strategy."""
    # Create data with:
    # - Fast EMA crossing above slow EMA
    # - RSI at 50-60 level
    # - Price above both EMAs
    pass

@pytest.fixture
def sample_ohlcv_downtrend():
    """OHLCV data in downtrend."""
    pass

@pytest.fixture
def sample_ohlcv_squeeze():
    """OHLCV data with BB squeeze."""
    pass

# Test each generator
async def test_ema_trend_rsi_entry_signal():
    """EMA generator detects entry conditions."""
    strategy = Strategy(
        id="test",
        template_id="ema_trend_rsi",
        parameters={'fast_ema': 10, 'slow_ema': 50, ...}
    )

    data = sample_ohlcv_uptrend()
    generator = EMATrendRSIGenerator()
    signal = await generator.generate_signal(strategy, "BTCUSDT", data)

    assert signal.type == SignalType.LONG_ENTRY
    assert signal.stop_loss is not None
    assert signal.take_profit is not None

async def test_ema_trend_rsi_exit_signal():
    """EMA generator detects exit conditions."""
    # Test with data that triggers exit
    pass

async def test_bb_squeeze_entry_signal():
    """BB generator detects squeeze breakout."""
    pass

# Test for all 7 generators
# Test entry and exit conditions
# Test NO_SIGNAL when conditions not met
# Test metadata includes indicator values
```

**Acceptance Criteria:**
- ✓ Each generator has entry/exit tests
- ✓ NO_SIGNAL tested
- ✓ Stop loss/take profit calculations verified
- ✓ Metadata verified
- ✓ >85% coverage
- ✓ All tests pass

---

## SECTION 5.3 & 5.4: DEFERRED TO SESSION 5B

Sections 5.3 (Backtest Engine) and 5.4 (Paper Trading) will be implemented in **SESSION 5B** due to their interdependencies and testing requirements.

---

## ✅ SESSION 5A COMPLETION CHECKLIST

**Code Quality:**
- [ ] All 10 tasks in Section 5.1 completed
- [ ] All 10 tasks in Section 5.2 completed
- [ ] 100% type hints across all code
- [ ] Zero technical debt
- [ ] >85% test coverage
- [ ] All tests passing
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] isort check passes

**Functionality:**
- [ ] All 7 templates load from YAML
- [ ] Template verification passes on startup
- [ ] All 7 signal generators working
- [ ] Signals generated for all 7 templates
- [ ] Strategy similarity check rejects >70% similar
- [ ] Regime manager working with 5 regimes
- [ ] Status transitions follow state machine
- [ ] API endpoints tested

**Integration:**
- [ ] StrategyEngine integrates with TemplateManager
- [ ] StrategyEngine integrates with DataStore
- [ ] Signal generators integrate with MarketDataService
- [ ] Regime manager persists to database
- [ ] All database migrations applied

**Verification:**
- [ ] Production audit Grade A- or higher
- [ ] No security issues
- [ ] All decision requirements met (DEC-2026-02-08-XXX)

---

**Next Step:** SESSION 5B begins with Section 5.3 (Backtest Engine) and Section 5.4 (Paper Trading)

**Duration:** ~44 hours
**Target Completion:** Production-grade, 90%+ coverage, Grade A+ readiness
