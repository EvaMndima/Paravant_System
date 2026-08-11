# PERSONAL AUTONOMOUS TRADING SYSTEM
# PRODUCT REQUIREMENTS DOCUMENT (PRD)

**Document Version:** 1.0  
**Created:** 2026-02-03  
**Last Updated:** 2026-06-04 (cross-reference to Research Layer PRD v2.0 added)  
**Status:** LOCKED FOR DEVELOPMENT  
**Author:** Nai (System Owner) + Claude (Technical Architect)

**Related PRDs:**
- [`docs/research/RESEARCH_LAYER_PRD.md`](research/RESEARCH_LAYER_PRD.md) — **Research Layer PRD v2.0** (ratified 2026-06-04, DEC-2026-06-04-001 through DEC-2026-06-04-012). Governs the `research/` module that produces strategies feeding into this trading system. Does NOT advance MVP scope (DEC-2026-06-04-007). Adds Tier A/B/C/D classification + DSR p<0.3 floor as additional gate ABOVE the auto-promotion gate of DEC-2026-06-01-001/002 (which require amendment for opt-in deployment per DEC-2026-06-04-009).

---

# TABLE OF CONTENTS

1. [PART 1: VISION & STRATEGIC CONTEXT](#part-1-vision--strategic-context)
2. [PART 2: MVP SCOPE DEFINITION](#part-2-mvp-scope-definition)
3. [PART 3: STRATEGY SYSTEM SPECIFICATION](#part-3-strategy-system-specification)
4. [PART 4: RISK MANAGEMENT SPECIFICATION](#part-4-risk-management-specification)
5. [PART 5: EXECUTION SYSTEM SPECIFICATION](#part-5-execution-system-specification)
6. [PART 6: MONITORING & DASHBOARD SPECIFICATION](#part-6-monitoring--dashboard-specification)
7. [PART 7: ACCOUNT MANAGEMENT SPECIFICATION](#part-7-account-management-specification)
8. [PART 8: ALERTING SYSTEM SPECIFICATION](#part-8-alerting-system-specification)
9. [PART 9: DATA MANAGEMENT SPECIFICATION](#part-9-data-management-specification)
10. [PART 10: V1 ROADMAP](#part-10-v1-roadmap)
11. [PART 11: V2 ROADMAP](#part-11-v2-roadmap)
12. [PART 12: MATURITY ROADMAP](#part-12-maturity-roadmap)
13. [PART 13: 5-10 YEAR EVERYTHING SYSTEM VISION](#part-13-5-10-year-everything-system-vision)
14. [PART 14: NON-FUNCTIONAL REQUIREMENTS](#part-14-non-functional-requirements)
15. [PART 15: SUCCESS CRITERIA & ACCEPTANCE TESTS](#part-15-success-criteria--acceptance-tests)
16. [PART 16: GLOSSARY & DEFINITIONS](#part-16-glossary--definitions)
17. [APPENDIX A: API REFERENCE](#appendix-a-api-reference)
18. [APPENDIX B: CONFIGURATION REFERENCE](#appendix-b-configuration-reference)
19. [APPENDIX C: STRATEGY TEMPLATES CATALOG](#appendix-c-strategy-templates-catalog)

---

# PART 1: VISION & STRATEGIC CONTEXT

## 1.1 Mission Statement

**Build a private, production-grade autonomous trading system that reliably generates income for a single operator, with deterministic execution, rigorous risk controls, full auditability, and the confidence to operate without constant supervision.**

The system exists to buy freedom — financial stability and time independence — not to be impressive or complex for its own sake.

## 1.2 What This System IS

- A **personal trading system** for a single operator (you)
- A **profit-generating machine** with explicit income targets
- A **trustworthy system** that fails loudly, never silently
- An **explainable system** where every decision can be understood
- A **calm system** that reduces anxiety through information and control
- A **professional-grade system** built to institutional standards
- An **evolvable system** designed to grow toward comprehensive capabilities over 5-10 years

## 1.3 What This System IS NOT

- NOT a SaaS platform for external users
- NOT a client-facing product (no family, no friends, no managed accounts)
- NOT a hedge fund infrastructure (no performance fees, no compliance for external capital)
- NOT a research toy or experiment without profit goals
- NOT a fully autonomous AI that operates without human oversight
- NOT an "everything" system on day one

## 1.4 Target User

**Primary User:** Single operator (Nai)
- Background: Manual forex trading experience
- Goal: Automate trading for income generation and time freedom
- Risk tolerance: Moderate (prefers steady income over maximum returns)
- Technical involvement: Operator level (not building strategies from scratch)
- Time commitment: 2-10 hours/week for operations after system is stable

**There are no other users.** For the next 24 months minimum, this system serves exactly one person.

## 1.5 Core Values (Ranked)

1. **Capital Preservation** — Never lose more than defined limits. Survive to trade another day.
2. **Profit Generation** — Make money reliably. This is not a hobby.
3. **Operational Clarity** — Know what's happening, what went wrong, and what to do about it.
4. **Time Freedom** — The system works whether you're watching or not.
5. **Continuous Improvement** — Learn from every trade, every decision, every mistake.

## 1.6 Success Definition

Success is NOT:
- Having the most features
- Using the latest technology
- Impressing anyone

Success IS:
- **Monthly profitability** — More green months than red months
- **Controlled drawdowns** — Never exceeding defined risk limits
- **Operational peace** — Checking the system weekly without anxiety
- **Understanding** — Knowing why trades were made and why they won or lost
- **Growth** — Increasing capital allocation as trust builds

### Quantified Success Criteria (12-24 months)

| Metric | Target |
|--------|--------|
| Monthly win rate | > 55% of months profitable |
| Maximum drawdown | Never exceeds 15% |
| Weekly check-in time | < 2 hours when stable |
| System uptime | > 99% during market hours |
| Unexplained failures | Zero silent failures |
| Trade logging | 100% of trades explained |

## 1.7 Locked Decisions

The following decisions are **locked** and cannot be revisited until explicitly scheduled review dates:

| Decision | Locked Value | Review Date |
|----------|--------------|-------------|
| Operating model | Personal single-operator | Feb 2028 |
| Asset class (MVP) | Crypto only | After 12 months profitable |
| Broker (MVP) | Binance only | After 12 months profitable |
| Market type (MVP) | **Binance Spot** for LIVE execution; **margin/futures permitted in research/backtest layer only** (staged — see below) | Step 4 of staged plan |
| Trading style | Day trading & Swing (15m-4H primary, 1D secondary) | After 6 months profitable |
| Client accounts | None | Feb 2028 |
| Autonomy model | Human approval for live deployment | After V2 stable |
| Strategy generation | Template-based with manual approval | After V2 stable |

### 1.7.1 Market-Type Scope Expansion (2026-05-28, DEC-2026-05-28-001)

**Amends the previously implicit "spot only" sub-constraint of the broker lock.**

The research/backtest layer now supports both long-only spot and long-short futures execution modes so we can honestly evaluate whether short-side strategies have edge once realistic perpetual funding costs are charged. The previous state — where the backtest credited short P&L that spot live trading could not execute (research-audit finding PARA-01) — is resolved.

**Staged deployment plan** (live leverage is deferred until short edge is proven):

1. **Research-layer capability** — `BacktestConfig.allow_shorts` and `funding_rate_per_8h` enable honest long-only-spot vs long-short-futures backtests in the same engine. **DONE 2026-05-28.**
2. **Honest re-validation** — re-run the full strategy funnel in both modes; identify which short-side strategies (if any) retain edge after funding.
3. **Spot long-only go-live first** — deploy validated long-only strategies (e.g., BTP, VBB, SRC) on Binance spot to prove the live execution path end-to-end with zero liquidation risk.
4. **Live futures execution (gated)** — only if step 2 finds genuine short edge: build the Binance Futures execution adapter + liquidation/margin risk models + leverage controls, then deploy cautiously at small capital.

**Until step 4 completes, all live execution remains spot.** Withdrawals and futures execution are explicitly disabled at the Binance API key level (see § 16.5).

## 1.8 What We Learned From the Legacy System

The previous system (665 files, 85+ agents, 150,000+ lines) failed because:

1. **No locked vision** — Built everything for no one
2. **Scope creep** — Added features hoping they'd help, without validation
3. **No definition of done** — Never knew when to stop building
4. **Complexity without value** — Features that added risk without adding profit
5. **No clear workflow** — Couldn't explain what the system actually did

**This PRD exists to prevent those failures from recurring.**

## 1.9 What Actually Worked: The Lite Generator Lesson

The ML Strategy Generator Lite produced **65 strategies** while the full ML generator produced only **14** in the same time period. Initial analysis suggested fallbacks were the reason, but deeper analysis reveals:

**What Actually Happened:**
- Lite generator used 3 simple templates
- When ML failed, it fell back to Simple_MA template
- Result: ~45 of 65 strategies were nearly identical Simple_MA variants
- **The 65 number was misleading — there were really only ~20 unique strategies**

| What Seemed True | What's Actually True |
|------------------|---------------------|
| "Fallbacks ensure output" | Fallbacks create clutter of similar garbage |
| "65 > 14 strategies" | 20 unique > 45 clones + 20 unique |
| "Quantity enables quality" | Quantity of *diverse* strategies enables quality |

**Correct Principles for this build:**
1. **Simple > Complex** — Templates beat neural networks ✓
2. **NO fallbacks** — Better to fail than create clones ✓
3. **Diversity required** — Enforce minimum template diversity ✓
4. **Fail fast** — If generation fails, investigate why ✓
5. **Quality over quantity** — 20 diverse > 65 similar ✓

**Strategy Generation Rules (MVP):**
```yaml
generation_rules:
  fallback_on_failure: false       # DO NOT fall back to default template
  fail_fast: true                  # If generation fails, log and stop
  diversity_required: true         # Reject if too similar to existing
  max_strategies_per_template: 5   # Force template diversity
  similarity_threshold: 0.7        # Reject if >70% similar to existing
  
  similarity_check:
    - parameter_distance: "Euclidean distance of normalized params"
    - entry_logic_hash: "Hash of entry conditions must differ"
    - symbol_overlap: "Max 50% symbol overlap with existing"
```

---

# PART 2: MVP SCOPE DEFINITION

## 2.1 MVP Philosophy

**The MVP is the minimum system that can:**
1. Execute trades safely on Binance
2. Enforce risk limits without exception
3. Generate strategies from templates
4. Validate strategies through backtesting
5. Track P&L accurately
6. Alert the operator to problems
7. Provide visibility into system state

**The MVP is NOT trying to:**
- Discover novel alpha
- Optimize itself
- Detect market regimes automatically
- Support multiple brokers
- Generate reports for external parties
- Be impressive

## 2.2 The Seven MVP Capabilities

### Capability 1: Execution Engine
Place and track orders on Binance with reliable state management.

### Capability 2: Risk Controller
Enforce position limits, daily loss limits, and emergency kill switch.

### Capability 3: Strategy System
Template-based strategy generation with backtest and paper trading gates.

### Capability 4: Account Management
Support 2-3 account profiles with different risk parameters.

### Capability 5: P&L Tracking
Calculate and display daily/weekly/monthly P&L at portfolio and strategy level.

### Capability 6: Monitoring Dashboard
Display system health, positions, P&L, and regime indicators.

### Capability 7: Alerting System
Send critical alerts via Telegram for kill switch events and risk breaches.

## 2.2.1 Additional MVP Features (Critical for Autonomous Operation)

After critical analysis, these features are REQUIRED for safe autonomous operation:

### Feature A: Portfolio Correlation Limits
```yaml
portfolio_correlation_limits:
  description: "Prevent over-concentration when multiple strategies trade same direction"
  
  why_critical: |
    Without this: Strategy A long BTC + Strategy B long BTC + Strategy C long ETH 
    = You're 3x leveraged to crypto direction without knowing it
  
  implementation:
    max_btc_exposure_pct: 40        # Total BTC across all strategies
    max_eth_exposure_pct: 30        # Total ETH across all strategies
    max_correlated_exposure_pct: 60 # Strategies with correlation > 0.7
    check_before_entry: true        # Block new entries that exceed limits
```

### Feature B: Manual Regime Tagging
```yaml
manual_regime_tagging:
  description: "Operator can tag current market regime"
  
  why_critical: |
    Strategies have regime preferences. A trend-following strategy in ranging market = losses.
    Without regime awareness, all strategies run all the time.
  
  implementation:
    regime_options: ["trending_up", "trending_down", "ranging", "volatile", "unknown"]
    strategy_regime_preferences: "Each strategy specifies preferred regimes"
    mismatch_action: "Reduce position size by 50% if regime doesn't match"
    default_regime: "unknown"
    dashboard_dropdown: true
```

### Feature C: Dead Man's Switch
```yaml
dead_mans_switch:
  description: "Auto-close positions if system stops responding"
  
  why_critical: |
    If your server crashes while positions are open, you have no protection.
    Unattended positions can suffer unlimited loss.
  
  implementation:
    heartbeat_interval_minutes: 5
    max_missed_heartbeats: 6        # 30 minutes of no response
    action_on_trigger: "close_all_positions"
    notification: "Send Telegram alert before closing"
    resume_behavior: "Require manual restart after trigger"
```

### Feature D: Strategy Similarity Check (Anti-Clone)
```yaml
strategy_similarity_check:
  description: "Reject strategies too similar to existing ones"
  
  why_critical: |
    Learned from Lite generator: 45 of 65 strategies were clones.
    Clones don't add diversification.
  
  implementation:
    similarity_threshold: 0.7       # Reject if >70% similar
    check_dimensions:
      - template_type: "Same template = +40% similarity"
      - parameter_distance: "Close parameters = +30% similarity"  
      - symbol_overlap: "Same symbols = +20% similarity"
      - entry_logic: "Same entry conditions = +10% similarity"
    action_if_too_similar: "Reject with explanation"
```

### Feature E: Entry Timing Coordination
```yaml
entry_timing_coordination:
  description: "Prevent multiple strategies entering simultaneously on same signal"
  
  why_critical: |
    If 5 strategies all trigger BUY on the same candle:
    - You execute 5 orders in milliseconds
    - Each subsequent order gets worse fill (slippage)
    - You're effectively 5x leveraged on one decision
  
  implementation:
    stagger_entries: true
    min_seconds_between_entries: 30    # Wait 30s between strategy entries
    max_entries_per_minute: 3          # Max 3 new positions per minute
    same_symbol_cooldown_minutes: 5    # If Strategy A enters BTC, others wait 5min
    
    priority_rules:
      - higher_sharpe_first: true       # Better strategies get priority
      - smaller_position_first: false   # Or prioritize smaller positions
    
    exception: "Kill switch and stop losses bypass coordination"
```

### Feature F: Pre-Trade Slippage Estimation
```yaml
pre_trade_slippage_estimation:
  description: "Estimate slippage BEFORE placing order, not just track after"
  
  why_critical: |
    A strategy might backtest well, but if your position size causes 2% slippage,
    profits disappear. Need to know expected slippage before deciding to trade.
  
  implementation:
    estimation_model:
      base_slippage: 0.05%              # Minimum expected slippage
      size_factor: "(order_size / avg_daily_volume) * 0.5%"
      volatility_factor: "(current_ATR / avg_ATR) * 0.1%"
      spread_factor: "current_spread / 2"
    
    actions:
      warn_threshold: 0.3%              # Warn if estimated slippage > 0.3%
      block_threshold: 1.0%             # Block if estimated slippage > 1%
    
    tracking:
      compare_estimated_vs_actual: true # Learn and improve model
      adjust_model_weekly: true         # Recalibrate based on actual fills
```

### Feature G: Capital Allocation Rules
```yaml
capital_allocation_rules:
  description: "Systematic rules for how much capital per strategy"
  
  why_critical: |
    Without rules: "I'll put 20% in each strategy" leads to
    - 100% allocated after 5 strategies
    - No reserve for new opportunities
    - Forced liquidation if you need to add capital elsewhere
  
  implementation:
    portfolio_reserves:
      minimum_cash_reserve_pct: 20%     # Always keep 20% uninvested
      emergency_buffer_pct: 10%         # Extra buffer for drawdowns
    
    per_strategy_limits:
      new_strategy_max_pct: 5%          # New strategies start small
      proven_strategy_max_pct: 15%      # Max 15% in any single strategy
      strategy_graduation:
        days_profitable: 30             # Must be profitable 30 days
        min_trades: 20                  # Must have 20+ trades
        promotion_increase: 5%          # Can increase allocation by 5%
    
    rebalancing:
      trigger: "Monthly or on strategy retirement"
      method: "Equal risk contribution (risk parity lite)"
```

### Feature H: Data Quality Validation
```yaml
data_quality_validation:
  description: "Validate market data before using for decisions"
  
  why_critical: |
    Bad data = bad decisions. Exchange APIs sometimes return:
    - Stale prices (cached from minutes ago)
    - Zero values (API errors)
    - Extreme outliers (flash crash artifacts)
    - Missing candles (gaps in data)
  
  implementation:
    real_time_checks:
      max_price_age_seconds: 10         # Price must be < 10 seconds old
      max_price_change_pct: 10%         # Flag if price changed > 10% in 1 candle
      required_fields: ["open", "high", "low", "close", "volume"]
      min_volume: 0                     # Volume must be non-negative
    
    historical_checks:
      max_gap_candles: 3                # Max 3 missing candles allowed
      interpolation_method: "linear"    # How to fill small gaps
      action_on_large_gap: "pause_strategy"
    
    actions:
      on_stale_data: "Use last known good, alert operator"
      on_extreme_outlier: "Ignore candle, log for review"
      on_missing_data: "Interpolate if small gap, pause if large"
```

### Feature I: Order State Reconciliation
```yaml
order_state_reconciliation:
  description: "Ensure local order state matches exchange state"
  
  why_critical: |
    Network issues can cause:
    - Order placed but confirmation lost → think order failed, it didn't
    - Order cancelled but confirmation lost → think order active, it isn't
    - Partial fill not recorded → position size wrong
  
  implementation:
    reconciliation_frequency: "Every 60 seconds"
    
    checks:
      open_orders: "Compare local open orders to exchange"
      positions: "Compare local positions to exchange positions"
      balances: "Compare local balance to exchange balance"
    
    on_mismatch:
      minor_difference: "Log and auto-correct (< 1% difference)"
      major_difference: "Alert operator, pause trading"
      order_exists_not_in_local: "Add to local state, investigate"
      order_in_local_not_on_exchange: "Mark as filled/cancelled based on exchange"
    
    audit_trail:
      log_all_mismatches: true
      track_mismatch_frequency: true    # If frequent, investigate root cause
```

### Feature J: Rate Limit Management
```yaml
rate_limit_management:
  description: "Proactively manage API rate limits"
  
  why_critical: |
    Binance rate limits: 1200 requests/minute for orders
    If you hit limits: Orders rejected at worst possible time (during volatility)
  
  implementation:
    tracking:
      requests_per_minute: "Rolling count"
      weight_per_minute: "Binance uses request weight system"
    
    thresholds:
      warning_pct: 70%                  # Warn at 70% of limit
      throttle_pct: 85%                 # Start throttling at 85%
      emergency_pct: 95%                # Only critical orders at 95%
    
    throttling:
      delay_non_critical_ms: 500        # Add delay to non-critical requests
      batch_requests: true              # Batch where possible
      cache_market_data: true           # Don't refetch unnecessarily
    
    priority_during_throttle:
      1: "Stop losses and kill switch"
      2: "Take profits"
      3: "New entries"
      4: "Data fetching"
```

### Feature K: Position Staleness Monitor
```yaml
position_staleness_monitor:
  description: "Track and act on positions held too long"
  
  why_critical: |
    Day trading strategies shouldn't hold positions for weeks.
    A "stuck" position might indicate:
    - Strategy logic error
    - Exit condition never triggered
    - Partial fill left small position
  
  implementation:
    thresholds_by_strategy_type:
      day_trading:
        warning_hours: 24
        force_review_hours: 48
        max_hold_hours: 72
      swing_trading:
        warning_days: 7
        force_review_days: 14
        max_hold_days: 30
    
    actions:
      on_warning: "Alert operator"
      on_force_review: "Add to daily review queue"
      on_max_hold: "Auto-close with market order (configurable)"
    
    exceptions:
      profitable_position: "Extend threshold by 50%"
      operator_override: "Can mark position as 'intentionally long-term'"
```

### Feature L: Execution Quality Tracking
```yaml
execution_quality_tracking:
  description: "Track how well orders are being executed"
  
  why_critical: |
    Backtest assumes perfect fills. Reality:
    - Slippage eats into profits
    - Partial fills leave awkward positions
    - Rejected orders miss opportunities
  
  implementation:
    metrics_per_order:
      expected_price: "Price when signal generated"
      execution_price: "Actual fill price"
      slippage_bps: "(execution - expected) / expected * 10000"
      time_to_fill_ms: "Order placed to fill confirmed"
      fill_rate: "Filled quantity / ordered quantity"
    
    aggregates:
      avg_slippage_by_symbol: "Rolling 30-day average"
      avg_slippage_by_strategy: "Per-strategy execution quality"
      avg_slippage_by_time_of_day: "Is execution worse at certain times?"
      rejection_rate: "Orders rejected / orders attempted"
    
    actions:
      high_slippage_alert: "Notify if avg slippage > 0.5%"
      poor_fill_rate_alert: "Notify if fill rate < 95%"
      strategy_execution_penalty: "Reduce estimated returns by actual slippage"
```

## 2.2.2 MVP Reliability Features

These features ensure the system operates reliably:

### Reliability A: Graceful Degradation
```yaml
graceful_degradation:
  description: "System continues operating when components fail"
  
  scenarios:
    exchange_api_down:
      detection: "3 consecutive failed requests"
      action: "Switch to read-only mode, no new trades"
      recovery: "Auto-resume when API responds"
    
    database_slow:
      detection: "Query time > 5 seconds"
      action: "Use cached data, queue writes"
      recovery: "Process queue when DB recovers"
    
    strategy_error:
      detection: "Exception during strategy evaluation"
      action: "Skip strategy this cycle, continue others"
      recovery: "Retry next cycle, alert if persistent"
    
    memory_pressure:
      detection: "Memory usage > 80%"
      action: "Clear caches, reduce data retention"
      recovery: "Auto-recover as memory frees"
```

### Reliability B: Comprehensive Logging
```yaml
comprehensive_logging:
  description: "Log everything needed for debugging and audit"
  
  log_levels:
    DEBUG: "Detailed internal state (dev only)"
    INFO: "Normal operations, trade decisions"
    WARNING: "Anomalies, degraded operation"
    ERROR: "Failures requiring attention"
    CRITICAL: "System-wide issues, kill switch events"
  
  required_logs:
    every_trade:
      - signal_generation: "Why did strategy generate signal?"
      - risk_check: "Did risk controller approve? Why/why not?"
      - order_placement: "Order details, expected vs actual"
      - fill_confirmation: "Fill price, slippage, time"
    
    every_decision:
      - strategy_evaluation: "All strategies evaluated this cycle"
      - position_check: "Current positions and P&L"
      - risk_status: "Current risk utilization"
  
  retention:
    hot_storage: "30 days in database"
    cold_storage: "1 year in files"
    critical_events: "Forever"
```

### Reliability C: Health Check Endpoints
```yaml
health_check_endpoints:
  description: "Endpoints to verify system health"
  
  endpoints:
    /health:
      returns: "overall_status: healthy|degraded|unhealthy"
      checks: ["database", "exchange_api", "strategies"]
    
    /health/detailed:
      returns: "Status of each component"
      includes:
        - database_latency_ms
        - exchange_api_status
        - active_strategies_count
        - open_positions_count
        - last_trade_time
        - memory_usage_pct
        - error_count_last_hour
    
    /health/strategies:
      returns: "Per-strategy health status"
      includes:
        - last_evaluation_time
        - consecutive_errors
        - current_drawdown
  
  monitoring:
    external_ping: "Uptime service calls /health every minute"
    alert_on_unhealthy: "Telegram alert if unhealthy > 5 minutes"
```

## 2.2.3 MVP Safety Features

These features prevent catastrophic failures:

### Safety A: Volatility Filter
```yaml
volatility_filter:
  description: "Reduce or skip trading during extreme volatility"
  
  why_critical: |
    Extreme volatility = wider spreads, more slippage, unpredictable fills.
    Strategies backtested on normal vol may fail in extreme conditions.
  
  implementation:
    volatility_measure: "ATR(14) / Close price * 100"  # ATR as % of price
    
    thresholds:
      normal: "< 3%"                    # Normal trading
      elevated: "3% - 5%"               # Reduce position size by 50%
      extreme: "> 5%"                   # No new entries, exits only
    
    actions:
      on_elevated:
        - reduce_position_size: 0.5     # Half normal size
        - widen_stops: 1.5              # 50% wider stops
        - alert_operator: true
      
      on_extreme:
        - pause_new_entries: true
        - allow_exits: true             # Can still exit
        - tighten_trailing_stops: true  # Protect profits
        - alert_operator: "URGENT"
    
    cooldown: "Wait 4 hours after vol drops before resuming"
```

### Safety B: Weekend/Holiday Awareness
```yaml
weekend_awareness:
  description: "Adjust behavior during low-liquidity periods"
  
  why_needed: |
    Crypto trades 24/7, but weekends have:
    - Lower liquidity
    - Wider spreads
    - More erratic movements
    - Fewer market makers active
  
  implementation:
    weekend_definition: "Saturday 00:00 UTC to Sunday 23:59 UTC"
    
    adjustments:
      position_size_multiplier: 0.5     # Half size on weekends
      min_volume_multiplier: 2.0        # Require 2x normal volume
      spread_tolerance: 1.5             # Accept 50% wider spreads
      avoid_large_positions: true       # No position > 3% portfolio
    
    major_holidays:
      - christmas: "Dec 24-26"
      - new_year: "Dec 31-Jan 2"
      - chinese_new_year: "Variable"    # Low Asia liquidity
    
    holiday_mode: "Weekend rules apply"
```

### Safety C: Emergency Contact Escalation
```yaml
emergency_escalation:
  description: "Multi-channel alerts for critical events"
  
  why_needed: |
    Telegram might be down or unread.
    Critical events need multiple contact methods.
  
  channels:
    primary: "Telegram"
    secondary: "Email"
    tertiary: "SMS (via Twilio)"
  
  escalation_rules:
    normal_alert:
      channels: ["telegram"]
      repeat: false
    
    warning_alert:
      channels: ["telegram"]
      repeat_after_minutes: 30
      max_repeats: 3
    
    critical_alert:
      channels: ["telegram", "email"]
      repeat_after_minutes: 15
      max_repeats: 5
    
    emergency_alert:
      channels: ["telegram", "email", "sms"]
      repeat_after_minutes: 5
      until: "acknowledged"
  
  emergency_triggers:
    - kill_switch_activated
    - daily_loss_limit_hit
    - system_unhealthy_30_min
    - exchange_api_down_1_hour
```

### Safety D: Configuration Backup & Restore
```yaml
config_backup:
  description: "Automated backup of all configuration"
  
  why_critical: |
    Configuration is critical:
    - Strategy parameters
    - Risk limits
    - API keys (encrypted)
    - Account settings
    If lost, system can't operate correctly.
  
  implementation:
    backup_frequency: "Daily at 00:00 UTC"
    backup_location: "Encrypted cloud storage"
    retention: "30 daily backups, 12 monthly backups"
    
    what_to_backup:
      - strategies: "All strategy definitions and parameters"
      - risk_config: "All risk limits and settings"
      - accounts: "Account configurations (not API keys)"
      - positions: "Current position snapshot"
      - state: "System state for recovery"
    
    restore_capability:
      one_click_restore: true
      point_in_time_restore: "Any backup in last 30 days"
      verify_after_restore: "Run health check"
    
    disaster_recovery:
      rto: "4 hours"                    # Recovery time objective
      rpo: "24 hours"                   # Recovery point objective (max data loss)
```

### Safety E: Startup Checklist
```yaml
startup_checklist:
  description: "Verify all systems before trading starts"
  
  why_needed: |
    After restart, things might be wrong:
    - Database corrupted
    - Exchange API changed
    - Positions out of sync
    - Config file corrupted
    Don't start trading until everything checks out.
  
  checklist:
    pre_start:
      - database_connection: "Can connect to database"
      - database_integrity: "No corrupt tables"
      - exchange_api_auth: "API keys valid"
      - exchange_api_permissions: "Has trading permissions"
      - config_valid: "Config file parses correctly"
      - disk_space: "> 1GB free"
      - memory_available: "> 500MB free"
    
    position_sync:
      - fetch_exchange_positions: "Get positions from exchange"
      - compare_local_positions: "Compare to local database"
      - reconcile_differences: "Alert if mismatch, don't auto-correct"
    
    balance_check:
      - fetch_exchange_balance: "Get balance from exchange"
      - verify_sufficient: "Balance > minimum required"
      - compare_expected: "Within 5% of last known balance"
    
    strategy_validation:
      - load_all_strategies: "All strategies load without error"
      - verify_parameters: "Parameters within valid ranges"
      - check_symbol_availability: "All symbols tradeable"
    
    on_failure:
      action: "Do not start trading, alert operator"
      require_manual_override: true
```

## 2.2.4 Symbols Configuration

### Default Symbols (MVP)
```yaml
default_symbols:
  selected_by_default:
    - symbol: "BTCUSDT"
      name: "Bitcoin / USDT"
      reason: "Most liquid, benchmark crypto asset"
    - symbol: "ETHUSDT"
      name: "Ethereum / USDT"
      reason: "Second largest, different behavior from BTC"
  
  available_for_selection:
    # Top 10 additional symbols (NOT selected by default)
    # These are recommended based on liquidity, volatility, and trading characteristics
    - symbol: "BNBUSDT"
      name: "Binance Coin / USDT"
      avg_daily_volume: "Very High"
      volatility: "Medium"
      correlation_to_btc: 0.75
      notes: "Exchange token, different dynamics"
    
    - symbol: "SOLUSDT"
      name: "Solana / USDT"
      avg_daily_volume: "High"
      volatility: "High"
      correlation_to_btc: 0.70
      notes: "High volatility, good for breakout strategies"
    
    - symbol: "XRPUSDT"
      name: "Ripple / USDT"
      avg_daily_volume: "High"
      volatility: "Medium-High"
      correlation_to_btc: 0.65
      notes: "News-driven, different from pure crypto"
    
    - symbol: "ADAUSDT"
      name: "Cardano / USDT"
      avg_daily_volume: "High"
      volatility: "High"
      correlation_to_btc: 0.72
      notes: "Strong community, event-driven moves"
    
    - symbol: "DOGEUSDT"
      name: "Dogecoin / USDT"
      avg_daily_volume: "High"
      volatility: "Very High"
      correlation_to_btc: 0.55
      notes: "Meme coin, social media driven"
    
    - symbol: "AVAXUSDT"
      name: "Avalanche / USDT"
      avg_daily_volume: "Medium-High"
      volatility: "High"
      correlation_to_btc: 0.68
      notes: "L1 competitor, DeFi ecosystem"
    
    - symbol: "DOTUSDT"
      name: "Polkadot / USDT"
      avg_daily_volume: "Medium-High"
      volatility: "High"
      correlation_to_btc: 0.70
      notes: "Parachain ecosystem"
    
    - symbol: "LINKUSDT"
      name: "Chainlink / USDT"
      avg_daily_volume: "Medium-High"
      volatility: "Medium-High"
      correlation_to_btc: 0.65
      notes: "Oracle leader, different use case"
    
    - symbol: "MATICUSDT"
      name: "Polygon / USDT"
      avg_daily_volume: "Medium-High"
      volatility: "High"
      correlation_to_btc: 0.68
      notes: "L2 solution, Ethereum ecosystem"
    
    - symbol: "LTCUSDT"
      name: "Litecoin / USDT"
      avg_daily_volume: "Medium"
      volatility: "Medium"
      correlation_to_btc: 0.85
      notes: "Bitcoin companion, halving cycles"
  
  selection_criteria:
    min_daily_volume_usdt: 50000000     # $50M minimum daily volume
    min_market_cap: 1000000000          # $1B minimum market cap
    exchange_listed: "Binance Spot"
    trading_pair: "USDT"
```

### UI Symbol Management
```yaml
ui_symbol_management:
  features:
    view_available:
      description: "See all available symbols with metrics"
      display:
        - symbol
        - name
        - daily_volume
        - volatility_score
        - correlation_to_btc
        - recommended_strategies
    
    add_symbol:
      description: "Add symbol to active trading list"
      validations:
        - check_liquidity: "Warn if low volume"
        - check_correlation: "Warn if highly correlated to existing symbols"
        - check_exchange_status: "Verify tradeable on Binance"
    
    remove_symbol:
      description: "Remove symbol from active trading"
      requires: "No open positions in symbol"
    
    custom_symbol:
      description: "Add symbol not in recommended list"
      warning: "Custom symbols may have lower liquidity"
      validations:
        - must_exist_on_binance: true
        - must_be_usdt_pair: true
```

## 2.2.5 Customizable Settings Architecture

All settings are customizable at three hierarchy levels:

### Settings Hierarchy
```yaml
settings_hierarchy:
  portfolio_level:
    description: "Global defaults for entire portfolio"
    scope: "All accounts, all strategies"
    examples:
      - max_portfolio_risk: 15%
      - default_position_size: 5%
      - emergency_contact: "telegram_id"
      - default_timeframe: "1H"
  
  account_level:
    description: "Defaults for all strategies in an account"
    scope: "All strategies in specific account"
    overrides: "Portfolio level settings"
    examples:
      - max_account_risk: 10%
      - account_capital: 10000
      - allowed_strategies: ["trend", "breakout"]
      - leverage_allowed: false
  
  strategy_level:
    description: "Settings for specific strategy instance"
    scope: "Single strategy"
    overrides: "Account level settings"
    examples:
      - fast_ema_period: 12
      - stop_loss_pct: 2.0
      - max_position_size: 3%
      - active_hours: "08:00-22:00 UTC"

inheritance_rules:
  - "Strategy inherits from Account inherits from Portfolio"
  - "Lower levels can override higher levels"
  - "Missing settings fall back to parent level"
  - "Some settings are FIXED at higher levels (e.g., kill switch always enabled)"
```

### UI Settings Editor
```yaml
ui_settings_editor:
  features:
    view_effective_settings:
      description: "See final computed settings with inheritance"
      show_source: true  # Shows where each setting comes from
    
    edit_at_any_level:
      description: "Edit settings at appropriate level"
      options:
        - "Edit just this strategy"
        - "Edit account default (affects all strategies in account)"
        - "Edit portfolio default (affects everything)"
    
    reset_to_parent:
      description: "Remove override and inherit from parent"
    
    bulk_edit:
      description: "Change setting across multiple strategies"
    
    export_import:
      description: "Export settings as JSON, import to another instance"
  
  validation:
    on_change:
      - "Validate against constraints"
      - "Warn if outside recommended range"
      - "Show impact preview (which strategies affected)"
    
    protected_settings:
      description: "Some settings cannot be overridden at lower levels"
      examples:
        - kill_switch_enabled: "Always true, cannot disable"
        - max_leverage: "Cannot exceed portfolio limit"
        - emergency_contact: "Must be set at portfolio level"
```

## 2.3 MVP Explicit Exclusions

The following are **explicitly excluded** from MVP and will not be built, discussed, or designed until their scheduled phase:

| Excluded Feature | Why Excluded | Scheduled Phase |
|------------------|--------------|-----------------|
| Multi-broker support | Complexity without validation | V1 |
| Automated regime detection | Needs training data | V2 |
| ML strategy generation | Needs proven manual process | Maturity |
| Symbol discovery | Manual selection sufficient | V2 |
| Sentiment analysis | Separate data pipeline | Maturity |
| Mobile application | Web works on mobile | Maturity |
| Tax/audit reports | Not enough trades early | V2 |
| Strategy correlation analysis | Needs multiple strategies running | V2 |
| Volatility forecasting | Advanced feature | Maturity |
| Portfolio rebalancing automation | Manual sufficient at scale | V2 |
| Alpha discovery | Research capability | Maturity |
| Funding rate optimization | Only for perpetuals with overnight | V1 |

## 2.4 MVP Success Criteria

The MVP is complete when:

| Criterion | Measurement |
|-----------|-------------|
| Execute paper trades | Successfully place and track 100 paper trades |
| Risk limits enforced | 100% of trades checked, dangerous trades blocked |
| Kill switch works | Response time < 1 second |
| Strategies generated | At least 3 strategies from templates |
| Backtests run | Deterministic results (same input = same output) |
| P&L accurate | Within 0.1% of manual calculation |
| Dashboard loads | All components render correctly |
| Alerts delivered | Test alerts arrive within 30 seconds |
| System runs unattended | 24 hours without crash in paper mode |

## 2.5 MVP Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1-2 | Foundation | Project structure, config, logging, database |
| 3-4 | Data Layer | Market data fetching, caching, symbol management |
| 5-6 | Risk Controls | Position limits, loss limits, kill switch, circuit breakers |
| 7-8 | Execution | Binance adapter, order management, position tracking |
| 9-10 | Strategy System | Templates, backtest engine, paper trading |
| 11-12 | Integration | Orchestrator, dashboard, alerting, final testing |

**Total MVP Development Time: 12 weeks at 40 hours/week**

---

# PART 3: STRATEGY SYSTEM SPECIFICATION

## 3.1 Strategy System Philosophy

The strategy system is built on these principles:

1. **Templates over creativity** — Start with proven patterns, not novel inventions
2. **Validation before deployment** — Every strategy must prove itself before risking capital
3. **Metadata for trust** — Comprehensive information about every strategy enables confident decisions
4. **Human gates** — Automation for testing, human judgment for deployment
5. **Lifecycle management** — Strategies are born, tested, deployed, monitored, and retired

## 3.2 Strategy Object Specification

Every strategy in the system is represented by a comprehensive data structure. This is the **single source of truth** about what a strategy is, how it works, and how it has performed.

### 3.2.1 Strategy Core Identity

```yaml
strategy:
  # === IDENTITY ===
  id: "str_20260203_ma_cross_btc_001"  # Unique identifier
  name: "BTC Moving Average Crossover"  # Human-readable name
  description: "Trend-following strategy using dual moving average crossover on BTC/USDT"
  
  # === CLASSIFICATION ===
  type: "trend_following"  # trend_following | mean_reversion | momentum | breakout
  template_id: "tpl_dual_ma_crossover"  # Which template generated this
  template_version: "1.0.0"  # Template version used
  
  # === OWNERSHIP ===
  created_at: "2026-02-03T10:30:00Z"
  created_by: "manual"  # manual | template_generator | optimizer
  
  # === STATUS ===
  status: "paper_trading"  # draft | backtest | paper_trading | pending_approval | live | paused | retired
  status_changed_at: "2026-02-03T14:00:00Z"
  status_reason: "Passed backtest criteria, promoted to paper trading"
```

### 3.2.2 Strategy Parameters

```yaml
  # === PARAMETERS ===
  parameters:
    # Entry parameters
    fast_ma_period: 10
    slow_ma_period: 50
    ma_type: "EMA"  # SMA | EMA | WMA
    
    # Exit parameters
    take_profit_pct: 3.0
    stop_loss_pct: 1.5
    trailing_stop_pct: null  # null = not used
    
    # Position parameters
    position_size_pct: 2.0  # Percent of account per trade
    max_positions: 3  # Max concurrent positions for this strategy
    
    # Timing parameters
    min_bars_between_trades: 5
    trading_hours: "00:00-23:59"  # UTC
    
  # === PARAMETER METADATA ===
  parameter_metadata:
    fast_ma_period:
      type: "integer"
      min: 5
      max: 50
      default: 10
      description: "Fast moving average period"
      sensitivity: "high"  # How much performance changes with this param
    slow_ma_period:
      type: "integer"
      min: 20
      max: 200
      default: 50
      description: "Slow moving average period"
      sensitivity: "high"
    # ... etc for all parameters
```

### 3.2.3 Strategy Trading Rules

```yaml
  # === TRADING RULES ===
  rules:
    entry:
      long:
        conditions:
          - "fast_ma > slow_ma"
          - "fast_ma_previous <= slow_ma_previous"
          - "close > slow_ma"
        description: "Enter long when fast MA crosses above slow MA and price is above slow MA"
      short:
        conditions:
          - "fast_ma < slow_ma"
          - "fast_ma_previous >= slow_ma_previous"
          - "close < slow_ma"
        description: "Enter short when fast MA crosses below slow MA and price is below slow MA"
        enabled: true  # Short enabled for crypto futures
    
    exit:
      take_profit:
        enabled: true
        type: "percentage"
        value: 3.0
        description: "Exit when profit reaches 3%"
      stop_loss:
        enabled: true
        type: "percentage"
        value: 1.5
        description: "Exit when loss reaches 1.5%"
      trailing_stop:
        enabled: false
        type: "percentage"
        value: null
      time_based:
        enabled: false
        max_bars: null
      signal_exit:
        enabled: true
        description: "Exit on opposite signal"
    
    filters:
      - type: "volatility"
        condition: "atr_14 > atr_14_sma_20"
        description: "Only trade when volatility is above average"
        enabled: false  # Disabled for MVP simplicity
      - type: "trend"
        condition: "close > sma_200"
        description: "Only long when above 200 SMA"
        enabled: false
```

### 3.2.4 Strategy Symbol Configuration

```yaml
  # === SYMBOLS ===
  symbols:
    approved:
      - symbol: "BTCUSDT"
        enabled: true
        custom_params: null  # Can override strategy params per symbol
      - symbol: "ETHUSDT"
        enabled: true
        custom_params:
          position_size_pct: 1.5  # Lower size for ETH
    
    symbol_requirements:
      min_daily_volume_usd: 10000000  # $10M minimum
      min_price: 0.0001
      quote_currency: "USDT"
```

### 3.2.5 Strategy Backtest Results

```yaml
  # === BACKTEST RESULTS ===
  backtest:
    # Test configuration
    config:
      start_date: "2024-01-01"
      end_date: "2025-12-31"
      initial_capital: 10000
      commission_pct: 0.1
      slippage_pct: 0.05
      data_source: "binance"
      timeframe: "4h"
      symbols_tested: ["BTCUSDT", "ETHUSDT"]
    
    # Aggregate results
    results:
      # Return metrics
      total_return_pct: 47.3
      annualized_return_pct: 23.1
      monthly_returns: [2.1, -1.3, 4.5, 1.2, -0.8, 3.2, 2.8, -2.1, 5.1, 1.9, 3.4, 2.2]
      
      # Risk metrics
      max_drawdown_pct: 12.4
      max_drawdown_duration_days: 23
      volatility_annualized_pct: 18.2
      downside_deviation_pct: 11.3
      
      # Risk-adjusted metrics
      sharpe_ratio: 1.27
      sortino_ratio: 2.04
      calmar_ratio: 1.86
      
      # Trade metrics
      total_trades: 156
      winning_trades: 89
      losing_trades: 67
      win_rate_pct: 57.1
      
      # Profit metrics
      average_win_pct: 2.8
      average_loss_pct: -1.4
      largest_win_pct: 8.7
      largest_loss_pct: -4.2
      profit_factor: 1.89
      expectancy_pct: 0.73
      expectancy_r: 0.52  # In terms of R (risk unit)
      
      # Time metrics
      average_trade_duration_hours: 28.4
      average_winning_trade_duration_hours: 22.1
      average_losing_trade_duration_hours: 36.8
      
      # Consistency metrics
      best_month_pct: 5.1
      worst_month_pct: -2.1
      positive_months: 10
      negative_months: 2
      max_consecutive_wins: 7
      max_consecutive_losses: 4
    
    # Per-symbol breakdown
    per_symbol:
      BTCUSDT:
        total_trades: 82
        win_rate_pct: 58.5
        total_return_pct: 28.1
        max_drawdown_pct: 9.2
        sharpe_ratio: 1.41
      ETHUSDT:
        total_trades: 74
        win_rate_pct: 55.4
        total_return_pct: 19.2
        max_drawdown_pct: 11.8
        sharpe_ratio: 1.12
    
    # Time period analysis
    per_period:
      by_year:
        2024: { return_pct: 22.1, trades: 78, win_rate: 56.4 }
        2025: { return_pct: 25.2, trades: 78, win_rate: 57.7 }
      by_quarter:
        "2024-Q1": { return_pct: 5.3, trades: 19, win_rate: 52.6 }
        "2024-Q2": { return_pct: 3.6, trades: 21, win_rate: 57.1 }
        # ... etc
      by_month:
        "2024-01": { return_pct: 2.1, trades: 6, win_rate: 50.0 }
        # ... etc
    
    # Market condition analysis
    market_conditions:
      trending_up:
        trades: 62
        win_rate_pct: 67.7
        avg_return_pct: 1.2
        description: "Performance when market trending up (price > SMA50)"
      trending_down:
        trades: 48
        win_rate_pct: 45.8
        avg_return_pct: -0.3
        description: "Performance when market trending down"
      ranging:
        trades: 46
        win_rate_pct: 52.2
        avg_return_pct: 0.4
        description: "Performance in ranging markets"
    
    # Robustness analysis
    robustness:
      parameter_sensitivity:
        fast_ma_period:
          tested_values: [8, 9, 10, 11, 12]
          results: [21.2, 23.8, 23.1, 22.4, 20.9]  # Returns for each
          stable: true  # Performance doesn't collapse with small changes
        slow_ma_period:
          tested_values: [40, 45, 50, 55, 60]
          results: [19.8, 22.1, 23.1, 21.7, 18.9]
          stable: true
      
      walk_forward:
        periods: 4
        in_sample_months: 6
        out_sample_months: 3
        results:
          - { in_sample_return: 15.2, out_sample_return: 8.1, degradation_pct: 46.7 }
          - { in_sample_return: 12.8, out_sample_return: 7.3, degradation_pct: 43.0 }
          - { in_sample_return: 18.1, out_sample_return: 9.8, degradation_pct: 45.9 }
          - { in_sample_return: 14.6, out_sample_return: 8.9, degradation_pct: 39.0 }
        average_degradation_pct: 43.7
        passed: true  # Degradation < 50% threshold
      
      monte_carlo:
        simulations: 1000
        confidence_95_return_range: [18.2, 52.4]
        confidence_95_drawdown_range: [8.1, 18.7]
        probability_of_profit: 94.2
        probability_of_target_return: 78.3  # Probability of hitting target
    
    # Backtest quality indicators
    quality:
      data_quality_score: 98.5  # Percentage of expected bars present
      sufficient_trades: true  # > 100 trades
      sufficient_history: true  # > 2 years
      no_lookahead_bias: true  # Validated
      realistic_fills: true  # Slippage and commission included
      
    # Backtest metadata
    metadata:
      run_id: "bt_20260203_143022_abc123"
      run_timestamp: "2026-02-03T14:30:22Z"
      duration_seconds: 45.2
      engine_version: "1.0.0"
      data_hash: "sha256:abc123..."  # For reproducibility
```

### 3.2.6 Paper Trading Results

```yaml
  # === PAPER TRADING RESULTS ===
  paper_trading:
    # Configuration
    config:
      start_date: "2026-01-15"
      end_date: null  # Still running
      initial_capital: 1000
      account_id: "paper_validation"
      symbols_traded: ["BTCUSDT"]
    
    # Status
    status: "running"  # running | completed | failed
    days_elapsed: 19
    days_required: 28  # Minimum paper trading period
    
    # Current results
    results:
      total_return_pct: 4.2
      max_drawdown_pct: 3.1
      
      total_trades: 12
      winning_trades: 7
      losing_trades: 5
      win_rate_pct: 58.3
      
      profit_factor: 1.72
      expectancy_pct: 0.35
      
      sharpe_ratio: 1.89
      sortino_ratio: 2.41
    
    # Comparison to backtest
    backtest_comparison:
      expected_trades_per_month: 6.5  # From backtest
      actual_trades_per_month: 9.5
      trade_frequency_deviation_pct: 46.2  # Warning if > 50%
      
      expected_win_rate_pct: 57.1
      actual_win_rate_pct: 58.3
      win_rate_deviation_pct: 2.1  # Good
      
      expected_avg_win_pct: 2.8
      actual_avg_win_pct: 2.1
      avg_win_deviation_pct: -25.0  # Some degradation expected
      
      expected_avg_loss_pct: -1.4
      actual_avg_loss_pct: -1.6
      avg_loss_deviation_pct: 14.3
      
      overall_alignment_score: 78.5  # 0-100, higher is better
      alignment_status: "acceptable"  # good | acceptable | warning | failed
    
    # Execution quality
    execution_quality:
      total_orders: 24  # Entry + exit
      successful_fills: 24
      failed_fills: 0
      partial_fills: 0
      
      average_slippage_pct: 0.03
      max_slippage_pct: 0.12
      slippage_vs_expected: -0.02  # Better than expected
      
      average_fill_time_ms: 145
      max_fill_time_ms: 892
    
    # Trade log (last 5 trades)
    recent_trades:
      - trade_id: "tr_001"
        symbol: "BTCUSDT"
        side: "long"
        entry_time: "2026-01-20T08:15:00Z"
        entry_price: 42150.50
        exit_time: "2026-01-21T14:30:00Z"
        exit_price: 43012.80
        exit_reason: "take_profit"
        return_pct: 2.05
        duration_hours: 30.25
      # ... more trades
```

### 3.2.7 Live Trading Results (After Deployment)

```yaml
  # === LIVE TRADING RESULTS ===
  live_trading:
    # Deployment info
    deployment:
      deployed_at: "2026-02-10T09:00:00Z"
      deployed_by: "manual_approval"
      approval_notes: "Paper trading passed all criteria. Starting with minimum allocation."
      accounts: ["binance_conservative"]
      initial_allocation_pct: 1.0  # Started at 1% allocation
      current_allocation_pct: 2.0  # Increased after good performance
    
    # Current status
    status: "active"  # active | paused | retired
    days_live: 45
    
    # Lifetime results
    lifetime:
      total_return_pct: 8.7
      total_return_usd: 87.00
      max_drawdown_pct: 4.2
      
      total_trades: 28
      winning_trades: 17
      losing_trades: 11
      win_rate_pct: 60.7
      
      profit_factor: 2.01
      expectancy_pct: 0.31
      
      sharpe_ratio: 1.65
      
    # Period results
    periods:
      last_7_days: { return_pct: 1.2, trades: 4, win_rate: 75.0 }
      last_30_days: { return_pct: 5.1, trades: 18, win_rate: 61.1 }
      month_to_date: { return_pct: 2.8, trades: 8, win_rate: 62.5 }
    
    # Performance vs expectations
    performance_tracking:
      expected_monthly_return_pct: 2.0  # From backtest
      actual_monthly_return_pct: 2.9  # Calculated from live
      performance_vs_expected: 145.0  # Outperforming
      
      expected_max_drawdown_pct: 12.4
      actual_max_drawdown_pct: 4.2
      drawdown_vs_expected: 33.9  # Much better than expected
      
      tracking_status: "exceeding"  # exceeding | meeting | underperforming | failing
```

### 3.2.8 Strategy Lifecycle History

```yaml
  # === LIFECYCLE HISTORY ===
  lifecycle:
    current_stage: "live"
    stages_completed:
      - stage: "draft"
        entered_at: "2026-02-03T10:30:00Z"
        exited_at: "2026-02-03T10:35:00Z"
        duration_minutes: 5
        notes: "Generated from template"
      
      - stage: "backtest"
        entered_at: "2026-02-03T10:35:00Z"
        exited_at: "2026-02-03T14:30:00Z"
        duration_minutes: 235
        notes: "Passed all backtest criteria"
        criteria_met:
          - "sharpe_ratio > 1.0" 
          - "max_drawdown < 15%"
          - "total_trades > 100"
          - "win_rate > 50%"
      
      - stage: "paper_trading"
        entered_at: "2026-01-15T00:00:00Z"
        exited_at: "2026-02-10T09:00:00Z"
        duration_days: 26
        notes: "Paper trading showed acceptable alignment with backtest"
        criteria_met:
          - "positive_return: true"
          - "alignment_score > 70%"
          - "no_system_failures"
      
      - stage: "pending_approval"
        entered_at: "2026-02-10T08:00:00Z"
        exited_at: "2026-02-10T09:00:00Z"
        duration_minutes: 60
        notes: "Reviewed paper results, approved for live deployment"
        approved_by: "operator"
        approval_reason: "All criteria met, starting with minimal allocation"
      
      - stage: "live"
        entered_at: "2026-02-10T09:00:00Z"
        exited_at: null
        notes: "Currently running live"
    
    # Modifications history
    modifications:
      - modification_id: "mod_001"
        timestamp: "2026-02-20T14:00:00Z"
        type: "allocation_increase"
        description: "Increased allocation from 1% to 2%"
        reason: "Strong performance in first 10 days"
        old_value: 1.0
        new_value: 2.0
        approved_by: "operator"
      
      - modification_id: "mod_002"
        timestamp: "2026-03-01T10:00:00Z"
        type: "parameter_adjustment"
        description: "Adjusted stop loss from 1.5% to 1.8%"
        reason: "Too many stop-outs in volatile conditions"
        old_value: { stop_loss_pct: 1.5 }
        new_value: { stop_loss_pct: 1.8 }
        requires_revalidation: true
        revalidation_status: "pending"
```

### 3.2.9 Strategy Recommendations and Insights

```yaml
  # === RECOMMENDATIONS ===
  recommendations:
    # Auto-generated recommendations based on analysis
    current:
      - recommendation_id: "rec_001"
        type: "allocation"
        priority: "medium"
        title: "Consider Increasing Allocation"
        description: "Strategy has outperformed expectations for 30+ days. Consider increasing allocation from 2% to 3%."
        evidence:
          - "Live performance: +8.7% vs expected +4%"
          - "Max drawdown: 4.2% vs allowed 15%"
          - "Sharpe ratio: 1.65 vs expected 1.27"
        action: "increase_allocation"
        suggested_value: 3.0
        risk_assessment: "low"
        requires_approval: true
      
      - recommendation_id: "rec_002"
        type: "warning"
        priority: "low"
        title: "Performance May Degrade in Ranging Markets"
        description: "Backtest shows this strategy underperforms in ranging markets. Current market appears to be entering ranging conditions."
        evidence:
          - "ADX dropping below 25"
          - "Price consolidating near SMA50"
          - "Backtest ranging market win rate: 52.2%"
        action: "monitor"
        suggested_value: null
        risk_assessment: "medium"
        requires_approval: false
    
    # Historical recommendations
    history:
      - recommendation_id: "rec_000"
        created_at: "2026-02-10T08:00:00Z"
        type: "deployment"
        title: "Ready for Live Deployment"
        status: "accepted"
        accepted_at: "2026-02-10T09:00:00Z"
    
  # === INSIGHTS ===
  insights:
    strengths:
      - "Performs well in trending markets (67.7% win rate)"
      - "Low maximum drawdown in live trading (4.2%)"
      - "Consistent monthly returns (10 of 12 months positive in backtest)"
      - "Good execution quality (minimal slippage)"
    
    weaknesses:
      - "Underperforms in ranging markets (52.2% win rate)"
      - "Trade duration longer for losers (36.8h) than winners (22.1h)"
      - "Some parameter sensitivity on slow MA period"
    
    opportunities:
      - "Could add volatility filter to avoid ranging markets"
      - "Trailing stop could capture more profit in strong trends"
      - "Could expand to additional symbols after more validation"
    
    risks:
      - "Trend-following strategies suffer in choppy markets"
      - "Performance degradation from backtest to live is normal (expect 30-50%)"
      - "Current outperformance may be due to favorable market conditions"
    
    # Correlation with other strategies
    correlations:
      - strategy_id: "str_002_rsi_mean_rev"
        correlation: 0.23
        relationship: "low_correlation"
        note: "Good diversification - different market regime preferences"
      - strategy_id: "str_003_momentum_breakout"
        correlation: 0.78
        relationship: "high_correlation"
        note: "Warning: Both strategies may lose simultaneously in ranging markets"
```

### 3.2.10 Strategy Display Configuration

```yaml
  # === DISPLAY CONFIGURATION ===
  display:
    # Dashboard card settings
    card:
      primary_metric: "total_return_pct"
      secondary_metrics: ["win_rate_pct", "sharpe_ratio", "max_drawdown_pct"]
      status_color: "green"  # green | yellow | red based on performance
      show_recommendation_badge: true
    
    # Detail view sections
    detail_sections:
      - section: "overview"
        visible: true
        order: 1
      - section: "parameters"
        visible: true
        order: 2
      - section: "backtest_results"
        visible: true
        order: 3
      - section: "paper_results"
        visible: true
        order: 4
      - section: "live_results"
        visible: true
        order: 5
      - section: "recommendations"
        visible: true
        order: 6
      - section: "lifecycle"
        visible: true
        order: 7
    
    # Chart configurations
    charts:
      equity_curve:
        show: true
        periods: ["backtest", "paper", "live"]
        overlay_benchmark: true
      monthly_returns:
        show: true
        type: "heatmap"
      drawdown:
        show: true
        highlight_max: true
      trade_distribution:
        show: true
        type: "histogram"
```

## 3.3 Strategy Templates

### 3.3.1 Template Structure

Templates are the blueprints for generating strategies. Each template defines:
- Fixed logic (entry/exit rules)
- Variable parameters with allowed ranges
- Default values
- Validation criteria

### 3.3.2 MVP Templates (3 Templates)

Based on extensive analysis, these 3 templates provide optimal coverage of market conditions:

| Template | Market Regime | Role |
|----------|---------------|------|
| EMA Trend + RSI Filter | Trending markets | Core trend-following (PRIMARY) |
| Bollinger Band Squeeze Breakout | Consolidation → Explosion | Volatility capture |
| MACD Trend + Pullback Entry | Strong but choppy trends | Safer trend continuation |

**Why These 3:**
- Together they cover: Trending, Consolidating, and Choppy conditions
- All are simple to parameterize and automate
- All work well on crypto (15m, 1H, 4H timeframes)
- All have clear, objective entry/exit rules (no subjectivity)

**Why NOT Others:**
- Ichimoku: Too complex, too many parameters for MVP
- Order Blocks/SMC: Subjective, hard to automate
- Fibonacci: Discretionary, requires human judgment
- VWAP: More equities-focused (can add in V1)
- Stochastic: Redundant with RSI

#### Template 1: EMA Trend + RSI Filter (PRIMARY STRATEGY)

If the system could only have ONE strategy, this is it. Most robust, proven across all markets.

```yaml
template:
  id: "tpl_ema_trend_rsi"
  name: "EMA Trend + RSI Filter"
  version: "1.0.0"
  type: "trend_following"
  description: "Trend-following with EMA crossover and RSI momentum confirmation"
  
  # Logic
  trend_definition:
    bullish: "Fast EMA > Slow EMA"
    bearish: "Fast EMA < Slow EMA"
  
  entry_logic:
    long:
      conditions:
        - "Price above both EMAs"
        - "Fast EMA crosses above Slow EMA"
        - "RSI > rsi_filter_level (momentum confirmation)"
    short:
      conditions:
        - "Price below both EMAs"
        - "Fast EMA crosses below Slow EMA"
        - "RSI < (100 - rsi_filter_level) (momentum confirmation)"
  
  exit_logic:
    primary: "Opposite EMA crossover"
    secondary: "RSI reaches extreme (>70 for longs, <30 for shorts)"
    stop_loss: "ATR-based trailing stop"
    take_profit: "Fixed percentage OR ATR multiple"
  
  # Parameters with ranges (ALL CUSTOMIZABLE IN UI)
  parameters:
    fast_ema_period:
      default: 9
      min: 5
      max: 20
      step: 1
      description: "Fast EMA period"
      ui_group: "Moving Averages"
    slow_ema_period:
      default: 21
      min: 15
      max: 50
      step: 1
      description: "Slow EMA period"
      ui_group: "Moving Averages"
    rsi_period:
      default: 14
      min: 7
      max: 21
      step: 1
      description: "RSI calculation period"
      ui_group: "RSI Settings"
    rsi_filter_level:
      default: 50
      min: 40
      max: 60
      step: 5
      description: "RSI level for momentum confirmation"
      ui_group: "RSI Settings"
    atr_period:
      default: 14
      min: 10
      max: 20
      step: 1
      description: "ATR period for stop loss calculation"
      ui_group: "Risk Management"
    atr_stop_multiplier:
      default: 2.0
      min: 1.5
      max: 3.5
      step: 0.25
      description: "ATR multiplier for stop distance"
      ui_group: "Risk Management"
    take_profit_pct:
      default: 3.0
      min: 1.5
      max: 8.0
      step: 0.5
      description: "Take profit percentage"
      ui_group: "Risk Management"
    enable_trailing_stop:
      default: true
      type: "boolean"
      description: "Enable trailing stop loss"
      ui_group: "Risk Management"
    trailing_stop_activation_pct:
      default: 1.5
      min: 0.5
      max: 3.0
      step: 0.25
      description: "Profit % before trailing stop activates"
      ui_group: "Risk Management"
  
  # Validation rules
  validation:
    fast_ema_must_be_less_than_slow: true
    min_difference: 5  # slow - fast >= 5
  
  # Performance expectations (for validation)
  expected_performance:
    min_sharpe: 0.5
    max_drawdown: 15%
    min_win_rate: 40%
    avg_trades_per_month: "5-15"
  
  # Recommended settings
  recommended_for:
    - "Trending markets"
    - "BTC, ETH, major altcoins"
    - "15m, 1H, 4H timeframes"
    - "Swing trading (hold hours to days)"
  
  not_recommended_for:
    - "Ranging/choppy markets (use BB Squeeze instead)"
    - "Very low timeframes (< 5m)"
    - "Low liquidity tokens"
```

#### Template 2: Bollinger Band Squeeze Breakout

Captures volatility expansion after consolidation — perfect for crypto's "range → explosion" behavior.

```yaml
template:
  id: "tpl_bb_squeeze_breakout"
  name: "Bollinger Band Squeeze Breakout"
  version: "1.0.0"
  type: "volatility_breakout"
  description: "Captures breakouts after periods of low volatility (squeeze)"
  
  # Logic
  squeeze_detection:
    method: "BB Width percentile"
    description: "Bollinger Band Width at N-period low indicates squeeze"
  
  entry_logic:
    long:
      conditions:
        - "BB Width in bottom squeeze_percentile over squeeze_lookback periods"
        - "Price closes above upper Bollinger Band"
        - "Volume > volume_threshold * average volume"
    short:
      conditions:
        - "BB Width in bottom squeeze_percentile over squeeze_lookback periods"
        - "Price closes below lower Bollinger Band"
        - "Volume > volume_threshold * average volume"
  
  exit_logic:
    primary: "Price closes back inside middle band (SMA)"
    secondary: "ATR-based trailing stop"
    time_exit: "Close if no significant move after max_hold_bars"
  
  # Parameters (ALL CUSTOMIZABLE IN UI)
  parameters:
    bb_period:
      default: 20
      min: 10
      max: 30
      step: 2
      description: "Bollinger Band SMA period"
      ui_group: "Bollinger Bands"
    bb_std_dev:
      default: 2.0
      min: 1.5
      max: 2.5
      step: 0.25
      description: "Standard deviation multiplier"
      ui_group: "Bollinger Bands"
    squeeze_lookback:
      default: 120
      min: 60
      max: 200
      step: 20
      description: "Bars to look back for squeeze detection"
      ui_group: "Squeeze Detection"
    squeeze_percentile:
      default: 10
      min: 5
      max: 25
      step: 5
      description: "BB width must be in bottom X percentile"
      ui_group: "Squeeze Detection"
    min_squeeze_duration:
      default: 5
      min: 3
      max: 15
      step: 1
      description: "Minimum bars squeeze must persist"
      ui_group: "Squeeze Detection"
    volume_threshold:
      default: 1.5
      min: 1.2
      max: 2.5
      step: 0.1
      description: "Volume must be X times average"
      ui_group: "Volume Filter"
    atr_period:
      default: 14
      min: 10
      max: 20
      step: 1
      ui_group: "Risk Management"
    atr_stop_multiplier:
      default: 2.5
      min: 2.0
      max: 4.0
      step: 0.25
      description: "ATR multiplier for trailing stop"
      ui_group: "Risk Management"
    max_hold_bars:
      default: 20
      min: 10
      max: 50
      step: 5
      description: "Exit if no significant move after X bars"
      ui_group: "Exit Rules"
  
  # Validation
  validation:
    squeeze_must_precede_entry: true
    volume_confirmation_required: true
  
  # Performance expectations
  expected_performance:
    min_sharpe: 0.4
    max_drawdown: 18%
    min_win_rate: 35%  # Lower win rate but larger wins
    avg_trades_per_month: "3-8"
  
  # Recommended settings
  recommended_for:
    - "Consolidation → explosion patterns"
    - "Crypto markets (high volatility)"
    - "1H and 4H timeframes"
    - "Catching big moves"
  
  not_recommended_for:
    - "Already volatile markets (no squeeze to catch)"
    - "Low volume periods"
    - "Very short timeframes"
```

#### Template 3: MACD Trend + Pullback Entry

Safer trend continuation entries by waiting for pullbacks instead of chasing breakouts.

```yaml
template:
  id: "tpl_macd_pullback"
  name: "MACD Trend + Pullback Entry"
  version: "1.0.0"
  type: "trend_continuation"
  description: "Enter established trends on pullbacks with MACD confirmation - reduces whipsaw"
  
  # Logic
  trend_filter:
    bullish:
      - "MACD histogram > 0"
      - "Trend EMA slope positive"
    bearish:
      - "MACD histogram < 0"
      - "Trend EMA slope negative"
  
  entry_logic:
    long:
      conditions:
        - "Trend filter is bullish"
        - "Price pulls back to pullback_ema (within pullback_tolerance_pct)"
        - "MACD histogram was declining but now rising"
        - "RSI not overbought (< rsi_overbought)"
    short:
      conditions:
        - "Trend filter is bearish"
        - "Price pulls back to pullback_ema (within pullback_tolerance_pct)"
        - "MACD histogram was rising but now declining"
        - "RSI not oversold (> rsi_oversold)"
  
  exit_logic:
    primary: "MACD histogram flips sign"
    secondary: "Fixed risk-reward target"
    stop_loss: "Below recent swing low (longs) / above swing high (shorts)"
  
  # Parameters (ALL CUSTOMIZABLE IN UI)
  parameters:
    macd_fast:
      default: 12
      min: 8
      max: 15
      step: 1
      description: "MACD fast EMA period"
      ui_group: "MACD Settings"
    macd_slow:
      default: 26
      min: 20
      max: 35
      step: 1
      description: "MACD slow EMA period"
      ui_group: "MACD Settings"
    macd_signal:
      default: 9
      min: 5
      max: 12
      step: 1
      description: "MACD signal line period"
      ui_group: "MACD Settings"
    pullback_ema:
      default: 20
      min: 10
      max: 30
      step: 2
      description: "EMA for pullback detection"
      ui_group: "Pullback Detection"
    pullback_tolerance_pct:
      default: 0.5
      min: 0.2
      max: 1.5
      step: 0.1
      description: "How close to EMA counts as pullback (%)"
      ui_group: "Pullback Detection"
    trend_ema:
      default: 50
      min: 40
      max: 100
      step: 10
      description: "EMA for overall trend confirmation"
      ui_group: "Trend Filter"
    risk_reward_ratio:
      default: 2.0
      min: 1.5
      max: 3.5
      step: 0.25
      description: "Target profit as multiple of stop distance"
      ui_group: "Risk Management"
    rsi_period:
      default: 14
      min: 7
      max: 21
      step: 1
      ui_group: "RSI Filter"
    rsi_overbought:
      default: 70
      min: 65
      max: 80
      step: 5
      description: "Don't enter long if RSI above this"
      ui_group: "RSI Filter"
    rsi_oversold:
      default: 30
      min: 20
      max: 35
      step: 5
      description: "Don't enter short if RSI below this"
      ui_group: "RSI Filter"
    swing_lookback:
      default: 10
      min: 5
      max: 20
      step: 1
      description: "Bars to look back for swing high/low"
      ui_group: "Stop Loss"
  
  # Validation
  validation:
    pullback_must_occur: true
    trend_must_be_established: true
    macd_fast_less_than_slow: true
  
  # Performance expectations
  expected_performance:
    min_sharpe: 0.6
    max_drawdown: 12%
    min_win_rate: 45%
    avg_trades_per_month: "4-10"
  
  # Recommended settings
  recommended_for:
    - "Strong but choppy trends"
    - "Avoiding whipsaw entries"
    - "1H and 4H timeframes (MACD can lag on 15m)"
    - "More conservative traders"
  
  not_recommended_for:
    - "Weak or unclear trends"
    - "Very fast-moving markets (use EMA+RSI instead)"
    - "15m or lower timeframes (MACD too slow)"
```

### 3.3.3 Template Selection Guide

| Market Condition | Use This Template | Why |
|------------------|-------------------|-----|
| Clear trending market | EMA Trend + RSI | Best for riding trends |
| Sideways consolidation | BB Squeeze | Catches the eventual breakout |
| Trending but choppy | MACD Pullback | Avoids getting shaken out |
| Unknown/Mixed | Start with EMA Trend + RSI | Most robust general-purpose |

### 3.3.4 Template Customization (UI Feature)

All parameters can be customized in the UI at three levels:

```yaml
customization_levels:
  strategy_level:
    description: "Override defaults for a specific strategy instance"
    example: "This BTC EMA strategy uses fast_ema=12 instead of default 9"
    
  account_level:
    description: "Default parameters for all strategies in an account"
    example: "Conservative account uses atr_multiplier=2.5 for all strategies"
    
  portfolio_level:
    description: "Global defaults for the entire portfolio"
    example: "All strategies default to take_profit=2.5%"

ui_requirements:
  parameter_editor:
    - Show parameter name, description, current value
    - Show min/max/step constraints
    - Group by ui_group for organization
    - Validate on change
    - Show warning if outside recommended range
  
  reset_to_default:
    - One-click reset to template default
    - Reset single parameter or all parameters
  
  presets:
    - Save custom parameter sets as presets
    - Load presets quickly
    - Share presets between strategies
```

## 3.4 Strategy Lifecycle

### 3.4.1 Lifecycle Stages

```
[DRAFT] → [BACKTEST] → [SIMULATED_PAPER] → [LIVE_PAPER] → [PENDING_APPROVAL] → [LIVE]
                ↓              ↓                ↓                                  ↓
            [FAILED]       [FAILED]         [FAILED]                          [PAUSED]
                ↑                                                                  │
                │                                                                  ↓
                └──────────────── [OPTIMIZATION] ←────────── [UNDERPERFORMING]
                                       │                           ↓
                                       │                      [RETIRED]
                                       ▼
                                  [BACKTEST]

Paper Trading Detail (Three-Phase Validation):

Phase 1: SIMULATED_PAPER (21 days)
  - Uses real market prices
  - Calculates fills locally with slippage model
  - 100+ strategies can run in parallel
  - Per-strategy P&L tracking

Phase 2: LIVE_PAPER (21-28 days)
  - Executes on Binance testnet
  - Real broker API interaction
  - Max 5 strategies at once
  - Validates execution quality, slippage

Phase 3: MICRO_LIVE (30 days)
  - Real money: $50-100 capital
  - Full execution costs (real fees, real slippage)
  - Max 1-2 strategies at once
  - Emotional and psychological validation

Total validation time: ~10-12 weeks per strategy before full live deployment
```

**New MVP Feature: Three-Phase Validation Pipeline**

This ensures strategies are thoroughly validated before real capital deployment:
- Phase 1 (Simulated Paper, 21 days): Fast iteration, logic validation, no API limits
- Phase 2 (Live Paper, 21-28 days): Real execution on testnet, catches slippage/fill issues
- Phase 3 (Micro-Live, 30 days): Small real capital, validates real costs and emotional readiness

**New MVP Feature: Re-Optimization Loop**

When a live strategy underperforms, it can be sent back for re-optimization rather than just paused or retired:
- LIVE → UNDERPERFORMING: Triggered when strategy fails performance thresholds
- UNDERPERFORMING → OPTIMIZATION: Operator chooses to re-optimize (manual decision)
- UNDERPERFORMING → RETIRED: Operator chooses to retire (manual decision)
- OPTIMIZATION → BACKTEST: After parameter adjustment, strategy re-enters validation loop

### 3.4.2 Stage Transitions

#### Draft → Backtest
- **Trigger:** Strategy created from template
- **Automatic:** Yes
- **Criteria:** Valid parameters

#### Backtest → Paper Trading
- **Trigger:** Backtest completes successfully
- **Automatic:** Yes (if criteria met)
- **Criteria:**
  - Sharpe ratio > 1.0
  - Max drawdown < 15%
  - Total trades > 100
  - Win rate > 50%
  - Profit factor > 1.3

#### Backtest → Failed
- **Trigger:** Backtest criteria not met
- **Automatic:** Yes
- **Action:** Strategy marked as failed, available for parameter adjustment

#### Simulated Paper → Failed
- **Trigger:** Phase 1 criteria not met after 21 days
- **Automatic:** Yes
- **Conditions:**
  - Total return <= 0%
  - Alignment score < 70%
  - Max drawdown > backtest * 1.5
- **Action:** Strategy marked as PAPER_FAILED
- **Options:**
  - Send to OPTIMIZATION (adjust parameters, re-backtest)
  - Send to RETIRED (fundamentally flawed)

#### Simulated Paper → Live Paper
- **Trigger:** Phase 1 criteria met
- **Automatic:** Yes (queued if >5 strategies already in live paper)
- **Action:** Strategy promoted to Phase 2 (Binance testnet execution)

#### Live Paper → Failed
- **Trigger:** Phase 2 criteria not met after 7 days
- **Automatic:** Yes
- **Conditions:**
  - Execution failures > 0
  - Average slippage > 0.5%
  - Return alignment < 80% vs simulated
- **Action:** Strategy marked as EXECUTION_FAILED
- **Options:**
  - Send back to SIMULATED_PAPER (if execution issues were temporary)
  - Send to OPTIMIZATION (if parameters need adjustment)
  - Send to RETIRED (if strategy fundamentally doesn't work in live)

#### Paper Trading → Pending Approval
- **Trigger:** Both paper trading phases complete
- **Automatic:** Yes (if criteria met)
- **Paper Trading Phases:**
  - **Phase 1: Simulated Paper (21 days)**
    - System calculates what WOULD have happened using real market prices
    - Uses realistic slippage model
    - 100% per-strategy tracking (no account conflicts)
    - Can run 100+ strategies simultaneously
  - **Phase 2: Live Paper (7 days)**
    - Actually executes on Binance testnet
    - Only for strategies that passed Phase 1
    - Catches execution edge cases
    - Maximum 5 strategies in live paper at once
- **Criteria (must pass both phases):**
  - Simulated: 21 days minimum, positive return, alignment > 70%
  - Live Paper: 7 days on testnet, no execution failures, slippage within 0.5%
  - Combined: 28 days total validation, no system failures

#### Pending Approval → Live
- **Trigger:** Human approval
- **Automatic:** No (requires explicit approval)
- **Actions:**
  - Operator reviews paper trading results
  - Operator confirms deployment
  - Operator sets initial allocation

#### Live → Paused
- **Trigger:** Manual or automatic
- **Conditions for automatic pause:**
  - Drawdown exceeds strategy limit
  - 5 consecutive losses
  - System error
- **Action:** Strategy stops trading but maintains state

#### Live → Underperforming
- **Trigger:** Automatic based on performance monitoring
- **Conditions:**
  - Win rate drops 15%+ below backtest for 14+ days
  - Sharpe ratio < 0.5 for 30+ days
  - Returns negative for 3 consecutive weeks
  - Performance vs expectation score < 50% for 21+ days
- **Action:** Strategy flagged, operator notified, recommendation generated

#### Underperforming → Optimization
- **Trigger:** Manual operator decision
- **Action:** 
  - Strategy cloned with new ID
  - Parameters available for adjustment
  - Original strategy data preserved for comparison
  - Clone enters BACKTEST after parameter changes

#### Underperforming → Retired
- **Trigger:** Manual operator decision
- **Criteria:** Strategy deemed not worth re-optimizing
- **Action:** Strategy archived with full history

#### Optimization → Backtest
- **Trigger:** Operator adjusts parameters and confirms
- **Action:** Re-optimized strategy enters normal validation loop
- **Note:** Must pass all backtest criteria again

#### Paused → Live
- **Trigger:** Manual only
- **Requires:** Operator review and explicit reactivation

#### Live → Retired
- **Trigger:** Manual decision
- **Criteria:** Strategy no longer viable
- **Action:** Strategy archived, removed from active rotation

## 3.5 Strategy Generation Workflow

### 3.5.1 Manual Generation

1. Operator selects template
2. Operator configures parameters (or uses defaults)
3. Operator selects symbols
4. System creates strategy in DRAFT status
5. System automatically begins backtest

### 3.5.2 Batch Generation (V1)

1. Operator selects template
2. Operator defines parameter ranges
3. System generates multiple strategies with parameter combinations
4. System backtests all strategies
5. System ranks strategies by performance
6. Operator reviews top performers
7. Operator selects which to promote to paper trading

### 3.5.3 Automated Discovery (Maturity)

1. Research system generates strategy candidates continuously
2. System backtests candidates automatically
3. System filters by minimum criteria
4. System promotes passing candidates to paper trading
5. System alerts operator of strategies ready for review
6. Operator approves or rejects for live deployment

## 3.6 Strategy Validation Criteria

### 3.6.1 Backtest Criteria (Must Pass All)

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Sharpe Ratio | > 1.0 | Risk-adjusted return acceptable |
| Max Drawdown | < 15% | Capital preservation |
| Total Trades | > 100 | Statistical significance |
| Win Rate | > 50% | More winners than losers |
| Profit Factor | > 1.3 | Gross profit > gross loss |
| Expectancy | > 0 | Positive expected value |
| Walk-Forward Degradation | < 50% | Strategy not overfit |

### 3.6.2 Paper Trading Criteria (Must Pass All)

**Phase 1: Simulated Paper Trading (21 days minimum)**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Duration | >= 21 days | Cover multiple market conditions |
| Total Return | > 0% | Positive performance |
| Alignment Score | > 70% | Simulated matches backtest |
| Max Drawdown | < backtest * 1.5 | Not significantly worse |

**Phase 2: Live Paper Trading (21-28 days minimum)**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Duration | >= 21 days (28 preferred) | Thorough execution validation |
| Execution Success | 100% | All orders executed properly |
| Slippage | < 0.5% average | Acceptable execution quality |
| System Failures | 0 | No technical issues |
| Return Alignment | > 80% vs simulated | Live paper matches simulated |

**Phase 3: Micro-Live Testing (30 days minimum)**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Duration | >= 30 days | Full month of real trading |
| Capital | $50-100 | Small enough to limit risk |
| Execution Success | 100% | All orders executed properly |
| Actual Costs | Within 20% of simulated | Real costs match expectations |
| Return | > -10% | Acceptable learning loss |
| Emotional Readiness | Operator comfortable | No panic decisions made |

**Combined Validation (~10-12 weeks total)**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Total Duration | >= 72 days | Full three-phase validation |
| All Phases Passed | Yes | Each phase criteria met |
| Strategy Consistency | Positive in 2+ phases | Not luck in one phase |
| Operator Confidence | High | Ready for real capital |

### 3.6.2.1 Simulated Paper Trading Specification

The simulated paper trading system enables validating 100+ strategies simultaneously without Binance testnet account limits:

```yaml
simulated_paper_trading:
  description: "Calculate hypothetical trades using real market prices"
  
  how_it_works:
    - Fetches real-time prices from Binance (live feed, not delayed)
    - When strategy signals entry, records entry price + simulated slippage
    - Tracks position as if held (mark-to-market every minute)
    - When strategy signals exit, records exit price + simulated slippage
    - Calculates P&L per trade and per strategy
  
  slippage_model:
    market_orders: "0.05% + (order_size / daily_volume) * 0.5%"
    limit_orders: "0% if filled, track fill rate by price distance"
    fill_rate_assumption: "95% for limits within 0.1% of market"
  
  advantages:
    - Run 100+ strategies in parallel
    - Perfect per-strategy P&L attribution
    - No testnet API limits
    - Faster iteration
  
  limitations:
    - Doesn't catch execution edge cases
    - Assumes fills that might not happen
    - Doesn't test broker API integration
  
  why_21_days:
    - Covers 3 weekends (crypto trades 24/7, but behavior differs)
    - Likely includes at least one volatility event
    - Enough trades for statistical confidence (day trading = 50-150 trades)
    - Not so long that good strategies are stuck waiting
```

### 3.6.3 Live Performance Monitoring

| Metric | Warning Threshold | Action |
|--------|-------------------|--------|
| Win Rate vs Backtest | -15% | Generate warning |
| Max Drawdown | Strategy limit | Auto-pause |
| Consecutive Losses | 5 | Generate warning |
| Monthly Return | -5% | Generate warning |
| Consecutive Losing Months | 2 | Generate warning |

---

# PART 4: RISK MANAGEMENT SPECIFICATION

## 4.1 Risk Management Philosophy

**The risk system is the most important component of the trading system.**

It has one job: **Prevent catastrophic loss.**

The risk system:
- Has veto power over any trade
- Cannot be bypassed by any other component
- Fails closed (if uncertain, block the trade)
- Operates independently of strategy logic

## 4.2 Risk Hierarchy

```
Level 1: GLOBAL KILL SWITCH
    ↓
Level 2: ACCOUNT-LEVEL LIMITS
    ↓
Level 3: STRATEGY-LEVEL LIMITS
    ↓
Level 4: TRADE-LEVEL LIMITS
```

Higher levels override lower levels. If the global kill switch is active, nothing trades regardless of account or strategy settings.

## 4.3 Global Kill Switch

### 4.3.1 Activation Triggers

The kill switch activates automatically when:

| Trigger | Threshold | Response Time |
|---------|-----------|---------------|
| Total portfolio drawdown | > 15% | Immediate |
| Daily loss | > 5% | Immediate |
| System error rate | > 10% of orders | Immediate |
| Data feed failure | > 5 minutes | Immediate |
| Broker connection lost | > 2 minutes | Immediate |
| Manual activation | Any time | Immediate |

### 4.3.2 Kill Switch Actions

When activated:
1. Cancel all pending orders
2. Stop all new order submissions
3. Send emergency alert
4. Log activation reason
5. Optionally: Flatten all positions (requires confirmation)

### 4.3.3 Kill Switch Deactivation

Deactivation requires:
1. Manual confirmation
2. Acknowledgment of activation reason
3. Verification that conditions have normalized

## 4.4 Account-Level Risk Limits

Each account has configurable risk parameters:

```yaml
account_risk_config:
  # Position limits
  max_position_size_pct: 5.0  # Max % of account per position
  max_concentration_pct: 20.0  # Max % in single asset
  max_open_positions: 10  # Max concurrent positions
  
  # Loss limits
  daily_loss_limit_pct: 3.0  # Hard stop for day
  daily_loss_warning_pct: 2.0  # Warning threshold
  weekly_loss_limit_pct: 7.0  # Hard stop for week
  
  # Drawdown limits
  max_drawdown_pct: 15.0  # Max drawdown from peak
  drawdown_warning_pct: 10.0  # Warning threshold
  
  # Leverage
  max_leverage: 1.0  # No leverage for MVP
  
  # Exposure
  max_long_exposure_pct: 100.0
  max_short_exposure_pct: 50.0  # Allow shorting with conservative limits
```

### 4.4.1 Account Profiles

**Conservative Profile:**
```yaml
profile: conservative
max_position_size_pct: 2.0
daily_loss_limit_pct: 2.0
max_drawdown_pct: 8.0
description: "For steady income generation with minimal volatility"
```

**Balanced Profile:**
```yaml
profile: balanced
max_position_size_pct: 3.0
daily_loss_limit_pct: 3.0
max_drawdown_pct: 12.0
description: "Balance between growth and protection"
```

**Aggressive Profile:**
```yaml
profile: aggressive
max_position_size_pct: 5.0
daily_loss_limit_pct: 5.0
max_drawdown_pct: 15.0
description: "For maximum growth with higher risk tolerance"
```

## 4.5 Strategy-Level Risk Limits

Each strategy has risk limits that operate within account limits:

```yaml
strategy_risk_config:
  # Position limits for this strategy
  max_position_size_pct: 2.0  # Overrides account if lower
  max_positions: 3  # Max positions for this strategy
  
  # Drawdown limits for this strategy
  max_strategy_drawdown_pct: 10.0  # Pause strategy if breached
  
  # Consecutive loss limits
  max_consecutive_losses: 5  # Pause and alert
  
  # Allocation
  max_account_allocation_pct: 20.0  # Max % of account for this strategy
```

## 4.6 Trade-Level Risk Checks

Every trade must pass all checks before execution:

### 4.6.1 Pre-Trade Checklist

```python
def check_trade(trade: Trade) -> RiskCheckResult:
    checks = [
        check_kill_switch_not_active(),
        check_trading_enabled(),
        check_within_trading_hours(),
        check_position_size_limit(trade),
        check_concentration_limit(trade),
        check_daily_loss_limit(),
        check_weekly_loss_limit(),
        check_drawdown_limit(),
        check_max_positions_limit(),
        check_strategy_allocation_limit(trade),
        check_symbol_allowed(trade),
    ]
    
    for check in checks:
        if not check.passed:
            return RiskCheckResult(passed=False, reason=check.reason)
    
    return RiskCheckResult(passed=True)
```

### 4.6.2 Position Size Calculation

```python
def calculate_position_size(
    account_equity: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_loss_price: float
) -> float:
    """
    Calculate position size based on risk.
    
    Risk-based sizing ensures consistent risk per trade.
    """
    # Calculate risk amount in dollars
    risk_amount = account_equity * (risk_per_trade_pct / 100)
    
    # Calculate price risk per unit
    price_risk = abs(entry_price - stop_loss_price)
    
    # Prevent division by zero
    if price_risk == 0:
        return 0
    
    # Calculate position size
    position_size = risk_amount / price_risk
    
    # Apply maximum position size limit
    max_position_value = account_equity * (max_position_size_pct / 100)
    max_position_size = max_position_value / entry_price
    
    return min(position_size, max_position_size)
```

## 4.7 Circuit Breakers

Circuit breakers provide automatic protection against cascading failures.

### 4.7.1 Drawdown Circuit Breaker

```yaml
drawdown_breaker:
  warning_threshold_pct: 10.0
  halt_threshold_pct: 15.0
  
  states:
    closed: "Normal operation"
    warning: "Reduced position sizes, increased monitoring"
    open: "Trading halted"
  
  recovery:
    type: "manual"  # Requires human intervention to reset
```

### 4.7.2 Loss Rate Circuit Breaker

```yaml
loss_rate_breaker:
  window_trades: 10  # Look at last 10 trades
  warning_threshold: 6  # 6 losses = warning
  halt_threshold: 8  # 8 losses = halt
  
  states:
    closed: "Normal operation"
    warning: "Alert sent, continue with caution"
    open: "Trading halted pending review"
  
  recovery:
    type: "time_based"
    cooldown_hours: 24
    plus_manual_confirmation: true
```

### 4.7.3 Error Rate Circuit Breaker

```yaml
error_rate_breaker:
  window_minutes: 60
  warning_threshold_pct: 5.0  # 5% of orders fail
  halt_threshold_pct: 10.0  # 10% of orders fail
  
  states:
    closed: "Normal operation"
    warning: "Check system health"
    open: "System unhealthy, halted"
  
  recovery:
    type: "automatic"
    condition: "error_rate < 2% for 30 minutes"
    plus_manual_confirmation: true
```

## 4.8 Human Escalation

Certain conditions require human decision:

### 4.8.1 Escalation Triggers

| Condition | Severity | Required Action |
|-----------|----------|-----------------|
| Large position request (>3% of account) | Medium | Review and approve |
| Unusual market volatility (>2x normal) | Medium | Continue/pause decision |
| Consecutive losses (5+) | High | Review strategy performance |
| Drawdown >50% of limit | High | Review and decide |
| System anomaly detected | High | Investigate |
| Kill switch activation | Critical | Acknowledge and resolve |

### 4.8.2 Escalation Interface

```yaml
escalation_request:
  id: "esc_20260203_001"
  timestamp: "2026-02-03T14:30:00Z"
  severity: "high"
  type: "consecutive_losses"
  
  title: "Strategy Experiencing Consecutive Losses"
  description: "Strategy 'BTC MA Crossover' has 5 consecutive losing trades."
  
  context:
    strategy_id: "str_001"
    recent_trades: [...]
    current_drawdown_pct: 8.2
    market_conditions: "ranging"
  
  options:
    - action: "continue"
      description: "Continue trading with current settings"
    - action: "reduce_allocation"
      description: "Reduce strategy allocation by 50%"
    - action: "pause"
      description: "Pause strategy until manual review"
  
  deadline: "2026-02-03T15:30:00Z"  # 1 hour to respond
  default_action: "pause"  # If no response
  
  notification_sent: true
  notification_channel: "telegram"
```

## 4.9 Risk Reporting

### 4.9.1 Daily Risk Report

Generated automatically at end of each trading day:

```yaml
daily_risk_report:
  date: "2026-02-03"
  
  portfolio_summary:
    starting_equity: 10000.00
    ending_equity: 10150.00
    daily_pnl: 150.00
    daily_return_pct: 1.5
    
  risk_metrics:
    current_drawdown_pct: 2.3
    max_drawdown_today_pct: 3.1
    daily_loss_used_pct: 0.0  # Of daily limit
    
  positions:
    open_positions: 2
    max_positions_reached: 3
    concentration_max_pct: 12.5
    
  circuit_breakers:
    drawdown_breaker: "closed"
    loss_rate_breaker: "closed"
    error_rate_breaker: "closed"
    
  alerts_generated: 0
  escalations_required: 0
  
  recommendations:
    - "Portfolio within normal parameters"
    - "No action required"
```

---

# PART 5: EXECUTION SYSTEM SPECIFICATION

## 5.1 Execution Philosophy

The execution system has one job: **Reliably convert trading signals into positions.**

Execution should be:
- **Deterministic:** Same signal → same order
- **Auditable:** Every order logged with full context
- **Resilient:** Handle failures gracefully
- **Efficient:** Minimize slippage and costs

## 5.2 Order Flow

```
[Signal Generated]
       ↓
[Risk Check] ──────────→ [Rejected] → [Log & Alert]
       ↓ (passed)
[Order Created]
       ↓
[Order Validated]
       ↓
[Sent to Broker]
       ↓
[Confirmation Received]
       ↓
[Position Updated]
       ↓
[P&L Updated]
       ↓
[Logged]
```

## 5.3 Order Types Supported

### MVP Order Types

| Type | Description | Use Case |
|------|-------------|----------|
| MARKET | Execute immediately at best price | Standard entries/exits |
| LIMIT | Execute at specified price or better | Entries with price targets |
| STOP_LOSS | Trigger market order when price crosses | Risk management |
| TAKE_PROFIT | Trigger limit order at target | Profit capture |

### V1 Order Types (Future)

| Type | Description | Use Case |
|------|-------------|----------|
| TRAILING_STOP | Stop that follows price | Lock in profits |
| OCO | One-cancels-other | Bracket orders |
| ICEBERG | Large order split into visible portions | Reduce market impact |

## 5.4 Order Object Specification

```yaml
order:
  # Identity
  id: "ord_20260203_143022_001"
  external_id: "binance_12345678"  # Broker's order ID
  
  # Source
  strategy_id: "str_001"
  signal_id: "sig_20260203_143020_001"
  account_id: "binance_conservative"
  
  # Order details
  symbol: "BTCUSDT"
  side: "BUY"  # BUY | SELL
  type: "MARKET"  # MARKET | LIMIT | STOP_LOSS | TAKE_PROFIT
  quantity: 0.01
  price: null  # For MARKET orders
  stop_price: null  # For STOP orders
  time_in_force: "GTC"  # GTC | IOC | FOK
  
  # Risk context
  risk_check_passed: true
  risk_check_timestamp: "2026-02-03T14:30:22Z"
  position_size_pct: 2.0
  
  # Status
  status: "FILLED"  # PENDING | SUBMITTED | PARTIAL | FILLED | CANCELLED | REJECTED | EXPIRED
  status_history:
    - status: "PENDING"
      timestamp: "2026-02-03T14:30:22Z"
    - status: "SUBMITTED"
      timestamp: "2026-02-03T14:30:22.150Z"
    - status: "FILLED"
      timestamp: "2026-02-03T14:30:22.312Z"
  
  # Fill information
  filled_quantity: 0.01
  average_fill_price: 42150.50
  commission: 0.42  # In quote currency
  commission_asset: "USDT"
  
  # Timing
  created_at: "2026-02-03T14:30:22Z"
  submitted_at: "2026-02-03T14:30:22.150Z"
  filled_at: "2026-02-03T14:30:22.312Z"
  
  # Execution quality
  expected_price: 42148.00
  slippage: 2.50
  slippage_pct: 0.006
  fill_latency_ms: 162
  
  # Reason (for auditability)
  reason: "MA crossover signal: fast MA (42200) crossed above slow MA (41800)"
```

## 5.5 Position Tracking

### 5.5.1 Position Object

```yaml
position:
  # Identity
  id: "pos_btcusdt_001"
  symbol: "BTCUSDT"
  account_id: "binance_conservative"
  
  # Position details
  side: "LONG"  # LONG | SHORT | FLAT
  quantity: 0.01
  average_entry_price: 42150.50
  current_price: 42500.00
  
  # P&L
  unrealized_pnl: 3.50
  unrealized_pnl_pct: 0.83
  realized_pnl: 0.00  # From partial closes
  total_commission: 0.42
  
  # Value
  market_value: 425.00
  cost_basis: 421.51
  
  # Risk
  stop_loss_price: 41500.00
  take_profit_price: 43500.00
  risk_amount: 6.51  # Distance to stop loss
  reward_amount: 13.50  # Distance to take profit
  risk_reward_ratio: 2.07
  
  # Source
  strategy_id: "str_001"
  entry_signal_id: "sig_001"
  entry_order_id: "ord_001"
  
  # Timing
  opened_at: "2026-02-03T14:30:22Z"
  last_updated_at: "2026-02-03T16:45:00Z"
  duration_hours: 2.25
  
  # Associated orders
  exit_orders:
    stop_loss_order_id: "ord_002"
    take_profit_order_id: "ord_003"
```

### 5.5.2 Position Lifecycle

```
[FLAT] → [OPENING] → [OPEN] → [CLOSING] → [FLAT]
                                   ↑
                              [PARTIAL]
```

## 5.6 Execution Quality Tracking

### 5.6.1 Slippage Tracking

```yaml
slippage_tracking:
  # Per-order slippage
  order_id: "ord_001"
  expected_price: 42148.00
  actual_price: 42150.50
  slippage: 2.50
  slippage_pct: 0.006
  slippage_direction: "unfavorable"  # favorable | unfavorable | neutral
  
  # Aggregate slippage statistics
  aggregate:
    period: "last_30_days"
    total_orders: 145
    average_slippage_pct: 0.008
    median_slippage_pct: 0.005
    max_slippage_pct: 0.15
    total_slippage_cost: 23.45
```

### 5.6.2 Fill Quality Metrics

```yaml
fill_quality:
  period: "last_30_days"
  
  fill_rate:
    total_orders: 150
    fully_filled: 148
    partially_filled: 1
    rejected: 1
    fill_rate_pct: 98.7
  
  timing:
    average_fill_time_ms: 145
    median_fill_time_ms: 120
    p95_fill_time_ms: 450
    p99_fill_time_ms: 890
  
  cost:
    total_commission: 145.23
    average_commission_per_trade: 0.97
    commission_pct_of_volume: 0.10
```

## 5.7 Broker Adapter Interface

### 5.7.1 Abstract Interface

```python
class BrokerAdapter(ABC):
    """Base interface for all broker adapters."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection to broker."""
        pass
    
    @abstractmethod
    async def get_account(self) -> Account:
        """Get account information including balance."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        pass
    
    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        """Place an order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get current status of an order."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get current price for a symbol."""
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int) -> OrderBook:
        """Get order book for a symbol."""
        pass
```

### 5.7.2 Binance Adapter (MVP)

```yaml
binance_adapter:
  name: "Binance"
  type: "crypto"
  
  supported_features:
    spot: true
    futures: true  # USDT-margined
    margin: false  # Not in MVP
    
  order_types:
    - MARKET
    - LIMIT
    - STOP_LOSS
    - STOP_LOSS_LIMIT
    - TAKE_PROFIT
    - TAKE_PROFIT_LIMIT
    
  environments:
    testnet:
      base_url: "https://testnet.binance.vision"
      ws_url: "wss://testnet.binance.vision/ws"
    production:
      base_url: "https://api.binance.com"
      ws_url: "wss://stream.binance.com:9443/ws"
  
  rate_limits:
    requests_per_minute: 1200
    orders_per_second: 10
    orders_per_day: 200000
  
  error_handling:
    retry_on: [408, 429, 500, 502, 503, 504]
    max_retries: 3
    retry_delay_ms: 1000
```

---

# PART 6: MONITORING & DASHBOARD SPECIFICATION

## 6.1 Monitoring Philosophy

**If you can't see it, you can't trust it.**

The monitoring system provides:
- Real-time visibility into system state
- Historical performance tracking
- Anomaly detection
- Decision support through information

## 6.2 Dashboard Layout

### 6.2.0 Dashboard Navigation Philosophy

The dashboard uses a **drill-down hierarchy**:

1. **Portfolio View (Default)** — Shows all accounts, all positions, total P&L
2. **Account View** — Click an account to see just that account's positions
3. **Strategy View** — Click a strategy to see its performance and positions
4. **Symbol View** — Click a symbol to see all positions in that symbol and technical data

Everything starts at portfolio level and drills down. You never need to "select a symbol first" — you see everything and click to zoom in.

### 6.2.1 Main Dashboard Sections

```
┌─────────────────────────────────────────────────────────────────┐
│                        HEADER BAR                                │
│  System Status: ● RUNNING    Kill Switch: ○ INACTIVE            │
│  Account: binance_conservative    Last Update: 14:30:22 UTC     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │   PORTFOLIO      │  │   TODAY'S P&L    │  │  RISK STATUS  │  │
│  │   $10,150.00     │  │   +$150.00       │  │  ● NORMAL     │  │
│  │   +1.5% today    │  │   +1.5%          │  │  DD: 2.3%     │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    OPEN POSITIONS (2)                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ BTCUSDT  LONG  0.01  $42,150 → $42,500  +$3.50 (+0.83%)    ││
│  │ ETHUSDT  LONG  0.1   $2,850  → $2,880   +$3.00 (+1.05%)    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    ACTIVE STRATEGIES (3)                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ BTC MA Cross    ● LIVE    +8.7%   Sharpe: 1.65   [Details] ││
│  │ ETH RSI MR      ● LIVE    +4.2%   Sharpe: 1.23   [Details] ││
│  │ BTC Momentum    ○ PAPER   +2.1%   Day 15/28      [Details] ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    REGIME INDICATORS                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Trend: ↗ BULLISH (ADX: 32)    Volatility: NORMAL (ATR: 2.1%)│
│  │ BTC: Above SMA50              Regime: TRENDING              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    RECENT ALERTS (1)                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ⚠ 14:25 - Strategy approaching 5 consecutive losses        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2.2 Dashboard Components

#### Portfolio Summary Widget

```yaml
portfolio_summary:
  displays:
    - total_equity: "Current account value"
    - daily_change: "$ and % change today"
    - weekly_change: "$ and % change this week"
    - monthly_change: "$ and % change this month"
    - available_margin: "Buying power"
  
  visual_elements:
    - equity_sparkline: "7-day equity curve"
    - color_coding: "Green for positive, red for negative"
```

#### Risk Status Widget

```yaml
risk_status:
  displays:
    - overall_status: "NORMAL | WARNING | CRITICAL"
    - current_drawdown: "% from peak"
    - daily_loss_used: "% of daily limit used"
    - position_count: "Current vs max"
    - circuit_breaker_states: "All breaker statuses"
  
  thresholds:
    normal: "All metrics within 50% of limits"
    warning: "Any metric 50-80% of limit"
    critical: "Any metric >80% of limit"
```

#### Positions Widget

```yaml
positions_widget:
  displays_per_position:
    - symbol
    - side: "LONG/SHORT"
    - quantity
    - entry_price
    - current_price
    - unrealized_pnl: "$ and %"
    - duration
    - strategy_name
  
  actions:
    - close_position: "Manual close button"
    - view_details: "Expand to full position view"
```

#### Strategies Widget

```yaml
strategies_widget:
  displays_per_strategy:
    - name
    - status: "LIVE | PAPER | PAUSED"
    - total_return: "Since deployment"
    - sharpe_ratio
    - open_positions_count
    - recommendation_badge: "If any pending"
  
  actions:
    - view_details: "Full strategy page"
    - pause_resume: "Toggle strategy"
```

#### Regime Indicators Widget

```yaml
regime_indicators:
  displays:
    trend:
      indicator: "Price vs SMA50"
      current_value: "BULLISH | BEARISH | NEUTRAL"
      confidence: "ADX value"
    
    volatility:
      indicator: "ATR / ATR_SMA"
      current_value: "HIGH | NORMAL | LOW"
      ratio: "Current vs average"
    
    momentum:
      indicator: "RSI 14"
      current_value: "Number 0-100"
      zone: "OVERBOUGHT | NEUTRAL | OVERSOLD"
    
    market_regime:
      calculated: "From above indicators"
      current_value: "TRENDING | RANGING | VOLATILE"
```

## 6.3 Performance Charts

### 6.3.1 Equity Curve

```yaml
equity_curve:
  type: "line_chart"
  data: "Daily account equity"
  overlays:
    - benchmark: "Buy-and-hold BTC"
    - drawdown: "Underwater chart below"
  
  time_ranges:
    - "1W"
    - "1M"
    - "3M"
    - "6M"
    - "1Y"
    - "ALL"
  
  annotations:
    - trade_markers: "Entry/exit points"
    - drawdown_periods: "Shaded regions"
```

### 6.3.2 Monthly Returns Heatmap

```yaml
monthly_returns:
  type: "heatmap"
  rows: "Years"
  columns: "Months"
  color_scale: "Red (negative) → White (zero) → Green (positive)"
  
  cell_display:
    - return_pct
    - trade_count
```

### 6.3.3 Trade Distribution

```yaml
trade_distribution:
  type: "histogram"
  data: "Return per trade"
  bins: "Auto-calculated"
  
  overlays:
    - mean_line
    - median_line
    - expectancy_annotation
```

## 6.4 Strategy Detail View

When clicking on a strategy, show full detail page:

```yaml
strategy_detail_view:
  sections:
    overview:
      - Strategy metadata
      - Current status
      - Key metrics summary
      - Recommendations (if any)
    
    parameters:
      - All strategy parameters
      - Parameter descriptions
      - Sensitivity indicators
    
    rules:
      - Entry rules (human-readable)
      - Exit rules (human-readable)
      - Filters (if any)
    
    backtest_results:
      - Full backtest metrics
      - Equity curve
      - Monthly returns
      - Drawdown chart
      - Trade distribution
      - Market condition breakdown
      - Robustness analysis
    
    paper_results:
      - Paper trading metrics
      - Comparison to backtest
      - Execution quality
      - Recent trades
    
    live_results:
      - Live performance metrics
      - Performance vs expectations
      - Recent trades
      - P&L chart
    
    lifecycle:
      - Stage history
      - Modification history
      - Full audit trail
    
    insights:
      - Strengths
      - Weaknesses
      - Opportunities
      - Risks
      - Correlations
```

## 6.5 System Health Monitoring

### 6.5.1 Health Check Components

```yaml
health_checks:
  broker_connection:
    check: "Can reach broker API"
    frequency: "Every 30 seconds"
    alert_on_failure: true
    failure_threshold: "2 consecutive failures"
  
  data_feed:
    check: "Receiving market data"
    frequency: "Every 10 seconds"
    alert_on_failure: true
    staleness_threshold: "60 seconds"
  
  database:
    check: "Database responsive"
    frequency: "Every 60 seconds"
    alert_on_failure: true
  
  order_processing:
    check: "Orders processing correctly"
    frequency: "Per order"
    alert_on_failure: true
    error_rate_threshold: "5%"
  
  position_sync:
    check: "Local positions match broker"
    frequency: "Every 5 minutes"
    alert_on_mismatch: true
```

### 6.5.2 Health Dashboard

```yaml
health_dashboard:
  displays:
    system_status:
      overall: "HEALTHY | DEGRADED | UNHEALTHY"
      uptime: "Time since last restart"
      last_incident: "Timestamp and description"
    
    component_status:
      - broker_connection: "● Connected"
      - data_feed: "● Active"
      - database: "● Healthy"
      - order_engine: "● Running"
    
    performance:
      - cpu_usage: "Current %"
      - memory_usage: "Current %"
      - api_latency: "Last 5 min average"
    
    recent_errors:
      - list: "Last 10 errors with timestamps"
```

---

# PART 7: ACCOUNT MANAGEMENT SPECIFICATION

## 7.1 Account Types

### 7.1.1 MVP Account Types

| Type | Purpose | Real Money | Risk Level |
|------|---------|------------|------------|
| Paper | Development and testing | No | None |
| Canary | Validation with real money | Yes ($50-100) | Low |
| Production | Primary trading | Yes | Configurable |

### 7.1.2 Account Object

```yaml
account:
  # Identity
  id: "binance_conservative"
  name: "Binance Conservative"
  description: "Low-risk production account for steady income"
  
  # Broker connection
  broker: "binance"
  broker_account_id: "12345678"
  environment: "production"  # testnet | production
  
  # Classification
  type: "production"  # paper | canary | production
  profile: "conservative"  # conservative | balanced | aggressive
  
  # Risk configuration (from profile)
  risk_config:
    max_position_size_pct: 2.0
    max_concentration_pct: 15.0
    max_open_positions: 5
    daily_loss_limit_pct: 2.0
    weekly_loss_limit_pct: 5.0
    max_drawdown_pct: 8.0
    max_leverage: 1.0
  
  # Current state
  state:
    status: "active"  # active | paused | disabled
    equity: 10150.00
    available_balance: 9000.00
    margin_used: 1150.00
    unrealized_pnl: 6.50
    
  # Assigned strategies
  strategies:
    - strategy_id: "str_001"
      allocation_pct: 10.0
      status: "active"
    - strategy_id: "str_002"
      allocation_pct: 8.0
      status: "active"
  
  # Performance
  performance:
    total_return_pct: 15.0
    total_return_usd: 1500.00
    since_inception: "2026-01-01"
    sharpe_ratio: 1.45
    max_drawdown_pct: 5.2
  
  # Metadata
  created_at: "2025-12-15T00:00:00Z"
  last_active_at: "2026-02-03T14:30:00Z"
```

## 7.2 Account Profiles

### 7.2.1 Conservative Profile

**Purpose:** Steady income generation with minimal volatility

```yaml
conservative_profile:
  name: "Conservative"
  description: "For steady income generation with minimal volatility"
  
  risk_parameters:
    max_position_size_pct: 2.0
    max_concentration_pct: 15.0
    max_open_positions: 5
    daily_loss_limit_pct: 2.0
    weekly_loss_limit_pct: 5.0
    max_drawdown_pct: 8.0
    max_leverage: 1.0
  
  strategy_preferences:
    preferred_types: ["mean_reversion", "trend_following"]
    avoid_types: ["momentum", "breakout"]
    max_strategy_drawdown_pct: 5.0
    min_sharpe_ratio: 1.2
  
  expected_outcomes:
    monthly_return_target_pct: 2.0
    monthly_return_range_pct: [0.5, 4.0]
    max_losing_months_per_year: 3
```

### 7.2.2 Balanced Profile

**Purpose:** Balance between growth and protection

```yaml
balanced_profile:
  name: "Balanced"
  description: "Balance between growth and protection"
  
  risk_parameters:
    max_position_size_pct: 3.0
    max_concentration_pct: 20.0
    max_open_positions: 8
    daily_loss_limit_pct: 3.0
    weekly_loss_limit_pct: 7.0
    max_drawdown_pct: 12.0
    max_leverage: 1.5
  
  strategy_preferences:
    preferred_types: ["trend_following", "momentum"]
    avoid_types: []
    max_strategy_drawdown_pct: 8.0
    min_sharpe_ratio: 1.0
  
  expected_outcomes:
    monthly_return_target_pct: 4.0
    monthly_return_range_pct: [1.0, 8.0]
    max_losing_months_per_year: 4
```

### 7.2.3 Aggressive Profile

**Purpose:** Maximum growth with higher risk tolerance

```yaml
aggressive_profile:
  name: "Aggressive"
  description: "Maximum growth with higher risk tolerance"
  
  risk_parameters:
    max_position_size_pct: 5.0
    max_concentration_pct: 30.0
    max_open_positions: 10
    daily_loss_limit_pct: 5.0
    weekly_loss_limit_pct: 10.0
    max_drawdown_pct: 15.0
    max_leverage: 2.0
  
  strategy_preferences:
    preferred_types: ["momentum", "breakout", "trend_following"]
    avoid_types: []
    max_strategy_drawdown_pct: 12.0
    min_sharpe_ratio: 0.8
  
  expected_outcomes:
    monthly_return_target_pct: 6.0
    monthly_return_range_pct: [2.0, 15.0]
    max_losing_months_per_year: 5
```

## 7.3 Account Operations

### 7.3.1 Create Account

```yaml
create_account:
  required_fields:
    - name
    - broker
    - profile
  
  optional_fields:
    - description
    - custom_risk_config  # Override profile defaults
  
  process:
    1. Validate broker credentials
    2. Connect to broker
    3. Verify account access
    4. Apply risk profile
    5. Create account record
    6. Start monitoring
```

### 7.3.2 Assign Strategy to Account

```yaml
assign_strategy:
  required_fields:
    - account_id
    - strategy_id
    - allocation_pct
  
  validations:
    - Strategy must be in LIVE status
    - Strategy risk config must be compatible with account profile
    - Total allocation must not exceed 100%
    - Strategy not already assigned to account
  
  process:
    1. Validate assignment
    2. Check risk compatibility
    3. Create assignment record
    4. Start strategy execution for account
```

### 7.3.3 Pause Account

```yaml
pause_account:
  triggers:
    - Manual operator action
    - Risk limit breach
    - System error
  
  actions:
    1. Stop all new order submissions
    2. Keep existing positions (don't auto-close)
    3. Continue monitoring positions
    4. Continue P&L updates
    5. Send notification
  
  resume_requires:
    - Manual confirmation
    - If risk breach: acknowledge and resolution
```

---

# PART 8: ALERTING SYSTEM SPECIFICATION

## 8.1 Alert Philosophy

Alerts should be:
- **Actionable:** Every alert should tell you what to do
- **Prioritized:** Critical alerts stand out from informational ones
- **Timely:** Delivered within seconds of trigger
- **Non-spammy:** Only alert when human attention is needed

## 8.2 Alert Severity Levels

| Level | Use Case | Delivery | Response Expected |
|-------|----------|----------|-------------------|
| CRITICAL | System down, kill switch, major loss | Telegram + Email | Immediate |
| HIGH | Risk warnings, consecutive losses | Telegram | Within 1 hour |
| MEDIUM | Performance alerts, recommendations | Telegram (quiet) | Within 24 hours |
| LOW | Informational, daily summaries | In-app only | No immediate action |

## 8.3 Alert Types

### 8.3.1 Critical Alerts

```yaml
critical_alerts:
  - kill_switch_activated:
      message: "🚨 KILL SWITCH ACTIVATED: {reason}"
      action_required: "Review and resolve before trading resumes"
  
  - daily_loss_limit_hit:
      message: "🚨 Daily loss limit reached: {loss_pct}%"
      action_required: "Trading halted for today"
  
  - max_drawdown_breach:
      message: "🚨 Maximum drawdown breached: {drawdown_pct}%"
      action_required: "Review portfolio and decide on action"
  
  - broker_connection_lost:
      message: "🚨 Lost connection to {broker}"
      action_required: "System attempting to reconnect"
  
  - system_error:
      message: "🚨 System error: {error_type}"
      action_required: "Investigate immediately"
```

### 8.3.2 High Priority Alerts

```yaml
high_alerts:
  - consecutive_losses:
      trigger: "5 consecutive losing trades"
      message: "⚠️ Strategy {strategy_name} has 5 consecutive losses"
      action_required: "Review strategy performance"
  
  - drawdown_warning:
      trigger: "Drawdown > 50% of limit"
      message: "⚠️ Drawdown at {drawdown_pct}% (limit: {limit_pct}%)"
      action_required: "Monitor closely"
  
  - strategy_underperforming:
      trigger: "Live performance < 50% of expected"
      message: "⚠️ Strategy {name} significantly underperforming"
      action_required: "Review and consider pausing"
  
  - position_approaching_limit:
      trigger: "Position > 80% of max size"
      message: "⚠️ Position {symbol} approaching size limit"
      action_required: "Be aware of limit"
```

### 8.3.3 Medium Priority Alerts

```yaml
medium_alerts:
  - strategy_ready_for_review:
      message: "📋 Strategy {name} completed paper trading, ready for review"
      action_required: "Review and approve/reject for live"
  
  - recommendation_generated:
      message: "💡 New recommendation for {strategy_name}"
      action_required: "Review recommendation"
  
  - weekly_summary_ready:
      message: "📊 Weekly performance summary ready"
      action_required: "Review when convenient"
  
  - position_closed:
      message: "✅ Position {symbol} closed: {pnl_pct}%"
      action_required: "None"
```

## 8.4 Alert Delivery

### 8.4.1 Telegram Integration

```yaml
telegram_config:
  bot_token: "{TELEGRAM_BOT_TOKEN}"
  chat_id: "{TELEGRAM_CHAT_ID}"
  
  message_format:
    critical: "🚨 *CRITICAL*\n\n{message}\n\n*Action:* {action}"
    high: "⚠️ *WARNING*\n\n{message}\n\n*Action:* {action}"
    medium: "📋 *INFO*\n\n{message}"
  
  rate_limits:
    max_per_minute: 5
    max_per_hour: 30
    quiet_hours: null  # No quiet hours for trading alerts
```

### 8.4.2 Alert Object

```yaml
alert:
  id: "alert_20260203_143022_001"
  timestamp: "2026-02-03T14:30:22Z"
  
  severity: "high"
  type: "consecutive_losses"
  
  title: "Strategy Experiencing Consecutive Losses"
  message: "Strategy 'BTC MA Crossover' has 5 consecutive losing trades"
  
  context:
    strategy_id: "str_001"
    strategy_name: "BTC MA Crossover"
    consecutive_losses: 5
    total_loss_pct: 3.2
    recent_trades: [...]
  
  action_required: "Review strategy performance"
  action_options:
    - "continue"
    - "reduce_allocation"
    - "pause_strategy"
  
  delivery:
    channels: ["telegram", "dashboard"]
    delivered_at: "2026-02-03T14:30:23Z"
    acknowledged: false
    acknowledged_at: null
```

## 8.5 Daily and Weekly Summaries

### 8.5.1 Daily Summary (End of Day)

```yaml
daily_summary:
  delivery_time: "00:00 UTC"
  channel: "telegram"
  
  contents:
    - date
    - portfolio_value
    - daily_pnl: "$ and %"
    - trades_executed
    - winning_trades
    - losing_trades
    - best_trade
    - worst_trade
    - active_strategies_count
    - alerts_generated
    - risk_status
  
  format: |
    📅 Daily Summary: {date}
    
    💰 Portfolio: ${portfolio_value}
    📈 Today's P&L: {daily_pnl_pct}% (${daily_pnl})
    
    📊 Trades: {trades_executed}
    ✅ Wins: {winning_trades} | ❌ Losses: {losing_trades}
    
    🏆 Best: {best_trade_symbol} +{best_trade_pct}%
    📉 Worst: {worst_trade_symbol} {worst_trade_pct}%
    
    ⚡ Active Strategies: {active_strategies_count}
    🚦 Risk Status: {risk_status}
```

### 8.5.2 Weekly Summary

```yaml
weekly_summary:
  delivery_time: "Sunday 00:00 UTC"
  channel: "telegram"
  
  contents:
    - week_dates
    - starting_equity
    - ending_equity
    - weekly_return: "$ and %"
    - total_trades
    - win_rate
    - best_day
    - worst_day
    - strategy_performance_ranking
    - recommendations
    - next_week_outlook
  
  format: |
    📅 Weekly Summary: {week_start} - {week_end}
    
    💰 Portfolio: ${starting_equity} → ${ending_equity}
    📈 Weekly Return: {weekly_return_pct}% (${weekly_return})
    
    📊 Total Trades: {total_trades}
    🎯 Win Rate: {win_rate_pct}%
    
    📆 Best Day: {best_day} +{best_day_pct}%
    📆 Worst Day: {worst_day} {worst_day_pct}%
    
    🏆 Strategy Rankings:
    {strategy_rankings}
    
    💡 Recommendations:
    {recommendations}
```

---

# PART 9: DATA MANAGEMENT SPECIFICATION

## 9.1 Data Categories

### 9.1.1 Market Data

```yaml
market_data:
  types:
    ohlcv:
      description: "Open, High, Low, Close, Volume"
      granularity: ["1m", "5m", "15m", "1h", "4h", "1d"]
      retention: "2 years"
    
    ticker:
      description: "Current price and 24h stats"
      granularity: "real-time"
      retention: "7 days"
    
    orderbook:
      description: "Current bid/ask levels"
      granularity: "real-time snapshots"
      retention: "24 hours"
  
  sources:
    primary: "binance"
    fallback: "coingecko"  # For historical data gaps
```

### 9.1.2 Trading Data

```yaml
trading_data:
  types:
    orders:
      description: "All orders submitted"
      retention: "forever"  # Required for audit
    
    trades:
      description: "All executed trades"
      retention: "forever"
    
    positions:
      description: "Position history"
      retention: "forever"
    
    signals:
      description: "Generated trading signals"
      retention: "1 year"
```

### 9.1.3 System Data

```yaml
system_data:
  types:
    logs:
      description: "Application logs"
      retention: "90 days"
    
    health_checks:
      description: "Health check results"
      retention: "30 days"
    
    alerts:
      description: "Generated alerts"
      retention: "1 year"
    
    audit_trail:
      description: "All system actions"
      retention: "7 years"  # For compliance
```

## 9.2 Data Storage

### 9.2.1 MVP Storage Architecture

```yaml
storage:
  primary_database:
    type: "SQLite"
    file: "data/trading.db"
    purpose: "All structured data"
  
  market_data_cache:
    type: "SQLite"
    file: "data/market_data.db"
    purpose: "Historical OHLCV data"
  
  logs:
    type: "File"
    path: "data/logs/"
    format: "JSON lines"
    rotation: "Daily"
```

### 9.2.2 Database Schema (Core Tables)

```sql
-- Accounts
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    broker TEXT NOT NULL,
    profile TEXT NOT NULL,
    status TEXT NOT NULL,
    risk_config JSON NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Strategies
CREATE TABLE strategies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    template_id TEXT NOT NULL,
    parameters JSON NOT NULL,
    status TEXT NOT NULL,
    backtest_results JSON,
    paper_results JSON,
    live_results JSON,
    lifecycle JSON NOT NULL,
    recommendations JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Orders
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    external_id TEXT,
    account_id TEXT NOT NULL,
    strategy_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    type TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL,
    status TEXT NOT NULL,
    filled_quantity REAL,
    average_fill_price REAL,
    commission REAL,
    reason TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- Positions
CREATE TABLE positions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    average_entry_price REAL NOT NULL,
    strategy_id TEXT,
    opened_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    realized_pnl REAL,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- Trades (executed fills)
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    commission REAL,
    executed_at TIMESTAMP NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- P&L Records
CREATE TABLE pnl_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    date DATE NOT NULL,
    starting_equity REAL NOT NULL,
    ending_equity REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    total_pnl REAL NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- Alerts
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,
    severity TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    context JSON,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
);

-- Audit Log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details JSON,
    user TEXT NOT NULL
);

-- Market Data (OHLCV)
CREATE TABLE ohlcv (
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (symbol, timeframe, timestamp)
);
```

## 9.3 Data Validation

### 9.3.1 Market Data Validation

```yaml
market_data_validation:
  checks:
    - no_negative_prices: "Open, high, low, close must be positive"
    - high_is_highest: "High >= all other prices"
    - low_is_lowest: "Low <= all other prices"
    - no_future_timestamps: "Timestamp <= current time"
    - no_large_gaps: "Gap between candles <= expected interval * 2"
    - volume_reasonable: "Volume within historical range"
  
  on_failure:
    - log_warning
    - try_fallback_source
    - if_still_failing: "Alert and use last valid data"
```

### 9.3.2 Order Validation

```yaml
order_validation:
  pre_submission:
    - symbol_exists: "Symbol is valid on broker"
    - quantity_positive: "Quantity > 0"
    - quantity_precision: "Quantity within allowed decimals"
    - price_reasonable: "Price within 10% of current price"
    - risk_check_passed: "All risk checks passed"
  
  post_submission:
    - order_acknowledged: "Broker returned order ID"
    - status_valid: "Status is known value"
```

---

# PART 10: V1 ROADMAP

## 10.1 V1 Overview

**V1 Goal:** Expand from single-broker MVP to multi-capability system with enhanced automation.

**Prerequisites:** MVP running profitably for 3+ months

**Timeline:** 3-6 months after MVP completion

## 10.2 V1 Capabilities

### 10.2.1 Multi-Broker Support

```yaml
v1_multi_broker:
  description: "Add support for additional brokers"
  
  new_brokers:
    - deriv:
        type: "forex_cfd"
        purpose: "Forex trading"
        adapter_complexity: "medium"
    
    - alpaca:
        type: "stocks"
        purpose: "US equities"
        adapter_complexity: "low"
  
  architecture_changes:
    - unified_symbol_manager: "Map symbols across brokers"
    - broker_router: "Route orders to correct broker"
    - aggregated_positions: "View all positions in one place"
```

### 10.2.2 Batch Strategy Generation

```yaml
v1_batch_generation:
  description: "Generate multiple strategy variants at once"
  
  features:
    - parameter_sweep: "Test ranges of parameters"
    - auto_backtest: "Backtest all variants"
    - ranking: "Rank by performance metrics"
    - comparison_view: "Compare variants side-by-side"
    - auto_filtering: "Reject strategies below thresholds"
  
  workflow:
    1. Select template
    2. Define parameter ranges
    3. System generates all combinations (up to 100)
    4. System backtests all
    5. System auto-rejects below minimum thresholds
    6. System ranks remaining by composite score
    7. Operator reviews top 10
    8. Operator selects which to promote
  
  # Strategy Scoring Formula (learned from legacy system)
  scoring_formula:
    composite_score: |
      Score = (SharpeNorm × 0.25) + (SortinoNorm × 0.20) + (WinRateNorm × 0.15) + 
              (ProfitFactorNorm × 0.15) + (ConsistencyScore × 0.15) + (RobustnessScore × 0.10)
    
    normalizations:
      SharpeNorm: "min(Sharpe / 3.0, 1.0)"        # Capped at 3.0
      WinRateNorm: "(WinRate - 0.4) / 0.3"        # 40% = 0, 70% = 1
      ConsistencyScore: "PositiveMonths / TotalMonths"
      RobustnessScore: "WalkForwardReturn / InSampleReturn"
  
  # Auto-rejection thresholds
  minimum_thresholds:
    sharpe_ratio: 0.5         # Must be > 0.5 to even consider
    win_rate: 40%             # Must win 40%+ of trades
    profit_factor: 1.0        # Must be net profitable
    min_trades: 50            # Must have enough samples
    max_drawdown: 25%         # Must not have massive drawdown
    walk_forward_degradation: 60%  # Must not overfit too badly
```

### 10.2.2.1 Extended Template Library (V1)

Based on legacy system learnings, add 7-10 more templates in V1:

```yaml
v1_additional_templates:
  - volatility_expansion: "Trade breakouts after volatility squeeze"
  - stochastic_momentum: "Stochastic + trend confirmation"
  - atr_adaptive_stops: "ATR-based dynamic stop losses"
  - volume_confirmed: "Volume confirmation for entries"
  - multi_timeframe_trend: "Align multiple timeframes"
  - fibonacci_retracement: "Trade Fibonacci levels"
  - bollinger_mean_reversion: "Bollinger Band mean reversion"
```

### 10.2.3 Enhanced Performance Tracking

```yaml
v1_performance_tracking:
  description: "More detailed performance analysis"
  
  new_metrics:
    - backtest_vs_live_comparison: "Track degradation"
    - execution_quality_score: "Slippage, fill rate"
    - strategy_correlation_matrix: "How strategies relate"
    - attribution_analysis: "Why did we make/lose money"
  
  new_reports:
    - monthly_performance_report: "Detailed monthly analysis"
    - strategy_health_report: "Per-strategy deep dive"
```

### 10.2.4 Semi-Automated Regime Detection

```yaml
v1_regime_detection:
  description: "System suggests regime, operator confirms"
  
  indicators_tracked:
    - trend: "Price vs moving averages"
    - volatility: "ATR ratio"
    - momentum: "RSI, MACD"
    - volume: "Volume vs average"
  
  regime_classification:
    - trending_up: "Strong uptrend"
    - trending_down: "Strong downtrend"
    - ranging: "No clear direction"
    - high_volatility: "Elevated volatility"
    - low_volatility: "Compressed volatility"
  
  workflow:
    1. System calculates indicators
    2. System suggests regime
    3. Operator confirms or overrides
    4. System logs both for accuracy tracking
    5. Strategies tagged for preferred regimes
    6. Dashboard shows regime-strategy fit
```

### 10.2.5 Funding Rate Tracking (Crypto)

```yaml
v1_funding_rate:
  description: "Track and account for perpetual funding rates"
  
  features:
    - real_time_funding_display: "Current funding rates"
    - funding_cost_tracking: "Track funding paid/received"
    - funding_in_pnl: "Include in P&L calculations"
    - high_funding_alerts: "Alert when funding unusually high"
```

### 10.2.6 Cost Tracking

```yaml
v1_cost_tracking:
  description: "Comprehensive cost accounting"
  
  costs_tracked:
    - commissions: "Trading fees"
    - slippage: "Execution cost"
    - funding_rates: "Perpetual funding"
    - spread_cost: "Bid-ask spread"
  
  reports:
    - cost_breakdown: "Where money goes"
    - cost_per_strategy: "Which strategies are expensive"
    - net_vs_gross: "Compare gross and net returns"
```

### 10.2.7 Order Book Depth Analysis

```yaml
v1_orderbook_depth:
  description: "Analyze order book before placing large orders"
  
  why_needed: |
    As position sizes grow, you need to know:
    - Can this order fill without moving the market?
    - What's the expected slippage for this size?
    - Should we split the order?
  
  implementation:
    depth_levels: 20                    # Analyze top 20 bid/ask levels
    analysis:
      available_liquidity: "Sum of quantities at each level"
      vwap_estimate: "Volume-weighted average price for order size"
      market_impact_estimate: "Expected price move from our order"
    
    decision_rules:
      if_impact_lt_0_1_pct: "Single market order"
      if_impact_lt_0_5_pct: "Split into 2-3 orders over 5 minutes"
      if_impact_gt_0_5_pct: "Use TWAP over 15-30 minutes (V2)"
    
    alerts:
      thin_book_warning: "Alert if liquidity < 2x order size"
```

### 10.2.8 Strategy Ensemble Signals

```yaml
v1_ensemble_signals:
  description: "Multiple strategies vote on direction before entry"
  
  why_useful: |
    Single strategy can have false signals.
    If 3 of 5 strategies agree on direction, signal is stronger.
    Reduces whipsaw trades.
  
  implementation:
    ensemble_groups:
      btc_strategies:
        members: ["btc_ma_cross", "btc_rsi_mr", "btc_momentum"]
        voting_threshold: "2 of 3 agree"
        action: "Only enter if threshold met"
      
      eth_strategies:
        members: ["eth_trend", "eth_breakout"]
        voting_threshold: "2 of 2 agree"
    
    signal_aggregation:
      unanimous: "All agree → Full position size"
      majority: "Majority agrees → 75% position size"
      split: "No majority → No entry"
    
    individual_override:
      allowed: false                    # Ensemble decision is final
      exception: "Stop losses execute individually"
```

### 10.2.9 Strategy Performance Attribution

```yaml
v1_performance_attribution:
  description: "Understand WHY strategies made or lost money"
  
  why_critical: |
    "Strategy made 5%" doesn't tell you:
    - Was it skill or luck?
    - Which trades drove performance?
    - Would it work again in similar conditions?
  
  attribution_factors:
    market_return: "What did the market do? (Beta)"
    strategy_alpha: "Return above market (skill)"
    timing_contribution: "Entry/exit timing value"
    selection_contribution: "Symbol selection value"
    execution_cost: "Lost to slippage and fees"
  
  reports:
    per_trade_attribution:
      - trade_pnl: "Total P&L"
      - market_contribution: "P&L from market move"
      - strategy_contribution: "P&L from strategy decisions"
      - execution_drag: "P&L lost to execution"
    
    per_strategy_attribution:
      - total_return: "Gross return"
      - alpha: "Return above benchmark"
      - sharpe_decomposition: "Risk-adjusted performance sources"
    
  benchmark:
    crypto: "Buy and hold BTC"
    equities: "Buy and hold SPY (future)"
```

### 10.2.10 Drawdown Recovery Tracking

```yaml
v1_drawdown_recovery:
  description: "Track time and path to recover from drawdowns"
  
  why_important: |
    A strategy with 10% max drawdown sounds ok.
    But if it takes 6 months to recover, that's different.
    Need to track: How long until new high water mark?
  
  tracking:
    current_drawdown_pct: "Distance from high water mark"
    drawdown_start_date: "When did drawdown begin"
    days_in_drawdown: "How long in current drawdown"
    estimated_recovery_days: "Based on recent return rate"
  
  historical_analysis:
    all_drawdowns:
      - peak_date
      - trough_date
      - recovery_date
      - max_drawdown_pct
      - days_to_trough
      - days_to_recovery
    
    statistics:
      avg_recovery_time: "Average days to recover"
      worst_recovery_time: "Longest recovery"
      recovery_rate: "% of drawdowns that recovered"
  
  alerts:
    extended_drawdown: "Alert if drawdown > 30 days"
    deepening_drawdown: "Alert if drawdown increases 3 days in row"
```

### 10.2.11 Multi-Timeframe Confirmation

```yaml
v1_multi_timeframe:
  description: "Confirm signals across multiple timeframes"
  
  concept: |
    1H chart shows buy signal, but 4H chart is bearish.
    Which do you trust?
    Answer: Require alignment across timeframes.
  
  implementation:
    timeframe_hierarchy:
      primary: "1H"          # Main signal generation
      confirmation: "4H"     # Must align with primary
      context: "1D"          # Overall trend context
    
    alignment_rules:
      full_alignment: "All timeframes agree → Full position"
      partial_alignment: "Primary + confirmation agree → 75% position"
      no_alignment: "Timeframes conflict → No entry"
    
    per_strategy_config:
      trend_following:
        requires_higher_tf_trend: true
        context_weight: 0.3
      
      mean_reversion:
        requires_higher_tf_trend: false   # Can trade against trend
        context_weight: 0.1
```

### 10.2.12 API Key Rotation

```yaml
v1_api_key_rotation:
  description: "Secure handling of API keys with rotation capability"
  
  why_critical: |
    API keys can be compromised.
    Old keys accumulate risk.
    Need ability to rotate without downtime.
  
  implementation:
    key_management:
      storage: "Encrypted environment variables"
      encryption: "AES-256"
      rotation_reminder: "Every 90 days"
    
    rotation_process:
      1: "Generate new key on exchange"
      2: "Add new key to system (don't remove old yet)"
      3: "Verify new key works"
      4: "Switch system to new key"
      5: "Verify operations continue"
      6: "Delete old key from exchange"
      7: "Remove old key from system"
    
    emergency_rotation:
      trigger: "Suspected compromise"
      action: "Immediate rotation, close all positions first"
```

### 10.2.13 Trade Journal Automation

```yaml
v1_trade_journal:
  description: "Automated logging of trade context and rationale"
  
  why_valuable: |
    Manual trade journals are tedious and incomplete.
    Automated journals capture everything for later analysis.
    Essential for learning what works and what doesn't.
  
  capture_for_each_trade:
    market_context:
      - regime_at_entry: "trending_up, ranging, etc."
      - volatility_at_entry: "ATR value"
      - volume_at_entry: "Relative to average"
      - time_of_day: "Hour in UTC"
      - day_of_week: "Monday-Sunday"
      - btc_direction: "BTC trend at entry (for altcoins)"
    
    strategy_context:
      - signal_strength: "How strong was the signal?"
      - confirmation_count: "How many indicators confirmed?"
      - entry_type: "Breakout, pullback, reversal, etc."
      - expected_holding_period: "From strategy parameters"
    
    execution_context:
      - expected_fill_price: "Price when signal generated"
      - actual_fill_price: "Price we got"
      - slippage: "Difference"
      - time_to_fill: "Milliseconds"
    
    outcome:
      - holding_period: "Actual bars held"
      - exit_reason: "TP, SL, trailing, manual, time"
      - pnl: "Realized P&L"
      - max_favorable_excursion: "Best unrealized P&L"
      - max_adverse_excursion: "Worst unrealized P&L"
  
  analysis_queries:
    - "What time of day am I most profitable?"
    - "Which regime produces best results?"
    - "What's my average slippage by symbol?"
    - "Which exit type is most profitable?"
```

### 10.2.14 Risk Budget System

```yaml
v1_risk_budget:
  description: "Allocate risk (not just capital) across strategies"
  
  why_better_than_capital_allocation: |
    Capital allocation: "Give 10% to Strategy A"
    But if Strategy A is 3x more volatile than Strategy B,
    it contributes 3x more risk to portfolio.
    Risk allocation equalizes risk contribution.
  
  implementation:
    portfolio_risk_budget: 100         # Total risk units to allocate
    
    risk_per_strategy:
      formula: "volatility * correlation_to_portfolio * capital"
      target: "Equal risk contribution from each strategy"
    
    calculation:
      step_1: "Calculate each strategy's volatility (30-day rolling)"
      step_2: "Calculate correlation to portfolio"
      step_3: "Size position so risk contribution = target"
    
    constraints:
      min_capital_pct: 2%              # No strategy below 2%
      max_capital_pct: 20%             # No strategy above 20%
      rebalance_trigger: "Risk drift > 20%"
  
  example:
    strategy_a:
      volatility: 20%
      correlation: 0.8
      risk_weight: 16%                 # 20% * 0.8
      capital_allocation: "Sized to contribute 16 risk units"
    
    strategy_b:
      volatility: 10%
      correlation: 0.5
      risk_weight: 5%                  # 10% * 0.5
      capital_allocation: "Sized to contribute 5 risk units"
```

### 10.2.15 Benchmark Comparison Dashboard

```yaml
v1_benchmark_dashboard:
  description: "Compare strategy performance to benchmarks"
  
  why_needed: |
    "I made 20% this year" sounds good.
    "Bitcoin made 150% this year" puts it in context.
    Need to know if strategies add value vs simple buy-and-hold.
  
  benchmarks:
    primary:
      btc_hold: "Buy and hold BTC"
      eth_hold: "Buy and hold ETH"
      equal_weight: "Equal weight BTC + ETH"
    
    risk_adjusted:
      btc_vol_matched: "BTC scaled to match strategy volatility"
      risk_free: "Stablecoin yield (USDC lending)"
  
  metrics:
    vs_benchmark:
      excess_return: "Strategy return - benchmark return"
      information_ratio: "Excess return / tracking error"
      beta: "Sensitivity to benchmark"
      alpha: "Return unexplained by benchmark"
    
    rolling:
      rolling_1m: "Last 30 days vs benchmark"
      rolling_3m: "Last 90 days vs benchmark"
      rolling_ytd: "Year to date vs benchmark"
  
  dashboard_display:
    chart: "Cumulative return: Strategy vs BTC vs ETH"
    table: "Monthly excess returns"
    highlight: "Periods where strategy outperformed"
```

### 10.2.16 Time-of-Day Analysis

```yaml
v1_time_of_day:
  description: "Analyze performance by time of day"
  
  why_useful: |
    Crypto markets have patterns:
    - Asia session: 00:00-08:00 UTC
    - Europe session: 08:00-16:00 UTC
    - US session: 14:00-22:00 UTC
    Some strategies work better in certain sessions.
  
  analysis:
    segmentation:
      - hour_of_day: "0-23 UTC"
      - session: "asia, europe, us, overlap"
      - day_of_week: "Mon-Sun"
    
    metrics_per_segment:
      - trade_count: "How many trades?"
      - win_rate: "What % won?"
      - avg_return: "Average P&L"
      - sharpe: "Risk-adjusted return"
      - volatility: "How volatile?"
  
  strategy_rules:
    enable_time_filters: true
    example:
      strategy_a:
        allowed_hours: [8, 9, 10, 11, 12, 13, 14, 15]  # Europe + early US
        blocked_hours: [0, 1, 2, 3, 4, 5, 6, 7]        # Asia session
      
      strategy_b:
        allowed_days: ["mon", "tue", "wed", "thu", "fri"]  # No weekends
  
  alerts:
    underperforming_session: "Alert if strategy consistently loses in a session"
```

### 10.2.17 Slippage Model Calibration

```yaml
v1_slippage_calibration:
  description: "Continuously improve slippage predictions"
  
  why_needed: |
    MVP has slippage estimation (Feature F).
    V1 makes it adaptive: learn from actual fills.
  
  calibration_process:
    data_collection:
      - every_fill: "Record expected vs actual slippage"
      - context: "Order size, volatility, time of day, symbol"
    
    model_update:
      frequency: "Weekly"
      method: "Regression on collected data"
      validation: "Out-of-sample prediction accuracy"
    
    segmented_models:
      by_symbol: "Different slippage characteristics"
      by_order_size: "Larger orders = more slippage"
      by_volatility: "High vol = more slippage"
      by_time_of_day: "Low liquidity times = more slippage"
  
  usage:
    pre_trade_adjustment: "Use calibrated model for decisions"
    backtest_realism: "Apply learned slippage to backtests"
    strategy_rejection: "Reject strategies where slippage > profit"
```

### 10.2.18 Advanced Order Types (OCO, Bracket)

```yaml
v1_advanced_order_types:
  description: "Support for sophisticated order types beyond simple market/limit"
  
  why_needed: |
    Simple orders require multiple API calls and manual coordination.
    Advanced order types handle complex scenarios atomically.
  
  order_types:
    oco:
      name: "One-Cancels-Other (OCO)"
      description: "Pair of orders where one executing cancels the other"
      use_case: "Set take profit AND stop loss simultaneously"
      example:
        position: "Long BTC at $50,000"
        take_profit: "Limit sell at $55,000"
        stop_loss: "Stop market sell at $48,000"
        behavior: "Whichever triggers first, the other is cancelled"
      
      binance_support: true  # Native OCO on Binance
      implementation:
        use_native: true
        fallback: "Manual coordination if exchange doesn't support"
    
    bracket:
      name: "Bracket Order"
      description: "Entry order with attached take profit and stop loss"
      use_case: "One order sets up entire trade lifecycle"
      example:
        entry: "Buy BTC at $50,000 limit"
        take_profit: "Sell at $55,000"
        stop_loss: "Sell at $48,000"
      
      binance_support: false  # Must implement in system
      implementation:
        entry_fills: "Automatically place TP and SL orders"
        partial_fill_handling: "Adjust TP/SL quantities"
    
    trailing_stop_market:
      name: "Trailing Stop Market"
      description: "Stop that trails price by fixed amount/percentage"
      use_case: "Lock in profits as price moves favorably"
      parameters:
        callback_rate: "Percentage to trail (e.g., 2%)"
        activation_price: "Price at which trailing starts"
      
      binance_support: true  # Binance has trailing stop
  
  ui_support:
    order_builder:
      description: "Visual order builder for complex orders"
      features:
        - "Select order type from dropdown"
        - "Configure all legs visually"
        - "Preview order before submission"
        - "Show estimated fees and slippage"
    
    order_templates:
      description: "Save common order configurations"
      examples:
        - "2:1 RR OCO template"
        - "Breakout bracket template"
```

### 10.2.19 Extended Timeframe Support

```yaml
v1_extended_timeframes:
  description: "Support for additional and custom timeframes"
  
  mvp_timeframes:
    - "15m"
    - "1H"
    - "4H"
    - "1D"
  
  v1_additional_timeframes:
    standard:
      - "1m"   # Scalping (not recommended but available)
      - "3m"   # Fast intraday
      - "5m"   # Short-term intraday
      - "30m"  # Medium intraday
      - "2H"   # Extended intraday
      - "6H"   # Intermediate
      - "8H"   # Crypto-specific (funding rate periods)
      - "12H"  # Half-day
      - "3D"   # Multi-day
      - "1W"   # Weekly
      - "1M"   # Monthly
    
    custom:
      description: "Create custom timeframes"
      examples:
        - "45m"   # Custom 45-minute bars
        - "90m"   # Custom 90-minute bars
      implementation:
        method: "Aggregate from 1m candles"
        limitations: "Must be multiple of 1m"
        max_custom: 10  # Max 10 custom timeframes
  
  multi_timeframe_strategies:
    description: "Single strategy using multiple timeframes"
    v1_capability:
      timeframe_roles:
        primary: "Signal generation"
        confirmation: "Trend confirmation"
        entry: "Precise entry timing"
      
      example:
        strategy: "EMA Trend with MTF confirmation"
        primary: "1H for signals"
        confirmation: "4H trend must agree"
        entry: "15m for precise entry"
      
      alignment_requirements:
        all_agree: "Strongest signal"
        majority: "Reduced position size"
        conflict: "No entry"
  
  ui_settings:
    timeframe_selector:
      show_all: true
      favorites: "Mark frequently used"
      recent: "Show recently used"
    
    custom_timeframe_builder:
      input: "Minutes (e.g., 45 for 45m)"
      validation: "Must be >= 1 and <= 10080 (1 week)"
```

## 10.3 V1 Success Criteria

| Criterion | Target |
|-----------|--------|
| Additional broker working | At least 1 new broker live |
| Batch generation functional | Generate 50+ variants at once |
| Regime detection accuracy | > 60% correct vs hindsight |
| Cost tracking complete | 100% of costs captured |
| Continued profitability | Maintain positive returns |

---

# PART 11: V2 ROADMAP

## 11.1 V2 Overview

**V2 Goal:** Advanced automation, research capabilities, and operational sophistication.

**Prerequisites:** V1 stable for 3+ months, accumulated data for ML

**Timeline:** 6-12 months after V1 completion

## 11.2 V2 Capabilities

### 11.2.1 Automated Regime Detection

```yaml
v2_auto_regime:
  description: "System detects and acts on regime without confirmation"
  
  model:
    type: "classification"
    features:
      - price_ma_distances
      - atr_ratio
      - rsi_level
      - volume_ratio
      - recent_return
    training_data: "Historical regimes labeled by operator"
  
  confidence_threshold: 70%
  fallback: "If confidence < threshold, ask for confirmation"
  
  actions:
    - high_confidence_regime: "Auto-adjust strategy weights"
    - low_confidence: "Alert and ask for input"
  
  tracking:
    - accuracy_vs_operator: "Compare to what operator would have chosen"
    - regime_return_attribution: "Did regime call help or hurt"
```

### 11.2.2 Symbol Discovery and Research

```yaml
v2_symbol_discovery:
  description: "System suggests new symbols to trade"
  
  criteria:
    - liquidity: "Minimum volume threshold"
    - volatility: "Within acceptable range"
    - correlation: "Low correlation to existing symbols"
    - strategy_fit: "Backtests well on existing strategies"
  
  workflow:
    1. System scans universe of symbols
    2. Filters by liquidity and basic criteria
    3. Runs backtests on promising symbols
    4. Ranks by performance
    5. Presents recommendations to operator
    6. Operator approves additions
```

### 11.2.3 Strategy Correlation Management

```yaml
v2_correlation:
  description: "Manage portfolio of strategies for diversification"
  
  features:
    - correlation_matrix: "Strategy return correlations"
    - concentration_warnings: "Alert on high correlation"
    - diversification_score: "Portfolio diversification metric"
    - allocation_optimizer: "Suggest allocations for diversification"
  
  rules:
    - max_correlation_for_new_strategy: 0.5
    - rebalance_trigger: "Correlation drift > 0.2"
```

### 11.2.4 ML-Enhanced Templates (Lite Approach)

Based on legacy system learnings: the ML Strategy Generator Lite outperformed full ML by 4x (65 vs 14 strategies). V2 adopts this "lite" approach.

```yaml
v2_ml_enhanced_templates:
  description: "Templates with ML-suggested parameters (not full ML strategies)"
  
  philosophy:
    - "Templates remain the core strategy structure"
    - "ML suggests optimal parameter values, not strategy logic"
    - "Always falls back to template defaults if ML fails"
    - "Human approval still required for live deployment"
  
  how_it_works:
    1. Template defines strategy structure (same as MVP)
    2. ML analyzes recent market data for symbol
    3. ML suggests parameter values within template ranges
    4. System generates strategy with ML-suggested parameters
    5. Strategy goes through normal backtest → paper → live pipeline
  
  ml_suggestions:
    - ma_periods: "Based on recent trend characteristics"
    - rsi_thresholds: "Based on recent overbought/oversold behavior"
    - stop_loss_pct: "Based on recent ATR and volatility"
    - take_profit_pct: "Based on recent price swing ranges"
  
  safeguards:
    - parameters_must_be_within_template_ranges: true
    - fallback_to_defaults_on_ml_failure: true
    - require_backtest_validation: true
    - no_ml_generated_strategy_logic: true
  
  expected_benefit:
    - "4x strategy generation throughput (based on legacy data)"
    - "Better initial parameter guesses = fewer backtest failures"
    - "Still fully explainable (templates + parameters)"
```

### 11.2.5 Tax and Audit Reports (Optional — Region Dependent)

```yaml
v2_tax_reports:
  description: "Generate reports for tax filing and business operations"
  
  status: "OPTIONAL — Depends on your tax jurisdiction"
  
  regional_notes:
    tanzania: "Tanzania currently has no specific crypto tax regulations. Skip this feature."
    us_uk_eu: "Required for compliance. Build if operating in these jurisdictions."
    other: "Check local regulations before investing time in this feature."
  
  reports:
    - trade_report:
        format: "CSV"
        contents: "All trades with cost basis"
        use: "Import into tax software or accountant"
    
    - realized_gains:
        format: "PDF"
        contents: "Summary of realized gains/losses"
        use: "Tax filing, personal records"
    
    - annual_summary:
        format: "PDF"
        contents: "Year-end performance summary"
        use: "Business records, investor reporting"
  
  tax_loss_harvesting:
    description: "Automatically sell losing positions for tax deductions"
    status: "SKIP — Not relevant for Tanzanian tax jurisdiction"
    future_consideration: "Implement only if regulations change or operating in taxed jurisdictions"
  
  compliance:
    - data_retention: "7 years minimum (even if not taxed, good practice)"
    - audit_trail: "Complete and immutable"
  
  recommendation: |
    For Tanzania: Skip tax reports initially. Keep good records.
    If regulations change or you operate in US/UK/EU later, implement then.
```

### 11.2.5 Research Mode

```yaml
v2_research:
  description: "Guided exploration for manual research"
  
  features:
    - symbol_explorer: "View symbol metrics and history"
    - indicator_tester: "Quick indicator visualization"
    - hypothesis_tracker: "Log and track research ideas"
    - quick_backtest: "Fast backtest without full validation"
  
  workflow:
    1. Select symbol(s)
    2. Apply indicators
    3. Visualize price and indicators
    4. Run quick backtest
    5. Log findings
    6. If promising: create formal strategy
```

### 11.2.6 Portfolio Rebalancing

```yaml
v2_rebalancing:
  description: "Automated portfolio rebalancing suggestions"
  
  triggers:
    - drift_threshold: "Allocation drifts > 5% from target"
    - time_based: "Monthly rebalance check"
    - performance_based: "Strategy outperforms/underperforms"
  
  workflow:
    1. Calculate current vs target allocations
    2. Generate rebalancing trades
    3. Present to operator
    4. Operator approves
    5. System executes rebalancing
```

### 11.2.7 Execution Algorithms (TWAP/VWAP)

```yaml
v2_execution_algorithms:
  description: "Sophisticated order execution to reduce market impact"
  
  why_needed: |
    As account grows, single market orders move the price against you.
    Need to split orders intelligently over time.
  
  algorithms:
    twap:
      name: "Time-Weighted Average Price"
      description: "Split order evenly over time period"
      parameters:
        duration_minutes: 15            # Execute over 15 minutes
        slice_count: 6                  # 6 child orders
        randomization: true             # Slightly randomize timing
      use_when: "Order size > 5% of 15-min volume"
    
    vwap:
      name: "Volume-Weighted Average Price"
      description: "Execute more when volume is high"
      parameters:
        duration_minutes: 30
        volume_profile: "historical"    # Use historical volume pattern
        participation_rate: 0.1         # Max 10% of volume
      use_when: "Order size > 10% of 15-min volume"
    
    iceberg:
      name: "Iceberg Order"
      description: "Show only small portion, refill as filled"
      parameters:
        visible_pct: 0.2                # Show 20% of total
        refill_threshold: 0.5           # Refill when 50% of visible filled
      use_when: "Want to hide order size from market"
  
  selection:
    automatic: true                     # System chooses algorithm
    criteria:
      - order_size_vs_volume
      - urgency: "Urgent = simple market order"
      - market_volatility
```

### 11.2.8 Market Impact Model

```yaml
v2_market_impact:
  description: "Predict and minimize our impact on market prices"
  
  why_critical: |
    Large orders move prices. Need to:
    1. Predict how much our order will move the price
    2. Decide if trade is still worth it after impact
    3. Choose execution strategy to minimize impact
  
  model_components:
    temporary_impact:
      description: "Price move during our execution"
      formula: "k * (volume / ADV) ^ 0.5 * volatility"
      parameters:
        k: "Calibrated constant (0.1 - 0.3)"
        ADV: "Average daily volume"
    
    permanent_impact:
      description: "Price move that persists after execution"
      formula: "lambda * (volume / ADV)"
      parameters:
        lambda: "Information leakage factor"
  
  usage:
    pre_trade:
      expected_impact: "Calculate before deciding to trade"
      adjusted_expected_return: "Return - expected impact"
      trade_decision: "Only trade if adjusted return > threshold"
    
    post_trade:
      actual_impact: "Measure actual vs expected"
      model_calibration: "Update model parameters"
```

### 11.2.9 Alternative Data Integration (Crypto-Specific)

```yaml
v2_alternative_data:
  description: "Integrate crypto-specific data beyond price/volume"
  
  data_sources:
    funding_rate:
      description: "Perpetual futures funding rate"
      signal: "High positive = over-leveraged longs, expect correction"
      integration: "Reduce long exposure when funding > 0.1%"
    
    open_interest:
      description: "Total outstanding derivative contracts"
      signal: "Rising OI + rising price = strong trend"
      integration: "Confirm trend signals"
    
    liquidation_data:
      description: "Forced liquidations on exchanges"
      signal: "Large liquidations = potential reversal"
      integration: "Pause entries during liquidation cascades"
    
    exchange_flows:
      description: "BTC flowing into/out of exchanges"
      signal: "Inflows = selling pressure, outflows = accumulation"
      integration: "Regime indicator"
    
    whale_alerts:
      description: "Large transactions on-chain"
      signal: "Large exchange deposits = potential selling"
      integration: "Caution flag on large inflows"
  
  data_providers:
    - coinglass: "Funding, OI, liquidations"
    - glassnode: "On-chain metrics"
    - whale_alert: "Large transaction alerts"
```

### 11.2.10 Dynamic Position Sizing

```yaml
v2_dynamic_position_sizing:
  description: "Adjust position sizes based on market conditions"
  
  why_better_than_fixed: |
    Fixed 5% position size ignores:
    - Current volatility (high vol = smaller position)
    - Recent performance (losing streak = smaller position)
    - Strategy confidence (high confidence = larger position)
    - Correlation with existing positions
  
  sizing_methods:
    volatility_adjusted:
      description: "Size inversely proportional to volatility"
      formula: "base_size * (target_volatility / current_volatility)"
      parameters:
        target_volatility: 0.02         # 2% daily vol target
        max_adjustment: 2.0             # Max 2x base size
        min_adjustment: 0.25            # Min 0.25x base size
    
    kelly_fraction:
      description: "Kelly criterion with fractional sizing"
      formula: "kelly_pct = (win_rate * avg_win - loss_rate * avg_loss) / avg_win"
      parameters:
        fraction: 0.25                  # Use 25% of Kelly (safer)
        max_kelly_pct: 0.2              # Cap at 20% even if Kelly says more
    
    risk_parity_lite:
      description: "Equal risk contribution from each strategy"
      formula: "size_i = target_risk / volatility_i / sum(1/volatility_all)"
      parameters:
        target_portfolio_risk: 0.15     # 15% annualized vol target
  
  adaptive_rules:
    losing_streak: "Reduce size by 20% after 3 consecutive losses"
    winning_streak: "Can increase by 10% after 5 consecutive wins"
    drawdown_reduction: "Reduce size proportionally during drawdown"
```

### 11.2.11 Strategy Decay Early Warning

```yaml
v2_decay_early_warning:
  description: "Detect strategy decay BEFORE it fails validation"
  
  why_critical: |
    Current system: Strategy fails → gets flagged → maybe re-optimized
    Better: Detect degradation early → proactive intervention
  
  leading_indicators:
    edge_erosion:
      metric: "Rolling Sharpe vs initial Sharpe"
      warning: "Sharpe dropped 30% from backtest"
      action: "Flag for review, don't wait for full failure"
    
    win_rate_decline:
      metric: "10-trade rolling win rate vs backtest"
      warning: "Win rate 15% below backtest for 10+ trades"
      action: "Reduce position size, flag for review"
    
    timing_degradation:
      metric: "Average bars held vs backtest"
      warning: "Holding 50% longer than backtest average"
      action: "Exit logic may not be triggering properly"
    
    correlation_increase:
      metric: "Strategy correlation with market"
      warning: "Correlation increased from 0.3 to 0.7"
      action: "Strategy losing its edge, becoming market beta"
  
  response_automation:
    mild_decay: "Alert operator, continue trading"
    moderate_decay: "Reduce position size to 50%"
    severe_decay: "Auto-pause, require operator review"
```

### 11.2.12 Monte Carlo Validation

```yaml
v2_monte_carlo:
  description: "Validate strategies with randomized scenario testing"
  
  why_needed: |
    Backtest shows ONE historical path.
    But what if trade order was different?
    What if we had bad luck on timing?
    Monte Carlo tests many possible outcomes.
  
  simulations:
    trade_shuffling:
      description: "Randomize order of trades, keep same trades"
      iterations: 1000
      output: "Distribution of final returns"
      accept_criteria: "95th percentile still profitable"
    
    return_bootstrapping:
      description: "Resample daily returns with replacement"
      iterations: 1000
      output: "Distribution of Sharpe ratios"
      accept_criteria: "5th percentile Sharpe > 0.5"
    
    drawdown_simulation:
      description: "Estimate probability of various drawdowns"
      output: "Probability of 20% drawdown, 30% drawdown, etc."
      accept_criteria: "P(30% drawdown) < 5%"
  
  reporting:
    confidence_intervals: "Return expected between X and Y with 95% confidence"
    worst_case_scenario: "In worst 5% of simulations, lost X%"
    risk_of_ruin: "Probability of losing 50%+ of capital"
```

### 11.2.13 Walk-Forward Optimization

```yaml
v2_walk_forward:
  description: "Continuously re-optimize strategies as new data arrives"
  
  why_needed: |
    Static optimization: Optimize once, deploy forever.
    Problem: Markets change, optimal parameters shift.
    Walk-forward: Periodically re-optimize with recent data.
  
  implementation:
    schedule:
      frequency: "Monthly"
      data_window: "Rolling 6 months"
      optimization_time: "Weekend (low activity)"
    
    process:
      1: "Gather last 6 months of data"
      2: "Run optimization on 4 months (in-sample)"
      3: "Validate on 2 months (out-of-sample)"
      4: "If improvement > threshold, propose new parameters"
      5: "Operator approves or rejects"
    
    safeguards:
      min_improvement_threshold: 10%   # Must be meaningfully better
      max_parameter_change: 30%        # Parameters can't change too much
      require_oos_validation: true     # Must pass out-of-sample test
      operator_approval: true          # Human reviews changes
    
    tracking:
      version_history: "Keep all parameter versions"
      performance_comparison: "Compare new vs old"
      rollback_capability: "Can revert to previous version"
```

### 11.2.14 Liquidity Regime Detection

```yaml
v2_liquidity_regime:
  description: "Detect and adapt to changing liquidity conditions"
  
  why_important: |
    Same strategy behaves differently in:
    - High liquidity: Tight spreads, easy fills, low slippage
    - Low liquidity: Wide spreads, partial fills, high slippage
    Need to detect and adapt.
  
  liquidity_indicators:
    spread_ratio: "Current spread / average spread"
    depth_ratio: "Current book depth / average depth"
    volume_ratio: "Current volume / average volume"
    trade_frequency: "Trades per minute vs average"
  
  liquidity_regimes:
    high_liquidity:
      criteria: "All indicators > 1.2"
      actions:
        - position_size: "Can use full size"
        - order_type: "Market orders acceptable"
        - spread_tolerance: "Normal"
    
    normal_liquidity:
      criteria: "Indicators between 0.8 and 1.2"
      actions:
        - position_size: "Normal"
        - order_type: "Prefer limit orders"
    
    low_liquidity:
      criteria: "Any indicator < 0.5"
      actions:
        - position_size: "Reduce by 50%"
        - order_type: "Limit orders only"
        - spread_tolerance: "Widen acceptable spread"
        - alert_operator: true
    
    crisis_liquidity:
      criteria: "Multiple indicators < 0.3"
      actions:
        - new_entries: "Pause"
        - exits_only: true
        - alert_operator: "URGENT"
```

### 11.2.15 Cross-Asset Correlation Tracking

```yaml
v2_cross_asset_correlation:
  description: "Monitor correlations across all traded assets"
  
  why_critical_at_scale: |
    With multiple assets/strategies:
    - BTC-ETH correlation: Usually 0.85+
    - During stress: Correlation approaches 1.0
    - "Diversification" disappears when you need it most
  
  tracking:
    correlation_matrix:
      assets: "All traded symbols"
      lookback: "30-day rolling"
      update_frequency: "Daily"
    
    metrics:
      average_correlation: "Mean of all pairwise correlations"
      max_correlation: "Highest pairwise correlation"
      correlation_cluster: "Groups of highly correlated assets"
      effective_assets: "Diversification-adjusted asset count"
  
  alerts:
    correlation_spike:
      threshold: "Average correlation increases > 20% in 7 days"
      action: "Alert operator, suggest reducing exposure"
    
    new_asset_correlation:
      check: "Before adding new asset, check correlation to existing"
      threshold: "Reject if correlation > 0.7 with any existing"
  
  stress_testing:
    scenario: "What if all correlations go to 0.95?"
    calculate: "Portfolio volatility under stress"
    action: "Ensure position sizes account for stress correlation"
```

### 11.2.16 Synthetic Data Generation

```yaml
v2_synthetic_data:
  description: "Generate realistic fake data for testing"
  
  why_useful: |
    Real historical data is limited.
    Can't test rare events that haven't happened.
    Synthetic data lets you test:
    - Flash crashes
    - Extended bear markets
    - Liquidity crises
    - Black swan events
  
  generation_methods:
    bootstrap:
      description: "Resample from real data"
      use: "Generate more data with same characteristics"
    
    garch_simulation:
      description: "Simulate with volatility clustering"
      use: "Realistic volatility dynamics"
    
    regime_switching:
      description: "Simulate regime changes"
      use: "Test strategy across different regimes"
    
    extreme_events:
      description: "Inject extreme moves"
      use: "Stress test strategies"
      examples:
        - flash_crash: "-30% in 10 minutes"
        - extended_dump: "-50% over 30 days"
        - v_shaped_recovery: "-40% then +60% in 1 week"
  
  validation:
    statistical_tests: "Synthetic data passes same tests as real"
    visual_inspection: "Charts look realistic"
    strategy_behavior: "Strategies behave similarly on real vs synthetic"
```

## 11.3 V2 Success Criteria

| Criterion | Target |
|-----------|--------|
| Auto regime accuracy | > 70% correct |
| Symbol discovery working | At least 2 symbols added via discovery |
| Correlation management | Portfolio diversification score > 0.6 |
| Tax reports generated | Annual report produced |
| Research mode used | At least 5 research sessions logged |

---

# PART 12: MATURITY ROADMAP

## 12.1 Maturity Overview

**Maturity Goal:** Full "everything system" capabilities with advanced AI/ML.

**Prerequisites:** V2 stable for 6+ months, significant data accumulation

**Timeline:** 2-5 years after initial MVP

## 12.2 Maturity Capabilities

### 12.2.1 ML Strategy Generation (Full ML — Not Before Maturity)

**Evolution Path:**
```
MVP: Templates only (3 templates, manual parameters)
  ↓
V1: Batch template generation (parameter sweeps, ranking)
  ↓
V2: ML-enhanced templates (ML suggests parameters, templates remain core)
  ↓
Maturity: Full ML (ML generates strategy logic, not just parameters)
```

**Why wait until Maturity?**
- Need 2+ years of YOUR data to train models properly
- Need proven template success to compare against
- Legacy system lesson: Full ML produced 4x FEWER strategies than lite templates
- ML strategies are black boxes — need high confidence before deploying

```yaml
maturity_ml_strategies:
  description: "Machine learning for strategy discovery (full ML, not template-based)"
  
  prerequisites:
    - v2_stable_12_months: "V2 ML-enhanced templates working profitably"
    - data_accumulation: "2+ years of trade data"
    - template_baseline: "Know what good looks like from templates"
  
  approaches:
    - feature_discovery:
        method: "Random Forest feature importance"
        purpose: "Find predictive features"
    
    - pattern_recognition:
        method: "LSTM / Transformer"
        purpose: "Find temporal patterns"
    
    - reinforcement_learning:
        method: "PPO / DQN"
        purpose: "Learn trading policies"
    
    - ensemble:
        method: "Combine multiple models"
        purpose: "Robust predictions"
  
  safeguards:
    - extensive_backtesting: "Multiple years, multiple regimes"
    - walk_forward_required: "Strict out-of-sample testing"
    - paper_trading_extended: "3+ months paper trading (vs 28 days for templates)"
    - human_approval: "Still required for live"
    - position_limits: "ML strategies capped at 10% portfolio initially"
    - must_beat_templates: "Must outperform best template strategies"
```

### 12.2.2 Alpha Discovery Engine

```yaml
maturity_alpha:
  description: "Systematic search for new alpha sources"
  
  components:
    - data_ingestion: "Multiple data sources"
    - feature_engineering: "Automated feature creation"
    - signal_testing: "Rapid signal evaluation"
    - decay_analysis: "Track alpha decay over time"
  
  data_sources:
    - price_data: "Multiple timeframes"
    - volume_data: "Volume patterns"
    - orderbook_data: "Microstructure"
    - sentiment_data: "Social, news"
    - on_chain_data: "Blockchain metrics (crypto)"
  
  workflow:
    1. Generate candidate signals
    2. Filter by statistical significance
    3. Test for look-ahead bias
    4. Evaluate decay rate
    5. Combine into strategies
    6. Full validation pipeline
```

### 12.2.3 Sentiment Analysis

```yaml
maturity_sentiment:
  description: "Incorporate market sentiment into trading"
  
  sources:
    - twitter: "Crypto Twitter sentiment"
    - reddit: "Reddit sentiment"
    - news: "News sentiment"
    - fear_greed_index: "Market fear/greed"
  
  integration:
    - sentiment_indicator: "Dashboard display"
    - strategy_input: "Sentiment as strategy input"
    - regime_modifier: "Adjust regime based on sentiment"
```

### 12.2.4 Advanced Execution

```yaml
maturity_execution:
  description: "Sophisticated execution algorithms"
  
  algorithms:
    - twap: "Time-weighted average price"
    - vwap: "Volume-weighted average price"
    - implementation_shortfall: "Minimize execution cost"
  
  use_cases:
    - large_orders: "Orders > 1% of daily volume"
    - rebalancing: "Minimize impact during rebalancing"
```

### 12.2.5 Mobile Application

```yaml
maturity_mobile:
  description: "Native mobile app for monitoring and control"
  
  features:
    - dashboard: "Portfolio overview"
    - alerts: "Push notifications"
    - positions: "View and close positions"
    - kill_switch: "Emergency stop"
  
  platforms:
    - ios: "Native iOS app"
    - android: "Native Android app"
```

### 12.2.6 Multi-Asset Expansion

```yaml
maturity_multi_asset:
  description: "Expand beyond crypto to full multi-asset"
  
  asset_classes:
    - crypto: "Already supported"
    - forex: "Via Deriv or other"
    - stocks: "Via Alpaca / Interactive Brokers"
    - futures: "Index futures"
    - options: "Options strategies (advanced)"
  
  unified_features:
    - cross_asset_correlation: "Track correlations"
    - asset_allocation: "Strategic allocation"
    - hedging: "Cross-asset hedging"
```

### 12.2.7 Fully Autonomous Mode

```yaml
maturity_autonomous:
  description: "Option for full autonomy (with safeguards)"
  
  toggle: "Can be enabled/disabled"
  
  when_enabled:
    - auto_deploy_strategies: "Deploy after validation"
    - auto_regime_adjust: "Adjust to regime"
    - auto_rebalance: "Rebalance portfolio"
    - auto_retire: "Retire failing strategies"
  
  safeguards_always_active:
    - risk_limits: "Never exceeded"
    - kill_switch: "Always available"
    - logging: "All decisions logged"
    - alerts: "All actions reported"
```

### 12.2.8 Groundbreaking Maturity Features

These features represent the cutting edge of autonomous trading systems:

#### A. Meta-Learning (Learning to Learn)
```yaml
meta_learning:
  description: "System learns HOW to create strategies, not just strategies"
  
  capability: |
    Instead of: "Here's a good MA crossover strategy"
    System learns: "What makes MA crossover work in certain conditions?"
    Then applies: "Market looks like condition X, so use MA parameters Y"
  
  implementation:
    - store_strategy_context: "Record market conditions when strategy was created"
    - track_strategy_lifetime: "How long did it remain profitable?"
    - correlate_conditions_to_success: "Which conditions predict success?"
    - generate_conditional_strategies: "Create strategies FOR specific conditions"
  
  requirement: "3+ years of strategy generation data"
```

#### B. Continuous Online Learning
```yaml
continuous_learning:
  description: "Strategies adapt parameters in real-time (not just periodic re-optimization)"
  
  how_it_differs: |
    Traditional: Strategy fixed at deployment, re-optimize manually when failing
    Continuous: Strategy adjusts parameters continuously within bounds
  
  example: |
    MA crossover deployed with fast=10, slow=50
    Market becomes more volatile
    System automatically adjusts to fast=8, slow=40 (within allowed range)
    No human intervention needed
  
  safeguards:
    - parameter_bounds: "Can only adjust within template limits"
    - change_rate_limit: "Max 10% parameter change per week"
    - performance_guard: "Stop adjusting if performance degrades"
    - audit_trail: "Log all automatic adjustments"
```

#### C. Adversarial Robustness Testing
```yaml
adversarial_testing:
  description: "Test strategies against adversarial market conditions"
  
  why_critical: |
    Most backtests use historical data.
    But what if the market ADAPTS to your strategy?
    What if a flash crash happens?
    What if liquidity disappears?
  
  tests:
    - strategy_crowding: "Simulate many traders using your strategy"
    - liquidity_shock: "What if orderbook depth drops 90%?"
    - correlation_breakdown: "What if BTC-ETH correlation inverts?"
    - flash_crash: "30% drop in 10 minutes"
    - exchange_outage: "4-hour exchange downtime"
  
  requirement: "Strategy must survive all adversarial tests"
```

#### D. Causal Inference (Beyond Correlation)
```yaml
causal_inference:
  description: "Find causation, not just correlation"
  
  problem: |
    Correlation: "When RSI drops below 30, price often rises"
    But is this because:
    - RSI predicts price? (causal)
    - Both respond to same hidden factor? (spurious)
    - Price dropping causes RSI to drop? (reverse causation)
  
  techniques:
    - granger_causality: "Does X predict Y beyond what Y predicts itself?"
    - instrumental_variables: "Find factors that affect X but not Y directly"
    - natural_experiments: "Use market structure changes as experiments"
    - counterfactual_analysis: "What would have happened if signal was opposite?"
  
  benefit: "Strategies based on causation decay slower than correlation-based"
```

#### E. Self-Healing Systems
```yaml
self_healing:
  description: "System automatically detects and fixes issues"
  
  capabilities:
    - connection_recovery: "Auto-reconnect to exchange on disconnect"
    - data_gap_detection: "Detect missing data, interpolate or pause"
    - strategy_isolation: "If one strategy errors, others continue"
    - automatic_failover: "Switch to backup systems on failure"
    - anomaly_correction: "Detect and handle erroneous data (flash crashes)"
  
  examples:
    - exchange_disconnect: "Auto-reconnect, resume from last known state"
    - invalid_price: "Detect price 50% below market, ignore as error"
    - memory_leak: "Detect growing memory, auto-restart cleanly"
    - hung_order: "Detect orders stuck >5 minutes, cancel and retry"
```

### 12.2.9 Transfer Learning Across Assets

```yaml
maturity_transfer_learning:
  description: "Apply lessons learned from one asset to another"
  
  concept: |
    You've learned BTC momentum strategy works well.
    Can you apply that knowledge to ETH without starting from scratch?
    Transfer learning accelerates strategy development for new assets.
  
  implementation:
    feature_transfer:
      description: "Same technical indicators work across assets"
      example: "RSI overbought works for BTC and ETH similarly"
      method: "Share feature engineering code, adjust parameters"
    
    model_transfer:
      description: "Pre-train on BTC, fine-tune on ETH"
      example: "LSTM trained on BTC price patterns, adapted to ETH"
      method: "Transfer weights, freeze early layers, retrain final layers"
    
    parameter_transfer:
      description: "Use BTC optimal parameters as starting point for ETH"
      example: "BTC MA crossover (10, 50) → Start ETH search near (10, 50)"
      benefit: "Faster optimization, better starting point"
  
  safeguards:
    validation_required: "Transferred strategy must pass full validation"
    no_blind_transfer: "Don't just copy, must prove it works"
    asset_specific_tuning: "Allow parameters to adjust to new asset"
```

### 12.2.10 Explainable AI (XAI)

```yaml
maturity_explainable_ai:
  description: "Understand WHY ML models make decisions"
  
  why_critical: |
    "Model says BUY" isn't enough.
    Need to know: Why does it say buy? Is the reason valid?
    Explainability builds trust and catches errors.
  
  techniques:
    feature_importance:
      description: "Which inputs drove the prediction?"
      method: "SHAP values, permutation importance"
      output: "RSI contributed 40%, MACD 30%, volume 20%, etc."
    
    attention_visualization:
      description: "What is the model looking at?"
      method: "Attention weights from transformer models"
      output: "Model focused on last 3 candles, ignored older data"
    
    counterfactual_explanation:
      description: "What would change the decision?"
      method: "Find minimal input change that flips prediction"
      output: "If RSI was 25 instead of 28, model would say SELL"
    
    rule_extraction:
      description: "Convert model to human-readable rules"
      method: "Decision tree approximation of neural network"
      output: "IF RSI < 30 AND MACD_cross = up THEN BUY"
  
  integration:
    dashboard_display: "Show explanation alongside every ML signal"
    audit_trail: "Log explanations for all trades"
    operator_review: "Flag trades where explanation seems wrong"
```

### 12.2.11 Strategy Crowding Detection

```yaml
maturity_crowding_detection:
  description: "Detect when too many traders use similar strategies"
  
  why_critical: |
    If your strategy is crowded:
    - Entry signals come late (others already entered)
    - Exit signals cause crashes (everyone exits together)
    - Alpha decays rapidly as others arbitrage it away
  
  detection_methods:
    volume_analysis:
      description: "Unusual volume at strategy entry points"
      signal: "Volume spike exactly when your entry triggers"
      interpretation: "Others using same signal"
    
    slippage_analysis:
      description: "Increasing slippage over time"
      signal: "Slippage trending upward for same order size"
      interpretation: "More competition for liquidity"
    
    return_autocorrelation:
      description: "Strategy returns becoming more predictable"
      signal: "Returns show patterns where none existed before"
      interpretation: "Others trading against the pattern"
    
    signal_to_price_lag:
      description: "Market moves before your signal triggers"
      signal: "Price already moved 50% of expected move before entry"
      interpretation: "Faster traders front-running the signal"
  
  response:
    mild_crowding: "Adjust parameters to differentiate"
    moderate_crowding: "Reduce position sizes"
    severe_crowding: "Retire strategy, it's arbitraged away"
```

### 12.2.12 Market Microstructure Analysis

```yaml
maturity_microstructure:
  description: "Analyze order flow and market structure for edge"
  
  concepts:
    order_flow_imbalance:
      description: "More buy orders vs sell orders"
      signal: "Predicts short-term price direction"
      use: "Improve entry timing by seconds"
    
    trade_arrival_rate:
      description: "How fast are trades happening?"
      signal: "Increasing rate often precedes big move"
      use: "Early warning of volatility"
    
    spread_dynamics:
      description: "Bid-ask spread changes"
      signal: "Widening spread = uncertainty, tightening = stability"
      use: "Avoid trading during wide spreads"
    
    depth_imbalance:
      description: "More bids vs asks in order book"
      signal: "Imbalance predicts short-term direction"
      use: "Fine-tune entry timing"
  
  data_requirements:
    tick_data: "Every trade, not just candles"
    order_book_snapshots: "Regular snapshots of book depth"
    trade_tape: "Who was aggressor (buyer or seller)"
  
  implementation:
    real_time_scoring: "Score microstructure favorability 0-100"
    entry_timing: "Only enter when microstructure score > 60"
    execution_optimization: "Choose limit vs market based on book state"
```

### 12.2.13 Predictive Risk Management

```yaml
maturity_predictive_risk:
  description: "Predict and preemptively manage risk"
  
  current_approach: |
    Risk limits trigger AFTER breach:
    - Drawdown hits 10% → pause strategy
    - This is reactive, damage already done
  
  predictive_approach: |
    Predict risk BEFORE it materializes:
    - Model predicts 70% chance of 10% drawdown this week
    - Preemptively reduce exposure
  
  models:
    drawdown_prediction:
      inputs: "Recent volatility, momentum, correlation changes"
      output: "Probability of X% drawdown in next N days"
      action: "Reduce exposure if P(10% drawdown) > 30%"
    
    volatility_forecasting:
      inputs: "GARCH model, implied volatility, recent returns"
      output: "Expected volatility for next day/week"
      action: "Adjust position sizes inversely to expected vol"
    
    tail_risk_prediction:
      inputs: "Order book depth, funding rates, liquidation levels"
      output: "Probability of flash crash"
      action: "Tighten stops, reduce leverage before high-risk periods"
  
  integration:
    daily_risk_forecast: "Dashboard shows predicted risk for coming day"
    automatic_adjustment: "System can auto-adjust exposure (with operator approval)"
    scenario_alerts: "Alert when entering high-risk scenario"
```

### 12.2.14 Fund-Ready Infrastructure

```yaml
maturity_fund_infrastructure:
  description: "Infrastructure capable of managing external capital"
  
  why_plan_for_this: |
    If system works well for personal trading,
    might want to manage capital for others.
    Better to build foundation now than retrofit later.
  
  requirements:
    investor_accounting:
      - multi_investor_tracking: "Track each investor's capital, returns"
      - high_water_mark: "Per-investor HWM for performance fees"
      - audit_trail: "Complete record of all transactions"
    
    reporting:
      - investor_statements: "Monthly statements for each investor"
      - performance_attribution: "Explain returns to investors"
      - risk_reports: "Show risk metrics and limits"
    
    compliance:
      - trade_allocation: "Fair allocation across investors"
      - best_execution: "Prove best execution for each trade"
      - conflict_management: "Handle conflicts of interest"
    
    operations:
      - subscription_redemption: "Handle investor capital flows"
      - nav_calculation: "Daily/weekly NAV calculation"
      - fee_calculation: "Management and performance fees"
  
  note: "These are CAPABILITIES to build, not a plan to start a fund"
```

### 12.2.15 Options and Derivatives Trading (If Ever)

```yaml
maturity_options_derivatives:
  description: "Support for trading options and other derivatives"
  
  status: "Optional future feature — may never be implemented"
  
  why_consider: |
    Options provide:
    - Non-linear payoffs (defined risk, unlimited upside)
    - Hedging capabilities
    - Income generation (selling premium)
    - Volatility trading (not just direction)
  
  potential_instruments:
    crypto_options:
      exchange: "Deribit (primary), Binance Options"
      instruments:
        - btc_options: "BTC European options"
        - eth_options: "ETH European options"
      strategies:
        - covered_calls: "Sell calls against spot holdings"
        - protective_puts: "Buy puts for downside protection"
        - straddles: "Trade volatility events"
    
    perpetual_futures:
      description: "Already crypto-native derivative"
      current_support: "Research/backtest layer supports long+short futures with conservative funding-cost model (DEC-2026-05-28-001, 2026-05-28). LIVE execution remains spot-only until step 4 of the staged plan (proven short edge + futures execution adapter)."
      enhancement: "Full perpetuals support (live execution adapter + liquidation/margin risk + leverage controls)"
      features:
        - funding_rate_arbitrage
        - basis_trading
        - delta_neutral_strategies
  
  requirements_to_implement:
    - proven_spot_profitability: "Spot strategies profitable 2+ years"
    - risk_management_maturity: "Full risk system operational"
    - capital_base: "Sufficient capital for margin requirements"
    - operator_knowledge: "Understanding of derivatives Greeks"
  
  implementation_phases:
    phase_1: "Perpetual futures (closest to spot)"
    phase_2: "Simple options (covered calls, protective puts)"
    phase_3: "Complex options strategies (spreads, straddles)"
  
  risks:
    - leverage_amplification: "Losses can exceed initial capital"
    - complexity: "Greeks, decay, vol surface"
    - liquidity: "Options markets less liquid"
  
  decision: "Defer until spot trading is consistently profitable for 2+ years"
```

### 12.2.16 Mobile Application (Flutter)

```yaml
maturity_mobile_app:
  description: "Dedicated mobile application for monitoring and control"
  
  technology:
    framework: "Flutter"
    platforms: ["iOS", "Android"]
    reason: "Single codebase, native performance, developer familiarity"
  
  core_features:
    dashboard:
      - portfolio_value: "Real-time equity"
      - pnl_today: "Today's P&L"
      - open_positions: "Current positions summary"
      - active_strategies: "Strategy status overview"
    
    notifications:
      - trade_executed: "Every trade notification"
      - alert_triggered: "Risk alerts, opportunities"
      - daily_summary: "Morning/evening P&L summary"
      - kill_switch_activated: "URGENT notification"
    
    quick_actions:
      - kill_switch: "One-tap emergency stop"
      - pause_all: "Pause all trading"
      - close_position: "Close specific position"
    
    monitoring:
      - strategy_performance: "Per-strategy metrics"
      - risk_utilization: "Current risk usage"
      - system_health: "API status, connectivity"
  
  notification_configuration:
    priority_levels:
      critical:
        sound: "Loud, distinct alarm"
        vibration: "Long pattern"
        persist: "Until acknowledged"
        examples: ["Kill switch", "Daily loss limit", "System down"]
      
      high:
        sound: "Attention sound"
        vibration: "Medium pattern"
        examples: ["Large trade executed", "Strategy paused"]
      
      medium:
        sound: "Subtle notification"
        vibration: "Short"
        examples: ["Trade executed", "Strategy started"]
      
      low:
        sound: "None"
        vibration: "None"
        examples: ["Daily summary", "Performance update"]
    
    do_not_disturb:
      schedule: "Configurable quiet hours"
      override_for_critical: true
  
  offline_capability:
    view_only: "Can view last-synced data offline"
    queue_commands: "Commands queued until online"
  
  security:
    biometric_auth: "Face ID / fingerprint required"
    session_timeout: "Auto-logout after 5 minutes inactive"
    critical_action_confirm: "Require PIN for kill switch"
```

## 12.3 Maturity Success Criteria

| Criterion | Target |
|-----------|--------|
| ML strategy contributing | At least 20% of returns from ML |
| Alpha discovery working | New alpha found via discovery |
| Multi-asset live | At least 2 asset classes |
| Mobile app functional | Used for daily monitoring |
| Autonomous mode option | Available and tested |

---

# PART 13: 5-10 YEAR EVERYTHING SYSTEM VISION

## 13.1 The Vision

**In 5-10 years, this system should be:**

A comprehensive, intelligent trading infrastructure that:

1. **Operates autonomously** within defined risk bounds
2. **Discovers alpha** through systematic research
3. **Adapts** to changing market conditions
4. **Trades multiple asset classes** with unified risk management
5. **Generates reliable income** with controlled drawdowns
6. **Requires minimal supervision** (hours per month, not hours per week)
7. **Is fully auditable** and explainable
8. **Could support external capital** if desired (fund-capable architecture)

## 13.2 Architecture Evolution

### 13.2.1 Critical Design Decision: Modular Monolith, NOT Multi-Agent

**The legacy system was multi-agent (85+ agents). This system is NOT.**

| Aspect | Legacy (Multi-Agent) | New System (Modular Monolith) |
|--------|---------------------|-------------------------------|
| Components | 85+ independent agents | 7 modules in one application |
| Communication | Message bus (async pub/sub) | Direct function calls |
| State | Distributed, synchronized | Single database |
| Debugging | Nightmare | Normal stack traces |
| Lines of code | 150,000+ | ~10,000 target |
| Deployment | Complex orchestration | Single Railway deploy |

**Why monolith is CORRECT for this use case:**
1. **Single operator** — No need for distributed agents
2. **Simplicity** — Lesson learned from legacy complexity
3. **Debuggability** — Can trace issues end-to-end
4. **Deployment** — One app, one database, Railway
5. **Evolution** — Can extract services LATER if needed

**Architecture pattern:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    SINGLE APPLICATION                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    ORCHESTRATOR                          │    │
│  │           (Single entry point, controls flow)            │    │
│  └─────────────────────────────────────────────────────────┘    │
│          │              │              │              │          │
│    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│    │ Strategy │   │ Backtest │   │Execution │   │   Risk   │   │
│    │  Module  │──▶│  Module  │──▶│  Module  │◀─▶│Controller│   │
│    └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
│          │                             │              │          │
│    ┌──────────────────────────────────────────────────────┐    │
│    │                     DATABASE                          │    │
│    └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**When to consider multi-service (Maturity+):**
- If parts need to scale independently
- If running on multiple machines
- If supporting multiple users
- If module teams work independently

### 13.2.2 System Evolution by Phase

```
MVP (Year 0-1)
├── Single broker (Binance)
├── Single asset class (Crypto)
├── Template strategies
├── Manual approval
└── Basic monitoring

V1 (Year 1-2)
├── Multi-broker
├── Batch generation
├── Semi-auto regime
├── Cost tracking
└── Enhanced reporting

V2 (Year 2-3)
├── Auto regime detection
├── Symbol discovery
├── Correlation management
├── Research mode
└── Tax reporting

Maturity (Year 3-5)
├── ML strategies
├── Alpha discovery
├── Sentiment integration
├── Multi-asset
└── Optional autonomy

Everything (Year 5-10)
├── Full AI/ML integration
├── Real-time adaptation
├── Predictive capabilities
├── Fund-ready infrastructure
└── Minimal supervision required
```

## 13.3 Capabilities by Year

### Year 1: Foundation
- System running live on Binance
- 3-5 strategies deployed
- Basic profitability demonstrated
- Weekly check-ins working

### Year 2: Expansion
- Multiple brokers
- 10+ strategies
- Regime awareness
- Monthly profitability consistent

### Year 3: Sophistication
- Auto regime detection
- Research workflow established
- Symbol universe expanded
- Correlation-aware allocation

### Year 4: Intelligence
- First ML strategies live
- Alpha discovery producing candidates
- Sentiment integration
- Multi-asset trading

### Year 5: Autonomy
- Autonomous mode option
- Full multi-asset
- Minimal supervision
- Fund-ready infrastructure

### Years 6-10: Refinement
- Continuous improvement
- New data sources
- Advanced execution
- Potential external capital

## 13.4 Decision Points

Key decisions to make along the way:

| Year | Decision | Options |
|------|----------|---------|
| 1 | Scale up capital? | If profitable, increase allocation |
| 2 | Add forex? | Based on crypto success |
| 3 | Invest in ML? | Based on data quality and ROI |
| 4 | Full autonomy? | Based on system reliability |
| 5 | External capital? | Based on performance and desire |

## 13.5 Risk Management Evolution

```
MVP: Conservative, manual oversight
  ↓
V1: Still conservative, semi-automated
  ↓
V2: Moderate risk, auto-regime
  ↓
Maturity: Dynamic risk based on conditions
  ↓
Everything: Intelligent risk allocation
```

## 13.6 What "Everything" Actually Means

The "everything system" is not:
- Every possible feature
- Maximum complexity
- Replacement for human judgment

The "everything system" is:
- **Comprehensive capabilities** across discovery → execution → monitoring
- **Intelligent automation** where automation adds value
- **Human oversight** where judgment is needed
- **Reliable income** through systematic approach
- **Time freedom** through operational efficiency

---

# PART 14: NON-FUNCTIONAL REQUIREMENTS

## 14.1 Performance

### 14.1.1 Response Times

| Operation | Target | Maximum |
|-----------|--------|---------|
| Place order | 500ms | 2s |
| Cancel order | 500ms | 2s |
| Dashboard load | 1s | 5s |
| Backtest (1 year) | 30s | 5min |
| Kill switch activation | 100ms | 1s |
| Alert delivery | 5s | 30s |

### 14.1.2 Throughput

| Metric | MVP Target |
|--------|------------|
| Orders per second | 10 |
| Concurrent strategies | 20 |
| Data points processed per second | 1,000 |
| API requests per minute | 100 |

## 14.2 Reliability

### 14.2.1 Uptime

| Component | Target |
|-----------|--------|
| Overall system | 99.5% |
| Trading engine (market hours) | 99.9% |
| Dashboard | 99% |
| Alerting | 99.9% |

### 14.2.2 Recovery

| Scenario | Recovery Target |
|----------|-----------------|
| Application crash | Auto-restart < 60s |
| Database corruption | Restore from backup < 1 hour |
| Broker disconnect | Auto-reconnect < 5 minutes |
| Data feed failure | Fallback < 30 seconds |

## 14.3 Security

### 14.3.1 Authentication

```yaml
authentication:
  api_access:
    method: "API key + secret"
    rotation: "Monthly recommended"
  
  dashboard_access:
    method: "Password"
    requirements: "12+ characters, complexity"
  
  kill_switch:
    method: "Confirmation code"
    additional: "Rate limited"
```

### 14.3.2 Data Protection

```yaml
data_protection:
  broker_credentials:
    storage: "Environment variables"
    never: "In code or logs"
  
  database:
    encryption: "At rest (optional for MVP)"
  
  logs:
    pii: "No PII in logs"
    credentials: "Never logged"
```

## 14.4 Maintainability

### 14.4.1 Code Standards

```yaml
code_standards:
  style: "PEP 8 (Python)"
  type_hints: "Required for public functions"
  documentation: "Docstrings for all modules and functions"
  testing: "Minimum 80% coverage for core components"
```

### 14.4.2 Deployment

```yaml
deployment:
  method: "Docker container"
  hosting: "Railway (MVP) → AWS (V2+)"
  ci_cd: "GitHub Actions"
  rollback: "Previous version always available"
```

## 14.5 Observability

### 14.5.1 Logging

```yaml
logging:
  format: "JSON structured"
  levels:
    - DEBUG: "Detailed debugging"
    - INFO: "Normal operations"
    - WARNING: "Potential issues"
    - ERROR: "Errors"
    - CRITICAL: "System failures"
  
  retention: "90 days"
  searchable: "By timestamp, level, component"
```

### 14.5.2 Metrics

```yaml
metrics:
  system:
    - cpu_usage
    - memory_usage
    - disk_usage
    - api_latency
  
  trading:
    - orders_per_minute
    - fill_rate
    - slippage_average
    - pnl_daily
  
  business:
    - active_strategies
    - open_positions
    - portfolio_value
    - drawdown_current
```

---

# PART 15: SUCCESS CRITERIA & ACCEPTANCE TESTS

## 15.1 MVP Acceptance Tests

### 15.1.1 Execution Engine Tests

```yaml
test_order_placement:
  description: "System can place and track orders"
  steps:
    1. Submit market order for BTCUSDT
    2. Verify order acknowledged by broker
    3. Verify order status updated in system
    4. Verify position created after fill
  expected: "All steps complete successfully"

test_order_cancellation:
  description: "System can cancel pending orders"
  steps:
    1. Submit limit order far from current price
    2. Cancel order before fill
    3. Verify order status is CANCELLED
  expected: "Order cancelled successfully"
```

### 15.1.2 Risk Controller Tests

```yaml
test_position_size_limit:
  description: "Position size limits are enforced"
  steps:
    1. Configure max position size at 5%
    2. Attempt to place order for 10% of account
    3. Verify order rejected
    4. Verify rejection logged
  expected: "Order rejected with reason 'exceeds position size limit'"

test_daily_loss_limit:
  description: "Daily loss limit triggers halt"
  steps:
    1. Configure daily loss limit at 3%
    2. Simulate losses reaching 3%
    3. Verify trading halted
    4. Verify alert sent
  expected: "Trading halted, alert sent"

test_kill_switch:
  description: "Kill switch stops all trading"
  steps:
    1. Activate kill switch via API
    2. Verify pending orders cancelled
    3. Verify new orders rejected
    4. Verify alert sent
    5. Verify response time < 1 second
  expected: "All trading stopped within 1 second"
```

### 15.1.3 Strategy System Tests

```yaml
test_strategy_generation:
  description: "System can generate strategies from templates"
  steps:
    1. Select MA Crossover template
    2. Configure parameters
    3. Create strategy
    4. Verify strategy created in DRAFT status
  expected: "Strategy created successfully"

test_backtest_determinism:
  description: "Backtests produce identical results"
  steps:
    1. Run backtest on strategy
    2. Record results
    3. Run identical backtest
    4. Compare results
  expected: "Results identical to 6 decimal places"

test_strategy_lifecycle:
  description: "Strategy moves through lifecycle correctly"
  steps:
    1. Create strategy (DRAFT)
    2. Run backtest (→ BACKTEST → PAPER_TRADING)
    3. Complete paper trading (→ PENDING_APPROVAL)
    4. Approve strategy (→ LIVE)
  expected: "Strategy progresses through all stages"
```

### 15.1.4 P&L Tracking Tests

```yaml
test_pnl_calculation:
  description: "P&L calculated correctly"
  steps:
    1. Execute buy at $100, quantity 1
    2. Price moves to $105
    3. Verify unrealized P&L = $5
    4. Execute sell at $105
    5. Verify realized P&L = $5 (minus commissions)
  expected: "P&L accurate to 2 decimal places"
```

### 15.1.5 Dashboard Tests

```yaml
test_dashboard_load:
  description: "Dashboard loads with all components"
  steps:
    1. Access dashboard URL
    2. Verify portfolio summary displays
    3. Verify positions display
    4. Verify strategies display
    5. Verify regime indicators display
  expected: "All components render within 5 seconds"
```

### 15.1.6 Alerting Tests

```yaml
test_alert_delivery:
  description: "Critical alerts delivered promptly"
  steps:
    1. Trigger kill switch
    2. Verify Telegram message received
    3. Verify delivery time < 30 seconds
  expected: "Alert delivered within 30 seconds"
```

## 15.2 Integration Test Suite

```yaml
full_trading_cycle:
  description: "Complete cycle from signal to P&L"
  steps:
    1. Create and validate strategy
    2. Deploy to paper account
    3. Generate trading signal
    4. Verify risk checks pass
    5. Submit order
    6. Verify fill
    7. Update position
    8. Update P&L
    9. Log all steps
  expected: "Complete cycle successful with full audit trail"
```

## 15.3 Performance Benchmarks

| Test | Target | How to Measure |
|------|--------|----------------|
| Order latency | < 500ms | Time from submission to acknowledgment |
| Backtest speed | < 60s for 2 years | Time for full backtest |
| Dashboard load | < 2s | Time to first meaningful paint |
| Memory usage | < 1GB | Peak memory during operation |
| CPU usage | < 50% | Average during trading hours |

---

# PART 16: OPERATIONS & INFRASTRUCTURE

## 16.1 Testing Strategy

### 16.1.1 Testing Levels

```yaml
testing_levels:
  unit_tests:
    description: "Test individual functions and classes"
    coverage_target: 80%
    tools: ["pytest"]
    focus_areas:
      - indicator_calculations: "EMA, RSI, MACD return correct values"
      - risk_calculations: "Position sizing, drawdown calculations"
      - order_generation: "Signal → Order conversion"
    
    examples:
      - test_ema_calculation: "EMA(14) returns expected value for known data"
      - test_position_size: "10% max position correctly calculated"
      - test_risk_limit: "Reject order exceeding daily loss limit"
  
  integration_tests:
    description: "Test component interactions"
    coverage_target: 60%
    tools: ["pytest", "testcontainers"]
    focus_areas:
      - database_operations: "CRUD operations work correctly"
      - broker_adapter: "Order submission and status tracking"
      - strategy_execution: "Signal → Order → Position flow"
    
    examples:
      - test_strategy_to_order: "Strategy signal creates correct order"
      - test_order_to_position: "Filled order updates position correctly"
      - test_pnl_calculation: "P&L calculated correctly after trade"
  
  system_tests:
    description: "End-to-end workflow testing"
    environment: "Staging with testnet"
    focus_areas:
      - full_trading_loop: "Strategy generates signal → order placed → filled → position updated → P&L calculated"
      - kill_switch: "Kill switch closes all positions within 1 second"
      - alerting: "Alerts delivered to Telegram within 30 seconds"
    
    examples:
      - test_paper_trade_loop: "Complete paper trade from signal to P&L"
      - test_kill_switch_speed: "Kill switch < 1 second response"
      - test_daily_loss_limit: "Trading stops when limit hit"
  
  regression_tests:
    description: "Ensure changes don't break existing functionality"
    when: "Before every deployment"
    scope: "All critical paths"
```

### 16.1.2 Test Data Management

```yaml
test_data:
  market_data:
    source: "Historical data from Binance"
    storage: "Local SQLite for tests"
    time_ranges:
      - trending_up: "Jan 2024 BTC bull run"
      - trending_down: "May 2022 LUNA crash period"
      - ranging: "Q3 2023 consolidation"
      - volatile: "March 2020 COVID crash"
    
  fixtures:
    strategy_fixtures: "Pre-configured strategy objects"
    order_fixtures: "Sample orders in various states"
    position_fixtures: "Sample positions for P&L testing"
  
  mocking:
    binance_api: "Mock responses for all endpoints"
    telegram_api: "Mock notification delivery"
    database: "In-memory SQLite for unit tests"
```

### 16.1.3 Continuous Integration

```yaml
ci_pipeline:
  trigger:
    - push_to_main: true
    - pull_request: true
  
  stages:
    lint:
      tools: ["ruff", "black"]
      fail_on_error: true
    
    type_check:
      tools: ["mypy"]
      strictness: "strict"
    
    unit_tests:
      command: "pytest tests/unit -v"
      coverage_threshold: 80%
    
    integration_tests:
      command: "pytest tests/integration -v"
      requires: "Test database"
    
    security_scan:
      tools: ["bandit", "safety"]
      fail_on_critical: true
  
  artifacts:
    - test_report: "HTML coverage report"
    - lint_report: "Linting results"
```

## 16.2 Deployment & DevOps

### 16.2.1 Deployment Architecture

```yaml
deployment:
  platform: "Railway"
  
  services:
    trading_app:
      type: "Long-running service"
      instances: 1  # Single instance for MVP
      memory: "1GB"
      cpu: "1 vCPU"
      restart_policy: "Always"
    
    database:
      type: "PostgreSQL"
      provider: "Railway PostgreSQL"
      backup: "Daily automatic"
    
    web_dashboard:
      type: "Static + API"
      framework: "Next.js"
      deployment: "Same Railway project"
  
  environments:
    development:
      purpose: "Local development"
      database: "SQLite"
      broker: "Binance Testnet"
    
    staging:
      purpose: "Pre-production testing"
      database: "PostgreSQL (Railway)"
      broker: "Binance Testnet"
      url: "staging.paravant.app"
    
    production:
      purpose: "Live trading"
      database: "PostgreSQL (Railway)"
      broker: "Binance Production"
      url: "app.paravant.app"
```

### 16.2.2 Deployment Process

```yaml
deployment_process:
  pre_deployment:
    - run_all_tests: "CI pipeline must pass"
    - review_changes: "Code review approved"
    - staging_verification: "Tested on staging"
    - backup_database: "Snapshot before deploy"
  
  deployment_steps:
    1: "Merge to main branch"
    2: "Railway auto-deploys from main"
    3: "Run database migrations"
    4: "Health check passes"
    5: "Smoke tests pass"
    6: "Monitor for 30 minutes"
  
  rollback:
    trigger: "Health check fails OR critical error in logs"
    process:
      - automatic_rollback: "Railway reverts to previous"
      - restore_database: "If migration caused issues"
      - notify_operator: "Alert via Telegram"
    time_to_rollback: "< 5 minutes"
  
  zero_downtime:
    method: "Rolling deployment"
    note: "MVP uses single instance, brief downtime acceptable"
```

### 16.2.3 Environment Variables & Secrets

```yaml
environment_management:
  secrets:
    storage: "Railway environment variables (encrypted)"
    
    required_secrets:
      - BINANCE_API_KEY: "Trading API key"
      - BINANCE_API_SECRET: "Trading API secret"
      - DATABASE_URL: "PostgreSQL connection string"
      - TELEGRAM_BOT_TOKEN: "Alerting bot token"
      - TELEGRAM_CHAT_ID: "Your chat ID for alerts"
    
    optional_secrets:
      - SENTRY_DSN: "Error tracking (optional)"
  
  configuration:
    storage: "Environment variables or config file"
    
    examples:
      - LOG_LEVEL: "INFO"
      - MAX_POSITION_SIZE_PCT: "10"
      - DAILY_LOSS_LIMIT_PCT: "5"
  
  security:
    never_commit_secrets: true
    rotate_keys_quarterly: true
    use_env_files_locally: ".env.local (gitignored)"
```

## 16.3 Documentation

### 16.3.1 Documentation Types

```yaml
documentation:
  code_documentation:
    tool: "docstrings (Google style)"
    coverage: "All public functions and classes"
    enforcement: "CI checks for missing docstrings"
    
    example: |
      def calculate_position_size(
          account_equity: float,
          risk_per_trade: float,
          stop_loss_distance: float
      ) -> float:
          '''Calculate position size based on fixed risk.
          
          Args:
              account_equity: Total account value in quote currency
              risk_per_trade: Maximum loss per trade (e.g., 0.02 for 2%)
              stop_loss_distance: Distance to stop loss as decimal
          
          Returns:
              Position size in base currency
          
          Example:
              >>> calculate_position_size(10000, 0.02, 0.05)
              4000.0  # Risk $200, stop 5% away = $4000 position
          '''
  
  api_documentation:
    tool: "OpenAPI/Swagger (auto-generated)"
    location: "/api/docs"
    includes:
      - all_endpoints: true
      - request_examples: true
      - response_schemas: true
  
  user_documentation:
    format: "Markdown in /docs folder"
    structure:
      - getting_started: "Quick start guide"
      - configuration: "All settings explained"
      - strategies: "Template documentation"
      - troubleshooting: "Common issues and solutions"
  
  runbook:
    purpose: "Operational procedures"
    includes:
      - deployment_steps: "How to deploy"
      - incident_response: "What to do when things break"
      - maintenance_tasks: "Regular maintenance procedures"
      - recovery_procedures: "How to recover from failures"
```

### 16.3.2 README Structure

```yaml
readme_requirements:
  sections:
    - project_overview: "What is PARAVANT"
    - quick_start: "Get running in 5 minutes"
    - prerequisites: "What you need installed"
    - installation: "Step-by-step setup"
    - configuration: "Environment variables, settings"
    - usage: "How to use the system"
    - development: "Contributing, running tests"
    - deployment: "How to deploy"
    - architecture: "System overview diagram"
    - license: "License information"
```

## 16.4 Monitoring & Observability

### 16.4.1 Logging

```yaml
logging:
  framework: "Python logging with structlog"
  format: "JSON for production, human-readable for dev"
  
  log_levels:
    DEBUG: "Detailed debugging (dev only)"
    INFO: "Normal operations"
    WARNING: "Potential issues"
    ERROR: "Failures requiring attention"
    CRITICAL: "System-wide emergencies"
  
  what_to_log:
    always:
      - trade_execution: "Every trade with full details"
      - risk_decisions: "Position sizing, limit checks"
      - errors: "All exceptions with stack traces"
      - system_events: "Startup, shutdown, config changes"
    
    debug_only:
      - indicator_values: "Every indicator calculation"
      - api_requests: "All API calls"
  
  retention:
    hot: "30 days in Railway logs"
    cold: "1 year exported to file storage"
    critical: "Forever (kill switch events, large losses)"
  
  log_aggregation:
    mvp: "Railway built-in logs"
    future: "Consider Grafana Loki or similar"
```

### 16.4.2 Metrics

```yaml
metrics:
  system_metrics:
    - cpu_usage: "CPU utilization percentage"
    - memory_usage: "RAM utilization"
    - disk_usage: "Storage utilization"
    - api_latency: "Exchange API response time"
  
  trading_metrics:
    - orders_per_hour: "Trading activity"
    - fill_rate: "Order execution success"
    - slippage_avg: "Average slippage"
    - position_count: "Open positions"
  
  business_metrics:
    - portfolio_value: "Total equity"
    - daily_pnl: "Today's profit/loss"
    - drawdown_current: "Current drawdown"
    - strategy_performance: "Per-strategy returns"
  
  dashboard:
    tool: "Grafana (future) or custom dashboard"
    refresh_rate: "5 seconds for critical, 1 minute for others"
```

### 16.4.3 Alerting

```yaml
alerting:
  channels:
    primary: "Telegram"
    secondary: "Email (if Telegram fails)"
    tertiary: "SMS via Twilio (critical only)"
  
  telegram_setup:
    bot_creation:
      step_1: "Message @BotFather on Telegram"
      step_2: "Send /newbot"
      step_3: "Name your bot (e.g., PARAVANT Trading)"
      step_4: "Copy the API token"
      step_5: "Message your bot to get chat_id"
      step_6: "Add token and chat_id to environment"
    
    notification_settings:
      phone_settings:
        - enable_notifications: "Settings → Notifications → PARAVANT bot"
        - set_custom_sound: "Use distinct sound for trading alerts"
        - enable_vibration: "For silent mode"
        - priority_notifications: "Mark as priority if available"
      
      mute_groups:
        tip: "Mute all other Telegram groups except trading bot"
  
  alert_types:
    critical:
      examples: ["Kill switch activated", "Daily loss limit hit", "System down"]
      delivery: "All channels, repeat until acknowledged"
      sound: "Loud, distinct"
    
    high:
      examples: ["Large trade executed", "Strategy paused", "Exchange error"]
      delivery: "Telegram immediately"
      sound: "Attention"
    
    medium:
      examples: ["Trade executed", "Position closed"]
      delivery: "Telegram"
      sound: "Subtle"
    
    low:
      examples: ["Daily summary", "Performance update"]
      delivery: "Telegram (batched)"
      sound: "None"
```

## 16.5 Security Hardening

### 16.5.1 API Key Security

```yaml
api_key_security:
  storage:
    never: "Never commit to git"
    always: "Use environment variables"
    encryption: "Railway encrypts at rest"
  
  binance_api_key_setup:
    restrictions:
      ip_whitelist: "Enable and add Railway IP"
      permissions:
        - enable_spot_trading: true
        - enable_futures: false  # MVP live execution is spot-only. Per
          # DEC-2026-05-28-001 the research/backtest layer evaluates
          # futures, but the API key must remain spot-only until step 4
          # of the staged plan (proven short edge + live futures adapter).
        - enable_withdrawals: false  # NEVER enable
        - enable_internal_transfer: false
    
    key_rotation:
      frequency: "Every 90 days"
      process: "Generate new key, update env, verify, delete old"
  
  access_control:
    principle: "Least privilege"
    application_permissions: "Only trading, no withdrawals"
```

### 16.5.2 Application Security

```yaml
application_security:
  authentication:
    dashboard: "Password protected (bcrypt hashed)"
    api: "API key required for all endpoints"
    sessions: "JWT with 24h expiry"
  
  input_validation:
    all_inputs: "Validate and sanitize"
    sql_injection: "Use parameterized queries (SQLAlchemy)"
    xss: "Escape all outputs"
  
  dependencies:
    scanning: "safety check on every CI run"
    updates: "Dependabot for automatic updates"
    pinning: "Pin exact versions in requirements.txt"
  
  secrets_in_logs:
    never_log:
      - api_keys
      - passwords
      - tokens
    masking: "Automatic masking in structured logs"
```

### 16.5.3 Network Security

```yaml
network_security:
  https: "Enforce HTTPS everywhere"
  cors: "Restrict to known origins"
  rate_limiting: "Implement on dashboard API"
  
  binance_connection:
    use_https: true
    verify_ssl: true
    ip_whitelist: "Use if supported by Railway"
```

## 16.6 Disaster Recovery

### 16.6.1 Backup Strategy

```yaml
backup:
  database:
    frequency: "Daily automatic (Railway)"
    retention: "30 days"
    type: "Full backup"
    
    manual_backup:
      when: "Before major changes"
      command: "pg_dump -Fc database > backup.dump"
  
  configuration:
    what: "All config files, environment template"
    where: "Git repository (secrets excluded)"
    when: "On every change"
  
  strategy_definitions:
    what: "All strategy parameters and settings"
    where: "Database + exported JSON"
    when: "Daily export"
  
  trade_history:
    what: "All trades, orders, positions"
    where: "Database + monthly CSV export"
    retention: "7 years"
```

### 16.6.2 Recovery Procedures

```yaml
recovery_procedures:
  database_corruption:
    detection: "Health check fails, queries error"
    response:
      1: "Stop trading immediately"
      2: "Restore from latest backup"
      3: "Reconcile with exchange state"
      4: "Resume trading"
    rto: "4 hours"  # Recovery Time Objective
    rpo: "24 hours"  # Recovery Point Objective (max data loss)
  
  application_failure:
    detection: "Health check fails, no heartbeat"
    response:
      1: "Railway auto-restarts"
      2: "If fails 3x, alert operator"
      3: "Manual intervention required"
  
  exchange_api_down:
    detection: "Multiple API errors"
    response:
      1: "Switch to read-only mode"
      2: "No new trades"
      3: "Monitor existing positions"
      4: "Alert operator"
      5: "Resume when API recovers"
  
  complete_disaster:
    scenario: "Everything lost"
    recovery:
      1: "Provision new Railway instance"
      2: "Restore database from backup"
      3: "Set environment variables"
      4: "Deploy from git"
      5: "Verify configuration"
      6: "Reconcile with exchange"
      7: "Resume trading"
    time_estimate: "4-8 hours"
```

### 16.6.3 Business Continuity

```yaml
business_continuity:
  single_points_of_failure:
    railway:
      risk: "Railway outage"
      mitigation: "Documented procedure to redeploy elsewhere"
      alternative: "Heroku, Render, or VPS as backup"
    
    binance:
      risk: "Binance down or account locked"
      mitigation: "V1 adds second broker (Deriv)"
      manual: "Can manually trade on exchange"
    
    operator:
      risk: "You're unavailable"
      mitigation: "System can run autonomously with safety limits"
      dead_mans_switch: "Auto-close if no heartbeat"
  
  emergency_contacts:
    telegram: "Primary notification"
    email: "Secondary notification"
    trusted_person: "Optional: Someone who can access kill switch"
```

## 16.7 Scaling Considerations

### 16.7.1 MVP Scale

```yaml
mvp_scale:
  expected_load:
    strategies: "3-10 active"
    positions: "5-20 open"
    trades_per_day: "10-50"
    data_points_per_day: "~100,000"
  
  resources:
    memory: "512MB - 1GB"
    cpu: "1 vCPU"
    database: "1GB storage"
  
  limitations:
    single_instance: "No horizontal scaling"
    single_broker: "Binance only"
    symbols: "10-15 symbols"
```

### 16.7.2 When to Scale

```yaml
scaling_triggers:
  performance:
    - response_time_increasing: "> 1s for orders"
    - memory_pressure: "> 80% usage"
    - cpu_saturation: "> 70% sustained"
    - database_slow: "> 100ms query times"
  
  business:
    - strategy_count: "> 50 strategies"
    - trade_volume: "> 500 trades/day"
    - capital: "> $100,000 (more reliability needed)"
```

### 16.7.3 Scaling Strategies

```yaml
scaling_strategies:
  vertical_scaling:
    description: "Bigger instance"
    when: "First option, simplest"
    how: "Upgrade Railway plan"
    limit: "Eventually hits ceiling"
  
  database_scaling:
    read_replicas: "For read-heavy workloads"
    connection_pooling: "PgBouncer if connections limited"
    partitioning: "Archive old data"
  
  horizontal_scaling:
    when: "Vertical limits reached or redundancy needed"
    approach: "Extract to microservices"
    candidates:
      - market_data_service: "Separate data fetching"
      - backtest_service: "Separate compute-heavy backtests"
      - notification_service: "Separate alerting"
    
    complexity_warning: |
      Horizontal scaling adds significant complexity.
      Only consider after:
      - $100K+ capital at risk
      - Need for 99.99% uptime
      - Multiple concurrent users
  
  recommendation: |
    For personal trading (even with significant capital):
    Vertical scaling on Railway should handle 100+ strategies.
    Only consider horizontal if requirements significantly expand.
```

---

# PART 17: GLOSSARY & DEFINITIONS

## 16.1 Trading Terms

| Term | Definition |
|------|------------|
| **Alpha** | Returns above benchmark; the value a strategy adds |
| **Backtest** | Simulation of strategy on historical data |
| **Drawdown** | Decline from peak portfolio value |
| **Expectancy** | Average expected profit per trade |
| **Fill** | Execution of an order |
| **Leverage** | Using borrowed funds to amplify positions |
| **P&L** | Profit and Loss |
| **Paper Trading** | Simulated trading without real money |
| **Position** | An open trade in a particular asset |
| **Sharpe Ratio** | Risk-adjusted return metric |
| **Slippage** | Difference between expected and actual execution price |
| **Win Rate** | Percentage of profitable trades |

## 16.2 System Terms

| Term | Definition |
|------|------------|
| **Account Profile** | Risk configuration preset (conservative/balanced/aggressive) |
| **Circuit Breaker** | Automatic protection that halts trading on certain conditions |
| **Escalation** | Raising an issue to human attention |
| **Kill Switch** | Emergency stop for all trading |
| **Lifecycle** | Stages a strategy goes through (draft → live → retired) |
| **Regime** | Market condition classification (trending/ranging/etc.) |
| **Signal** | Indication that a trade should be made |
| **Template** | Blueprint for generating strategies |

## 16.3 Status Values

### Strategy Status
| Status | Description |
|--------|-------------|
| DRAFT | Just created, not yet backtested |
| BACKTEST | Currently being backtested |
| PAPER_TRADING | Running in paper mode |
| PENDING_APPROVAL | Ready for human review |
| LIVE | Running with real money |
| PAUSED | Temporarily stopped |
| RETIRED | Permanently removed |

### Order Status
| Status | Description |
|--------|-------------|
| PENDING | Created, not yet submitted |
| SUBMITTED | Sent to broker |
| PARTIAL | Partially filled |
| FILLED | Completely filled |
| CANCELLED | Cancelled before fill |
| REJECTED | Rejected by broker |
| EXPIRED | Expired without fill |

---

# PART 18: COMPLETE FEATURE SUMMARY BY PHASE

This section provides a comprehensive overview of ALL features planned for each development phase.

## 18.1 MVP Features (Complete List)

### Core Capabilities (7)
| # | Capability | Description |
|---|------------|-------------|
| 1 | Execution Engine | Place and track orders on Binance |
| 2 | Risk Controller | Position limits, loss limits, kill switch |
| 3 | Strategy System | Template-based generation, backtest, paper trading |
| 4 | Account Management | 2-3 account profiles |
| 5 | P&L Tracking | Daily/weekly/monthly at portfolio and strategy level |
| 6 | Monitoring Dashboard | System health, positions, P&L, regime indicators |
| 7 | Alerting System | Telegram alerts for critical events |

### Additional Features (12)
| # | Feature | Description |
|---|---------|-------------|
| A | Portfolio Correlation Limits | Prevent over-concentration in same direction |
| B | Manual Regime Tagging | Operator tags market regime |
| C | Dead Man's Switch | Auto-close if system unresponsive |
| D | Strategy Similarity Check | Reject strategies too similar to existing |
| E | Entry Timing Coordination | Stagger entries, prevent simultaneous signals |
| F | Pre-Trade Slippage Estimation | Estimate slippage before order |
| G | Capital Allocation Rules | Systematic rules for position sizing |
| H | Data Quality Validation | Validate market data before using |
| I | Order State Reconciliation | Sync local state with exchange |
| J | Rate Limit Management | Proactive API rate limit handling |
| K | Position Staleness Monitor | Alert on positions held too long |
| L | Execution Quality Tracking | Track slippage, fill rates |

### Safety Features (5)
| # | Feature | Description |
|---|---------|-------------|
| A | Volatility Filter | Reduce trading in extreme volatility |
| B | Weekend/Holiday Awareness | Adjust for low-liquidity periods |
| C | Emergency Contact Escalation | Multi-channel alerts (Telegram, Email, SMS) |
| D | Configuration Backup & Restore | Automated backup of all config |
| E | Startup Checklist | Verify all systems before trading |

### Reliability Features (3)
| # | Feature | Description |
|---|---------|-------------|
| A | Graceful Degradation | Continue operating when components fail |
| B | Comprehensive Logging | Log everything for debugging and audit |
| C | Health Check Endpoints | Verify system health programmatically |

**MVP Total: 7 capabilities + 12 features + 5 safety + 3 reliability = 27 items**

---

## 18.2 V1 Features (Complete List)

| # | Feature | Description |
|---|---------|-------------|
| 1 | Multi-Broker Support | Add Deriv, Alpaca |
| 2 | Batch Strategy Generation | Generate 50+ variants with parameter sweeps |
| 3 | Extended Template Library | 7-10 additional templates |
| 4 | Enhanced Performance Tracking | Backtest vs live comparison |
| 5 | Semi-Automated Regime Detection | System suggests, operator confirms |
| 6 | Funding Rate Tracking | Track perpetual funding rates |
| 7 | Cost Tracking | Comprehensive cost accounting |
| 8 | Order Book Depth Analysis | Analyze liquidity before large orders |
| 9 | Strategy Ensemble Signals | Multiple strategies vote on direction |
| 10 | Strategy Performance Attribution | Understand why strategies made/lost money |
| 11 | Drawdown Recovery Tracking | Track time to recover from drawdowns |
| 12 | Multi-Timeframe Confirmation | Confirm signals across timeframes |
| 13 | API Key Rotation | Secure key management with rotation |
| 14 | Trade Journal Automation | Automated logging of trade context |
| 15 | Risk Budget System | Allocate risk, not just capital |
| 16 | Benchmark Comparison Dashboard | Compare to buy-and-hold |
| 17 | Time-of-Day Analysis | Analyze performance by session |
| 18 | Slippage Model Calibration | Learn and improve slippage predictions |

**V1 Total: 18 new features**

---

## 18.3 V2 Features (Complete List)

| # | Feature | Description |
|---|---------|-------------|
| 1 | Automated Regime Detection | System detects regime without confirmation |
| 2 | Symbol Discovery and Research | System suggests new symbols |
| 3 | Strategy Correlation Management | Manage portfolio diversification |
| 4 | ML-Enhanced Templates | ML suggests parameters, templates remain core |
| 5 | Tax and Audit Reports | Generate reports for tax filing |
| 6 | Research Mode | Exploratory analysis environment |
| 7 | Portfolio Rebalancing | Automated rebalancing suggestions |
| 8 | Execution Algorithms (TWAP/VWAP) | Sophisticated order execution |
| 9 | Market Impact Model | Predict and minimize market impact |
| 10 | Alternative Data Integration | Funding rates, OI, liquidations |
| 11 | Dynamic Position Sizing | Adjust sizes based on conditions |
| 12 | Strategy Decay Early Warning | Detect decay before failure |
| 13 | Monte Carlo Validation | Randomized scenario testing |
| 14 | Walk-Forward Optimization | Continuous re-optimization |
| 15 | Liquidity Regime Detection | Detect and adapt to liquidity changes |
| 16 | Cross-Asset Correlation Tracking | Monitor correlations across all assets |
| 17 | Synthetic Data Generation | Generate fake data for testing |

**V2 Total: 17 new features**

---

## 18.4 Maturity Features (Complete List)

| # | Feature | Description |
|---|---------|-------------|
| 1 | ML Strategy Generation | Full ML for strategy discovery |
| 2 | Alpha Discovery Engine | Systematic search for alpha sources |
| 3 | Sentiment Analysis | Incorporate market sentiment |
| 4 | Advanced Execution | Market making, optimal execution |
| 5 | Mobile Application | Native mobile app for monitoring |
| 6 | Multi-Asset Expansion | Forex, equities, commodities |
| 7 | Fully Autonomous Mode | Optional full autonomy with safeguards |
| 8 | Meta-Learning | System learns how to create strategies |
| 9 | Continuous Online Learning | Strategies adapt in real-time |
| 10 | Adversarial Robustness Testing | Test against adversarial conditions |
| 11 | Causal Inference | Find causation, not just correlation |
| 12 | Self-Healing Systems | Auto-detect and fix issues |
| 13 | Transfer Learning | Apply lessons across assets |
| 14 | Explainable AI (XAI) | Understand why ML makes decisions |
| 15 | Strategy Crowding Detection | Detect when strategy is crowded |
| 16 | Market Microstructure Analysis | Order flow and market structure edge |
| 17 | Predictive Risk Management | Predict and preemptively manage risk |
| 18 | Fund-Ready Infrastructure | Capability to manage external capital |

**Maturity Total: 18 new features**

---

## 18.5 Grand Total Feature Count

| Phase | Features | Cumulative |
|-------|----------|------------|
| MVP | 27 | 27 |
| V1 | 18 | 45 |
| V2 | 17 | 62 |
| Maturity | 18 | 80 |

**Total system features when fully mature: 80**

---

## 18.6 Feature Priority Matrix

### Must-Have for Live Trading (MVP)
These are non-negotiable for going live with real money:

| Feature | Why Non-Negotiable |
|---------|-------------------|
| Kill Switch | Can't trade without emergency stop |
| Risk Controller | Prevents catastrophic loss |
| Order Reconciliation | Must know true position state |
| Dead Man's Switch | Protection if system crashes |
| Execution Quality Tracking | Must know if execution is costing money |
| Alerting | Must know when things go wrong |
| Position Limits | Prevents over-exposure |
| Data Quality Validation | Garbage in = garbage out |

### Nice-to-Have for MVP (Could Defer)
If time is constrained, these could move to V1:

| Feature | Why Could Defer |
|---------|-----------------|
| Time-of-Day Analysis | Can analyze manually at first |
| Benchmark Comparison | Nice but not critical |
| Position Staleness | Manual monitoring ok initially |
| Volatility Filter | Manual regime tagging covers some of this |

### V1 Priority Order
Build these in order of value:

| Priority | Feature | Value |
|----------|---------|-------|
| 1 | Batch Generation | Dramatically speeds up strategy development |
| 2 | Performance Attribution | Understand what's working |
| 3 | Cost Tracking | Know true net returns |
| 4 | Multi-Broker | Diversifies exchange risk |
| 5 | Slippage Calibration | Improves backtest accuracy |

---

## 18.7 Risk Mitigation Features

Features specifically designed to prevent loss:

| Phase | Feature | Risk Mitigated |
|-------|---------|----------------|
| MVP | Kill Switch | System malfunction |
| MVP | Dead Man's Switch | System crash with open positions |
| MVP | Drawdown Circuit Breaker | Runaway losses |
| MVP | Portfolio Correlation Limits | Hidden concentration risk |
| MVP | Volatility Filter | Trading in dangerous conditions |
| V1 | Order Book Depth | Market impact on large orders |
| V1 | Ensemble Signals | False signals from single strategy |
| V2 | Decay Early Warning | Strategy degradation |
| V2 | Liquidity Regime | Trading in thin markets |
| V2 | Monte Carlo | Overfitting in backtest |
| Maturity | Predictive Risk | Anticipate problems before they happen |
| Maturity | Adversarial Testing | Strategy crowding, market adaptation |

---

## 18.8 Profitability Enhancement Features

Features specifically designed to improve returns:

| Phase | Feature | Profit Impact |
|-------|---------|---------------|
| MVP | Slippage Estimation | Avoid trades where slippage > profit |
| MVP | Entry Timing | Better fills through staggered entries |
| MVP | Manual Regime | Don't run wrong strategies in wrong regime |
| V1 | Multi-Timeframe | Higher quality signals |
| V1 | Ensemble Voting | Reduced false signals |
| V1 | Time-of-Day | Trade during profitable hours |
| V2 | ML-Enhanced Templates | Better parameter selection |
| V2 | Dynamic Position Sizing | Bigger positions when confident |
| V2 | Walk-Forward Optimization | Adapt to changing markets |
| Maturity | Alpha Discovery | Find new profit sources |
| Maturity | Meta-Learning | Improve strategy creation itself |

---

## 18.9 Final Pre-Build Checklist

Before starting development, confirm:

- [ ] All 27 MVP items are understood and scoped
- [ ] Development timeline (12 weeks) is realistic
- [ ] Binance API access is set up (testnet first)
- [ ] Railway account is ready for deployment
- [ ] Telegram bot is created for alerts
- [ ] Database schema is approved
- [ ] Templates are defined (3 for MVP)
- [ ] Risk parameters are decided (position limits, loss limits)
- [ ] Success criteria are agreed (100 paper trades, etc.)
- [ ] Architecture is understood (modular monolith, NOT multi-agent)

---

# APPENDIX A: API REFERENCE

## A.1 Health Endpoints

### GET /api/health
Returns overall system health.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "broker": "healthy",
    "data_feed": "healthy"
  },
  "timestamp": "2026-02-03T14:30:00Z"
}
```

## A.2 Account Endpoints

### GET /api/accounts
List all accounts.

### GET /api/accounts/{id}
Get specific account details.

### POST /api/accounts/{id}/pause
Pause account trading.

### POST /api/accounts/{id}/resume
Resume account trading.

## A.3 Strategy Endpoints

### GET /api/strategies
List all strategies.

### GET /api/strategies/{id}
Get strategy details with full metadata.

### POST /api/strategies
Create new strategy from template.

### POST /api/strategies/{id}/backtest
Run backtest on strategy.

### POST /api/strategies/{id}/approve
Approve strategy for live trading.

### POST /api/strategies/{id}/pause
Pause strategy.

### POST /api/strategies/{id}/retire
Retire strategy.

## A.4 Order Endpoints

### GET /api/orders
List orders with filters.

### POST /api/orders
Place new order (manual).

### DELETE /api/orders/{id}
Cancel order.

## A.5 Position Endpoints

### GET /api/positions
List all open positions.

### POST /api/positions/{id}/close
Close specific position.

## A.6 Emergency Endpoints

### POST /api/kill-switch/activate
Activate kill switch.

### POST /api/kill-switch/deactivate
Deactivate kill switch (requires confirmation).

### GET /api/kill-switch/status
Get kill switch status.

## A.7 Dashboard Endpoints

### GET /api/dashboard
Get dashboard summary data.

### GET /api/dashboard/pnl
Get P&L data.

### GET /api/dashboard/performance
Get performance metrics.

---

# APPENDIX B: CONFIGURATION REFERENCE

## B.1 Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///data/trading.db

# Binance
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
BINANCE_TESTNET=true

# Alerting
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# System
LOG_LEVEL=INFO
TRADING_MODE=paper
```

## B.2 Settings File (settings.yaml)

```yaml
# General
system:
  name: "Personal Trading System"
  version: "1.0.0"
  mode: "paper"  # paper | live

# Risk defaults
risk:
  global:
    max_portfolio_drawdown_pct: 15.0
    daily_loss_limit_pct: 5.0

# Strategy defaults
strategies:
  default_paper_period_days: 28
  min_backtest_sharpe: 1.0
  min_backtest_trades: 100

# Monitoring
monitoring:
  health_check_interval_seconds: 30
  position_sync_interval_seconds: 300

# Alerting
alerting:
  enabled: true
  channels:
    - telegram
  quiet_hours: null
```

## B.3 Risk Profiles (risk_profiles.yaml)

```yaml
profiles:
  conservative:
    max_position_size_pct: 2.0
    max_concentration_pct: 15.0
    max_open_positions: 5
    daily_loss_limit_pct: 2.0
    weekly_loss_limit_pct: 5.0
    max_drawdown_pct: 8.0
    max_leverage: 1.0
  
  balanced:
    max_position_size_pct: 3.0
    max_concentration_pct: 20.0
    max_open_positions: 8
    daily_loss_limit_pct: 3.0
    weekly_loss_limit_pct: 7.0
    max_drawdown_pct: 12.0
    max_leverage: 1.5
  
  aggressive:
    max_position_size_pct: 5.0
    max_concentration_pct: 30.0
    max_open_positions: 10
    daily_loss_limit_pct: 5.0
    weekly_loss_limit_pct: 10.0
    max_drawdown_pct: 15.0
    max_leverage: 2.0
```

---

# APPENDIX C: STRATEGY TEMPLATES CATALOG

## C.1 Template: Dual Moving Average Crossover

**ID:** tpl_dual_ma_crossover  
**Type:** Trend Following  
**Complexity:** Low

### Description
Classic trend-following strategy using two moving averages. Enters when fast MA crosses slow MA, exits on opposite signal or stop/target.

### Parameters
| Parameter | Type | Default | Range |
|-----------|------|---------|-------|
| fast_ma_period | int | 10 | 5-50 |
| slow_ma_period | int | 50 | 20-200 |
| ma_type | enum | EMA | SMA/EMA/WMA |
| take_profit_pct | float | 3.0 | 1.0-10.0 |
| stop_loss_pct | float | 1.5 | 0.5-5.0 |

### Best For
- Trending markets
- Higher timeframes (4H, 1D)
- Major pairs with good liquidity

### Avoid When
- Ranging/choppy markets
- Low timeframes
- Low liquidity

---

## C.2 Template: RSI Mean Reversion

**ID:** tpl_rsi_mean_reversion  
**Type:** Mean Reversion  
**Complexity:** Low

### Description
Counter-trend strategy using RSI overbought/oversold levels. Enters against the trend when RSI reaches extremes, exits when RSI normalizes.

### Parameters
| Parameter | Type | Default | Range |
|-----------|------|---------|-------|
| rsi_period | int | 14 | 7-28 |
| oversold_level | int | 30 | 15-40 |
| overbought_level | int | 70 | 60-85 |
| exit_level | int | 50 | 40-60 |
| take_profit_pct | float | 2.0 | 0.5-5.0 |
| stop_loss_pct | float | 1.0 | 0.5-3.0 |

### Best For
- Ranging markets
- Mean-reverting instruments
- Lower timeframes (1H, 4H)

### Avoid When
- Strong trending markets
- Breakout conditions

---

## C.3 Template: Momentum Breakout

**ID:** tpl_momentum_breakout  
**Type:** Breakout  
**Complexity:** Medium

### Description
Enters on price breaking out of recent range with volume confirmation. Uses trailing stop for exits.

### Parameters
| Parameter | Type | Default | Range |
|-----------|------|---------|-------|
| lookback_period | int | 20 | 10-50 |
| volume_multiplier | float | 1.5 | 1.0-3.0 |
| trailing_stop_pct | float | 2.0 | 1.0-5.0 |
| max_hold_bars | int | 20 | 5-50 |

### Best For
- Volatile markets
- After consolidation periods
- News-driven moves

### Avoid When
- Low volatility conditions
- Choppy price action

---

*End of Product Requirements Document*

**Document Status:** LOCKED FOR DEVELOPMENT  
**Next Review:** After MVP completion  
**Change Control:** All changes require operator approval and version increment
