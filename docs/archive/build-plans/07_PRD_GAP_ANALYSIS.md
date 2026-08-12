# PRD REQUIREMENTS GAP ANALYSIS
## MVP Task List vs PRD Verification

**Analyzed By:** Claude  
**Date:** 2026-02-06  
**Status:** COMPLETE - Gaps Identified with Subtask Recommendations

---

## EXECUTIVE SUMMARY

After systematic comparison of the 6 MVP Phase files (187 tasks) against PRD requirements (Parts 2-9), I identified **15 gaps** requiring subtasks. The task numbering will be preserved; only subtasks are added.

**Key Findings:**
- ✅ **7 features fully covered** (L, Reliability B/C, Strategy lifecycle, Backtest, Paper trading, Core risk)
- ⚠️ **8 features partially covered** (A, H, I, J, Safety A/B/C/E)
- ❌ **7 features missing or minimally covered** (B, C, D, E, F, G, K, Safety D, Reliability A)

---

## DETAILED GAP ANALYSIS

### ❌ MISSING: Feature B - Manual Regime Tagging
**PRD 2.2.1 Feature B requires:**
- Regime options: trending_up, trending_down, ranging, volatile, unknown
- Strategy regime preferences (work well in / avoid)
- Mismatch action: reduce size by 50%
- Dashboard dropdown for manual regime setting

**Current Coverage:** Not addressed in any phase

**Recommended Subtasks:**

```
### Task 5.1.3a: Implement Market Regime Manager
- [ ] **Status:** Not Started
- **Description:** Manual regime tagging system per PRD Feature B
- **Dependencies:** [5.1.3]
- **Effort:** 2 hours

**Add to:** `src/core/strategy/regime.py`

**MarketRegime enum:** TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, UNKNOWN (default)

**RegimeManager:**
- get_current_regime() -> MarketRegime
- set_regime(regime: MarketRegime, operator_note: str)
- get_regime_history() -> List[RegimeChange]

**Integration with strategies:**
- Strategy template defines `preferred_regimes` and `avoid_regimes`
- On mismatch: reduce position size by 50%
- Log regime mismatch decisions

**Acceptance Criteria:**
- [ ] Regime enum defined
- [ ] Manual regime setting via API
- [ ] Strategy regime preference checking
- [ ] 50% size reduction on mismatch
- [ ] Unit test: regime checking
```

```
### Task 6.2.3a: Add Regime Dashboard Dropdown
- [ ] **Status:** Not Started  
- **Description:** Dashboard dropdown for manual regime selection per PRD Feature B
- **Dependencies:** [6.2.3, 5.1.3a]
- **Effort:** 1 hour

**Add to:** `GET /api/dashboard` response and `PUT /api/system/regime`

**Dashboard data includes:**
- current_regime: string
- regime_options: list of valid regimes
- regime_changed_at: timestamp
- regime_changed_by: operator name

**Endpoint:** `PUT /api/system/regime` - Set current market regime

**Acceptance Criteria:**
- [ ] Regime in dashboard response
- [ ] Regime update endpoint works
- [ ] Audit trail for changes
```

---

### ❌ MISSING: Feature C - Dead Man's Switch
**PRD 2.2.1 Feature C requires:**
- Heartbeat interval: 5 minutes
- Max missed heartbeats: 6 (30 minutes)
- Action on trigger: close all positions
- Telegram alert before closing
- Require manual restart after trigger

**Current Coverage:** Kill Switch exists (3.2.1-3.2.6) but Dead Man's Switch is DIFFERENT - it monitors if the system itself stops responding

**Recommended Subtasks:**

```
### Task 3.2.6a: Implement Dead Man's Switch
- [ ] **Status:** Not Started
- **Description:** Auto-close if system stops responding per PRD Feature C
- **Dependencies:** [3.2.1, 6.3.2]
- **Effort:** 3 hours

**File:** `src/core/risk/dead_mans_switch.py`

**DeadMansSwitch class:**
```python
class DeadMansSwitch:
    HEARTBEAT_INTERVAL_MINUTES = 5
    MAX_MISSED_HEARTBEATS = 6  # 30 minutes total
    
    def __init__(self, data_store, alert_manager, execution_engine):
        self._last_heartbeat = datetime.utcnow()
        self._missed_count = 0
        self._triggered = False
    
    async def record_heartbeat(self):
        """Called by orchestrator main loop."""
        self._last_heartbeat = datetime.utcnow()
        self._missed_count = 0
    
    async def check_heartbeat(self) -> bool:
        """Called by external watchdog process."""
        # Returns True if system is healthy
        pass
    
    async def trigger(self):
        """Close all positions and require manual restart."""
        await self._send_telegram_warning()
        await asyncio.sleep(60)  # 1 minute warning
        await self._close_all_positions()
        self._triggered = True
        raise DeadMansSwitchTriggered()
```

**Watchdog:** Separate lightweight process that calls check_heartbeat() every 5 minutes

**Acceptance Criteria:**
- [ ] Heartbeat recorded in main loop
- [ ] Watchdog detects missed heartbeats
- [ ] Telegram warning sent before close
- [ ] All positions closed on trigger
- [ ] Manual restart required
- [ ] Unit test: trigger scenarios
```

---

### ❌ MISSING: Feature D - Strategy Similarity Check
**PRD 2.2.1 Feature D requires:**
- Similarity threshold: 70%
- Check dimensions: template_type (+40%), parameter_distance (+30%), symbol_overlap (+20%), entry_logic (+10%)
- Reject if too similar to existing active strategy

**Current Coverage:** Not addressed

**Recommended Subtasks:**

```
### Task 5.1.2a: Implement Strategy Similarity Check
- [ ] **Status:** Not Started
- **Description:** Reject strategies too similar to existing ones per PRD Feature D
- **Dependencies:** [5.1.2]
- **Effort:** 2.5 hours

**Add to:** `src/core/strategy/engine.py`

**Method:** `check_similarity(new_strategy, existing_strategies) -> SimilarityResult`

**Similarity scoring:**
- Same template type: +40%
- Parameter distance < 20% normalized: +30%
- Symbol overlap > 50%: +20%
- Same entry conditions: +10%

**SimilarityResult:**
```python
@dataclass
class SimilarityResult:
    is_too_similar: bool
    similarity_pct: float
    most_similar_strategy_id: Optional[str]
    breakdown: Dict[str, float]  # template, params, symbols, logic
```

**Integration:** Call during strategy creation, reject if similarity > 70%

**Acceptance Criteria:**
- [ ] Similarity calculation correct
- [ ] Rejects similar strategies with explanation
- [ ] Compares against all active strategies
- [ ] Unit test: similarity scenarios
```

---

### ❌ MISSING: Feature E - Entry Timing Coordination
**PRD 2.2.1 Feature E requires:**
- Stagger entries: 30 seconds between
- Max 3 entries per minute
- Same symbol cooldown: 5 minutes
- Priority by Sharpe ratio
- Exception: Kill switch and stop losses bypass

**Current Coverage:** Not addressed

**Recommended Subtasks:**

```
### Task 6.1.3a: Implement Entry Timing Coordinator
- [ ] **Status:** Not Started
- **Description:** Coordinate entry timing across strategies per PRD Feature E
- **Dependencies:** [6.1.3]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**EntryCoordinator class:**
```python
class EntryCoordinator:
    MIN_SECONDS_BETWEEN_ENTRIES = 30
    MAX_ENTRIES_PER_MINUTE = 3
    SAME_SYMBOL_COOLDOWN_MINUTES = 5
    
    def __init__(self):
        self._entry_times: List[datetime] = []
        self._symbol_cooldowns: Dict[str, datetime] = {}
        self._pending_entries: List[PendingEntry] = []
    
    async def queue_entry(self, signal: Signal, strategy: Strategy):
        """Add entry to queue with priority."""
        pass
    
    async def process_queue(self):
        """Process entries respecting timing rules."""
        # Sort by Sharpe (highest first)
        # Respect cooldowns
        # Stagger entries
        pass
    
    def can_enter_now(self, symbol: str) -> Tuple[bool, int]:
        """Check if entry allowed, return wait seconds if not."""
        pass
```

**Bypass rules:** Stop losses, take profits, and kill switch orders skip queue

**Acceptance Criteria:**
- [ ] Entries staggered by 30 seconds
- [ ] Max 3 entries per minute enforced
- [ ] Same-symbol 5-minute cooldown
- [ ] Priority by Sharpe ratio
- [ ] Bypass for SL/TP/kill switch
- [ ] Unit test: coordination scenarios
```

---

### ❌ MISSING: Feature F - Pre-Trade Slippage Estimation
**PRD 2.2.1 Feature F requires:**
- Estimate slippage BEFORE placing order
- Base slippage: 0.05%
- Size factor: (order_size / avg_daily_volume) * 0.5%
- Volatility factor: (current_ATR / avg_ATR) * 0.1%
- Spread factor: current_spread / 2
- Warn threshold: 0.3%, Block threshold: 1.0%
- Track estimated vs actual for model improvement

**Current Coverage:** Task 4.4.1 tracks AFTER the trade, not before

**Recommended Subtasks:**

```
### Task 4.4.1a: Implement Pre-Trade Slippage Estimation
- [ ] **Status:** Not Started
- **Description:** Estimate slippage before order placement per PRD Feature F
- **Dependencies:** [4.4.1, 2.2.4]
- **Effort:** 2.5 hours

**Add to:** `src/core/execution/quality.py`

**SlippageEstimator class:**
```python
class SlippageEstimator:
    BASE_SLIPPAGE_PCT = 0.05
    WARN_THRESHOLD_PCT = 0.3
    BLOCK_THRESHOLD_PCT = 1.0
    
    async def estimate_slippage(
        self,
        symbol: str,
        order_size: float,
        side: str
    ) -> SlippageEstimate:
        """
        Estimate expected slippage before placing order.
        
        Components:
        - base_slippage = 0.05%
        - size_factor = (order_size / avg_daily_volume) * 0.5%
        - volatility_factor = (current_ATR / avg_ATR) * 0.1%
        - spread_factor = current_spread / 2
        """
        pass

@dataclass
class SlippageEstimate:
    estimated_slippage_pct: float
    components: Dict[str, float]  # base, size, volatility, spread
    should_warn: bool  # > 0.3%
    should_block: bool  # > 1.0%
    recommended_action: str
```

**Integration:** Call before order submission, warn or block based on estimate

**Model improvement:** Compare estimated vs actual, recalibrate weekly

**Acceptance Criteria:**
- [ ] All slippage components calculated
- [ ] Warn threshold alerts operator
- [ ] Block threshold prevents order
- [ ] Comparison with actual recorded
- [ ] Unit test: estimation scenarios
```

---

### ❌ MISSING: Feature G - Capital Allocation Rules
**PRD 2.2.1 Feature G requires:**
- Minimum cash reserve: 20%
- Emergency buffer: 10%
- New strategy max: 5%
- Proven strategy max: 15%
- Strategy graduation: 30 days profitable, 20+ trades → can increase by 5%

**Current Coverage:** Not addressed

**Recommended Subtasks:**

```
### Task 3.1.6a: Implement Capital Allocation Rules
- [ ] **Status:** Not Started
- **Description:** Systematic capital allocation per PRD Feature G
- **Dependencies:** [3.1.6]
- **Effort:** 2.5 hours

**Add to:** `src/core/risk/controller.py`

**CapitalAllocator class:**
```python
class CapitalAllocator:
    MINIMUM_CASH_RESERVE_PCT = 20
    EMERGENCY_BUFFER_PCT = 10
    NEW_STRATEGY_MAX_PCT = 5
    PROVEN_STRATEGY_MAX_PCT = 15
    GRADUATION_DAYS = 30
    GRADUATION_MIN_TRADES = 20
    
    def get_available_capital(self, portfolio: PortfolioState) -> float:
        """Capital available for new positions (excludes reserves)."""
        total = portfolio.total_equity
        reserved = total * (self.MINIMUM_CASH_RESERVE_PCT + self.EMERGENCY_BUFFER_PCT) / 100
        return max(0, portfolio.cash_balance - reserved)
    
    def get_max_allocation(self, strategy: Strategy) -> float:
        """Max % of portfolio for this strategy."""
        if self._is_proven(strategy):
            return self.PROVEN_STRATEGY_MAX_PCT
        return self.NEW_STRATEGY_MAX_PCT
    
    def _is_proven(self, strategy: Strategy) -> bool:
        """Check if strategy qualifies as proven."""
        # 30+ days profitable, 20+ trades
        pass
    
    def check_graduation(self, strategy: Strategy) -> Optional[float]:
        """Check if strategy can increase allocation."""
        # Returns new allocation if eligible, None otherwise
        pass
```

**Integration:** Call from RiskController before allowing position

**Acceptance Criteria:**
- [ ] Cash reserves enforced
- [ ] New vs proven limits work
- [ ] Graduation detection works
- [ ] Integration with risk checks
- [ ] Unit test: allocation scenarios
```

---

### ❌ MISSING: Feature K - Position Staleness Monitor
**PRD 2.2.1 Feature K requires:**
- Day trading: warn 24h, force review 48h, max 72h
- Swing trading: warn 7d, force review 14d, max 30d
- Actions: warn, add to review queue, auto-close (configurable)
- Exception: profitable positions get 50% extended threshold

**Current Coverage:** Not addressed

**Recommended Subtasks:**

```
### Task 4.3.5a: Implement Position Staleness Monitor
- [ ] **Status:** Not Started
- **Description:** Monitor and act on stale positions per PRD Feature K
- **Dependencies:** [4.3.5]
- **Effort:** 2 hours

**Add to:** `src/core/execution/position_tracker.py`

**PositionStalenessMonitor class:**
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
    }
}

class PositionStalenessMonitor:
    def check_staleness(self, position: Position) -> StalenessResult:
        """Check if position is stale based on strategy type."""
        # Profitable positions get 50% extension
        pass
    
    async def process_stale_positions(self):
        """Check all positions, alert or close as needed."""
        for position in await self.get_open_positions():
            result = self.check_staleness(position)
            if result.should_close:
                await self._auto_close(position)
            elif result.should_review:
                await self._add_to_review_queue(position)
            elif result.should_warn:
                await self._send_warning(position)
```

**Acceptance Criteria:**
- [ ] Thresholds by strategy type
- [ ] Profitable extension works
- [ ] Warnings sent
- [ ] Auto-close (if enabled)
- [ ] Unit test: staleness scenarios
```

---

### ⚠️ PARTIAL: Feature A - Portfolio Correlation Limits
**PRD 2.2.1 Feature A requires:**
- Max BTC exposure: 40%
- Max ETH exposure: 30%
- Max combined correlated exposure: 60%

**Current Coverage:** Task 3.3.6 implements correlation groups but doesn't specify the exact limits

**Recommended Addition to Task 3.3.6:**

```
**Add to Task 3.3.6 Acceptance Criteria:**
- [ ] BTC exposure capped at 40% of portfolio
- [ ] ETH exposure capped at 30% of portfolio
- [ ] Combined correlated exposure capped at 60%
- [ ] Check performed BEFORE allowing new entry

**Add to implementation:**
CORRELATION_LIMITS = {
    'BTCUSDT': 0.40,  # 40% max
    'ETHUSDT': 0.30,  # 30% max
    'correlated_total': 0.60  # 60% for any correlated group
}
```

---

### ⚠️ PARTIAL: Feature H - Data Quality Validation
**PRD 2.2.1 Feature H requires:**
- Max price age: 10 seconds
- Max price change: 10% per candle
- Required fields validation
- Gap handling: interpolate small gaps, pause on large

**Current Coverage:** Task 2.1.6 covers some validation but missing specific thresholds

**Recommended Addition to Task 2.1.6:**

```
**Add to Task 2.1.6 Acceptance Criteria:**
- [ ] Price age check: reject if > 10 seconds old
- [ ] Price change check: flag if > 10% in single candle
- [ ] Gap handling: interpolate if < 3 candles, pause if larger
- [ ] Stale data fallback: use last known good, alert operator
- [ ] Extreme outlier handling: ignore candle, log for review
```

---

### ⚠️ PARTIAL: Feature I - Order State Reconciliation
**PRD 2.2.1 Feature I requires:**
- Every 60 seconds
- Compare local open orders to exchange
- Compare local positions to exchange
- Auto-correct minor (<1%)
- Alert on major differences

**Current Coverage:** Task 4.3.5 syncs positions but doesn't cover order reconciliation

**Recommended Addition:**

```
### Task 4.2.8a: Implement Order State Reconciliation
- [ ] **Status:** Not Started
- **Description:** Reconcile order state with exchange per PRD Feature I
- **Dependencies:** [4.2.8]
- **Effort:** 2 hours

**Add to:** `src/core/execution/order_manager.py`

**Method:** `async reconcile_orders()`

**Reconciliation (every 60 seconds):**
1. Fetch all open orders from exchange
2. Compare to local order tracking
3. Handle discrepancies:
   - Order on exchange not local: Add to local, log warning
   - Order local not on exchange: Mark as filled/cancelled
   - Minor differences (<1%): Auto-correct, log
   - Major differences: Alert operator, pause trading

**Acceptance Criteria:**
- [ ] Runs every 60 seconds
- [ ] Detects all discrepancy types
- [ ] Auto-corrects minor issues
- [ ] Alerts on major issues
- [ ] Audit trail for all corrections
```

---

### ⚠️ PARTIAL: Feature J - Rate Limit Management
**PRD 2.2.1 Feature J requires:**
- Warning at 70% of limit
- Throttle at 85%
- Emergency at 95%
- Priority ordering during throttle

**Current Coverage:** Task 2.1.2 has basic rate limiting but missing thresholds and priority

**Recommended Addition to Task 2.1.2:**

```
**Add to Task 2.1.2 Acceptance Criteria:**
- [ ] Warning triggered at 70% usage
- [ ] Throttling begins at 85% (add delays to non-critical)
- [ ] Emergency mode at 95% (critical orders only)
- [ ] Priority during throttle: SL/TP > entries > data

**Add to implementation:**
RATE_LIMIT_THRESHOLDS = {
    'warning_pct': 70,
    'throttle_pct': 85,
    'emergency_pct': 95
}

PRIORITY_ORDER = [
    'stop_loss', 'take_profit', 'kill_switch',  # Always allowed
    'new_entry',  # Delayed during throttle
    'data_fetch'  # Lowest priority
]
```

---

### ⚠️ PARTIAL: Safety A - Volatility Filter
**PRD 2.2.3 Safety A requires:**
- Normal: < 3% ATR
- Elevated: 3-5% (reduce size by 50%)
- Extreme: > 5% (exits only)
- Cooldown: Wait 4 hours after vol drops

**Current Coverage:** Task 3.4.1-3.4.2 exist but thresholds not specified

**Recommended Addition to Task 3.4.1:**

```
**Add to Task 3.4.1 Acceptance Criteria:**
- [ ] Normal regime: ATR/Price < 3%
- [ ] Elevated regime: ATR/Price 3-5% → 50% size reduction
- [ ] Extreme regime: ATR/Price > 5% → exits only
- [ ] Cooldown: 4 hours after vol drops below threshold
- [ ] Widen stops by 50% in elevated
```

---

### ⚠️ PARTIAL: Safety B - Weekend/Holiday Awareness
**PRD 2.2.3 Safety B requires:**
- Weekend: Saturday 00:00 UTC to Sunday 23:59 UTC
- Position size multiplier: 0.5
- Min volume multiplier: 2.0
- Major holidays defined

**Current Coverage:** Task 3.4.3 mentions weekends but missing specific adjustments

**Recommended Addition to Task 3.4.3:**

```
**Add to Task 3.4.3 Acceptance Criteria:**
- [ ] Weekend detection: Sat 00:00 - Sun 23:59 UTC
- [ ] Position size reduced to 50% on weekends
- [ ] Volume requirement doubled on weekends
- [ ] Holiday calendar: Christmas (Dec 24-26), New Year (Dec 31-Jan 2), Chinese New Year
- [ ] Holiday mode applies weekend rules
```

---

### ⚠️ PARTIAL: Safety C - Emergency Contact Escalation
**PRD 2.2.3 Safety C requires:**
- Primary: Telegram
- Secondary: Email
- Tertiary: SMS
- Escalation rules by severity

**Current Coverage:** Task 6.3.2 has Telegram only

**Recommended Addition:**

```
### Task 6.3.2a: Implement Multi-Channel Alerting
- [ ] **Status:** Not Started
- **Description:** Email and SMS escalation per PRD Safety C
- **Dependencies:** [6.3.2]
- **Effort:** 2.5 hours

**Add to:** `src/core/alerting/channels/`

**Additional channels:**
- `email.py` - Email via SMTP or SendGrid
- `sms.py` - SMS via Twilio

**Escalation rules:**
```python
ESCALATION_RULES = {
    'normal': {
        'channels': ['telegram'],
        'repeat': False
    },
    'warning': {
        'channels': ['telegram'],
        'repeat_after_minutes': 30,
        'max_repeats': 3
    },
    'critical': {
        'channels': ['telegram', 'email'],
        'repeat_after_minutes': 15,
        'max_repeats': 5
    },
    'emergency': {
        'channels': ['telegram', 'email', 'sms'],
        'repeat_after_minutes': 5,
        'until': 'acknowledged'
    }
}
```

**Acceptance Criteria:**
- [ ] Email sending works
- [ ] SMS sending works (via Twilio)
- [ ] Escalation rules followed
- [ ] Emergency alerts repeat until ack
```

---

### ⚠️ PARTIAL: Safety E - Startup Checklist
**PRD 2.2.3 Safety E requires:**
- Pre-start checks: DB, API, config, disk, memory
- Position sync on startup
- Balance check
- Strategy validation
- Fail → don't start

**Current Coverage:** Task 6.1.5 has health checks but missing full startup checklist

**Recommended Addition:**

```
### Task 6.1.1a: Implement Startup Checklist
- [ ] **Status:** Not Started
- **Description:** Full pre-start verification per PRD Safety E
- **Dependencies:** [6.1.1]
- **Effort:** 2 hours

**Add to:** `src/core/orchestrator.py`

**Pre-start checklist:**
```python
async def _run_startup_checklist(self) -> StartupResult:
    checks = [
        ('database_connection', self._check_db),
        ('database_integrity', self._check_db_integrity),
        ('exchange_api_auth', self._check_api_auth),
        ('exchange_api_permissions', self._check_api_perms),
        ('config_valid', self._check_config),
        ('disk_space', self._check_disk),  # > 1GB free
        ('memory_available', self._check_memory),  # > 500MB free
    ]
    
    for name, check_fn in checks:
        result = await check_fn()
        if not result.passed:
            return StartupResult(success=False, failed_check=name)
    
    # Position sync (compare but don't auto-correct)
    sync_result = await self._sync_positions_on_startup()
    if sync_result.has_mismatch:
        await self._alert_position_mismatch(sync_result)
        # Don't start, require manual review
        return StartupResult(success=False, failed_check='position_sync')
    
    # Balance check
    balance = await self._check_balance()
    if not balance.sufficient:
        return StartupResult(success=False, failed_check='balance')
    
    # Strategy validation
    strategies = await self._validate_all_strategies()
    if strategies.has_errors:
        return StartupResult(success=False, failed_check='strategies')
    
    return StartupResult(success=True)
```

**On failure:** Do NOT start trading, alert operator

**Acceptance Criteria:**
- [ ] All checks run before main loop
- [ ] Any failure prevents startup
- [ ] Position mismatch requires manual resolution
- [ ] Alert sent on startup failure
```

---

### ❌ MISSING: Safety D - Configuration Backup & Restore
**PRD 2.2.3 Safety D requires:**
- Daily backups at 00:00 UTC
- 30 daily + 12 monthly retention
- One-click restore
- RTO: 4 hours, RPO: 24 hours

**Current Coverage:** Not addressed

**Recommended Addition:**

```
### Task 1.3.7a: Implement Configuration Backup System
- [ ] **Status:** Not Started
- **Description:** Automated config backup per PRD Safety D
- **Dependencies:** [1.3.7]
- **Effort:** 3 hours

**File:** `src/core/config/backup.py`

**ConfigBackupManager:**
```python
class ConfigBackupManager:
    BACKUP_TIME = "00:00"  # UTC
    DAILY_RETENTION = 30
    MONTHLY_RETENTION = 12
    
    def __init__(self, storage_backend):
        self.storage = storage_backend  # Local or cloud
    
    async def create_backup(self) -> Backup:
        """Create backup of all configuration."""
        data = {
            'strategies': await self._export_strategies(),
            'risk_config': await self._export_risk_config(),
            'accounts': await self._export_accounts(),
            'positions': await self._export_positions(),
            'system_state': await self._export_state(),
        }
        return await self.storage.save(data)
    
    async def restore_backup(self, backup_id: str):
        """Restore from backup."""
        pass
    
    async def list_backups(self) -> List[Backup]:
        """List available backups."""
        pass
```

**Schedule:** Runs daily at 00:00 UTC via orchestrator

**Acceptance Criteria:**
- [ ] Daily backups created
- [ ] Retention policy enforced
- [ ] Restore works correctly
- [ ] Encrypted if using cloud storage
- [ ] Health check after restore
```

---

### ❌ MISSING: Reliability A - Graceful Degradation
**PRD 2.2.2 Reliability A requires:**
- Exchange API down → read-only mode
- Database slow → cache + queue
- Strategy error → skip, continue others
- Memory pressure → clear caches

**Current Coverage:** Not explicitly addressed

**Recommended Addition:**

```
### Task 6.1.5a: Implement Graceful Degradation
- [ ] **Status:** Not Started
- **Description:** Continue operating when components fail per PRD Reliability A
- **Dependencies:** [6.1.5]
- **Effort:** 2.5 hours

**Add to:** `src/core/orchestrator.py`

**Degradation handlers:**
```python
class DegradationManager:
    async def handle_exchange_api_down(self):
        """Switch to read-only mode."""
        self._read_only = True
        await self._alert('Exchange API down, read-only mode')
        # Continue monitoring positions but no new trades
    
    async def handle_database_slow(self):
        """Use cache and queue writes."""
        self._use_cache_only = True
        self._queue_writes = True
        await self._alert('Database slow, using cache')
    
    async def handle_strategy_error(self, strategy_id: str, error: Exception):
        """Skip failing strategy, continue others."""
        await self._mark_strategy_error(strategy_id, error)
        await self._alert(f'Strategy {strategy_id} error, skipping')
        # Don't stop other strategies
    
    async def handle_memory_pressure(self):
        """Clear caches to free memory."""
        await self._clear_market_data_cache()
        await self._clear_indicator_cache()
        gc.collect()
```

**Auto-recovery:** Resume normal operation when issue resolves

**Acceptance Criteria:**
- [ ] Each scenario handled
- [ ] System continues operating
- [ ] Alerts sent
- [ ] Auto-recovery works
```

---

### ⚠️ PARTIAL: Reliability C - Health Check Endpoints
**PRD 2.2.2 Reliability C requires:**
- `/health` - overall status
- `/health/detailed` - component breakdown
- `/health/strategies` - per-strategy status

**Current Coverage:** Task 6.2.1 has basic `/health`

**Recommended Addition to Task 6.2.1:**

```
**Add to Task 6.2.1 Acceptance Criteria:**
- [ ] /health returns overall_status: healthy|degraded|unhealthy
- [ ] /health/detailed returns:
  - database_latency_ms
  - exchange_api_status
  - active_strategies_count
  - open_positions_count
  - last_trade_time
  - memory_usage_pct
  - error_count_last_hour
- [ ] /health/strategies returns per-strategy:
  - last_evaluation_time
  - consecutive_errors
  - current_drawdown
```

---

## SUMMARY OF REQUIRED ADDITIONS

| Phase | Task | Addition Type | Feature |
|-------|------|---------------|---------|
| 1 | 1.3.7a | New subtask | Safety D (Backup) |
| 2 | 2.1.2 | Update criteria | Feature J (Rate limits) |
| 2 | 2.1.6 | Update criteria | Feature H (Data quality) |
| 3 | 3.1.6a | New subtask | Feature G (Capital allocation) |
| 3 | 3.2.6a | New subtask | Feature C (Dead man's switch) |
| 3 | 3.3.6 | Update criteria | Feature A (Correlation limits) |
| 3 | 3.4.1 | Update criteria | Safety A (Volatility thresholds) |
| 3 | 3.4.3 | Update criteria | Safety B (Weekend/holiday) |
| 4 | 4.2.8a | New subtask | Feature I (Order reconciliation) |
| 4 | 4.3.5a | New subtask | Feature K (Position staleness) |
| 4 | 4.4.1a | New subtask | Feature F (Pre-trade slippage) |
| 5 | 5.1.2a | New subtask | Feature D (Similarity check) |
| 5 | 5.1.3a | New subtask | Feature B (Regime manager) |
| 6 | 6.1.1a | New subtask | Safety E (Startup checklist) |
| 6 | 6.1.3a | New subtask | Feature E (Entry coordination) |
| 6 | 6.1.5a | New subtask | Reliability A (Degradation) |
| 6 | 6.2.1 | Update criteria | Reliability C (Health endpoints) |
| 6 | 6.2.3a | New subtask | Feature B (Regime dropdown) |
| 6 | 6.3.2a | New subtask | Safety C (Multi-channel alerts) |

**Total New Subtasks:** 14  
**Total Updated Tasks:** 8  
**New Effort Estimate:** ~32 additional hours

---

## NEXT STEPS

1. **Review this analysis** with project stakeholders
2. **Prioritize gaps** - some may be deferred to post-MVP
3. **Add subtasks** to respective phase files
4. **Update task counts** in index file if needed
5. **Re-estimate timeline** (may need +1 week for 32 hours of additions)

---

**Analysis Complete**
