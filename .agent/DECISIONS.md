# PARAVANT Trading System - Architecture & Implementation Decisions

## Purpose

This document records ALL significant architectural, design, and implementation decisions made during the development of the PARAVANT Trading System.

**Why This Matters:**
- Provides audit trail for future developers/AI assistants
- Prevents decision drift and architectural erosion
- Documents rationale for "why" (not just "what")
- Enables consistent decision-making across sessions
- Required reading before ANY code changes

---

## Format

Each decision entry follows this structure:

```
### DEC-YYYY-MM-DD-XXX: Decision Title
- **Decision:** What was decided
- **Context:** Why it matters / what problem it solves
- **Rationale:** Why this choice over alternatives
- **Alternatives Considered:** What else was evaluated
- **Status:** ACTIVE | SUPERSEDED | REVISITED
- **Date Decided:** YYYY-MM-DD
- **Implemented By:** Section/Task reference
- **Affected Files:** Which modules/files implement this
- **References:** PRD sections, architecture docs, external sources
```

---

## Phase 1 Decisions (Foundation)

### DEC-2026-02-08-001: Virtual Environment Management
- **Decision:** Use Python venv for virtual environment management (NOT conda)
- **Context:** Need isolated dependency management to prevent "works only on my computer" issues and ensure consistent development environment across all developers and CI/CD pipelines
- **Rationale:**
  - Pure Python project with no scientific computing packages (no numpy/scipy/pandas for data science)
  - venv is Python standard library (no external tool required)
  - Simpler dependency management with requirements.txt
  - Better CI/CD integration (most CI systems use pip by default)
  - Smaller footprint (conda environments are 500MB+, venv is ~50MB)
  - Cross-platform compatibility without platform-specific configurations
- **Alternatives Considered:**
  - **Conda:** Rejected due to overhead for non-scientific project, slower environment creation, larger disk usage
  - **Pipenv:** Rejected due to slower adoption, less mature tooling, compatibility issues with some CI systems
  - **Poetry:** Rejected due to additional complexity for MVP, lockfile format not as widely supported
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.1 (Project Setup), Task 1.1.3
- **Affected Files:**
  - `setup_dev.bat` (Windows setup script)
  - `setup_dev.sh` (Linux/macOS setup script)
  - `DEVELOPMENT_SETUP.md` (setup documentation)
  - `.gitignore` (excludes `.venv/`)
- **References:**
  - Python Packaging User Guide: https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/

---

### DEC-2026-02-08-002: SQLAlchemy 2.0 with Mapped[T] Syntax
- **Decision:** Use modern SQLAlchemy 2.0 with `Mapped[T]` type annotation syntax for all database models
- **Context:** Database models are the foundation of the system. Need type safety, modern best practices, and prevention of common bugs (mutable defaults, naive datetimes)
- **Rationale:**
  - **Explicit type hints** with `Mapped[T]` provide IDE autocomplete and catch type errors at development time
  - **Prevents mutable default bugs** (requires explicit lambda functions for dict/list defaults)
  - **Modern SQLAlchemy best practices** (2.0 released 2023, replaces deprecated 1.x patterns)
  - **Better error messages** when column types don't match Python types
  - **Mandatory for Python 3.11+** compatibility (SQLAlchemy 1.x deprecated)
  - **Cleaner syntax** than legacy `Column()` declarations
- **Alternatives Considered:**
  - **SQLAlchemy 1.4 with Column():** Rejected due to deprecated status, missing type safety, allows mutable defaults bug
  - **Django ORM:** Rejected due to framework lock-in, requires full Django stack
  - **Tortoise ORM:** Rejected due to smaller community, less mature, async-only design
  - **Peewee:** Rejected due to less powerful query API, smaller ecosystem
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.2 (Database Layer), Tasks 1.2.1 through 1.2.10
- **Affected Files:**
  - `src/data/models/base.py` - Base model with Mapped[T]
  - `src/data/models/account.py` - All models use Mapped[T]
  - `src/data/models/order.py`
  - `src/data/models/position.py`
  - `src/data/models/strategy.py`
  - `src/data/models/trade.py`
  - `src/data/models/pnl.py`
  - `src/data/models/system.py`
  - `src/data/models/signal.py`
  - `src/data/models/strategy_assignment.py`
- **References:**
  - SQLAlchemy 2.0 Documentation: https://docs.sqlalchemy.org/en/20/
  - SQLAlchemy 2.0 Migration Guide: https://docs.sqlalchemy.org/en/20/changelog/migration_20.html

---

### DEC-2026-02-08-003: Timezone-Aware Timestamps Everywhere
- **Decision:** ALL timestamps use `datetime.now(timezone.utc)` (NEVER `datetime.utcnow()`)
- **Context:** Timezone bugs are subtle, hard to debug, and cause production issues (incorrect order timestamps, wrong PnL calculations, missed circuit breaker triggers)
- **Rationale:**
  - **datetime.utcnow() is deprecated** in Python 3.12+ (will be removed)
  - **Timezone-aware datetimes prevent naive datetime bugs** (comparing UTC to local time)
  - **Consistent with modern Python best practices** (PEP 615, Python 3.9+)
  - **Better for debugging and logs** (all times explicitly UTC, no ambiguity)
  - **Trading systems require UTC** (all exchanges use UTC timestamps)
  - **Prevents DST bugs** (no local timezone shifts affect logic)
- **Alternatives Considered:**
  - **datetime.utcnow():** Rejected due to deprecation, returns naive datetime (no timezone info)
  - **pytz library:** Not needed (timezone module in stdlib since Python 3.9)
  - **Local time with conversion:** Rejected due to complexity and DST edge cases
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.1 (Utils), Section 1.2 (Models)
- **Affected Files:**
  - `src/utils/time.py` - All time utility functions use timezone.utc
  - `src/data/models/base.py` - TimestampMixin uses `default=lambda: datetime.now(timezone.utc)`
  - `src/api/main.py` - All API timestamps use timezone.utc
  - All model files - All datetime fields use timezone-aware defaults
- **References:**
  - PEP 615 (Support for IANA Time Zone Database): https://peps.python.org/pep-0615/
  - Python datetime docs: https://docs.python.org/3/library/datetime.html

---

### DEC-2026-02-08-004: CORS Security - Explicit Origins Only
- **Decision:** CORS middleware uses explicit origin lists (NEVER `allow_origins=["*"]`)
- **Context:** Production security audit identified wildcard CORS as CRITICAL security vulnerability (SEC-001)
- **Rationale:**
  - **Wildcard CORS allows ANY website to make requests** to the API (XSS, CSRF attacks)
  - **OWASP Top 10 violation** (A05:2021 - Security Misconfiguration)
  - **Prevents credential theft** (cookies, API keys exposed to malicious sites)
  - **Defense in depth** (even if other security fails, CORS provides boundary)
  - **Environment-specific control:**
    - Development: Explicit localhost origins only (`http://localhost:3000`, etc.)
    - Production: Load from `ALLOWED_ORIGINS` environment variable
- **Alternatives Considered:**
  - **Wildcard with credentials=False:** Still vulnerable to data exfiltration attacks
  - **Origin validation in middleware:** Rejected due to complexity, CORS middleware already provides this
  - **No CORS middleware:** Rejected due to legitimate need for browser-based dashboard
- **Status:** ACTIVE (FIXED from initial wildcard)
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.1 (API Setup), Task 1.1.2
- **Affected Files:**
  - `src/api/main.py` - CORS middleware configuration (lines 51-73)
- **References:**
  - OWASP CORS Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Origin_Resource_Sharing_Cheat_Sheet.html
  - MDN CORS Documentation: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS

---

### DEC-2026-02-08-005: Real Database Health Checks (Not Fake)
- **Decision:** `/ready` endpoint performs ACTUAL database connectivity check with `SELECT 1` query
- **Context:** Kubernetes/Docker orchestrators rely on health checks for deployment decisions (routing, scaling, restarts). Fake health checks mask real failures and cause production outages.
- **Rationale:**
  - **Real check verifies actual connectivity** (not just process running)
  - **Kubernetes uses /ready for readiness probes** (determines if pod receives traffic)
  - **Catches database connection pool exhaustion** (real issue in production)
  - **Detects network issues between app and database** (firewalls, DNS)
  - **Returns 503 Service Unavailable when unhealthy** (standard HTTP status for health checks)
  - **Fake "ok" string masks real failures** (pod appears healthy but can't serve requests)
- **Alternatives Considered:**
  - **Fake "ok" response:** Original implementation, rejected due to masking failures
  - **Ping database server:** Rejected, doesn't verify actual SQL connectivity
  - **Check session pool only:** Rejected, doesn't verify database is actually responding
- **Status:** ACTIVE (FIXED from fake check)
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.1 (API Setup), Task 1.1.2
- **Affected Files:**
  - `src/api/main.py` - `/ready` endpoint (lines 131-179)
- **References:**
  - Kubernetes Liveness/Readiness Probes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
  - Docker HEALTHCHECK: https://docs.docker.com/engine/reference/builder/#healthcheck

---

### DEC-2026-02-08-006: N+1 Query Prevention with selectinload()
- **Decision:** Use `selectinload()` for ALL relationship eager loading in DataStore queries
- **Context:** Lazy loading relationships causes N+1 query problem (loading 100 orders triggers 100+ additional queries for trades). This creates severe performance degradation in production.
- **Rationale:**
  - **98% query reduction achieved** (101 queries → 2 queries for 100 orders with trades)
  - **10x performance improvement** (500ms → 50ms for typical operations)
  - **selectinload() uses efficient IN query** (single query with `WHERE id IN (...)`)
  - **Critical for production systems** (hundreds of orders/day would generate thousands of queries)
  - **Prevents database connection pool exhaustion** (each query holds connection)
  - **Better than joinedload() for one-to-many** (avoids Cartesian product)
- **Alternatives Considered:**
  - **Lazy loading (default):** Rejected due to N+1 problem, unacceptable in production
  - **joinedload():** Rejected for one-to-many (creates Cartesian product, larger result sets)
  - **Hybrid approach:** Rejected due to complexity, inconsistent patterns
  - **Manual join queries:** Rejected due to boilerplate, error-prone
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.2 (DataStore), Task 1.2.12
- **Affected Files:**
  - `src/data/store.py` - All query methods use selectinload() (lines 150+)
- **References:**
  - SQLAlchemy Loading Techniques: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
  - N+1 Problem Explained: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#what-is-the-n-plus-one-problem

---

### DEC-2026-02-08-007: Comprehensive Input Validation at Model Layer
- **Decision:** ALL numeric fields validated with `@validates` decorators at the model layer
- **Context:** Invalid data (NaN, Infinity, negative balances) causes downstream calculation errors, crashes, and data corruption. Must fail fast at data entry.
- **Rationale:**
  - **Fail-fast validation prevents corruption** (catch errors at INSERT, not calculation time)
  - **Validates: NaN, Infinity, negative values, zero quantities** (all common edge cases)
  - **Model layer is authoritative** (all data passes through models, single validation point)
  - **Reduces downstream validation complexity** (trust model data is valid)
  - **Better error messages** (field-specific, includes actual value)
  - **Prevents cascading failures** (bad data doesn't propagate through system)
  - **Required for production systems** (cannot trust external data sources)
- **Alternatives Considered:**
  - **API layer validation only:** Rejected, doesn't protect direct database access or internal operations
  - **Service layer validation:** Rejected, validation scattered across multiple files
  - **Database constraints only:** Rejected, doesn't catch NaN/Infinity (SQL has limited validation)
  - **No validation:** Original implementation, rejected due to data corruption risk
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.2 (Database Models), Tasks 1.2.2 through 1.2.7
- **Affected Files:**
  - `src/data/models/account.py` - Validates balance_usdt, equity_usdt (lines 54-76)
  - `src/data/models/order.py` - Validates quantity, price, filled_quantity (lines 79-113)
  - `src/data/models/position.py` - Validates size, entry_price, pnl (similar pattern)
  - `src/data/models/trade.py` - Validates quantity, price, commission
- **References:**
  - SQLAlchemy Validation: https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html#simple-validators
  - Data Validation Best Practices: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html

---

### DEC-2026-02-08-008: Structured Logging with structlog
- **Decision:** Use `structlog` for structured logging (JSON format in production, console in development)
- **Context:** Production observability and debugging require machine-parseable logs with rich context (not string concatenation)
- **Rationale:**
  - **JSON logs are machine-parseable** (ElasticSearch, CloudWatch Insights, Datadog)
  - **Better for log aggregation** (structured fields can be queried, filtered, aggregated)
  - **Structured context** (error, path, method, user, etc. as separate fields)
  - **Development uses console format** for readability (colors, indentation)
  - **Consistent logging across all modules** (same structured format everywhere)
  - **Better debugging** (grep by order_id, symbol, account_id instead of parsing strings)
  - **Required for production systems** (log analysis, alerting, troubleshooting)
- **Alternatives Considered:**
  - **Standard logging with string formatting:** Rejected, not machine-parseable, hard to query
  - **Python logging with JSON formatter:** Rejected, less flexible than structlog
  - **Custom logging solution:** Rejected, reinventing wheel
  - **No structured logging:** Rejected, unacceptable for production
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.1 (Utils/Logging), Task 1.1.3
- **Affected Files:**
  - `src/utils/logging.py` - Structured logging setup (lines 1-150)
  - `src/api/main.py` - All log calls use structured format
  - `src/data/database.py` - Database errors logged with context
- **References:**
  - structlog Documentation: https://www.structlog.org/
  - Logging Best Practices: https://www.loggly.com/ultimate-guide/python-logging-basics/

---

### DEC-2026-02-08-009: Explicit JSON Type for SQLAlchemy 2.0
- **Decision:** ALL dict/list fields in models use explicit `JSON` type in `mapped_column()`
- **Context:** SQLAlchemy 2.0 with `Mapped[dict[str, Any]]` syntax requires explicit column type specification. Without it, raises `MappedAnnotationError`.
- **Rationale:**
  - **Required by SQLAlchemy 2.0** (type inference doesn't work for complex types)
  - **Explicit is better than implicit** (clear intent in code)
  - **Prevents runtime errors** (fails immediately on import, not at query time)
  - **Type-safe JSON serialization** (ensures dict/list are JSON-serializable)
  - **Clear documentation** (developers know field is stored as JSON)
- **Alternatives Considered:**
  - **Type inference:** Doesn't work in SQLAlchemy 2.0 for dict/list types
  - **PickleType:** Rejected, not human-readable in database, not portable
  - **String with manual serialization:** Rejected, error-prone, loses type safety
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.2 (Database Models), multiple fixes
- **Affected Files:**
  - `src/data/models/account.py` - risk_config field (line 47)
  - `src/data/models/strategy.py` - parameters, symbols, backtest_results fields
  - `src/data/models/signal.py` - indicators field
  - `src/data/models/pnl.py` - extra_data field
  - `src/data/models/system.py` - circuit_breakers field
- **References:**
  - SQLAlchemy JSON Type: https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.JSON

---

### DEC-2026-02-08-010: Lambda Functions for Mutable Defaults
- **Decision:** ALL dict/list defaults use `default=lambda: {...}` or `default=lambda: cast(..., {})`
- **Context:** Python mutable default bug causes shared state across instances (all accounts share same risk_config dict). This is a critical bug that corrupts data.
- **Rationale:**
  - **Prevents mutable default bug** (Python's most infamous gotcha)
  - **Each instance gets separate dict/list** (no shared state)
  - **SQLAlchemy 2.0 best practice** (documented in migration guide)
  - **Required with Mapped[T] syntax** (static type checkers catch missing defaults)
  - **Using cast() for type checker happiness** (mypy requires explicit type for lambda returns)
- **Alternatives Considered:**
  - **default=dict or default=list:** CRITICAL BUG - all instances share same object
  - **No default:** Rejected, field becomes NOT NULL without default (breaks existing data)
  - **default=None with nullable:** Rejected, complicates logic (need to handle None everywhere)
- **Status:** ACTIVE (FIXED from mutable defaults)
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.2 (Database Models), multiple fixes
- **Affected Files:**
  - `src/data/models/account.py` - risk_config (line 47)
  - `src/data/models/strategy.py` - parameters, symbols, backtest_results
  - `src/data/models/system.py` - circuit_breakers
  - `src/data/models/pnl.py` - extra_data
- **References:**
  - Python Mutable Default Arguments: https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
  - SQLAlchemy 2.0 Migration: https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#orm-declarative-models

---

### DEC-2026-02-08-011: Boolean SQL Comparison with .is_()
- **Decision:** Use `.is_(False)` instead of `== False` for boolean SQL comparisons
- **Context:** SQL NULL handling with boolean columns. `== False` doesn't match NULL values, but `.is_(False)` correctly handles NULL in SQL.
- **Rationale:**
  - **Correct NULL handling** (SQL three-valued logic: TRUE, FALSE, NULL)
  - **`== False` doesn't match NULL rows** (WHERE column = FALSE excludes NULLs)
  - **`.is_(False)` generates `IS FALSE`** (correct SQL for boolean comparison)
  - **SQLAlchemy best practice** (documented in ORM tutorial)
- **Alternatives Considered:**
  - **== False:** Original implementation, rejected due to NULL handling
  - **explicit NULL check:** More verbose, less readable
- **Status:** ACTIVE (FIXED)
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.2 (DataStore), Task 1.2.12
- **Affected Files:**
  - `src/data/store.py` - get_active_strategies() query
- **References:**
  - SQLAlchemy Boolean Operations: https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.ColumnElement.is_

---

### DEC-2026-02-08-012: Graceful Shutdown with Resource Cleanup
- **Decision:** Application shutdown handler closes database connections gracefully
- **Context:** Docker/Kubernetes send SIGTERM before killing containers. Must cleanup resources to prevent connection leaks and corrupted transactions.
- **Rationale:**
  - **Prevents connection leaks** (database connection pool exhaustion)
  - **Allows in-flight transactions to complete** (prevents data corruption)
  - **Standard Docker/K8s pattern** (handles SIGTERM gracefully)
  - **Logs shutdown events** (audit trail for debugging)
  - **Better than abrupt termination** (SIGKILL after 30s)
- **Alternatives Considered:**
  - **No shutdown handler:** Rejected, connections not closed, potential leaks
  - **atexit handler:** Rejected, not called on SIGTERM
  - **Context manager only:** Not sufficient for FastAPI lifespan
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.1 (API Setup), Task 1.1.2
- **Affected Files:**
  - `src/api/main.py` - shutdown_event() handler (lines 242-268)
- **References:**
  - FastAPI Lifespan Events: https://fastapi.tiangolo.com/advanced/events/

---

### DEC-2026-02-08-013: Global Exception Handler for Unhandled Errors
- **Decision:** FastAPI global exception handler catches all unhandled exceptions
- **Context:** Unhandled exceptions return 500 with generic error, no logging. Need detailed logging and environment-appropriate error messages.
- **Rationale:**
  - **All exceptions logged with full context** (path, method, error, traceback)
  - **Development: detailed errors** (full exception message for debugging)
  - **Production: generic errors** (prevents information leakage)
  - **Structured logging** (exc_info=True captures full traceback)
  - **Better than default FastAPI handler** (no logging, generic message)
- **Alternatives Considered:**
  - **Default FastAPI handler:** Rejected, no logging
  - **Per-route error handling:** Rejected, duplicated code, easy to miss
  - **Middleware-based:** Rejected, exception handlers more idiomatic
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.1 (API Setup), Task 1.1.2
- **Affected Files:**
  - `src/api/main.py` - global_exception_handler() (lines 80-110)
- **References:**
  - FastAPI Exception Handlers: https://fastapi.tiangolo.com/tutorial/handling-errors/

---

### DEC-2026-02-08-014: Explicit Table Names (No Auto-Pluralization)
- **Decision:** All models define explicit `__tablename__` (no relying on automatic naming)
- **Context:** SQLAlchemy auto-pluralization creates "strategys" (incorrect) instead of "strategies". Foreign keys break when table names mismatch.
- **Rationale:**
  - **Prevents naming bugs** (naive pluralization: "strategys", "activitys")
  - **Explicit is better than implicit** (clear intent in code)
  - **Foreign key constraints work correctly** (references match actual table names)
  - **Database inspector tools show expected names** (strategies, not strategys)
  - **Migration scripts use correct names** (Alembic generates proper SQL)
- **Alternatives Considered:**
  - **Auto-pluralization:** Rejected, creates incorrect table names
  - **Custom pluralization function:** Rejected, adds complexity
  - **Singular table names:** Rejected, violates database naming conventions
- **Status:** ACTIVE (FIXED)
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.2 (Database Models), multiple fixes
- **Affected Files:**
  - `src/data/models/strategy.py` - `__tablename__ = "strategies"` (line 52)
  - `src/data/models/strategy_assignment.py` - `__tablename__ = "strategy_assignments"`
- **References:**
  - SQLAlchemy Table Configuration: https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html

---

### DEC-2026-02-08-015: Bidirectional Relationships with back_populates
- **Decision:** All relationships define bidirectional links with `back_populates`
- **Context:** Unidirectional relationships prevent object graph navigation and break eager loading. Need to traverse relationships in both directions.
- **Rationale:**
  - **Enables bidirectional navigation** (order.trades and trade.order both work)
  - **Required for eager loading** (selectinload needs back_populates)
  - **Maintains referential integrity** (SQLAlchemy keeps both sides in sync)
  - **Better DX** (can navigate object graph naturally)
  - **Clearer intent** (documents relationship explicitly on both sides)
- **Alternatives Considered:**
  - **Unidirectional relationships:** Rejected, breaks eager loading
  - **backref:** Deprecated in SQLAlchemy 2.0, use back_populates instead
- **Status:** ACTIVE
- **Date Decided:** 2026-02-08
- **Implemented By:** Section 1.2 (Database Models), Task 1.2.6
- **Affected Files:**
  - `src/data/models/order.py` - trades relationship (line 77)
  - `src/data/models/trade.py` - order relationship
  - All other models with relationships
- **References:**
  - SQLAlchemy Relationships: https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html

---

### DEC-2026-05-04-001: RegimeDetector Dual-EMA Composite 4-State Approach
- **Decision:** Use EMA(50) + EMA(200) on BTC daily bars to classify regime into 4 states: STRONG_BULL, PULLBACK_BULL, BOUNCE_BEAR, STRONG_BEAR
- **Context:** Single EMA(200) creates a long ambiguous zone where price straddles the average for weeks. Two EMAs capture both market structure velocity AND directional bias simultaneously, giving actionable signal for strategy selection.
- **Rationale:**
  - **4 states map to real strategy needs:** Bull pullback strategies (BTP, MACD_PB) work in PULLBACK_BULL but would burn capital in STRONG_BEAR
  - **EMA(50)/EMA(200) golden/death cross is industry-standard** for macro regime identification
  - **BTC as proxy:** BTC regime strongly correlates with altcoin conditions, making it the right signal source for the whole portfolio
  - **Self-directing strategies (ICVP)** route via "all" tag and handle their own internal direction via Ichimoku cloud
- **Alternatives Considered:**
  - **Single EMA(200) threshold:** Rejected — long ambiguous zones where price oscillates around EMA200 create false switches
  - **Manual regime tagging:** Replaced — required human intervention, caused -$2,323 loss when BTF was left active in bull (April 2026)
  - **ADX + trend filter:** Rejected — adds parameters without solving the regime identification problem
- **Status:** ACTIVE
- **Date Decided:** 2026-05-04
- **Implemented By:** `src/core/strategy/regime/detector.py`
- **Affected Files:**
  - `src/core/strategy/regime/detector.py` - RegimeState enum + RegimeDetector class
  - `src/core/strategy/regime/router.py` - _get_template_ids_for_regime() uses is_bull/is_bear
  - `scripts/run_paper_trading.py` - FULL_STRATEGY_CONFIG regime tags
- **References:**
  - Golden/death cross: standard technical analysis reference

---

### DEC-2026-05-04-002: 2-Consecutive-Close Confirmation for Regime Changes
- **Decision:** A regime change is only acted upon after 2 consecutive daily closes on the same macro side (bull or bear). A single-bar disagreement returns UNKNOWN and no action is taken.
- **Context:** Single-candle reversals (wicks, flash crashes, overnight gaps) can temporarily flip EMA relationships without representing true regime changes. Acting on them causes unnecessary engine restarts and potentially switches the wrong strategy set during intraday noise.
- **Rationale:**
  - **2 closes = 48h of price evidence** before committing to a regime change
  - **Market-structure-driven:** Anchored to actual price evidence rather than calendar time (unlike a 2-day timer that ignores candle direction)
  - **UNKNOWN fallback is safe:** If confirmation fails, existing engines keep running, avoiding partial-regime states
  - **Empirical basis:** Q1 2026 bear → April 2026 bull transition took 3+ days of consecutive closes above EMA(200) before stabilizing
- **Alternatives Considered:**
  - **Single-close confirmation:** Rejected — too reactive to intraday spikes and wicks
  - **3+ closes:** Rejected — adds 24h lag without proportional benefit; 2 closes proven sufficient for prior regime transitions
  - **48-hour calendar timer:** Rejected — ignores price direction during the wait window
- **Status:** ACTIVE
- **Date Decided:** 2026-05-04
- **Implemented By:** `src/core/strategy/regime/detector.py::get_confirmed_state()`
- **Affected Files:**
  - `src/core/strategy/regime/detector.py` - get_confirmed_state() checks last N closes
  - `src/core/strategy/regime/router.py` - calls get_confirmed_state() before applying regime
- **References:**
  - See MEMORY.md: "Architecture plan — RegimeRouter (next sprint)"

---

## Locked Decisions (DO NOT CHANGE Without PRD Update)

These decisions are **LOCKED** per MVP scope control rules until specified review dates:

### DEC-2026-01-15-001: Asset Class - Crypto ONLY
- **Decision:** MVP supports ONLY cryptocurrency trading (BTC, ETH, BNB, etc.)
- **Status:** LOCKED until Q2 2026 review
- **Rationale:** Focus on single asset class for MVP, best API support, high liquidity
- **Do NOT:** Add stocks, forex, commodities, options
- **References:** PRD Part 2.2.1, `.claude/rules/mvp-scope-control.md` Rule 2.4.1

### DEC-2026-01-15-002: Broker - Binance ONLY
- **Decision:** MVP supports ONLY Binance exchange (testnet for development)
- **Status:** LOCKED (broker) — **market-type sub-constraint AMENDED by DEC-2026-05-28-001 on 2026-05-28** to permit Binance margin/futures (still Binance-only).
- **Rationale:** Best API, highest liquidity, comprehensive testnet, excellent documentation
- **Do NOT:** Add Coinbase, Kraken, FTX, other exchanges
- **References:** PRD Part 2.2.2, `.claude/rules/mvp-scope-control.md` Rule 2.4.2

### DEC-2026-01-15-003: Database - SQLite (dev) / PostgreSQL (prod)
- **Decision:** SQLite for development, PostgreSQL for production (NO MongoDB, MySQL)
- **Status:** LOCKED until V1
- **Rationale:** Simplicity, zero-ops for development, proven for production
- **Do NOT:** Add MongoDB, MySQL, NoSQL databases
- **References:** PRD Part 2.2.3, `.claude/rules/mvp-scope-control.md` Rule 2.4.3

### DEC-2026-01-15-004: Order Types - Market Orders ONLY
- **Decision:** MVP supports ONLY market orders (no limit, stop, conditional orders)
- **Status:** LOCKED until V1
- **Rationale:** Simplicity, guaranteed fills, easier risk management
- **Do NOT:** Add limit orders, stop-loss orders, OCO orders, conditional orders
- **References:** PRD Part 2.2.4, `.claude/rules/mvp-scope-control.md` Rule 2.4.4

### DEC-2026-01-15-005: Architecture - Monolithic
- **Decision:** MVP uses monolithic architecture (single deployment unit, no microservices)
- **Status:** LOCKED until V2
- **Rationale:** Simplicity, single deployment, easier debugging, faster development
- **Do NOT:** Split into microservices, add service mesh, introduce message brokers
- **References:** PRD Part 2.2.5, `.claude/rules/mvp-scope-control.md` Rule 2.4.5

---

## Superseded Decisions

(Empty - no decisions have been superseded yet)

---

## Decisions Under Review

(Empty - no decisions currently under review)

---

## Decision Change Process

### To Change an Existing Decision:

1. **Identify the decision** to change (DEC-YYYY-MM-DD-XXX)
2. **Document why change is needed** (what problem exists with current decision?)
3. **Propose new decision** with rationale and alternatives
4. **Get explicit user approval** (required for all decision changes)
5. **Update this file:**
   - Mark old decision as **SUPERSEDED**
   - Add new decision with new ID
   - Reference superseded decision in new entry
6. **Update affected code** to match new decision
7. **Update documentation** (PRD, Architecture, etc.)
8. **Run production audit** to verify no regressions

### To Add a New Decision:

1. **Assign next sequential ID** (DEC-YYYY-MM-DD-XXX)
2. **Fill out decision template** (complete all fields)
3. **Add to appropriate section** (Phase 1, Phase 2, etc.)
4. **Reference in code comments** where implemented
5. **Update CLAUDE.md** if decision affects all future work

---

## Quick Reference

### Most Critical Decisions (Read First):

1. **DEC-2026-02-08-003:** Timezone-aware timestamps (affects ALL datetime code)
2. **DEC-2026-02-08-007:** Input validation at model layer (affects ALL models)
3. **DEC-2026-02-08-006:** N+1 prevention with selectinload (affects ALL queries)
4. **DEC-2026-02-08-004:** CORS security (affects API security)
5. **DEC-2026-02-08-002:** SQLAlchemy 2.0 with Mapped[T] (affects ALL models)

### Locked Decisions (Cannot Change in MVP):

- Asset Class: Crypto ONLY
- Broker: Binance ONLY
- Database: SQLite/PostgreSQL ONLY
- Orders: Market orders ONLY
- Architecture: Monolithic ONLY

---

### DEC-2026-05-07-001: Three New Bull-Regime Signal Generators
- **Decision:** Add EmaRibbonExpansion, VolumeBalanceBreakout, and RocMomentumSurge as new bull-regime generators targeting three orthogonal signal dimensions.
- **Context:** Existing bull generators (BTP, TAM, VRB) all detect slightly overlapping patterns. Adding orthogonal signals — trend structure, order flow, and price velocity — reduces correlated losses and provides diversified entries across different bull market phases.
- **Rationale:** (1) EREE measures EMA ribbon compression/expansion (trend momentum geometry), not used by any prior strategy. (2) VBB measures up-volume fraction over a rolling window (institutional order flow), not used by any prior strategy. (3) RMS uses ROC acceleration in the RSI 60-75 "power zone" — counter-intuitively buys elevated RSI as a strength signal specific to crypto bull markets, not used by any prior strategy. Three distinct market dimensions with zero indicator overlap.
- **Alternatives Considered:** Candle pattern recognition (too noisy for 1H crypto), funding rate analysis (no data source), on-chain metrics (no data source), VWAP reclaim (close to existing strategies).
- **Status:** ACTIVE
- **Date Decided:** 2026-05-07
- **Implemented By:** Strategy generator layer
- **Affected Files:** `src/core/strategy/generators/ema_ribbon_expansion.py`, `src/core/strategy/generators/volume_balance_breakout.py`, `src/core/strategy/generators/roc_momentum_surge.py`, `src/core/strategy/generators/__init__.py`, `src/core/strategy/factory.py`
- **References:** Backtest validation pending (90d × 8 symbols vigorous test)

### DEC-2026-05-07-002: VRB BTC + BTP DOGE Promoted to Paper Trading
- **Decision:** Promote VolatilityRegimeBreakout on BTCUSDT and BullTrendPullback on DOGEUSDT to paper trading observation with relaxed gates (Gate1=10, Gate2=20) due to low-frequency nature.
- **Context:** VRB BTC showed consistent edge (PF 1.16-1.55, WR 40-43%) across 45d and 90d backtest windows. BTP DOGE showed exceptional 45d bull performance (PF=5.10, Sharpe=7.15, WR=66.7%). Both are low-frequency strategies that cannot hit the standard 30-trade SUPERVISED threshold in 45-90 days.
- **Rationale:** Relaxed paper trading gates (10 trades for Gate1 instead of 20) are appropriate for regime-gated strategies that only fire in bull phases. The quality metrics (WR, PF, Sharpe) are strong enough to warrant live observation.
- **Alternatives Considered:** Loose parameters to generate more trades (rejected — degrades quality), skip paper trading and defer (rejected — strong enough evidence for observation).
- **Status:** ACTIVE
- **Date Decided:** 2026-05-07
- **Implemented By:** `scripts/run_paper_trading.py` BULL_STRATEGY_CONFIG
- **Affected Files:** `scripts/run_paper_trading.py`
- **References:** Backtest results 2026-05-07

### DEC-2026-05-08-001: VBB Promoted to Paper Trading on BTC/ETH/SOL
- **Decision:** Promote VolumeBalanceBreakout on BTCUSDT, ETHUSDT, SOLUSDT to paper trading with Gate1=10, Gate2=20.
- **Context:** Three independent 90-day backtest rounds confirmed edge on large-cap symbols: BTC PF=1.39/Sharpe=0.59/10 trades, ETH PF=1.94/Sharpe=1.83/9 trades, SOL PF=2.02/Sharpe=1.66/10 trades. Strategy fails on altcoins (XRP/AVAX/DOT/BNB PF<0.85) — institutional accumulation patterns are clearest on highest-liquidity assets. Low-frequency by design (6-10 trades per 90d) because it requires rare institutional accumulation + breakout conditions.
- **Rationale:** VBB results were stable across 3 rounds of independent testing, including one round where VBB params were unchanged while other strategy params changed — results were identical (PF=1.39/1.94/2.02), confirming signal stability. Edge confirmed. Relaxed gates (Gate1=10) applied per precedent from BTP/VRB.
- **Alternatives Considered:** Loosen parameters to increase trade count (rejected — round 2 tightening didn't improve quality; loosening would introduce noise), test on additional symbols (no evidence of edge on altcoins).
- **Status:** ACTIVE
- **Date Decided:** 2026-05-08
- **Implemented By:** `scripts/run_paper_trading.py` BULL_STRATEGY_CONFIG
- **Affected Files:** `scripts/run_paper_trading.py`, `src/core/strategy/generators/volume_balance_breakout.py`
- **References:** Backtest results 2026-05-08, min_bars_required fixed from 110 to 230

### DEC-2026-05-08-002: EREE and RMS Shelved — No Edge in Current Regime
- **Decision:** Shelve EmaRibbonExpansion and RocMomentumSurge strategies pending confirmed bull-market conditions.
- **Context:** Three rounds of 90d backtesting (24 runs each) showed no profitable edge for EREE or RMS. EREE: tightening ribbon_percentile from 25 to 10 + adding RSI 50-75 filter made results worse (DOGE PF dropped from 1.05 to 0.95), confirming the pattern has no edge in current regime — not a tuning problem. RMS: loosening RSI zone (60-78) and ROC threshold (1.5) increased trade count but reduced PF everywhere — DOT's PF=1.29 in round 2 was parameter noise.
- **Rationale:** Both strategies are conceptually designed for sustained bull markets where (EREE) EMA ribbon expansions lead to sustained trend continuation and (RMS) RSI 60-75 reflects acceleration not overbought conditions. In 90d mixed-regime data (partial bear market), both fire on bear relief bounces that quickly reverse. Shelving is appropriate rather than continued parameter tuning.
- **Alternatives Considered:** More tuning rounds (rejected — 3 rounds with different approaches showed consistent failure), redesign generators (deferred — may revisit in confirmed bull market regime).
- **Status:** ACTIVE
- **Date Decided:** 2026-05-08
- **Implemented By:** Not promoted to paper trading
- **Affected Files:** `src/core/strategy/generators/ema_ribbon_expansion.py`, `src/core/strategy/generators/roc_momentum_surge.py`
- **References:** Backtest results 2026-05-08

### DEC-2026-05-08-003: SRC Promoted to Paper Trading on BTC/ETH/SOL
- **Decision:** Promote StochRsiBullCross on BTCUSDT, ETHUSDT, SOLUSDT to paper trading with Gate1=10, Gate2=20.
- **Context:** Three independent 90-day backtest rounds confirmed exceptional large-cap edge. R1: BTC PF=6.77/5 trades, ETH PF=2.21/6 trades, SOL PF=2.72/5 trades. R2: ETH PF=2.21 (identical), SOL PF=2.82 (BTC missed due to API timeout). R3: BTC PF=8.71/Sharpe=3.185, ETH PF=2.21/Sharpe=1.285, SOL PF=2.80/Sharpe=1.687 — all with DD <3%. ETH producing exactly PF=2.21 across all three independent rounds is near-definitive signal stability. Fails on altcoins (BNB/XRP/AVAX/DOGE/DOT PF<0.90) — same large-cap selectivity as VBB.
- **Rationale:** The StochasticRSI oversold-cross-in-trend pattern is highly selective on liquid large-caps: genuine pullbacks to oversold levels in confirmed bull trends (EMA-50 above EMA-200) are rare, high-quality re-entry points. Altcoins have noisier StochRSI (frequent false oversold signals from high volatility) and weaker trend structure. Low frequency (5-6 trades per 90d per symbol = ~2/month) consistent with Gate1=10 precedent from VBB/BTP/VRB.
- **Alternatives Considered:** Loosen parameters to increase trade count (rejected — would include altcoins' false signals), test stoch_oversold=30 (rejected — wider threshold catches mid-range oscillations, destroying the edge).
- **Status:** ACTIVE
- **Date Decided:** 2026-05-08
- **Implemented By:** `scripts/run_paper_trading.py` BULL_STRATEGY_CONFIG
- **Affected Files:** `scripts/run_paper_trading.py`, `src/core/strategy/generators/stoch_rsi_bull_cross.py`
- **References:** Backtest results 2026-05-08 (3 rounds), stoch_rsi_bull_cross.py generator

### DEC-2026-05-08-004: ADT and KCC Shelved — No Edge in Current Regime
- **Decision:** Shelve AdxDirectionalThrust and KeltnerChannelContinuation strategies — no viable edge found across 3 rounds.
- **Context:** ADT: R1 showed marginal positive (ETH PF=1.05, SOL PF=1.03), R2 similar, R3 dropped to ETH PF=0.89/SOL PF=0.48 after loosening di_min_spread from 8.0 to 5.0 and reducing adx_rise_bars from 3 to 2. Loosening made results worse, not better — a parameter-insensitive failure. KCC: R3 catastrophic WR collapse on ETH (15.8%), BNB (15.0%), SOL (22.2%) after widening kc_multiplier to 2.0. BTC held at PF=1.11 across all rounds but never approached promotion threshold (1.35). Best single result across 3×8=24 runs was ADT ETH PF=1.05.
- **Rationale:** ADT's +DI/-DI spread oscillates frequently in the current bull market — many false accelerations where ADX rises briefly then reverses. KCC's wider band (2.0 multiplier) filters out weaker breakouts but the remaining breakouts appear to be momentum exhaustion moves rather than continuation signals. Both strategies conceptually sound but empirically fail in current mixed-regime 90d windows.
- **Alternatives Considered:** Further tuning (rejected — 3 rounds with systematically different approaches showed consistent failure or worsening); redesign entry conditions (deferred — generators exist in codebase and can be reactivated/redesigned if market regime changes).
- **Status:** ACTIVE
- **Date Decided:** 2026-05-08
- **Implemented By:** Not promoted to paper trading
- **Affected Files:** `src/core/strategy/generators/adx_directional_thrust.py`, `src/core/strategy/generators/keltner_channel_continuation.py`
- **References:** Backtest results 2026-05-08 (3 rounds, 24 runs each)

---

**Last Updated:** 2026-05-08
**Total Decisions:** 130 active, 0 superseded, 5 locked
**Next Decision ID:** DEC-2026-05-08-005

---

## Phase 1 Quality Improvements (2026-02-09)

### DEC-2026-02-09-001: Unique Constraint on Strategy Assignments
- **Decision:** Add unique constraint on `strategy_assignments(account_id, strategy_id)` to prevent duplicate assignments
- **Context:** Business rule violation - the same strategy should not be assigned to the same account multiple times. Without database constraint, race conditions or bugs could create duplicate assignments leading to unpredictable behavior and incorrect position sizing
- **Rationale:**
  - Database-level enforcement is more reliable than application-level validation
  - Prevents race conditions in concurrent assignment operations
  - Test suite expects this constraint (test_real_world_scenarios.py line 259)
  - Ensures data integrity at the lowest level
  - Performance impact negligible (constraint check is O(log n) with index)
- **Alternatives Considered:**
  - **App-level validation only:** Rejected due to race condition vulnerabilities
  - **Unique on (account_id, strategy_id, symbol):** Rejected as too restrictive (prevents same strategy on multiple symbols for same account)
  - **Allow duplicates with "active" flag:** Rejected as overly complex and error-prone
- **Status:** ACTIVE
- **Date Decided:** 2026-02-09
- **Implemented By:** Alembic migration `a3f9b82c1e45_add_unique_constraint`
- **Affected Files:**
  - `alembic/versions/20260209_add_unique_constraint_strategy_assignments.py` (migration)
  - `src/data/models/strategy_assignment.py` (enforced by database)
  - `tests/integration/test_real_world_scenarios.py` (validated by tests)
- **References:** DEC-2026-02-08-007 (input validation), Zero-Technical-Debt rules

---

### DEC-2026-02-09-002: 100% Model Test Coverage Requirement
- **Decision:** Require comprehensive unit test coverage for ALL database models with validators, properties, relationships, and edge cases
- **Context:** During Phase 1 completion audit, discovered 5 critical models (Trade, PnLRecord, EquitySnapshot, SystemState, AuditLog) had ZERO test coverage, representing 45% of untested models. This creates significant risk of data corruption, validator bugs, and regression during refactoring
- **Rationale:**
  - **Validators must be tested:** Models with @validates decorators can reject invalid data; untested validators may fail silently or have logic bugs
  - **Properties need verification:** Computed fields (notional_value, win_rate, is_safe_to_trade) have business logic that must be verified
  - **Relationships must work:** FK constraints, back_populates, and cascade deletes need testing to prevent N+1 queries and orphaned records
  - **Edge cases prevent production bugs:** Testing NaN, Infinity, negative values, None, and boundary conditions catches bugs before production
  - **Regression protection:** Comprehensive tests enable safe refactoring without breaking existing functionality
  - **Production-grade requirement:** Zero-Technical-Debt rules mandate this level of quality
- **Alternatives Considered:**
  - **Integration tests only:** Rejected as too coarse-grained (don't catch validator-specific bugs) and too slow
  - **Manual testing:** Rejected as not repeatable, error-prone, and time-consuming
  - **Partial coverage (80%):** Rejected as 20% gap includes critical safety models (SystemState kill switch)
- **Status:** ACTIVE
- **Date Decided:** 2026-02-09
- **Implemented By:** 
  - `tests/unit/data/test_models_trade.py` (14 test cases, 490 lines)
  - `tests/unit/data/test_models_pnl.py` (17 test cases, 380 lines)
  - `tests/unit/data/test_models_system.py` (26 test cases, 570 lines)
  - **Total: 57 new test cases, 1,440 lines of coverage**
- **Affected Files:** All 11 database models now have comprehensive test coverage
- **References:** 
  - `.claude/rules/zero-technical-debt.md` (testing requirements)
  - DEC-2026-02-08-007 (input validation testing)
  - DEC-2026-02-08-003 (timezone-aware timestamp testing)

---

### DEC-2026-02-09-003: Type-Safe DataStore Methods with Explicit Parameters
- **Decision:** Replace `**kwargs: Any` with explicit typed parameters in DataStore methods, providing IDE autocomplete and compile-time type checking
- **Context:** `DataStore.update_system_state(**updates: Any)` accepted any keyword arguments with no type validation, causing potential runtime errors from typos (e.g., `kill_swtich_active`), missing IDE autocomplete, and bypassing type checker validation
- **Rationale:**
  - **Type safety:** Type checker validates argument names and types at compile time, catching typos before runtime
  - **IDE autocomplete:** Explicit parameters enable intelligent code completion, reducing errors and improving developer experience
  - **Self-documenting API:** Function signature clearly shows available parameters and their types without reading docs
  - **Prevents silent failures:** `hasattr(state, key)` silently ignored typos; now they cause type errors
  - **Maintainability:** Future developers immediately see what fields can be updated
- **Alternatives Considered:**
  - **Keep **kwargs:** Rejected due to lack of type safety and poor developer experience
  - **TypedDict:** Rejected as still allows extra keys and doesn't provide as good IDE support as explicit parameters
  - **Partial class with only updatable fields:** Rejected as overly complex for this use case
- **Status:** ACTIVE
- **Date Decided:** 2026-02-09
- **Implemented By:** `src/data/store.py` line 575 (update_system_state method)
- **Affected Files:**
  - `src/data/store.py` (DataStore.update_system_state method)
  - All future callers benefit from type-safe API
- **References:** 
  - DEC-2026-02-08-002 (SQLAlchemy 2.0 type safety philosophy)
  - `.claude/rules/zero-technical-debt.md` (type hints required)
  - PEP 604 (union type syntax: `X | None`)

---

## Phase 1.3 & 1.4 Decisions (Configuration & Error Handling)

### DEC-2026-02-09-004: Configuration Hierarchy with Lazy Loading
- **Decision:** Configuration cascades from settings.yaml -> risk_profiles.yaml -> templates/*.yaml, accessed via a unified ConfigLoader with lazy-loaded properties
- **Context:** The system needs to load configuration from multiple sources (environment variables, YAML files, strategy templates) without loading everything eagerly at startup. Different components need different subsets of configuration.
- **Rationale:**
  - **Lazy loading avoids startup penalty** (only loads YAML when first accessed)
  - **Singleton pattern ensures consistency** (all components see same config)
  - **Pydantic v2 validation at load time** catches invalid config immediately
  - **Unified interface** (one `get_config()` call provides access to settings, profiles, and templates)
  - **Separation of concerns** (sensitive data in .env, non-sensitive in YAML, templates in separate files)
  - **Reset functions enable testing** (can reset singletons between tests)
- **Alternatives Considered:**
  - **Eager loading all config at startup:** Rejected, unnecessary for components that don't use all config
  - **Separate accessor functions per source:** Rejected, scattered access patterns
  - **Django-style settings module:** Rejected, not flexible enough for YAML + env + templates
- **Status:** ACTIVE
- **Date Decided:** 2026-02-09
- **Implemented By:** Section 1.3 (Configuration System), Tasks 1.3.1-1.3.6
- **Affected Files:**
  - `src/core/config/settings.py` - Pydantic v2 BaseSettings with env file
  - `src/core/config/risk_profiles.py` - YAML risk profile loading
  - `src/core/config/templates.py` - Strategy template YAML loading
  - `src/core/config/loader.py` - Unified lazy-loading ConfigLoader
  - `src/core/config/__init__.py` - Package exports
  - `config/settings.yaml` - Non-sensitive app configuration
  - `config/risk_profiles.yaml` - Risk profile definitions
  - `config/templates/*.yaml` - Strategy template definitions
- **References:** DEC-2026-02-08-008 (structured logging), PRD Part 2.2

---

### DEC-2026-02-09-005: Backup Retention Policy (30 Daily + 12 Monthly)
- **Decision:** Configuration backups use gzip-compressed JSON with retention policy of 30 daily backups and 12 monthly backups
- **Context:** Critical system state (strategies, accounts, positions, risk config) needs periodic backups with automatic cleanup to prevent unbounded disk usage while maintaining recovery capability
- **Rationale:**
  - **Gzip compression** reduces backup size by 70-90% (JSON compresses well)
  - **30-day daily retention** provides fine-grained recovery for recent issues
  - **12-month monthly retention** provides long-term historical recovery
  - **Automatic cleanup** prevents disk space exhaustion
  - **Filename-based timestamps** enable easy manual inspection and sorting
  - **Industry standard** for financial systems backup policies
  - **Restore validates required fields** (timestamp, version) to prevent corrupt restores
- **Alternatives Considered:**
  - **Keep all backups:** Rejected, unbounded disk growth
  - **Keep only last N backups:** Rejected, loses long-term recovery capability
  - **Database-level backups only:** Rejected, doesn't capture YAML config state
  - **Cloud storage (S3):** Out of MVP scope per DEC-2026-01-15-005
- **Status:** ACTIVE
- **Date Decided:** 2026-02-09
- **Implemented By:** Section 1.3 (Configuration System), Task 1.3.7
- **Affected Files:**
  - `src/core/config/backup.py` - ConfigBackupManager with retention policy
  - `config/settings.yaml` - backup section with retention settings
- **References:** PRD Part 2.2.14 (operational requirements), `.claude/rules/mvp-scope-control.md`

---

### DEC-2026-02-09-006: Sensitive Data Masking in Logs (Last 4 Chars)
- **Decision:** Log entries mask sensitive fields (api_key, secret_key, password, token, secret, authorization, credential) showing only last 4 characters; values shorter than 5 chars are fully masked as "****"
- **Context:** Structured logging captures rich context for debugging, but must never expose credentials in log output (violates security best practices, compliance requirements)
- **Rationale:**
  - **Last 4 chars preserved** for debugging (can identify which key is in use)
  - **Short values fully masked** prevents exposing entire 2-3 char tokens
  - **None values untouched** (no masking needed for missing fields)
  - **Implemented as structlog processor** (runs automatically on all log entries)
  - **Pattern-based key matching** catches common sensitive field names
  - **Balance between security and observability** (can verify correct key without exposing it)
- **Alternatives Considered:**
  - **No masking:** Rejected, CRITICAL security violation (credentials in plaintext logs)
  - **Full masking (show nothing):** Rejected, loses debugging capability
  - **First 4 chars instead of last 4:** Rejected, API key prefixes are less useful for identification
  - **Regex-based value detection:** Rejected, too complex and error-prone
- **Status:** ACTIVE
- **Date Decided:** 2026-02-09
- **Implemented By:** Section 1.4 (Logging Enhancement), Task 1.4.1
- **Affected Files:**
  - `src/utils/logging.py` - mask_sensitive_data() processor function
- **References:** DEC-2026-02-08-008 (structured logging), OWASP Logging Cheat Sheet

---

## Phase 2 Decisions (Data Acquisition Layer)

### DEC-2026-02-10-001: Use python-binance SDK Wrapper for API Integration
- **Decision:** Use the official `python-binance` library as a blocking sync wrapper, then wrap in asyncio.to_thread() for async integration with the system
- **Context:** Need to fetch market data (OHLCV, exchange info, account data) from Binance Spot API. Decision is how to integrate with the async-first system architecture
- **Rationale:**
  - **Official library** is production-tested with 200k+ downloads/week, actively maintained by ccxt community
  - **Well-documented API** reduces implementation risk and debugging time
  - **Supports HMAC-SHA256 authentication** without rolling custom crypto code (security risk)
  - **Request signing handled automatically** (prevents security bugs in signature implementation)
  - **Binance testnet support** enables development without real funds
  - **asyncio.to_thread() wrapper** integrates blocking library into async system cleanly
  - **Alternative (aiohttp + manual requests)** would add 2-3 days of work and introduce signature bugs
- **Alternatives Considered:**
  - **ccxt library:** Rejected, adds multi-exchange support (out of MVP scope), heavier dependency
  - **Manual requests.Session + HMAC:** Rejected, security risk, duplication of battle-tested code
  - **aiohttp with async-binance:** Rejected, immature library, fewer users, higher maintenance risk
  - **Build custom HTTP client:** Rejected, security liability for API authentication
- **Status:** ACTIVE
- **Date Decided:** 2026-02-10
- **Implemented By:** Section 2.1 (Market Data Fetching), Task 2.1.1
- **Affected Files:**
  - `src/brokers/binance/client.py` - BinanceClient async wrapper
  - `src/brokers/binance/exceptions.py` - Binance-specific exception hierarchy
  - `src/brokers/binance/__init__.py` - Module exports
  - `requirements.txt` - python-binance dependency
- **References:**
  - PRD Section 2.1 (Market Data Fetching)
  - DEC-2026-02-10-004 (Async-first architecture)
  - github.com/sammchardy/python-binance (official repository)

---

### DEC-2026-02-10-002: Token Bucket Rate Limiter with Priority Queue (PRD Feature J)
- **Decision:** Implement three independent token buckets (requests/min, orders/sec, daily orders) with priority queue for order execution (P1: stop_loss/take_profit > P2: new_entry > P3: data_fetch)
- **Context:** Binance enforces strict rate limits. PRD Feature J requires three tiers of rate limits with different thresholds (70% warning, 85% throttle, 95% emergency). Must prioritize critical orders over data fetching
- **Rationale:**
  - **Three independent buckets** match Binance's actual limit structure (1200 req/min, 10 orders/sec, 200k daily)
  - **Token bucket algorithm** allows controlled burst traffic while respecting average rate
  - **Priority queue ensures** stop_loss/take_profit orders execute even under load (safety critical)
  - **Threshold percentages** (70%, 85%, 95%) provide operational visibility and graceful degradation
  - **Async-aware design** with asyncio.Lock prevents race conditions in token consumption
  - **Testable algorithm** decoupled from actual rate limiter state (easier unit testing)
- **Alternatives Considered:**
  - **Single global bucket:** Rejected, doesn't match Binance's actual 3-bucket design
  - **Fixed delays between requests:** Rejected, doesn't handle bursts, no priority system
  - **Exponential backoff:** Rejected, reactive not proactive, poor user experience
  - **No rate limiting (trust Binance SDK):** Rejected, SDK doesn't track usage, violates "know your limits" principle
- **Status:** ACTIVE
- **Date Decided:** 2026-02-10
- **Implemented By:** Section 2.1 (Market Data Fetching), Task 2.1.2
- **Affected Files:**
  - `src/brokers/binance/rate_limiter.py` - TokenBucket and RateLimiter classes
  - `src/brokers/binance/client.py` - Integration with rate limiter
  - `tests/unit/test_rate_limiter.py` - Comprehensive unit tests
- **References:**
  - PRD Section 2.1.3 (Rate Limit Management - Feature J)
  - Binance API Documentation (rate limit structure)
  - DEC-2026-02-10-001 (python-binance wrapper)
  - `.claude/rules/zero-technical-debt.md` (no temporary hacks)

---

### DEC-2026-02-10-004: Async-First Architecture with asyncio.to_thread() for Blocking Operations
- **Decision:** System uses async/await throughout (coroutines in main execution paths), but wraps blocking operations (Binance SDK, DB operations) using asyncio.to_thread() to prevent blocking the event loop
- **Context:** PARAVANT is inherently I/O-bound (API calls, database queries, waiting for execution). Async allows handling multiple operations concurrently. However, some libraries (python-binance, SQLAlchemy ORM) are synchronous. Decision is how to integrate them
- **Rationale:**
  - **asyncio.to_thread()** executes blocking code in thread pool without blocking main event loop
  - **Minimal code changes** (wrap calls, keep library internal structure unchanged)
  - **Type-safe** (preserves return types and error handling)
  - **Scales to 100+ concurrent operations** with thread pool (default 5 workers, can configure)
  - **Easier than async SDK wrappers** which require understanding library internals
  - **Industry standard** for integrating legacy sync libraries into async systems
  - **Python 3.9+ feature** (we target 3.11+, no compatibility issues)
- **Alternatives Considered:**
  - **Greenlets/gevent:** Rejected, monkey-patching risks, less mature than asyncio
  - **Pure async libraries:** Rejected, would need aiohttp + custom async-binance (security risk)
  - **Threads everywhere:** Rejected, bad performance, GIL contention, unpredictable behavior
  - **Completely synchronous code:** Rejected, defeats purpose of async, can't scale
  - **Process pool (multiprocessing):** Rejected, overkill for I/O-bound, adds IPC overhead
- **Status:** ACTIVE
- **Date Decided:** 2026-02-10
- **Implemented By:** Section 2.1-2.3 (All Phase 2), Tasks 2.1.1-2.1.7, 2.3.1-2.3.4
- **Affected Files:**
  - `src/brokers/binance/client.py` - All methods use `await asyncio.to_thread()`
  - `src/data/market_data.py` - MarketDataFetcher async methods
  - `src/data/service.py` - MarketDataService async methods
  - `src/data/symbol_manager.py` - SymbolManager async methods
  - `tests/unit/test_*.py` - Tests use `@pytest.mark.asyncio`
  - `tests/integration/test_*.py` - Integration tests are async
- **References:**
  - Python docs: asyncio.to_thread() https://docs.python.org/3/library/asyncio-task-utils.html#asyncio.to_thread
  - PRD Section 2 (overall architecture)
  - DEC-2026-02-10-001 (python-binance wrapper integration)

---

### DEC-2026-02-11-001: Compute-on-Demand Indicator Strategy
- **Decision:** All technical indicators use compute-on-demand pattern (calculate from OHLCVSeries on each call, no stored state between calculations)
- **Context:** Indicators need to be calculated from OHLCV data. Decision is whether to store intermediate state or recompute from scratch each time
- **Rationale:**
  - **Stateless design** makes indicators pure functions (same input = same output)
  - **No stale state bugs** (no risk of cached intermediate values becoming outdated)
  - **Thread-safe by default** (no shared mutable state between calls)
  - **Simpler testing** (just provide input series, check output)
  - **Caching handled separately** by CachedIndicatorCalculator (DEC-2026-02-11-003)
  - **Performance acceptable** (full recalculation is ~1-20ms per indicator)
- **Alternatives Considered:**
  - **Incremental updates:** Rejected, complex state management, risk of drift from full calculation
  - **Store intermediate arrays:** Rejected, memory overhead, stale state risk
  - **Lazy evaluation with memoization:** Rejected, complex invalidation logic
- **Status:** ACTIVE
- **Date Decided:** 2026-02-11
- **Implemented By:** Section 2.2 (Technical Indicators), Tasks 2.2.1-2.2.11
- **Affected Files:**
  - `src/core/indicators/base.py` - Indicator ABC with stateless calculate()
  - `src/core/indicators/rsi.py`, `ema.py`, `sma.py`, `atr.py` - All compute from series
  - `src/core/indicators/macd.py`, `bollinger.py`, `donchian.py` - All compute from series
  - `src/core/indicators/supertrend.py`, `vwap.py`, `adx.py`, `volume.py` - All compute from series
- **References:**
  - PRD Section 2.2 (Technical Indicators)
  - DEC-2026-02-11-003 (caching layer for performance)

---

### DEC-2026-02-11-002: Wilder's Smoothing for RSI, ATR, and ADX
- **Decision:** RSI, ATR, and ADX use Wilder's smoothing (alpha = 1/period) instead of standard EMA smoothing (alpha = 2/(period+1))
- **Context:** Multiple smoothing methods exist for technical indicators. Wilder's original formulas (1978) use a specific smoothing method that differs from standard EMA. Using the wrong smoothing produces materially different indicator values
- **Rationale:**
  - **Matches TradingView reference values** (TradingView uses Wilder's for RSI/ATR/ADX)
  - **Original formula fidelity** (Wilder published these indicators with this specific smoothing)
  - **Industry standard** (most professional charting platforms use Wilder's)
  - **Material difference:** For period=14, Wilder's alpha=0.0714 vs EMA alpha=0.1333 (87% different smoothing factor)
  - **Verified by test:** `test_rsi_not_ema` confirms the correct smoothing is used
- **Alternatives Considered:**
  - **Standard EMA (alpha = 2/(period+1)):** Rejected, produces materially different values, doesn't match TradingView
  - **SMA fallback:** Rejected, no smoothing at all, very different from Wilder's
  - **Configurable smoothing:** Rejected, adds complexity, Wilder's is the de facto standard
- **Status:** ACTIVE
- **Date Decided:** 2026-02-11
- **Implemented By:** Section 2.2 (Technical Indicators), Tasks 2.2.2-2.2.4
- **Affected Files:**
  - `src/core/indicators/rsi.py` - Wilder's smoothing for avg gain/loss (line 144)
  - `src/core/indicators/atr.py` - Wilder's smoothing for ATR (line 130)
  - `src/core/indicators/adx.py` - Wilder's smoothing for DM, DI, and ADX (lines 284-329)
  - `tests/unit/indicators/test_rsi.py` - test_rsi_not_ema verification
- **References:**
  - Wilder, J.W. (1978). "New Concepts in Technical Trading Systems"
  - TradingView RSI documentation
  - DEC-2026-02-11-001 (compute-on-demand strategy)

---

### DEC-2026-02-11-003: Three-Layer Caching Architecture
- **Decision:** Implement three-layer caching: InMemoryCache (backend) -> CacheManager (key generation + get_or_set) -> CachedIndicatorCalculator (indicator-specific caching)
- **Context:** API calls to Binance cost ~500ms. Indicator calculations cost ~1-20ms. Caching reduces both to <1ms for repeated requests. Need cache isolation between different indicators, symbols, timeframes, and parameters
- **Rationale:**
  - **Three layers separate concerns:**
    - InMemoryCache: low-level dict with TTL and async safety (asyncio.Lock)
    - CacheManager: deterministic key generation, get_or_set pattern, sync/async factory support
    - CachedIndicatorCalculator: indicator-aware cache keys with parameter hashing
  - **TTL by timeframe** (30s for 1m candles, 300s for 1h candles) matches data freshness needs
  - **Cache key includes indicator name + symbol + timeframe + params hash** prevents collisions
  - **Async-safe with asyncio.Lock** prevents race conditions in concurrent access
  - **Target: >80% cache hit rate** reduces API calls and computation significantly
  - **Cache-aside pattern** (check cache -> compute if miss -> store result)
- **Alternatives Considered:**
  - **Redis:** Rejected for MVP, adds external dependency (DEC-2026-01-15-005 monolithic)
  - **Single-layer dict cache:** Rejected, no TTL, no key generation, no isolation
  - **LRU cache with functools:** Rejected, no TTL support, no async safety
  - **No caching:** Rejected, 500ms API calls unacceptable for real-time trading
- **Status:** ACTIVE
- **Date Decided:** 2026-02-11
- **Implemented By:** Section 2.3 (Caching Layer), Tasks 2.3.1-2.3.4
- **Affected Files:**
  - `src/data/cache.py` - CacheBackend ABC, InMemoryCache, CacheManager
  - `src/core/indicators/cached.py` - CachedIndicatorCalculator, INDICATOR_CACHE_TTLS
  - `src/data/service.py` - MarketDataService with OHLCV caching
  - `tests/unit/test_cache.py` - Comprehensive cache tests
  - `tests/unit/indicators/test_cached.py` - CachedIndicatorCalculator tests
- **References:**
  - PRD Section 2.3 (Data Caching Strategy)
  - DEC-2026-02-10-004 (async-first architecture)
  - DEC-2026-02-11-001 (compute-on-demand makes caching essential)

---

## Phase 3A Decisions (Risk Controls - Kill Switch & Risk Controller)

### DEC-2026-02-12-001: Frozen Dataclasses for Immutable Risk Data Types
- **Decision:** All risk pipeline data types (OrderRequest, PortfolioState, PositionSizeResult, RiskCheckResult) use `@dataclass(frozen=True)` for immutability and thread safety
- **Context:** Risk checks run concurrently across accounts. Immutable data prevents subtle race conditions where one order's risk data could be accidentally modified, affecting another order's validation
- **Rationale:**
  - **Thread-safe by design** (frozen objects cannot be modified, no locks needed)
  - **Prevents bugs** where code accidentally modifies shared risk state
  - **Enables caching** (immutable objects can be safely cached and reused)
  - **Explicit API contract** (frozen = callers know state won't change)
  - **Type-checker friendly** (mypy understands frozen=True semantics)
  - **Critical for correctness** (kill switch decisions based on mutable state could fail)
- **Alternatives Considered:**
  - **Mutable dataclasses:** Rejected, risks race conditions in concurrent order validation
  - **NamedTuple:** Rejected, less flexible (no field validation via __post_init__)
  - **pydantic BaseModel:** Rejected, adds unnecessary runtime validation overhead
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.1 (Risk Controller), Task 3.1.1
- **Affected Files:**
  - `src/core/risk/types.py` - All four dataclasses use frozen=True
  - `src/core/risk/checks.py` - All check functions use frozen types
  - `src/core/risk/controller.py` - validate_order() pipeline uses frozen types
- **References:** DEC-2026-02-08-007 (input validation), threading safety principles

---

### DEC-2026-02-12-002: Pure Function Risk Checks (No Side Effects)
- **Decision:** Each risk check (kill_switch, daily_loss_limit, weekly_loss_limit, etc.) is a pure function taking typed inputs and returning RiskCheckResult with no side effects or database access
- **Context:** Risk validation must be fast (<100ms for full pipeline), testable, and composable. Side effects make testing difficult and create hidden dependencies
- **Rationale:**
  - **Fast execution** (no I/O, pure computation)
  - **Easily testable** (just provide inputs, check outputs)
  - **Composable pipeline** (each check independent, can reorder without breaking)
  - **No hidden dependencies** (all inputs explicit in function signature)
  - **Parallelizable** (no shared state, can run checks concurrently)
  - **Fail-fast architecture** (pipeline stops on first rejection)
- **Alternatives Considered:**
  - **Check methods on class:** Rejected, harder to compose, more complex testing
  - **Checks with side effects:** Rejected, would log/update state, making tests brittle
  - **SQL-based checks:** Rejected, too slow (each check = query)
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.1 (Risk Controller), Task 3.1.2
- **Affected Files:**
  - `src/core/risk/checks.py` - All 7 check functions are pure
  - `src/core/risk/controller.py` - validate_order() uses pure functions
- **References:** Functional programming best practices, DEC-2026-02-08-008 (logging)

---

### DEC-2026-02-12-003: Kill Switch Persistence via Existing SystemState
- **Decision:** Kill switch state (active, reason, timestamp) persists via existing SystemState singleton model (no new tables)
- **Context:** Kill switch is a critical safety mechanism that must survive application restarts. Needs centralized state but doesn't require dedicated table
- **Rationale:**
  - **Reuses existing architecture** (SystemState already exists for system-wide state)
  - **No schema migration needed** (leverages existing kill_switch_* fields)
  - **Single source of truth** (one table for all system state)
  - **Fail-safe design** (kill switch stays active on restart, manual deactivation required)
  - **Consistent with existing pattern** (other system state also in SystemState)
- **Alternatives Considered:**
  - **Separate KillSwitchState table:** Rejected, redundant schema, violates DRY principle
  - **In-memory only:** Rejected, lost on restart (violates fail-safe)
  - **Distributed state store:** Rejected, out of MVP scope, adds operational complexity
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.2 (Kill Switch), Task 3.2.1
- **Affected Files:**
  - `src/core/risk/kill_switch.py` - Uses existing SystemState.kill_switch_* fields
  - `src/data/models/system.py` - Already has the fields, no changes needed
  - `src/data/store.py` - update_system_state() used for persistence
- **References:** DEC-2026-02-08-015 (bidirectional relationships), MVP simplicity

---

### DEC-2026-02-12-004: Deactivation Codes in Memory Only (MVP Limitation)
- **Decision:** Kill switch deactivation codes generated via `secrets.token_hex(4)` and stored in KillSwitch instance memory only (lost on restart)
- **Context:** Deactivation requires confirmation code to prevent accidental re-enabling. MVP limitation: codes not persisted to database
- **Rationale:**
  - **Minimal implementation** (simple secrets.token_hex generation)
  - **Single-use enforcement** (code cleared after successful deactivation)
  - **New code on each request** (invalidates previous code)
  - **Acceptable for MVP** (operator must generate new code after restart)
  - **Future V1 can persist to database** (requires additional security considerations like encryption)
  - **Fail-safe** (kill switch stays active if operator loses code, can't accidentally slip back)
- **Alternatives Considered:**
  - **Persist to database:** Out of MVP scope, adds complexity (code encryption, TTL, etc.)
  - **No deactivation codes (always require restart):** Rejected, operationally inconvenient
  - **Static code in config:** Rejected, security risk (credentials in config file)
- **Status:** ACTIVE (MVP LIMITATION - revisit for V1)
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.2 (Kill Switch), Task 3.2.1
- **Affected Files:**
  - `src/core/risk/kill_switch.py` - _deactivation_code instance variable
  - `tests/unit/test_kill_switch.py` - Single-use code validation
- **References:** MVP scope boundaries, DEC-2026-01-15-004 (monolithic architecture)

---

### DEC-2026-02-12-005: Risk Check Pipeline Ordering (STRICT - DO NOT REORDER)
- **Decision:** Risk check pipeline runs in fixed order: (1) kill_switch → (2) daily_loss → (3) weekly_loss → (4) max_drawdown → (5) max_positions → (6) concentration → (7) position_size
- **Context:** Pipeline runs checks in order, stopping on first failure (fail-fast). Order matters: kill switch check should run first (safest rejection), expensive checks run later
- **Rationale:**
  - **Kill switch first** (immediate safety: if trading halted, reject all orders)
  - **Daily/weekly loss early** (common rejections, cheap to check, fail fast)
  - **Drawdown early** (accounts at risk, should reject before position checks)
  - **Max positions before concentration** (harder constraint, cheaper to check)
  - **Concentration before position size** (catches largest violations first)
  - **Fail-fast optimization** (expensive portfolio state built once, used for remaining checks)
  - **Deterministic behavior** (same order produces same results)
- **Alternatives Considered:**
  - **Parallel checks:** Rejected, complex coordination, non-deterministic ordering
  - **Different order:** Rejected, changes behavior, harder to reason about
  - **Lazy evaluation:** Rejected, doesn't provide fail-fast benefits
- **Status:** ACTIVE (LOCKED - DO NOT CHANGE)
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.1 (Risk Controller), Task 3.1.3
- **Affected Files:**
  - `src/core/risk/controller.py` - validate_order() method (lines 85-215)
  - `tests/unit/test_risk_controller.py` - Pipeline ordering tests
- **References:** DEC-2026-02-12-002 (pure function checks)

---

### DEC-2026-02-12-006: Three Position Sizing Methods (Fixed Risk, ATR, Kelly)
- **Decision:** Support three independent position sizing methods: (1) Fixed Risk % (default), (2) ATR-based (volatility-adjusted), (3) Kelly Criterion (probability-adjusted)
- **Context:** Different trading strategies need different sizing approaches. Must support all three without forcing traders into wrong method
- **Rationale:**
  - **Fixed Risk %:** Simplest, most common (size = (capital * risk%) / risk_per_unit)
  - **ATR-based:** Volatility-responsive (high volatility = smaller positions)
  - **Kelly Criterion:** For strategies with known win rate and avg win/loss
  - **Each method independent:** No forced conversions between methods
  - **Regime adjustment applied to all** (reduces size in volatile/ranging markets)
  - **Capital limits applied to all** (enforces 20% cash reserve, 10% emergency buffer)
- **Alternatives Considered:**
  - **Fixed risk only:** Rejected, ignores volatility and strategy characteristics
  - **Single unified method:** Rejected, no single method fits all strategies
  - **Many methods (10+):** Rejected, complexity/maintenance burden exceeds benefit
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.1 (Risk Controller), Task 3.1.4
- **Affected Files:**
  - `src/core/risk/sizing.py` - All three sizing functions
  - `src/core/risk/controller.py` - calculate_position_size() with method selection
  - `tests/unit/test_risk_controller.py` - Tests for all three methods
- **References:** PRD Section 3.1.4 (Position Sizing), DEC-2026-02-12-003 (sizing methods)

---

### DEC-2026-02-12-007: Regime Adjustments Pre-Sized (Not Post-Sized)
- **Decision:** Regime adjustments multiply raw position size BEFORE applying max_position_size_pct cap (not after)
- **Context:** In volatile/ranging regimes, should cap size at reduced level. If applying multiplier AFTER max cap, volatile regime adjustment becomes ineffective (already capped at max)
- **Rationale:**
  - **Volatile (0.5x multiplier):** 10k equity, max 5% = 500. After regime: 500 * 0.5 = 250 ✓
  - **If applied after cap:** Would cap at 500 first, then multiply = still 500 ✗
  - **Matching market conditions** (reduce size in bad conditions BEFORE hitting hard caps)
  - **Intuitive semantics** (regime adjustment = "reduce by this much")
- **Alternatives Considered:**
  - **Post-sizing (apply after cap):** Rejected, regime adjustment has no effect if already capped
  - **No regime adjustment:** Rejected, ignores market regime (PRD feature)
  - **Separate regime bucket:** Rejected, adds complexity
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.1 (Risk Controller), Task 3.1.4
- **Affected Files:**
  - `src/core/risk/controller.py` - calculate_position_size() applies adjustments pre-cap
  - `src/core/risk/sizing.py` - apply_regime_adjustment() called before max cap
- **References:** PRD Section 3.1.4, DEC-2026-02-12-006 (position sizing methods)

---

### DEC-2026-02-12-008: Test Coverage Threshold - 90% Per File (ALL MODULES)
- **Decision:** All risk control modules (controller, checks, sizing, kill_switch, dead_mans_switch, types) require ≥90% line coverage per file, with comprehensive edge case testing
- **Context:** Risk controls are mission-critical (prevent capital loss, halt trading). Untested code in these modules could cause production losses. Set high bar for coverage
- **Rationale:**
  - **90% minimum per file** (not just overall) ensures no weak files
  - **Edge cases tested:** NaN, Infinity, negative values, zero equity, zero capital
  - **All rejection paths covered** (each check's rejection case must be tested)
  - **All sizing methods exercised** (fixed risk, ATR, Kelly with valid/invalid inputs)
  - **Pipeline ordering verified** (tests confirm checks run in correct order)
  - **Non-negotiable for safety** (untested code in risk controls = unacceptable risk)
- **Alternatives Considered:**
  - **80% coverage:** Rejected, 20% gap in mission-critical code unacceptable
  - **Just unit test:** Rejected, need integration tests too (e.g., pipeline ordering)
  - **No coverage requirement:** Rejected, violates zero-technical-debt rules
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3 (Risk Controls), comprehensive test suites
- **Affected Files:**
  - `src/core/risk/*.py` - All modules maintain 90%+ coverage
  - `tests/unit/test_risk_controller.py` - 123 test cases, comprehensive coverage
  - `tests/unit/test_kill_switch.py` - 29 test cases for kill switch
- **References:** DEC-2026-02-09-002 (100% model test coverage), `.claude/rules/zero-technical-debt.md`

---

## Phase 3B Decisions (Circuit Breakers & Volatility Filter)

### DEC-2026-02-12-009: Circuit Breakers Are Stateful Classes (Not Pure Functions)
- **Decision:** Circuit breakers use ABC-based class hierarchy with persistent state, unlike the pure-function risk checks in `checks.py`
- **Context:** Existing checks (daily_loss, drawdown, etc.) are stateless pure functions. Circuit breakers need to track triggered/reset state across calls and persist across restarts
- **Rationale:**
  - **Stateful classes allow:** (1) tracking triggered timestamp, (2) auto-reset after cooldown, (3) persisting state to SystemState.circuit_breakers JSON field
  - **ABC provides consistent interface** (all breakers implement `check()`, `reset()`, `to_dict()`, `from_dict()`)
  - **Encapsulation of state** (each breaker manages its own triggered flag, cooldown timer)
  - **Testable via injectable `now` parameter** (no datetime mocking needed)
- **Alternatives Considered:**
  - **Pure functions with external state dict:** Rejected, loses encapsulation, state management scattered
  - **Async classes:** Rejected, breaks existing sync architecture (entire risk module is sync)
  - **Single monolithic CircuitBreakerChecker:** Rejected, violates SRP, harder to test individual breakers
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.3 (Circuit Breakers), Tasks 3.3.1-3.3.8
- **Affected Files:**
  - `src/core/risk/circuit_breakers.py` - ABC framework and 5 breaker implementations
  - `src/core/risk/controller.py` - Pipeline integration via CircuitBreakerManager
  - `tests/unit/test_circuit_breakers.py` - Comprehensive tests
- **References:** DEC-2026-02-12-001 (frozen dataclasses), DEC-2026-02-12-002 (pure function checks)

---

### DEC-2026-02-12-010: Circuit Breakers Complement Existing Pure Checks
- **Decision:** Circuit breakers and existing pure checks both run in the pipeline; they are complementary, not redundant
- **Context:** Both `check_daily_loss_limit()` (pure) and `DailyLossCircuitBreaker` (stateful) evaluate daily loss thresholds
- **Rationale:**
  - **Pure checks validate current values each cycle** (stateless, resets every call)
  - **Circuit breakers add persistent "tripped" state** that stays active until explicit reset/cooldown
  - **A breaker can block trading even after PnL improves** if cooldown hasn't elapsed
  - **Example:** Daily loss hits 5%, breaker trips with 60min cooldown. PnL recovers to 3%. Pure check would pass, but breaker stays tripped for remaining cooldown
  - **Defense in depth** (two independent mechanisms catch risk violations)
- **Alternatives Considered:**
  - **Replace pure checks with breakers:** Rejected, pure checks are simpler and always needed
  - **Only run one or the other:** Rejected, loses defense-in-depth benefit
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.3 (Circuit Breakers), Task 3.3.4
- **Affected Files:**
  - `src/core/risk/controller.py` - Both run in pipeline (breakers before pure checks)
- **References:** DEC-2026-02-12-002 (pure function checks), DEC-2026-02-12-005 (pipeline ordering)

---

### DEC-2026-02-12-011: VolatilityAnalyzer Accepts Pre-Computed Values
- **Decision:** VolatilityAnalyzer receives `volatility_pct` (ATR/price*100) as input rather than fetching market data
- **Context:** Keeping the risk module sync and free of I/O dependencies. Upstream data pipeline computes ATR; risk module only classifies and filters
- **Rationale:**
  - **No async market data fetching** (keeps risk module sync per existing architecture)
  - **Separation of concerns** (data pipeline computes, risk module evaluates)
  - **Testable without mocking HTTP calls** (just pass float values)
  - **Pre-computed values are cached** (DEC-2026-02-11-003 three-layer caching)
  - **Consistent with frozen dataclass inputs** (PortfolioState already provides pre-computed values)
- **Alternatives Considered:**
  - **VolatilityAnalyzer fetches market data directly:** Rejected, introduces async dependency, breaks sync architecture
  - **Pass raw OHLCV series:** Rejected, ATR calculation belongs in indicator module, not risk module
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.4 (Volatility Filter), Tasks 3.4.1-3.4.6
- **Affected Files:**
  - `src/core/risk/volatility.py` - Accepts volatility_pct float input
  - `src/core/risk/controller.py` - Passes pre-computed volatility to analyzer
- **References:** DEC-2026-02-11-003 (caching), DEC-2026-02-10-004 (async-first in data layer only)

---

### DEC-2026-02-12-012: Injectable Datetime for Time-Dependent Components
- **Decision:** All time-dependent classes (WeekendHolidayFilter, EventFilter, circuit breaker cooldowns) accept `now: datetime | None = None` parameter, defaulting to `datetime.now(timezone.utc)`
- **Context:** Enables deterministic testing without mocking `datetime.now()`, which is fragile and error-prone
- **Rationale:**
  - **Deterministic testing** (pass fixed datetime, get predictable results)
  - **No monkeypatching** (avoids fragile `unittest.mock.patch("datetime.datetime.now")`)
  - **Follows existing pattern** in codebase (KillSwitch uses similar approach internally)
  - **Timezone-aware by default** (DEC-2026-02-08-003 compliance)
  - **Simple API** (None means "use real time", explicit datetime for tests)
- **Alternatives Considered:**
  - **Mock datetime.now():** Rejected, fragile, doesn't work well with frozen dataclasses
  - **Clock abstraction class:** Rejected, over-engineering for this use case
  - **Fixed-time test fixtures only:** Rejected, doesn't allow testing time-dependent behavior
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.3-3.4 (Circuit Breakers + Volatility Filter)
- **Affected Files:**
  - `src/core/risk/circuit_breakers.py` - `check(now=...)` parameter
  - `src/core/risk/volatility.py` - `analyze(now=...)` parameter
  - `src/core/risk/time_filter.py` - `check(now=...)` parameter
  - `src/core/risk/event_filter.py` - `check(now=...)` parameter
- **References:** DEC-2026-02-08-003 (timezone-aware timestamps)

---

### DEC-2026-02-12-013: New Pipeline Checks Are Optional and Backward Compatible
- **Decision:** All new components (CircuitBreakerManager, VolatilityAnalyzer, WeekendHolidayFilter, EventFilter) are optional constructor parameters in RiskController, defaulting to None
- **Context:** Existing tests and consumers of RiskController must continue to work without modification
- **Rationale:**
  - **Backward compatible** (existing `RiskController(store, profile_manager)` calls unchanged)
  - **Gradual adoption** (components injected only when configured)
  - **No forced dependencies** (weekend filter not needed for crypto 24/7 trading)
  - **Testable in isolation** (each component tested independently before integration)
  - **Pipeline skips absent components** (if manager is None, circuit breaker check is skipped)
- **Alternatives Considered:**
  - **Required parameters:** Rejected, breaks all existing tests and consumers
  - **Configuration-driven activation:** Rejected, adds complexity, optional params are simpler
  - **Builder pattern:** Rejected, over-engineering for 4 optional components
- **Status:** ACTIVE
- **Date Decided:** 2026-02-12
- **Implemented By:** Section 3.3-3.4 (Circuit Breakers + Volatility Filter)
- **Affected Files:**
  - `src/core/risk/controller.py` - Constructor with optional parameters
  - All existing tests continue to pass without changes
- **References:** DEC-2026-02-12-005 (pipeline ordering), backward compatibility principles

---

## PHASE 4A: EXECUTION INFRASTRUCTURE

### DEC-2026-02-13-001: Order Submission Flow Sequence
**Decision:** Risk checks MUST run BEFORE database persistence, and orders MUST be persisted to database BEFORE submission to exchange

**Context:** Order submission has specific ordering requirements for data integrity and recoverability. The sequence of operations determines what happens on failures at each step.

**Rationale:**
- Risk checks are memory-only with no side effects, must run first to avoid creating orphaned records for rejected orders
- Database persistence BEFORE API submission ensures order safety - if API fails, we have a record to mark as REJECTED
- If order submitted to exchange but DB update fails, we lose synchronization between our records and exchange state
- Monitoring spawned as background task doesn't block submission completion

**Alternatives Considered:**
- Submit to exchange first: Rejected, could lose track of order if DB fails after successful submission
- Risk check after DB persist: Rejected, creates orphaned records for rejected orders, wastes DB operations
- No strict ordering: Rejected, race conditions and data integrity issues

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4A, Task 4.2.2
**Affected Files:**
  - `src/core/execution/order_manager.py` - submit_order() method implements 7-step sequence
**References:** SESSION_4A_IMPLEMENTATION_PROMPT.md lines 830-1032

**Implementation Details:**
```
STRICT SEQUENCE (CANNOT SKIP STEPS):
1. Risk Check    (memory, no side effects)
2. Create Record (memory only)
3. Persist DB    (first irreversible step)
4. Submit API    (can fail, but we have record)
5. Update DB     (persist submission)
6. Start Monitor (background tracking)

Key invariant: Order exists in DB before going to exchange
```

---

### DEC-2026-02-13-002: Order Status Polling with Exponential Backoff
**Decision:** Order monitoring uses three-tier exponential backoff: 1s (0-30s), 5s (30-300s), 10s (300s+), with max 1000 polls (~30 minutes)

**Context:** Market orders fill within seconds while limit orders may take minutes or hours. Need responsive polling without API spam or excessive costs.

**Rationale:**
- Fast detection critical for market orders which typically fill in 1-3 seconds
- Reasonable load for limit orders waiting for price targets
- Clean exit after 30 minutes prevents infinite polling on stuck orders
- Give up after 3 consecutive errors handles network issues gracefully
- Balances API rate limits, responsiveness, and server load

**Alternatives Considered:**
- Fixed 5s polling: Rejected, too slow for market orders (poor UX), too fast for long-waiting limits (API waste)
- No max poll limit: Rejected, could poll forever on stuck/forgotten orders
- WebSocket status updates: Deferred to V2, out of MVP scope
- Fibonacci backoff: Rejected, unnecessary complexity, linear tiers sufficient

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4A, Task 4.2.3
**Affected Files:**
  - `src/core/execution/order_manager.py` - _monitor_order() method
**References:** SESSION_4A_IMPLEMENTATION_PROMPT.md lines 1094-1261

**Implementation Details:**
```
Polling timeline:
0-30s:     Every 1 second (fast feedback for immediate fills)
30-300s:   Every 5 seconds (normal execution phase)
300s+:     Every 10 seconds (slow for limit orders waiting)
Max: 1000 polls (~30 minutes total) then give up
```

---

### DEC-2026-02-13-003: Bracket Order Atomic Submission
**Decision:** Bracket orders (entry + stop loss + take profit) submit as three separate API calls but are logically linked via parent_order_id field

**Context:** Binance Spot API doesn't support true OCO (One-Cancels-Other) bracket orders. Must submit individually and manage relationships in application layer.

**Rationale:**
- Binance Spot API limitation: No native bracket order support (Futures has it, but out of MVP scope)
- Must track parent-child relationship in application layer using parent_order_id foreign key
- On entry fill, SL/TP orders become active and start monitoring
- On SL or TP fill, system must cancel the other leg to prevent double exit
- Three separate submissions allow individual error handling per leg

**Alternatives Considered:**
- Wait for entry fill before submitting SL/TP: Rejected, exposes position to risk gap between fill and protective order placement
- Use Futures API which has native brackets: Rejected, out of MVP scope (crypto spot only)
- Single API call with manual OCO logic: Not possible with Binance Spot API
- Submit SL/TP as conditional orders: Rejected, adds complexity, not materially better

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4A, Task 4.2.5
**Affected Files:**
  - `src/core/execution/order_manager.py` - submit_bracket_order() method
  - `src/data/models.py` - Order.parent_order_id field
**References:** SESSION_4A_IMPLEMENTATION_PROMPT.md lines 1393-1487, TRADING_SYSTEM_PRD.md Section 3.4.3

---

### DEC-2026-02-13-004: Binance API Testnet vs Mainnet Switching
**Decision:** BinanceExecutionAdapter switches between testnet and mainnet via explicit `use_testnet: bool` constructor parameter, defaulting to testnet for safety

**Context:** Development requires testnet for safe testing, production requires mainnet for real trading. Must be explicit and validated to prevent accidental mainnet usage during development.

**Rationale:**
- Explicit flag prevents accidental mainnet usage during development (could lose real money)
- Defaults to testnet for safety - requires conscious choice to use mainnet
- Fail-fast on initialization if connection fails, making environment issues immediately visible
- Clear in logs which environment is active
- Simple boolean better than multiple environment strings

**Alternatives Considered:**
- Environment variable: Rejected, too implicit, easy to forget to set or misconfigure
- Separate classes (BinanceTestnetAdapter, BinanceMainnetAdapter): Rejected, unnecessary code duplication
- Auto-detect from API keys: Rejected, unclear behavior, API keys don't indicate environment
- Default to mainnet: Rejected, too dangerous for development

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4A, Task 4.1.1
**Affected Files:**
  - `src/brokers/binance/execution.py` - BinanceExecutionAdapter.__init__()
**References:** SESSION_4A_IMPLEMENTATION_PROMPT.md lines 323-351

**Implementation Details:**
```python
def __init__(
    self,
    binance_client: BinanceClient,
    symbol_manager: SymbolManager,
    use_testnet: bool = True  # Defaults to testnet for safety
):
    self.use_testnet = use_testnet
    self.base_url = TESTNET_URL if use_testnet else MAINNET_URL
```

---

### DEC-2026-02-13-005: Quantity and Price Rounding Strategy - Always Round Down
**Decision:** Always round DOWN quantity to step_size and price to tick_size (never round up) to avoid exceeding intended order size or available balance

**Context:** Binance enforces step size (quantity precision) and tick size (price precision). Rounding errors could exceed available balance or intended risk limits.

**Rationale:**
- Rounding UP quantity could exceed available balance, causing order rejection
- Rounding UP price on BUY orders gets worse fill; on SELL orders violates user expectations
- Rounding DOWN is consistently conservative across all scenarios
- Small rounding errors accumulate toward safety, not risk
- Prevents "insufficient balance" errors from rounding up
- Aligns with risk management principle: never take more risk than intended

**Alternatives Considered:**
- Round to nearest: Rejected, could round up and exceed limits or balances
- Round up: Rejected, violates conservative risk management, could exceed balance
- Banker's rounding (round to even): Rejected, too complex, no clear benefit, still rounds up 50% of the time
- No rounding (rely on exchange): Rejected, exchange rejects orders with wrong precision

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4A, Task 4.1.2
**Affected Files:**
  - `src/brokers/binance/execution.py` - _round_quantity(), _round_price()
**References:** SESSION_4A_IMPLEMENTATION_PROMPT.md lines 364-416

**Implementation Details:**
```python
# Round down to step size (quantity)
rounded_qty = (quantity // step_size) * step_size

# Round down to tick size (price)
rounded_price = (price // tick_size) * tick_size
```

---

## PHASE 4B: POSITION TRACKING & EXECUTION QUALITY

### DEC-2026-02-13-006: Position P&L Commission Handling
**Decision:** Commission is SUBTRACTED from unrealized P&L calculations to accurately reflect net profit/loss

**Context:** Binance charges commission on both entry and exit trades. P&L must account for all trading costs to provide accurate performance metrics.

**Rationale:**
- Commission is real cost that reduces net profit and must be included for accurate tracking
- Exit commission should be estimated and included in unrealized P&L (not just realized upon close)
- Both entry and exit commission reduce final realized P&L
- Overstating P&L by ignoring commission leads to false performance metrics
- Critical for strategy evaluation and risk management decisions

**Alternatives Considered:**
- Ignore commission: Rejected, leads to systematically overstated performance, false profit signals
- Only account on close (realized P&L): Rejected, unrealized P&L would be too optimistic, misleads operators
- Separate commission tracking: Rejected, P&L should be net of all costs for decision-making
- Estimate average commission rate: Considered but unnecessary, can get exact values from exchange

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4B, Task 4.3.2
**Affected Files:**
  - `src/core/execution/position_tracker.py` - calculate_unrealized_pnl(), calculate_realized_pnl()
**References:** SESSION_4B_IMPLEMENTATION_PROMPT.md lines 196-324

**Implementation Details:**
```python
# Unrealized P&L formula
unrealized_pnl = (current_price - entry_price) * quantity - total_commission_paid

# Example: Long position
# Entry: Bought 0.5 BTC @ $45,000 = $22,500 investment
# Entry commission: $5
# Current price: $46,000
# Estimated exit commission: $5
# Calculation:
#   unrealized = (46000 - 45000) * 0.5 - 5 - 5
#   unrealized = 500 - 10 = $490
```

---

### DEC-2026-02-13-007: Position Staleness Monitoring with Profitable Extension
**Decision:** Position staleness thresholds extended by 50% (1.5x multiplier) for profitable positions to "let winners run"

**Context:** PRD Feature K requires position staleness monitoring with different thresholds by strategy type. Need to balance closing stale positions while allowing profitable trades to develop.

**Rationale:**
- Winners should be given more time to develop (trading maxim: "let winners run")
- Losers should be reviewed/closed more aggressively (cut losses quickly)
- 50% extension is material but not excessive (balance between rules and flexibility)
- Profitable positions earning money justify longer hold time
- Prevents premature exit from strong trending positions
- Unprofitable positions signal strategy failure, warrant faster review

**Alternatives Considered:**
- No extension: Rejected, forces early exit of profitable trades, leaves money on the table
- 2x extension (100%): Rejected, too loose, positions could stay open too long even if trending
- Different thresholds per regime: Rejected, adds complexity without clear benefit
- Disable staleness monitoring for profitable: Rejected, still need maximum hold checks

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4B, Task 4.3.5a
**Affected Files:**
  - `src/core/execution/position_tracker.py` - PositionStalenessMonitor.check_staleness()
**References:** SESSION_4B_IMPLEMENTATION_PROMPT.md lines 497-583, TRADING_SYSTEM_PRD.md Feature K

**Implementation Details:**
```python
THRESHOLDS = {
    'day_trading': {
        'warning_hours': 24,
        'max_hold_hours': 72
    },
    'swing_trading': {
        'warning_days': 7,
        'max_hold_days': 30
    }
}

# Profitable Position Extension:
if position.unrealized_pnl > 0:
    threshold *= 1.5  # Extend by 50%
```

---

### DEC-2026-02-13-008: Pre-Trade Slippage Estimation Model
**Decision:** Slippage estimated as sum of four components: base (0.05%), size factor, volatility factor, and spread factor, with thresholds at 0.3% (warn) and 1.0% (block)

**Context:** PRD Feature F requires pre-trade slippage estimation to warn or block orders with excessive expected slippage. Need accurate model that adapts to market conditions.

**Rationale:**
- Base slippage (0.05%) accounts for minimum market impact on any market order
- Size factor penalizes large orders relative to average volume (prevents market moving orders)
- Volatility factor adjusts for current market conditions (ATR-based)
- Spread incorporated directly (empirically, average slippage is approximately half the spread)
- Conservative thresholds prevent excessive slippage: 0.3% material warning, 1.0% blocks order
- Multi-component model more accurate than single fixed estimate

**Alternatives Considered:**
- Fixed slippage estimate (e.g., 0.1%): Rejected, ignores order size and market conditions, inaccurate
- Historical average only: Rejected, doesn't adapt to current volatility or order size
- Machine learning model: Deferred to V2, out of MVP scope, requires training data
- Volume-weighted only: Rejected, misses volatility and spread components

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4B, Task 4.4.1
**Affected Files:**
  - `src/core/execution/quality.py` - SlippageEstimator.estimate_slippage()
**References:** SESSION_4B_IMPLEMENTATION_PROMPT.md lines 745-798, TRADING_SYSTEM_PRD.md Feature F

**Implementation Details:**
```
Components:
- base_slippage = 0.05% (minimum for market orders)
- size_factor = (order_size / avg_daily_volume) * 0.5%
- volatility_factor = (current_ATR / avg_ATR) * 0.1%
- spread_factor = current_spread / 2

Total estimated slippage = base + size + volatility + spread

Thresholds:
- WARN if > 0.3% (material but acceptable)
- BLOCK if > 1.0% (excessive, likely to regret)
```

---

### DEC-2026-02-13-009: Position Sync via Balance Reconciliation
**Decision:** Position synchronization on Binance Spot done via balance comparison (not position API, which doesn't exist for Spot) to detect external trades or discrepancies

**Context:** Binance Spot doesn't have native "positions" like Futures. Must reconcile positions via asset balances to detect manual trades or system errors.

**Rationale:**
- Spot trading: positions = asset balances (no separate position tracking in exchange)
- No dedicated position query API for Spot (unlike Futures)
- Balance is source of truth from exchange perspective
- Must reconcile regularly to catch external trades (manual trading) or system errors
- Detects quantity mismatches, missing positions, or unexpected holdings

**Alternatives Considered:**
- Trust local state only: Rejected, loses sync if manual trades or system errors occur
- Query trade history and reconstruct: Rejected, expensive API calls, complex logic, pagination issues
- Use Futures API positions: Rejected, out of MVP scope (Spot only)
- No synchronization: Rejected, could diverge significantly from reality

**Status:** ACTIVE
**Date Decided:** 2026-02-13
**Implemented By:** Phase 4B, Task 4.3.5
**Affected Files:**
  - `src/core/execution/position_tracker.py` - sync_positions()
**References:** SESSION_4B_IMPLEMENTATION_PROMPT.md lines 448-494

**Implementation Details:**
```
For each open position in local state:
1. Get exchange balance for position.symbol (base asset)
2. Expected balance = position.quantity
3. Actual balance = exchange.get_balance(symbol)
4. If mismatch:
   - Log discrepancy warning
   - Update position.quantity = actual_balance
   - Mark position for operator review
```

---

## PHASE 5A: STRATEGY FOUNDATION

### DEC-2026-02-14-001: Strategy Status Lifecycle State Machine
**Decision:** Strategy status transitions follow strict state machine with only forward progression (except BACKTEST → DRAFT on failure), enforcing validation phases before live trading

**Context:** Strategies must progress through validation phases (backtest → paper trading → live) before risking real capital. Need to prevent skipping safety checks.

**Rationale:**
- Enforces validation progression: backtest → paper → live (no shortcuts)
- Prevents skipping safety checks which could lead to untested strategies trading live
- RETIRED is terminal state (can't un-retire) for audit trail integrity
- Only BACKTEST can go backward (to DRAFT for fixes) - reasonable iteration cycle
- Clear state progression makes behavior predictable and enforceable
- Operator can pause at any stage but can't skip forward

**Alternatives Considered:**
- Allow skipping validation phases: Rejected, too risky, undermines safety philosophy
- Allow backward transitions generally: Rejected, unclear semantics, audit trail issues
- No state machine (free-form status): Rejected, too easy to misuse, no enforcement
- Allow RETIRED → DRAFT reuse: Rejected, name reuse could confuse audit trails

**Status:** ACTIVE
**Date Decided:** 2026-02-14
**Implemented By:** Phase 5A, Task 5.1.2
**Affected Files:**
  - `src/core/strategy/engine.py` - transition_status() with validation logic
  - `src/data/models.py` - StrategyStatus enum
**References:** SESSION_5A_IMPLEMENTATION_PROMPT.md lines 38-576, TRADING_SYSTEM_PRD.md Section 3.3

**Implementation Details:**
```
State Machine Allowed Transitions:
DRAFT → BACKTEST → SIMULATED_PAPER → LIVE_PAPER → PENDING_APPROVAL → LIVE
                ↓
              DRAFT (backtest failure only)

Any state → PAUSED (manual/auto)
LIVE → UNDERPERFORMING (auto-detected)
Any state → RETIRED (terminal, irreversible)

DISALLOWED:
- BACKTEST → LIVE (skip paper trading)
- DRAFT → LIVE (skip all validation)
- RETIRED → Any (terminal state)
- Any backward moves except BACKTEST → DRAFT
```

---

### DEC-2026-02-14-002: Strategy Similarity Threshold (70%)
**Decision:** Reject new strategies that are >70% similar to existing active strategies using weighted similarity scoring across template, parameters, symbols, and entry logic

**Context:** PRD Feature D prevents strategy cloning which doesn't add diversification and could amplify correlated losses.

**Rationale:**
- 70% threshold balances avoiding clones while allowing reasonable variations
- Template type most important (40% weight) - different templates have fundamentally different behavior
- Parameters second (30% weight) - allows tuning same template with different risk profiles
- Symbol overlap (20% weight) - trading same assets increases correlation
- Entry logic least weighted (10%) - mostly covered by template matching
- Prevents running 5 nearly-identical EMA strategies on BTC (concentrates risk)
- Forces genuine diversification across templates, symbols, or parameters

**Alternatives Considered:**
- 50% threshold: Rejected, too strict, blocks reasonable variations of same template
- 90% threshold: Rejected, too loose, allows near-clones that don't add diversification
- No similarity check: Rejected, violates PRD Feature D, allows dangerous concentration
- Only check template ID: Rejected, same template with different params can be very different

**Status:** ACTIVE
**Date Decided:** 2026-02-14
**Implemented By:** Phase 5A, Task 5.1.2
**Affected Files:**
  - `src/core/strategy/engine.py` - StrategySimilarityChecker class
**References:** SESSION_5A_IMPLEMENTATION_PROMPT.md lines 248-490, TRADING_SYSTEM_PRD.md Feature D

**Implementation Details:**
```
Similarity Score = weighted_sum of:
- same_template_id: +40% (most important)
- param_distance < 20%: +30% (second most important)
- symbol_overlap > 50%: +20% (correlation factor)
- same_entry_conditions: +10% (least important)

REJECTION RULE: Reject if total_similarity > 70%
```

---

### DEC-2026-02-14-003: Market Regime Manual Tagging with Size Reduction
**Decision:** Market regime set manually by operator via API/dashboard. On regime mismatch (not in strategy.preferred_regimes), reduce position size by 50%. Block trading if in strategy.avoid_regimes.

**Context:** PRD Feature B requires manual regime tagging with strategy adaptation. Operators have market expertise to classify regimes, strategies perform differently in different regimes.

**Rationale:**
- 50% size reduction is material enough to reduce risk without fully blocking trading
- Operator control leverages human expertise (automated detection is V2 feature)
- Simple three-way logic: preferred (1.0x), mismatch (0.5x), avoid (0.0x)
- Persists across restarts (DB-backed) for consistency
- Allows strategies to continue in suboptimal conditions but with reduced risk
- Complete block on avoid_regimes prevents strategies from trading in their worst conditions

**Alternatives Considered:**
- Automated regime detection: Deferred to V2, out of MVP scope, requires ML/indicators
- 25% size reduction: Rejected, not material enough to meaningfully reduce risk
- 75% size reduction: Rejected, too severe, nearly equivalent to blocking
- Block on mismatch: Rejected, too restrictive, strategies should adapt not stop
- No size adjustment: Rejected, violates PRD Feature B adaptation requirement

**Status:** ACTIVE
**Date Decided:** 2026-02-14
**Implemented By:** Phase 5A, Task 5.1.3
**Affected Files:**
  - `src/core/strategy/regime.py` - MarketRegimeManager class
  - `src/data/models.py` - MarketRegime enum, Strategy.preferred_regimes, Strategy.avoid_regimes
**References:** SESSION_5A_IMPLEMENTATION_PROMPT.md lines 589-827, TRADING_SYSTEM_PRD.md Feature B

**Implementation Details:**
```python
MISMATCH_SIZE_REDUCTION = 0.5  # 50% reduction

class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

Logic:
- If current in strategy.avoid_regimes: size_multiplier = 0.0 (block)
- Elif current in strategy.preferred_regimes: size_multiplier = 1.0 (full)
- Elif UNKNOWN: size_multiplier = 1.0 (operator aware, allow)
- Else (mismatch): size_multiplier = 0.5 (reduce)
```

---

### DEC-2026-02-14-004: Template Parameter Validation with Cross-Field Rules
**Decision:** Strategy parameters validated against template specification including type, bounds, step size, enums, AND cross-parameter validation rules (e.g., slow_ma > fast_ma + 5)

**Context:** Invalid parameters lead to runtime errors or nonsensical strategies. Need comprehensive validation before strategy creation or backtesting.

**Rationale:**
- Type checking prevents runtime errors from wrong types (str instead of int)
- Bounds validation prevents nonsensical values (negative periods, >100% allocations)
- Step size ensures UI increment logic matches backend validation
- Enum validation ensures only allowed choices (prevents typos)
- Cross-field rules catch logical conflicts (slow MA faster than fast MA)
- Validates BEFORE expensive operations like backtest (fail fast principle)

**Alternatives Considered:**
- Validation at runtime only: Rejected, fails too late, wastes computation on invalid configs
- No cross-field validation: Rejected, allows logical conflicts like slow_ma=20, fast_ma=50 (backward)
- Pydantic models for all parameters: Considered for V1, YAML + explicit validation sufficient for MVP
- Lenient validation (warnings only): Rejected, invalid parameters should be hard errors

**Status:** ACTIVE
**Date Decided:** 2026-02-14
**Implemented By:** Phase 5A, Task 5.1.1
**Affected Files:**
  - `src/core/strategy/engine.py` - _validate_parameters() method
  - `config/templates/*.yaml` - validation_rules section in each template
**References:** SESSION_5A_IMPLEMENTATION_PROMPT.md lines 156-245

**Implementation Details:**
```yaml
# In template YAML:
validation_rules:
  - "fast_ema_period < slow_ema_period"  # Cross-field
  - "min_difference: slow_ema_period - fast_ema_period >= 5"  # Computed

parameters:
  fast_ema_period:
    type: "integer"    # Type validation
    min: 5            # Bounds validation
    max: 20
    step: 1           # Step size validation
    
  entry_mode:
    type: "enum"      # Enum validation
    choices: ["aggressive", "conservative"]
```

---

### DEC-2026-02-15-001: Synchronous Simulation for Paper Trading
- **Decision:** PaperTradingEngine runs synchronously for SIMULATED mode (historical replay) but uses async polling for LIVE mode
- **Context:** Paper trading has two modes: SIMULATED (replays historical data) and LIVE (polls real-time data). The execution model should match the workload type.
- **Rationale:** Simulating 21 days of historical data asynchronously would be unnecessarily slow. CPU-bound sequential replay should be blocking/synchronous to maximize throughput. LIVE mode genuinely benefits from async I/O for polling.
- **Alternatives Considered:**
  - Fully async for both modes: Rejected - async overhead on CPU-bound replay is wasteful
  - Fully sync for both modes: Rejected - LIVE mode needs non-blocking I/O for polling
- **Status:** ACTIVE
- **Date Decided:** 2026-02-15
- **Implemented By:** Phase 5B - Paper Trading Engine
- **Affected Files:** `src/core/strategy/paper/`
- **References:** TRADING_SYSTEM_PRD.md Feature J (Paper Trading)

---

### DEC-2026-02-15-002: Regime Persistence via SystemState JSON Field
- **Decision:** Market regimes are stored in `SystemState.circuit_breakers["market_regimes"]` JSON field
- **Context:** The MarketRegimeManager needs to persist regime state per symbol across restarts. DEC-2026-02-14-003 established manual regime tagging but did not specify the persistence mechanism.
- **Rationale:** Using the existing SystemState singleton's `circuit_breakers` JSON field avoids schema migration for MVP. The field already exists, is JSON-typed, and the SystemState singleton pattern ensures single-writer consistency.
- **Alternatives Considered:**
  - New database column on Account model: Rejected - requires schema migration
  - New RegimeState table: Rejected - over-engineering for MVP (only 3 symbols)
  - Config file: Rejected - not suitable for runtime updates
- **Status:** ACTIVE
- **Date Decided:** 2026-02-15
- **Implemented By:** Phase 5B - Market Regime Manager
- **Affected Files:** `src/core/strategy/regime.py`, `src/data/models/system.py`
- **References:** DEC-2026-02-14-003 (Manual Regime Tagging)

---

## Phase 6 Gap-Fix Decisions (PRD Completeness Pass — 2026-02-22)

### DEC-2026-02-22-001: Portfolio Correlation Limits via Pre-Trade Check Function
- **Decision:** Portfolio-level asset exposure limits (BTC 40%, ETH 30%, total correlated long 60%) are enforced as a pure pre-trade check function `check_portfolio_correlation()` in `checks.py`, and as a stateful `CorrelationCircuitBreaker` in `circuit_breakers.py`.
- **Context:** PRD §2.2.1 Feature A requires cross-strategy exposure caps. The previous `CorrelationCircuitBreaker` only checked for duplicate symbols, not actual percentage exposure.
- **Rationale:**
  - Pure function approach matches the existing checks.py pattern (no side effects, composable, testable).
  - Stateful circuit breaker provides auto-trip/reset semantics for sustained limit breaches.
  - Running both gives defense-in-depth: pre-trade blocks orders; circuit breaker halts the symbol if sustained.
- **Alternatives Considered:**
  - Circuit breaker only: Rejected — circuit breakers are stateful and persist; pre-trade check needed for per-order accuracy.
  - Pre-trade check only: Rejected — no persistent alert if sustained overexposure builds up.
- **Status:** ACTIVE
- **Date Decided:** 2026-02-22
- **Implemented By:** PRD Gap Fix Session (checks.py + circuit_breakers.py)
- **Affected Files:** `src/core/risk/checks.py`, `src/core/risk/circuit_breakers.py`, `src/core/risk/controller.py`
- **References:** PRD §2.2.1 Feature A

### DEC-2026-02-22-002: Underperformance Auto-Transition Stored in live_results JSON
- **Decision:** The underperformance condition tracking timestamps (when each PRD §3.5 condition was first detected) are stored in `strategy.live_results["underperformance_tracking"]` JSON field rather than a dedicated database column.
- **Context:** PRD §3.5 requires automatic transition to UNDERPERFORMING when win rate drops 15%+ for 14 days, Sharpe < 0.5 for 30 days, or expectancy < 50% of backtest for 21 days. Tracking "how long has this been failing" requires persisting timestamps.
- **Rationale:**
  - `live_results` is already a flexible JSON column on Strategy that is written/read by the orchestrator.
  - Adding a new database column would require an Alembic migration with enum changes.
  - The tracking data is only meaningful while the strategy is LIVE — JSON co-location with other live metrics is natural.
  - The `underperformance_tracking` sub-dict is ephemeral metadata, not a first-class domain concept.
- **Alternatives Considered:**
  - New `underperformance_tracking` database columns: Rejected — migration risk, premature schema expansion.
  - Separate `UnderperformanceRecord` table: Rejected — over-engineering for MVP.
- **Status:** ACTIVE
- **Date Decided:** 2026-02-22
- **Implemented By:** PRD Gap Fix Session (engine.py + orchestrator.py)
- **Affected Files:** `src/core/strategy/engine.py`, `src/core/orchestrator.py`, `src/data/models/strategy.py`
- **References:** PRD §3.5

---

### DEC-2026-02-22-003: Two-Tier Backtest Validation Thresholds (E. Chan Framework)
- **Decision:** Replace the single hardcoded ValidationThresholds with two named presets — SUPERVISED_THRESHOLDS (Tier-1, default) and AUTOMATED_THRESHOLDS (Tier-2) — and add Expectancy and Calmar ratio checks. Default constructor now returns Tier-1 (Supervised) values.
- **Context:** The original validator used five checks with thresholds copied from the PRD without consulting strategy-type norms. Three problems were identified:
  1. min_win_rate_pct=50% rejects ALL trend-following templates (donchian_atr, bb_squeeze_breakout) which are designed to operate at 35-45% win rates. Both templates declare min_win_rate_pct=40-42% in their own YAML but the validator rejected them at 50%.
  2. min_num_trades=100 makes 30-day backtests on 1H timeframe mathematically impossible (typical yield: 48-90 trades). Required 90-120 day backtests to hit threshold.
  3. No Expectancy or Calmar check despite both metrics already being computed in BacktestMetrics. These are more informative quality gates than win rate.
- **Rationale:**
  - E. Chan ("Quantitative Trading", 2008) states win rate is "a psychological comfort metric" with no standalone meaning without the win/loss ratio. Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss) makes win rate redundant as a check.
  - E. Chan's minimum trade count for statistical validity is 45 (central limit theorem floor). 30 is the bare minimum. 100 is excessive for MVP validation.
  - Two tiers match the two operational phases: manual oversight (now) and full automation (target). Thresholds should reflect the degree of human protection in the loop.
  - Calmar ratio (annualized_return / max_drawdown) measures whether returns justify the drawdown experienced. Automated strategies must cover their own drawdown without a human stepping in.
  - Profit factor raised from 1.3 to 1.5 in Tier-2 to compensate for the relaxed win rate requirement.
- **Tier-1 SUPERVISED_THRESHOLDS (default, current phase):**
  - min_sharpe_ratio: 0.5
  - max_drawdown_pct: 25.0
  - min_win_rate_pct: 0.0  (disabled — expectancy is the gate)
  - min_profit_factor: 1.35
  - min_num_trades: 30
  - min_expectancy: 0.01  (any positive expectancy)
  - min_calmar_ratio: 0.0  (disabled — human oversight provides protection)
- **Tier-2 AUTOMATED_THRESHOLDS (use when promoting to live automated):**
  - min_sharpe_ratio: 1.0
  - max_drawdown_pct: 15.0
  - min_win_rate_pct: 35.0  (permits trend strategies; blocks genuinely broken ones)
  - min_profit_factor: 1.5
  - min_num_trades: 60
  - min_expectancy: 10.0  ($10 avg profit/trade on $10K capital)
  - min_calmar_ratio: 1.0  (annual return must cover max drawdown)
- **Alternatives Considered:**
  - Keep win_rate=50%: Rejected — internally contradicts template YAML files (donchian min_win_rate_pct=40%, bb_squeeze=42%). Would permanently block two of seven templates.
  - Keep min_num_trades=100: Rejected — makes 30-day 1H backtests impossible, forcing unnecessarily long validation windows.
  - Single threshold set: Rejected — conflates manually-supervised and fully-automated risk profiles. Human oversight is a meaningful safety layer that should relax automated thresholds.
  - Per-template thresholds: Rejected — adds complexity. Two tiers (supervised vs automated) cover the operational phases clearly.
- **Status:** ACTIVE
- **Date Decided:** 2026-03-11
- **Implemented By:** Session — validator.py refactor
- **Affected Files:**
  - `src/core/strategy/backtest/validator.py` — ValidationThresholds, SUPERVISED_THRESHOLDS, AUTOMATED_THRESHOLDS, BacktestValidator.validate()
  - `tests/unit/backtest/test_validator.py` — 40 tests covering both tiers, all 7 checks, boundary conditions
- **References:** E. Chan "Quantitative Trading" (2008) Ch.3, "Algorithmic Trading" (2013) Ch.2

---

### DEC-2026-05-17-001: Short Position Cash Settlement Fix in PortfolioState

- **Decision:** On `close_position`, return `pos.entry_price * pos.quantity + pos.entry_commission + realized_pnl` to cash instead of the direction-blind `pos.quantity * fill_price - commission`.
- **Context:** The original proceeds formula treated SHORT closes identically to LONG closes — crediting `exit_price × qty` back to cash. For a LONG this is correct (you sold the asset at exit price). For a SHORT, the collateral deposited was `entry_price × qty`; using `exit_price` inverts the settlement direction, making profitable shorts drain cash and losing shorts inflate it.
- **Rationale:**
  - The new formula reduces algebraically to the old one for LONG positions (no regression).
  - Net cash change after any trade (both directions) is now exactly `realized_pnl`, which is the correct invariant.
  - The equity curve (used for Sharpe, drawdown) was wrong between trades for SHORT-heavy strategies; this fix corrects those metrics.
  - `realized_pnl` was already computed correctly using a direction-aware formula (lines 237–245); only the cash-return was wrong.
- **Alternatives Considered:**
  - Direction-specific `if/else` block for proceeds: correct but verbose; the unified formula is equivalent and cleaner.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-17
- **Implemented By:** Bug fix — `close_position` in `PortfolioState`
- **Affected Files:**
  - `src/core/strategy/backtest/portfolio.py` — `close_position` lines 251-256
  - `tests/unit/backtest/test_portfolio.py` — added `test_cash_accounting_roundtrip_short_win` and `test_cash_accounting_roundtrip_short_loss`
- **References:** Confirmed against 10 days of live paper trading data (Neon DB) — LONG sessions had zero discrepancy; all SHORT sessions had systematic cash errors proportional to realized_pnl magnitude.

### DEC-2026-05-27-001: Live Trading Kill Switch — Fail-Closed Default

- **Decision:** `scripts/run_all.py` only spawns `run_live_trading` when the `LIVE_TRADING_ENABLED` env var is explicitly truthy (`true`/`1`/`yes`/`on`). Paper trading always runs; live is opt-in.
- **Context:** Diagnostic on Neon DB on 2026-05-27 revealed BTF (the live-deployed strategy) is showing live paper PF=0.75 across 25 trades — a clear negative edge in the current bear regime, despite Q1 backtests claiming 100% WR / Sharpe 2.4-3.6. Continuing live operation under these conditions would compound losses on real capital, and the expansion-tier mechanism would scale up the same negative-edge signal.
- **Rationale:**
  - **Fail-closed default**: if all Railway env vars are wiped or misconfigured, live trading does NOT silently resume. The opposite (default-on with a disable flag) makes the dangerous mode the easy mode.
  - **Paper continues unmodified**: keeps generating the dataset needed to re-validate strategies without risking real capital.
  - **Reversible**: re-enable by setting one env var on the Railway dashboard — no code change required.
- **Alternatives Considered:**
  - Comment out the live entry point: rejected — easy to forget to revert, no audit trail in env vars.
  - Delete `run_live_trading.py`: rejected — preserves the work; we want it re-runnable when paper proves an edge.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-27
- **Implemented By:** `scripts/run_all.py` (`_live_enabled()` + dynamic SCRIPTS list).
- **Affected Files:**
  - `scripts/run_all.py`

### DEC-2026-05-27-002: Drop DOTUSDT from BTF Basket

- **Decision:** Remove `DOTUSDT` from `BEAR_STRATEGY_CONFIG["bear_trend_follower"]["symbols"]`. BTF now trades 7 symbols (BTC, ETH, BNB, SOL, XRP, AVAX, DOGE).
- **Context:** Live paper data shows BTF/DOTUSDT lost -$171 across 3 trades = **-$57 per trade average**, the worst per-symbol outcome in the entire portfolio. By comparison, BTF/AVAXUSDT under identical parameters produced +$73 over 7 trades. DOT's wider effective spreads + thinner liquidity make the 2.5× ATR stop especially vulnerable to intrabar whipsaws.
- **Rationale:**
  - Per-symbol outlier — removing DOT would have changed BTF basket from -$189 to ~-$18 over the same window.
  - DOT trades on the same signal as other symbols, so the basket loses diversification but the diversification was negatively correlated (it added losses, not buffered them).
  - Decision is reversible once we have evidence that the stop is appropriate for DOT's microstructure.
- **Alternatives Considered:**
  - Widen the stop only for DOT: rejected — would require per-symbol stop tuning that isn't in the strategy interface and would mask the underlying microstructure issue.
  - Move DOT to a different strategy (mean-reversion): possible future work; out of scope here.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-27
- **Implemented By:** `scripts/run_paper_trading.py` — comment + symbol list edit in `BEAR_STRATEGY_CONFIG`.
- **Affected Files:**
  - `scripts/run_paper_trading.py`
  - `scripts/backtest_btf_may2026.py` (diagnostic script using the 7-symbol list)

### DEC-2026-05-27-003: Consecutive-Failure Threshold for Live Error Alerts

- **Decision:** The live trading loop only sends a Telegram "Live Trading Error" alert after 3 consecutive failed polls (the first 2 are logged only). On recovery, an explicit "Live Trading Recovered" alert is sent.
- **Context:** A single Binance API read-timeout was firing an ERROR-level Telegram alert at 3:30 AM despite the loop self-healing on the next poll. This is alert noise that erodes trust in the alerts that actually matter.
- **Rationale:**
  - 3 consecutive failures ≈ 3 minutes of real problems (at 60 s poll interval) — a meaningful threshold for "something is genuinely wrong" (e.g. API key revoked, Binance outage, key permission change).
  - Boundary-crossing alert: only fires when crossing N==3, not on every subsequent failure — prevents alert storms during longer outages.
  - Recovery alert closes the loop so the operator knows the system is healthy again.
- **Alternatives Considered:**
  - Time-based debounce (e.g. "no more than 1 alert per 30 min"): rejected — counts failures more directly than time.
  - Severity downgrade for first failure: rejected — INFO-level alerts would still ping Telegram.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-27
- **Implemented By:** `consecutive_failures` counter + threshold logic in `main()` poll loop.
- **Affected Files:**
  - `scripts/run_live_trading.py`

### DEC-2026-05-27-004: Promotion Gate — Paper-to-Live Classification Thresholds

- **Decision:** Establish the canonical promotion gate. A live paper trading session is classified as:
  - **READY_FOR_LIVE** — N >= 30 trades AND PF >= 1.35 AND Sharpe (per-trade) >= 1.0 AND MaxDD <= 5% of session capital
  - **OBSERVING** — N >= 10 AND PF >= 1.0 (not enough confidence, but not bleeding)
  - **DEGRADED** — N >= 10 AND PF < 0.8 (live capital must not touch this template)
  - **RESEARCH** — otherwise (insufficient sample)
- **Context:** BTF was promoted to live trading on the basis of Q1 2026 backtests (claimed 100% WR / Sharpe 2.4-3.6). May 2026 live paper showed PF=0.75 across 25 trades — a 50%+ degradation that nothing in the existing code would have caught. The promotion process needs an explicit numeric gate that any strategy must clear before live capital can flow to it.
- **Rationale:**
  - N >= 30 is the minimum sample where per-trade Sharpe stabilises enough to mean something for crypto 1H strategies.
  - PF >= 1.35 is the SUPERVISED threshold already used in backtesting — keeps backtest and live-paper gates aligned.
  - Sharpe >= 1.0 (per-trade) filters out high-PF/low-frequency or high-PF/high-variance strategies that aren't safe to scale.
  - MaxDD <= 5% of session capital is the equity-protection rail; anything worse means a single bad week could wipe out >$1 per $20 of live capital.
  - DEGRADED at PF < 0.8 (not 1.0) leaves a small "OBSERVING" buffer between healthy and demoted so noise doesn't flap classifications.
- **Alternatives Considered:**
  - Calendar-based (e.g. "30 days minimum"): rejected — trade count is the statistical signal, not time.
  - Single-metric gate (e.g. just PF): rejected — PF can be inflated by one big winner; combo gate is more honest.
  - Manual override via memory file: rejected — that's what failed for BTF.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-27
- **Implemented By:** `scripts/validation_report.py` (`PROMOTION_GATE` dict + `_classify()`), enforced at tier activation time by `_paper_strategy_is_degraded()` in `run_live_trading.py`.
- **Affected Files:**
  - `scripts/validation_report.py`
  - `scripts/run_live_trading.py`

### DEC-2026-05-27-005: Rolling-Window Validation Requirement

- **Decision:** New strategy promotions to paper trading MUST pass a rolling-window backtest (default: 4 non-overlapping 30-day windows). The strategy is classified by PF stability: STABLE_EDGE (median PF >= 1.35, CV < 0.30, min PF >= 1.0), PROMISING, MARGINAL, OVERFIT_OR_BROKEN, INSUFFICIENT.
- **Context:** BTF's Q1 backtest hit 100% WR / Sharpe 2.4-3.6 on one specific window and was promoted on that basis alone. Live paper shows PF=0.75 in May. This is the textbook overfitting failure mode. A single-window backtest cannot distinguish "real edge" from "lucky window."
- **Rationale:**
  - 4 windows × 30 days = ~120 days total exposure across multiple regime states.
  - Coefficient of variation (CV) penalises strategies whose PF swings wildly between windows even if the mean is acceptable.
  - Minimum-PF floor protects against "one great window" averaging out several losers.
  - Cheap to run (`scripts/backtest_rolling.py` reuses the existing engine).
- **Alternatives Considered:**
  - Walk-forward optimization (Anchor + roll): better but heavier. This is a lighter gate that catches the most common overfit failure.
  - Single OOS holdout: insufficient — one OOS window is still one window.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-27
- **Implemented By:** `scripts/backtest_rolling.py`.
- **Affected Files:**
  - `scripts/backtest_rolling.py`

### DEC-2026-05-27-006: Decorrelation Cap on Same-Direction Live Positions

- **Decision:** The live engine refuses to open a new position if `MAX_CONCURRENT_SAME_DIRECTION` (default 4) tiers already hold an open position in that direction. Configurable via env var.
- **Context:** On 2026-05-23 20:00 UTC, 5 BTF-short sessions stopped out simultaneously for ~$395 of realised loss in a single hour. The basket appeared diversified (7 symbols) but they were really one signal with symbol substitutions — when the bear-trend assumption broke, all 7 took the same hit. A cap on concurrent same-direction positions bounds the worst-case correlated bleed.
- **Rationale:**
  - 4-position cap reduces correlated-stop blast from ~$395 to ~$315 in retrospect; tighter caps would be too restrictive.
  - Direction-aware (LONG vs SHORT) so the cap doesn't trigger when one strategy is LONG and another SHORT.
  - Configurable via env var so it can be tuned without redeploy when more data arrives.
  - Block-only on entry — exits and stop closes still execute unconditionally (the cap protects against new exposure, not from managing existing risk).
- **Alternatives Considered:**
  - Cap based on aggregate USDT exposure: harder to reason about with multi-symbol baskets at different prices.
  - Per-strategy-template cap (e.g. max 3 BTF positions): more nuanced but requires knowing which templates are correlated; this simpler rule is regime-agnostic.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-27
- **Implemented By:** `_count_open_same_direction()` + entry-path check in `_process_tier()`.
- **Affected Files:**
  - `scripts/run_live_trading.py`

### DEC-2026-05-27-008: Regime-Aware Backtest Validation + Strategy Tagging

- **Decision:** Introduce a fine-grained regime taxonomy (`SubRegime` enum with 8 values: TRENDING_BULL, CHOPPY_BULL, TRENDING_BEAR, CHOPPY_BEAR, RANGING, HIGH_VOL, TRANSITIONAL, UNKNOWN) and a corresponding `HistoricalRegimeClassifier` that walks any OHLCV series and labels every bar. Each strategy now declares `regime_tags: list[str]` in its config, naming the SubRegimes it claims to work in. The rolling backtest classifies each window's dominant regime (from BTC daily) and reports per-regime metrics, enabling the diagnostic "STABLE_EDGE_IN_REGIME" vs "POOR_IN_REGIME" distinction.
- **Context:**
  - The existing `RegimeState` enum (4 macro states + UNKNOWN) is too coarse for strategy classification. It tells you "we're in a bear" but not "this is a trending bear vs. a choppy bear."
  - BTF's promotion-then-failure illustrates the problem: Q1 was TRENDING_BEAR (BTF worked) and May has been CHOPPY_BEAR (BTF fails). The old taxonomy treats both as just "bear" and can't surface the distinction.
  - Without regime-aware validation, the rolling backtest could only say "this strategy's PF varies a lot across windows" — leaving it ambiguous whether the strategy has a real regime-specific edge or is just curve-fit noise.
- **Taxonomy (precedence order; a bar matches exactly one):**
  1. UNKNOWN — indicators not warmed up (EMA-200, ADX-14)
  2. TRANSITIONAL — macro side (EMA50 vs EMA200) flipped within last 2 bars
  3. HIGH_VOL — ATR/close >= 90th percentile over last 60 bars
  4. RANGING — ADX < 20 AND ATR/close <= 25th percentile
  5. TRENDING_BULL — EMA50 > EMA200 + ADX >= 25
  6. TRENDING_BEAR — EMA50 < EMA200 + ADX >= 25
  7. CHOPPY_BULL — EMA50 > EMA200 + ADX < 25
  8. CHOPPY_BEAR — EMA50 < EMA200 + ADX < 25
- **Rationale:**
  - ADX threshold of 25 is industry standard for "trending" classification; ADX < 20 widely used for "ranging."
  - ATR/close as realized-vol proxy avoids the complexity of computing rolling-window standard deviation while capturing the same essence.
  - BTC daily is the universal regime anchor for crypto — every strategy's window gets its regime label from BTC, not from the strategy's own asset (avoids the tautology "this strategy works when its asset trends").
  - Backwards-compatible: the old `regime: "bull"/"bear"/"all"` field is preserved alongside the new `regime_tags: list[str]`. Migration to use only `regime_tags` will follow once empirical regime performance is established.
- **Per-strategy preliminary tags (verify with `backtest_rolling.py` before trusting):**
  - MACD_PB → [choppy_bull]
  - BTP → [trending_bull, choppy_bull]
  - VRB → [choppy_bull, trending_bull]
  - VBB → [trending_bull, choppy_bull]
  - SRC → [choppy_bull]
  - HATP → [trending_bull]
  - VPT → [trending_bull]
  - RVCB → [ranging, choppy_bull]
  - CMF → [trending_bear, choppy_bear]
  - RSI_BB → [choppy_bear, ranging]
  - ICVP → [trending_bull, trending_bear]
- **Promotion gate update:** A strategy now passes the rolling-backtest gate if and only if it shows STABLE_EDGE_IN_REGIME (median PF >= 1.35, min PF >= 1.0) within at least one of its DECLARED regime_tags. POOR_IN_REGIME findings in declared regimes block promotion, even if the strategy looks fine in non-declared regimes (which would just be reading coincidence).
- **Alternatives Considered:**
  - Extend the existing RegimeState enum: rejected — RegimeState is consumed by live regime router; mixing macro-classification and fine-classification breaks single-responsibility.
  - Use the strategy's own OHLCV for regime: rejected — tautological (a strategy that "trends with its asset" is just describing market beta).
  - More sub-regimes (e.g. separate HIGH_VOL_BULL vs HIGH_VOL_BEAR): rejected — 8 categories already require ~16 trades each minimum to populate; finer cuts would never have enough samples.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-27
- **Implemented By:**
  - `src/core/strategy/regime/historical_classifier.py` (new): `SubRegime`, `HistoricalRegimeClassifier`, `ClassifierThresholds`
  - `scripts/backtest_rolling.py`: fetches BTC daily, classifies each window's dominant regime, adds per-regime breakdown to report
  - `scripts/run_paper_trading.py`: each strategy in BULL/BEAR/ALL configs now has `regime_tags`
- **Affected Files:**
  - `src/core/strategy/regime/historical_classifier.py`
  - `scripts/backtest_rolling.py`
  - `scripts/run_paper_trading.py`

### DEC-2026-05-27-007: Retire BTF (bear_trend_follower) — Overfit Strategy

- **Decision:** `bear_trend_follower` (BTF) is retired from `BEAR_STRATEGY_CONFIG` and `EXPANSION_TIERS`. The strategy generator file (`src/core/strategy/generators/bear_trend_follower.py`) is preserved for future re-validation. No live or paper sessions of BTF will start; the regime router will no longer activate it.
- **Context:**
  - BTF was originally promoted on Q1 2026 backtests claiming **100% WR / Sharpe 2.4-3.6**.
  - May 2026 90-day backtest (commit `c1cc098`, ran 2026-05-27) showed **basket avg PF = 0.76 across 90 trades** with negative Sharpe on 6 of 7 symbols.
  - Live paper trading (2026-05-17 to 2026-05-27) showed **PF = 0.75 across 25 trades** — confirming the backtest within 1%.
  - Per-symbol PFs (May backtest): BTC 0.83, ETH 0.64, BNB 0.46, SOL 1.02, XRP 0.68, AVAX 1.10, DOGE 0.60.
  - AVAX (1.10) and SOL (1.02) cannot be saved — confidence interval at N=16 is ~[0.7, 1.6], statistically indistinguishable from noise. Sharpe +0.19 / -0.10 respectively — well below the 0.5 threshold where slippage costs erode the edge.
- **Rationale:**
  - The Q1 backtest was sample-overfit to a specific market structure (steep monotonic descents). May 2026 bear has been choppy with relief bounces — the regime BTF was designed to exploit isn't currently present.
  - Refitting parameters on May data would just shift the overfit, not fix the underlying assumption mismatch.
  - Keeping AVAX/SOL paper-running for "marginal data" has negative EV: operational complexity + paper compute + cognitive load on the operator for data that isn't statistically distinguishable from noise.
  - Generator code is preserved so the strategy can be re-validated when market regime returns to clean monotonic-descent conditions.
- **Process improvements that should have caught this:**
  - DEC-2026-05-27-005 (rolling-window validation) is now in place — BTF would have failed it.
  - DEC-2026-05-27-004 (promotion gate with N>=30, PF>=1.35, Sharpe>=1.0) is now in place — BTF would not have cleared it.
- **Alternatives Considered:**
  - Retain BTF on AVAX/SOL only: rejected — noise-level edge is not a deployment.
  - Refit BTF parameters on May data: rejected — that's the same overfit failure mode.
  - Delete generator code entirely: rejected — the strategy may have edge in a different regime; preserve for future re-test.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-27
- **Implemented By:** Removal of `bear_trend_follower` entry from `BEAR_STRATEGY_CONFIG`; removal of BTF/BTC and BTF/ETH `LiveTier` entries from `EXPANSION_TIERS`; retirement banner comment in both files referencing this decision.
- **Affected Files:**
  - `scripts/run_paper_trading.py`
  - `scripts/run_live_trading.py`
- **References:** Backtest output preserved in conversation; live paper data preserved in Neon `paper_trading_sessions`.

---

### DEC-2026-05-28-001: Expand Execution Scope to Margin/Futures (Long + Short), Staged

- **Decision:** Expand the system beyond spot-long-only to support Binance margin/futures so strategies can go both LONG and SHORT. **Deployment is staged** — capability is built and validated in the research layer FIRST; real leveraged capital is deferred until short edge is proven. This amends the spot-only sub-constraint of DEC-2026-01-15-002 (still Binance-only; market orders per DEC-2026-01-15-004 retained).
- **Context:**
  - PARA-01 (research audit, 2026-05-28) found 17 of 29 generators emit SHORT, and the backtest credits short P&L, but Binance **spot cannot short** — short-side edge was unrealizable. The system was in the worst state: simulating trades it could not execute.
  - The user explicitly approved expanding scope to margin/futures (the locked-decision change) to keep the short strategy space available.
  - There is currently **no validated short edge** — every short-emitting strategy (BTF, CMF, RSI_BB shorts) is POOR or noise even with the optimistic fictional-short credit. The proven edges (BTP, VBB, SRC) are all LONG-only.
- **Staged plan (the deployment discipline):**
  1. Build honest short backtesting in the research layer (funding-cost model + long/short toggle). NO live money. **(Implemented in this decision.)**
  2. Re-run the full funnel in both `spot` (long-only) and `futures` (long+short) modes to discover which short strategies, if any, have real edge once funding is charged.
  3. Go live on **spot long-only first** (BTP/VBB/SRC) to prove the live system end-to-end with zero liquidation risk.
  4. Only if step 2 finds genuine short edge: build the live Binance Futures execution adapter + liquidation/margin risk models + leverage controls, then deploy cautiously.
- **Rationale:**
  - Building futures *capability* fixes the PARA-01 honesty problem and keeps the strategy space open.
  - Deferring live leveraged deployment avoids existential liquidation risk on a system still finding its first reliable strategy, and avoids funding bleed on unproven strategies.
  - Conservative funding model (charged as an always-cost) ensures the futures backtest does not OVERstate edge.
- **Implementation (research layer, this session):**
  - `BacktestConfig.allow_shorts` (bool, default True) — when False, SHORT signals never open a position (spot long-only). A SHORT still closes a held long.
  - `BacktestConfig.funding_rate_per_8h` (float, default 0.0) — perpetual funding drag on notional per 8h, modeled as a conservative cost. 0.0 = spot; ~0.0001 = futures.
  - `SimulatedTrader`: long-only filter in `execute_signal`; `_funding_cost()` applied in `_close_position` and `force_close_at_price` (folded into commission so realized P&L reflects it).
  - `scripts/backtest_rolling.py`: `--market spot|futures` flag (spot = long-only/no funding; futures = long+short/funding).
- **Still pending (NOT done this session):**
  - Live Binance Futures execution adapter, funding/liquidation risk models, leverage controls — deferred to step 4.
  - PRD update to reflect the scope expansion (PRD Part 1.7 / 2.2 spot-only language is now stale).
  - `mvp-scope-control.md` update (futures was previously out-of-MVP).
- **Alternatives Considered:**
  - Long-only on spot permanently (PARA-01 Option A): rejected by user — discards the short strategy space and bear-market profitability.
  - Build live futures execution immediately: rejected — premature without validated short edge; adds liquidation risk before it's warranted.
- **Status:** ACTIVE (research-layer capability built; live futures deployment deferred)
- **Date Decided:** 2026-05-28
- **Implemented By:** `BacktestConfig` (allow_shorts, funding_rate_per_8h), `SimulatedTrader` (long-only filter + funding), `scripts/backtest_rolling.py` (--market flag).
- **Affected Files:**
  - `src/core/strategy/backtest/types.py`
  - `src/core/strategy/backtest/trader.py`
  - `scripts/backtest_rolling.py`
  - `tests/unit/backtest/test_types.py`, `tests/unit/backtest/test_trader_execution_model.py`

---

### DEC-2026-05-28-002: Spot-Wins Portfolio Triage — Retire 5 Strategies, Re-tag 5 Keepers

- **Decision:** Based on the spot-vs-futures rolling-window backtest comparison (run 2026-05-28 against ~10 months of 1H data, 5 windows × 60 days), retire 5 additional strategies (CMF, RSI_BB, HATP, VRB, VPT) — joining BTF (DEC-2026-05-27-007) — and refine `regime_tags` on the 5 keepers (MACD_PB, BTP, VBB, SRC, ICVP) to match empirical per-regime performance. Mark RVCB observe-only (insufficient sample, N=19). The live execution path stays spot long-only; futures is NOT worth building live execution for.
- **Context:**
  - The spot run (`allow_shorts=False, funding=0`) produced honest results matching architectural intent (the system was originally designed for spot).
  - The futures run (`allow_shorts=True, funding=0.0001/8h`) showed that strategies with bidirectional signals perform WORSE with shorts enabled — MACD_PB in choppy_bear went from PF 2.33 (spot, 29 trades) to PF 1.02 (futures, 60 trades). ICVP choppy_bear: spot PF 1.28 → futures PF 0.78. The short signals are actively destroying edge, not adding it.
  - Strategies that depend on shorts (BTF, CMF, RSI_BB) have no validated edge even with shorts enabled and modeled funding cost.
  - This resolves PARA-01 cleanly: spot is the right deployment, and futures execution is NOT needed.
- **Triage outcomes:**
  - **KEEP** (5 strategies with STABLE_EDGE or strong PROMISING in declared regime):
    - **MACD_PB** → `[choppy_bull, choppy_bear, trending_bull]` — STABLE_EDGE in 3 of 4 regimes (PF 1.58 / 2.33 / 1.65). Multi-regime real edge — closest to "robust" in portfolio.
    - **BTP** → `[choppy_bear]` (re-tagged from `[trending_bull, choppy_bull]` — was wrong). STABLE in choppy_bear PF 1.63 CV 0.16 across 69 trades.
    - **VBB** → `[choppy_bear]` (re-tagged from `[trending_bull, choppy_bull]` — was wrong). STABLE in choppy_bear PF 1.61 CV 0.14.
    - **SRC** → `[choppy_bull, choppy_bear]` — STABLE choppy_bull, PROMISING choppy_bear.
    - **ICVP** → `[choppy_bull, choppy_bear, trending_bear]` (re-tagged from `[trending_bull, trending_bear]` — wrong on trending_bull). PROMISING in 3 regimes, the most regime-resilient after MACD_PB.
  - **RETIRE** (5 strategies):
    - **CMF** — POOR in all 3 bear/chop regimes (design intent failed). Trending_bull "edge" wrong direction, unreliable.
    - **RSI_BB** — PF 0.06–0.41 across all 4 regimes both modes. Worst in portfolio.
    - **HATP** — POOR in all 4 regimes, 231 trades. Promoted on Q1 3-round backtest claiming PF 1.40–1.70; rolling backtest could not reproduce. Same overfit pattern as BTF.
    - **VRB** — BTC-only, single-window per regime, no robust verdict possible.
    - **VPT** — PF 1.00 overall (break-even). Loses after live slippage. BTC-only.
  - **OBSERVE** (1 strategy):
    - **RVCB** — N=19, single-window per regime. Trending_bear PROMISING (PF 1.56) but sample too thin. Keep paper-running with `observe_only: True`; do NOT activate live tier.
- **Rationale:**
  - Spot mode results are statistically AND architecturally coherent — the system was built for spot. The short signals were retrofitted, not first-class.
  - The 5 retired strategies all fail in their DESIGN regime, not just in adjacent regimes. They are not "regime-specific edges deployed wrong" — they have no edge.
  - The 5 keepers' regime_tags were verified against multi-window empirical data. Previously-PRELIMINARY tags are now backed by 5-window/multi-symbol rolling backtests.
  - Live futures execution is NOT built — saves weeks of work, avoids liquidation risk, no edge lost.
- **Consequences (acknowledged):**
  - `BEAR_STRATEGY_CONFIG` is now empty. Paper trading runs nothing when the legacy bear router activates. The choppy_bear strategies (BTP, VBB, MACD_PB, SRC) are tagged "bull" in the coarse `regime` field and won't activate via the legacy router in choppy_bear. **This is intentional** — better quiet than losing money — and is the motivating bug for the next build.
  - The next build (DEC-2026-05-28-003 when written) is the SubRegime-aware live router that reads `regime_tags` from the paper config and activates strategies whose tags match the current SubRegime. That unlocks BTP/VBB/MACD_PB trading in choppy_bear.
- **Implementation:**
  - `scripts/run_paper_trading.py`: BEAR_STRATEGY_CONFIG emptied (banner explains); VRB, HATP, VPT entries removed from BULL_STRATEGY_CONFIG with retirement banner; RVCB gets `observe_only: True`; the 5 keepers' regime_tags refined with empirical citations.
  - `scripts/run_live_trading.py`: CMF/SOL, RSI_BB/ETH, HATP/BTC tiers removed from `EXPANSION_TIERS`. MACD_PB/AVAX added as tier-1. MIN_BARS_LOOKUP + STRATEGY_PARAMS_LOOKUP gain macd_pullback entry.
- **Alternatives Considered:**
  - Keep retired strategies in paper "just in case": rejected — they pollute aggregate metrics and waste compute on signals confirmed to lose money.
  - Build futures live execution anyway: rejected — empirical data shows no edge to capture even WITH shorts modeled honestly. Would add liquidation risk for nothing.
  - Refit the retired strategies on May data to "rescue" them: rejected — that's the same overfit failure mode that produced BTF.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-28
- **Implemented By:** Edits to run_paper_trading.py (BEAR/BULL configs + RVCB) and run_live_trading.py (EXPANSION_TIERS + MACD_PB_PARAMS).
- **Affected Files:**
  - `scripts/run_paper_trading.py`
  - `scripts/run_live_trading.py`
- **References:** Spot run output preserved in conversation history. Per-regime breakdown clean-data version is the canonical triage record.

---

### DEC-2026-05-28-003: SubRegime-Aware Live Routing — Unlock Choppy-Bear Strategies

- **Decision:** Add a live `SubRegimeDetector` (parallel to `RegimeDetector`) that classifies the current BTC daily bar into one of 8 `SubRegime` values with 2-bar confirmation. Extend both `RegimeRouter` (paper) and the live trading tier-activation logic to consult per-strategy `regime_tags` (list of SubRegime strings) before the legacy coarse `regime` field. **Fail-closed**: when SubRegime is UNKNOWN, no `regime_tags`-tagged strategy activates.
- **Context:**
  - DEC-2026-05-28-002 left a critical architectural mismatch: the strategies with empirically-validated edge in the current regime (BTP, VBB, MACD_PB, SRC for choppy_bear) are stored under `BULL_STRATEGY_CONFIG` and tagged `regime: "bull"` in the legacy coarse field. Under the existing router, those strategies were SUSPENDED while the system was in any bear sub-regime, even though their actual edge is in choppy_bear.
  - The result: paper trading runs nothing in the current regime even though we have 5 validated strategies for it. Live trading would have the same problem.
  - This is the build that unlocks deployment of the validated strategies in their actual operating regime.
- **Architecture:**
  - `SubRegimeDetector` wraps the existing `HistoricalRegimeClassifier`, fetches BTC 1d OHLCV at runtime, and applies the same per-bar classification. Confirmation rule: last N bars (default 2) must all share the same SubRegime label AND label must not be UNKNOWN or TRANSITIONAL — else return UNKNOWN.
  - `RegimeRouter._get_template_ids_for_regime` now takes a `sub_regime` parameter. Per-entry precedence:
    1. `regime_tags` present + non-empty + `sub_regime != UNKNOWN` + `sub_regime.value in regime_tags` → activate
    2. `regime_tags` present BUT sub_regime UNKNOWN or not in list → **do not activate**
    3. No `regime_tags` → fall back to legacy coarse `regime` matching
  - `observe_only: True` overrides everything — that entry is for data-collection only and never activates via the router.
  - Live trading: identical precedence implemented in `_tier_regime_match()` helper; applied to BOTH tier-activation check AND per-tier entry gate (`regime_allows_entry` in `_process_tier`).
- **Fail-closed contract (the critical safety property):**
  - Any failure in fetching, classifying, or confirming SubRegime → return UNKNOWN.
  - UNKNOWN sub_regime → `regime_tags`-tagged strategies do NOT activate. Better quiet than wrong-regime.
  - This is enforced by tests in `tests/unit/regime/test_sub_regime_routing.py` (14 new tests, all passing).
- **Strategy → SubRegime tag mapping (per DEC-2026-05-28-002 empirical data):**
  - MACD_PB: `[choppy_bull, choppy_bear, trending_bull]`
  - BTP: `[choppy_bear]`
  - VBB: `[choppy_bear]`
  - SRC: `[choppy_bull, choppy_bear]`
  - ICVP: `[choppy_bull, choppy_bear, trending_bear]`
  - RVCB: `[trending_bear]` (but `observe_only: True`)
- **Backward compatibility:**
  - All existing strategy configs that have no `regime_tags` continue to work via the legacy coarse `regime` field — unchanged behavior.
  - `RegimeRouter.__init__` gains an optional `sub_detector` parameter; existing code that passes only the coarse detector is unaffected (regime_tags routing is opt-in by virtue of needing the sub_detector).
  - `LiveTier` dataclass adds `regime_tags: list[str]` with default `[]` — existing tier definitions work without modification.
- **Live re-enable readiness:**
  - The kill switch (`LIVE_TRADING_ENABLED` env var, default OFF) remains the gate for any real-capital activity. Nothing in this decision enables live by itself.
  - When the user does flip the switch, the new SubRegime routing means MACD_PB/BTP/VBB/SRC/ICVP tiers can correctly activate in their validated regime.
  - All other safety layers from prior decisions remain active: demotion guardrail (DEC-2026-05-27-004), decorrelation cap (DEC-2026-05-27-006), consecutive-failure alert (DEC-2026-05-27-003), kill switch (DEC-2026-05-27-001).
- **Alternatives Considered:**
  - Hack temporary `regime: "bear"` on BTP/VBB: rejected — would also activate in trending_bear where they're POOR.
  - Replace coarse `RegimeState` entirely with `SubRegime`: rejected — existing code (manual regime tagging, system state persistence, API) consumes RegimeState; coexistence is the safer migration path.
  - Use a "current SubRegime" in `regime_tags` AND require the coarse field to also match: rejected — adds belt-and-suspenders complexity without safety improvement (since regime_tags is the empirical source of truth).
- **Status:** ACTIVE
- **Date Decided:** 2026-05-31
- **Implemented By:**
  - `src/core/strategy/regime/sub_regime_detector.py` — new SubRegimeDetector
  - `src/core/strategy/regime/router.py` — extended with sub_detector + regime_tags precedence
  - `src/core/strategy/regime/__init__.py` — re-export SubRegime, SubRegimeDetector
  - `scripts/run_paper_trading.py` — wires SubRegimeDetector into RegimeRouter
  - `scripts/run_live_trading.py` — `_tier_regime_match()` helper, LiveTier.regime_tags field, SubRegime detection in main(), used in tier activation + entry gate
  - `tests/unit/regime/test_sub_regime_routing.py` — 14 new tests covering the fail-closed contract
- **Affected Files:** (above)

---

### DEC-2026-05-31-001: Fix Research Data-Corruption + Metric-Labeling Bugs (PARA-02, PARA-08, PARA-09)

- **Decision:** Fix three audit findings from `docs/research/RESEARCH_FIXLIST.md` that distort the data the live-promotion infrastructure (DEC-2026-05-27-004/005) consumes, without altering any locked decision or the live trading kill switch:
  - **PARA-02 (HIGH):** The live-paper force-close on stop priced the final trade at `equity / position_value` — a dimensionless ratio (~1.x), not a market price — booking a BTC exit at ~$1-2 and corrupting `paper_trading_sessions.trade_log`. Fixed to force-close at the last observed market close, mirroring `BacktestEngine`'s end-of-run force-close (`price=last_bar.close`).
  - **PARA-09 (LOW):** `largest_loss = min(all_pnl)` reported the smallest *win* as "largest loss" on loss-free runs. Fixed to compute `largest_win`/`largest_loss` over the existing winning/losing trade sets, default 0.0 when empty. The symmetric `largest_win` defect (least-bad loss mislabeled as largest win on win-free runs) is fixed in the same change.
  - **PARA-08 (LOW):** Per-symbol `total_return` summed per-trade percentages. Fixed to compound them: `(prod(1 + return_pct/100) - 1) * 100`.
- **Context:** The validation_report + demotion guardrail + promotion gate (DEC-2026-05-27-004/005) gate live-capital deployment by reading per-session trade logs and equity curves from Neon. PARA-02 injected fake ~$1-2 force-close prices into those logs, polluting per-session PnL stats with unknown noise. Until fixed, every promotion/demotion decision carried that contamination. PARA-08/09 are localized metric-labeling errors surfaced in the same audit; fixed opportunistically as cheap correctness wins.
- **Rationale:**
  - **PARA-02 root cause is missing retained state, not a bad formula.** The force-close runs after the live polling loop exits, by which point the last `series` is out of scope. The original author reverse-engineered a "price" from the equity curve, but `EquityPoint` deliberately stores no price. The fix retains the last close (`_last_close_price`) the moment each bar is processed, mirroring how `BacktestEngine` keeps `series[-1]` in scope through to its force-close. A `None`-safe fallback to the open position's `entry_price` covers the restored-position-then-immediate-stop edge case — always a real, positive price, never a fabricated one, and logged (`force_close_missing_live_close_price`) for observability.
  - **PARA-09 reuses the existing `winning_trades`/`losing_trades` classification** (zero naming/semantic drift per zero-technical-debt rules).
  - **PARA-08 compounding** is self-contained (needs no capital base threaded through) and is comparable in spirit to the portfolio-level compounded `total_return_pct`.
- **Scope / safety:**
  - Code-path-only fix for FUTURE force-closes. Existing corrupted `trade_log` rows in Neon are NOT migrated or touched.
  - `LIVE_TRADING_ENABLED` kill switch untouched — stays fail-closed OFF (DEC-2026-05-27-001).
  - No locked decision affected (spot/market/SQLite/monolithic). No PRD scope change.
  - PARA-01 (the CRITICAL spot-shorts finding) is NOT addressed here — it remains gated by DEC-2026-05-28-001's staged plan.
- **Alternatives Considered:**
  - Persist `_last_close_price` across restarts in the state snapshot: rejected for now — adds save/load schema surface; the `entry_price` fallback already guarantees a real price in the rare no-bar-processed case. Can revisit if the warning fires in production.
  - Back-fill/repair historical corrupted force-close rows in Neon: rejected — out of scope for a code fix; the constraint was explicitly "don't touch existing trade_log data." Validation consumers can be re-run on clean forward data.
  - Fix only `largest_loss` (literal PARA-09): rejected — `largest_win` is the identical defect; fixing both is honest and costs one line.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-31
- **Implemented By:**
  - `src/core/strategy/paper/engine.py` — `_last_close_price` state, capture in `_process_live_bar`, rewritten force-close block in `_run_live`
  - `src/core/strategy/backtest/metrics.py` — `largest_win`/`largest_loss` over matching trade sets; compounded per-symbol `total_return`
  - `tests/unit/paper/test_engine.py` — 2 force-close regression tests (real-price + entry-price fallback)
  - `tests/unit/backtest/test_metrics.py` — 3 regression tests (PARA-09 both directions + PARA-08 compounding)
- **Affected Files:** (above)
- **References:** `docs/research/RESEARCH_FIXLIST.md` (PARA-02, PARA-08, PARA-09); DEC-2026-05-27-004 (promotion gate), DEC-2026-05-27-005 (rolling-window validation), DEC-2026-05-27-001 (kill switch).

---

### DEC-2026-05-31-002: PARA-02 Historical Quarantine — Read-Time Filter for Corrupted Force-Closes

- **Decision:** Add a read-time filter to `scripts/validation_report.py` that drops PARA-02-contaminated trades from per-session statistics by their corruption signature, without ever modifying the database. A trade is quarantined when its `exit_price` is in [0.5, 3.0] AND the entry/exit price ratio is >10x in either direction — the unmistakable signature of a force-close booked at the dimensionless `equity / position_value` ratio (~1.x) instead of a market price. The count of dropped trades is logged per session and surfaced on `SessionStats.quarantined_trades`; sessions where >20% of raw trades were dropped are flagged (`quarantine_flag`) so the operator knows the metrics rest on a reduced sample.
- **Context:** DEC-2026-05-31-001 fixed PARA-02 **forward-only** — it stopped new corrupted force-closes but explicitly did NOT migrate the corrupted rows already in Neon (constraint: don't touch existing trade_log data). Those historical rows book fake ~$1-3 exit prices, which distort per-session PnL/PF/Sharpe/MaxDD — the exact inputs to the promotion gate (DEC-2026-05-27-004). The validation report needed to stop trusting those specific trades without throwing away the genuine signal in the same sessions.
- **Rationale:**
  - **Surgical, signature-based, not date-based.** Filtering all pre-fix trades would discard genuinely good signal. Real market prices for the traded symbols (BTC ~$50k-100k, ETH ~$2k, BNB, SOL, AVAX, XRP ~$2, DOGE ~$0.15) are never simultaneously inside [0.5, 3.0] AND >10x disconnected from the entry price, so the two-condition test isolates corruption with no false positives on real trades (a real XRP trade near $2 has entry~exit, ratio ~1, so it is never flagged).
  - **Read-only by construction.** The filter builds a filtered Python list at read time; it issues no UPDATE/DELETE. Safe to run against Neon (prod) — which is exactly where the corrupted rows live — while honoring the "no Neon mutation" constraint. DB is selected by `DATABASE_URL` (SQLite locally, Neon on Railway); the filter is DB-agnostic.
  - **Operator visibility over silent correction.** Logging per-session counts + a >20% flag means a session whose classification improved only because corrupted losses were removed is visible, not hidden.
- **Known limitation (accepted):** A corrupted DOGE force-close (real entry ~$0.15, exit-ratio ~1.0) yields an entry/exit ratio of ~6.7x, below the 10x threshold, so it can slip through. This is deliberate — the band is tuned to never drop genuine trades. DOGE's absolute-dollar corruption is also the smallest. Revisit only if DOGE/XRP sessions show anomalous stats.
- **Alternatives Considered:**
  - Date-based filter (drop all trades before commit 536bfc8): rejected — discards genuine signal; the corruption is per-trade, not per-session.
  - Back-fill/repair the Neon rows: rejected — violates the "don't modify Neon data" constraint and is riskier than a read-time filter.
  - Widen the band / lower the ratio threshold to catch DOGE: rejected — raises false-positive risk on genuine low-price-asset trades; not worth it for the smallest-dollar corruption.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-31
- **Implemented By:**
  - `scripts/validation_report.py` — `_is_corrupt_force_close()` predicate, filter in `compute_session_stats()`, `SessionStats.quarantined_trades` + `quarantine_flag`, per-session warning log, console-report markers/summary
  - `tests/unit/scripts/test_validation_report.py` — 9 tests (predicate detection + no-false-positives + session-stats integration + >20% flag boundary)
- **Affected Files:** (above)
- **References:** DEC-2026-05-31-001 (the forward-only PARA-02 code fix this complements); `docs/research/RESEARCH_FIXLIST.md` (PARA-02); DEC-2026-05-27-004 (promotion gate that consumes these stats).

---

### DEC-2026-05-31-003: Portfolio Capital Model (PARA-12) — Per-Strategy Allocation, Concurrency Cap, Capital Reserve

- **Decision:** Replace the "every live tier owns the full LIVE_CAPITAL" model in `scripts/run_live_trading.py` with a minimum-viable portfolio capital model:
  - **Per-strategy allocation:** each tier's `capital` is a slice = `LIVE_CAPITAL * PER_STRATEGY_ALLOCATION_PCT` (default 20%), not the full account.
  - **Concurrency cap:** at most `MAX_STRATEGIES_LIVE_CONCURRENT` (default 4) tiers active at once, in tier-definition order, even if more are eligible by regime + threshold.
  - **Capital reserve:** total committed capital across active tiers may never exceed `LIVE_CAPITAL * CAPITAL_RESERVE_FRACTION` (default 0.85); the gate uses the PROJECTED total (active + candidate), not current-only, so no single activation can overshoot the reserve.
  - Both rails live in a pure, unit-tested helper `_can_activate_tier()`, called in the activation loop after the existing regime/threshold/degradation checks.
- **Context:** PARA-12 (RESEARCH_FIXLIST): every backtest and every live tier assumed it owned the whole account, so N concurrent strategies double-counted capital N times and per-strategy returns were not additive — portfolio risk was unknown. This is the last structural blocker before live re-enable. The full portfolio layer (ReturnStreamStore, CorrelationEngine, risk-parity Allocator — `docs/research/PORTFOLIO_LAYER_DESIGN.md`) is large and deferred; this decision implements only the capital-allocation + concurrency + reserve rails needed to stop the double-counting and bound aggregate exposure.
- **Rationale:**
  - **Slice, not full account:** directly fixes the double-counting. At `LIVE_CAPITAL=$100` with 20% slices, per-strategy capital is $20 and the tier ladder reproduces the original $0/$40/$60/$80 thresholds exactly — the model is the original design expressed honestly at portfolio scale.
  - **Projected reserve check:** a current-only "if committed > cap" test would allow one activation to breach the reserve; checking `committed + candidate` keeps the 15% buffer intact. Committed capital uses the fixed `tier.capital`, not mark-to-market equity, because the reserve protects the cash buffer.
  - **Concurrency cap reinforces the decorrelation cap (DEC-2026-05-27-006):** bounds how many strategies — hence how much correlated risk — can be live at once, independent of the same-direction position cap.
  - **Activation thresholds rebased to the per-strategy slice:** thresholds are multiples of `PER_STRATEGY_CAPITAL`, not `LIVE_CAPITAL`. Tied to the full account they would be unreachable (a $4 slice can never make `active_equity` hit a $40 threshold), so tiers 2-4 would never activate. Rebasing keeps "grow the active book before adding a strategy" reachable.
- **Minimum-capital consequence (IMPORTANT, money-relevant):** each strategy trades `PER_STRATEGY_CAPITAL * POSITION_SIZE_FRACTION`. With $20 × 20% × 25% = $1, below Binance's $5 minimum notional. The startup guard is now per-strategy-aware and **fails closed** (`sys.exit(1)`) with the exact floor: the 4-strategy model needs `LIVE_CAPITAL ≥ $100` (= 5 / (0.20 × 0.25)), or a higher `PER_STRATEGY_ALLOCATION_PCT`. On the current $20 account the live harness will refuse to start — by design, better than activating tiers that silently never place a valid order.
- **Safety:**
  - **Dormant until re-enable:** `run_live_trading` is only launched by `run_all.py` when `LIVE_TRADING_ENABLED` is truthy (DEC-2026-05-27-001); the switch stays OFF, so this changes nothing about live behavior until explicitly turned on with adequate capital.
  - Sub-min-notional already fails safe at order time (`calculate_quantity` returns 0.0 + warns), so even a misconfig cannot place an invalid order.
  - All env-overridable; no locked decision touched (still Binance spot, market orders, SQLite/Neon).
- **Alternatives Considered:**
  - Full portfolio layer now (CorrelationEngine + Allocator + risk parity): rejected as too large for this step; deferred to PORTFOLIO_LAYER_DESIGN phased rollout. This MVP unblocks live re-enable without it.
  - Current-only reserve check (literal "total_active_capital > cap"): rejected — permits a single overshoot past the reserve; projected check is safer.
  - Keep thresholds on LIVE_CAPITAL: rejected — makes tiers 2-4 unreachable under sliced capital (a real bug caught during implementation).
  - Auto-scale per-strategy % up when few strategies run: rejected as gold-plating; explicit config + fail-closed guard is simpler and safer.
- **Status:** ACTIVE
- **Date Decided:** 2026-05-31
- **Implemented By:**
  - `scripts/run_live_trading.py` — `MAX_STRATEGIES_LIVE_CONCURRENT`, `PER_STRATEGY_ALLOCATION_PCT`, `CAPITAL_RESERVE_FRACTION`, `PER_STRATEGY_CAPITAL`; `_can_activate_tier()`; `_build_tiers` capital + threshold rebased to the slice; per-strategy fail-closed min-notional guard; activation-loop gate; display labels
  - `tests/unit/scripts/test_live_capital_model.py` — 6 tests (concurrency cap both sides, reserve both sides, projected-overshoot block, default-config coherence)
- **Affected Files:** (above)
- **References:** `docs/research/RESEARCH_FIXLIST.md` (PARA-12); `docs/research/PORTFOLIO_LAYER_DESIGN.md` (full layer, deferred); DEC-2026-05-27-006 (decorrelation cap), DEC-2026-05-27-001 (kill switch), DEC-2026-05-28-002 (the 5 KEEP strategies this allocates across).

---

### DEC-2026-06-01-001: Auto-Promotion Gate — Require READY_FOR_LIVE Before Live Tier Activation

- **Decision:** A live expansion tier may only activate if its pooled live-paper performance is classified **READY_FOR_LIVE** by the canonical promotion gate (DEC-2026-05-27-004: N>=30 AND PF>=1.35 AND per-trade Sharpe>=1.0 AND MaxDD<=5%). Implemented by a new `_paper_strategy_classification(template_id)` in `scripts/run_live_trading.py`, checked in the tier-activation loop after the existing demotion check. Also: a daily Railway cron runs `validation_report --telegram` at 09:00 UTC for passive visibility (`docs/operations/RAILWAY_CRONS.md`).
- **Context:** The demotion guardrail (DEC-2026-05-27-004 / `_paper_strategy_is_degraded`) only blocks a tier when paper data shows N>=10 AND PF<0.8. A brand-new strategy with **N=0** classifies RESEARCH and sailed through the activation check with zero validation — as did any OBSERVING (N>=10, PF>=1.0 but not yet proven) strategy. This gate closes that gap: activation now requires positive proof of readiness, not merely the absence of degradation. This is the last structural safety before live re-enable.
- **Rationale:**
  - **Single source of truth:** `_paper_strategy_classification` reuses the exact validation-report helpers (`_classify`, `_profit_factor`, `_sharpe_per_trade`, `_max_drawdown_pct`, `_is_corrupt_force_close`) rather than re-deriving thresholds, so the live gate and the daily report can never disagree (zero drift). To make those helpers importable without side effects, `validation_report`'s module-level `setup_logging()` was moved into its `main()`.
  - **PARA-02 quarantine applied:** the classifier excludes corrupted force-close trades (DEC-2026-05-31-002) before computing stats, so contaminated historical rows cannot fake a READY verdict.
  - **Fail-open on DB error, fail-closed on a clear verdict:** `_paper_strategy_classification` returns `(classification, db_ok)`. When the DB can't be read (`db_ok=False`) the caller does NOT block — mirroring `_paper_strategy_is_degraded`, so a transient outage never blocks a restart (which would leave an open position unmanaged). A successfully-computed non-READY verdict blocks. The fail-closed path is the point of the gate; the fail-open path preserves restart resilience. The residual risk (a brand-new strategy activating during a DB outage at its first activation) is small, bounded by the per-strategy capital slice, and symmetric with the existing demotion design.
  - **Alert-once:** a blocked tier sends one Telegram alert per session via a `_promotion_alerted` state flag, mirroring the demotion-blocked alert pattern (no per-poll spam).
  - **Relationship to demotion:** the gate logically subsumes the demotion check (READY implies not-degraded), but demotion is retained — it fires first with a more specific "PF=x degraded" alert for the actively-bleeding case, and is defense-in-depth.
- **Scope — tier 1 exempt (deliberate):** the gate applies to **expansion tiers only**. Tier 1 (the operator-chosen primary, `EXPANSION_TIERS[0]`) is bootstrapped active at startup and bypasses the activation loop — exactly as it already bypasses the demotion guardrail. The operator explicitly selects tier 1 and has daily-report visibility into its classification before flipping `LIVE_TRADING_ENABLED`; automation vets the auto-expansion tiers that activate later as equity grows. Extending the gate to tier 1 is a one-line follow-up if desired, but is intentionally not done here to keep the change surgical and avoid introducing the unmanaged-open-position edge to the bootstrap path.
- **Graduated promotion (OBSERVING at 50% capital) — SKIPPED in v1:** considered allowing OBSERVING strategies to activate at half the normal capital slice. Rejected for v1 because variable per-tier capital interacts with the PER_STRATEGY min-notional floor (DEC-2026-05-31-003: a half-slice could fall below Binance's $5 minimum and silently never trade) and the reserve math, and deserves its own decision with its own tests. The v1 gate is binary: READY_FOR_LIVE or wait.
- **Safety:** dormant until re-enable — `run_live_trading` only launches when `LIVE_TRADING_ENABLED` is truthy (DEC-2026-05-27-001), which stays OFF. No locked decision touched. The daily cron is read-only (DEC-2026-05-31-002) and safe against Neon.
- **Alternatives Considered:**
  - Duplicate the `_classify` thresholds in `run_live_trading`: rejected — drift risk; import the single source instead.
  - Fail closed on DB error: rejected — would block restarts during transient outages and leave open positions unmanaged, inconsistent with the demotion guardrail's documented rationale.
  - Gate tier 1 too: deferred — see scope above; consistent with existing demotion exemption, surgical.
  - Graduated OBSERVING promotion: deferred — see above.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-01
- **Implemented By:**
  - `scripts/run_live_trading.py` — `_paper_strategy_classification()`; promotion-gate block in the activation loop; import of validation-report helpers
  - `scripts/validation_report.py` — `setup_logging()` moved into `main()` (import-safety)
  - `tests/unit/scripts/test_promotion_gate.py` — 7 tests (all 4 classification states, multi-session pooling, fail-open on DB error, PARA-02 quarantine applied)
  - `docs/operations/RAILWAY_CRONS.md` — daily validation-report cron setup
- **Affected Files:** (above)
- **References:** DEC-2026-05-27-004 (promotion gate thresholds — the canonical logic reused); DEC-2026-05-31-002 (PARA-02 quarantine, applied in the classifier); DEC-2026-05-31-003 (per-strategy capital model the gate guards); DEC-2026-05-27-001 (kill switch).

---

### DEC-2026-06-01-002: Uniform Tier-1 Auto-Promotion Gate + Distance-to-Promotion Reporting

- **Decision:** Two operational refinements to the auto-promotion gate (DEC-2026-06-01-001):
  1. **Tier 1 is now gated identically to expansion tiers.** A new `_tier1_activation_blocked(template_id)` in `scripts/run_live_trading.py` applies the same READY_FOR_LIVE classification check to the operator-chosen primary tier (`EXPANSION_TIERS[0]`) at startup. If the verdict is a clear non-READY (`db_ok=True`), tier 1 does NOT auto-activate: the runner logs a warning, sends a one-time Telegram alert, and leaves `tier1.active = False`. The gate fails OPEN on DB error (mirrors the demotion guardrail), so a transient outage never blocks a restart.
  2. **`scripts/validation_report.py` now reports distance-to-promotion.** A new `promotion_distance(stats) -> PromotionDistance` computes, for any session, the minimum additional progress needed on each gate dimension: `trades_needed`, `pf_deficit`, `sharpe_deficit`, `dd_overage` (each floored at 0; a +inf PF reads as 0 deficit). Rendered in the console report (`print_distance_section`, ASCII `[OK]`/`[...]`/`[MISS]` markers), in `--compact`/`--telegram` (trade gap only, for brevity), and in `--json` (`distance_to_promotion`, keyed by session_id).
- **Context:** DEC-2026-06-01-001 deliberately left tier 1 exempt from the gate and called extending it "a one-line follow-up if desired." With the system now structurally complete and waiting on calendar paper data, the operator wanted (a) the gate rule to be uniform across every live tier so there is no special-case path to reason about at re-enable time, and (b) the daily validation report to answer not just "is this strategy READY?" but "exactly what does each maturing strategy still need?" — turning the report into an actionable dashboard for the calendar wait.
- **Rationale:**
  - **Uniformity removes a reasoning hazard:** with tier 1 gated, "no live tier activates unless READY_FOR_LIVE" is now universally true, rather than "...unless it's tier 1." One rule, one mental model, fewer ways to be surprised at re-enable.
  - **Single source of truth preserved:** `_tier1_activation_blocked` delegates to the existing `_paper_strategy_classification` (which reuses the validation-report helpers), so no thresholds are duplicated — the tier-1 gate, the expansion gate, and the report can never disagree (zero drift).
  - **Self-healing via the existing loop:** a blocked tier 1 is simply left inactive, so the expansion-activation loop re-evaluates it every poll (its `activation_threshold` is 0.0) and brings it online automatically once paper data clears the gate. This reuses one control-flow path instead of adding a separate tier-1 retry path. Startup pre-sets the `_promotion_alerted` and `_degradation_alerted` state flags so the first poll's re-check does not emit a duplicate blocked alert (honors the existing "alert once per session" contract).
  - **Distance metric agrees with the gate by construction:** a session whose four distance dimensions are all zero is exactly a READY_FOR_LIVE session, so the new report cannot contradict `_classify`. The distance is purely informational; `classification` remains the source of truth.
  - **ASCII-only markers:** the report uses `[OK]`/`[...]`/`[MISS]` rather than unicode glyphs, per the project rule against unicode in generated output.
- **Open-position edge (the reason 06-01-001 deferred this):** DEC-2026-06-01-001 cited "the unmanaged-open-position edge to the bootstrap path" as why it left tier 1 exempt — if tier 1 is blocked while holding an open position, stop/TP enforcement does not run for that position. This is accepted and mitigated rather than eliminated: (1) the runner only launches when `LIVE_TRADING_ENABLED` is truthy, which stays OFF; (2) at the actual re-enable the operator will only flip the switch once tier 1's paper data is READY, so the gate will not block it then; (3) the blocked-tier alert explicitly states when a position is open and unmanaged so the operator can intervene manually; (4) the fail-open-on-DB-error contract means a restart during a transient outage still activates and resumes managing the position.
- **Alternatives Considered:**
  - Leave tier 1 exempt (status quo): rejected — the operator explicitly wanted uniformity; the special-case is a latent reasoning hazard.
  - Manage an open position even when the gate blocks new entries: rejected for v1 — that is a larger change (a "manage-only, no-entry" tier mode) that deserves its own decision and tests; the mitigations above bound the risk for the current dormant state.
  - Show distance as an extra column in the existing per-session table: rejected — too wide for the console; a dedicated section reads better and is easy to omit for READY sessions.
  - Full per-dimension distance in the Telegram compact mode: rejected — trade gap only keeps the message tidy; the full breakdown lives in the console + JSON.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-01
- **Implemented By:**
  - `scripts/run_live_trading.py` — `_tier1_activation_blocked()`; tier-1 startup gate + blocked-tier alert with dedup-flag pre-set in `main()`
  - `scripts/validation_report.py` — `PromotionDistance`, `promotion_distance()`, `_distance_cells()`, `print_distance_section()`; compact-mode trade gap; `--json` `distance_to_promotion`
  - `tests/unit/scripts/test_promotion_gate.py` — `TestTier1ActivationGate` (blocked / RESEARCH / READY-allowed / fail-open)
  - `tests/unit/scripts/test_validation_report.py` — `TestPromotionDistance`, `TestDistanceCells`, `TestCompactTextTradeGap`
- **Affected Files:** (above)
- **References:** DEC-2026-06-01-001 (the gate this extends — closes its documented tier-1 follow-up + open-position-edge note); DEC-2026-05-27-004 (promotion gate thresholds — single source of truth); DEC-2026-05-27-001 (kill switch — stays OFF, untouched).

### DEC-2026-06-01-003: Geo-Block Fail-Fast — Skip Useless Retries on Binance Regional Rejection

- **Decision:** When a Binance API call fails with the regulatory geo-restriction signature (`"restricted location"` or `"b. Eligibility"`), both `run_paper_trading.py` and `run_live_trading.py` exit immediately with a dedicated exit code (`GEO_BLOCK_EXIT_CODE = 2`). The `run_all.py` supervisor recognizes this code and does NOT restart — it stops the whole wrapper so the operator can intervene. Diagnostic time goes from ~30 minutes of wasted retries to ~5 seconds.
- **Context:**
  - On 2026-06-01 the Railway service began crash-looping with Binance returning `APIError(code=0): Service unavailable from a restricted location ... 'b. Eligibility'`. Root cause was the deployment region (`europe-west4` had been set in March via commit 476878e, but the Railway dashboard region reverted at some point, possibly during a redeploy).
  - The existing crash-restart harness wasted 25 attempts (5 inner × 5 outer) over ~30 minutes before exhausting — all attempts certain to fail because the rejection is regulatory, not transient. Each restart consumed Railway compute and produced redundant log noise.
  - The diagnosis was non-obvious from the log pattern; only by reading commit 476878e + d14a9d2 did the root cause become clear. Future occurrences need to surface the cause in seconds, not require git archaeology.
- **Rationale:**
  - **Fail-closed on a known-unfixable failure.** Geo-restriction cannot self-heal on retry. The system already has fail-closed semantics for related concerns (kill switch, demotion guardrail, SubRegime UNKNOWN); this extends the same pattern to a runtime failure category.
  - **Exit-code as inter-process contract.** The supervisor and child processes are independent Python processes; an exit code is the cleanest cross-process signal. Code `2` follows Unix convention for "misuse / configuration error" (distinct from `1` for generic crash).
  - **Operator-facing message in the log.** When fail-fast triggers, both runners and the supervisor print a banner with: the diagnosis, the fix steps (Railway dashboard region change), known-good regions (europe-west4, asia-southeast1, europe-west1), and a back-reference to this decision + commit 476878e. The operator sees the answer in the log, not just the problem.
  - **Signatures chosen for specificity.** `"restricted location"` and `"b. Eligibility"` are highly Binance-specific phrases. The generic `"Service unavailable"` was deliberately excluded — it would false-positive on common transient 503s that legitimately benefit from retry.
- **False-positive avoidance (the critical safety property):**
  - The test suite asserts the detector does NOT fire on: generic 503 Service Unavailable, network timeouts, invalid API key errors, random RuntimeError, empty strings, KeyboardInterrupt.
  - A false negative wastes ~30 min of retries (annoying but recoverable). A false positive permanently halts the system on a transient blip (unacceptable). The asymmetry drove the signature choice.
- **Implementation:**
  - `src/utils/geo_block.py` (new): `GEO_BLOCK_SIGNATURES`, `GEO_BLOCK_EXIT_CODE`, `is_geo_block_error()`, `print_geo_block_message()`.
  - `scripts/run_paper_trading.py` `__main__`: detect + print + exit-with-code-2 BEFORE the standard retry loop runs.
  - `scripts/run_live_trading.py` `__main__`: same pattern, with `logger.error("live_geo_block_detected", ...)` for structured-log correlation.
  - `scripts/run_all.py` supervisor poll loop: when a child's `proc.poll()` returns `GEO_BLOCK_EXIT_CODE`, the supervisor sets `shutting_down = True` and prints a clear log line — it does not restart because both children share the same Binance API and one being geo-blocked implies the other is too.
  - `tests/unit/utils/test_geo_block.py` (new): 18 tests covering detection, rejection, exit-code contract, operator message content.
- **Alternatives Considered:**
  - **Catch the specific `APIError` exception type and check its code/message.** Rejected — would tie the fail-fast logic to python-binance's exception hierarchy, making it fragile to library updates. String-signature matching is library-agnostic.
  - **Add `"Service unavailable"` to the signatures.** Rejected — false-positive risk on legitimate 503s. The two specific phrases we kept are unique to Binance regulatory rejections.
  - **Retry once with exponential backoff before fail-fast.** Rejected — the rejection is regulatory state, not load state; "wait and retry" cannot fix it.
  - **Auto-switch to a different region/proxy.** Rejected as out of scope; that's an infrastructure decision, not a code one. The fix path remains operator-driven via Railway dashboard.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-01
- **Implemented By:** New `src/utils/geo_block.py` module; integration in `run_paper_trading.py`, `run_live_trading.py`, `run_all.py`; 18 unit tests in `tests/unit/utils/test_geo_block.py`.
- **Affected Files:**
  - `src/utils/geo_block.py` (new)
  - `scripts/run_paper_trading.py`
  - `scripts/run_live_trading.py`
  - `scripts/run_all.py`
  - `tests/unit/utils/test_geo_block.py` (new)
- **References:** Commit 476878e (original March 2026 region fix), commit d14a9d2 (region key removed from railway.toml because Railway only supports dashboard region config), Railway logs from 2026-06-01T16:40 onward.

---

### DEC-2026-06-04-001: Adopt Research Layer PRD v2.0 — Bounded `research/` Module with One-Way Dependency

- **Decision:** Ratify `docs/research/RESEARCH_LAYER_PRD.md` v2.0 as the governing document for all research-layer work. Structure as a top-level `research/` module in the existing repository (NOT a separate project), with the strict one-way dependency rule: `src/` does NOT import from `research/`; `research/` imports from `src/` freely. Strategies graduate from research to production by moving the file from `research/generators/` to `src/core/strategy/generators/` via `scripts/promote_to_production.py`.
- **Context:** The PARAVANT trading system has matured to a production-quality MVP but the research process feeding it is ad-hoc (no pre-registration, no DSR, no per-symbol cost modeling, no leakage detection, no institutional memory of failed strategies). After three rounds of PRD review (v1.0 → critique → v2.0 → external review of v2.0 + four points baked in), the document is good enough to build. Continued refinement would itself become the "never finish building" trap the PRD warns against.
- **Rationale:**
  - **Bounded co-existence over full separation:** sharing data pipelines, regime detector, backtest engine, and decision audit is high-leverage; the one-way dependency boundary prevents research's exploratory standards from contaminating production code.
  - **No MVP scope change:** locked trading decisions (crypto-only, Binance-only, spot-long-only, market orders) remain in force. The research layer operates entirely upstream of live execution.
  - **Provability + capital-trajectory framing:** at $20 paper / $100 live floor capital, the research layer cannot serve near-term income generation. The framing is audit-grade documentation as the durable asset — supporting either external capital paths (raise, prop allocation, licensing) or the operator's eventual personal capital trajectory.
- **Alternatives Considered:**
  - **Separate project for research:** rejected — would force re-implementation tax on every promotion (research strategy → production strategy duplicates code) and split the decision audit trail.
  - **Mix research into `src/`:** rejected — would contaminate production code with exploratory standards and looser dependencies (sklearn, scipy, statsmodels).
  - **Keep ad-hoc research process:** rejected — produces structurally biased results (selection bias, cost-blindness, lookahead), as the BTF post-mortem demonstrates.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** `docs/research/RESEARCH_LAYER_PRD.md` v2.0
- **Affected Files:** `docs/research/RESEARCH_LAYER_PRD.md`, future `research/` directory tree
- **References:** External Claude critique cycles (3 rounds), DEC-2026-05-31-003 (portfolio capital model), DEC-2026-06-01-001/002 (auto-promotion gate to be amended)

---

### DEC-2026-06-04-002: Mandatory Methodology Primitives for Research Layer

- **Decision:** All research-stage strategy evaluation MUST use the following methodology primitives, enforced by `scripts/eval_research_strategy.py`: (1) **Pre-registration** — every hypothesis declares expected PF, Sharpe, regime, and fail modes BEFORE backtest; CLI refuses to run if missing. (2) **Per-symbol cost modeling** — spread (95th percentile historical) + fee (Binance taker) + slippage (per-symbol historical), with cost model "verified" only against ≥10 real paper-trading fills per symbol; until verified, costs default to 2x estimate (extra-conservative). (3) **Leakage detection** — automated checks for future timestamps in lookback, survivor bias, restatement bias, index reconstitution effects; CLI refuses to run if leakage detected. (4) **Walk-forward validation** — rolling 6-month train / 1-month test for ALL parameter optimization; test data NEVER seen during parameter selection. (5) **Deflated Sharpe Ratio (DSR)** — Bailey/Lopez de Prado 2014, with proper effective-K counting (parameter combos × symbols × timeframes, NOT just ledger entries).
- **Context:** The previous research process lacked all five primitives. The recently-retired BTF strategy (Q1 100% WR → live PF 0.75) likely failed from a combination of thin-sample overfit + cost-blindness + selection bias — protected against by these primitives.
- **Rationale:**
  - **Cost modeling is THE most likely cause of historical backtest-to-live degradation.** On a strategy with 2.8% wins / 1.4% losses, a 0.5% round-trip cost flips PF from 1.5 to <1.0. Without honest cost modeling, backtest results are systematically optimistic.
  - **Leakage detection is cheap insurance.** A 100% backtest WR is almost always a bug (lookahead, restatement, survivor) — not selection bias. Detection catches the bug class.
  - **Effective K must include the full hypothesis space.** A grid search of 100 parameter combos × 5 symbols × 3 timeframes = 1,500 effective trials per hypothesis, not 1. The previous (v1.0) homemade multiple-testing formula `1 + 0.05 * ln(K)` was arbitrary and undercounted K by 2-3 orders of magnitude — removed from v2.0; DSR (which already incorporates effective K correctly) is the sole correction.
  - **Walk-forward is the only structural overfit protection.** Single-window optimization on full history is the #1 cause of overfit.
  - **Pre-registration eliminates "I knew it would work" bias.** Results dramatically exceeding pre-registration are a RED FLAG (likely overfit or leakage), not a green light.
- **Alternatives Considered:**
  - **Optional methodology (operator chooses):** rejected — defeats the purpose; methodology that's optional gets skipped under deadline pressure.
  - **Keep homemade multi-testing formula:** rejected — not Bonferroni-equivalent, 0.05 coefficient arbitrary, redundant with DSR.
  - **K = ledger entries only:** rejected — undercounted by 2-3 orders of magnitude, provided no real protection.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** Phase R0.5 (weeks 1-4) — `research/backtest/cost_model.py`, `research/backtest/leakage_check.py`, `research/backtest/walk_forward.py`, `research/validation/deflated_sharpe.py`, `research/validation/effective_k.py`
- **Affected Files:** `scripts/eval_research_strategy.py` (orchestrator), all of above
- **References:** Bailey & Lopez de Prado 2014 (DSR), Lopez de Prado 2018 (CPCV, deferred), BTF post-mortem (project_backtest_results.md)

---

### DEC-2026-06-04-003: Hypothesis Ledger + Strategy Biography as Canonical Research Truth

- **Decision:** Two YAML-based artifacts are the canonical source of research truth: (1) `research/hypotheses/ledger.yaml` — every hypothesis ever proposed, with pre-registration fields and current status; (2) `research/biographies/<strategy_id>.yaml` — full lifecycle record of every strategy from hypothesis through retirement, including hypothesis history, parameter history, optimization history, backtest history, paper trading history, live deployment history, decay events, re-optimization attempts, decision log, and post-mortem (if retired). Database tables with `research_` prefix are projections of YAML for querying — YAML is canonical, DB is derived.
- **Context:** Without a canonical ledger, hypotheses get re-tested, lessons get lost, and the "graveyard" becomes dead weight instead of an active learning library. The biography schema is the same for active and retired strategies — retirement adds the post-mortem section but does not change the data structure. This makes "active vs retired" a status field, not a structural divide.
- **Rationale:**
  - **YAML over DB-as-source-of-truth:** human-editable, version-controlled in git, survives database migrations, readable without tooling.
  - **Continuous biography (full circle):** captures the WHY behind every decision, supports informed operator review at Tier B deployment decisions, feeds back into future hypothesis pattern-matching via post-mortems.
  - **Decisions inline in biography:** every state change references the DEC ID from DECISIONS.md, providing complete audit trail.
  - **Pattern tags in post-mortems:** retired strategies' lessons are queryable; new hypothesis at Stage 2 surfaces similar past failures.
- **Alternatives Considered:**
  - **Database as canonical, YAML as export:** rejected — schema migrations would lock the format too rigidly; YAML's flexibility serves exploratory research better.
  - **Markdown documents per strategy:** rejected — too unstructured for programmatic queries (effective K calculation, pattern matching).
  - **Skip biographies, use just the ledger:** rejected — loses the institutional memory that turns the graveyard into a library.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** `research/hypotheses/ledger.yaml`, `research/biographies/` directory, `research/biographies/schema.py`
- **Affected Files:** Hypothesis ledger entries (Appendix B of PRD), strategy biography template (Appendix A), post-mortem template (Appendix C)
- **References:** DEC-2026-06-04-002 (methodology primitives feed into biography fields), DEC-2026-06-04-011 (post-mortem closes the circle)

---

### DEC-2026-06-04-004: Strategy Graduation Path — `research/generators/` → `src/core/strategy/generators/`

- **Decision:** Strategies graduate from research to production by literally moving the file from `research/generators/<name>.py` to `src/core/strategy/generators/<name>.py` via `scripts/promote_to_production.py`. The CLI runs all production-code-quality checks (type hints, docstrings, unit tests, zero-tech-debt compliance), updates STRATEGY_CONFIG with the new entry, files a decision in DECISIONS.md referencing the promotion, and creates a git commit. **No re-implementation tax** — the same code that ran research-stage evaluation runs in production.
- **Context:** Most quant systems pay an "integration tax" when research strategies are re-implemented as production strategies (production team rewrites for performance/correctness, introducing bugs). The one-way dependency rule plus this graduation path eliminates that tax: research code is already importing from `src/` for shared infrastructure, so the only change at promotion is the file location.
- **Rationale:**
  - **Single implementation across pipeline:** what got DSR-validated in research is what runs in paper and live. No translation, no bugs.
  - **Production quality bar enforced at promotion:** the script refuses to promote until the code meets production standards (full type hints, docstrings, tests).
  - **Decision-log integration:** every promotion files a DEC entry with rationale and timing, supporting the audit-grade documentation goal.
- **Alternatives Considered:**
  - **Keep research and production as parallel directories with cross-imports:** rejected — would break the one-way dependency rule.
  - **Re-implement at promotion:** rejected — introduces bugs and discourages promotion.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** `scripts/promote_to_production.py` (Phase R0.5)
- **Affected Files:** All research strategies that graduate
- **References:** DEC-2026-06-04-001 (one-way dependency rule), DEC-2026-06-04-009 (opt-in deployment)

---

### DEC-2026-06-04-005: Paid Alt-Data Deferred to Capital Threshold ≥ $25,000 (Not Calendar Date)

- **Decision:** Paid alt-data subscriptions (Glassnode at $39-$799/month, CryptoQuant at $29-$499/month, Coin Metrics Network Data Pro) are DEFERRED until working capital reaches a structural threshold, NOT a calendar date. Thresholds: Glassnode + CryptoQuant ≥ $25,000 capital; Coin Metrics Pro ≥ $50,000; Delphi Digital ≥ $100,000.
- **Context:** PRD v1.0 placed paid alt-data integration in Phase R4 (months 11-14, calendar-scheduled). External review correctly noted the math doesn't pencil at sub-$25k capital: $68/month for the starter Glassnode + CryptoQuant subscriptions is $816/year. At $10k capital with a realistic 30% annual return, that's $3,000 gross — the subscription consumes 27% of gross profit. At $1k capital, the subscription is LARGER than realistic annual returns.
- **Rationale:**
  - **Subscription ROI must be structurally affordable.** Tying deferral to capital, not calendar, prevents the "we're in month 11 so we should subscribe" trap.
  - **Free alternatives suffice at current scale.** Binance futures funding rates and open interest are available for free via API. Fear & Greed Index is free. These cover the most impactful crypto-native signals.
  - **No commitment by default.** Decision frames paid alt-data as conditional, not promised; reduces psychological pressure to "use the subscription we're paying for" (sunk-cost trap).
- **Alternatives Considered:**
  - **Subscribe at Phase R4 regardless of capital (v1.0 framing):** rejected — math doesn't pencil; subscription would consume disproportionate share of returns.
  - **Subscribe immediately for the data flow itself:** rejected — research value of unused data subscription is zero.
  - **Never subscribe (free data only forever):** rejected — at $25k+ capital, alt-data unlocks genuinely uncorrelated edge sources worth pursuing.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** Section 11.4 of Research Layer PRD v2.0, Appendix D Phase R4 condition
- **Affected Files:** `docs/research/RESEARCH_LAYER_PRD.md`
- **References:** External Claude review (capital-relative subscription math), DEC-2026-05-31-003 (current capital structure: $20 paper / $100 live floor)

---

### DEC-2026-06-04-006: Permanent Non-Goals — Structurally Inaccessible or Discredited Capabilities

- **Decision:** The following capabilities are PERMANENTLY out of scope for the research layer, either because they are structurally inaccessible to retail or because the academic literature is clear they do not produce sustainable edge:
  1. Price-direction ML models (LSTM/Transformer on OHLCV) — literature is clear they almost always overfit
  2. Deep reinforcement learning agents — fail catastrophically in production
  3. Auto-discovered strategies without human hypothesis — produce spurious correlations, data mining bias
  4. HFT / microstructure strategies — retail latency uncompetitive
  5. Tick-data infrastructure — storage cost prohibitive, marginal value over OHLCV at our timeframes
  6. Proprietary alt-data licensing (satellite, ship tracking) — institutional cost (5-7 figures/year)
  7. Co-location at exchanges — requires exchange floor space rental
  8. Internal market making — institutional capital + regulatory approval required
  9. Capacity analysis (size-driven slippage modeling) — not relevant below $25k account; deferred above threshold
- **Context:** Explicitly naming what we will NOT build is as important as naming what we will. Future Claude sessions, future operator instincts, and future "what if we tried..." moments all have a documented answer.
- **Rationale:**
  - **Discipline preservation:** without explicit non-goals, the scope-creep gradient is one-way (always toward more features).
  - **Lesson hard-won:** earlier project iterations included RL (PPO/DDPG) and genetic discovery in the decision layer. Excluding them is institutional learning, not received wisdom.
  - **Cost-relative analysis:** items 5-7 fail on cost-effectiveness for retail. Items 1-3 fail on academic evidence. Items 8 and 9 fail on structural access.
- **Alternatives Considered:**
  - **Leave non-goals implicit (the v1.0 approach):** rejected — silence allows scope creep over years.
  - **Include some "maybe later" for ML/RL:** rejected — ambiguity is worse than firm exclusion; if it changes, that change requires explicit decision-log entry.
- **Status:** LOCKED — modification requires explicit PRD update + decision-log entry with strong justification
- **Date Decided:** 2026-06-04
- **Implemented By:** Section 4.1 of Research Layer PRD v2.0
- **Affected Files:** `docs/research/RESEARCH_LAYER_PRD.md`
- **References:** Lopez de Prado's "Advances in Financial Machine Learning" (ML hardness in finance), prior PARAVANT iterations (RL/genetic discovery removed)

---

### DEC-2026-06-04-007: Research Layer Does NOT Advance MVP Scope

- **Decision:** Building the research layer does NOT advance PARAVANT to V1 or V2 of the trading system. The MVP scope rules (crypto-only, Binance-only, spot-long-only, market orders) remain locked. Research can STUDY strategies that would require out-of-scope features (multi-broker arbitrage, limit orders, futures) but those strategies CANNOT enter the live deployment pipeline without explicit unlocking via new locked-decision review.
- **Context:** Adding rigorous research methodology to the existing trading system is depth investment within current scope, NOT scope expansion. Research findings might surface ideas that require out-of-scope features ("this strategy needs limit orders to work properly") — those are flagged as deferred-until-trading-V1, not actioned in research.
- **Rationale:**
  - **Locked decisions remain locked.** DEC-2026-01-15-001 through DEC-2026-01-15-005 are unchanged by this PRD.
  - **Research operates upstream of live execution.** No research-layer change touches `scripts/run_live_trading.py` execution paths.
  - **Live deployment criteria (Tier system) STRENGTHEN the locked decisions** by adding DSR + cost-verification + leakage-check floors on top of existing thresholds.
- **Alternatives Considered:**
  - **Use research findings to push for V1 features:** rejected — sequencing matters; research v0.5 must prove the funnel produces survivors before scope expansion is justified.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** Section 4.2 of Research Layer PRD v2.0
- **Affected Files:** `docs/research/RESEARCH_LAYER_PRD.md`, `.claude/rules/mvp-scope-control.md` (unchanged, reaffirmed)
- **References:** DEC-2026-01-15-001 through DEC-2026-01-15-005 (locked MVP decisions)

---

### DEC-2026-06-04-008: Hybrid Tier A/B/C/D Promotion Model with DSR p<0.3 as Non-Negotiable Statistical Floor

- **Decision:** Replace binary auto-promotion (pass/fail) with a graduated four-tier classification system: **Tier A (FULL_READY)** — DSR p<0.2, MaxDD<5%, PF≥1.35, Sharpe≥1.0, N≥30 → recommended for 100% capital slice deployment; **Tier B (PROVISIONAL_READY)** — DSR p<0.3, MaxDD<5%, PF≥1.25, Sharpe≥0.8, N≥20 → recommended for 50% capital slice deployment (the modal year-1 deployment, given trade-frequency math); **Tier C (NEEDS_WORK)** — DSR p<0.5 OR multiple soft misses → cannot deploy, needs more data or re-optimization; **Tier D (REJECT)** — DSR p≥0.5 OR MaxDD≥10% OR leakage detected OR PBO>0.5 → auto-shelved with post-mortem. Classification is mechanical, based on objective criteria. **No manual override path exists.** The Deflated Sharpe Ratio p-value < 0.3 is the **non-negotiable statistical floor** below which no strategy can deploy at ANY capital allocation, regardless of any other consideration. Hard floors also include MaxDD<5% for Tiers A/B, cost model verified, and leakage check passed.
- **Context:** The operator correctly identified that binary auto-promotion gates are methodologically wrong: a strategy with PF 1.34 vs threshold 1.35 is statistically indistinguishable from one with PF 1.36, but the binary gate treats them as categorically different. The proposed solution was a "human override" path for strategies that "almost pass." This is the most well-documented failure mode in quant research (confirmation bias). The Tier B mechanism achieves the operator's intent (smaller bets on "almost-passing" strategies) without the override mechanism (which destroys rigor).
- **Rationale:**
  - **Tier B handles "almost-passing" mechanically, not via judgment.** Reduced capital instead of zero capital. No override required.
  - **DSR is the right tool for a non-binary decision.** It encodes the probability that the edge is real, not a binary pass/fail.
  - **Hard floors prevent the override doorway.** A strategy below DSR p<0.3 cannot deploy at any allocation. This is what separates "graduated rigor" from "human override defeats rigor."
  - **Modal year-1 deployment is Tier B, not Tier A.** Given 12 trades/quarter at 4H/1D, N=30 takes 7-8 months per strategy. Most year-1 deployments will be Tier B at N=20-29 — this is consciously the steady state, not the exception.
  - **N=20 floor (raised from initial N=15 proposal) hedges against DSR's reduced reliability at very small N.** Below N≈20, skew and kurtosis estimates that DSR depends on become structurally unmeasurable.
  - **Tier classification uses BACKTEST N as primary signal.** Live performance never re-tiers a strategy upward; downward only via decay guardrail (Stage 10).
- **Alternatives Considered:**
  - **Keep binary auto-promotion + add manual override path:** rejected — most well-documented failure mode in quant research (confirmation bias).
  - **Tier B at N≥15 (initial proposal):** rejected — DSR's skew/kurtosis estimates structurally unmeasurable below N≈20; "DSR p<0.3 at N=15" carries materially less weight than at N=25.
  - **Allow operator to bypass hard floors with documented reasoning:** rejected — the floor IS the protection; an opt-out path destroys it.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** `research/promotion/classifier.py`, `research/promotion/floors.py`, `scripts/classify_strategy.py`
- **Affected Files:** Section 9 of Research Layer PRD v2.0
- **References:** Operator review 2026-06-04 (proposed tier system), external Claude review 2026-06-04 (N=20 floor + modal-deployment honesty), DEC-2026-06-04-009 (opt-in deployment), DEC-2026-06-01-001/002 (will be amended)

---

### DEC-2026-06-04-009: Opt-In Deployment for ALL Tiers — Overrides DEC-2026-06-01-001 Opt-Out Behavior

- **Decision:** All live deployments require explicit operator action (click DEPLOY). The system NEVER auto-deploys, regardless of tier classification. Tier A and Tier B both result in NOTIFICATIONS to the operator with biography link; deployment requires the operator's explicit click. This honors the trading PRD's Section 1.7 locked decision ("Autonomy model: Human approval for live deployment") and **overrides the previous opt-out behavior of DEC-2026-06-01-001/002** (which auto-activated tiers passing the gate unless operator vetoed).
- **Context:** DEC-2026-06-01-001 was designed to protect against the "never deploy" trap by auto-activating ready strategies. External review correctly noted this silently flipped the trading PRD's locked autonomy posture from opt-in (human approval) to opt-out (auto-deploy unless vetoed). The two cannot both hold; the trading PRD's locked decision wins.
- **Rationale:**
  - **Locked decision in trading PRD takes precedence.** Section 1.7 ("Human approval for live deployment") is the explicit autonomy posture for the system.
  - **Opt-in at N=30 (Tier A) is meaningful protection.** MaxDD<5% over 30 trades can be pure luck; Sharpe at N=30 has wide CI. Operator review is the right protection at this sample size.
  - **"Never deploy" trap addressed by Tier system + calibration tracking, not by opt-out.** Strategies that have been Tier A or B for >2 weeks without deployment decision are flagged in calibration report. This pressures deployment via visibility, not via automatic action.
- **Alternatives Considered:**
  - **Keep opt-out behavior of 06-01-001:** rejected — contradicts trading PRD locked decision; opt-out at small N is statistically risky.
  - **Opt-out for Tier A, opt-in for Tier B:** rejected — inconsistent autonomy posture is the worst configuration (two mental models to keep in mind).
- **Status:** ACTIVE — supersedes opt-out behavior aspect of DEC-2026-06-01-001 and DEC-2026-06-01-002
- **Date Decided:** 2026-06-04
- **Implemented By:** Updates to `scripts/run_live_trading.py` (`_paper_strategy_classification`, `_tier1_activation_blocked`), notification dispatcher, `scripts/deploy_live.py` CLI
- **Affected Files:** Section 9.7 of Research Layer PRD v2.0, `scripts/run_live_trading.py`
- **References:** Trading PRD Section 1.7 (locked autonomy decision), DEC-2026-06-01-001 and DEC-2026-06-01-002 (require amendment), external Claude review 2026-06-04

---

### DEC-2026-06-04-010: Pre-Registered Stop/Pivot Gate at 2026-12-01 with Verified-Cost-Model Criteria

- **Decision:** A pre-registered stop/pivot gate fires on **2026-12-01** (hard date) with the following evaluation criteria: **(A) Continue building** if at least 1 strategy has reached stable Tier A or Tier B classification AND at least 10 hypotheses tested through full pipeline AND cost model verified for 3+ symbols AND operator calibration delta < ±30% on average. **(B) STOP and reassess** if 20+ hypotheses tested with verified cost models + clean leakage checks AND zero have achieved Tier A or Tier B classification AND DSR p-values consistently > 0.5. **Pre-registered definition of "verified cost model"** (to prevent escape-hatch drift): validated against ≥10 actual paper trading fills per symbol; validation must show actual fills within 20% of cost model prediction. **If hard date arrives without methodology verification: failures count anyway.** No further development of Phase R4+ until reassessment.
- **Context:** PRD v1.0's 30-week roadmap was structurally vulnerable to the "never finish building" trap — 2 years of tooling with zero deployed strategies, rigor as alibi. The hard date + soft criterion combo protects against this. External review correctly noted the cost-verification bottleneck means the hard date will likely fire before the soft "20 verified hypotheses" criterion is fully met for newly-introduced symbols — this is acceptable; the hard date is the protection-of-record.
- **Rationale:**
  - **Hard date prevents methodology-theater escape hatches.** Without "failures count regardless of validation status" clause, the operator could perpetually delay the stop by claiming "we just need to verify a few more symbols first."
  - **Verified cost model criterion is pre-registered to prevent drift.** ≥10 fills + 20% accuracy requirement is locked NOW, cannot be relaxed later.
  - **Soft criterion is honest-check, not escape hatch.** It functions as additional protection on the same axis as the hard date.
  - **Continue criteria are intentionally permissive.** "At least 1 Tier A or B" is achievable evidence the funnel works; the goal is to detect "this approach genuinely doesn't work," not to set an aggressive bar.
- **Alternatives Considered:**
  - **Calendar only (no soft criterion):** rejected — would fire even if approach is clearly working; soft criterion provides honest-check evidence.
  - **Soft criterion only (no hard date):** rejected — "we just need to verify a few more symbols" becomes permanently deferrable.
  - **Different threshold for failures (10 instead of 20):** rejected — 20 provides stronger evidence that the approach is structurally flawed vs just unlucky.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** Section 14.2 of Research Layer PRD v2.0; manual evaluation by operator on 2026-12-01
- **Affected Files:** `docs/research/RESEARCH_LAYER_PRD.md`
- **References:** External Claude review 2026-06-04 (escape-hatch concern), Risk 14.10 of Research Layer PRD (never deploy trap mitigation)

---

### DEC-2026-06-04-011: Strategy Lifecycle Pipeline Closes the Circle — Post-Mortem Completes Every Retired Strategy

- **Decision:** The strategy lifecycle is an 11-stage CIRCLE, not a linear pipeline. The eleventh stage — POST-MORTEM — is mandatory for every retired strategy. The post-mortem (see Appendix C of PRD) is a structured causal analysis containing: lifecycle summary, primary cause classification (REGIME_SHIFT, PARAMETER_DECAY, MARKET_STRUCTURE_CHANGE, NEVER_VALIDATED, STATISTICAL_NOISE, OPERATIONAL_FAILURE), multi-paragraph causal analysis, contributing factors, lessons extracted with pattern tags, related active strategies with shared risk factors, and searchable terms for graveyard indexing. **Post-mortems feed back to Stage 1 (sourcing)** via pattern-tag matching — when a new hypothesis is proposed, the system surfaces post-mortems sharing pattern tags ("this hypothesis is similar to STRAT_XXX which failed because of regime-detector lag"). The graveyard is a learning library, not a memorial.
- **Context:** Most retail quant systems treat retired strategies as dead weight — configs deleted, data archived, lessons forgotten. The post-mortem completes the full-circle institutional memory function.
- **Rationale:**
  - **The retired strategy IS the lesson.** Each failure carries information about which hypotheses are riskier than they appear.
  - **Pattern-tag matching surfaces relevant lessons automatically.** Future hypotheses get matched against retired strategies without requiring the operator to remember everything.
  - **The biography is the SAME for active and retired strategies.** Only the post-mortem section is added; the data structure does not change. "Active vs retired" is a status field, not a structural divide.
  - **Compounding institutional memory.** Year 2 hypotheses benefit from year 1 post-mortems automatically.
- **Alternatives Considered:**
  - **Skip post-mortems for "obvious" failures:** rejected — "obvious" failures are exactly the ones that re-occur because no one wrote down why.
  - **Post-mortem as free-form text only:** rejected — pattern tags require structured fields for queryability.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** Section 10 Stage 11 of Research Layer PRD v2.0, Appendix C post-mortem template, `research/biographies/retired/` directory, `scripts/generate_post_mortem.py` (conditional per DEC-2026-06-04-008's R3.5 deferral; manual generation initially)
- **Affected Files:** Strategy biography schema (Appendix A), post-mortem template (Appendix C)
- **References:** Operator request 2026-06-04 ("post-mortem completes the full process, around the circle"), DEC-2026-06-04-003 (biography schema)

---

### DEC-2026-06-04-012: Provability + Future-Capital-Trajectory Framing — Audit-Grade Documentation as Durable Asset

- **Decision:** The research layer is built under a hybrid framing confirmed by the operator: **(1) Build for provability** — audit-grade documentation that could support external capital paths (raise, prop allocation, licensing) if those materialize. Strategy biographies, decision logs, DSR-validated metrics, full-circle lifecycle tracking are first-class deliverables. **(2) Build for the operator's actual future capital trajectory** — whatever capital materializes from other sources (work, savings, business) finds a research-ready system waiting. The framing explicitly REJECTS: promising near-term income (math doesn't work at $20-$10k capital), framing as "preparing for a fundraise" (no fundraise planned), shortcuts on rigor ("it's only $100, doesn't matter"), and scope creep ("more features = more impressive").
- **Context:** Three rounds of PRD review surfaced the implicit assumption that the system was being built for income generation. At current scale ($20 paper / $100 live floor), this is structurally impossible — even spectacular 50% annual returns on $100 produce $50, not income. The "which game" question needed explicit answering. Operator confirmed both framings simultaneously on 2026-06-04.
- **Rationale:**
  - **The rigor is the asset, durable independent of any specific strategy.** Strategies decay; the methodology + documentation persists.
  - **Allocators weight real live performance heavily, even tiny live performance.** Going live at $100 starts the only clock that matters for the provability prize.
  - **Future capital trajectory is unknown.** Building to allocator-grade standards keeps optionality open without committing to any specific external-capital path.
  - **What we are NOT building:** a system whose unspoken goal is near-term income via $100 of capital. That goal cannot be reached by this system at this capital; naming it explicitly prevents drift.
- **Alternatives Considered:**
  - **Build for income generation only:** rejected — math doesn't work at $20-$10k capital; this framing leads to disappointment or shortcuts on rigor.
  - **Build for learning/IP only (accept no income for years):** rejected — under-sells the durable asset that is being built.
  - **Right-size time allocation downward:** rejected by operator — 70% allocation to research over 2 years is the operator's chosen investment.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-04
- **Implemented By:** Section 2.4 of Research Layer PRD v2.0
- **Affected Files:** `docs/research/RESEARCH_LAYER_PRD.md`
- **References:** External Claude reviews 2026-06-04 (raised "which game are we playing" question), operator confirmation 2026-06-04, DEC-2026-05-31-003 (current capital structure)

---

### DEC-2026-06-04-013: Retrospective DSR Cost Application — Incremental Pad Over Booked Costs (Data-Reality Driven)

- **Decision:** The retrospective DSR run (`scripts/retrospective_dsr.py`) applies the v0 conservative cost model as an **INCREMENTAL pad over costs the simulator already booked**, NOT by re-subtracting a full cost model from the recorded returns. The recorded per-trade `return_pct` (the canonical trade source) is already net of the simulator's commission and slippage, so the realistic BASE case is the recorded return unchanged, and the CONSERVATIVE case subtracts only `max(0, conservative_round_trip_cost_pct − booked_cost_pct)`. Three consequent implementation facts are locked in:
  1. **Canonical trade source is `PaperTradingSession.trade_log`** (a JSON array of `TradeRecord` dicts), selected by `session_id` prefix `paper_<LABEL>_`. There is no `paper_trades` SQL table (the spec's first-draft assumption). This is the SAME source `scripts/validation_report.py` reads, preserving single-source-of-truth, and it reuses `_is_corrupt_force_close` for the PARA-02 quarantine.
  2. **Realized slippage cannot be measured.** No `signal_price`/`fill_price` fields exist; `entry_price`/`exit_price` ARE the post-slippage fills. So spread and slippage are ESTIMATED (2x-padded) for every symbol per the single-pad rule (the fee is exact and never padded). Recorded as a caveat in every biography.
  3. **Effective K is an estimated lower bound, not DB-reconstructed.** No parameter-combination counts are recorded in the trade-log DB for these 11 strategies, so K is estimated (~1150 point / 2000 gating) with the mandatory multi-K sweep {115, 500, 2000} and an unconditional `variance_sr` sweep; the gating verdict uses the most conservative end. Derivation stored in each biography (`is_lower_bound: true`).
- **Context:** Implementation session 2026-06-05 reconnaissance found the trade data differs materially from `docs/research/RETROSPECTIVE_DSR_SPEC.md` Section 5.1's assumptions. Applying the spec's cost model literally to already-net recorded returns would double-charge commission + slippage, rejecting real edge by being too harsh — the exact failure mode the spec's Section 6.5 warns against. Operator (Eva) was presented the fork and chose "Incremental pad only" on 2026-06-05.
- **Rationale:**
  - **No double-counting.** Recorded returns already embed the in-sim costs; the conservative case charges only the excess over what is booked, floored at zero.
  - **Leg-aware notional preserved.** Exit-leg cost is charged on exit notional (`exit_price/entry_price` scaling) so large winners are not under-costed (spec 5.5-pre).
  - **Honest about unmeasurable components.** Estimating slippage and flagging it beats fabricating a realized-slippage number from data that does not exist.
  - **Conservative K gates.** Because no opt history exists to reconstruct K, the swept high end (2000) gates, keeping verdicts honest rather than optimistic.
- **Alternatives Considered:**
  - **Reconstruct gross then re-cost:** rejected by operator — live records lack a separable slippage figure (real slippage is embedded in fills), making the add-back asymmetric and itself a source of double-charge on the live leg.
  - **Spec-literal full re-subtraction:** rejected — double-charges costs on already-net returns, manufacturing Tier-D verdicts out of real-but-modest edge.
- **Status:** ACTIVE — AMENDED by DEC-2026-06-04-014 (2026-06-06): the cost logic (incremental pad over already-net returns) is UNCHANGED and now also applies to regenerated backtest trades; only the trade-DATA SOURCE is extended from paper-session logs to regenerated rolling-backtest per-trade series, because the 2026-06-05 Neon run proved the paper logs are near-empty (geo-block) and the promoted-strategy backtest per-trade data was never persisted.
- **Date Decided:** 2026-06-05
- **Implemented By:** `scripts/retrospective_dsr.py`, `research/backtest/cost_model.py`, `research/validation/effective_k.py`, `research/promotion/classifier.py`, `research/biographies/schema.py`, `scripts/show_strategy.py`; tests in `tests/research/`
- **References:** `docs/research/RETROSPECTIVE_DSR_SPEC.md` (Sections 5, 5.5, 6), DEC-2026-06-04-002 (methodology primitives), DEC-2026-06-04-008 (Tier A/B/C/D + DSR floor), DEC-2026-05-31-002 (PARA-02 quarantine), operator decision 2026-06-05. NOTE: the run on real Neon trade logs is executed by the operator (local DATABASE_URL points at an empty SQLite); tier-change DEC entries for individual KEEP strategies are filed AFTER that run.

---

### DEC-2026-06-04-014: Retrospective/Regime-Conditional DSR Data Source — Regenerated Backtest Trades Over Empty Paper Logs (Reality-Driven; pulls Phase B forward)

- **Decision:** The retrospective DSR data source changes from paper-session trade logs (`PaperTradingSession.trade_log`, per DEC-2026-06-04-013) to **REGENERATED rolling-backtest per-trade series** produced on demand by re-running `BacktestEngine` on each strategy's real config. The retrospective is extended into **regime-conditional DSR** (Phase B of the research roadmap, pulled forward): DSR is computed both POOLED per strategy AND separately WITHIN each market-regime bucket of the strategy's backtest trades, producing a strategy x regime coverage matrix. The 2026-06-04-013 cost model (incremental pad over already-net returns) is UNCHANGED and applies identically to backtest trades (verified below). Five non-negotiable guards bind regime-conditional DSR:
  1. **It is a SCREEN, not a deployment gate.** Backtest edge degrades live. A regime-DSR pass identifies which strategy x regime pairs are WORTH paper-trading; paper/live remains the deployment gate. A regime-DSR-validated backtest NEVER bypasses paper validation.
  2. **K counts regime-buckets as trials.** effective_K = param-combos x symbols x timeframes x REGIME-BUCKETS. Slicing 8 regimes and keeping the best is selection bias across regimes; if K does not penalize it the deflation is fake. `research/validation/effective_k.py` is extended for the regime-bucket multiplier.
  3. **Causal regime tagging + leakage test.** Each trade is tagged with the SubRegime active AT ENTRY using only data available at that time (`historical_classifier.classify_series` on BTC daily, verified causal: each label uses EMA/ADX/trailing-ATR-percentile at bar i only). A leakage test asserts label[i] computed on `series[:i+1]` equals the full-series label[i].
  4. **Coarse buckets where N is thin.** Start with coarse buckets (bull/bear/chop); use fine SubRegimes only where per-bucket N supports DSR. Per-bucket results below a minimum N are DESCRIPTIVE (INSUFFICIENT_DATA), not gating.
  5. **DSR is necessary, not sufficient.** A regime-DSR pass means the backtest edge is distinguishable from selection-bias luck — a strong screen, not a guarantee of live performance.
- **Context:** The 2026-06-05 operator-run retrospective against Neon (read-only) returned all 11 strategies as TIER_D_REJECT, but with N=0 for 6 of 11 and N<=4 for 4 more — only BTF had analyzable N (25). Reconnaissance established WHY: (a) paper trading has been down (Railway geo-block, DEC-2026-06-01-003) so paper sessions opened but orders never filled — `PaperTradingSession.trade_log` is near-empty; (b) the per-trade backtest data that justified the KEEP promotions was NEVER persisted — `scripts/backtest_rolling.py` prints/summarizes but does not store per-trade logs; (c) the local SQLite `data/trading.db` holds only old single-symbol MVP-template BTC backtests (all losing: macd_pullback BTC PF 0.26/-54.7%), NOT the regime-routed research configs. DSR requires a per-trade RETURN SERIES (it derives Sharpe/skew/kurtosis); aggregate PF/Sharpe summaries cannot feed it. Regeneration is the only source of that series for the KEEP strategies. Operator (Eva) chose "build the regenerate path" on 2026-06-06.
- **Rationale:**
  - **Cost-model carryover is verified, not assumed.** `portfolio.close_position()` computes `realized_pnl = gross_pnl - total_commission` with slippage already in `fill_price`, then `return_pct = realized_pnl/entry_value*100` (`src/core/strategy/backtest/portfolio.py:245`). So backtest `return_pct` is NET of commission+slippage — the same already-net property as paper. The incremental-pad logic carries over with zero changes; booked round-trip = 2x(commission_rate 0.1% + slippage_rate 0.05%) = 0.30% (matches the ~0.30% the Neon run reported).
  - **The Neon run still has value: it validated the instrument.** BTF (the known-bad calibration control) returned N=25, raw PF 0.75 (matching its documented live PF 0.75), adjusted 0.54, Tier D — the instrument correctly fails the strategy that deserved to fail, with a healthy cost diagnostic. The instrument is sound; the DATA was the problem.
  - **Regime-conditional answers the portfolio-construction question before paper trading.** It reveals coverage gaps (e.g. TRENDING_BULL uncovered) and tells us which strategy x regime pairs merit paper validation — directly serving the provability framing (DEC-2026-06-04-012).
- **Alternatives Considered:**
  - **Repoint at local SQLite as-is:** rejected — `data/trading.db` lacks the KEEP-strategy per-trade data; its only backtests are old losing single-symbol BTC template runs.
  - **Wait for paper data to accumulate:** rejected as the near-term answer — paper is geo-blocked and N=30 takes 7-8 months/strategy (PRD 3.4); the regenerate path answers now while paper remains the eventual deployment gate.
  - **Trust the aggregate PF/Sharpe summaries in project notes:** rejected — DSR needs the per-trade series; summaries cannot produce skew/kurtosis.
- **Consequent actions locked in:**
  1. The 11 paper-based TIER_D biographies from the 2026-06-05 run are NOT canonical edge verdicts (data-starved). They are superseded by the regenerated run and MUST NOT trigger any retirement/demotion. No KEEP strategy is retired on the basis of the Neon run.
  2. The classifier gains an **INSUFFICIENT_DATA** guard (minimum-N floor) so a strategy/bucket below the floor is reported as INSUFFICIENT_DATA, never TIER_D_REJECT — "no data" and "rejected as noise" are different states.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-06
- **Implemented By:** `research/backtest/regime_tagging.py` (causal per-trade tagging + runnable leakage self-check), `research/validation/effective_k.py` (`regime_conditional_k` bucket-multiplier extension), `research/promotion/classifier.py` + `research/biographies/schema.py` (`Tier.INSUFFICIENT_DATA` guard + `regime_coverage` models), `scripts/regime_dsr.py` (regeneration via `BacktestEngine`, pooled + per-regime DSR reusing `analyze_strategy`, coverage matrix + biography `regime_coverage` writes), tests in `tests/research/` (`test_regime_tagging.py`, `test_regime_dsr.py`, classifier/effective_k additions); hypothesis `research/hypotheses/ledger.yaml` entry `H-2026-06-001`. NOTE: regeneration was folded into `scripts/regime_dsr.py` (peer to `backtest_rolling.py`/`retrospective_dsr.py`) rather than a separate `research/backtest/regenerate.py`, to keep the dependency direction clean (no `research/` -> `scripts/` import) and reuse `analyze_strategy` as the single statistical-core source of truth.
- **References:** DEC-2026-06-04-013 (amended — cost logic intact, data source extended), DEC-2026-06-04-008 (Tier A/B/C/D + DSR floor), DEC-2026-06-04-012 (provability framing), DEC-2026-05-27-008 (regime-aware backtest validation / historical_classifier), DEC-2026-06-01-003 (geo-block), operator decision 2026-06-06. PRD Sections 8.5, 9, Appendix A (`regime_coverage`), Appendix B (ledger).

---

### DEC-2026-06-04-015: Backtest Engine `lookback_window` Optimization (O(n^2) -> O(n), Opt-In, Equivalence-Gated)

- **Decision:** Add an OPT-IN `lookback_window: int | None = None` parameter to `BacktestEngine.run_backtest`. When `None` (default), each bar's signal is generated from the FULL history up to that bar -- the original behavior, byte-for-byte unchanged, so every existing caller (production backtests) is unaffected. When set to `W`, the engine passes only the trailing `max(W, min_bars)` bars to the generator each step, collapsing the per-bar indicator recomputation from O(i) to O(W) and the whole loop from **O(n^2) to O(n)**. The research regime-DSR runner (`scripts/regime_dsr.py`) uses `W=1800` but ONLY for templates PROVEN window-safe by `tests/unit/backtest/test_window_equivalence.py` (the 5 KEEP templates: macd_pullback, bull_trend_pullback, volume_balance_breakout, stoch_rsi_bull_cross, ichimoku_cloud_trend); all other templates run full-history (`None`) because they may use inception-cumulative / recursive indicators (vpt_momentum running VPT, heikin_ashi recursion) or are simply not yet equivalence-covered. The runner also caches regenerated trades on disk so re-runs skip fetch+backtest entirely.
- **Context:** The regime-conditional DSR regeneration over 540 days of 1H data took ~4-5 hours per strategy and ~13 hours for the five KEEP strategies (operator-observed). Profiling (2026-06-07) isolated the cost precisely: network fetch = 8.1s for 14,041 bars (0.85%); the backtest = 943.9s for ONE symbol (99%). Root cause in `engine.py`: the loop sliced `series.slice(0, i+1)` (the full growing history) every bar -- which also re-sorts in `OHLCVSeries.__init__` -- and `generator.generate()` recomputed every indicator (EMA/MACD/ATR/ADX/RSI/BB/Ichimoku) from scratch over that growing slice. O(n^2) (really O(n^2 log n)).
- **Rationale:**
  - **Windowing exploits indicator convergence.** EMA/MACD/RSI/ADX/BB/Ichimoku are bounded-lookback or exponentially-converging; a trailing window of 1800 reproduces EMA(200)-class values to ~1e-8, and since signals are comparisons, decisions never flip. **Proven trade-identical on real data: 102 vs 102 trades, 943.9s -> 156.4s (6.0x).**
  - **Equivalence-gated, not assumed.** `test_window_equivalence.py` proves (a) indicator numeric convergence (EMA-200/ADX full vs window <=1e-6), (b) signal-stream equivalence across sampled bars where 1000+ older bars are dropped, (c) the default path is unchanged. A real-data trade-level spot-check (102==102) confirmed it before any run trusted it.
  - **Opt-in + safe-list = zero production risk.** Default `None` means the live/production backtests are byte-identical to before; only the research runner opts in, and only for templates whose equivalence is proven. Cumulative-indicator templates stay full-history.
- **Alternatives Considered:**
  - **GPU:** rejected -- a backtest is a sequential, data-dependent, branch-heavy loop over a few MB; GPUs accelerate large dense parallel math and would sit idle. Wrong tool.
  - **Extended thinking / "UltraThink":** rejected (category error) -- that is model reasoning depth, not Python execution speed; it cannot affect runtime.
  - **Vectorized "compute indicators once" engine rewrite:** deferred -- the exact (no-approximation) fix, but a large cross-generator refactor; windowing is contained, opt-in, and equivalence-proven now. Revisit if more speed is needed.
  - **Multiprocessing only:** complementary, not a substitute -- it parallelizes independent symbol backtests (CPU cores) but does not reduce per-symbol cost; can be layered on top later.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-07
- **Implemented By:** `src/core/strategy/backtest/engine.py` (`lookback_window` param + windowed loop), `tests/unit/backtest/test_window_equivalence.py` (equivalence gate), `scripts/regime_dsr.py` (`WINDOW_SAFE_TEMPLATES`, `DEFAULT_LOOKBACK_WINDOW=1800`, on-disk trade cache)
- **References:** DEC-2026-06-04-014 (regime-conditional DSR that surfaced the cost), profiling 2026-06-07 (8.1s fetch vs 943.9s backtest), real-data spot-check 102==102 trades / 6.0x, operator decision 2026-06-07 ("also do the engine windowing fix").

---

### DEC-2026-06-04-016: MACD_PB Re-Examination — Documented Choppy Edge Did Not Reproduce (Retirement/Post-Mortem Candidate)

- **Decision:** MACD_PB is flagged for **RE-EXAMINATION** and is a **retirement / post-mortem candidate**. Its documented edge -- choppy_bear PF 2.33 (the empirical basis for its KEEP status, project memory 2026-05-28) -- did NOT reproduce under the regime-conditional backtest DSR screen (DEC-2026-06-04-014) over a continuous 540-day spot window ending 2026-06-07: choppy_bear PF fell to **0.76** (net-negative after costs), and MACD_PB shows **NO positive cost-adjusted cell in ANY regime** (bull/bear/chop or any fine SubRegime), with base DSR p-values >= 0.90 everywhere. This is a SCREEN-LEVEL flag (a recommendation, opt-in per DEC-2026-06-04-009), NOT a live demotion: the kill switch is OFF, MACD_PB is not deployed, and its `current_classification` is already `INSUFFICIENT_DATA` (empty paper data, geo-block). No live config changes.
- **Context:** The regime-conditional DSR screen's first real subjects were the 5 KEEP strategies. Of the five, MACD_PB was the ONLY one with no positive regime cell at all (VBB/SRC/BTP/ICVP each showed >=1 faint positive choppy/ranging cell, though none cleared DSR either). The disappearance of a PF-2.33 edge to PF-0.76 over the full window is the BTF failure mode (time-window selection bias / decay).
- **Rationale:**
  - **Non-reproduction across EVERY regime is the strongest single signal in the KEEP cohort.** Other KEEP strategies at least show their documented choppy edge faintly (VBB choppy_bear PF 1.38); MACD_PB shows nothing positive anywhere.
  - **The cause is DECAY, not fabrication (period-dependence run RESULT, 2026-06-08).** Over the ~90-day promotion-era window (ending 2026-05-28), MACD_PB choppy_bear was **PF 1.97 / Sharpe +0.29 (N=8)** -- a genuine positive edge matching the documented 2.33 -- versus PF 0.76 over the full 540d. So the edge was REAL at promotion and DECAYED (regime shift bear/choppy -> bull recovery), NOT overfit from a cherry-picked slice. Crucially it was real-but-FRAGILE: even at promotion its DSR p was 0.569 (above the 0.30 floor; N=8 thin), so the old PF-based promotion deployed an edge DSR would have flagged as not-yet-proven, and the subsequent decay confirmed that caution. Post-mortem primary_cause: REGIME_SHIFT / PARAMETER_DECAY (DEC-2026-06-04-011), NOT NEVER_VALIDATED. The same decay pattern holds cohort-wide (VBB choppy_bear 2.70->1.38, BTP 1.40->0.81): bear/choppy strategies promoted in a bear era, fading as the regime turned.
  - **Screen, not gate.** Per DEC-2026-06-04-014 guard #1/#5, this does not retire MACD_PB by itself; it records the evidence and recommends operator-directed re-examination.
- **Alternatives Considered:**
  - **Auto-retire MACD_PB now:** rejected -- retirement is operator-ratified (DEC-2026-06-04-009), and the period test may show recoverable (decayed) vs unrecoverable (overfit) edge, which changes the post-mortem framing.
  - **Take no action:** rejected -- a documented edge vanishing in every regime is exactly the institutional-memory event the biography/post-mortem system exists to capture.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-08
- **Implemented By:** MACD_PB biography `regime_coverage` (run `regime_dsr_run_20260607`) + `decision_log`; `research/hypotheses/ledger.yaml` H-2026-06-001 (`reexamine: [MACD_PB]`); period-dependence run `docs/research/regime_dsr/period_promo/`
- **References:** DEC-2026-06-04-014 (regime-conditional DSR screen), DEC-2026-06-04-011 (post-mortem closure), DEC-2026-06-04-009 (opt-in/operator ratification), project memory (MACD_PB choppy_bear PF 2.33 promotion basis), operator decision 2026-06-08.

---

### DEC-2026-06-04-017: MACD_PB Retirement via Structured Post-Mortem (Regime-Shift Decay) + Post-Mortem Infrastructure Built

- **Decision:** MACD_PB is **RETIRED** (status `ACTIVE_LIVE` -> `RETIRED`; biography moved `active/` -> `retired/`) with a structured **post-mortem** attached (primary_cause: **REGIME_SHIFT**). This ratifies the retirement candidacy flagged in DEC-2026-06-04-016, after the period-dependence test (2026-06-08) confirmed the cause is DECAY, not fabrication. The post-mortem records the full circle: the choppy_bear edge was REAL at promotion (PF 1.97, promo-era 90d window) and DECAYED (PF 0.76 over 540d) as the macro regime shifted bear/choppy -> bull recovery; it was never DSR-validated even at promotion (best-window p=0.569, above the 0.30 floor, N=8 thin); retired for single-regime concentration with no current positive edge in any regime. **No live impact** -- MACD_PB was never deployed (kill switch OFF, paper geo-blocked). **The post-mortem INFRASTRUCTURE (deferred at v0.5 per DEC-2026-06-04-011) is built in this decision**: a structured `PostMortem`/`Lesson`/`SimilarStrategy`/`LifecycleSummary` model + `PrimaryCause` enum (PRD Appendix C), and `scripts/generate_post_mortem.py` (validate + attach + retire + move `active/`->`retired/`, idempotent).
- **Context:** Operator ratified MACD_PB's retirement on 2026-06-08 and requested the post-mortem be done (building the infrastructure if absent -- it was). MACD_PB was the only KEEP strategy with no positive cost-adjusted cell in any regime over 540d; the period test showed its documented edge was real-but-fragile and decayed.
- **Rationale:**
  - **Full-circle closure (DEC-2026-06-04-011).** The retired strategy IS the lesson; structured fields (pattern_tags, lessons, similar_active_strategies) make the graveyard a queryable learning library, not a memorial.
  - **The lessons feed forward.** LESS-2026-06-001 (single-SubRegime edges carry concentration risk) and LESS-2026-06-002 (real-but-fragile edges with DSR p above the floor should be paper-validated in-regime, not PF-promoted) are pattern-tagged for future hypothesis matching. similar_active_strategies flags VBB (most-similar; choppy_bear edge persists more strongly -- the likely next decay subject).
  - **Honest cause.** REGIME_SHIFT (not NEVER_VALIDATED): the edge existed; the regime left. The period test is the evidence.
- **Alternatives Considered:**
  - **Free-text post-mortem (no model):** rejected -- pattern-tag matching requires structured, validated fields (PRD Appendix C).
  - **Keep MACD_PB active pending more data:** rejected by operator -- no positive edge remains in any current regime, and its regime has departed.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-08
- **Implemented By:** `research/biographies/schema.py` (`PostMortem`, `Lesson`, `SimilarStrategy`, `LifecycleSummary`, `PrimaryCause`; `post_mortem` field typed), `scripts/generate_post_mortem.py` (mechanism + authored MACD_PB post-mortem + CLI), `research/biographies/retired/MACD_PB.yaml`, `tests/research/test_post_mortem.py`
- **References:** DEC-2026-06-04-016 (re-examination + decay finding), DEC-2026-06-04-011 (post-mortem closes the circle), DEC-2026-06-04-014 (regime-DSR screen), PRD Appendix C (post-mortem template), period-dependence run `docs/research/regime_dsr/period_promo/`, operator ratification 2026-06-08.

---

### DEC-2026-06-04-018: Pre-DSR Hypothesis Quality Gate — Reasoning Scorecard + Blind Structural Profile (Discipline Now, Tooling Deferred)

- **Decision:** Adopt a two-stage quality gate UPSTREAM of DSR so that a DSR trial is spent only on theoretically-sound, feasible, non-duplicate hypotheses. **Stage 1 — reasoning scorecard (no data):** hard gates (mechanism stated; falsifiable fail modes; sample-size feasibility; not a known-dead graveyard pattern) plus scored dimensions (mechanism strength, inverse-crowding, crypto-native fit, regime specificity, parameter parsimony, diversity contribution, source credibility). **Stage 2 — blind structural feasibility profile (optional, data but NO performance):** confirm it runs, adequate trade count, holding-period/turnover/per-regime coverage are sane — reporting ONLY structure, NEVER PF/Sharpe/returns. **Stage 3 — DSR (unchanged evidence gate).** Failures are recorded and tagged FUNDAMENTAL (never revisit) vs FIXABLE (diagnosable near-miss = seedbed for new hypotheses); a mechanism x regime coverage map directs sourcing at the unexplored complement. Adopted NOW as a by-hand checklist (`docs/research/HYPOTHESIS_QUALITY_GATE.md`); automated tooling is DEFERRED until the manual rubric proves which dimensions discriminate and that triage (not idea-generation) is the bottleneck.
- **Context:** With backtesting now fast (regime_dsr in minutes), the temptation is a "numbers game" — push as many ideas as possible through DSR. But DSR deflates by effective K, so mass-volume sourcing RAISES the bar for every survivor (the numbers game eats itself) and a scrape-the-internet pipeline preferentially surfaces the MOST crowded (already-arbitraged) patterns. The operator correctly intuited that a quality filter must sit BEFORE DSR. The resolution: a reasoning gate measures reasoning-quality (knowable without data), reserving the K-inflating evidence gate for serious candidates.
- **Rationale:**
  - **Backtest is for CONFIRMATION, not DISCOVERY (Lopez de Prado).** The reasoning gate forces "theory first," keeping research in confirmatory mode (small K, credible survivors) rather than search/data-mining mode (K explosion).
  - **Reasoning-quality is knowable without performance data;** evidence-quality is not. The gate filters on the former; DSR on the latter.
  - **Fewer, theory-motivated trials reduce K both mechanically and statistically** (pre-specified selection carries less bias than data-mined selection).
  - **The graveyard is generative as a NEGATIVE-SPACE MAP, not a generator.** FIXABLE near-misses (right edge/wrong regime label; wrong universe/timeframe; DSR p just over floor with thin N) already cleared the mechanism gate and are the best seedbed for new hypotheses.
- **Two hard lines (non-negotiable):**
  1. **No performance peek before DSR.** Any pre-DSR data check is STRUCTURAL only; computing/showing PF/Sharpe/returns pre-DSR irreversibly biases the eventual test. "A light backtest that shows how it did" is an uncorrected backtest — the overfit trap.
  2. **No algorithmic strategy generation from failures.** Failures steer HUMAN mechanism choice; they never feed a spec-generator. Remixing no-edge strategies yields no-edge strategies — the DEC-2026-06-04-006 auto-discovery non-goal.
- **Alternatives Considered:**
  - **Mass internet-scrape + test-everything ("numbers game"):** rejected — inflates K against every survivor, surfaces the most-crowded ideas, and crosses the auto-discovery non-goal.
  - **A "lite DSR" / performance-lite backtest as the pre-filter:** rejected — there is no valid performance verdict without the K correction; showing performance pre-DSR biases the real test.
  - **Build the gate as automated tooling now:** rejected (sequencing) — premature optimization of a process never run by hand; adopt the checklist first, automate the proven bottleneck later.
  - **A failure-driven strategy generator:** rejected — auto-discovery non-goal; produces dressed-up failures.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-08
- **Implemented By:** `docs/research/HYPOTHESIS_QUALITY_GATE.md` (by-hand checklist); folded into the research loop in `docs/research/NEXT_SESSION_PROMPT.md`. No code/tooling built (deferred by design).
- **Affected Files:** `docs/research/HYPOTHESIS_QUALITY_GATE.md`, `docs/research/NEXT_SESSION_PROMPT.md`, PRD Section 8 (one-line pointer to be added).
- **References:** DEC-2026-06-04-008 (Tier/DSR floor — the evidence gate this precedes), DEC-2026-06-04-006 (auto-discovery non-goal — the line failures must not cross), DEC-2026-06-04-011 (post-mortem/graveyard), DEC-2026-06-04-014 (regime-DSR guards), DEC-2026-06-04-002 (effective-K / multiple-testing). PRD Sections 8, 9. Operator design dialogue 2026-06-08.

---

### DEC-2026-06-04-019: Research Generator Registration Path for the Forward Hypothesis Loop

- **Decision:** New research-only strategy generators live in `research/generators/<name>.py`, subclass the production `src.core.strategy.signals.SignalGenerator`, and are loaded into the eval (`scripts/regime_dsr.py`) at RUNTIME via the factory's existing `SignalGeneratorFactory.register_generator()` hook plus a research-side params/symbols/market registry. They are NEVER added to `src/core/strategy/factory.py`'s `_DEFAULT_GENERATORS` (i.e. never enter `src/`) before DSR validation + promotion. Separately, an EXISTING production template that was simply never DSR-screened (e.g. `donchian_atr`) is screened by registering its params/symbols/label in the eval registry only (`STRATEGY_PARAMS`/`STRATEGY_SYMBOLS` in `scripts/backtest_rolling.py` + `RESEARCH_LABEL_TO_TEMPLATE`/`_DEFAULT_MARKET_BY_LABEL` in `scripts/regime_dsr.py`) -- it is already legitimately in `src/`, so no new `src/` code is added. This is the only glue the forward loop needs (the FIRST SMALL TASK of the 2026-06-08 session).
- **Context:** Starting the forward hypothesis loop (source -> quality-gate -> formalize -> register -> DSR screen) requires a way to screen a brand-new hypothesis. `regime_dsr.py` evaluates strategies registered in `scripts/backtest_rolling.py` and instantiated by `template_id` via `SignalGeneratorFactory`. Two registration paths were possible; the choice is forced by the existing rules rather than open.
- **Rationale:**
  - **Preserves the one-way dependency (PRD Section 5.2: `src/` never imports `research/`).** A new research generator subclasses the `src/` base (research->src import is allowed) and is injected into the factory at runtime; `src/` is never edited and never imports `research/`.
  - **Respects the lifecycle (PRD Section 10, Stage 8).** Promotion `research/generators/` -> `src/` happens ONLY after validation. Putting an unvalidated generator in `_DEFAULT_GENERATORS` would promote-before-proof. The runtime `register_generator()` hook (already present in `src/core/strategy/factory.py`) makes the clean path zero-cost.
  - **No parallel eval tool.** `regime_dsr.py` IS the eval; the research registry feeds the SAME screen. No `eval_research_strategy.py` is built (the session prompt's explicit non-goal).
  - **Spawn-worker note (implementation).** `regime_dsr.py`'s parallel workers spawn fresh processes (Windows spawn) and construct their own `SignalGeneratorFactory()`; a NEW research generator must therefore be registered INSIDE the worker (`_backtest_series_worker` or its loader), not only the parent. (Existing production templates like `donchian_atr` are already in `_DEFAULT_GENERATORS`, so they need no runtime registration and parallel workers are safe as-is.)
- **Alternatives Considered:**
  - **Add new research generators to `_DEFAULT_GENERATORS` (the literal "pragmatic" path):** rejected -- promotes unvalidated code into `src/` before DSR, breaking the lifecycle and the one-way dependency.
  - **Build a separate `scripts/eval_research_strategy.py`:** rejected -- duplicates `regime_dsr.py` (the session prompt's explicit "do not build a parallel eval tool").
- **Status:** ACTIVE
- **Date Decided:** 2026-06-08
- **Implemented By:** `scripts/backtest_rolling.py` (`donchian_atr` params/symbols for H-2026-06-002), `scripts/regime_dsr.py` (`DONCHIAN_ATR` label + spot market), `research/hypotheses/ledger.yaml` (H-2026-06-002/003 registration blocks). The `research/generators/` runtime loader is built when H-2026-06-003's funding generator lands.
- **References:** DEC-2026-06-04-014 (regime-DSR screen this feeds), DEC-2026-06-04-018 (the pre-DSR quality gate upstream), PRD Section 5.2 (one-way dependency) + Section 10 (lifecycle Stages 3/8). Session prompt 2026-06-08 "HOW THE EVAL ACTUALLY WORKS" + FIRST SMALL TASK.

---

### DEC-2026-06-04-020: Validation Methodology Principles — DSR Does Not Replace Forward Validation; Optimization / Monte-Carlo / Diagnostics Discipline

- **Decision:** Five validation-methodology principles, established to bound how far backtest analysis can go before real capital:
  1. **DSR (backtest) does NOT replace paper/live forward validation.** DSR is the gate before PAPER, not before CAPITAL. The backtest-to-live gap is IRREDUCIBLE: a backtest describes the past; only forward data sees present-tense edge and decay. Forward validation (paper -> micro-live) remains the gate before real money. Compress it via regime-aware deployment (router activates a strategy only in its live regime), micro-live ($50-100 real-but-tiny capital for real forward data faster), and higher-frequency sourcing — NOT by skipping it.
  2. **Optimization discipline.** Parameter optimization (especially entries/exits — the largest overfit surface) is permitted ONLY: walk-forward (optimize on train, evaluate on untouched OOS window); every parameter combination counted in effective K (optimization RAISES the bar, never lowers it); robust ZONES preferred over point optima; gated by PBO. Entries/exits kept minimal and mechanism-driven.
  3. **Realism vs tuning (the line).** Calibrating the cost/execution model to reality is NOT overfitting (encouraged — it is the highest-leverage backtest work for live profitability, since most backtest->live degradation is cost-blindness, not strategy weakness). Tuning strategy parameters to fit backtest performance IS overfitting (disciplined per #2). Realism diagnostics (MAE/MFE, cost sensitivity, holding-period, trade concurrency) are pre-DSR-safe ONLY when descriptive — never used to select/tune on performance (the DEC-2026-06-04-018 no-performance-peek line extends to optimization).
  4. **Multiple methods must be complementary, pre-registered, and ALL-required.** Methods that test DIFFERENT failure modes add value: DSR (selection bias), Monte-Carlo trade-order/bootstrap (path dependence + tail risk), walk-forward (out-of-sample), PBO (overfit probability), regime-conditioning. Monte-Carlo is adopted as a planned COMPLEMENT (roadmap R5) that a strategy must ALSO pass — never an alternative. Deploying on ANY-method-pass is multiple-testing across methods (deploying noise) and is forbidden; the method set is pre-registered and all-required. Resist redundant method-sprawl.
  5. **Pre-creation benchmark = the §8.0 Stage 1 reasoning scorecard (DEC-2026-06-04-018).** That gate is the sufficient "should we even test/create this" filter; no separate pre-creation benchmark is needed.
- **Context:** Operator asked whether to collect more backtest data, optimize entries/exits before DSR, add Monte-Carlo and more hypothesis-testing methods, and ultimately make DSR the final gate before execution (motivated by MACD_PB having decayed by deployment time). The shared premise — that backtest sophistication can replace forward validation — needed challenging because real capital is at stake.
- **Rationale:**
  - **The MACD_PB lesson argues AGAINST compressing out forward validation, not for it.** MACD_PB decayed because its edge was regime-conditional and the regime turned — a market event, not a process delay. Skipping paper and deploying from a passing backtest DSR would have committed real capital to an already-decaying edge. Forward validation is the only present-tense decay detector; removing it re-exposes exactly the failure it prevents.
  - **Optimization counted honestly raises the bar.** Walk-forward + K-counting means optimization cannot manufacture a pass; it only reveals whether a robust zone exists. Entries/exits are the highest-degree-of-freedom surface, so they are kept minimal and mechanism-driven.
  - **Complementary-and-all-required prevents method-level p-hacking.** Any-pass across N methods is an N-fold multiple-testing inflation.
- **Alternatives Considered:**
  - **Make DSR the final gate before capital (skip/replace paper):** REJECTED — removes the only present-tense decay detector; MACD_PB is the counter-evidence.
  - **Optimize entries/exits to maximize backtest performance, then test:** REJECTED — textbook overfitting; only walk-forward + K-counted + robust-zone optimization permitted.
  - **Deploy on any-method-pass / add methods post-hoc to rescue a strategy:** REJECTED — multiple-testing across methods; pre-register the set and require all.
  - **Build MC / optimization-harness / realism-diagnostics tooling now:** DEFERRED — premature before the manual forward loop reveals which is the real bottleneck; these are principles recorded now, tooling built when a tested hypothesis needs it.
- **Status:** ACTIVE
- **Date Decided:** 2026-06-08
- **Implemented By:** `docs/research/RESEARCH_LAYER_PRD.md` Section 8 (principles documented); no tooling built (deferred by design). Realism diagnostics fold into the DEC-2026-06-04-018 Stage 2 structural profile when built; Monte-Carlo is research roadmap R5.
- **Affected Files:** `docs/research/RESEARCH_LAYER_PRD.md` (Section 8). Cross-refs the quality gate and lifecycle.
- **References:** DEC-2026-06-04-018 (pre-DSR quality gate — this extends the methodology), DEC-2026-06-04-008 (DSR floor — the evidence gate this clarifies), DEC-2026-06-04-002 (effective-K), DEC-2026-06-04-016/-017 (MACD_PB decay evidence), DEC-2026-06-04-014 (regime-DSR), DEC-2026-06-04-006 (auto-discovery non-goal). PRD Sections 8.2/8.4/8.8 (cost model / walk-forward / PBO), Section 10 (lifecycle / forward validation), roadmap R5 (Monte-Carlo). Trading PRD three-phase validation + regime router. Operator design dialogue 2026-06-08.

---

### DEC-2026-06-04-021: Forward Liquidation Data Channel + Collector (Binance forceOrder, JSONL, causal accessor)

- **Decision:** Build a forward-collecting liquidation data channel for the research layer. A long-running collector subscribes to the FREE, public, no-auth Binance USD-M futures liquidation websocket (`!forceOrder@arr`) and appends every event to a namespaced, append-only JSONL store under `research/data/liquidations/`. A causal as-of accessor `liquidations_in_window(t0, t1, now=...)` exposes the history leak-free, mirroring `research/data/funding_rates.py:FundingSeries.rate_at`. The collector is a DATA process ONLY: it places no orders, imports no execution code, and never touches `LIVE_TRADING_ENABLED` (stays OFF). Deploy target is Railway, GATED on the Railway region geo-block fix (DEC-2026-06-04-003); the code is host-agnostic.
- **Context:** H-2026-06-004 (Binance/Coinglass liquidation reversion) and H-2026-06-009 (Hyperliquid liquidation reversion) both PASSED the Stage-1 quality gate (17/21 and 18/21) but were blocked ONLY on liquidation-history accessibility, not reasoning. The forward-loop meta-finding (`docs/research/NEGATIVE_SPACE_MAP.md`): every PUBLIC price/flow signal on liquid majors at 1H is arbitraged (10+ trials, 0 promotions, all DSR-rejected); the one genuinely non-public lens (liquidations) hit a DATA wall. H-009's `unblock_when` explicitly lists "forward-collect via the WebSocket from now." Per DEC-2026-06-04-018 (build a tool only when a tested, gate-passing hypothesis demonstrably needs it), a gate-passing hypothesis blocked SOLELY by data justifies building the data channel.
- **Rationale:**
  - **Free + public + largest venue:** Binance perps are the largest crypto liquidation venue; the `forceOrder` stream is free and no-auth, the best free liquidation signal and the one reachable path (Coinglass is paid/DEC-005; Hyperliquid deep history is S3 requester-pays needing absent AWS creds).
  - **Causal by construction:** a forward collector only records past events as they arrive, so lookahead is structurally impossible. The accessor still enforces `trade_time <= now` (defensive symmetry with `rate_at`). The causal timestamp is the forced-trade time (`o.T`), not the push time.
  - **JSONL over parquet:** stdlib-only (no new dependency; pyarrow is absent from the venv), append/stream-friendly, human-inspectable, consistent with the funding JSON cache. One immutable fragment per flush satisfies the durable requirement (a crash loses <= one flush interval).
  - **Namespaced + read-only discipline:** writes ONLY to `research/data/liquidations/` (git-ignored); touches NO production / Neon table.
  - **Side-semantics footgun handled:** stores the raw `order_side` AND a derived `liquidated_side` (a `SELL` order = a LONG was force-sold = the H-004 "long flush"), so the eventual generator cannot invert direction.
  - **Honest limit (documented, not hidden):** the public `forceOrder` stream is throttled to <= 1 order per symbol per ~1000ms (a representative snapshot, not full tick volume), so per-second notional in an intense same-symbol cascade is UNDERCOUNTED. The windowed/percentile cascade trigger (the H-006 lesson) tolerates a proportional undercount; full-volume history still needs a paid source (DEC-005). `notional` is NOT exact market-wide liquidation volume - stated in the channel docstring and the ledger blockers.
  - **Reliability:** exponential reconnect backoff that resets only after a healthy session (monotonic clock, so a connect-then-drop flap keeps escalating), bounded in-memory dedup, flush on size / silence / disconnect / shutdown.
- **Alternatives Considered:**
  - **Coinglass paid liquidation history:** REJECTED for now - gated by DEC-2026-06-04-005 (>= $25k capital).
  - **Hyperliquid S3 archive:** REJECTED here - requester-pays, needs AWS creds this env lacks (the H-009 blocker).
  - **Parquet store:** REJECTED - adds a heavy dependency absent from the venv; JSONL meets the durable-fragment need with stdlib only.
  - **`research_liquidations` Neon table:** REJECTED - the collector host may lack the Neon connection, and a DB sink risks coupling to production data; local JSONL is fully isolated.
  - **Price-only liquidation proxy:** REJECTED - removing the exogenous signal leaves plain price action = the already-DEAD H-2026-06-002 breakout (per the H-004/H-009 blocker notes).
- **Status:** ACTIVE
- **Date Decided:** 2026-06-11
- **Implemented By:** `research/data/liquidations.py` (LiquidationEvent + `parse_force_order` + LiquidationStore + causal `liquidations_in_window`), `research/data/liquidation_collector.py` (async WS collector), `scripts/run_liquidation_collector.py` (runner), `tests/research/test_liquidations.py` (31 tests, 96% coverage on both modules), `.gitignore` (store ignored).
- **Affected Files:** the four above + `.gitignore`. `src/` is UNTOUCHED (one-way dependency, PRD 5.2; verified `src/` imports no `research/`).
- **Operational note (operator decision 2026-06-11):** The collector must run on an always-on, NON-geo-blocked host (Binance market-data WS is rejected from geo-blocked regions; DEC-2026-06-04-003 root cause). Operator chose Railway, GATED on the Railway region geo-block being fixed. Until then the collector is built-and-ready but NOT accruing; the data clock starts when the region is non-blocked OR the operator runs it on another permitted always-on host. This process never enables live trading.
- **Expectations:** Liquidation cascades large enough to trade are RARE; reaching testable N (>= 30 in HIGH_VOL) will take WEEKS-to-MONTHS of accrual. The liquidation generator (H-004 / H-009) re-enters the lifecycle at the data/implement step and is screened via `regime_dsr` once N is sufficient (Stage-1 already passed). The LONG flush (buy forced-selling) is spot-deployable; the SHORT squeeze-fade stays research-only (DEC-2026-05-28-001).
- **References:** DEC-2026-06-04-018 (data-channel-on-pass discipline this invokes), DEC-2026-06-04-005 (paid alt-data deferral this routes around with a free source), DEC-2026-06-04-003 (geo-block root cause / deploy gate), DEC-2026-05-28-001 (spot-only live lock - short fade research-only), DEC-2026-06-04-019 (research generator runtime hook the eventual generator will use). Ledger `H-2026-06-004` / `H-2026-06-009` (the unblocked hypotheses); `docs/research/NEGATIVE_SPACE_MAP.md` (meta-finding). PRD Section 5.2 (one-way dependency), Section 11.1 (free Binance data). Session prompt 2026-06-11 (PROMPT_LIQUIDATION_COLLECTOR).

---

**End of Decisions Log**

**Total Decisions:** 130 active, 0 superseded, 5 locked (1 amended); DEC-2026-06-04-013 amended
**Last Updated:** 2026-08-16
**Next Decision ID:** DEC-2026-08-16-003

> Count corrected 2026-08-14. This footer read "107 active" while the file held
> 124 real decision entries -- the count had drifted as decisions were appended
> without updating it. It is now asserted by
> `tests/unit/test_governance_sync.py::test_footer_decision_count_matches_reality`
> so it cannot drift again silently. The count excludes the
> `DEC-YYYY-MM-DD-XXX` template near the top of this file.
>
> **Known defect, not yet resolved:** `DEC-2026-02-15-001` and
> `DEC-2026-02-15-002` each appear TWICE, in two separate transcriptions. The
> pairs agree on substance; the later copies cite stale paths
> (`src/paper/engine.py` rather than `src/core/strategy/paper/`). The duplicate
> IDs make any cross-reference to them ambiguous. They are allowlisted in
> `test_decision_ids_are_unique` so the test still catches NEW duplicates while
> this one awaits an owner decision on which copy is canonical.
>
> See DEC-2026-08-14-002, Rule 1.3: a number in a document is a claim, and a
> confidently wrong one is a worse failure than a dated one.

## Phase 5 Decisions (Backtesting & Simulation)

### DEC-2026-02-15-001: Synchronous Simulation (Paper Trading)
- **Decision:** PaperTradingEngine runs synchronously for SIMULATED mode, and asynchronously for LIVE mode
- **Context:** Historical replay backtesting is CPU-bound and blocks the event loop if run in the main thread. Asyncio is designed for I/O-bound operations, not CPU-bound simulation.
- **Rationale:**
  - **CPU-bound workload:** Processing 1 year of 1-minute candles (525k bars) is pure computation
  - **Simplicity:** Synchronous simulation is easier to debug and reason about
  - **Performance:** Avoids asyncio overhead for tight loops in simulation
  - **Dual-mode engine:** Engine supports both modes while sharing signal generation logic
- **Alternatives Considered:**
  - **Async simulation:** Rejected due to event loop blocking and unnecessary complexity
  - **Separate engines:** Rejected to ensure simulation matches live behavior exactly (same code paths)
  - **Multiprocessing:** Rejected as over-engineering for MVP data volumes
- **Status:** ACTIVE
- **Date Decided:** 2026-02-15
- **Implemented By:** Phase 5b Implementation
- **Affected Files:**
  - `src/paper/engine.py`
  - `src/backtest/engine.py`
- **References:** PRD Section 5.2

### DEC-2026-02-15-002: Regime Persistence Mechanism
- **Decision:** Market regimes are stored in `SystemState.circuit_breakers["market_regimes"]` JSON field
- **Context:** Need to persist detected market regimes (bullish, bearish, volatile) without modifying the database schema for MVP.
- **Rationale:**
  - **Schema stability:** Avoids complex Alembic migrations for MVP
  - **JSON flexibility:** Can store regime data per symbol/timeframe easily
  - **Centralized state:** SystemState is already the source of truth for system-wide flags
  - **Persistence:** SystemState is persisted to SQLite/PostgreSQL
- **Alternatives Considered:**
  - **New MarketRegime table:** Rejected to avoid schema changes
  - **File-based storage:** Rejected due to lack of transactional integrity associated with SystemState
  - **In-memory only:** Rejected, need to persist across restarts
- **Status:** ACTIVE
- **Date Decided:** 2026-02-15
- **Implemented By:** Phase 5b Implementation
- **Affected Files:**
  - `src/core/risk/regime.py`
  - `src/data/models/system.py`
- **References:** PRD Section 5.3

---

## Pre-Publication Decisions (2026-08-11)

### DEC-2026-08-11-001: Startup Strategy Validation Is Read-Only, via TemplateManager
- **Decision:** `StartupChecklist._check_strategies` validates active strategies by calling `TemplateManager.get_template()` and `TemplateManager.validate_parameters()` directly. It MUST NOT call `StrategyEngine.create_strategy()`.
- **Context:** The check was calling `create_strategy()` with four keyword arguments that do not exist on its signature (`template`, `symbol`, `account_id`, `status`) and reading three attributes absent from the Strategy model (`.template`, `.symbol`, `.params`) plus one it never had (`.account_id`). Every call raised, and a bare `except Exception` reported it as "Strategy <name> validation failed". The check could not pass in any environment with active strategies.
- **Rationale:**
  - **create_strategy is not a validator:** it constructs a Strategy and persists it via `DataStore.save_strategy`, and hardcodes `StrategyStatus.DRAFT` with no `status` parameter to opt out. Correcting the keyword arguments alone would have replaced a loud `TypeError` with a silent write of one duplicate DRAFT row per active strategy on every startup.
  - **Validation is what the check claims to do:** template resolution plus parameter validation is exactly the stated intent, and both are already public on TemplateManager.
  - **Catches template drift:** a template can change after a strategy row is written; this surfaces that at startup rather than at first signal.
  - **Read-only startup checks:** a pre-flight check must not mutate the state it is checking.
- **Alternatives Considered:**
  - **Fix the keyword arguments only:** REJECTED - turns a visible crash into silent data corruption. This was the fix proposed by the read-only audit, which had seen the signature but not the body.
  - **Add a persist=False flag to create_strategy:** REJECTED - widens a public API to serve one caller, and a validation-only path through a persistence method invites future misuse.
  - **Delete the check:** REJECTED - validating that active strategies are constructible is a legitimate pre-flight condition.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-11
- **Implemented By:** `src/core/orchestrator.py` `_check_strategies`; `tests/unit/test_orchestrator.py` `TestCheckStrategiesWithRealEngine`
- **Affected Files:**
  - `src/core/orchestrator.py`
  - `tests/unit/test_orchestrator.py`
- **References:** `docs/PRODUCTION_READINESS_ASSESSMENT.md` sections 2.4 and 3.2 item 4, plan item 2.1. Related: DEC-2026-08-11-002 (error propagation, same defect).

### DEC-2026-08-11-002: Programming Errors Propagate From Startup Checks
- **Decision:** Startup checks catch expected domain errors and return `CheckResult(passed=False)`. `TypeError` and `AttributeError` propagate instead.
- **Context:** The defect in DEC-2026-08-11-001 survived for roughly six months because a bare `except Exception` converted a `TypeError` from a broken call into an ordinary failed-check message. The message described a data problem when the cause was a programming error, so the log gave no route to the bug.
- **Rationale:**
  - **Same failure outcome, better diagnosis:** startup aborts on a failed check either way, so propagating costs no safety. What changes is that a programming error now produces a traceback pointing at the defect.
  - **A bare except hides the next one too:** the catch was the reason the defect was undiagnosable, independent of the defect itself.
  - **Consistent with fail-closed:** an unrecoverable programming error must not be reported as a recoverable condition.
- **Alternatives Considered:**
  - **Keep the broad catch, add exc_info=True logging:** REJECTED - still reports a programming error as a check failure, and relies on someone reading logs at the right level.
  - **Narrow to specific domain exceptions across the whole class:** DEFERRED - the other seven checks wrap genuine I/O (database, exchange, disk, memory) where a broad catch is defensible. Revisit if a second defect hides the same way.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-11
- **Implemented By:** `src/core/orchestrator.py` `_check_strategies`; `tests/unit/test_orchestrator.py::TestCheckStrategiesWithRealEngine::test_programming_errors_propagate`
- **Affected Files:**
  - `src/core/orchestrator.py`
  - `tests/unit/test_orchestrator.py`
- **References:** `docs/PRODUCTION_READINESS_ASSESSMENT.md` plan item 2.2. Related: DEC-2026-08-11-001.

### DEC-2026-08-11-003: Pre-Publication Repository Hygiene
- **Decision:** Before public release the repository root holds only project structure. Specifically: 35 `SESSION_*`/`PHASE_*` AI prompt files and 17 one-off root scripts removed; `.claude/skills` and `.agent/skills` untracked; `src/core/strategy/regime.py` and the empty `src/domain/` and `src/core/account/` packages removed; `docs/design/pdf/` untracked; full 102-commit history retained.
- **Context:** A reviewer lists the root directory and clones the repository before reading any code. The root held 45 entries, most of them build scaffolding. Two directories were tracked as gitlinks (mode 160000) with no `.gitmodules`, so a fresh clone produced empty directories that `git submodule update --init` could not repair.
- **Rationale:**
  - **Prompt files are scaffolding, not documentation:** they describe completed work and duplicate what this decision log holds. Curated into one honest document (`docs/AI_ASSISTED_DEVELOPMENT.md`) rather than deleted silently or published raw.
  - **Root scripts were unreferenced:** verified that no import statement in `src/`, `scripts/` or `tests/` resolves to any of them, and none appears in Dockerfile, Procfile or railway.toml. The six root `test_*.py` files were never collected (`testpaths = ["tests"]`) but inflated the apparent test surface.
  - **Skills directories are third-party:** clones of `sickn33/antigravity-awesome-skills`, unrelated to the trading system. Untracked rather than promoted to real submodules - the system does not depend on them and vendoring an unrelated repository is not appropriate.
  - **regime.py was unreachable:** CPython resolves packages before same-named modules, so the `regime/` package had shadowed it since its creation. Its exports already live in `regime/manual.py` and are re-exported for backward compatibility.
  - **History is retained deliberately:** four months of single-author commits is evidence of sustained work. Untracking the PDFs shrinks the working tree, not the clone; rewriting all 102 commits to reclaim about 21 MB was considered and declined as a poor trade.
- **Alternatives Considered:**
  - **Archive prompt files to docs/archive/build-log/:** REJECTED - moves 35 files of prompt text into published documentation; reads as clutter rather than transparency.
  - **git filter-repo to purge PDFs from history:** REJECTED - rewrites every commit SHA to save about 21 MB of clone.
  - **Squash to a fresh initial commit:** REJECTED - discards the commit record, which is one of the repository's stronger signals.
  - **Promote skills directories to real submodules:** REJECTED - see rationale.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-11
- **Implemented By:** Pre-publication cleanup on branch `cleanup/pre-publication`. Pre-cleanup state recoverable at tag `pre-cleanup` (`622ac49`).
- **Affected Files:** repository root, `.gitignore`, `LICENSE`, `src/core/strategy/regime.py`, `src/domain/`, `src/core/account/`, `docs/design/pdf/`, `docs/validation/`
- **References:** `docs/PRODUCTION_READINESS_ASSESSMENT.md` sections 2.6 and 3.2 items 8-10, plan items 1.1, 1.2, 1.7, and Phase 0 item 0.4. A secret scan across all 102 commits returned no findings.

### DEC-2026-08-11-004: Hermetic Test Environment, Network Tests Opt-In
- **Decision:** An autouse fixture in `tests/conftest.py` strips `BINANCE_*`, `TELEGRAM_*`, `DATABASE_URL` and the live-trading switches from `os.environ` and disables `.env` discovery on `Settings` for every test. Network-dependent integration tests are auto-marked `binance` and skipped unless `PARAVANT_RUN_NETWORK_TESTS=1`.
- **Context:** `test_settings_defaults` failed because it asserted `binance_testnet is True` while reading the developer's real `.env`, which sets `BINANCE_TESTNET=false`. The test suite could observe -- and act on -- the setting that selects real-money mode. Separately, `tests/integration/test_binance_client.py` and `test_symbol_refresh.py` opened a live connection during fixture setup, producing 32 setup ERRORS on any machine without working exchange connectivity.
- **Rationale:**
  - **Safety before hygiene:** a test run must not be able to see live credentials. This is the same fail-closed principle as the kill switch, applied to the test boundary.
  - **Two leaks, two fixes:** clearing `os.environ` is insufficient on its own because `Settings` declares `env_file=".env"` and re-reads the file at instantiation. Both had to be closed.
  - **Opt-in by flag, not by credential sniffing:** skipping only when an API key is absent would mean that merely having a key configured is enough to start making live network calls. An explicit environment flag makes the choice deliberate.
  - **A clean clone must produce zero errors:** 32 errors a contributor cannot act on are indistinguishable from a real regression.
- **Alternatives Considered:**
  - **`monkeypatch.chdir(tmp_path)` to hide `.env`:** REJECTED - breaks every other relative path (`config/templates`, etc.).
  - **Skip network tests when `BINANCE_API_KEY` is unset:** REJECTED - see rationale; presence of a key should not authorise network traffic.
  - **Delete the network tests:** REJECTED - they are valuable when run deliberately against testnet.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-11
- **Implemented By:** `tests/conftest.py` (`hermetic_environment`, `pytest_collection_modifyitems`)
- **Affected Files:** `tests/conftest.py`
- **References:** `docs/PRODUCTION_READINESS_ASSESSMENT.md` 2.1 and plan items 2.3-2.5.

### DEC-2026-08-11-005: Liquidation Store Partitions by Trade Date, Not Flush Time
- **Decision:** `LiquidationStore.write_batch` groups events by the UTC date of their own `trade_time_ms` and writes one immutable fragment per date. `flush_dt` is retained only to name the fragment file. Return type changes from `Path | None` to `list[Path]`, and `LiquidationCollector.flush` follows.
- **Context:** `write_batch` selected its date-partition directory from wall-clock `flush_dt`, while `read_window` derives candidate directories from the query window, which is expressed in trade time. Two different clocks keying one partition scheme. They agree only while events are flushed on the same UTC day they occurred; any wider gap wrote the event to disk and made it invisible to every subsequent query.
- **Rationale:**
  - **Correct by construction:** the reader queries in trade time, so the writer must partition in trade time. Widening the read pad would only move the failure threshold.
  - **The failure mode was silent and expensive:** this store accrues data for months before H-2026-06-004 and H-2026-06-009 can be screened. Lost events would have presented as "the hypothesis still has no data", with no signal as to why.
  - **The model already declares the authority:** `LiquidationEvent.trade_time_ms` is documented as "the CAUSAL timestamp". Partitioning on anything else contradicts the type's own contract.
  - **A passing test was masking it:** `test_store_read_window_spans_midnight_partition_padding` documented the one-day workaround, which made the flaw read as intentional.
- **Alternatives Considered:**
  - **Widen `_READ_DATE_PAD`:** REJECTED - fragile, and unbounded in the replay case.
  - **Scan all date directories on read:** REJECTED - correct but discards the point of partitioning.
  - **Keep `Path | None` and reject multi-date batches:** REJECTED - a buffer straddling UTC midnight is normal operation, not an error.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-11
- **Implemented By:** `research/data/liquidations.py`, `research/data/liquidation_collector.py`
- **Affected Files:** `research/data/liquidations.py`, `research/data/liquidation_collector.py`, `tests/research/test_liquidations.py`
- **Backward compatibility:** BREAKING within `research/`. `write_batch` and `flush` return `list[Path]`. Callers are the collector, `scripts/run_liquidation_collector.py` (return value unused), and tests -- all updated. `src/` is unaffected (one-way dependency, DEC-2026-06-04-001).
- **References:** DEC-2026-06-04-021 (the collector this store backs). Regression cover: `test_store_partitions_by_trade_date_not_flush_date`, `test_store_batch_spanning_dates_splits_fragments`.

### DEC-2026-08-11-006: TradingSignal.indicators Is Mapping[str, float | str]
- **Decision:** `TradingSignal.indicators` is declared `Mapping[str, float | str]`, not `dict[str, float]`.
- **Context:** The field was typed `dict[str, float]` while generators have always also stored categorical labels in it (`divergence_type="bullish"` and similar). mypy reported the mismatch 15 times across the generator package rather than once at the definition.
- **Rationale:**
  - **The annotation described a contract the code did not keep.** Fixing it at the definition is one change; suppressing it at 15 call sites is fifteen.
  - **`Mapping`, not `dict`, because `dict` is invariant in its value type.** Widening to `dict[str, float | str]` made things worse -- 42 mypy errors became 64 -- because a generator building `dict[str, float | int]` cannot be passed to a `dict[str, float | str]` parameter at all. `Mapping` is covariant and accepts every generator's dict shape.
  - **Read-only is the honest contract:** no code outside the generators reads `indicators`, and nothing mutates it after the signal is constructed.
- **Alternatives Considered:**
  - **`dict[str, float | str]`:** REJECTED - invariance, see rationale.
  - **Annotate the local dict in each generator:** REJECTED - roughly 20 files to state one fact.
  - **Serialise labels to float codes at the boundary:** REJECTED - destroys the diagnostic value of the field to satisfy a type that was wrong.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-11
- **Implemented By:** `src/core/strategy/signals.py`
- **Affected Files:** `src/core/strategy/signals.py`
- **References:** `docs/PRODUCTION_READINESS_ASSESSMENT.md` plan item 2.7.

### DEC-2026-08-11-007: Operational Scripts Emit ASCII Only
- **Decision:** Every script that writes to stdout uses ASCII markers (`[OK]`, `[FAIL]`, `[WARN]`) rather than emoji or typographic characters.
- **Context:** `scripts/init_db.py` -- the first command in the README quickstart -- printed a check-mark emoji on success. On a default Windows console (cp1252) that raises `UnicodeEncodeError`. The bare `except Exception` then attempted to print a cross-mark emoji, which raised again, unhandled. The database was created correctly and the script exited 1 with a traceback. Twelve files carried non-ASCII inside `print()`, including `run_all.py`, `run_live_trading.py`, `validation_report.py` and `health_check.py`.
- **Rationale:**
  - **The quickstart is the first thing a reviewer runs.** A stack trace in the first sixty seconds is read as "this project does not work", regardless of the cause.
  - **`run_live_trading.py` is not a place to risk an encoding crash.** A print that raises inside the live loop is an availability failure with capital at stake.
  - **Console encoding is not the program's to assume.** Emitting ASCII is correct on every platform; forcing UTF-8 reconfiguration at each entrypoint treats the symptom.
  - **Consistent with existing practice:** `validation_report.py` already used ASCII `[OK]`/`[MISS]`/`[...]` markers.
- **Alternatives Considered:**
  - **`sys.stdout.reconfigure(encoding="utf-8")` at each entrypoint:** REJECTED - a band-aid, easy to omit in the next script, and leaves the output undisplayable in some terminals regardless.
  - **Set `PYTHONIOENCODING` in the docs:** REJECTED - pushes a defect onto the reader, and does not help anyone who runs the script without reading first.
  - **Fix only `init_db.py`:** REJECTED - the same latent crash sits in the live loop and the daily report.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-11
- **Implemented By:** 12 files under `scripts/` and `tests/performance/`
- **Affected Files:** `scripts/init_db.py`, `verify_db.py`, `run_all.py`, `run_live_trading.py`, `validation_report.py`, `health_check.py`, `audit_check.py`, `backtest_rolling.py`, `backtest_btf_may2026.py`, `sweep_tp_wfo.py`, `sweep_stop_multiplier.py`, `tests/performance/test_risk_performance.py`
- **References:** Verified after the change: `python scripts/init_db.py` and `python scripts/verify_db.py` both exit 0 on a default Windows console.

### DEC-2026-08-11-008: required_periods Is a Per-Class Helper, Not a Polymorphic Contract
- **Decision:** `Indicator.required_periods` provides a single-period default. Indicators whose warmup depends on several period parameters (Ichimoku, Keltner, StochasticRSI) declare their own signature and carry a narrow `# type: ignore[override]` with a comment pointing here.
- **Context:** mypy reported three `[override]` errors because those subclasses take different parameters from the base. `disallow_untyped_defs = true` is declared in `pyproject.toml` but was never enforced, so the divergence had gone unremarked.
- **Rationale:**
  - **It is not used polymorphically.** Every call site invokes it on a concrete class -- `ADX.required_periods(14)` in tests, `self.required_periods(self.ema_period, self.atr_period)` inside the subclass. No caller holds a base-typed reference and calls it, so no caller can be broken by the differing arity. Liskov is about substitutability that something actually relies on.
  - **The parameters are genuinely different.** Ichimoku needs `senkou_b_period` and `displacement`; Keltner needs `ema_period` and `atr_period`; StochasticRSI needs four. Collapsing them to `*periods: int` would discard the names that make the calls readable, to satisfy a contract nothing consumes.
  - **A narrow, explained suppression beats a false abstraction.** The alternative designs each cost more clarity than the ignore does.
- **Alternatives Considered:**
  - **Widen the base to `*periods: int`:** REJECTED - loses named parameters at every call site.
  - **Remove `required_periods` from the base:** REJECTED - it is a documented part of the base API and `tests/unit/indicators/test_base.py` exercises it directly.
  - **Add `**kwargs` to the base:** REJECTED - types nothing and hides real mistakes.
  - **Blanket-disable the `override` error code:** REJECTED - would hide genuine Liskov violations elsewhere. The suppression is per-method and commented.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-11
- **Implemented By:** `src/core/indicators/ichimoku.py`, `keltner.py`, `stochastic_rsi.py`
- **Affected Files:** the three above
- **References:** `docs/PRODUCTION_READINESS_ASSESSMENT.md` plan item 2.7. With this, `mypy src/` reports no issues across 167 files, so `disallow_untyped_defs` is enforced in fact and not only declared.

### DEC-2026-08-13-001: Bar-Derived Features Are Knowable Only After the Bar Closes
- **Decision:** A series stamped with bar OPEN times whose values derive from the bar's CLOSE must be read one full bar late. `coinbase_prices.close_at` and `btc_reference.thrust_at` now select on `open + bar_duration <= ts`. The rule is enforced generally by `research/features/`, where each feature declares its `FeatureKind`, `interval` and `publication_lag`, and the store refuses any value whose `knowable_at` exceeds the query instant.
- **Context:** Both channels documented their accessors as causal and both were wrong in the same way. `times_ms` held bar OPEN times; `close_at`/`thrust_at` did `bisect_right(times_ms, ts)` and returned the matching bar's close-derived value. A query at 10:30 therefore received the 10:00-11:00 bar's close -- a price from 11:00. Up to 59 minutes of lookahead. Each channel looked correct read on its own; the defect only became visible when the same question was asked of all six channels uniformly.
- **Rationale:**
  - **Causality by construction, not convention.** Six channels each implemented causality independently, with different accessor names and no shared test. That is why two could be wrong while all six were documented as right. The store computes knowability from declared metadata, so a channel cannot assert its way to being causal.
  - **Two audits, because there are two failure modes.** `audit_knowability` catches a record whose timestamp is legitimately past while its content is future (this defect). `audit_future_invariance` catches a resolver that scans beyond the query instant. Neither detects the other's failure; a suite with only the intuitive second check would have passed on a channel leaking 59 minutes.
  - **The affected conclusions stand.** The leak biases results optimistically. H-2026-06-010 (Coinbase premium, PF 0.35) and H-2026-06-011 (BTC lead-lag, PF 0.44) were rejected anyway, so correcting the leak can only make those rejections more conservative. No published finding changes; re-screening is not required to preserve any conclusion.
- **Alternatives Considered:**
  - **Restamp the series with bar CLOSE times:** REJECTED - loses the bar's identity, and every caller that joins on bar open would silently shift.
  - **Fix the two channels and stop there:** REJECTED - leaves the next channel free to repeat it. The defect was a class, not an instance.
  - **Have resolvers apply their own lag:** REJECTED - that is exactly the per-channel convention that failed. The arithmetic belongs in one tested place.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-13
- **Implemented By:** `research/features/` (spec, store, audit, channels); fixes in `research/data/coinbase_prices.py` and `research/data/btc_reference.py`
- **Affected Files:** the above, plus `tests/research/test_feature_store.py` (24 tests), `test_coinbase_prices.py`, `test_btc_reference.py`, `test_coinbase_premium.py`
- **Note on the tests:** `test_close_at_is_causal` asserted `close_at(01:30) == 101.0` -- the leak -- with the comment "latest <= ts". A test named for causality was asserting its violation. This is the third instance in this repository of a test written to match a defect rather than the specification; see `docs/AI_ASSISTED_DEVELOPMENT.md` section 4.1.
- **References:** DEC-2026-06-04-021 (the liquidation collector, whose causal accessor was already correct and served as the model), PARA-03/04 in `docs/research/RESEARCH_FIXLIST.md`.

### DEC-2026-08-13-003: LLM Hypothesis Evaluation Is an Evals Study, Not a Strategy Search
- **Decision:** Build `research/llm/` as a pre-registered evaluation of whether an LLM can generate trading hypotheses better than the human baseline, and of whether the project's own Stage-1 rubric can tell the difference. The protocol is fixed in advance in `docs/research/LLM_HYPOTHESIS_EVAL_SPEC.md`.
- **Context:** The repository contains no ML and no LLM integration, which is the largest gap between what it is (systems and quantitative research engineering) and the roles it is being published for. The obvious response -- bolt on a model that predicts prices -- would produce a demo indistinguishable from thousands of others and would contradict this project's own findings.
- **Rationale:**
  - **The question is answerable and the answer is useful either way.** The human Stage-1 rubric correlates with realised profit factor at r = +0.146 over seven screened hypotheses, and the higher-scoring of the two flagship hypotheses performed worse. Pointing a text generator that is optimised to satisfy rubrics at a rubric that already appears not to work is a direct, measurable instance of Goodhart's law.
  - **Power is where the design must be honest.** Novelty rate, hard-gate pass rate, score distribution and mechanism diversity are measurable at n >= 100 without a single backtest. Outcome correlation is not: it caps at n < 10 and is pre-registered as exploratory. Reporting an underpowered correlation as a finding would repeat exactly the error corrected in `RESEARCH_FINDINGS.md` section 3.
  - **It reuses machinery rather than inventing a parallel stack.** Effective-K counts LLM proposals as trials; the similarity checker detects structural duplicates; the negative-space map supplies the novelty ground truth; the feature store guards leakage. The technical contribution is applying existing multiple-comparisons correction to LLM output, which is not a thing most LLM projects do.
  - **The harness is the artifact.** Caching for deterministic replay, cost accounting, prompt content-hashing and an explicit failure taxonomy are the properties that make an LLM integration reviewable. They hold their value regardless of which way the result falls.
- **Alternatives Considered:**
  - **A price-prediction model:** REJECTED - contradicts the project's own null result, and a model that "works" without the same DSR scrutiny applied to every other strategy would be indefensible here.
  - **An autonomous research agent:** REJECTED - the human gate at each stage is the point of the protocol; removing it to make a better demo would discard the thing worth showing.
  - **An ML regime classifier (assessment item 5.1):** DEFERRED - honest and smaller, but it demonstrates conventional supervised learning rather than evaluation engineering, and it does not reuse the statistical machinery that distinguishes this repository.
  - **Nothing, and reposition to backend/platform roles:** PARTIALLY ADOPTED - the repository is already strong for those roles and should be applied with immediately. This decision does not depend on the LLM work landing.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-13
- **Implemented By:** `docs/research/LLM_HYPOTHESIS_EVAL_SPEC.md` (pre-registration); `research/llm/` (to be built in five phases)
- **Affected Files:** `docs/research/LLM_HYPOTHESIS_EVAL_SPEC.md`, `docs/research/LLM_EVAL_SESSION_PROMPT.md`
- **Expected outcome, recorded before the fact:** null. The LLM is expected to score at or above the human median on the rubric while proposing predominantly exhausted mechanism classes. A positive result is to be treated as a suspected defect until leakage and trial accounting are re-checked.
- **References:** DEC-2026-06-04-008 (DSR floor), DEC-2026-06-04-001 (one-way dependency), `docs/research/HYPOTHESIS_QUALITY_GATE.md`, `docs/research/NEGATIVE_SPACE_MAP.md`, `docs/RESEARCH_FINDINGS.md` section 4.

---

### DEC-2026-08-14-001: API Key on State-Mutating Endpoints, Enforced by Method-Based Middleware
- **Decision:** All 21 state-mutating endpoints (`POST`/`PUT`/`PATCH`/`DELETE`) require a shared secret in an `X-API-Key` header, configured via `PARAVANT_API_KEY`. Enforcement is a single `ApiKeyAuthMiddleware` keyed on HTTP method (`src/api/auth.py`), NOT a `Depends` on each route. The 42 read endpoints remain ungated. Outside `ENVIRONMENT=development` a missing key aborts startup; a key under 32 characters is rejected in every environment.
- **Context:** Finding #1 of `docs/PRODUCTION_READINESS_ASSESSMENT.md` and plan item 3.1. Every endpoint was open, including order placement, position closure, system start/stop, and kill-switch activation and deactivation. It was the top-ranked gap and it hard-blocked item 3.8 (public read-only demo), since a public URL would have exposed order placement and the kill switch to anyone who found it.
- **Rationale:**
  - **Method-based middleware is fail-closed; a per-route dependency is fail-open.** The assessment specified "a static API key validated by a FastAPI dependency". That is the idiomatic approach and it was rejected on inspection: protection would depend on the author of every future endpoint remembering to attach it, and nothing fails when they forget -- the endpoint simply ships unauthenticated. Gating by HTTP method covers a mutating endpoint added tomorrow on the day it is written. This matches the fail-closed posture already used for the min-notional guard (DEC-2026-05-31-003), the promotion gate (DEC-2026-06-01-001) and `SubRegimeDetector` on UNKNOWN (DEC-2026-05-28-003).
  - **The OpenAPI cost is paid down by a contract test.** Middleware does not appear in the generated schema. `tests/unit/api/test_auth.py::TestMutatingRouteCoverage` enumerates `app.routes`, derives every mutating route, and asserts each returns 401 without a key -- with a guard test asserting the enumeration is non-empty so the parametrised cases cannot pass vacuously. Verified to fail when the middleware is removed: `POST /api/v1/orders` reached its handler and another route attempted a live Binance call.
  - **Reads stay open deliberately.** The dashboard is a read-only browser client. Gating GET would break it for no safety gain, since reads cannot place orders. The cost -- full trading state is readable by anyone who can reach the port -- is documented in `SECURITY.md` rather than hidden.
  - **A single static key is the honest size of the problem.** One operator, one client. JWT or OAuth would be theatre: more surface, more code, no more security for a single-user system. The assessment made this point and it holds.
  - **Middleware ordering is load-bearing.** Starlette makes the last-added middleware outermost. The gate is added BEFORE `CORSMiddleware` so it sits inside it; an auth layer outside CORS returns 401s stripped of CORS headers, which a browser reports as an opaque network error rather than an authentication failure. `TestMiddlewareOrdering` guards this. `X-API-Key` was added to `allow_headers` or the preflight would reject it.
  - **Weak keys are rejected, not warned about.** A short key produces the appearance of protection while remaining brute-forceable, which is worse than none. `secrets.compare_digest` is used so response timing does not leak key content, and the 401 body is identical for a missing and an incorrect key so the response is not an oracle -- the distinction is kept in the log.
- **Alternatives Considered:**
  - **Per-route `Depends`:** REJECTED - fail-open by omission, as above. This is a deliberate deviation from the assessment's own wording.
  - **Gating every endpoint including reads:** REJECTED - breaks the read-only dashboard and blocks item 3.8 for no safety gain.
  - **JWT / OAuth2:** REJECTED - over-engineering for one operator; a reviewer respects a justified simple choice more.
  - **Reverse proxy auth only (nginx basic auth):** REJECTED - moves the control outside the repository, so nothing in the codebase or its tests can assert it holds.
  - **Rejecting mutating requests with 503 instead of aborting startup:** REJECTED - a half-serving system is harder to notice than a crash-loop. Loud failure was chosen.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-14
- **Implemented By:** Assessment plan item 3.1
- **Affected Files:** `src/api/auth.py` (new), `src/api/main.py` (middleware registration + startup validation + `allow_headers`), `tests/unit/api/test_auth.py` (new, 26 tests), `tests/conftest.py` (`PARAVANT_API_KEY` added to the hermetic strip list), `.env.example`, `SECURITY.md`, `README.md`, `DEPLOYMENT.md`, `docs/ARCHITECTURE.md` (new section 8.1), `docs/API_CONTRACT.md`, `docs/PROJECT_CONTEXT.md`, `docs/PRODUCTION_READINESS_ASSESSMENT.md`.
- **Known limits, recorded deliberately:** one shared key with no identities, rotation or expiry; no rate limiting (item 3.2); open reads; plaintext header requiring TLS termination in front; development bypass when the variable is unset. All enumerated in `SECURITY.md` rather than implied to be solved.
- **Operational consequence:** any deployment with `ENVIRONMENT` set to something other than `development` will crash-loop until `PARAVANT_API_KEY` is set. This is intended. `DEPLOYMENT.md` carries the upgrade note.
- **References:** DEC-2026-02-08-004 (explicit CORS origins - the ordering constraint here interacts with it), `docs/PRODUCTION_READINESS_ASSESSMENT.md` sections 2.5 and 3.2 finding #1, `SECURITY.md`.

---

### DEC-2026-08-14-002: Documentation Freshness Is Part of the Change, Not a Follow-Up
- **Decision:** A change that makes any sentence in a tracked `.md` file untrue must update that sentence in the same commit. Enforced by `.claude/rules/documentation-freshness.md` and `.agent/rules/documentation-freshness.md`, referenced from section 4A of `.claude/CLAUDE.md` and `.agent/SYSTEM.md`, with the post-implementation checklist extended accordingly. `docs/archive/` is exempt as a deliberate historical record.
- **Context:** Implementing DEC-2026-08-14-001 invalidated claims in eight tracked documents, several of which stated flatly that "no authentication exists". The repository had already accumulated this failure independently: `.agent/rules/mvp-scope-control.md` was missing the DEC-2026-05-28-001 market-type amendment that `.claude/` carried, so non-Claude agents were reading a scope rule forbidding futures backtesting that had in fact been permitted since 2026-05-28.
- **Rationale:**
  - **Stale documentation is worse than absent documentation.** Absent docs make a reader go and check. Stale docs make a reader trust a false claim. In this repository the false claims include security posture and trading safety, which a reader may act on with real money.
  - **Discovery must be mechanical, not remembered.** The rule requires grepping for the OLD claim rather than recalling which files mention a concept. The old claim is what is now wrong and it is what the search must target. Memory is exactly what failed for `mvp-scope-control.md`.
  - **Partial fixes are the dangerous case.** Rule 7 forbids deleting a documented limitation when only partially fixing it. A partial fix that reads as complete is worse than the original warning, because the reader stops looking. This is why `SECURITY.md` now enumerates what the API key does NOT give rather than simply removing the warning.
  - **Wrong and outdated are different failures.** Rule 6 keeps the existing practice of marking corrections visibly (as `RESEARCH_FINDINGS.md` and section 2.8 of the assessment already do) while allowing merely-outdated facts to be updated in place. Silently deleting an error destroys the record of having made it, which in a research repository is itself a finding.
  - **The rule extends dual-file sync beyond DECISIONS.md.** `decision-consistency.md` Rule 0 covered only the decision logs. The observed drift was in a rules file, so Rule 4 here covers every paired `.claude/` and `.agent/` artifact.
- **Alternatives Considered:**
  - **A CI job asserting doc freshness:** REJECTED for now - "is this sentence still true" is not mechanically checkable in general. A grep-based linter for a fixed list of forbidden stale phrases was considered and deferred; it would catch a narrow class and give false confidence about the rest.
  - **A periodic documentation audit:** REJECTED - a scheduled sweep means documents are knowingly wrong between sweeps, which is the failure being fixed.
  - **Folding it into `zero-technical-debt.md`:** REJECTED - that file is about code. A separate file is discoverable by name and can be cited on its own.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-14
- **Implemented By:** This decision; applied immediately to DEC-2026-08-14-001's documentation.
- **Affected Files:** `.claude/rules/documentation-freshness.md` (new), `.agent/rules/documentation-freshness.md` (new, identical), `.claude/CLAUDE.md` (section 4A + checklist + quick reference), `.agent/SYSTEM.md` (identical), `.agent/rules/mvp-scope-control.md` (drift corrected against `.claude/`).
- **References:** `.claude/rules/decision-consistency.md` Rule 0 (dual-file sync, extended here), `.claude/rules/zero-technical-debt.md` Rule 13.2 (explicit change summary, extended here to name updated documents), DEC-2026-05-28-001 (the amendment that had drifted).

---

### DEC-2026-08-14-003: Rate Limiting on State-Mutating Endpoints -- Reuse the TokenBucket Primitive, Invert the Policy
- **Decision:** State-mutating requests are capped by two independent token buckets in `src/api/rate_limit.py`: per-client (`API_RATE_LIMIT_PER_MINUTE`, default 30, keyed on the leftmost `X-Forwarded-For` else peer IP) and global (`API_RATE_LIMIT_GLOBAL_PER_MINUTE`, default 120, keyed on nothing). Exceeding either returns `429` with `Retry-After`. Read endpoints are not limited. The `TokenBucket` primitive from `src/brokers/binance/rate_limiter.py` (DEC-2026-02-10-002) is reused; the `RateLimiter` class from that module is deliberately NOT.
- **Context:** Item 3.2 of `docs/PRODUCTION_READINESS_ASSESSMENT.md`, and the gap `SECURITY.md` named after DEC-2026-08-14-001 landed: "a leaked key can be used as fast as the process will serve it". The assessment offered `slowapi` or a custom dependency reusing the existing token bucket.
- **Rationale:**
  - **Reuse the primitive, invert the policy.** `RateLimiter.acquire()` blocks with `await asyncio.sleep()` until tokens are available. That is correct for OUTBOUND calls to Binance, where waiting beats being banned. It is wrong INBOUND: a held request occupies a connection and a coroutine, so 10,000 excess requests would become 10,000 sleeping tasks -- the limiter would amplify the flood it exists to absorb. Inbound must reject immediately. `TestRejectionIsNotBlocking` asserts this: 20 rejections against a 2/minute bucket must complete in under 5 seconds.
  - **No new dependency.** `slowapi` was rejected under zero-technical-debt Rule 2.3: an in-repo, already-tested primitive solves the problem. `TokenBucket` has two dedicated test files and needed no modification.
  - **Per-client alone does not work, and this is the crux.** Behind a proxy the real client address arrives in `X-Forwarded-For`, a header the CLIENT sets. An attacker rotates it and evades a per-IP bucket completely, while also filling the identity map with junk keys. Per-client is therefore fairness only, explicitly best-effort. The global bucket trusts no client-supplied value and is the actual security control. `test_global_limit_applies_across_distinct_identities` asserts rotation does not evade it.
  - **Bounded storage is a security property, not housekeeping.** Because identities are attacker-controlled, an unbounded map is a memory-exhaustion vector. Storage is an LRU capped at 1,024 entries with identities truncated to 64 characters. Evicting a bucket resets that client's allowance, which is an accepted trade: bounded memory beats perfect accounting for a client idle longer than 1,023 others.
  - **This layer sits INSIDE the auth layer.** Unauthenticated requests are rejected by `ApiKeyAuthMiddleware` first, for a cheap 401, and consume no rate budget. Placed outside auth, an anonymous flood could exhaust the global bucket and lock the operator out of their own kill switch -- precisely when they most need it. `test_unauthenticated_flood_yields_401_not_429` asserts the ordering holds in the real application stack.
  - **Limits are generous on purpose.** A human operator clicking buttons never approaches 30/minute; a runaway script exceeds it in seconds. The operator must never be rate-limited away from the kill switch, so the defaults separate human from machine rather than being set as tight as possible.
  - **Gate on HTTP method, consistent with DEC-2026-08-14-001.** A mutating endpoint added later is covered the day it is written rather than depending on an author remembering a decorator.
  - **Fail toward applying a limit.** An unparseable value in either env var logs a warning and falls back to the default rather than raising. A typo must not take the API down, and the fallback direction applies a limit rather than removing one.
- **Alternatives Considered:**
  - **`slowapi`:** REJECTED - a new dependency for a problem an existing, tested in-repo primitive solves.
  - **Reusing `RateLimiter` as-is:** REJECTED - its blocking policy is a DoS amplifier inbound. This is the single most important distinction in the decision.
  - **Per-client bucket only:** REJECTED - evaded entirely by rotating `X-Forwarded-For`, which is the realistic attack.
  - **Global bucket only:** REJECTED - one abusive client would deny service to the operator, including access to the kill switch.
  - **Limiting read endpoints too:** REJECTED - reads cannot place orders, and the dashboard polls them.
  - **Redis or another shared store for cross-process state:** REJECTED - a new infrastructure dependency for a single-worker deployment. The per-process limitation is documented rather than engineered around.
  - **Trusting `X-Forwarded-For` only from a configured proxy allowlist:** DEFERRED - correct in principle, but it requires knowing Railway's egress ranges and would silently degrade if they changed. The global bucket achieves the security goal without that fragility.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-14
- **Implemented By:** Assessment plan item 3.2
- **Affected Files:** `src/api/rate_limit.py` (new), `src/api/main.py` (middleware registration + stack-order comment), `tests/unit/api/test_rate_limit.py` (new, 27 tests), `.env.example`, `SECURITY.md`, `README.md`, `DEPLOYMENT.md`, `docs/ARCHITECTURE.md` (new section 8.2), `docs/API_CONTRACT.md`, `docs/PROJECT_CONTEXT.md`, `docs/PRODUCTION_READINESS_ASSESSMENT.md`, `.claude/rules/documentation-freshness.md` + `.agent/` copy (Rule 7 example extended).
- **Known limits, recorded deliberately:** per-client identity is spoofable; buckets are per process, so limits multiply by uvicorn worker count and reset on restart; a leaked key can still be used indefinitely within the global cap. This bounds the RATE of damage, not the TOTAL. All enumerated in `SECURITY.md`.
- **Governance side-effect:** writing the tests for this change produced `tests/unit/test_governance_sync.py`, which mechanically enforces DEC-2026-08-14-002 (`.claude`/`.agent` parity, decision-ID uniqueness, footer count accuracy, every env var the code reads being present in `.env.example`). It immediately found three pre-existing defects: the footer count was wrong by 18, `DEC-2026-02-15-001` and `DEC-2026-02-15-002` are each duplicated in two transcriptions, and the corrected count committed earlier that day was itself off by one because it counted the `DEC-YYYY-MM-DD-XXX` template. The duplicate IDs are allowlisted pending an owner decision on which copy is canonical.
- **References:** DEC-2026-02-10-002 (TokenBucket primitive reused here), DEC-2026-08-14-001 (auth layer this sits inside), DEC-2026-08-14-002 (documentation freshness applied to this change), `.claude/rules/zero-technical-debt.md` Rule 2.3 (dependency discipline), `docs/PRODUCTION_READINESS_ASSESSMENT.md` item 3.2.

---

### DEC-2026-08-14-004: Coverage Is Measured Over the Whole Suite, Not a Subset
- **Decision:** The CI coverage job runs `pytest tests/` rather than `pytest tests/unit tests/research`, and the floor moves from 62% to 72% against a measured 74%. Assessment finding #11 (`data/store.py` at 28%) is closed as a MEASUREMENT defect, not a coverage gap: the module was at 100% the whole time. Separately, 36 tests in `tests/unit/data/test_store_queries.py` close the `DataStore` paths that genuinely had no coverage from any suite.
- **Context:** Item 2.10 asked to raise `data/store.py` from 28% to 80%. Measuring before writing showed 28% under `tests/unit + tests/research` and 79% under `tests/`. `DataStore` is tested from `tests/integration/test_datastore_crud.py` and `test_datastore_extended.py`, which the CI `test` job runs on every commit while the CI `coverage` job excluded them. The same artifact affected `src/api/main.py` (42% vs 86%).
- **Rationale:**
  - **The finding was an artifact of the instrument, so the instrument is what gets fixed.** Writing unit tests to move 28% to 80% would have duplicated coverage that already existed, purely to move a number. That is the precise failure this repository's research layer exists to catch -- optimising a metric rather than the thing the metric proxies -- and doing it to test coverage while publishing a paper about not doing it to Sharpe ratios would be indefensible.
  - **The integration tests were never the problem.** They run in CI, they pass, they are deterministic since DEC-2026-08-11-004 made network tests opt-in. There was no remaining reason to exclude them from measurement; the exclusion most likely predates that fix, when they errored without connectivity.
  - **A subset-scoped floor is worse than no floor.** It reports a number that is precise, official, enforced, and wrong in a specific direction: it systematically understates any module whose tests live in `tests/integration/`. That is how a fully-covered 1,332-line data facade came to be ranked as a finding in a document that was otherwise careful.
  - **The genuine gaps were real but small.** 93 of 436 statements had no coverage from any suite: the order query variants (`get_orders_by_status`, `get_orders_by_account_and_status`, `count_open_orders`, `get_order_by_external_id`), the `update_order` / `update_position` field validators, the symbol registry, and the whole paper-session persistence block. That last one matters most -- `upsert_paper_session` runs every poll cycle and `get_paper_session` on startup, so a break there silently resets the paper history that the promotion gate (DEC-2026-06-01-001) reads as evidence.
  - **New tests live under `tests/unit/`, not `tests/integration/`.** They are fast, hermetic and use the function-scoped SQLite fixture, so they belong there regardless of the scope change. This also means they would have counted even if the job scope had been left alone.
  - **Floor set to 72 against 74.** Two points of headroom for ordinary variation, consistent with the previous 62-against-63 convention. Ratchet up, never down.
- **Alternatives Considered:**
  - **Write unit tests duplicating the integration coverage to reach 80%:** REJECTED - metric-gaming, and it would add maintenance burden for zero real assurance.
  - **Leave the job scope and accept the misleading number:** REJECTED - it had already produced one wrong finding in a document intended to be authoritative, and would produce more.
  - **Add a second coverage job for integration only:** REJECTED - two numbers to reconcile, and neither would be the answer to "how much of this code is covered".
  - **Keep the floor at 62 after widening scope:** REJECTED - a floor 12 points below the measured value enforces nothing.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-14
- **Implemented By:** Assessment plan items 2.9 and 2.10
- **Affected Files:** `.github/workflows/ci.yml` (coverage job scope + floor), `tests/unit/data/test_store_queries.py` (new, 36 tests), `README.md`, `docs/PROJECT_CONTEXT.md`, `docs/PRODUCTION_READINESS_ASSESSMENT.md` (section 2.2 correction, finding #11, items 2.9 and 2.10).
- **Measured before and after:** `src/data/store.py` 28% -> 100%; `src/api/main.py` 42% -> 86%; project total 67% -> 74%; suite 1,981 -> 2,017 passing, 0 failing.
- **Generalisation worth carrying:** a number that is enforced is not the same as a number that is true. The coverage floor, the `DECISIONS.md` footer count (DEC-2026-08-14-002) and the Stage-1 hypothesis rubric (DEC-2026-08-13-003) are three instances of the same failure in this repository within one week. Where a claim is mechanically checkable, check it mechanically.
- **References:** DEC-2026-08-11-004 (network tests opt-in, which made whole-suite measurement deterministic), DEC-2026-08-14-002 (documentation freshness; numbers are claims), DEC-2026-02-08-006 (eager loading, exercised by the new query tests), DEC-2026-06-01-001 (promotion gate that consumes paper-session state), `docs/PRODUCTION_READINESS_ASSESSMENT.md` finding #11.

---

### DEC-2026-08-14-005: Timing Tests Control the Clock; They Do Not Sleep on It
- **Decision:** A test asserting time-dependent behaviour drives a controlled clock rather than calling `time.sleep` and asserting against wall-clock elapsed time. Applied to `test_bucket_refill_partial_second` in `tests/unit/test_rate_limiter_edge_cases.py`.
- **Context:** During the whole-suite verification for DEC-2026-08-14-004 the suite failed once on that test, then passed ten consecutive times in isolation. It slept 10ms and asserted `tokens <= 50.15`, allowing 15ms of refill -- roughly 5ms of slack against a default Windows timer granularity of about 15.6ms. Under full-suite load the sleep overshoots and the assertion fails. The test had presumably been intermittently failing since it was written; nothing had made it visible because it usually ran on an unloaded machine.
- **Rationale:**
  - **A flaky test is worse than no test.** It teaches readers that a red suite means "re-run CI" rather than "read the failure". That habit is what allows a genuine regression to be waved through, and this repository depends on its suite being trustworthy: the promotion gate and the demotion guardrail both read from data the suite is supposed to protect.
  - **The assertion was testing the wrong thing.** With a real sleep, the subject under test is partly the OS scheduler. Driving the clock isolates the refill arithmetic, which is the actual contract, and lets the assertion be exact (`== approx(50.1)`) rather than a tolerance band. A tighter assertion on a smaller surface is strictly better.
  - **Widening the tolerance was the tempting fix and the wrong one.** It would have hidden the flake at the cost of a test that no longer distinguishes correct refill from roughly-correct refill, and the next contributor under heavier load would widen it again.
  - **`last_refill` needs explicit handling.** `TokenBucket.last_refill` uses `field(default_factory=time.time)`, which binds the real function at class-definition time and is therefore unaffected by patching `time.time` afterwards. The test sets it onto the controlled clock explicitly, and says so in a comment, because this is a genuine trap for the next person who patches the clock here.
  - **Scope was checked before generalising.** The other four sleep sites in the suite were inspected: `tests/unit/test_rate_limiter.py` sleeps 1.1s with an explicit jitter allowance or asserts a capacity-capped value, and `tests/unit/data/test_base.py` asserts only that a mechanism exists. None has slack narrower than timer granularity, so none was changed. One fragile test was fixed rather than five rewritten -- this is not a licence to churn passing tests.
- **Alternatives Considered:**
  - **Widen the tolerance to 50.5:** REJECTED - hides the flake, weakens the assertion, recurs under heavier load.
  - **Mark the test `flaky` / add a retry plugin:** REJECTED - institutionalises the problem and adds a dependency.
  - **Delete the test:** REJECTED - sub-second refill is real behaviour worth asserting; the bug was in how it was asserted, not that it was.
  - **Inject a clock into `TokenBucket` as a constructor parameter:** REJECTED for now - it is the cleaner long-term design and matches the injectable clock already used in `orchestrator.py`, but it changes production code to suit a test. Deferred until something in production needs it.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-14
- **Implemented By:** Whole-suite verification for DEC-2026-08-14-004
- **Affected Files:** `tests/unit/test_rate_limiter_edge_cases.py` only. `src/brokers/binance/rate_limiter.py` is UNCHANGED -- the defect was in the test, not the subject.
- **Verification:** ran ten consecutive times in isolation and once in the full 2,054-test suite; deterministic in all eleven.
- **References:** DEC-2026-02-10-002 (the TokenBucket under test), DEC-2026-08-14-004 (the whole-suite run that exposed this), DEC-2026-08-11-004 (hermetic tests -- same principle applied to environment rather than time).

---

### DEC-2026-08-15-001: `docker compose up` Must Work on a Fresh Clone, and Must Not Inherit Live Configuration
- **Decision:** `docker-compose.yml` declares every variable inline with `${VAR:-default}` instead of requiring `env_file: .env`, runs `scripts/init_db.py` before handing off to uvicorn, and **hardcodes** `LIVE_TRADING_ENABLED=false` and `BINANCE_TESTNET=true` rather than interpolating them. Dependabot is enabled for pip, npm, github-actions and docker. The README carries CI, Python and licence badges.
- **Context:** Pre-publication review of what a reviewer meets in the first five minutes. `docker compose up` is the most likely "let me try this" command and it failed outright on a clean clone.
- **Rationale:**
  - **Two independent failures, both the same class as the `init_db.py` Windows crash (DEC-2026-08-11-003): a documented path nobody had walked.** First, `env_file: .env` made a gitignored file a hard requirement, so the command errored before starting anything. Second, nothing created the schema -- `init_db()` in `src/data/database.py` is a function only `scripts/init_db.py` calls, so the API would have booted and failed every query with "no such table". A reviewer would have concluded the system does not work, and been right about the evidence available to them.
  - **The mainnet leak is the serious finding.** `BINANCE_TESTNET: ${BINANCE_TESTNET:-true}` looks safe and is not. Compose reads a local `.env` for `${VAR}` substitution independently of `env_file`, so on a developer machine whose `.env` sets `BINANCE_TESTNET=false`, `docker compose config` resolved to `"false"` -- a local demo container pointed at real markets. This is the same leak the test suite had before its hermetic fixture (DEC-2026-08-11-004), arriving through a different door, which is why it is recorded rather than quietly fixed. Live-affecting settings are now hardcoded, and no `BINANCE_API_KEY` or `BINANCE_SECRET_KEY` is passed into the container, so it cannot reach a funded account even if a setting were wrong.
  - **Pinning and Dependabot are two halves of one trade.** Exact pins (requirements.txt, 2026-08-13) removed surprise upgrades but moved the burden of noticing advisories onto a human who will not reliably notice. Dependabot makes upgrades visible while pins keep them deliberate. Updates are grouped and rate-limited because an unbounded stream of single-dependency PRs on a solo project gets ignored, and an ignored alert is worse than none -- the same reasoning as the flaky test in DEC-2026-08-14-005.
  - **The CI badge is the highest signal-per-character item in the repository.** Seven CI jobs existed and the front page did not say so.
- **Alternatives Considered:**
  - **`env_file: [{path: .env, required: false}]`:** REJECTED - correct, but needs Compose 2.24+, and inline defaults are readable without knowing that.
  - **Committing a working `.env`:** REJECTED - trains the habit of committing a file that holds credentials.
  - **Calling `init_db()` from the API startup event:** REJECTED - schema creation is a deployment step, not a request-serving concern, and it would silently create a schema against a misconfigured production `DATABASE_URL`.
  - **Adding Postgres and the frontend now:** DEFERRED to item 4.1 proper. Fixing the broken path is separable from widening it, and mixing them would violate one-change-one-intent.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-15
- **Implemented By:** Assessment plan item 4.1 (partial)
- **Affected Files:** `docker-compose.yml`, `.github/dependabot.yml` (new), `README.md` (badges), `DEVELOPMENT_SETUP.md`, `docs/PRODUCTION_READINESS_ASSESSMENT.md`.
- **Verification status, stated honestly:** `docker compose config` validates and `scripts/init_db.py` was confirmed to succeed and to be idempotent across restarts. **The container was NOT observed serving `/health`** -- the Docker daemon was not running on the machine where this landed. Item 4.1 stays marked partial until someone watches it come up. Recording an unverified claim as verified would be the precise failure this repository's research layer exists to prevent.
- **References:** DEC-2026-08-11-003 (pre-publication hygiene; same defect class), DEC-2026-08-11-004 (hermetic environment; same leak, different door), DEC-2026-05-27-001 (kill switch defaults OFF), DEC-2026-08-14-001 (API key gate the compose file leaves optional in development), DEC-2026-08-14-005 (an ignored signal is worse than none).

---

### DEC-2026-08-16-001: Frontend Test Infrastructure First, Then the Dependency Upgrades It Made Safe
- **Decision:** Add Vitest + React Testing Library + jsdom with 59 tests covering the shared formatters, the regime hook, `PositionsTable`'s gain/loss handling, `EmergencyPanel`'s typed confirmation gate, and a router API contract test. Wire `npm test` into CI as a blocking job with **no coverage floor**. Then, with that net in place, upgrade `react-router-dom` 6.30.3 -> 7.18.2 and add a blocking `pip-audit` job. Vitest runs test files sequentially (`fileParallelism: false`).
- **Context:** Assessment items 3.7 and 3.2. The operator declined item 3.4 (wiring pages to real data) out of concern for breaking the frontend, which was the correct call and identified the real blocker: the frontend had **zero** tests. CI ran `tsc -b`, which proves types line up and says nothing about behaviour, so 17,000 lines of UI were unverifiable.
- **Rationale:**
  - **The assessment's ordering was wrong and the operator caught it.** It lists 3.4 (rewire) before 3.7 (tests). Tests are what make rewiring safe, so they come first. This decision inverts that order and the react-router upgrade is the immediate proof: the upgrade was performed against a green baseline of 59 tests rather than against nothing.
  - **The canary was written before the change, not after.** `src/App.routing.test.tsx` exercises exactly the seven react-router symbols the app imports and was confirmed green on 6.30.3 **before** the bump. A test written after a migration only proves the migration's end state is self-consistent; written before, it proves behaviour did not change.
  - **The upgrade was safe because the app had already opted in.** `BrowserRouter` carried `future={{ v7_startTransition, v7_relativeSplatPath }}`, which are precisely the v6->v7 behaviour changes. In v7 both are the default and the prop no longer exists, so `tsc -b` failed on it and the fix was a deletion with no runtime change.
  - **Sequential test execution is a correctness fix, not a performance tuning.** Vitest defaults to one worker per core, each with its own jsdom; the combined heap footprint produced a FATAL out-of-memory that killed a DIFFERENT test file on each run -- 47 of 59 tests one run, 15 the next. A non-deterministic OOM in CI is indistinguishable from a real failure and trains everyone to hit re-run, the same failure mode as DEC-2026-08-14-005. The react-router bump added the module weight that surfaced it; the cause was always the worker count.
  - **No frontend coverage floor, deliberately.** Five test files over a prototype would report a number either meaningless or immediately blocking. A gate that is routinely overridden teaches people to override gates. Add one when the suite covers a defensible surface.
  - **Two known defects are documented by test rather than fixed.** `useRegimeState` discards the last good regime on any failed poll, because the guard in its catch block reads a `regime` captured from the first render and therefore always null. `PositionsTable` falls back to hardcoded equity positions (NVDA, MSFT, TSLA) when `data` is undefined, in a crypto-only system. Both are labelled KNOWN ISSUE / KNOWN FOOTGUN in the tests, with instructions to delete the test when fixed. Fixing them here would have mixed behaviour changes into a test-infrastructure commit.
  - **pip-audit blocks rather than advises.** An advisory security job is a job people learn to scroll past. It audits `requirements.txt` only: a CVE in a linter that never sees untrusted input is not a reason to block a merge.
- **Alternatives Considered:**
  - **Wiring pages to real data first (item 3.4):** REJECTED by the operator, correctly. Refactoring untested UI is how a working prototype quietly stops working.
  - **Rendering `App` itself in the routing test:** REJECTED - it mounts four providers and ten lazy pages, several fetching on mount. It would fail for reasons unrelated to routing. `App.tsx`'s own route table is covered by `tsc -b` and the production build.
  - **Asserting the confirmation dialog disappears after EXECUTE:** REJECTED - `AnimatePresence` keeps the exiting node mounted for its transition, so that assertion races framer-motion. The tests assert the outcome (the action fired / did not fire) instead.
  - **Raising the V8 heap via `NODE_OPTIONS` instead of serialising:** DEFERRED - it hides the growth rather than bounding it, and the suite runs in ~41s sequentially. It is the next lever if that stops being true.
  - **`npm audit fix --force`:** REJECTED - it performs semver-major bumps unattended. The upgrade was done deliberately, with a baseline and a verification pass.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-16
- **Implemented By:** Assessment plan items 3.7 and 3.2
- **Affected Files:** `frontend/vitest.config.ts` (new), `frontend/src/test/setup.ts` (new), `frontend/src/lib/utils.test.ts` (new), `frontend/src/hooks/useRegimeState.test.ts` (new), `frontend/src/components/dashboard/PositionsTable.test.tsx` (new), `frontend/src/components/dashboard/EmergencyPanel.test.tsx` (new), `frontend/src/App.routing.test.tsx` (new), `frontend/package.json`, `frontend/src/App.tsx` (future prop removed), `requirements-dev.txt`, `.github/workflows/ci.yml` (frontend-test and audit jobs).
- **Measured:** frontend 0 -> 59 tests, deterministic across three consecutive runs; `npm audit --omit=dev` 3 moderate -> **0** vulnerabilities; production bundle 416.74 kB -> 435.81 kB (+19 kB, the v7 cost); eslint unchanged at 0 errors / 80 warnings; `tsc -b` and `vite build` green.
- **Verification gap, stated honestly:** the `pip-audit` job has never been observed running. The machine it landed on could not reach pypi.org (TLS chain failure), so its baseline is unknown and it may be red on first CI run. Triage the findings rather than reaching for `--ignore-vuln`.
- **References:** DEC-2026-08-14-005 (a non-deterministic signal trains people to ignore the channel -- the reasoning behind serialising the runner), DEC-2026-08-15-001 (Dependabot; pip-audit is the blocking half of the same trade), `docs/PRODUCTION_READINESS_ASSESSMENT.md` items 3.2, 3.4 and 3.7.

---

### DEC-2026-08-16-002: The Project Is a Validation System That Returns `no`, Not a System Built to Fail -- and Cross-Document Consistency Is Enforced by Test
- **Decision:** Reframe the headline from "a validation layer built to prove its own strategies don't work" to "a validation layer that decides whether a strategy has a real edge, and is built to return `no` when the evidence is not there". The null result stays in the second line, bold and unqualified. Separately, extend `documentation-freshness.md` with Rules 10-13 (one owner per claim, repeated numbers derived and asserted, correction style by informativeness, one concept one name) and add `tests/unit/test_doc_consistency.py` to enforce them mechanically.
- **Context:** Raised by the operator: the previous framing "might give the wrong idea about building a system that doesn't work". Separately, they asked that documentation stop drifting and stop saying different things in different places.
- **Rationale:**
  - **The old framing was inaccurate, which is the real objection.** Nobody builds a trading system *in order to* prove its strategies fail. The project was built to find out whether edge existed, with honest validation so the answer would mean something. The null result is the OUTCOME, not the design goal. Stating it as the goal misdescribes the artifact, and a reviewer who notices that discounts everything else.
  - **The artifact is the harness, and it is reusable.** "Point it at a strategy and it tells you whether the result survives multiple-comparisons correction and realistic costs" describes something with standing value. "We proved ours don't work" describes a postmortem. The first is true and more useful.
  - **The positioning follows from the accuracy, not the other way round.** Evaluation engineering -- pre-registration, multiple-comparisons correction, holdout hygiene, Goodhart resistance, negative-space tracking -- is directly the skill set LLM evals work requires, and the repository genuinely contains it. The reframe is not spin toward that; it is a more accurate description that happens to land there.
  - **The null result must not soften, and that is the specific risk this change carried.** A reviewer who finds the headline hedged distrusts everything else, and the honesty is the differentiator. `TestNarrativeConsistency` asserts "None has a validated edge" survives in `README.md` and its counterpart in `RESEARCH_FINDINGS.md`, and fails on phrases that would contradict the null result. The framing may change again; the result may not quietly.
  - **Cross-document consistency is a distinct failure mode from staleness.** Rules 1-9 keep a document true against the code. They do nothing about five documents that are each individually plausible and collectively contradictory. Every restatement of a claim is an independent thing to remember, so the rule is: the owning document states it, others link.
  - **The rule was written against a real instance, not a hypothetical.** `PROJECT_CONTEXT.md` and the readiness assessment claimed "14 route modules"; `ARCHITECTURE.md` said 13. Ground truth was 13 -- including at `622ac49`, the commit the assessment was written against. It was wrong when written and had been copied twice. Ground truth for a repeated count must be the code, never another document.
  - **Rule 12 sharpens Rule 6 rather than replacing it.** "Mark, do not erase" was producing pressure to annotate trivia. The line is now whether the error is informative: a withdrawn research result gets marked because "we got this wrong and caught it" is part of the document's value; a miscount of files gets fixed inline, with the history in the commit message where it belongs.
- **Alternatives Considered:**
  - **Leave the framing alone:** REJECTED - it is inaccurate, which is a stronger objection than it being unflattering.
  - **Drop or soften the null result while reframing:** REJECTED, and actively guarded against by test. It would trade the repository's one genuinely distinguishing property for a marginally better first impression.
  - **A separate `documentation-consistency.md` rules file:** REJECTED - four rules files already exist and the domain is the same ("documentation must be true"). Freshness is truth against the code; consistency is truth against other documents.
  - **Asserting test counts and coverage across documents:** REJECTED per Rule 11.3 - they churn every commit, so the test would fail on unrelated work and would be deleted. Stated once, dated, in the owning document.
  - **A general prose-similarity or LLM-based consistency check:** REJECTED - unfalsifiable and unmaintainable. Narrow regex claims with computed ground truth fail loudly and for one legible reason.
- **Status:** ACTIVE
- **Date Decided:** 2026-08-16
- **Implemented By:** Operator request, 2026-08-16
- **Affected Files:** `README.md` (headline), `docs/PROJECT_CONTEXT.md` (section 1 framing, route-module count x2), `docs/PRODUCTION_READINESS_ASSESSMENT.md` (route-module count), `.claude/rules/documentation-freshness.md` + `.agent/` copy (Rules 10-13), `tests/unit/test_doc_consistency.py` (new, 19 tests).
- **Defects found while writing the enforcement:** the "14 route modules" error in three places across two documents, wrong since it was first written. Two test-design errors of my own were caught by the same run and are recorded because both are traps for the next person: a pattern matching `(\d+) endpoints` also matched "21 endpoints mutate state", reporting a contradiction between two correct claims about different things; and asserting a literal phrase against raw text failed because the repository hard-wraps prose at ~80 columns and a newline sat inside the phrase.
- **References:** DEC-2026-08-14-002 (documentation freshness, extended here), DEC-2026-08-14-004 (a number that is enforced is not the same as a number that is true -- the same lesson, applied to prose), `.claude/rules/zero-technical-debt.md` Rule 3 (naming drift in code; Rule 13 is its prose counterpart), `docs/RESEARCH_FINDINGS.md` (the owning document for the null result).
