---
trigger: always_on
---

# MVP SCOPE CONTROL RULES
## Prevention of Scope Creep and Out-of-MVP Features

### Purpose

This rule file enforces **STRICT adherence to the MVP scope** defined in `TRADING_SYSTEM_PRD.md` Part 2.

These rules prevent:
- Adding features not in the MVP scope
- Implementing V1/V2/Maturity features prematurely
- Gold-plating (over-engineering MVP features beyond requirements)
- Mission creep during development

**Core Principle:** Build the **production-grade implementation** of **only** the features in the MVP scope. No scope creep, but no shortcuts either.

---

## 1. LOCKED SCOPE BOUNDARIES

### ✅ ALLOWED: MVP Features (MUST Build These)

The following features are **LOCKED IN** for MVP and must be implemented to **production quality**:

#### A. Asset Class & Broker
- **Asset:** Crypto ONLY (BTCUSDT, ETHUSDT, BNBUSDT)
- **Broker:** Binance ONLY (testnet for development)
- **Market type (LIVE execution):** **Binance Spot** — long-only, no leverage, no liquidation risk. This is the only market type permitted for real-capital execution under MVP.
- **Market type (RESEARCH/BACKTEST layer):** Long-short futures evaluation is **PERMITTED** via `BacktestConfig.allow_shorts` + `funding_rate_per_8h` (DEC-2026-05-28-001, 2026-05-28). This is research-only; it MUST NOT touch live capital until the staged plan's step 4 (validated short edge + live futures execution adapter + leverage/liquidation risk model) is complete.
- **Data:** OHLCV + Volume ONLY
- **Locked Until:** Q2 2026 review (broker); market-type lock amended 2026-05-28 — see DEC-2026-05-28-001 and PRD § 1.7.1

#### B. Manual Regime Tagging
- Regime options: trending_up, trending_down, ranging, volatile, unknown
- UI: Simple dropdown or button group
- Persistence: AccountConfig table

#### C. Strategy Library (6 Templates)
- Simple_MA
- Donchian_BB
- Scalper_RSI
- Conservative_EMA
- Momentum_MACD
- BreakoutRetest

**IMPORTANT:** Implement templates with **production-grade code quality**, not prototypes.

#### D. Risk Management (Core Rules)
- Max position size (% of capital)
- Max daily loss limit (% of capital)
- Max total drawdown limit (% of capital)
- Reject trade if breached

#### E. Execution Layer
- Market orders ONLY (no limit orders)
- Synchronous execution (no async order tracking)
- Simple order placement + fill confirmation

#### F. Data Pipeline
- Fetch OHLCV from Binance
- Store in SQLite
- Simple polling (no WebSocket for MVP)

#### G. Backtesting
- Historical simulation
- Simple metrics: win rate, total return, max drawdown
- No walk-forward or Monte Carlo for MVP

#### H. Monitoring Dashboard (Read-Only)
- Current positions
- Open orders
- PnL summary
- Strategy status
- NO CONTROLS (read-only for MVP)

#### I. Telegram Alerts
- Trade execution alerts
- Risk breach alerts
- System status alerts

#### J. Paper Trading Mode
- Simulated execution
- Real-time data
- Same code path as live (dry-run flag)

#### K. Operational Logging
- Trade execution logs
- System state logs
- Error logs
- Structured logging (JSON)

---

### ❌ FORBIDDEN: Out-of-MVP Features (DO NOT Build)

The following features are **EXPLICITLY OUT OF SCOPE** for MVP:

#### V1 Features (Post-MVP)
- Multi-asset support (stocks, forex)
- Multi-broker support (other exchanges)
- Limit orders, stop orders
- Partial fills
- Order modification/cancellation
- Advanced backtesting (walk-forward, Monte Carlo)
- Live chart visualization
- Custom indicator builder
- Strategy cloning
- Multi-account support
- **Live Binance Futures execution + leverage controls + liquidation/margin risk model** (gated by DEC-2026-05-28-001 step 4 — only built after validated short edge in research). Research-layer futures backtesting is already in MVP scope per § 1.A above.

#### V2 Features (Maturity Phase)
- Real-time WebSocket data
- Advanced risk (portfolio, correlation)
- Machine learning strategies
- Automated regime detection
- Alert customization
- Mobile app
- API for external systems
- Multi-user support

#### Maturity Features (Future)
- Options trading
- Algorithm trading (HFT)
- Social trading
- Copy trading
- Managed accounts
- Licensing/SaaS

---

## 2. SCOPE ENFORCEMENT RULES

### Rule 2.1: Feature Request Triage

**When a feature request is made:**

1. **Check if it's in MVP scope** (see Section 1)
   - ✅ If YES → Proceed with implementation
   - ❌ If NO → Apply Rule 2.2

2. **If unsure:**
   - Search `TRADING_SYSTEM_PRD.md` Part 2 for the feature
   - Check `docs/archive/build-plans/00_MVP_TASK_INDEX.md` for related tasks
   - Default to **NO** if not explicitly listed

---

### Rule 2.2: Rejecting Out-of-Scope Requests

**Response Template:**

```
❌ OUT OF MVP SCOPE

Feature: [feature name]
Request: [brief description]

Analysis:
- This feature is NOT in the MVP scope defined in TRADING_SYSTEM_PRD.md Part 2
- Closest MVP feature: [if applicable]
- Roadmap placement: [V1/V2/Maturity]

Recommendation:
- Add to V1/V2 backlog
- Document in [appropriate roadmap file]
- Revisit after MVP launch

Would you like to:
1. Add this to the V1 roadmap?
2. Modify the request to fit MVP scope?
3. Explicitly approve scope change (requires PRD update)?
```

---

### Rule 2.3: NO Gold-Plating

**Gold-plating is forbidden, but production quality is mandatory.**

**Gold-plating examples (FORBIDDEN):**
- Adding features not in PRD: "I added automatic regime detection" ❌
- Over-engineering: "I built a config DSL instead of using JSON" ❌
- Unnecessary abstraction: "I made it support 50 exchanges for future" ❌
- Feature creep: "I added SMS alerts since we have Telegram" ❌

**Production quality examples (REQUIRED):**
- Comprehensive error handling ✅
- Proper validation of all inputs ✅
- Logging and observability ✅
- Clean, maintainable code ✅
- Complete test coverage ✅
- Proper resource management ✅
- Graceful degradation ✅

**Key Distinction:**
- Gold-plating = Adding scope beyond PRD
- Production quality = Implementing PRD requirements excellently

---

### Rule 2.4: Locked Decisions (Do Not Revisit)

The following decisions are **LOCKED** until their review dates:

1. **Asset Class: Crypto ONLY**
   - Locked until: Q2 2026 review
   - Rationale: Focus, API simplicity
   - Do NOT suggest adding stocks/forex

2. **Broker: Binance ONLY**
   - Locked until: Q2 2026 review
   - Rationale: Best API, liquidity, testnet
   - Do NOT suggest other exchanges

2a. **Market type — LIVE execution: Binance Spot ONLY** (long-only, no leverage)
   - Locked until: step 4 of staged plan in DEC-2026-05-28-001 (validated short edge + live futures execution adapter)
   - Rationale: zero liquidation risk while the system is finding its first reliable strategy
   - Do NOT route live orders through Binance Futures or Margin until the staged unlock completes

2b. **Market type — RESEARCH/BACKTEST layer: long-short futures evaluation PERMITTED**
   - Amendment date: 2026-05-28 (DEC-2026-05-28-001)
   - Rationale: PARA-01 — backtest was crediting short P&L spot live could not execute. Honest evaluation requires the option to model futures + funding cost.
   - Implementation: `BacktestConfig.allow_shorts` + `funding_rate_per_8h`
   - This MUST NOT cross into live execution without explicit completion of the staged plan

3. **Database: SQLite**
   - Locked until: V1
   - Rationale: Simplicity, zero-ops
   - Do NOT suggest Postgres/MySQL

4. **Orders: Market ONLY**
   - Locked until: V1
   - Rationale: Simplicity, guaranteed fills
   - Do NOT suggest limit orders

5. **Architecture: Monolithic**
   - Locked until: V2
   - Rationale: Simplicity, single deployment
   - Do NOT suggest microservices

---

## 3. SCOPE CHANGE APPROVAL PROCESS

**If a scope change is absolutely necessary:**

### Step 3.1: Document Justification

Create a document with:
- Feature name
- Problem it solves
- Why MVP can't launch without it
- Alternatives considered
- Effort estimate
- Dependencies
- Risks

### Step 3.2: User Approval Required

- User must **explicitly approve**
- Approval must be in writing (chat/email)
- Document as **SCOPE CHANGE REQUEST**

### Step 3.3: Update Documentation

- Update `TRADING_SYSTEM_PRD.md` Part 2 (MVP Scope)
- Update `docs/archive/build-plans/00_MVP_TASK_INDEX.md` (Task List)
- Update relevant Phase files
- Update timeline/effort estimates

### Step 3.4: Communicate Impact

- Notify all stakeholders
- Update roadmap
- Adjust timelines
- Re-estimate effort

---

## 4. SIMPLICITY ENFORCEMENT

### Rule 4.1: Prefer Simplest Implementation

**When multiple implementation approaches exist:**

1. Choose the **simplest** approach that meets MVP requirements
2. Avoid premature optimization
3. Avoid unnecessary abstraction
4. Use boring, proven technology

**Example:**
- ✅ Use `requests` library for HTTP
- ❌ Build custom HTTP client

### Rule 4.2: No Premature Generalization

**Do NOT build for "future-proofing":**

- ❌ "This will be useful when we add stocks"
- ❌ "Let's make this support 100 exchanges"
- ❌ "I'll add this hook for future ML integration"

**Build for TODAY's requirements:**
- ✅ Solve the problem defined in the PRD
- ✅ Make it easy to extend later (via good design)
- ✅ But don't implement extensions now

---

## 5. FEATURE COMPLETENESS VS. FEATURE CREEP

### Rule 5.1: Complete Features Properly

**Each MVP feature must be:**
- ✅ Fully implemented (no half-baked features)
- ✅ Production-grade quality
- ✅ Fully tested
- ✅ Documented
- ✅ Meets acceptance criteria

**But:**
- ❌ Don't add features beyond spec
- ❌ Don't add "nice-to-haves"
- ❌ Don't implement V1 features "while we're here"

---

## 6. INTEGRATION BOUNDARIES

### Rule 6.1: Only Integrate MVP Components

**Allowed integrations:**
- Binance API (crypto data/execution)
- Telegram Bot API (alerts)
- SQLite (data persistence)

**Forbidden integrations (for MVP):**
- Other exchanges
- Other messaging platforms (Discord, Slack)
- Cloud services (AWS, GCP)
- Analytics platforms (Mixpanel, Amplitude)
- Payment processors

---

## 7. UI/UX SCOPE

### Rule 7.1: MVP UI is Read-Only Dashboard

**Allowed UI features:**
- View positions
- View orders
- View PnL
- View strategy status
- View system health

**Forbidden UI features (for MVP):**
- Strategy configuration UI
- Manual trading controls
- Risk limit adjustments
- Live chart visualization
- Custom dashboards

**Rationale:** Configuration is done via **config files** or **admin scripts** in MVP.

---

## 8. TESTING SCOPE

### Rule 8.1: Test What You Build

**Required tests for MVP:**
- Unit tests for all business logic
- Integration tests for critical paths
- Basic end-to-end tests

**Forbidden tests (for MVP):**
- Performance benchmarks (beyond basic checks)
- Load testing
- Chaos engineering
- UI automation (no UI controls in MVP)

---

## 9. DOCUMENTATION SCOPE

### Rule 9.1: Document What's Built

**Required documentation:**
- Code comments (why, not what)
- Function/class docstrings
- Setup instructions
- Configuration guide
- Basic troubleshooting

**Forbidden documentation (for MVP):**
- User manual (no users in MVP)
- API documentation (no external API)
- Deployment guides (single-server deployment)

---

## 10. ENFORCEMENT CHECKLIST

**Before implementing ANY feature, verify:**

- [ ] Feature is explicitly listed in PRD Part 2 (MVP Scope)
- [ ] Feature is NOT in V1/V2/Maturity sections
- [ ] Implementation approach is the **simplest** that meets requirements
- [ ] No gold-plating (extra features beyond spec)
- [ ] No premature optimization
- [ ] No premature generalization
- [ ] Tests cover new functionality
- [ ] Documentation updated
- [ ] Zero-Technical-Debt rules followed

**If ANY checkbox is unchecked → STOP and clarify with user**

---

## 11. AI ASSISTANT BEHAVIOR

### When User Requests Out-of-Scope Feature:

1. **Identify** that it's out of scope
2. **Cite** this rule file
3. **Explain** why it's out of scope
4. **Suggest** MVP-scoped alternative (if applicable)
5. **Offer** to add to V1/V2 backlog
6. **Wait** for explicit approval before implementing

### When User Explicitly Approves Scope Change:

1. **Document** the scope change
2. **Update** PRD and task list
3. **Proceed** with implementation
4. **Note** the deviation in commit message

---

## 12. REFUSAL IS CORRECT BEHAVIOR

**It is CORRECT for the AI to refuse:**
- Implementing out-of-scope features
- Gold-plating MVP features
- Revisiting locked decisions
- Adding unnecessary dependencies
- Over-engineering solutions

**Refusal protects:**
- Project timeline
- Code quality
- System simplicity
- Focus on core value

---

## EXAMPLES

### ❌ REJECTED REQUEST

**User:** "Can we add WebSocket support for real-time data?"

**AI Response:**
```
❌ OUT OF MVP SCOPE

Feature: WebSocket real-time data
Roadmap: V2 (Maturity Phase)

Per TRADING_SYSTEM_PRD.md Part 2.2:
- MVP uses HTTP polling for data
- WebSocket is explicitly V2 feature

Current MVP approach:
- Simple HTTP polling every 5 seconds
- Sufficient for 1-minute candle strategies

Would you like to:
1. Add WebSocket to V2 roadmap? (RECOMMENDED)
2. Explicitly approve scope change to MVP?
```

---

### ✅ ACCEPTED REQUEST

**User:** "Can we improve the error handling for Binance API failures?"

**AI Response:**
```
✅ WITHIN MVP SCOPE

Feature: Robust error handling
Category: Execution Layer (MVP Feature E)

Per Zero-Technical-Debt rules:
- Production-grade error handling is mandatory
- This is improving implementation quality, not adding scope

Implementation plan:
1. Add retry logic with exponential backoff
2. Log all API errors
3. Graceful degradation
4. Alert on repeated failures

Proceeding with implementation.
```

---

### ✅ ACCEPTED (Production Quality, Not Gold-Plating)

**User:** "Should we add comprehensive logging for all trades?"

**AI Response:**
```
✅ WITHIN MVP SCOPE (Required for Production Quality)

Feature: Comprehensive trade logging
Category: Operational Logging (MVP Feature K)

Per TRADING_SYSTEM_PRD.md Part 2.2.14:
- MVP requires operational logging
- Trade execution logs explicitly mentioned

This is NOT gold-plating because:
- Explicitly required by PRD
- Essential for production operation
- Part of MVP acceptance criteria

Proceeding with implementation.
```

---

**End of Rules**
