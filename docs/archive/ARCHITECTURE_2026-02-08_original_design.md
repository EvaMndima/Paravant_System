> **ARCHIVED — This is the original design document, written 2026-02-08 before
> implementation began. It was never updated.**
>
> It is kept because the gap between it and what was actually built is itself
> informative. It describes a multi-broker adapter pattern that was never built
> (see Part 10.2, which uses a Deriv config example from an earlier conception
> of the project), a `pnl` module whose logic ended up in the execution layer,
> and a single orchestrated main loop that was built but never wired.
>
> **For the system as it actually exists, see
> [docs/ARCHITECTURE.md](../ARCHITECTURE.md)**, which includes a section on
> where this design and the implementation diverged, and why.

---

# PERSONAL AUTONOMOUS TRADING SYSTEM
# ARCHITECTURE DOCUMENT

**Document Version:** 1.0  
**Created:** 2026-02-03  
**Last Updated:** 2026-02-03  
**Status:** LOCKED FOR DEVELOPMENT  
**Companion Document:** TRADING_SYSTEM_PRD.md

---

# TABLE OF CONTENTS

1. [PART 1: ARCHITECTURE OVERVIEW](#part-1-architecture-overview)
2. [PART 2: SYSTEM COMPONENTS](#part-2-system-components)
3. [PART 3: DATA FLOW](#part-3-data-flow)
4. [PART 4: TECHNOLOGY STACK](#part-4-technology-stack)
5. [PART 5: DATABASE DESIGN](#part-5-database-design)
6. [PART 6: API DESIGN](#part-6-api-design)
7. [PART 7: DIRECTORY STRUCTURE](#part-7-directory-structure)
8. [PART 8: DEPLOYMENT ARCHITECTURE](#part-8-deployment-architecture)
9. [PART 9: SECURITY ARCHITECTURE](#part-9-security-architecture)
10. [PART 10: EVOLUTION PATH](#part-10-evolution-path)
11. [PART 11: INTEGRATION PATTERNS](#part-11-integration-patterns)
12. [PART 12: ERROR HANDLING](#part-12-error-handling)
13. [PART 13: TESTING ARCHITECTURE](#part-13-testing-architecture)

---

# PART 1: ARCHITECTURE OVERVIEW

## 1.1 Architecture Philosophy

This system is built on these architectural principles:

1. **Simplicity First** — Start simple, add complexity only when justified
2. **Separation of Concerns** — Each component has one clear responsibility
3. **Fail-Safe by Default** — System defaults to safe state on errors
4. **Observable** — Every component exposes health and state
5. **Evolvable** — Architecture supports growth to "everything system"

## 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE LAYER                            │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │    Web Dashboard    │  │   REST API Client   │  │  Telegram Alerts    │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 API LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         FastAPI Application                          │    │
│  │  /health  /accounts  /strategies  /orders  /positions  /dashboard   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CORE ENGINE LAYER                                │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Orchestrator │  │   Strategy   │  │  Execution   │  │     Risk     │    │
│  │              │  │   Engine     │  │   Engine     │  │  Controller  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Account    │  │     P&L      │  │  Monitoring  │  │   Alerting   │    │
│  │   Manager    │  │   Tracker    │  │   Service    │  │   Service    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    Market    │  │   Data       │  │    Symbol    │  │    Cache     │    │
│  │  Data Fetch  │  │   Store      │  │   Manager    │  │   Manager    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INTEGRATION LAYER                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Broker Adapter Layer                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │   Binance    │  │    Deriv     │  │   Alpaca     │               │    │
│  │  │   Adapter    │  │   Adapter    │  │   Adapter    │               │    │
│  │  │   (MVP)      │  │   (V1)       │  │   (V1)       │               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Binance    │  │   Telegram   │  │  Deriv (V1)  │  │ Alpaca (V1)  │    │
│  │     API      │  │     API      │  │     API      │  │     API      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1.3 Component Responsibility Matrix

| Component | Responsibility | Depends On | Depended On By |
|-----------|---------------|------------|----------------|
| Orchestrator | Coordinate all components | All engines | API |
| Strategy Engine | Generate signals | Market Data | Execution Engine |
| Execution Engine | Execute orders | Broker Adapter, Risk | Orchestrator |
| Risk Controller | Enforce limits | Data Store | Execution Engine |
| Account Manager | Manage accounts | Data Store | All engines |
| P&L Tracker | Calculate P&L | Data Store, Positions | Dashboard |
| Monitoring | Track health | All components | Alerting |
| Alerting | Send notifications | Monitoring | External (Telegram) |
| Market Data | Fetch prices | Broker Adapter | Strategy Engine |
| Data Store | Persist data | SQLite | All components |
| Broker Adapter | Exchange interface | External API | Execution Engine |

## 1.4 Key Design Decisions

### Decision 1: Monolithic Architecture for MVP

**Decision:** Single application, not microservices.

**Rationale:**
- Single operator, no scaling requirements
- Simpler deployment and debugging
- Lower operational overhead
- Can evolve to services later if needed

### Decision 2: SQLite for MVP Database

**Decision:** Use SQLite, not PostgreSQL.

**Rationale:**
- Zero configuration
- Sufficient for single-user workload
- Easy backup (single file)
- Can migrate to PostgreSQL in V2 if needed

### Decision 3: Synchronous Core with Async I/O

**Decision:** Async for I/O operations, synchronous for business logic.

**Rationale:**
- Trading logic is easier to debug synchronously
- Async only where it adds value (broker communication, data fetching)
- Reduces complexity of error handling

### Decision 4: In-Memory Message Bus for MVP

**Decision:** Simple in-memory pub/sub, not Kafka/Redis.

**Rationale:**
- No distributed requirements for single instance
- Simpler debugging
- Can add Kafka in V2 for multiple instances

---

# PART 2: SYSTEM COMPONENTS

## 2.1 Core Engine Layer

### 2.1.1 Orchestrator

**Purpose:** Central coordinator for all trading activities.

**Responsibilities:**
- Initialize all components on startup
- Run the main trading loop
- Coordinate signal → risk check → execution flow
- Handle graceful shutdown

**Key Interface:**

```python
class Orchestrator:
    """Central coordinator for the trading system."""
    
    async def initialize(self) -> bool:
        """Initialize all components. Returns True if successful."""
        pass
    
    async def start(self) -> None:
        """Start the main trading loop."""
        pass
    
    async def stop(self) -> None:
        """Gracefully stop all trading."""
        pass
    
    async def run_cycle(self) -> None:
        """Run one iteration of the trading loop."""
        pass
    
    def get_status(self) -> SystemStatus:
        """Get current system status."""
        pass
```

**State Machine:**

```
[INITIALIZING] → [READY] → [RUNNING] → [STOPPING] → [STOPPED]
                    ↑           │
                    └───────────┘ (on error recovery)
```

### 2.1.2 Strategy Engine

**Purpose:** Generate trading signals from market data.

**Responsibilities:**
- Manage strategy lifecycle
- Run backtests
- Generate signals from active strategies
- Track strategy performance

**Key Interface:**

```python
class StrategyEngine:
    """Engine for strategy management and signal generation."""
    
    def create_strategy(self, template_id: str, params: dict) -> Strategy:
        """Create a new strategy from template."""
        pass
    
    def run_backtest(self, strategy_id: str, config: BacktestConfig) -> BacktestResult:
        """Run backtest on a strategy."""
        pass
    
    async def generate_signals(self, strategies: List[Strategy], 
                                market_data: MarketData) -> List[Signal]:
        """Generate trading signals from active strategies."""
        pass
    
    def get_strategy(self, strategy_id: str) -> Strategy:
        """Get strategy with full metadata."""
        pass
    
    def update_strategy_status(self, strategy_id: str, status: str) -> None:
        """Update strategy lifecycle status."""
        pass
```

### 2.1.3 Execution Engine

**Purpose:** Execute orders and track positions.

**Responsibilities:**
- Submit orders to broker
- Track order status
- Maintain position state
- Calculate slippage and execution quality

**Key Interface:**

```python
class ExecutionEngine:
    """Engine for order execution and position management."""
    
    async def submit_order(self, order: Order) -> OrderResult:
        """Submit order after risk checks pass."""
        pass
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        pass
    
    async def cancel_all_orders(self) -> int:
        """Cancel all pending orders. Returns count cancelled."""
        pass
    
    def get_positions(self, account_id: str) -> List[Position]:
        """Get all open positions for account."""
        pass
    
    async def close_position(self, position_id: str) -> OrderResult:
        """Close a specific position."""
        pass
```

### 2.1.4 Risk Controller

**Purpose:** Enforce all risk limits.

**Responsibilities:**
- Check trades against limits before execution
- Track account and strategy risk metrics
- Manage circuit breakers
- Control kill switch

**Key Interface:**

```python
class RiskController:
    """Controller for all risk management."""
    
    def check_trade(self, trade: Trade) -> RiskCheckResult:
        """Check trade against all risk limits."""
        pass
    
    def check_account_limits(self, account_id: str) -> AccountRiskStatus:
        """Check current account against limits."""
        pass
    
    def activate_kill_switch(self, reason: str) -> None:
        """Activate global kill switch."""
        pass
    
    def deactivate_kill_switch(self, confirm: bool) -> bool:
        """Deactivate kill switch with confirmation."""
        pass
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        pass
```

### 2.1.5 Account Manager

**Purpose:** Manage trading accounts and their configurations.

**Key Interface:**

```python
class AccountManager:
    """Manager for trading accounts."""
    
    def create_account(self, config: AccountConfig) -> Account:
        """Create a new trading account."""
        pass
    
    def get_account(self, account_id: str) -> Account:
        """Get account with current state."""
        pass
    
    def assign_strategy(self, account_id: str, strategy_id: str, 
                        allocation_pct: float) -> None:
        """Assign strategy to account."""
        pass
    
    def pause_account(self, account_id: str, reason: str) -> None:
        """Pause all trading on account."""
        pass
    
    async def sync_account_state(self, account_id: str) -> None:
        """Sync account state with broker."""
        pass
```

### 2.1.6 P&L Tracker

**Purpose:** Calculate and track all profit and loss.

**Key Interface:**

```python
class PnLTracker:
    """Tracker for profit and loss calculations."""
    
    def calculate_realized_pnl(self, trades: List[Trade]) -> Decimal:
        """Calculate realized P&L from trades."""
        pass
    
    def calculate_unrealized_pnl(self, positions: List[Position], 
                                  prices: Dict[str, Decimal]) -> Decimal:
        """Calculate unrealized P&L from positions."""
        pass
    
    def get_daily_pnl(self, account_id: str, date: date) -> DailyPnL:
        """Get P&L for specific day."""
        pass
    
    def get_strategy_pnl(self, strategy_id: str) -> StrategyPnL:
        """Get P&L for specific strategy."""
        pass
```

### 2.1.7 Monitoring Service

**Purpose:** Monitor system health and performance.

**Key Interface:**

```python
class MonitoringService:
    """Service for system monitoring."""
    
    async def run_health_checks(self) -> HealthCheckResult:
        """Run all health checks."""
        pass
    
    def record_metric(self, name: str, value: float, tags: dict = None) -> None:
        """Record a metric value."""
        pass
    
    def check_for_anomalies(self) -> List[Anomaly]:
        """Check for system anomalies."""
        pass
    
    def get_system_status(self) -> SystemStatus:
        """Get comprehensive system status."""
        pass
```

### 2.1.8 Alerting Service

**Purpose:** Send notifications to operator.

**Key Interface:**

```python
class AlertingService:
    """Service for sending alerts."""
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert. Returns True if delivered."""
        pass
    
    async def send_critical_alert(self, message: str, context: dict) -> bool:
        """Send critical alert with immediate delivery."""
        pass
    
    async def send_daily_summary(self, summary: DailySummary) -> bool:
        """Send daily summary report."""
        pass
```

## 2.2 Data Layer

### 2.2.1 Market Data Fetcher

**Key Interface:**

```python
class MarketDataFetcher:
    """Fetcher for market data."""
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str, 
                           limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV candles."""
        pass
    
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """Fetch current price/ticker."""
        pass
    
    def validate_data(self, data: pd.DataFrame) -> DataQualityResult:
        """Validate data quality."""
        pass
```

### 2.2.2 Data Store

**Key Interface:**

```python
class DataStore:
    """Store for all persistent data."""
    
    # Account operations
    def save_account(self, account: Account) -> None: pass
    def get_account(self, account_id: str) -> Optional[Account]: pass
    
    # Strategy operations
    def save_strategy(self, strategy: Strategy) -> None: pass
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]: pass
    def get_strategies_by_status(self, status: str) -> List[Strategy]: pass
    
    # Order operations
    def save_order(self, order: Order) -> None: pass
    def get_orders(self, filters: OrderFilters) -> List[Order]: pass
    
    # Position operations
    def save_position(self, position: Position) -> None: pass
    def get_open_positions(self, account_id: str) -> List[Position]: pass
    
    # P&L operations
    def save_pnl_record(self, record: PnLRecord) -> None: pass
    def get_pnl_history(self, account_id: str, days: int) -> List[PnLRecord]: pass
    
    # Audit operations
    def log_audit(self, action: str, entity_type: str, 
                  entity_id: str, details: dict) -> None: pass
```

## 2.3 Integration Layer

### 2.3.1 Broker Adapter (Abstract)

```python
from abc import ABC, abstractmethod

class BrokerAdapter(ABC):
    """Abstract base for all broker adapters."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to broker."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from broker."""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Balance:
        """Get account balance."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[BrokerPosition]:
        """Get open positions."""
        pass
    
    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get order status."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get current ticker."""
        pass
    
    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str, 
                        limit: int) -> List[OHLCV]:
        """Get OHLCV candles."""
        pass
```

### 2.3.2 Binance Adapter (MVP)

**Configuration:**

```yaml
binance_config:
  api_key: "${BINANCE_API_KEY}"
  secret_key: "${BINANCE_SECRET_KEY}"
  testnet: true
  
  endpoints:
    testnet:
      rest: "https://testnet.binance.vision"
      websocket: "wss://testnet.binance.vision/ws"
    production:
      rest: "https://api.binance.com"
      websocket: "wss://stream.binance.com:9443/ws"
  
  rate_limits:
    requests_per_minute: 1200
    orders_per_second: 10
  
  retry_config:
    max_retries: 3
    retry_delay_ms: 1000
    retry_on_status: [408, 429, 500, 502, 503, 504]
```

---

# PART 3: DATA FLOW

## 3.1 Trading Cycle Flow

```
1. MARKET DATA FETCH
   Binance API → Market Data Fetcher → Cache Manager

2. SIGNAL GENERATION
   Cached Data → Strategy Engine → Signal List

3. RISK CHECK
   Signal → Risk Controller → Approved/Rejected

4. EXECUTION
   Approved Order → Execution Engine → Broker Adapter

5. POSITION UPDATE
   Fill Event → Position Tracker → Data Store

6. P&L UPDATE
   Updated Position → P&L Tracker → Dashboard Update
```

## 3.2 Strategy Lifecycle Flow

```
[DRAFT] → [BACKTEST] → [PAPER_TRADING] → [PENDING_APPROVAL] → [LIVE]
               ↓              ↓                                   ↓
           [FAILED]       [FAILED]                            [PAUSED]
                                                                  ↓
                                                             [RETIRED]
```

## 3.3 Risk Check Flow

```
Trade Request Received
         │
         ▼
┌────────────────────┐
│ Kill Switch Active?│──── YES ──▶ REJECT
└────────────────────┘
         │ NO
         ▼
┌────────────────────┐
│ Position Size OK?  │──── NO ───▶ REJECT
└────────────────────┘
         │ YES
         ▼
┌────────────────────┐
│ Daily Loss Limit?  │──── NO ───▶ REJECT
└────────────────────┘
         │ YES
         ▼
┌────────────────────┐
│ Drawdown Limit?    │──── NO ───▶ REJECT
└────────────────────┘
         │ YES
         ▼
      APPROVED
```

---

# PART 4: TECHNOLOGY STACK

## 4.1 MVP Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Language | Python 3.11+ | Mature ecosystem, quant libraries |
| Web Framework | FastAPI | Modern, fast, async support |
| Database | SQLite | Zero config, sufficient for MVP |
| ORM | SQLAlchemy 2.0 | Mature, async support |
| Data Processing | Pandas, NumPy | Industry standard |
| Backtesting | VectorBT | Fast vectorized backtesting |
| Broker SDK | CCXT, python-binance | Multi-exchange support |
| HTTP Client | HTTPX | Modern async HTTP |
| Logging | structlog | Structured JSON logging |
| Testing | pytest, pytest-asyncio | Standard testing |
| Container | Docker | Consistent deployment |
| Hosting | Railway | Simple PaaS for MVP |

## 4.2 Key Library Versions

```
# Core
python>=3.11
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0

# Database
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
alembic>=1.13.0

# Data
pandas>=2.1.0
numpy>=1.26.0
vectorbt>=0.25.0

# Broker
ccxt>=4.1.0
python-binance>=1.0.19

# HTTP/Async
httpx>=0.25.0
aiohttp>=3.9.0

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0.1
structlog>=23.2.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
```

## 4.3 V1+ Technology Additions

| Version | Addition | Purpose |
|---------|----------|---------|
| V1 | Redis | Caching, rate limiting |
| V1 | PostgreSQL | Multi-broker data scale |
| V2 | Celery | Background task processing |
| V2 | Prometheus + Grafana | Advanced monitoring |
| Maturity | Kafka | Event streaming |
| Maturity | TimescaleDB | Time-series optimization |

---

# PART 5: DATABASE DESIGN

## 5.1 Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   accounts   │       │  strategies  │       │   orders     │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │       │ id (PK)      │
│ name         │◄──────│ account_id   │◄──────│ account_id   │
│ broker       │   1:N │ template_id  │   1:N │ strategy_id  │
│ profile      │       │ parameters   │       │ symbol       │
│ status       │       │ status       │       │ side/type    │
│ risk_config  │       │ backtest_*   │       │ quantity     │
│ created_at   │       │ paper_*      │       │ status       │
└──────────────┘       │ live_*       │       │ filled_qty   │
       │               └──────────────┘       └──────────────┘
       │                      │                      │
       ▼                      ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  positions   │       │ strategy_    │       │   trades     │
├──────────────┤       │ assignments  │       ├──────────────┤
│ id (PK)      │       ├──────────────┤       │ id (PK)      │
│ account_id   │       │ account_id   │       │ order_id     │
│ symbol       │       │ strategy_id  │       │ symbol       │
│ side         │       │ allocation   │       │ quantity     │
│ quantity     │       │ status       │       │ price        │
│ strategy_id  │       └──────────────┘       │ executed_at  │
└──────────────┘                              └──────────────┘
```

## 5.2 Core Tables

### accounts
```sql
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    broker TEXT NOT NULL,
    profile TEXT NOT NULL DEFAULT 'balanced',
    status TEXT NOT NULL DEFAULT 'active',
    risk_config JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### strategies
```sql
CREATE TABLE strategies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    template_id TEXT NOT NULL,
    parameters JSON NOT NULL,
    symbols JSON NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    backtest_results JSON,
    paper_results JSON,
    live_results JSON,
    lifecycle JSON NOT NULL DEFAULT '[]',
    recommendations JSON,
    insights JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### orders
```sql
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    external_id TEXT,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    strategy_id TEXT REFERENCES strategies(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    type TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL,
    status TEXT NOT NULL DEFAULT 'pending',
    filled_quantity REAL DEFAULT 0,
    average_fill_price REAL,
    commission REAL DEFAULT 0,
    reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### positions
```sql
CREATE TABLE positions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    average_entry_price REAL NOT NULL,
    strategy_id TEXT REFERENCES strategies(id),
    stop_loss_price REAL,
    take_profit_price REAL,
    opened_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### trades
```sql
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id),
    account_id TEXT NOT NULL REFERENCES accounts(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    commission REAL DEFAULT 0,
    executed_at TIMESTAMP NOT NULL
);
```

### pnl_records
```sql
CREATE TABLE pnl_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    date DATE NOT NULL,
    starting_equity REAL NOT NULL,
    ending_equity REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    total_pnl REAL NOT NULL,
    UNIQUE(account_id, date)
);
```

### alerts
```sql
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,
    severity TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    context JSON,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### audit_log
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details JSON,
    user TEXT NOT NULL DEFAULT 'system'
);
```

### ohlcv
```sql
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

---

# PART 6: API DESIGN

## 6.1 API Structure

```
/api/v1
├── /health                 # Health checks
├── /accounts               # Account management
├── /strategies             # Strategy management
├── /orders                 # Order management
├── /positions              # Position management
├── /trades                 # Trade history
├── /pnl                    # P&L tracking
├── /dashboard              # Dashboard data
├── /alerts                 # Alert management
├── /kill-switch            # Emergency controls
└── /templates              # Strategy templates
```

## 6.2 Key Endpoints

### Strategies
- `GET /strategies` - List all strategies
- `POST /strategies` - Create strategy from template
- `GET /strategies/{id}` - Get strategy with full metadata
- `POST /strategies/{id}/backtest` - Run backtest
- `POST /strategies/{id}/approve` - Approve for live
- `POST /strategies/{id}/pause` - Pause strategy
- `POST /strategies/{id}/retire` - Retire strategy

### Orders
- `GET /orders` - List orders with filters
- `POST /orders` - Place manual order
- `DELETE /orders/{id}` - Cancel order

### Positions
- `GET /positions` - List open positions
- `POST /positions/{id}/close` - Close position

### Dashboard
- `GET /dashboard` - Full dashboard data
- `GET /dashboard/portfolio` - Portfolio summary
- `GET /dashboard/regime` - Regime indicators

### Emergency
- `GET /kill-switch/status` - Get status
- `POST /kill-switch/activate` - Activate
- `POST /kill-switch/deactivate` - Deactivate

## 6.3 Error Response Format

```json
{
  "error": {
    "code": "RISK_LIMIT_EXCEEDED",
    "message": "Position size exceeds maximum allowed",
    "details": {
      "requested_size_pct": 8.5,
      "max_allowed_pct": 5.0
    }
  }
}
```

---

# PART 7: DIRECTORY STRUCTURE

## 7.1 MVP Directory Structure

```
trading-system/
│
├── app.py                      # Entry point
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
│
├── config/
│   ├── settings.yaml
│   ├── risk_profiles.yaml
│   └── templates/
│       ├── dual_ma_crossover.yaml
│       ├── rsi_mean_reversion.yaml
│       └── momentum_breakout.yaml
│
├── src/
│   ├── __init__.py
│   │
│   ├── api/                    # API Layer
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── accounts.py
│   │       ├── strategies.py
│   │       ├── orders.py
│   │       ├── positions.py
│   │       ├── dashboard.py
│   │       └── kill_switch.py
│   │
│   ├── core/                   # Core Engine Layer
│   │   ├── orchestrator.py
│   │   │
│   │   ├── strategy/
│   │   │   ├── engine.py
│   │   │   ├── generator.py
│   │   │   ├── backtester.py
│   │   │   └── templates.py
│   │   │
│   │   ├── execution/
│   │   │   ├── engine.py
│   │   │   ├── order_manager.py
│   │   │   └── position_tracker.py
│   │   │
│   │   ├── risk/
│   │   │   ├── controller.py
│   │   │   ├── limits.py
│   │   │   ├── circuit_breakers.py
│   │   │   └── kill_switch.py
│   │   │
│   │   ├── account/
│   │   │   └── manager.py
│   │   │
│   │   ├── pnl/
│   │   │   └── tracker.py
│   │   │
│   │   ├── monitoring/
│   │   │   └── service.py
│   │   │
│   │   └── alerting/
│   │       ├── service.py
│   │       └── telegram.py
│   │
│   ├── data/                   # Data Layer
│   │   ├── store.py
│   │   ├── models.py
│   │   ├── market_data.py
│   │   └── cache.py
│   │
│   ├── brokers/                # Integration Layer
│   │   ├── base.py
│   │   ├── binance.py
│   │   └── factory.py
│   │
│   ├── domain/                 # Domain Models
│   │   ├── account.py
│   │   ├── strategy.py
│   │   ├── order.py
│   │   ├── position.py
│   │   └── alert.py
│   │
│   └── utils/
│       ├── config.py
│       ├── logging.py
│       └── time.py
│
├── migrations/
│   └── versions/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│   ├── init_db.py
│   └── run_backtest.py
│
└── data/                       # Runtime (gitignored)
    ├── trading.db
    └── logs/
```

## 7.2 File Counts by Phase

| Phase | Estimated Files | Lines of Code |
|-------|-----------------|---------------|
| MVP | ~60 | ~8,000 |
| V1 | ~80 | ~12,000 |
| V2 | ~100 | ~18,000 |
| Maturity | ~150 | ~30,000 |

---

# PART 8: DEPLOYMENT ARCHITECTURE

## 8.1 MVP Deployment (Railway)

```
┌─────────────────────────────────────┐
│            Railway.app              │
│  ┌───────────────────────────────┐  │
│  │     Docker Container          │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │    Trading System       │  │  │
│  │  │    (FastAPI + Core)     │  │  │
│  │  └─────────────────────────┘  │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │    SQLite Database      │  │  │
│  │  │    (Persistent Volume)  │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│   Binance API   │  │  Telegram API   │
└─────────────────┘  └─────────────────┘
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/logs
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 8.2 Environment Configuration

### Development
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///data/trading.db
TRADING_MODE=paper
BINANCE_TESTNET=true
```

### Production
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///data/trading.db
TRADING_MODE=live
BINANCE_TESTNET=false
TELEGRAM_ENABLED=true
```

---

# PART 9: SECURITY ARCHITECTURE

## 9.1 Security Layers

1. **Network Security:** HTTPS only, rate limiting
2. **Application Security:** API key authentication, input validation
3. **Data Security:** Encrypted credentials, no sensitive data in logs
4. **Operational Security:** Kill switch, risk limits, anomaly detection

## 9.2 Credential Management

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    binance_api_key: str
    binance_secret_key: str
    binance_testnet: bool = True
    telegram_bot_token: str
    telegram_chat_id: str
    api_secret_key: str
    
    class Config:
        env_file = ".env"
```

## 9.3 API Security

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
```

---

# PART 10: EVOLUTION PATH

## 10.1 Architecture Evolution

### MVP → V1
| Component | MVP | V1 |
|-----------|-----|-----|
| Database | SQLite | PostgreSQL |
| Cache | In-memory | Redis |
| Brokers | Binance only | + Deriv, Alpaca |
| Monitoring | Basic | Prometheus + Grafana |

### V1 → V2
| Component | V1 | V2 |
|-----------|-----|-----|
| Background Jobs | Synchronous | Celery workers |
| Research | Manual | Guided UI |
| Regime Detection | Semi-auto | Auto with ML |

### V2 → Maturity
| Component | V2 | Maturity |
|-----------|-----|----------|
| ML | None | Strategy generation |
| Alpha Discovery | None | Systematic search |
| Execution | Simple | TWAP/VWAP |
| Mobile | None | Native apps |

## 10.2 Adding New Broker

```python
# 1. Create adapter implementing BrokerAdapter
class DerivAdapter(BrokerAdapter):
    async def connect(self) -> bool: ...
    async def place_order(self, order: OrderRequest) -> OrderResponse: ...
    # ... implement all abstract methods

# 2. Register in factory
BROKER_ADAPTERS = {
    'binance': BinanceAdapter,
    'deriv': DerivAdapter,
}

# 3. Add configuration in config/brokers/deriv.yaml

# 4. Update symbol manager for broker mappings

# 5. Test with paper trading first
```

---

# PART 11: INTEGRATION PATTERNS

## 11.1 Broker Communication

### Request/Response Pattern

```python
async def place_order_with_retry(self, order: OrderRequest) -> OrderResponse:
    for attempt in range(self.max_retries):
        try:
            response = await self._send_order(order)
            return response
        except RetryableError as e:
            if attempt == self.max_retries - 1:
                raise
            await asyncio.sleep(self.retry_delay * (attempt + 1))
    raise MaxRetriesExceeded()
```

### WebSocket Pattern (for real-time data)

```python
async def subscribe_to_ticker(self, symbol: str, callback: Callable):
    async with websockets.connect(self.ws_url) as ws:
        await ws.send(json.dumps({
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@ticker"],
            "id": 1
        }))
        
        async for message in ws:
            data = json.loads(message)
            await callback(data)
```

## 11.2 Event Handling

### Internal Event Bus

```python
class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, event_type: str, handler: Callable):
        self._handlers[event_type].append(handler)
    
    async def publish(self, event_type: str, data: Any):
        for handler in self._handlers[event_type]:
            await handler(data)

# Usage
event_bus = EventBus()
event_bus.subscribe("order.filled", handle_order_filled)
event_bus.subscribe("position.opened", handle_position_opened)
await event_bus.publish("order.filled", order_data)
```

---

# PART 12: ERROR HANDLING

## 12.1 Error Hierarchy

```python
class TradingSystemError(Exception):
    """Base exception for all trading system errors."""
    pass

class BrokerError(TradingSystemError):
    """Errors from broker communication."""
    pass

class RiskLimitError(TradingSystemError):
    """Risk limit violations."""
    pass

class ValidationError(TradingSystemError):
    """Input validation errors."""
    pass

class ConfigurationError(TradingSystemError):
    """Configuration errors."""
    pass

class DataError(TradingSystemError):
    """Data quality or availability errors."""
    pass
```

## 12.2 Error Recovery Strategies

| Error Type | Strategy | Example |
|------------|----------|---------|
| Transient Network | Retry with backoff | Broker API timeout |
| Rate Limit | Wait and retry | Too many requests |
| Invalid Order | Reject and log | Bad symbol |
| Data Quality | Use fallback | Missing candles |
| Critical | Activate kill switch | Broker down |

## 12.3 Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int, reset_timeout: int):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "closed"
        self.last_failure_time = None
    
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"
    
    def record_success(self):
        self.failures = 0
        self.state = "closed"
    
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
                return True
        return False
```

---

# PART 13: TESTING ARCHITECTURE

## 13.1 Testing Pyramid

```
           ╱╲
          ╱  ╲
         ╱ E2E╲         (Few, slow, expensive)
        ╱──────╲
       ╱        ╲
      ╱Integration╲     (Some, medium)
     ╱────────────╲
    ╱              ╲
   ╱   Unit Tests   ╲   (Many, fast, cheap)
  ╱──────────────────╲
```

## 13.2 Test Categories

### Unit Tests (80%)
- Individual functions and classes
- No external dependencies
- Fast execution (<1s per test)

```python
# tests/unit/test_risk_controller.py
def test_position_size_check_passes():
    controller = RiskController(config)
    trade = Trade(symbol="BTCUSDT", quantity=0.01, account_id="test")
    result = controller.check_position_size(trade)
    assert result.passed is True

def test_position_size_check_rejects_oversized():
    controller = RiskController(config)
    trade = Trade(symbol="BTCUSDT", quantity=100, account_id="test")
    result = controller.check_position_size(trade)
    assert result.passed is False
    assert "exceeds limit" in result.reason
```

### Integration Tests (15%)
- Component interactions
- May use test database
- Medium execution time

```python
# tests/integration/test_trading_cycle.py
async def test_full_trading_cycle():
    # Create strategy
    strategy = await strategy_engine.create_strategy(...)
    
    # Run backtest
    result = await strategy_engine.run_backtest(strategy.id, config)
    assert result.sharpe_ratio > 1.0
    
    # Generate signal
    signals = await strategy_engine.generate_signals([strategy], market_data)
    assert len(signals) > 0
    
    # Check risk
    check = risk_controller.check_trade(signals[0].to_trade())
    assert check.passed
```

### End-to-End Tests (5%)
- Full system tests
- Against test broker
- Slow execution

```python
# tests/e2e/test_paper_trading.py
async def test_paper_trade_execution():
    # Connect to testnet
    await broker.connect()
    
    # Place order
    result = await execution_engine.submit_order(test_order)
    assert result.status == "FILLED"
    
    # Verify position
    positions = await execution_engine.get_positions()
    assert len(positions) == 1
```

## 13.3 Test Fixtures

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def risk_controller():
    config = RiskConfig(
        max_position_size_pct=5.0,
        daily_loss_limit_pct=3.0,
        max_drawdown_pct=15.0
    )
    return RiskController(config)

@pytest.fixture
def sample_strategy():
    return Strategy(
        id="str_test_001",
        name="Test Strategy",
        type="trend_following",
        template_id="tpl_dual_ma_crossover",
        parameters={"fast_ma_period": 10, "slow_ma_period": 50}
    )
```

## 13.4 Mocking External Services

```python
# tests/mocks/broker_mock.py
class MockBinanceAdapter(BrokerAdapter):
    def __init__(self):
        self.orders = {}
        self.positions = []
        self.balance = 10000.0
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        order_id = f"mock_{uuid.uuid4()}"
        self.orders[order_id] = {
            "status": "FILLED",
            "filled_quantity": order.quantity,
            "average_price": 42000.0  # Mock price
        }
        return OrderResponse(
            order_id=order_id,
            status="FILLED",
            filled_quantity=order.quantity
        )
```

---

# APPENDIX A: CONFIGURATION FILES

## A.1 settings.yaml

```yaml
system:
  name: "Personal Trading System"
  version: "1.0.0"
  mode: "paper"  # paper | live

risk:
  global:
    max_portfolio_drawdown_pct: 15.0
    daily_loss_limit_pct: 5.0

strategies:
  default_paper_period_days: 28
  min_backtest_sharpe: 1.0
  min_backtest_trades: 100

monitoring:
  health_check_interval_seconds: 30
  position_sync_interval_seconds: 300

alerting:
  enabled: true
  channels: [telegram]
```

## A.2 risk_profiles.yaml

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

# APPENDIX B: DEVELOPMENT WORKFLOW

## B.1 Local Development

```bash
# 1. Clone and setup
git clone <repo>
cd trading-system
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt -r requirements-dev.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Initialize database
python scripts/init_db.py

# 4. Run tests
pytest

# 5. Start development server
uvicorn src.api.main:app --reload
```

## B.2 Git Workflow

```
main (production)
  │
  └── develop (integration)
        │
        ├── feature/strategy-engine
        ├── feature/risk-controller
        └── bugfix/order-tracking
```

## B.3 Code Review Checklist

- [ ] All tests pass
- [ ] Risk-related code has 100% test coverage
- [ ] No credentials in code
- [ ] Logging is appropriate (no sensitive data)
- [ ] Error handling is complete
- [ ] Documentation is updated

---

**Document Status:** LOCKED FOR DEVELOPMENT  
**Next Review:** After MVP completion  
**Change Control:** All changes require version increment
