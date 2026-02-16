# User Acceptance Testing (UAT) Checklist

## PARAVANT Trading System - Session 6B Verification

**Tester:** _______________
**Date:** _______________
**Environment:** Development / Staging / Production

---

## Prerequisites

- [ ] Virtual environment activated (`.venv\Scripts\activate`)
- [ ] Database initialized (`python scripts/init_db.py`)
- [ ] API server running (`uvicorn src.api.main:app --reload`)
- [ ] API docs accessible at `http://localhost:8000/docs`

---

## 1. System Start

- [ ] `GET /health` returns `{"status": "healthy"}` with 200
- [ ] `GET /health/detailed` returns component breakdown
- [ ] `GET /ready` returns `{"ready": true}` with 200
- [ ] `GET /` returns API info with version and uptime
- [ ] `GET /api/v1/system/status` returns system status

## 2. Account Management

- [ ] `POST /api/v1/accounts` creates a new account with valid data
- [ ] `POST /api/v1/accounts` returns 400 for invalid profile
- [ ] `GET /api/v1/accounts` lists all accounts
- [ ] `GET /api/v1/accounts/{id}` returns account detail with position/strategy counts
- [ ] `PUT /api/v1/accounts/{id}` updates account name/profile/regime
- [ ] `GET /api/v1/accounts/{id}/balance` returns balance breakdown
- [ ] `GET /api/v1/accounts/{id}/pnl` returns P&L history with summary

## 3. Strategy Management (Existing)

- [ ] `GET /api/v1/strategies` lists strategies
- [ ] Strategy creation endpoints work as expected

## 4. Backtesting (Existing)

- [ ] Backtest endpoints return results
- [ ] Backtest results include key metrics (return, drawdown, win rate)

## 5. Paper Trading (Existing)

- [ ] Paper trading endpoints functional
- [ ] Paper trades create positions correctly

## 6. Dashboard

- [ ] `GET /api/v1/dashboard/summary` returns aggregated metrics
- [ ] Summary includes portfolio value, P&L changes, position/strategy counts
- [ ] `GET /api/v1/dashboard/equity?time_range=1M` returns equity curve data
- [ ] All time ranges work: 1W, 1M, 3M, 6M, 1Y, ALL
- [ ] Invalid time range returns 400
- [ ] `GET /api/v1/dashboard/performance` returns 30-day performance metrics
- [ ] `GET /api/v1/dashboard/recent-trades` returns trade list
- [ ] `GET /api/v1/dashboard/alerts` returns filtered alerts
- [ ] `GET /api/v1/dashboard/positions` returns open positions with P&L

## 7. P&L Tracking

- [ ] `GET /api/v1/pnl/daily` returns daily P&L records
- [ ] `GET /api/v1/pnl/monthly` returns monthly aggregations
- [ ] `GET /api/v1/pnl/by-strategy` returns per-strategy breakdown
- [ ] `GET /api/v1/pnl/by-symbol` returns per-symbol breakdown
- [ ] `GET /api/v1/pnl/heatmap` returns monthly return heatmap data

## 8. Regime Management

- [ ] `GET /api/v1/system/regime` returns current regime
- [ ] `PUT /api/v1/system/regime` changes regime successfully
- [ ] Invalid regime returns 400
- [ ] Regime change appears in `GET /api/v1/system/regime/history`

## 9. Kill Switch (via System State)

- [ ] System status shows kill_switch_active field
- [ ] When kill_switch is active, risk_status changes accordingly

## 10. SSE Events

- [ ] `curl -N http://localhost:8000/api/v1/events/stream` connects successfully
- [ ] Initial "connected" event received with subscriber_id
- [ ] Heartbeat comments received every 30 seconds
- [ ] Disconnecting cleans up subscription (check logs)

## 11. System Control

- [ ] `POST /api/v1/system/start` returns appropriate response
- [ ] `POST /api/v1/system/stop` returns appropriate response
- [ ] Stopping already-stopped system returns 409

## 12. Logging and Observability

- [ ] HTTP requests are logged with method, path, status, duration
- [ ] Health check requests (/health, /ready) are NOT logged
- [ ] Structured JSON logging in non-development mode
- [ ] Error responses include timestamps

---

## Test Summary

| Category | Pass | Fail | Notes |
|----------|------|------|-------|
| System Start | | | |
| Account Mgmt | | | |
| Strategy | | | |
| Backtesting | | | |
| Paper Trading | | | |
| Dashboard | | | |
| P&L Tracking | | | |
| Regime | | | |
| Kill Switch | | | |
| SSE Events | | | |
| System Control | | | |
| Logging | | | |

**Overall Result:** PASS / FAIL

**Notes:**
