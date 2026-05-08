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
- **Status:** LOCKED until Q2 2026 review
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
**Total Decisions:** 23 active, 0 superseded, 5 locked
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

**End of Decisions Log**

**Total Decisions:** 58 active, 0 superseded, 5 locked
**Last Updated:** 2026-03-11
**Next Decision ID:** DEC-2026-03-11-001

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
