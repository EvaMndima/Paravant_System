# SESSION 6B: API LAYER & FINAL TESTING IMPLEMENTATION
## 52 Hours | 14 Tasks | Interfaces & Comprehensive Validation

**Objective:** Build FastAPI application that exposes all trading system data to the frontend dashboard, implement real-time event streaming via SSE, and perform comprehensive end-to-end testing to validate the complete system for production.

**Start Conditions:** Session 6A complete (Orchestrator + Alerting working)
**Exit Conditions:**
- All API endpoints functional and returning correct data
- SSE event stream delivers real-time updates (<100ms latency)
- Dashboard receives all required data
- 24-hour stability test passes without crashes
- 100+ paper trades executed successfully
- >90% test coverage across entire system
- Grade A+ production readiness verified

**Using:** `docs/06_PHASE_6_BACKEND_INTEGRATION.md` (Sections 6.2 and 6.4)

---

## SECTION 6.2: API LAYER (28 HOURS, 9 TASKS)

### Task 6.2.1: Create FastAPI Application (2 hours)

**File:** `src/api/main.py`

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.api.routes import (
    system, dashboard, accounts, strategies, orders, positions, risk, events
)
from src.api.middleware.error_handler import ErrorHandlerMiddleware
from src.api.middleware.request_logger import RequestLoggerMiddleware
from src.utils.logging import get_logger

logger = get_logger(__name__)

def create_app(orchestrator=None) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        orchestrator: Orchestrator instance (injected for testing)
    """
    app = FastAPI(
        title="PARAVANT Trading System",
        version="1.0.0",
        description="Autonomous crypto trading system — Investor Cockpit API",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Store orchestrator for route access
    app.state.orchestrator = orchestrator

    # Middleware (order matters: last added = first executed in request)
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Vite dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes (all under /api/v1)
    app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
    app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
    app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
    app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
    app.include_router(positions.router, prefix="/api/v1/positions", tags=["positions"])
    app.include_router(risk.router, prefix="/api/v1/risk", tags=["risk"])
    app.include_router(events.router, prefix="/api/v1/events", tags=["events"])

    # Health check endpoints (3 levels per PRD Reliability C)
    @app.get("/health")
    async def health():
        """Quick health check — overall status only."""
        status = await orchestrator.get_status() if orchestrator else {}
        return {
            "overall_status": status.get("status", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @app.get("/health/detailed")
    async def health_detailed():
        """Component-by-component breakdown for monitoring tools."""
        status = await orchestrator.get_status() if orchestrator else {}
        return {
            "overall_status": status.get("status", "unknown"),
            "uptime_seconds": status.get("uptime_seconds", 0),
            "mode": status.get("mode", "unknown"),
            "components": {
                "database": {
                    "status": "healthy" if status else "unknown",
                    "latency_ms": 0
                },
                "exchange_api": {
                    "status": "healthy" if status else "unknown",
                    "latency_ms": 0
                },
                "strategy_engine": {
                    "status": "healthy" if status else "unknown",
                    "active_count": status.get("active_strategies", 0)
                },
                "alert_manager": {
                    "status": "healthy" if status else "unknown",
                    "pending_escalations": 0
                }
            },
            "metrics": {
                "memory_usage_pct": 45,
                "error_count_last_hour": status.get("metrics", {}).get("errors_encountered", 0),
                "open_positions_count": status.get("open_positions", 0),
                "last_trade_time": status.get("last_trade_at"),
                "cycles_completed": status.get("metrics", {}).get("cycles_completed", 0),
                "orders_executed": status.get("metrics", {}).get("orders_submitted", 0)
            }
        }

    @app.get("/health/strategies")
    async def health_strategies():
        """Per-strategy health for debugging individual strategy issues."""
        if not orchestrator:
            return {"strategies": []}

        strategies = await orchestrator.strategy_engine.get_all_strategies()
        result = []

        for strategy in strategies:
            result.append({
                "id": strategy.id,
                "name": strategy.name,
                "status": "healthy",
                "last_evaluation_time": datetime.now(timezone.utc).isoformat(),
                "consecutive_errors": 0,
                "current_drawdown_pct": 0,
                "signals_today": 0
            })

        return {"strategies": result}

    logger.info("FastAPI application created",
               docs_url="/api/docs",
               redoc_url="/api/redoc")

    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Acceptance Criteria:**
- [ ] App starts on port 8000
- [ ] All route groups registered under `/api/v1/`
- [ ] CORS configured for frontend dev server
- [ ] Error handler returns consistent JSON format
- [ ] Request logging captures method, path, duration, status
- [ ] `/health` returns overall_status
- [ ] `/health/detailed` returns component breakdown
- [ ] `/health/strategies` returns per-strategy status
- [ ] OpenAPI docs accessible at `/api/docs`
- [ ] Integration test: all health endpoints

---

### Task 6.2.2: Create System Control Endpoints (2 hours)

**File:** `src/api/routes/system.py`

**Endpoints:**
```
GET  /api/v1/system/status           → Overall system status
POST /api/v1/system/start            → Start trading
POST /api/v1/system/stop             → Stop trading
GET  /api/v1/system/regime           → Get market regime
PUT  /api/v1/system/regime           → Set market regime
GET  /api/v1/system/regime/history   → Get regime history
```

**Implementation Pattern:**

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

router = APIRouter(prefix="/system", tags=["system"])

class SystemStatusResponse(BaseModel):
    status: str  # running | stopped | starting | stopping | failed
    mode: str  # paper | live
    uptime_seconds: int
    active_strategies: int
    open_positions: int
    daily_pnl: float
    daily_pnl_pct: float
    kill_switch_active: bool
    degradation_mode: str
    circuit_breakers_triggered: List[str]
    last_trade_at: Optional[str] = None
    started_at: Optional[str] = None

class SetRegimeRequest(BaseModel):
    regime: str  # trending_up, trending_down, ranging, volatile, unknown
    operator: str
    note: str = ""

@router.get("/status")
async def get_system_status(orchestrator = Depends(get_orchestrator)):
    """Get overall system status."""
    status = await orchestrator.get_status()
    return SystemStatusResponse(**status)

@router.post("/start")
async def start_system(orchestrator = Depends(get_orchestrator)):
    """Start the trading system."""
    try:
        # Start is async, so we just trigger it
        asyncio.create_task(orchestrator.start())
        return {"status": "starting"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_system(
    reason: str = "Manual shutdown",
    close_positions: bool = False,
    orchestrator = Depends(get_orchestrator)
):
    """Stop the trading system gracefully."""
    try:
        await orchestrator.stop(reason=reason)
        return {"status": "stopped", "reason": reason}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/regime")
async def get_current_regime(orchestrator = Depends(get_orchestrator)):
    """Get current market regime and options."""
    regime = await orchestrator._get_market_regime()
    return {
        "current_regime": regime.value if hasattr(regime, 'value') else regime,
        "regime_options": [
            "trending_up", "trending_down", "ranging", "volatile", "unknown"
        ],
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "changed_by": "system",
        "note": "",
        "affected_strategies": {
            "active_in_regime": 0,
            "paused_by_regime": 0,
            "size_reduced": 0
        }
    }

@router.put("/regime")
async def set_market_regime(
    body: SetRegimeRequest,
    orchestrator = Depends(get_orchestrator)
):
    """Set current market regime."""
    try:
        await orchestrator.strategy_engine.regime_manager.set_regime(
            body.regime,
            operator=body.operator,
            note=body.note
        )
        return {
            "status": "updated",
            "new_regime": body.regime,
            "affected_strategies": {
                "active_in_regime": 0,
                "paused_by_regime": 0,
                "size_reduced": 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/regime/history")
async def get_regime_history(
    limit: int = 20,
    orchestrator = Depends(get_orchestrator)
):
    """Get recent regime changes."""
    return {
        "changes": [
            {
                "from": "unknown",
                "to": "ranging",
                "changed_at": datetime.now(timezone.utc).isoformat(),
                "changed_by": "system",
                "note": ""
            }
        ]
    }
```

**Acceptance Criteria:**
- [ ] System status endpoint returns complete state
- [ ] Start/stop controls work with proper reason tracking
- [ ] Regime GET returns current regime + options
- [ ] Regime PUT updates regime and returns affected count
- [ ] Regime history endpoint returns recent changes
- [ ] All endpoints properly documented
- [ ] Error responses consistent JSON format

---

### Task 6.2.3: Create Dashboard Data Endpoints (3 hours)

**File:** `src/api/routes/dashboard.py`

**Key endpoints:**
- `GET /api/v1/dashboard/summary` - Portfolio summary (hero metrics)
- `GET /api/v1/dashboard/equity` - Equity curve data
- `GET /api/v1/dashboard/performance` - Performance metrics
- `GET /api/v1/dashboard/recent-trades` - Recent trades with P&L
- `GET /api/v1/dashboard/positions` - Open positions with live P&L

**Implementation focuses on:**
- Aggregating data from orchestrator components
- Fast response times (<200ms)
- Caching where appropriate (10s TTL for summary, 1m for equity)
- Real-time positions (no caching)

**Acceptance Criteria:**
- [ ] Summary endpoint returns all required fields
- [ ] Equity curve supports time ranges (1W/1M/3M/6M/1Y/ALL)
- [ ] Positions include live unrealized P&L
- [ ] Recent trades sorted by time (newest first)
- [ ] Caching implemented for non-real-time data
- [ ] Response times < 200ms
- [ ] Integration test: all endpoints

---

### Task 6.2.4: Create Account Management Endpoints (1.5 hours)

**Endpoints:**
```
POST /api/v1/accounts              → Create account
GET  /api/v1/accounts              → List all accounts
GET  /api/v1/accounts/{id}         → Get account details + risk profile
PUT  /api/v1/accounts/{id}         → Update account settings
GET  /api/v1/accounts/{id}/balance → Get live balance
GET  /api/v1/accounts/{id}/pnl     → Get P&L history
```

**Acceptance Criteria:**
- [ ] All CRUD operations functional
- [ ] Balance fetched from exchange
- [ ] P&L history filterable by period
- [ ] Risk profile included
- [ ] Integration test: account APIs

---

### Task 6.2.5: Create P&L Tracking Endpoints (2 hours)

**Endpoints:**
```
GET /api/v1/pnl/daily              → Daily P&L records
GET /api/v1/pnl/monthly            → Monthly aggregated P&L
GET /api/v1/pnl/by-strategy        → P&L breakdown by strategy
GET /api/v1/pnl/by-symbol          → P&L breakdown by symbol
GET /api/v1/pnl/heatmap            → Monthly returns heatmap
```

**Acceptance Criteria:**
- [ ] Daily records filterable by date range
- [ ] Monthly aggregation computed correctly
- [ ] Strategy breakdown shows per-strategy P&L
- [ ] Symbol breakdown shows per-symbol P&L
- [ ] Heatmap formatted for chart rendering
- [ ] Integration test: P&L APIs

---

### Task 6.2.6: Create API Documentation (1.5 hours)

**Tasks:**
- Add Pydantic models with `Field(description=..., example=...)`
- Add endpoint docstrings with usage examples
- Document error responses (400, 401, 404, 422, 500)
- Verify Swagger UI at `/api/docs`
- Verify ReDoc at `/api/redoc`

**Acceptance Criteria:**
- [ ] All endpoints documented with descriptions
- [ ] Request/response examples for every endpoint
- [ ] Error responses documented
- [ ] Swagger UI accessible and functional
- [ ] ReDoc accessible

---

### Task 6.2.7: Write API Tests (3 hours)

**File:** `tests/integration/test_api.py`

**Test Coverage:**
- System status/health endpoints
- Account CRUD operations
- Strategy management
- Order submission/cancellation
- Position queries
- Risk endpoints
- Dashboard data
- Error responses

**Acceptance Criteria:**
- [ ] All endpoints tested (happy path + error)
- [ ] Error responses match documented format
- [ ] >80% coverage on API routes
- [ ] Mock database and exchange dependencies

---

### Task 6.2.8: Create SSE Event Stream Endpoint (3 hours)

**File:** `src/api/routes/events.py`

**Endpoint:**
```
GET /api/v1/events/stream → SSE stream (text/event-stream)
```

**Why SSE (not WebSocket):**
- One-directional (server → client) matches dashboard needs
- Works over standard HTTP (Railway-friendly, no upgrade negotiation)
- Browser `EventSource` API auto-reconnects
- FastAPI supports natively via `StreamingResponse`
- Replaces high-frequency polling (63 requests/min → 1 connection)

**Event Types (Tier 1):**
- `kill_switch_changed` - Push on activation/deactivation
- `system_status_changed` - Push on mode change
- `position_updated` - Push on fill, close, P&L recalc
- `alert_created` - Push immediately on alert
- `risk_status_changed` - Push on threshold crossed
- `regime_changed` - Push on operator regime change
- `heartbeat` - Send every 30s to keep connection alive

**Implementation:**

```python
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime, timezone

router = APIRouter(prefix="/events")

@router.get("/stream")
async def event_stream(request: Request, api_key: str = None):
    """
    SSE endpoint for real-time state changes.

    Replaces high-frequency polling with single persistent connection.
    Reduces ~91K HTTP requests/day to ~5K via single SSE connection.
    """
    # Validate API key
    if not api_key:  # In production, validate against stored keys
        return JSONResponse(status_code=401, content={"detail": "Missing API key"})

    async def generate():
        # Subscribe to internal EventBus
        queue = asyncio.Queue()

        async def handler(event_type: str, data: dict):
            await queue.put({
                "type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Subscribe to all event types
        event_bus.subscribe("kill_switch_changed", handler)
        event_bus.subscribe("system_status_changed", handler)
        event_bus.subscribe("position_updated", handler)
        event_bus.subscribe("alert_created", handler)
        event_bus.subscribe("risk_status_changed", handler)
        event_bus.subscribe("regime_changed", handler)

        try:
            # Send connection confirmation
            yield f"event: connected\ndata: {json.dumps({'subscriptions': 'all'})}\n\n"

            # Send heartbeat every 30s
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

                # Check if client disconnected
                if await request.is_disconnected():
                    break
        finally:
            # Unsubscribe on disconnect
            event_bus.unsubscribe_all(handler)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering
        }
    )
```

**Event Payload Examples:**

```json
// Kill switch activated
event: kill_switch_changed
data: {"active": true, "reason": "Manual", "activated_at": "2026-02-14T10:30:00Z", "transaction_id": "ks_20260214_103000"}

// New position opened
event: position_updated
data: {"action": "opened", "symbol": "BTCUSDT", "side": "long", "size": 0.01, "entry_price": 97500.00}

// Alert created
event: alert_created
data: {"id": "alert_042", "level": "warning", "title": "Daily loss warning", "message": "Daily loss at 1.8%"}

// Heartbeat
event: heartbeat
data: {"timestamp": "2026-02-14T10:31:30Z"}
```

**Acceptance Criteria:**
- [ ] SSE endpoint streams events in correct format
- [ ] Frontend `EventSource` connects and receives
- [ ] Events push within 100ms of occurrence
- [ ] Heartbeat sent every 30s
- [ ] Auto-cleanup on disconnect
- [ ] API key validated
- [ ] Works on Railway (no buffering)
- [ ] Kill switch returns `transaction_id` + `server_timestamp`
- [ ] Audit log persists all state changes

---

## SECTION 6.4: FINAL TESTING (24 HOURS, 5 TASKS)

### Task 6.4.1: Create Integration Test Suite (4 hours)

**File:** `tests/integration/test_full_system.py`

**Test Scenarios (12 complete flows):**

1. **System Startup** - Initialize → checklist passes → main loop starts
2. **Startup Failure** - Inject failure → system stops → alert sent
3. **Strategy Creation** - Create from template → similarity check → saved
4. **Backtest Flow** - Run backtest → metrics computed → results returned
5. **Paper Trading Flow** - Start → signals → fills → position tracked
6. **Order Flow** - Submit → risk checks → fill → P&L updated
7. **Risk Rejection** - Order exceeds limit → rejected → alert sent
8. **Kill Switch Flow** - Activate → trading stops → deactivate → resume
9. **Circuit Breaker Flow** - Trigger → paused → reset → resume
10. **Alert Escalation** - Send warning → wait → escalate → acknowledge
11. **Degradation Flow** - API down → read-only → recovery → resume
12. **Shutdown Flow** - Stop → orders cancelled → state saved → alert

**Acceptance Criteria:**
- [ ] All 12 flows tested end-to-end
- [ ] Uses testnet or mocked exchange
- [ ] Deterministic results
- [ ] Clear pass/fail assertions
- [ ] Independent tests (no ordering dependencies)

---

### Task 6.4.2: Create Load Test Suite (2 hours)

**Tests:**
- 100 concurrent API requests (pass if all < 500ms)
- Dashboard summary 50 req/s for 60s (p95 < 200ms)
- 1000 candles/batch processing (< 1s)
- 100 signals/minute evaluation
- 10 orders/second throughput
- Main loop single cycle (< 2s)

**Memory Leak Detection:**
```python
async def test_no_memory_leak():
    initial = get_memory_usage()
    for _ in range(1000):
        await orchestrator._main_loop_single_cycle()
    final = get_memory_usage()
    growth_pct = (final - initial) / initial * 100
    assert growth_pct < 5  # Less than 5% growth
```

**Acceptance Criteria:**
- [ ] API handles 100 concurrent requests
- [ ] No memory leaks over 1000 cycles
- [ ] Dashboard response times < 200ms
- [ ] System stable under load

---

### Task 6.4.3: Create 24-Hour Stability Test (1h setup + 24h run)

**Test Procedure:**
1. Start system in paper trading
2. Activate all 5 strategy templates
3. Monitor continuously for 24 hours
4. Hourly checks:
   - No crashes/restarts
   - Memory stable (< 5% growth)
   - All signals processed
   - Alerts sent correctly
   - Logs clean (no ERROR entries)
   - Database stable

**Stability Report:**
```
=== 24-Hour Stability Report ===
Duration: 24h 0m 12s
Restarts: 0
Peak Memory: 412MB (45% of available)
Total Cycles: 2,880
Strategy Evaluations: 14,400
Signals Generated: 47
Paper Trades Executed: 23
Errors Logged: 0
Warnings Logged: 3
Database Size Growth: 2.1MB
```

**Acceptance Criteria:**
- [ ] System runs full 24 hours without crash
- [ ] Zero restarts required
- [ ] Memory usage stable (< 5% growth)
- [ ] All evaluations completed
- [ ] No ERROR entries in logs
- [ ] Stability report generated

---

### Task 6.4.4: Create UAT Checklist (2 hours)

**File:** `tests/UAT_CHECKLIST.md`

**Manual Verification Checklist (12 items):**

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| 1 | System Start | Run start command | Startup checklist passes, alert received |
| 2 | Create Strategy | POST to strategy API | Strategy created, visible in list |
| 3 | Run Backtest | POST backtest request | Results returned with metrics |
| 4 | Paper Trading | Activate strategy | Signals generated within 1 cycle |
| 5 | View Dashboard | GET dashboard/summary | All fields populated, reasonable values |
| 6 | View Positions | GET positions | Open positions with live P&L |
| 7 | Kill Switch On | POST activate | Trading stops, alert received |
| 8 | Kill Switch Off | POST deactivate | Trading resumes, alert received |
| 9 | Set Regime | PUT regime | Regime updated, strategies adjust |
| 10 | Receive Alert | Trigger condition | Telegram message within 30s |
| 11 | System Recovery | Stop and restart | State recovered, positions intact |
| 12 | View Logs | Check log files | Clear, structured, useful entries |

**Acceptance Criteria:**
- [ ] Comprehensive checklist covering MVP features
- [ ] All items pass during verification
- [ ] Issues documented with severity

---

### Task 6.4.5: Create Deployment Guide (2 hours)

**File:** `DEPLOYMENT.md`

**Contents:**
1. Prerequisites (Railway account, API keys, environment variables)
2. Local Development (setup, config, database, start)
3. Railway Deployment (connect GitHub, configure env, deploy)
4. Post-Deployment (health checks, first strategy, first trade, alerts)
5. Monitoring & Maintenance (logs, backups, updates, rollback)
6. Troubleshooting (common issues, logs, support)

**Acceptance Criteria:**
- [ ] Step-by-step guide (no assumed knowledge)
- [ ] All prerequisites listed
- [ ] Environment variables documented
- [ ] Troubleshooting section complete
- [ ] Tested on fresh deployment

---

## CRITICAL INVARIANTS FOR SESSION 6B

1. **API Data Consistency** - All endpoints return accurate, real-time data from orchestrator
2. **SSE Event Ordering** - Events delivered in correct order, no gaps or duplicates
3. **Heartbeat Requirement** - SSE heartbeat sent every 30s to prevent proxy timeouts
4. **Response Time SLA** - Dashboard endpoints < 200ms, health checks < 100ms
5. **Test Coverage Threshold** - >90% coverage across entire system before production
6. **24-Hour Stability Mandatory** - System must run 24h without crash before MVP complete

---

**Related Files:**
- Previous: [SESSION_6A_IMPLEMENTATION_PROMPT.md](SESSION_6A_IMPLEMENTATION_PROMPT.md)
- Validation: [SESSION_6B_VERIFICATION_PROMPT.md](SESSION_6B_VERIFICATION_PROMPT.md)
- Master: [PHASE_6_IMPLEMENTATION_GUIDE.md](PHASE_6_IMPLEMENTATION_GUIDE.md)

**Total Phase 6 Effort:** 98 hours (6A: 46h + 6B: 52h) | 29 tasks
