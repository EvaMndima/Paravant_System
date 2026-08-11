# PARAVANT — Production Readiness Assessment & Publication Plan

**Assessed:** 2026-08-08
**Assessed against:** `master` @ `622ac49`
**Purpose:** Establish the verified state of the system and define the work required
before this repository is published publicly as a portfolio artifact.

All numbers in this document were measured, not estimated. The commands used are
listed in Appendix A so the assessment is reproducible.

---

## 1. Verified Inventory

### 1.1 Scale

| Layer | Tracked files | Lines |
|---|---|---|
| `src/` — application | 170 `.py` | 49,294 |
| `research/` — research library | 27 `.py` | 5,411 |
| `scripts/` — operational entrypoints | 24 | 11,865 |
| `tests/` | 134 `.py` | 36,221 |
| `frontend/src/` | 100 `.ts`/`.tsx` | 17,230 |
| `docs/` | 50 `.md` | — |
| **Total tracked** | **769 files** | **~120,000** |

Git history: 102 commits, 2026-02-08 through 2026-06-11, single author.

### 1.2 Backend application (`src/`)

**API layer** — FastAPI, 14 route modules, 63 endpoints (21 state-mutating).
`accounts`, `backtest`, `dashboard`, `events`, `execution`, `orders`,
`paper_trading`, `pnl`, `positions`, `regime`, `risk`, `strategies`, `system`.
Middleware: structured request logging, global error handler. Explicit CORS
allowlist (no wildcard).

**Data layer** — SQLAlchemy 2.0 with `Mapped[T]` typing throughout.
15 ORM models: `account`, `order`, `position`, `trade`, `pnl`, `signal`,
`strategy`, `strategy_assignment`, `symbol`, `system`, `paper_session`,
`fill_rate_record`, `slippage_record`, plus base/mixins.
`DataStore` (1,332 lines) is the repository facade. Alembic with 6 migrations.
Supporting modules: `market_data`, `service`, `validators`, `cache`, `symbol_manager`.

**Indicators** — 19 implementations, each independently unit-tested:
ADX, ATR, Bollinger, Donchian, EMA, Ichimoku, Keltner, MACD, RSI, SMA,
Stochastic RSI, Supertrend, VWAP, volume, plus resample/factory/cached wrappers.

**Risk layer** — 11 modules: `controller`, `checks`, `sizing`, `circuit_breakers`,
`kill_switch`, `dead_mans_switch`, `event_filter`, `time_filter`, `volatility`, `types`.
This is the most complete and best-tested subsystem in the codebase
(`sizing` 100%, `checks` 99%, `time_filter` 100%, `kill_switch` 94%).

**Execution layer** — `order_manager` (843 lines, state machine),
`position_tracker` (950 lines), `quality` (948 lines — slippage and fill-rate
measurement), `interface` (broker abstraction).

**Broker adapter** — Binance client (877 lines), execution adapter (509 lines),
token-bucket rate limiter (343 lines).

**Strategy layer** — 29 signal generators, a strategy engine, a template system,
a similarity checker (duplicate-strategy detection), a backtest package
(engine / trader / portfolio / metrics / validator / types), a paper-trading
package (engine / manager), and a regime package (detector / historical
classifier / SubRegime-aware router).

**Orchestration** — `orchestrator.py` (1,800 lines): 8-step startup validation,
async main loop, kill-switch-first ordering, graceful degradation, emergency
shutdown, health monitoring, injectable clock for testing.

**Cross-cutting** — event bus, exception hierarchy (868 lines), health checks,
structured logging (structlog), config loader with YAML + env layering,
config backup, alerting (Telegram channel, triggers, scheduler, escalation).

### 1.3 Research layer (`research/` + `scripts/`)

This is the most intellectually distinctive part of the repository.

- `validation/deflated_sharpe.py` (446) — Deflated Sharpe Ratio, correcting
  Sharpe for the number of trials actually run.
- `validation/effective_k.py` (241) — effective-trial counting, including a
  regime-bucket multiplier.
- `backtest/cost_model.py` (356) — explicit, versioned cost model
  (`v0_unverified`) applied as a conservative pad.
- `backtest/regime_tagging.py` (308) — per-bar regime attribution.
- `promotion/classifier.py` (216) — tier assignment (A/B/C/D) and promotion gating.
- `biographies/schema.py` (443) — per-strategy structured history with an
  append-only decision log.
- `data/` — funding rates, ETF flows, Coinbase premium, liquidations (with a
  forward collector), BTC reference series, cross-sectional ranking.
- `generators/` — 8 crypto-native hypothesis generators driven by derivatives
  and flow data rather than price alone.

Operational tooling: `retrospective_dsr.py` (1,207), `regime_dsr.py` (1,050),
`validation_report.py` (710), `backtest_rolling.py` (699),
`sweep_tp_wfo.py` (797 — walk-forward optimisation),
`generate_post_mortem.py` (581).

Governance: `docs/research/RESEARCH_PROTOCOL.md` defines a pre-registered
funnel (HYPOTHESIS → TRAIN → HOLDOUT → SIMULATED PAPER → LIVE PAPER →
MICRO-LIVE → LIVE) with gates fixed before results are seen, plus a
`HYPOTHESIS_QUALITY_GATE.md` scorecard and a `NEGATIVE_SPACE_MAP.md`
recording where edge has been proven absent.

### 1.4 Live/paper operations (`scripts/`)

`run_live_trading.py` (2,111 lines) implements the capital and safety model:

- Per-strategy capital slicing (`LIVE_CAPITAL x PER_STRATEGY_ALLOCATION_PCT`).
- Concurrency cap (`MAX_STRATEGIES_LIVE_CONCURRENT`).
- Capital reserve fraction (projected commitment must stay under 85%).
- Minimum-notional startup guard that **fails closed** (`sys.exit(1)`) rather
  than silently placing sub-minimum orders.
- Demotion guardrail (PF < 0.8 at N >= 10 deactivates a tier).
- Auto-promotion gate: a tier may only activate when its pooled paper record is
  `READY_FOR_LIVE` (N >= 30, PF >= 1.35, Sharpe >= 1.0, MaxDD <= 5%).
  Fails **open** on DB error, **closed** on a clear non-READY verdict.
- Kill switch (`LIVE_TRADING_ENABLED`) defaults OFF.

`run_paper_trading.py` (947 lines) runs the same code path in simulation.
Deployment is Railway (Dockerfile, `railway.toml`, Procfile with `web` + `paper`
processes), plus documented cron jobs in `docs/operations/RAILWAY_CRONS.md`.

### 1.5 Frontend (`frontend/`)

React 19 + Vite 7 + TypeScript 5.9 + Tailwind v3 + framer-motion + Recharts.
13 pages, ~40 components, 4 palette themes with light/dark, keyboard shortcuts,
error boundary, toast system, path aliases, `verbatimModuleSyntax` enforced.
`npm run build` succeeds cleanly in ~41s.

### 1.6 Governance artifacts

- `.claude/DECISIONS.md` and `.agent/DECISIONS.md` — 113 dated architectural
  decisions, 2,998 lines, verified byte-identical.
- `.claude/rules/` — decision-consistency, zero-technical-debt, MVP scope control.
- `docs/` — PRD, architecture, API contract, indicator spec, phase plans,
  research protocol, operations runbooks.

---

## 2. Verified State

### 2.1 Test suite

```
1,900 tests collected
1,855 passed | 9 failed | 4 skipped | 32 errors | 132s
```

The 32 errors are all in `tests/integration/test_binance_client.py` and
`tests/integration/test_symbol_refresh.py` — they require live Binance testnet
connectivity and are not marked to skip when it is unavailable.

The 9 failures are genuine and fall into three groups:

1. **Environment leakage (1)** — `test_settings_defaults` asserts
   `binance_testnet is True` but reads the developer's real `.env`, which
   contains `BINANCE_TESTNET=false`. Tests are not hermetic, and the leaking
   value is the one that selects real-money mode.
2. **Stale assertions (5)** — e.g. `TestRsiBbMeanReversion::test_properties`
   expects `min_bars_required == 50`; the implementation now returns 210.
   The tests were not updated when the generators changed.
3. **Test-environment defects (3)** — `test_collector_flush_writes_and_clears`
   writes a fragment and then reads zero events back.

### 2.2 Coverage

63% overall across `src/` + `research/` (unit + research suites; 15,784
statements, 5,828 uncovered).

Strong: risk sizing 100%, risk checks 99%, indicators 88-100%,
data models 88-100%, health 94%, config 96-97%.

Weak: `data/store.py` 28% (the 1,332-line data facade),
`strategy/engine.py` 60%, `orchestrator.py` 71%, `risk/controller.py` 74%.
`scripts/` — including the 2,111-line live trading loop — is not measured at all
outside its three dedicated unit test files.

### 2.3 Static analysis

```
ruff check src/ research/ scripts/   ->  76 errors (50 auto-fixable)
mypy src/                            ->  50 errors in 16 files
```

`pyproject.toml` declares `disallow_untyped_defs = true`. It is not enforced
anywhere, so the gate exists on paper only.

### 2.4 Confirmed defect

`src/core/orchestrator.py:464` calls:

```python
self._strategy_engine.create_strategy(
    name=..., template=..., symbol=..., account_id=..., params=..., status=...
)
```

The actual signature (`src/core/strategy/engine.py:91`) is:

```python
def create_strategy(self, name, template_id, params=None, symbols=None, description="")
```

Four keyword arguments are wrong. This raises `TypeError` at runtime, but the
call sits inside `except Exception`, so the startup validation step reports
"strategies check failed" rather than surfacing the type error. **The
orchestrator's strategy-validation startup check cannot pass in any environment
that has active strategies.** It was not caught because the orchestrator tests
mock the strategy engine rather than exercising the real signature.

### 2.5 Security posture

No authentication exists on the API. All 63 endpoints are open, including
21 mutating endpoints: place order, cancel order, close position, activate and
deactivate the kill switch, start and stop paper trading sessions, mutate
strategy parameters, and change system configuration.

CORS is correctly restricted, secrets are correctly kept out of git (`.env` has
never been committed; a scan of all tracked non-doc files found no hardcoded
credentials), and the Dockerfile runs as a non-root user. The gap is
authentication specifically, and it is total.

### 2.6 Repository hygiene

- No `.github/` directory — no CI, no automated checks on any commit.
- No `LICENSE` file, although `README.md` and `pyproject.toml` both claim MIT.
- 35 `SESSION_*` / `PHASE_*` markdown files at repository root (some over
  70 KB) which are AI implementation prompts, not project documentation.
- 17 loose `.py` files at root (`run_*.py`, `test_*.py`, `create_*.py`,
  `backtest_optimization_guide.py`) which are one-off scratch scripts.
- `README.md` is 4 KB, opens with a feature checklist of green ticks, and
  describes an MVP scope that the system outgrew months ago. It does not
  mention the research layer, the DSR validation work, or the live capital model.

### 2.7 Frontend integration status

The frontend contains 17,230 lines and makes **three** network calls in total:

- `GET /api/v1/regime/current`
- `GET /api/v1/regime/paper-sessions`
- `GET /api/v1/strategies/{id}/backtest/results`

Every other page renders hardcoded arrays. `PortfolioPage` ships a fixed
7-position portfolio and generates its equity curve with
`Math.sin(i * 0.25) + Math.random()`. `CockpitPage`, `AlertsPage`,
`TradeHistoryPage`, `RiskPage`, and `SystemPage` are similarly static.
There are no frontend tests of any kind.

So: 63 working backend endpoints, and a UI wired to 3 of them.

### 2.8 Research findings to date

`docs/research/retrospective/PORTFOLIO_SUMMARY_2026-06-05.md` records that all
11 strategies analysed — including the 5 previously classified KEEP — land at
`TIER_D_REJECT` under the Deflated Sharpe Ratio. Zero strategies survive the
conservative DSR floor.

Two subsequent forward hypotheses were also rejected:
- H-2026-06-002 (price breakout-continuation): trending_bull PF 0.59, N=341, DSR p=1.0.
- H-2026-06-003 (funding-confirmed trend): trending_bull PF 0.53, N=132, DSR p=1.0.

`NEGATIVE_SPACE_MAP.md` now records TRENDING_BULL continuation as a hard gap
across two distinct mechanism classes.

**Interpretation:** the system has no validated trading edge. It also has a
validation layer rigorous enough to prove that, and it was applied honestly to
the author's own work. Those two statements are both true and the second is the
more valuable one.

---

## 3. Assessment

### 3.1 What is genuinely production-grade

- The risk subsystem: layered checks, circuit breakers, kill switch, dead man's
  switch, near-total test coverage.
- The live capital model: fails closed on the min-notional guard, enforces a
  reserve, caps concurrency, and gates promotion on measured paper performance.
- The research validation layer: DSR, effective-K, pre-registered gates,
  cost modelling, negative-space tracking. This is stronger than what most
  retail quant projects attempt, and it is the differentiator.
- The decision log: 113 dated decisions with rationale and alternatives.
- The indicator library and data models: well typed, well tested, well factored.

### 3.2 What blocks a "production ready" verdict

Ordered by how quickly a senior reviewer will find it:

| # | Finding | Severity |
|---|---|---|
| 1 | No API authentication on 21 mutating endpoints incl. order placement and kill switch | Critical |
| 2 | No CI — nothing verifies any commit | Critical |
| 3 | 9 failing tests on `master` | High |
| 4 | Orchestrator startup check calls a function with 4 wrong kwargs; error swallowed | High |
| 5 | Tests read the developer's real `.env`; the leaked value selects live mode | High |
| 6 | 50 mypy + 76 ruff errors against a config that claims strict typing | Medium |
| 7 | Frontend is a static prototype presented as a dashboard | Medium |
| 8 | No LICENSE despite two MIT claims | Medium |
| 9 | 35 AI prompt files + 17 scratch scripts at repo root | Medium (presentation) |
| 10 | README describes a system two quarters out of date | Medium (presentation) |
| 11 | `data/store.py` at 28% coverage | Low |
| 12 | Integration tests error rather than skip without network | Low |

### 3.3 Positioning note

The stated goal is applying to AI engineering roles. This repository contains no
machine learning, no LLM integration, and no model serving. It is a strong
**backend / data / systems engineering** portfolio piece with unusually rigorous
**quantitative research methodology**.

That is not a reason to change the project. It is a reason to be deliberate:
either present it accurately as distributed systems and research-engineering
work (which it is, and which is relevant to AI infrastructure roles), or add a
genuine ML component as a distinct, honestly-scoped module. Dressing the
existing heuristics up as "AI" would be the single fastest way to lose a
technical reviewer's trust.

---

## 4. Plan

Five phases. Phases 0-2 are required before any public push. Phase 3 is what
converts the repo from "impressive backend" to "complete product". Phase 4 is
what makes the production-ready claim defensible. Phase 5 is optional
positioning work.

### Phase 0 — Safety gate (do first, before any push)

**Goal:** nothing embarrassing or dangerous becomes public.

- [ ] 0.1 Scan full git history for secrets, not just the working tree
      (`gitleaks detect --log-opts="--all"` or `trufflehog git file://.`).
      `.env` was never committed, but verify keys were never pasted into a
      markdown file or a notebook.
- [ ] 0.2 Rotate the Binance API keys and the Telegram bot token regardless of
      scan result. They exist in a local `.env` on a machine that has run
      `BINANCE_TESTNET=false`.
- [ ] 0.3 Confirm the live kill switch (`LIVE_TRADING_ENABLED`) is OFF on
      Railway and that no public documentation reveals the deployment URL.
- [ ] 0.4 Decide the license. Add a real `LICENSE` file matching the claim.
- [ ] 0.5 Add `SECURITY.md` with a "this software trades real money; use at your
      own risk; no warranty" statement and a disclosure contact.

**Exit:** history is clean, credentials are rotated, license is real.

### Phase 1 — Repository presentation (2-3 days)

**Goal:** the first 60 seconds of a reviewer's visit are accurate and impressive.

- [ ] 1.1 Move the 35 `SESSION_*` / `PHASE_*` files out of root. Either delete
      them or archive to `docs/archive/build-log/`. They read as AI scaffolding
      and they are the first thing visible in the file listing.
- [ ] 1.2 Move the 17 loose root `.py` scripts into `scripts/legacy/` or delete.
      Anything named `test_*.py` at root that is not a real test must go — it
      makes the test suite look untrustworthy.
- [ ] 1.3 Rewrite `README.md` around what the system actually is. Structure:
      - One-paragraph statement: an autonomous crypto trading system built to
        find out whether a retail-scale strategy edge exists, with a validation
        layer designed to reject its own results.
      - Architecture diagram (a Mermaid diagram renders natively on GitHub).
      - The honest headline result: 11 strategies built, all 11 rejected by
        Deflated Sharpe; two forward hypotheses rejected at N=341 and N=132.
        State this as the finding, not as a failure — it demonstrates that the
        validation layer works and was applied against the author's own bias.
      - Quickstart that a stranger can actually run in under five minutes.
      - Test/coverage/lint badges (real ones from CI, after Phase 2).
      - Explicit "what this is not" section.
- [ ] 1.4 Write `docs/ARCHITECTURE.md` as a genuine system document: the data
      flow from Binance to signal to risk check to order to position, the state
      ownership boundaries, the async boundaries, and the failure modes. One
      diagram per layer.
- [ ] 1.5 Write `docs/RESEARCH_FINDINGS.md` — the story of the DSR result. This
      is the single most differentiating document you can publish. Include the
      coverage matrices and the negative-space map.
- [ ] 1.6 Prune `docs/`. 50 tracked markdown files with overlapping phase plans
      is noise. Keep: README, ARCHITECTURE, RESEARCH_FINDINGS, RESEARCH_PROTOCOL,
      API_CONTRACT, ENVIRONMENT_SETUP, operations runbooks, DECISIONS. Archive
      the rest under `docs/archive/`.
- [ ] 1.7 Remove `docs/design/references/node_modules/` from disk (it is
      gitignored, but it makes local clones and greps painful).

**Exit:** a stranger landing on the repo understands what it is, what it found,
and how to run it, without opening a second file.

### Phase 2 — Correctness and enforced quality gates (1 week)

**Goal:** every claim in the README is machine-verified on every commit.

- [ ] 2.1 Fix the orchestrator defect at `orchestrator.py:464`. Correct the
      kwargs to the real signature. Then add an integration test that runs
      startup validation against a **real** `StrategyEngine`, not a mock —
      the mock is why this survived.
- [ ] 2.2 Narrow the `except Exception` in the startup validation loop, or
      re-raise `TypeError`/`AttributeError`. Swallowing programming errors as
      "check failed" is the root cause here, and it will hide the next one too.
- [ ] 2.3 Make tests hermetic. Add a `conftest.py` fixture that clears
      `BINANCE_*`, `TELEGRAM_*`, `DATABASE_URL`, `ENVIRONMENT`, and
      `LIVE_TRADING_ENABLED` from `os.environ` and prevents `.env` loading
      during tests. This is a safety fix, not just a hygiene fix.
- [ ] 2.4 Fix the 5 stale generator assertions and the 3 liquidation-collector
      test defects. Where the implementation changed deliberately, update the
      test and note why in the commit.
- [ ] 2.5 Mark network-dependent integration tests with
      `@pytest.mark.binance` and `skipif` on a missing API key, so a clean clone
      produces 0 errors instead of 32.
- [ ] 2.6 `ruff check --fix`, then resolve the ~26 remaining by hand.
- [ ] 2.7 Resolve the 50 mypy errors. The `dict[str, float]` vs
      `dict[str, object]` cluster in the generators is one root cause — widen
      `TradingSignal.indicators` to `dict[str, float | str]` or serialise at the
      boundary; fix once, not 15 times.
- [ ] 2.8 Add `.github/workflows/ci.yml`: matrix on Python 3.11/3.12, running
      `ruff check`, `mypy src/`, `pytest --cov`, and `cd frontend && npm ci &&
      npm run build && npm run lint`. Fail the build on any of them.
- [ ] 2.9 Add coverage reporting to CI and a real badge. Set a floor
      (start at the current 63%, ratchet up) and fail below it.
- [ ] 2.10 Raise `data/store.py` from 28%. It is the widest-blast-radius module
      in the codebase and the least tested. Target 80%.
- [ ] 2.11 Add `.pre-commit-config.yaml` wiring ruff, black, and mypy.
      `pre-commit` is already declared in `requirements-dev.txt` but unused.

**Exit:** green CI badge, 0 failing tests, 0 mypy errors, 0 ruff errors,
coverage floor enforced.

### Phase 3 — Close the vertical slice (1-2 weeks)

**Goal:** the dashboard shows real system state. This is the largest gap between
what the repo looks like and what it is.

- [ ] 3.1 Add API authentication. For a single-operator system, a static API key
      in an `X-API-Key` header validated by a FastAPI dependency is sufficient
      and honest — document the choice and its limits in `ARCHITECTURE.md`.
      Apply it to all mutating routes at minimum. Do not ship JWT/OAuth theatre
      for a single-user system; a reviewer respects a justified simple choice
      more than an over-engineered one.
- [ ] 3.2 Add rate limiting on mutating endpoints (`slowapi` or a small custom
      dependency reusing the existing token-bucket in the Binance adapter).
- [ ] 3.3 Generate a typed API client for the frontend from the OpenAPI schema
      (`openapi-typescript`). This kills an entire class of drift between the
      63 endpoints and the UI types.
- [ ] 3.4 Replace hardcoded page data with real queries, in priority order:
      1. `CockpitPage` — positions, PnL, activity, system status
      2. `PortfolioPage` — real equity curve from `equity_snapshots`
      3. `TradeHistoryPage` — real trades with pagination
      4. `RiskPage` — real limits and current utilisation
      5. `SystemPage` — real health from `/health/detailed`
      6. `AlertsPage` — real alert history
      Use TanStack Query (already a dependency, currently unused for this).
- [ ] 3.5 Add loading, empty, and error states to every data-backed view. An
      empty-state design is itself evidence of production thinking.
- [ ] 3.6 Delete or clearly quarantine `DevPage`, `Dev2Page`, `Dev3Page`
      (2,097 lines of component gallery). If kept, move to a `/dev` route that
      is excluded from the production build and say so in the README.
- [ ] 3.7 Add frontend tests: Vitest + React Testing Library. Cover the data
      hooks, the currency/percent formatters, and two critical components
      (`PositionsTable`, `EmergencyPanel`). Wire into CI.
- [ ] 3.8 Publish a live read-only demo (Railway or Vercel) seeded with the real
      paper-trading history. A reviewer clicking a working link is worth more
      than any README paragraph.

**Exit:** every page in the UI reflects real database state; the demo link works.

### Phase 4 — Operational proof (1 week)

**Goal:** make "production ready" a demonstrable claim rather than an adjective.

- [ ] 4.1 Add `docker-compose.yml` that brings up API + Postgres + frontend with
      one command, seeded with demo data. This is the single highest-leverage
      thing for a reviewer who wants to try it.
- [ ] 4.2 Add a seed script producing a realistic demo dataset so a fresh clone
      is not an empty dashboard.
- [ ] 4.3 Add `/metrics` (Prometheus format) exposing the metrics the
      orchestrator already tracks: cycles, orders submitted/filled/rejected,
      errors, cycle duration. The counters exist; they are just not exported.
- [ ] 4.4 Write `docs/operations/RUNBOOK.md`: how to start, stop, kill, recover,
      what each alert means, what to do when the dead man's switch fires.
      A `kill_switch_runbook.md` already exists — extend the pattern.
- [ ] 4.5 Document the failure modes explicitly: exchange outage, network
      partition mid-order, DB unavailable, stale market data, clock skew.
      For each: current behaviour and whether it is tested.
- [ ] 4.6 Add a load/soak result: run the paper loop for 72 hours, publish
      cycle-latency percentiles and memory profile. Evidence beats assertion.
- [ ] 4.7 Add architecture decision records to the public docs — surface the
      113-entry decision log as a genuine engineering artifact, with 5-10
      highlighted decisions written up as narratives.

**Exit:** `docker compose up` produces a working system with data in under
two minutes, and the operational docs answer "what happens when it breaks".

### Phase 5 — Optional: AI/ML positioning

Only if you want this to read as an AI engineering piece rather than a
systems/quant piece. Each of these is a real, honest addition:

- [ ] 5.1 An ML regime classifier trained on the labelled regime data the
      `historical_classifier` already produces, benchmarked against the existing
      rule-based detector — including the case where the rules win.
- [ ] 5.2 An LLM-based research assistant that drafts hypothesis scorecards
      against `HYPOTHESIS_QUALITY_GATE.md`, with the human gate preserved.
      This mirrors how the project was actually built and is defensible.
- [ ] 5.3 Feature-store framing for the research data layer (funding, flows,
      premium, liquidations), with point-in-time correctness guarantees — this
      is genuine ML infrastructure work and the data is already there.

Whatever is added must pass the same DSR discipline as everything else. An ML
model that fails validation and is reported as failing is a stronger portfolio
signal than one that "works" without scrutiny.

---

## 5. Sequencing and effort

| Phase | Effort | Blocking for publication? |
|---|---|---|
| 0 — Safety gate | 0.5 day | Yes |
| 1 — Presentation | 2-3 days | Yes |
| 2 — Quality gates | 5-7 days | Yes |
| 3 — Vertical slice | 8-12 days | No, but the repo is visibly incomplete without it |
| 4 — Operational proof | 4-6 days | No, but required for a "production ready" claim |
| 5 — AI positioning | 5-10 days | Optional |

Minimum viable public repo: Phases 0-2, roughly two weeks.
Defensible "production ready": Phases 0-4, roughly five to six weeks.

**Recommended order deviation:** do 1.3 (README rewrite) *last* within Phase 1,
after Phase 2 gives you real badges and real numbers to put in it. Write it once,
with true figures.

---

## Appendix A — Reproducing this assessment

```bash
# Scale
git ls-files | wc -l
git ls-files "src/**.py" | xargs wc -l | tail -1

# Tests
.venv/Scripts/python.exe -m pytest tests/ -q --tb=no

# Coverage
.venv/Scripts/python.exe -m pytest tests/unit tests/research -q \
  --cov=src --cov=research --cov-report=term

# Static analysis
.venv/Scripts/python.exe -m ruff check src/ research/ scripts/
.venv/Scripts/python.exe -m mypy src/

# Auth surface
grep -rn "@router\.\(post\|put\|delete\|patch\)" src/api/routes/ | wc -l
grep -rn "Depends\|APIKey\|HTTPBearer" src/api/main.py

# Frontend API wiring
grep -rn "fetch(\|axios" frontend/src --include=*.ts --include=*.tsx | wc -l

# Hygiene
ls .github 2>/dev/null; ls LICENSE* 2>/dev/null
git ls-files "*.md" | grep -v "/" | grep -cE "SESSION_|PHASE_"
```
