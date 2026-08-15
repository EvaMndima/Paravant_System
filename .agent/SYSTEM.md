# PARAVANT Trading System - Project Instructions

## MANDATORY: Read Before ANY Work

This file contains project-specific instructions that MUST be followed for all code changes, implementations, and refactoring in the PARAVANT Trading System.

---

## 1. DECISION CONSISTENCY (MANDATORY)

**BEFORE implementing ANY feature, fix, or change:**

1. **READ** `.claude/DECISIONS.md` - Review all documented decisions
2. **IDENTIFY** relevant decisions affecting your work (use DEC-YYYY-MM-DD-XXX IDs)
3. **VERIFY** your implementation is consistent with decision rationale
4. **DOCUMENT** any new decisions or changes to existing decisions

**AFTER completing implementation:**

1. **VERIFY** all relevant decisions were followed
2. **UPDATE** `.claude/DECISIONS.md` with any new decisions made
3. **CROSS-CHECK** code matches documented rationale

**See:** `.claude/rules/decision-consistency.md` for detailed enforcement rules.

**THIS IS NON-NEGOTIABLE.** Decision consistency prevents architectural drift and technical debt.

---

## 2. Development Environment (MANDATORY FOR ALL SESSIONS)

### Environment Setup Summary

```
Project: PARAVANT Trading System
Python Version: 3.11+ (see .python-version)
Virtual Environment: venv (NOT conda)
Setup Method: Automated scripts (setup_dev.bat / setup_dev.sh)
Database: SQLite (development), PostgreSQL (production)
```

### First-Time Setup (Local Development)

**Windows:**
```bash
setup_dev.bat
```

**Linux/macOS:**
```bash
chmod +x setup_dev.sh
./setup_dev.sh
```

### Subsequent Sessions (EVERY TIME)

**ALWAYS activate the virtual environment before running ANY Python code:**

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

**Verify activation:**
```bash
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

### Troubleshooting "Module Not Found" Errors

**CAUSE:** Running Python outside the virtual environment

**SOLUTION:**
1. Activate venv (see above)
2. If still fails: `pip install -r requirements.txt` (inside activated venv)
3. Never run Python commands outside activated venv

### Why venv (not conda)?

**Decision:** DEC-2026-02-08-001 (see `.claude/DECISIONS.md`)
- Pure Python project (no scientific computing packages)
- Simpler dependency management
- Better CI/CD integration
- Smaller footprint
- Standard Python tooling

---

## 3. Code Quality Standards (Zero-Technical-Debt)

### All code MUST follow these standards:

#### A. Type Hints (100% Coverage Required)
```python
# CORRECT - Full type hints with SQLAlchemy 2.0 Mapped[T] syntax
from sqlalchemy.orm import Mapped, mapped_column
balance: Mapped[float] = mapped_column(Float, nullable=False)

# INCORRECT - Missing type hints
balance = Column(Float, nullable=False)
```

#### B. Timezone-Aware Timestamps (ALWAYS)
```python
# CORRECT - Timezone-aware
from datetime import datetime, timezone
created_at = datetime.now(timezone.utc)

# INCORRECT - Naive datetime (deprecated)
created_at = datetime.utcnow()  # NEVER USE THIS
```

#### C. Mutable Defaults (NEVER use dict/list defaults)
```python
# CORRECT - Lambda function for mutable defaults
from typing import Any, cast
risk_config: Mapped[dict[str, Any]] = mapped_column(
    JSON,
    nullable=False,
    default=lambda: cast(dict[str, Any], {})
)

# INCORRECT - Mutable default bug
risk_config: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
```

#### D. Input Validation (All Numeric Fields)
```python
# CORRECT - Comprehensive validation
from sqlalchemy.orm import validates
import math

@validates("balance_usdt", "equity_usdt")
def validate_financial_values(self, key: str, value: float) -> float:
    if value is None:
        raise ValueError(f"{key} cannot be None")
    if math.isnan(value):
        raise ValueError(f"{key} cannot be NaN")
    if math.isinf(value):
        raise ValueError(f"{key} cannot be Infinity")
    if value < 0:
        raise ValueError(f"{key} must be non-negative")
    return value
```

#### E. N+1 Query Prevention (Use Eager Loading)
```python
# CORRECT - Eager loading with selectinload
from sqlalchemy.orm import selectinload

stmt = (
    select(Order)
    .options(
        selectinload(Order.account),
        selectinload(Order.strategy),
        selectinload(Order.trades)  # Prevents N+1
    )
)

# INCORRECT - Lazy loading causes N+1 queries
orders = session.query(Order).all()  # Will trigger 100s of queries
```

#### F. Security Best Practices
```python
# CORRECT - Explicit CORS origins
ALLOWED_ORIGINS_DEV = [
    "http://localhost:3000",
    "http://localhost:8000",
]

# INCORRECT - Wildcard CORS (CRITICAL SECURITY ISSUE)
allow_origins=["*"]  # NEVER DO THIS
```

---

## 4. Documentation Requirements

### 4A. DOCUMENTATION FRESHNESS (MANDATORY)

**A change is not finished until the documentation describing it is true.**

If a change makes any sentence in a tracked `.md` file untrue, that sentence is
updated in the **same commit**. Not a follow-up, not a TODO. This applies
whether or not the user asks for it -- "update the docs" is part of "make the
change", not a separate request.

Before reporting any behaviour-changing task complete:

1. **Grep for the OLD claim**, not the new one. The old claim is what is now
   wrong: `grep -rniE "<concept>|<old-config-key>" --include=*.md .`
2. **Check the owning document** for each category the change touched (security,
   architecture, API contract, deployment, config template, decisions).
3. **Update paired files together** -- `.claude/` and `.agent/` copies.
4. **Never delete a documented limitation** when partially fixing it. Replace it
   with what is now true AND what is still not.
5. **State in your summary** which documents you updated and which you
   deliberately left alone.

`docs/archive/` is exempt -- those are historical snapshots, deliberately frozen.

**See:** `.agent/rules/documentation-freshness.md` for the full rules,
the canonical document map, and the discovery procedure.

**THIS IS NON-NEGOTIABLE.** Stale documentation is worse than absent
documentation: absent docs make a reader check, stale docs make a reader trust
a false claim. In this repository those claims govern real money.

### All functions/classes MUST have:
1. **Docstrings** explaining purpose (Google style)
2. **Type hints** on all parameters and returns
3. **Inline comments** for complex logic (WHY, not WHAT)

```python
def calculate_position_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float
) -> float:
    """Calculate position size based on risk parameters.

    Uses fixed fractional position sizing with stop loss distance.
    Formula: (capital * risk_pct) / (entry_price - stop_loss)

    Args:
        capital: Total account capital in USDT
        risk_pct: Risk percentage per trade (0.0 to 1.0)
        entry_price: Entry price for the position
        stop_loss: Stop loss price

    Returns:
        Position size in base currency units

    Raises:
        ValueError: If stop_loss >= entry_price (invalid risk)
    """
    if stop_loss >= entry_price:
        raise ValueError("Stop loss must be below entry price")

    risk_amount = capital * risk_pct
    risk_per_unit = entry_price - stop_loss

    # Position size = total risk / risk per unit
    return risk_amount / risk_per_unit
```

---

## 5. Testing Requirements

### Before marking any task complete:
- [ ] Unit tests written for new functionality
- [ ] Integration tests for database operations
- [ ] All tests pass locally
- [ ] No regressions introduced

```bash
# Run tests with coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## 6. Git Commit Standards

### Commit Message Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** feat, fix, docs, refactor, test, chore, perf, style

**Examples:**
```
feat(database): Add comprehensive input validation to all models

- Added @validates decorators to prevent NaN/Infinity values
- Validates negative values on financial fields
- Prevents data corruption at INSERT time

Addresses: Production audit findings (SEC-002)
Decision: DEC-2026-02-08-007

fix(api): Replace wildcard CORS with explicit origins

- Changed allow_origins=["*"] to explicit localhost list
- Production origins loaded from ALLOWED_ORIGINS env var
- Eliminates CRITICAL security vulnerability

Addresses: Production audit findings (SEC-001)
Decision: DEC-2026-02-08-004
```

---

## 7. Production Audit Compliance

### All code changes must maintain:
- [ ] Zero CRITICAL security issues
- [ ] Zero HIGH priority issues
- [ ] Grade A- or higher (95%+ production readiness)

**Run production audit after major changes:**
```
Use skill: @production-code-audit
```

---

## 8. Project-Specific Rules

### Locked Decisions (DO NOT CHANGE without explicit approval):
1. **Asset Class:** Crypto ONLY (no stocks/forex in MVP)
2. **Broker:** Binance ONLY (no other exchanges in MVP)
3. **Database:** SQLite (dev), PostgreSQL (prod) - no MongoDB/MySQL
4. **Orders:** Market orders ONLY (no limit orders in MVP)
5. **Architecture:** Monolithic (no microservices in MVP)

**See:** `.claude/rules/mvp-scope-control.md` for full scope rules

---

## 9. Error Handling Standards

### All database operations must:
```python
# CORRECT - Comprehensive error handling with logging
from src.utils.logging import get_logger

logger = get_logger(__name__)

try:
    with get_db() as session:
        result = session.execute(stmt)
        session.commit()
except IntegrityError as e:
    logger.error("database_integrity_error", error=str(e), exc_info=True)
    raise
except Exception as e:
    logger.error("database_error", error=str(e), exc_info=True)
    raise
```

---

## 10. Performance Requirements

### Query Optimization (MANDATORY):
- Use `selectinload()` for all relationships (prevents N+1)
- Use `joinedload()` for one-to-one relationships
- Add database indexes on foreign keys
- Monitor query counts in tests

**Target:** < 5 queries for typical operations (not 100+)

---

## 11. Structured Logging (MANDATORY)

### All log messages must use structured format:
```python
from src.utils.logging import get_logger

logger = get_logger(__name__)

# CORRECT - Structured logging
logger.info(
    "order_created",
    order_id=order.id,
    symbol=order.symbol,
    quantity=order.quantity,
    price=order.price
)

# INCORRECT - String concatenation
logger.info(f"Created order {order.id} for {order.symbol}")
```

---

## 12. Configuration Management

### All configuration must:
- **Sensitive data:** Environment variables (.env) - NEVER commit
- **Non-sensitive:** YAML files (config/settings.yaml)
- **Defaults:** Hardcoded in settings.py with env override

```python
# CORRECT - Environment variable with default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/trading.db")

# INCORRECT - Hardcoded sensitive value
API_KEY = "abc123secret"  # NEVER DO THIS
```

---

## 13. Pre-Implementation Checklist

**BEFORE starting ANY implementation:**

- [ ] Read relevant decisions in `.claude/DECISIONS.md`
- [ ] Review related PRD sections
- [ ] Check architectural constraints in `ARCHITECTURE.md`
- [ ] Verify MVP scope (`.claude/rules/mvp-scope-control.md`)
- [ ] Check Zero-Technical-Debt rules (`.claude/rules/zero-technical-debt.md`)
- [ ] Activate virtual environment (`source .venv/bin/activate`)
- [ ] Understand existing code patterns (read before writing)

---

## 14. Post-Implementation Checklist

**AFTER completing implementation:**

- [ ] All relevant decisions followed
- [ ] New decisions documented in `.claude/DECISIONS.md` AND `.agent/DECISIONS.md`
- [ ] Tests written and passing
- [ ] Type hints complete (100% coverage)
- [ ] Docstrings added
- [ ] Input validation implemented
- [ ] Eager loading used (no N+1 queries)
- [ ] Structured logging added
- [ ] Error handling comprehensive
- [ ] Code follows Zero-Technical-Debt rules
- [ ] **Grepped tracked `.md` files for the OLD claim and updated every stale one**
- [ ] **`.env.example` updated if configuration changed**
- [ ] **`DEPLOYMENT.md` carries an upgrade note if anything breaks existing deployments**
- [ ] **Summary names which documents were updated and which were left alone**
- [ ] Production audit shows no new issues

---

## 15. Quick Reference

### Essential Files
- `.claude/DECISIONS.md` - All architectural decisions
- `.claude/rules/decision-consistency.md` - Decision enforcement
- `.claude/rules/documentation-freshness.md` - Keeping `.md` files true after changes
- `.claude/rules/zero-technical-debt.md` - Code quality rules
- `.claude/rules/mvp-scope-control.md` - MVP scope boundaries
- `docs/README.md` - Documentation index and reading order
- `docs/RESEARCH_FINDINGS.md` - What the research established (and what was withdrawn)
- `docs/archive/build-plans/` - Completed phase plans and the MVP task index (historical)
- `TRADING_SYSTEM_PRD.md` - Product requirements
- `ARCHITECTURE.md` - System architecture

### Essential Commands
```bash
# Activate venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Run tests
pytest tests/ -v --cov=src

# Initialize database
python scripts/init_db.py

# Verify database
python scripts/verify_db.py

# Start API
uvicorn src.api.main:app --reload
```

---

## 16. Contact & Support

### When Stuck:
1. Check `.claude/DECISIONS.md` for context
2. Review relevant documentation files
3. Run production audit for quality issues
4. Ask user for clarification (use AskUserQuestion tool)

### When Unsure:
- **Default to simplicity** (avoid over-engineering)
- **Follow existing patterns** (consistency over novelty)
- **Ask before breaking** (don't guess)

---

**Last Updated:** 2026-02-08
**Applies To:** All code in PARAVANT Trading System
**Enforcement:** MANDATORY for all AI assistants and developers
