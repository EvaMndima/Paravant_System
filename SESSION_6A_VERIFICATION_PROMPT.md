# SESSION 6A VERIFICATION PROMPT
## Orchestrator & Alerting System Validation
## 8 Hours | 4 Validation Stages | Production Quality Assurance

**Objective:** Verify that Orchestrator and Alerting implementations are production-grade, comprehensive, and production-ready before proceeding to Session 6B API implementation.

**Duration:** 8 hours total (2h per stage)
**Effort Split:** Stage 1 (2h) + Stage 2 (2h) + Stage 3 (2h) + Stage 4 (2h)

---

## STAGE 1: CODE QUALITY VERIFICATION (2 hours)

### Checklist Items

- [ ] **Type Hints (100% Coverage)**
  - All function parameters have type hints
  - All return types specified
  - SQLAlchemy Mapped[T] syntax used
  - mypy --strict passes without errors

- [ ] **Timezone Awareness**
  - All datetime fields use `datetime.now(timezone.utc)`
  - No usage of `datetime.utcnow()` anywhere
  - All timestamps in database marked as UTC

- [ ] **Input Validation**
  - All numeric values validated for NaN/Infinity
  - Financial fields validated (balance, P&L, etc.)
  - Configuration values verified before use
  - No silent failures on invalid input

- [ ] **Structured Logging**
  - All log messages use named parameters (not f-strings)
  - Structured format for parsing/analysis
  - Appropriate log levels (DEBUG, INFO, WARNING, ERROR)
  - No sensitive data in logs

- [ ] **Error Handling**
  - All exceptions caught and logged
  - Graceful degradation on errors
  - No generic `except Exception` without context
  - Proper error propagation to caller

### Verification Commands

```bash
# Type checking
mypy src/core/orchestrator.py --strict

# Linting
ruff check src/core/orchestrator.py

# Test for regressions
pytest tests/unit/test_orchestrator.py -v --tb=short

# Code coverage
pytest tests/unit/test_orchestrator.py --cov=src/core/orchestrator --cov-report=term-missing
```

---

## STAGE 2: ORCHESTRATOR FUNCTIONALITY (2 hours)

### Task: Verify Startup Checklist

```python
# Test that startup checklist fails correctly
async def verify_startup_failure():
    # Mock a database failure
    mock_store = AsyncMock()
    mock_store.health_check.side_effect = Exception("Connection failed")

    checklist = StartupChecklist({'data_store': mock_store}, config)
    result = await checklist.run()

    assert result.success == False
    assert result.failed_check == 'database_connection'
    print("✓ Startup checklist correctly fails on database error")
```

**Verification Items:**
- [ ] Database connection check works (test with mock failure)
- [ ] Database integrity check works
- [ ] Exchange API auth check works (test with mock failure)
- [ ] Exchange API permissions check works
- [ ] Config validity check works
- [ ] Disk space check works (returns failure if < 1GB)
- [ ] Memory check works (returns failure if < 500MB)
- [ ] Position sync detects mismatches correctly
- [ ] Balance check verifies sufficient funds
- [ ] Balance check enforces 5% tolerance
- [ ] Strategy validation loads and validates all strategies
- [ ] On ANY failure: system does NOT start

### Task: Verify Main Trading Loop

```python
# Verify loop executes in correct order
async def verify_loop_order():
    mock_orchestrator = create_mock_orchestrator()

    # Run one cycle
    await mock_orchestrator._main_loop_single_cycle()

    # Verify call order
    calls = mock_orchestrator.method_calls
    assert calls[0].name == '_check_kill_switch'  # First
    assert calls[1].name == '_check_circuit_breakers'  # Second
    assert calls[2].name == '_process_strategies'  # Third
    assert calls[3].name == '_sync_positions'  # Fourth
    assert calls[4].name == '_health_check'  # Fifth

    print("✓ Main loop executes steps in correct order")
```

**Verification Items:**
- [ ] Kill switch check is FIRST step
- [ ] Circuit breaker check is SECOND step
- [ ] Degradation mode respected (read-only blocks trades)
- [ ] Strategies processed sequentially
- [ ] Entry coordinator called for new entries
- [ ] Positions and P&L updated each cycle
- [ ] Health check runs each cycle
- [ ] Metrics logged correctly
- [ ] Non-fatal errors don't crash loop
- [ ] Error count incremented
- [ ] Cycle duration measured and logged
- [ ] Loop continues on transient errors

### Task: Verify Health Check System

```python
# Verify health check thresholds
async def verify_health_checks():
    checker = HealthChecker(components, alert_manager)

    # Test memory warning threshold
    with patch('psutil.virtual_memory') as mock_mem:
        mock_mem.return_value.percent = 75  # Above 70% warning threshold
        health = await checker._check_memory()
        assert health.status == 'warning'
        print("✓ Memory warning triggered at 75%")

    # Test memory critical threshold
    with patch('psutil.virtual_memory') as mock_mem:
        mock_mem.return_value.percent = 86  # Above 85% critical threshold
        health = await checker._check_memory()
        assert health.status == 'critical'
        print("✓ Memory critical triggered at 86%")
```

**Verification Items:**
- [ ] Database latency checked (returns warning if > 1000ms)
- [ ] Exchange API latency checked (returns warning if > 2000ms)
- [ ] Market data freshness checked (critical if > 5 min stale)
- [ ] Memory warning at 70%, critical at 85%
- [ ] Error rate monitored (10/hour threshold)
- [ ] Last trade time tracked
- [ ] Disk space monitored (critical if < 1GB)
- [ ] Overall status computed correctly
- [ ] Warnings don't crash system
- [ ] Critical triggers appropriate alerts

---

## STAGE 3: ALERTING SYSTEM (2 hours)

### Task: Verify Alert Manager

```python
# Verify multi-channel delivery
async def verify_alert_channels():
    alert_manager = AlertManager(config, data_store)

    # Register mock channels
    telegram_channel = AsyncMock()
    email_channel = AsyncMock()
    alert_manager.register_channel(telegram_channel)
    alert_manager.register_channel(email_channel)

    # Send alert
    await alert_manager.send_warning(
        title="Test Alert",
        message="This is a test"
    )

    # Verify both channels received it
    telegram_channel.send.assert_called_once()
    email_channel.send.assert_called_once()
    print("✓ Alert delivered to all channels")
```

**Verification Items:**
- [ ] Alert levels (INFO/WARNING/ERROR/CRITICAL) work
- [ ] Telegram channel sends formatted messages
- [ ] Email channel sends with proper subject/body
- [ ] SMS channel sends with Twilio
- [ ] Escalation timing: Email after 15min, SMS after 30min
- [ ] Critical alerts repeat every 5min until acknowledged
- [ ] Acknowledgment stops escalation
- [ ] Rate limiting prevents spam (1/5min per title)
- [ ] Critical alerts always send (no rate limit)
- [ ] Alerts persisted to database for dashboard feed

### Task: Verify Escalation Timing

```python
# Verify escalation delays
async def verify_escalation_timing():
    manager = EscalationManager(channels, contacts)

    # Send warning
    alert_id = await manager.send_with_escalation(warning_alert)

    # Should NOT escalate yet
    await manager.check_escalations()
    email_channel.send.assert_not_called()

    # Simulate 16 minutes passing
    with patch('datetime.now') as mock_now:
        mock_now.return_value = datetime.now() + timedelta(minutes=16)
        await manager.check_escalations()

    # Now should have escalated to email
    email_channel.send.assert_called_once()
    print("✓ Escalation to email triggered after 15 minutes")
```

**Verification Items:**
- [ ] INFO: Telegram only, no escalation
- [ ] WARNING: Telegram → Email after 15 min
- [ ] ERROR: Telegram + Email → SMS after 30 min
- [ ] CRITICAL: All channels immediately, repeat 5 min
- [ ] Escalation state tracked correctly
- [ ] Acknowledgment stops all escalation
- [ ] Edge cases handled (old alerts cleaned)

---

## STAGE 4: INTEGRATION & COMPLETENESS (2 hours)

### Task: Verify API Endpoints

```bash
# Start local orchestrator
python -m pytest tests/integration/test_api_status.py -v

# Verify health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8000/health/strategies
```

**Verification Items:**
- [ ] `/health` endpoint returns overall_status
- [ ] `/health/detailed` returns component breakdown with latencies
- [ ] `/health/strategies` returns per-strategy status
- [ ] All responses contain required fields
- [ ] Response times < 100ms

### Task: Verify Persistence & Recovery

```python
# Verify state can be recovered
async def verify_state_recovery():
    # Save state
    await orchestrator._save_system_state(reason="test")

    # Verify saved
    saved_state = await data_store.load_shutdown_state()
    assert saved_state is not None
    assert saved_state['stop_reason'] == 'test'

    # Restart orchestrator
    new_orch = create_orchestrator()
    recovered = await new_orch.recover_from_state(saved_state)
    assert recovered == True
    print("✓ State recovered successfully after restart")
```

**Verification Items:**
- [ ] System state persisted on shutdown
- [ ] All relevant metrics saved (cycles, orders, etc.)
- [ ] State recoverable after restart
- [ ] No P&L gaps on recovery
- [ ] Positions correctly restored
- [ ] Orders correctly restored

### Task: Verify Test Coverage

```bash
# Run full test suite with coverage
pytest tests/unit/test_orchestrator.py \
        tests/unit/test_alerting.py \
        tests/integration/test_orchestrator_*.py \
        --cov=src/core/orchestrator \
        --cov=src/core/alerting \
        --cov-report=html \
        --cov-report=term-missing

# Check coverage percentage
# Target: >85% coverage for both modules
```

**Verification Items:**
- [ ] Unit tests >85% coverage
- [ ] Integration tests cover major flows
- [ ] Error scenarios tested
- [ ] Edge cases covered
- [ ] All public methods tested
- [ ] All private methods tested or justified

---

## DEBUGGING GUIDE

### **Issue: Startup Checklist Always Fails**

**Symptoms:**
```
FAILED test_startup
StartupError: Check failed: database_connection
```

**Solutions:**
1. Verify mock database is configured correctly
2. Check that health_check() method exists
3. Verify no actual database calls in tests
4. Check component registry has all required keys

### **Issue: Main Loop Never Exits Kill Switch Check**

**Symptoms:**
```
Loop stuck, kill switch not deactivating
```

**Solutions:**
1. Verify kill_switch.is_active() returns boolean
2. Check that kill switch can be deactivated
3. Ensure loop checks every cycle, doesn't cache value
4. Verify sleep(5) timeout is not infinite

### **Issue: Alerts Not Being Sent**

**Symptoms:**
```
Send alert called but no message received
```

**Solutions:**
1. Verify channels are registered with manager
2. Check channel implementation has `async def send()`
3. Verify rate limiter isn't suppressing alert
4. Check alert level matches channel rules
5. Verify database persistence isn't failing silently

### **Issue: Health Check Hangs**

**Symptoms:**
```
Health check takes > 30 seconds
```

**Solutions:**
1. Add timeouts to all health checks
2. Verify no blocking I/O in health checks
3. Check database.health_check() has timeout
4. Verify exchange API calls have timeout
5. Mock slow operations in tests

---

## SIGN-OFF CHECKLIST

**Code Quality:**
- [ ] All type hints present (mypy --strict passes)
- [ ] All timestamps timezone-aware (UTC)
- [ ] All input validated (no NaN/Infinity)
- [ ] All errors properly handled
- [ ] Structured logging throughout
- [ ] No secrets in logs

**Orchestrator:**
- [ ] Startup checklist prevents unsafe starts
- [ ] Main loop runs continuously
- [ ] Kill switch checked first (safety)
- [ ] Circuit breakers prevent loss cascade
- [ ] Degradation mode respected
- [ ] Entry coordinator staggers entries (30s, 3/min, 5min symbol)
- [ ] Health checks run each cycle
- [ ] Graceful shutdown without orphans
- [ ] State recovery works

**Alerting:**
- [ ] Multi-channel delivery (Telegram, Email, SMS)
- [ ] Escalation timing correct (15min, 30min)
- [ ] Critical alerts repeat 5min
- [ ] Rate limiting prevents spam
- [ ] Critical alerts never suppressed
- [ ] Acknowledgment stops escalation
- [ ] All triggers integrated
- [ ] Alerts persisted to database

**Testing:**
- [ ] >85% unit test coverage
- [ ] All integration tests passing
- [ ] No regressions introduced
- [ ] All edge cases covered
- [ ] All error scenarios tested

**Documentation:**
- [ ] All classes have docstrings
- [ ] All methods documented
- [ ] Complex logic has inline comments
- [ ] Architecture decisions documented
- [ ] Invariants documented

**Sign-Off:** _________________ Date: _________________ Time: _________

---

**Next Step:** Proceed to SESSION_6B_VERIFICATION_PROMPT.md
**Related Files:** SESSION_6A_IMPLEMENTATION_PROMPT.md | PHASE_6_IMPLEMENTATION_GUIDE.md
