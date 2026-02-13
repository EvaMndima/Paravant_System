# Kill Switch Operator Runbook

**Version:** 1.0
**Last Updated:** 2026-02-12
**Criticality:** P0 (Emergency Response)
**Audience:** Trading Operations, SRE, On-Call Engineers

---

## Overview

The Kill Switch is an emergency safety mechanism that immediately halts all trading activity. This runbook provides step-by-step procedures for kill switch operations.

**⚠️ CRITICAL:** The kill switch is designed for emergency use only. Activating it will:
- Immediately reject ALL new orders
- Stop ALL trading strategies
- Maintain existing positions (does not close them)
- Require manual deactivation with confirmation code

---

## Quick Reference

| Action | API Endpoint | CLI Command | Time to Effect |
|--------|-------------|-------------|----------------|
| **Check Status** | `GET /api/v1/risk/kill-switch/status` | N/A | Immediate |
| **Activate** | `POST /api/v1/risk/kill-switch/activate` | N/A | < 1 second |
| **Generate Code** | `POST /api/v1/risk/kill-switch/generate-code` | N/A | Immediate |
| **Deactivate** | `POST /api/v1/risk/kill-switch/deactivate` | N/A | < 1 second |

---

## Emergency Activation Procedure

### When to Activate

Activate the kill switch IMMEDIATELY if:
- 🔴 **Market anomaly** detected (flash crash, exchange outage)
- 🔴 **Trading system malfunction** (runaway strategy, order flood)
- 🔴 **Security incident** (unauthorized access, suspicious activity)
- 🔴 **Daily loss limit approaching** (proactive halt before breach)
- 🔴 **Data feed corruption** (bad prices, stale data)

### Activation Steps

#### 1. Check Current Status

```bash
curl -X GET http://localhost:8000/api/v1/risk/kill-switch/status
```

**Expected Response (Inactive):**
```json
{
  "active": false,
  "activated_at": null,
  "reason": null,
  "duration_seconds": null,
  "trading_enabled": true
}
```

#### 2. Activate Kill Switch

```bash
curl -X POST http://localhost:8000/api/v1/risk/kill-switch/activate \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Emergency: Market anomaly detected"
  }'
```

**Expected Response:**
```json
{
  "status": "activated",
  "message": "Kill switch activated: Emergency: Market anomaly detected",
  "timestamp": "2026-02-12T10:30:45.123Z"
}
```

**⏱️ Performance:** Activation completes in < 1 second (spec requirement).

#### 3. Verify Activation

```bash
curl -X GET http://localhost:8000/api/v1/risk/kill-switch/status
```

**Expected Response (Active):**
```json
{
  "active": true,
  "activated_at": "2026-02-12T10:30:45.123Z",
  "reason": "Emergency: Market anomaly detected",
  "duration_seconds": 15.5,
  "trading_enabled": false
}
```

#### 4. Notify Team

**Immediately notify:**
- Trading desk lead
- Risk management team
- On-call engineer
- Executive stakeholders (if > $10k impact)

**Notification template:**
```
🔴 KILL SWITCH ACTIVATED
Time: 2026-02-12 10:30:45 UTC
Reason: Emergency: Market anomaly detected
Impact: All trading halted
Next Steps: Investigating root cause
ETA for resolution: TBD
```

---

## Deactivation Procedure

### When to Deactivate

Deactivate the kill switch ONLY when:
- ✅ Root cause identified and resolved
- ✅ Market conditions stabilized
- ✅ System integrity verified
- ✅ Risk team approval obtained
- ✅ Monitoring systems operational

**⚠️ DO NOT deactivate without:**
1. Understanding why it was activated
2. Confirming the issue is resolved
3. Approval from risk team lead

### Deactivation Steps

#### 1. Generate Deactivation Code

```bash
curl -X POST http://localhost:8000/api/v1/risk/kill-switch/generate-code
```

**Expected Response:**
```json
{
  "code": "a1b2c3d4",
  "message": "Use this code to deactivate the kill switch. Code is single-use and expires on next generation."
}
```

**⚠️ CRITICAL:**
- Code is **single-use** (invalidated after first attempt)
- Code is **stored in memory only** (lost on system restart)
- Each generation **invalidates previous code**

#### 2. Verify System Health

Before deactivating, verify:

```bash
# Check system status
curl -X GET http://localhost:8000/health

# Check database connectivity
# Check data feed status
# Check order execution system
# Review recent errors
```

#### 3. Deactivate with Code

```bash
curl -X POST http://localhost:8000/api/v1/risk/kill-switch/deactivate \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation_code": "a1b2c3d4"
  }'
```

**Expected Response (Success):**
```json
{
  "status": "deactivated",
  "message": "Kill switch deactivated successfully",
  "timestamp": "2026-02-12T10:45:30.456Z"
}
```

**Expected Response (Wrong Code - 403 Forbidden):**
```json
{
  "detail": "Invalid confirmation code"
}
```

#### 4. Verify Deactivation

```bash
curl -X GET http://localhost:8000/api/v1/risk/kill-switch/status
```

**Expected Response:**
```json
{
  "active": false,
  "activated_at": null,
  "reason": null,
  "duration_seconds": null,
  "trading_enabled": true
}
```

#### 5. Gradual Resume

**Do NOT resume full trading immediately:**

1. **Monitor Phase (5-10 minutes):**
   - Watch order flow
   - Monitor PnL
   - Check data feeds
   - Review system logs

2. **Limited Testing (10-20 minutes):**
   - Enable 1-2 low-risk strategies
   - Small position sizes (10% normal)
   - Close monitoring

3. **Full Resume (if stable):**
   - Enable all strategies
   - Resume normal position sizes
   - Continue monitoring

---

## Troubleshooting

### Problem: Deactivation Code Lost

**Scenario:** Kill switch activated, but deactivation code lost (system restart, operator error).

**Solution:**
```bash
# Generate new code
curl -X POST http://localhost:8000/api/v1/risk/kill-switch/generate-code

# Use new code immediately
curl -X POST http://localhost:8000/api/v1/risk/kill-switch/deactivate \
  -H "Content-Type: application/json" \
  -d '{"confirmation_code": "NEW_CODE_HERE"}'
```

### Problem: Wrong Code Entered

**Scenario:** Deactivation attempt returns 403 Forbidden.

**Solution:**
```bash
# Generate fresh code (invalidates old one)
curl -X POST http://localhost:8000/api/v1/risk/kill-switch/generate-code

# Use fresh code
curl -X POST http://localhost:8000/api/v1/risk/kill-switch/deactivate \
  -H "Content-Type: application/json" \
  -d '{"confirmation_code": "FRESH_CODE_HERE"}'
```

### Problem: Kill Switch Stuck Active After Deactivation

**Scenario:** Deactivation returns success, but status still shows active.

**Diagnosis:**
```bash
# Check database state
sqlite3 data/trading.db "SELECT kill_switch_active, kill_switch_reason FROM system_state;"

# Check system logs
tail -f logs/trading_system.log | grep "kill_switch"
```

**Solution:**
1. Verify database write permissions
2. Check for database lock issues
3. Restart application if necessary
4. Contact engineering team if persists

### Problem: API Unreachable

**Scenario:** Cannot reach kill switch API endpoints.

**Emergency Fallback:**
1. Direct database update (USE WITH EXTREME CAUTION):
   ```sql
   -- EMERGENCY ONLY: Direct activation via SQL
   sqlite3 data/trading.db <<EOF
   UPDATE system_state
   SET kill_switch_active = 1,
       kill_switch_reason = 'Emergency: API unreachable',
       kill_switch_activated_at = datetime('now');
   EOF
   ```

2. Restart application to load new state

3. Investigate API issues separately

---

## State Persistence

### How State is Stored

The kill switch state persists in the `system_state` table:

| Column | Type | Description |
|--------|------|-------------|
| `kill_switch_active` | BOOLEAN | Active flag |
| `kill_switch_reason` | TEXT | Activation reason |
| `kill_switch_activated_at` | DATETIME | Activation timestamp (UTC) |

### Restart Behavior

**On Application Restart:**
- ✅ Kill switch state is **preserved**
- ✅ Active state survives restart
- ❌ Deactivation code is **lost** (stored in memory only)

**Implications:**
- If kill switch was active before restart → stays active after restart
- Must generate new deactivation code after restart
- Cannot accidentally deactivate during restart

---

## Post-Incident Review

After each kill switch activation, conduct a post-incident review (PIR):

### PIR Template

**1. Incident Timeline**
- Activation time:
- Deactivation time:
- Total duration:

**2. Root Cause**
- What triggered activation:
- System behavior observed:
- Data anomalies detected:

**3. Impact Assessment**
- Orders rejected:
- PnL impact:
- Positions affected:

**4. Response Effectiveness**
- Was activation justified? ✅ / ❌
- Response time adequate? ✅ / ❌
- Communication effective? ✅ / ❌

**5. Action Items**
- Preventive measures:
- Monitoring improvements:
- Documentation updates:

---

## Best Practices

### ✅ DO:
- Activate immediately when in doubt (fail-safe)
- Document activation reason clearly
- Notify team within 1 minute
- Conduct post-incident review
- Test activation/deactivation quarterly

### ❌ DON'T:
- Deactivate without understanding root cause
- Share deactivation codes via insecure channels
- Resume full trading immediately after deactivation
- Use kill switch for routine maintenance (use pause mechanisms)

---

## Testing & Drills

### Quarterly Kill Switch Drill

**Objective:** Verify kill switch functionality and team readiness.

**Procedure:**
1. Schedule drill during low-volume period
2. Notify team: "DRILL - Not a real incident"
3. Execute activation procedure
4. Verify all systems halt correctly
5. Execute deactivation procedure
6. Document any issues
7. Update runbook if needed

**Success Criteria:**
- Activation < 1 second
- All new orders rejected
- Team notified within 2 minutes
- Deactivation successful
- Trading resumed normally

---

## Contact Information

| Role | Contact | Availability |
|------|---------|--------------|
| Risk Team Lead | risk-lead@company.com | 24/7 |
| On-Call Engineer | oncall@company.com | 24/7 |
| Trading Desk | trading-desk@company.com | Market hours |
| CTO | cto@company.com | Critical only |

**Emergency Hotline:** +1-XXX-XXX-XXXX

---

**Document Version History:**
- v1.0 (2026-02-12): Initial runbook for MVP release
