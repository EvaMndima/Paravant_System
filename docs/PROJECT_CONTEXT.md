# PARAVANT — Complete Project Context

**Version:** 1.0
**Compiled:** 2026-08-08
**Repository state:** `master` @ `622ac49`
**Companion document:** `docs/PRODUCTION_READINESS_ASSESSMENT.md` (gaps, defects, and the
publication plan). This document covers *what exists and why*; that one covers
*what is wrong and what to do about it*.

---

## 0. How to use this document

This is a self-contained briefing. A reader with no access to the repository should
finish it able to reason about the system's design, its history, its current state,
and its open questions. Nothing here requires opening a source file, though file
paths are given throughout as anchors.

Every factual claim was verified against the codebase on 2026-08-08. Where a claim
is a design intention rather than a verified behaviour, it is marked as such.

---

## 1. What PARAVANT is

PARAVANT is a personal autonomous cryptocurrency trading system. It ingests market
data from Binance, evaluates it against a library of signal generators, filters the
resulting signals through a layered risk system, sizes positions, places orders, and
tracks the outcome — in backtest, in paper simulation, and (behind a default-off kill
switch) with real capital.

Its distinguishing feature is not the trading engine. It is the **research and
validation layer** built around the trading engine, whose explicit purpose is to
reject the system's own strategies. The project treats "we found a profitable
strategy" as a claim requiring statistical proof, and it implements the machinery to
test that claim honestly: Deflated Sharpe Ratio, effective-trial counting,
pre-registered gates, regime-conditional attribution, and a written protocol that
forbids moving a gate to make a strategy pass.

### 1.1 The founding question

The project exists to answer one question: **does a retail-scale, systematically
discoverable trading edge exist in crypto, and can it be proven rather than
assumed?**

The answer to date is no. See Section 14.

### 1.2 Design philosophy

Three commitments shape almost every decision in the codebase:

1. **Fail closed.** Ambiguity resolves toward not trading. The kill switch defaults
   off. Unknown market regime means no strategy activates. A position size below the
   exchange minimum exits the process rather than rounding up.
2. **Capital preservation over return.** The risk layer is the most complete and
   best-tested subsystem. Every order passes seven independent pre-trade checks and
   five circuit breakers.
3. **Decisions are written down.** 113 dated architectural decisions with rationale,
   alternatives considered, and status. Code is required to match them.

### 1.3 Locked scope

The MVP scope is deliberately narrow and enforced by a rules file:

- Crypto only (no equities, no FX)
- Binance only (no other exchanges)
- Binance **Spot** for live execution — long-only, no leverage, no liquidation risk
- Market orders only (no limit, stop, or conditional orders)
- Monolithic architecture (no microservices)
- SQLite in development, PostgreSQL in production

One amendment (2026-05-28, DEC-2026-05-28-001): the **research/backtest layer** may
model long-short futures with funding costs, because honest evaluation requires the
option. This must not cross into live execution without a staged unlock. Section 14
records that this amendment ultimately produced the finding that spot long-only
*outperforms* futures for the strategies in question, so live futures was never built.

---

## 2. Timeline

| Period | Work |
|---|---|
| 2026-02-08 | First commit. Project scaffold, database models, config, logging |
| 2026-02-10 | Phase 1 complete — foundation |
| 2026-02-12 | Phase 2 complete — data layer, Binance client, indicators |
| 2026-02-14 | Phase 3 complete — risk controls, kill switch, circuit breakers |
| 2026-02-16 | Phase 4 complete — order manager, position tracker, Binance adapter |
| 2026-02-18 | Phase 5 complete — strategy templates, backtest, paper trading |
| 2026-02-22 | Phase 6 complete — dashboard API, alerting, orchestrator |
| 2026-03-07 | Frontend rebuilt from scratch on Tailwind v3 after a v4 dark-mode failure |
| 2026-03 to 2026-05 | Strategy generation and backtesting at volume — 120+ runs |
| 2026-05-27/28 | Portfolio triage. 6 strategies retired. SubRegime routing built |
| 2026-05-31 | Research-layer bug fixes (PARA-02/08/09), portfolio capital model |
| 2026-06-01 | Auto-promotion gate; tier-1 gate; distance-to-promotion reporting |
| 2026-06-04 | Research Layer PRD ratified. 21 decisions filed in one day |
| 2026-06-05 | Retrospective DSR run. **All 11 strategies rejected** |
| 2026-06-08 to 06-11 | Forward hypothesis loop. Two more hypotheses rejected |

102 commits total, single author. Roughly four months of sustained work.

---

## 3. Repository map

```
Paravant_System/
├── src/                      170 .py, 49,294 lines — the application
│   ├── api/                  FastAPI: 14 route modules, 63 endpoints, 2 middleware
│   ├── brokers/binance/      Exchange client, execution adapter, rate limiter
│   ├── core/
│   │   ├── alerting/         Telegram channel, triggers, scheduler, escalation
│   │   ├── config/           YAML+env loader, templates, risk profiles, backup
│   │   ├── execution/        Order manager, position tracker, execution quality
│   │   ├── indicators/       19 technical indicators
│   │   ├── monitoring/       Monitoring service
│   │   ├── risk/             11 modules — the safety system
│   │   ├── strategy/
│   │   │   ├── backtest/     Engine, trader, portfolio, metrics, validator
│   │   │   ├── generators/   29 signal generators
│   │   │   ├── paper/        Paper trading engine and manager
│   │   │   └── regime/       Detector, historical classifier, router
│   │   ├── event_bus.py      Pub/sub
│   │   ├── exceptions.py     868-line exception hierarchy
│   │   ├── health.py         Health checks
│   │   └── orchestrator.py   1,800 lines — the main loop
│   ├── data/                 15 ORM models, DataStore, market data, validators, cache
│   └── utils/                Logging, time, config, geo-block
├── research/                 27 .py, 5,411 lines — the research library
│   ├── backtest/             Cost model, regime tagging
│   ├── biographies/          Strategy biography schema
│   ├── data/                 Funding, ETF flows, Coinbase premium, liquidations
│   ├── generators/           7 crypto-native hypothesis generators
│   ├── promotion/            Tier classifier
│   └── validation/           Deflated Sharpe, effective-K
├── scripts/                  24 files, 11,865 lines — operational entrypoints
├── tests/                    134 files, 36,221 lines, 1,900 tests
├── frontend/                 100 .ts/.tsx, 17,230 lines — React dashboard
├── docs/                     50 tracked .md
├── config/                   settings.yaml, risk_profiles.yaml, 14 strategy templates
├── alembic/                  6 migrations
└── .claude/ + .agent/        DECISIONS.md (113 decisions, dual-maintained) + rules
```

---

## 4. Architecture

### 4.1 Runtime topology

Three processes, all built from the same Docker image:

1. **`web`** — `uvicorn src.api.main:app`. The read/query API and dashboard backend.
2. **`paper`** — `scripts/run_paper_trading.py`. The simulation loop.
3. **`live`** — `scripts/run_live_trading.py`. The real-capital loop, kill-switch gated.

Plus scheduled cron jobs on Railway (documented in `docs/operations/RAILWAY_CRONS.md`),
most importantly a daily validation report pushed to Telegram at 09:00 UTC.

### 4.2 The trading data flow

```
Binance REST  ->  MarketDataFetcher  ->  OHLCVSeries (in-memory, cached)
                                              |
                                              v
                                    IndicatorFactory (cached)
                                              |
                                              v
                       SignalGenerator.generate() -> TradingSignal | None
                                              |
                                              v
                    RegimeRouter: is this strategy allowed in this regime?
                                              |
                                              v
                        RiskController.validate_order()
                          - kill switch          (checked FIRST)
                          - daily loss limit
                          - weekly loss limit
                          - max drawdown
                          - max open positions
                          - concentration
                          - position size
                          - portfolio correlation
                          - circuit breakers (5)
                          - time filter / event filter
                                              |
                                     APPROVED  |  REJECTED -> logged + alerted
                                              v
                              PositionSizer -> quantity
                                              |
                                              v
                       OrderManager (state machine) -> ExecutionInterface
                                              |
                            +-----------------+-----------------+
                            v                                   v
                   BinanceExecution                     PaperExecution
                            |                                   |
                            +-----------------+-----------------+
                                              v
                                     PositionTracker
                                              |
                                              v
                        DataStore -> orders, trades, positions, pnl
                                              |
                                              v
                        ExecutionQuality (slippage, fill rate)
                        AlertTriggers -> Telegram
```

The key architectural property: **paper and live share the entire code path** and
diverge only at the `ExecutionInterface` boundary. A paper session and a live session
run identical signal generation, identical risk checks, and identical position
tracking. This is what makes paper results meaningful as a promotion gate.

### 4.3 The orchestrator

`src/core/orchestrator.py` (1,800 lines) is the async coordinator. It provides:

- **8-step startup validation** — database reachable, config valid, broker reachable,
  account state loadable, strategies constructible, risk limits sane, kill switch
  readable, disk space available. Any failure aborts startup.
- **Main event loop** with the kill switch checked *first* on every cycle
  (DEC-2026-02-12-003) — before any strategy is even evaluated.
- **Entry timing coordination** via a heap, so strategies on different timeframes
  wake at the right bar boundaries rather than polling.
- **Graceful degradation** — a failing subsystem downgrades the system to a reduced
  mode rather than crashing it, and emits an alert on entering and leaving that mode.
- **Emergency shutdown** on SIGTERM/SIGINT with position reconciliation.
- **Injectable clock** (DEC-2026-02-12-012) so time-dependent logic is testable.
- **Metrics counters** — cycles completed, strategies processed, orders
  submitted/filled/rejected, errors caught, cycle duration. These exist but are not
  exported anywhere; see the readiness assessment, item 4.3.

### 4.4 Dependency rule

`research/` may import from `src/`. `src/` must never import from `research/`
(DEC-2026-06-04-001). This one-way boundary means the research layer can be deleted
without breaking the trading system, and research experiments cannot accidentally
change live behaviour.

Graduation path: a generator proven in `research/generators/` is *promoted* by being
reimplemented in `src/core/strategy/generators/` (DEC-2026-06-04-004). Nothing runs
live from the research tree.

---

## 5. Data model

15 SQLAlchemy 2.0 models, all using `Mapped[T]` typing, timezone-aware UTC
timestamps, `@validates` guards rejecting NaN/Infinity/negative values on every
financial field, and lambda factories for mutable defaults.

| Model | Purpose |
|---|---|
| `Account` | Balance, equity, risk config (JSON), regime tag |
| `Strategy` | Template id, parameters (JSON), status, live results (JSON) |
| `StrategyAssignment` | Which strategy runs on which symbol, unique-constrained |
| `Order` | Client order id, side, type, quantity, status, submitted/filled timestamps |
| `Trade` | Executed fill: price, quantity, commission, realized PnL |
| `Position` | Symbol, quantity, average entry, unrealized PnL, commission |
| `PnLRecord` | Realized/unrealized PnL snapshots |
| `EquitySnapshot` | Time series of account equity — the source for equity curves |
| `Signal` | Emitted trading signals with indicator values at emission |
| `Symbol` | Exchange metadata: tick size, step size, min notional, filters |
| `SystemState` | Kill switch state, regime, degradation mode, singleton row |
| `PaperTradingSession` | A paper run: template, symbol, capital, equity, trade count |
| `SlippageRecord` | Measured slippage per fill |
| `FillRateRecord` | Measured fill rate per order |
| `AuditLog` | Append-only record of state-changing operations |

**Strategy lifecycle statuses:** DRAFT -> TESTING -> BACKTESTING -> PAPER -> LIVE,
with SUSPENDED and RETIRED as terminal-ish states, and an OPTIMIZATION status added
2026-02-22.

Migrations are managed by Alembic (6 revisions). Development uses SQLite; production
uses PostgreSQL on Neon.

---

## 6. API surface

FastAPI, 63 endpoints across 14 route modules. The 21 state-mutating endpoints
require a shared `X-API-Key` secret as of 2026-08-14 (DEC-2026-08-14-001); the
42 read endpoints are open. The gate is method-based middleware rather than a
per-route dependency, chosen because the latter is fail-open for endpoints
added later — see `docs/ARCHITECTURE.md` section 8.1. Remaining gaps: one
shared key with no identities or rotation, open reads. Mutating requests are
also rate-capped per client and globally (DEC-2026-08-14-003), reusing the
`TokenBucket` primitive from the Binance adapter but rejecting rather than
blocking, since blocking inbound would amplify a flood rather than absorb it.

| Module | Endpoints | Notable |
|---|---|---|
| `accounts` | 6 | Create, read, update account and risk config |
| `backtest` | 3 | Run a backtest, fetch results |
| `dashboard` | 6 | Aggregated dashboard payloads |
| `events` | 1 | Event stream |
| `execution` | 4 | Execution quality: slippage, fill rates |
| `orders` | 5 | Place, list, get, cancel, retry |
| `paper_trading` | 5 | Start/stop sessions, read state |
| `pnl` | 5 | Realized, unrealized, daily, by-strategy |
| `positions` | 4 | List, get, close |
| `regime` | 2 | `/current`, `/paper-sessions` |
| `risk` | 4 | Limits, kill switch activate/deactivate, breaker reset |
| `strategies` | 10 | CRUD, parameter update, status transition, assignment, regimes |
| `system` | 7 | Status, start, stop, config |
| root | 3 | `/health`, `/ready`, `/health/detailed` |

21 endpoints mutate state, including order placement, position closure, and kill
switch control.

Middleware: structured request logging with request IDs, and a global exception
handler that returns detail in development and a generic message in production.
CORS is an explicit allowlist — no wildcard (DEC-2026-02-08-004, fixing what was
originally a critical vulnerability).

---

## 7. Indicators

19 implementations in `src/core/indicators/`, each independently unit-tested with
coverage between 88% and 100%:

ADX (with +DI/-DI), ATR, Bollinger Bands, Donchian Channels, EMA, Ichimoku Cloud,
Keltner Channels, MACD, RSI, SMA, Stochastic RSI, SuperTrend, VWAP, volume metrics,
plus `base` (shared interface), `factory` (construction), `cached` (memoised wrapper),
`resample` (timeframe conversion), and `utils`.

All indicators operate on an `OHLCVSeries` value object and return typed results.
The cached wrapper is what makes multi-timeframe strategies affordable — a strategy
requiring 1h, 4h, and 1d alignment computes each series once.

---

## 8. Strategy library

29 signal generators in `src/core/strategy/generators/`. 14 have YAML templates in
`config/templates/` defining default parameters and bounds.

### 8.1 Trend following

| Generator | Mechanism |
|---|---|
| `bull_trend_pullback` (BTP) | Long-only continuation in confirmed bull; buys retracement |
| `bear_trend_follower` (BTF) | Multi-timeframe bear trend following. **Retired** |
| `macd_pullback` (MACD_PB) | MACD confirms trend, price pulls back to EMA. **Retired** |
| `ema_trend_rsi` | EMA crossover with RSI momentum confirmation |
| `supertrend_volume_macd` (SRC) | Triple confluence: SuperTrend + volume + MACD |
| `cascading_momentum_filter` (CMF) | Requires all 3 timeframes aligned. **Retired** |
| `multi_tf_confluence` | Trend alignment across three timeframes |
| `ichimoku_cloud_trend` (ICVP) | Ichimoku cloud system |
| `heikin_ashi_trend_pulse` (HATP) | Heikin-Ashi smoothed trend. **Retired** |
| `trend_acceleration_momentum` | Enters only when a trend is accelerating |
| `adx_directional_thrust` (ADT) | ADX +DI/-DI directional system |
| `keltner_channel_continuation` (KCC) | Close above upper Keltner as continuation |

### 8.2 Breakout / volatility

| Generator | Mechanism |
|---|---|
| `donchian_atr` | Donchian channel break with ATR volatility filter |
| `bb_squeeze_breakout` | BB breakout after squeeze, MACD confirmed |
| `bb_squeeze_momentum` | TTM Squeeze (BB inside Keltner) |
| `volatility_regime_breakout` (VRB) | BB-width squeeze-release. **Retired** |
| `realized_vol_compression_breakout` (RVCB) | Rolling stdev compression. **Observe only** |
| `volume_balance_breakout` (VBB) | Up-volume balance ratio breakout |
| `ema_ribbon_expansion` (EREE) | Spread between EMA(8/21/55) expanding. **Shelved** |

### 8.3 Mean reversion

| Generator | Mechanism |
|---|---|
| `rsi_bb_mean_reversion` (RSI_BB) | RSI extreme + BB touch in low-trend. **Retired** |
| `regime_aware_mean_reversion` (RAMR) | Direction bias adapts to regime |
| `keltner_fade_adx` (KFA) | Fades Keltner overextension, ADX-filtered. **Shelved** |
| `rsi_divergence_reversal` | Classic price/RSI divergence |
| `crypto_wick_reversal` (CWR) | Stop-hunt wick recovery — crypto leverage cascades |

### 8.4 Volume / flow

| Generator | Mechanism |
|---|---|
| `obv_trend_divergence` (OBV_TD) | On-Balance Volume institutional accumulation lead |
| `vpt_momentum` (VPT) | Volume Price Trend cumulative momentum. **Retired** |
| `vwap_pullback_volume` | Pullback to VWAP with volume confirmation |
| `roc_momentum_surge` | ROC acceleration + RSI in the 60-75 "power zone" |
| `stoch_rsi_bull_cross` | StochRSI K/D cross from oversold as micro-pullback |

### 8.5 Research-layer generators (`research/generators/`)

Seven generators driven by data other than price. These are hypothesis vehicles;
none has graduated to `src/`:

`funding_confirmed_trend`, `funding_extreme_contrarian` (v1 and v2),
`coinbase_premium`, `etf_flow_demand`, `btc_lead_lag`, `cross_sectional_momentum`.

---

## 9. Regime system

The regime system decides *which strategies are allowed to trade right now*.

### 9.1 Coarse regime — `RegimeState`

Computed from BTC daily EMA(50) and EMA(200) (DEC-2026-05-04-001):

| State | Condition |
|---|---|
| `STRONG_BULL` | EMA50 > EMA200 and price > EMA50 |
| `PULLBACK_BULL` | EMA50 > EMA200 and price <= EMA50 |
| `BOUNCE_BEAR` | EMA50 < EMA200 and price >= EMA50 |
| `STRONG_BEAR` | EMA50 < EMA200 and price < EMA50 |
| `UNKNOWN` | Insufficient data or confirmation failure |

A state change requires **two consecutive daily closes** in the new state before it
takes effect. This prevents whipsaw thrashing of strategy activation.

### 9.2 Fine regime — `SubRegime`

Eight values, used for both backtest attribution and live routing:

`trending_bull`, `choppy_bull`, `trending_bear`, `choppy_bear`, `ranging`,
`high_vol`, `transitional`, `unknown`.

The distinction matters because the coarse buckets merge trending and choppy within
a direction, which masks where edge actually concentrates. Several strategies
originally named for bull conditions turned out to have their real (if weak) edge in
`choppy_bear` — the names were wrong, not the strategies.

### 9.3 Routing

`RegimeRouter` (`src/core/strategy/regime/router.py`) resolves which strategies
activate. Precedence (DEC-2026-05-28-003):

1. If a strategy declares `regime_tags: list[str]` (fine SubRegime values), those
   take precedence.
2. Otherwise the legacy coarse `regime` field is used.
3. If SubRegime is `UNKNOWN` or `TRANSITIONAL`, `regime_tags`-tagged strategies do
   **not** activate. Fail closed — better quiet than wrong-regime.
4. `observe_only: True` blocks router activation entirely (paper data collection only).

The same precedence logic is applied in the live loop via `_tier_regime_match()`, so
routing and live tier activation cannot disagree. 14 fail-closed contract tests cover
this in `tests/unit/regime/test_sub_regime_routing.py`.

---

## 10. Risk system

The most complete subsystem in the codebase. Coverage: sizing 100%, checks 99%,
time filter 100%, kill switch 94%.

### 10.1 Pre-trade checks (`src/core/risk/checks.py`)

Eight independent functions, each returning a `RiskCheckResult`:

1. `check_kill_switch` — evaluated first, always
2. `check_daily_loss_limit`
3. `check_weekly_loss_limit`
4. `check_max_drawdown`
5. `check_max_positions`
6. `check_concentration` — exposure to a single asset
7. `check_position_size`
8. `check_portfolio_correlation` — same-direction correlated exposure
   (DEC-2026-02-22-001)

### 10.2 Circuit breakers (`src/core/risk/circuit_breakers.py`)

Five breakers behind a common abstract base with cooldown, trip state, persistence,
and restore-from-dict:

`DailyLossCircuitBreaker`, `WeeklyLossCircuitBreaker`, `DrawdownCircuitBreaker`,
`ConsecutiveLossCircuitBreaker`, `CorrelationCircuitBreaker`, coordinated by a
`CircuitBreakerManager`.

Breaker state survives restart — a tripped breaker does not reset itself by the
process dying.

### 10.3 Additional safety

- **Kill switch** — persisted in `SystemState`, fail-closed default,
  runbook at `docs/operations/kill_switch_runbook.md`
- **Dead man's switch** — halts trading if the main loop stops heartbeating
- **Time filter** — blocks trading in configured windows
- **Event filter** — blocks trading around known high-impact events
- **Volatility filter** — blocks entries when realised volatility is out of band
- **Geo-block fail-fast** (DEC-2026-06-01-003) — recognises Binance regional
  rejection and stops retrying instead of burning the rate limit

### 10.4 Position sizing

`src/core/risk/sizing.py`, 100% covered. Fixed-fractional sizing off stop distance,
with exchange constraint enforcement: step size rounding, tick size rounding,
minimum quantity, minimum notional.

---

## 11. Backtest engine

`src/core/strategy/backtest/` — engine, trader, portfolio, metrics, validator, types.

### 11.1 Configuration (`BacktestConfig`)

| Field | Default | Meaning |
|---|---|---|
| `initial_capital` | 10,000 USDT | Starting equity |
| `commission_rate` | 0.001 (0.1%) | Per-trade commission |
| `slippage_rate` | 0.0005 (0.05%) | Per-trade slippage |
| `use_next_bar_open` | True | Fill at next bar open — prevents lookahead bias |
| `risk_free_rate` | 0.02 | For Sharpe/Sortino |
| `position_size_pct` | 0.35 | Fraction of equity per trade |
| `allow_shorts` | True | False = spot long-only mode (DEC-2026-05-28-001) |
| `funding_rate_per_8h` | 0.0 | Perp funding drag; charged as an always-cost |

The funding model is deliberately conservative: since the funding sign cannot be
known in advance, the held side is always charged.

### 11.2 Metrics computed

`total_return_pct`, `annualized_return_pct` (CAGR), `sharpe_ratio`, `sortino_ratio`,
`calmar_ratio`, `max_drawdown_pct`, `max_drawdown_duration_days`, `total_trades`,
`winning_trades`, `losing_trades`, `win_rate_pct`, `profit_factor`, `avg_win_pct`,
`avg_loss_pct`, `expectancy`, `largest_win`, `largest_loss`,
`avg_trade_duration_hours`, `max_trade_duration_hours`, `monthly_returns`,
`per_symbol_breakdown`.

### 11.3 Validation gates (`validator.py`)

Two-tier thresholds from the Ernest Chan framework (DEC-2026-02-22-003).
PRD Section 3.6 gates: Sharpe >= 1.0, total trades >= 100, win rate >= 50%,
profit factor >= 1.3, expectancy > 0.

### 11.4 Performance

`lookback_window` optimisation reduced the engine from O(n^2) to O(n)
(DEC-2026-06-04-015). It is opt-in and gated by an equivalence test
(`tests/unit/backtest/test_window_equivalence.py`) proving the fast path produces
identical results to the slow path.

### 11.5 Rolling and walk-forward

- `scripts/backtest_rolling.py` — rolling-window backtests with per-bar SubRegime
  attribution
- `scripts/sweep_tp_wfo.py` (797 lines) — walk-forward optimisation
- `scripts/sweep_*.py` — parameter sweeps for stop multiplier, bull params, new strategies

---

## 12. Paper trading

`src/core/strategy/paper/` — engine (735 lines) and manager (276 lines).

Synchronous simulation (DEC-2026-02-15-001) using real-time market data through the
identical code path as live, diverging only at the execution interface. Each session
is a `PaperTradingSession` row tracking template, symbol, initial capital, current
equity, PnL, trade count, and activity state.

Paper is not a toy. It is the **promotion gate**: a strategy cannot go live until its
pooled paper record is classified `READY_FOR_LIVE`.

---

## 13. Live trading and the capital model

`scripts/run_live_trading.py`, 2,111 lines. This is where the project's safety
thinking is most concentrated.

### 13.1 Capital model (PARA-12, DEC-2026-05-31-003)

The original design gave every strategy tier the *full* account, double-counting
capital across concurrent strategies. The fix:

```
PER_STRATEGY_CAPITAL = LIVE_CAPITAL x PER_STRATEGY_ALLOCATION_PCT   (default 20%)
per_trade_notional   = PER_STRATEGY_CAPITAL x POSITION_SIZE_FRACTION (0.25)
```

Rails in `_can_activate_tier()`:

1. **Concurrency cap** — `MAX_STRATEGIES_LIVE_CONCURRENT`, default 4
2. **Capital reserve** — projected committed capital must stay at or below
   `LIVE_CAPITAL x CAPITAL_RESERVE_FRACTION` (default 0.85)
3. Tier activation thresholds are rebased to multiples of the per-strategy slice, not
   the full account, so they remain reachable

**Binding constraint:** at LIVE_CAPITAL = $20, per-trade notional is
$20 x 0.20 x 0.25 = $1, below the Binance $5 minimum. The startup guard therefore
**fails closed with `sys.exit(1)`** rather than silently rounding up. The 4-strategy
model requires LIVE_CAPITAL >= $100.

### 13.2 Promotion and demotion gates

**Auto-promotion gate** (DEC-2026-06-01-001, extended by -002): a tier may only
activate when its pooled live-paper record is classified `READY_FOR_LIVE`:

```
N >= 30   AND   PF >= 1.35   AND   Sharpe >= 1.0   AND   MaxDD <= 5%
```

Failure semantics are deliberate and asymmetric:
- **Fails OPEN on database error** — a DB outage must not block a restart
- **Fails CLOSED on a clear non-READY verdict** — an unproven strategy never activates

The gate reuses the same helper functions as `validation_report.py`
(`_classify`, `_profit_factor`, `_sharpe_per_trade`, `_max_drawdown_pct`), so the
gate and the report cannot disagree. Originally tier 1 was exempt; DEC-2026-06-01-002
closed that hole — a blocked tier 1 self-heals by re-entering the activation loop
each poll.

**Demotion guardrail**: PF < 0.8 at N >= 10 deactivates a tier.

**Decorrelation cap** (DEC-2026-05-27-006): limits same-direction correlated positions.

**Consecutive-failure alerting** (DEC-2026-05-27-003): repeated errors escalate.

### 13.3 Distance-to-promotion reporting

`scripts/validation_report.py` computes a `PromotionDistance` per session: trades
needed, PF deficit, Sharpe deficit, drawdown overage — each floored at zero. Rendered
in console (ASCII markers `[OK]` / `[...]` / `[MISS]`), in compact/Telegram form, and
in JSON. Delivered daily to Telegram at 09:00 UTC. **This is the operator's primary
dashboard during the waiting period.**

### 13.4 Current live state

`LIVE_TRADING_ENABLED` defaults OFF and is off. Re-enabling requires setting the
environment variable on Railway *and* passing the capital floor guard *and* passing
the promotion gate. As of this writing no strategy passes the promotion gate.

---

## 14. The research layer

This is the intellectually distinctive part of the project.

### 14.1 The problem it defends against

From `docs/research/RESEARCH_PROTOCOL.md`:

| Failure mode | How it appears here | Defense |
|---|---|---|
| Multiple testing | Many strategies x symbols x params; winners promoted | Experiment registry + DSR + PBO |
| Small-sample illusion | PF 4.6 on 5 trades promoted | Minimum-evidence gate, Bayesian shrinkage |
| Out-of-sample leakage | Picking params by best OOS score | Strict train/holdout separation |
| Backtest-vs-reality gap | Shorts simulated but unexecutable on spot; flat slippage | Executability check, cost stress |
| Regime confounding | Strategy looks good only because the market trended | Regime-conditional attribution |
| No reproducibility | Data re-fetched every run; results drift | Frozen, versioned datasets |

Prime directive: *assume every edge is fake until overwhelming, multiply-corrected,
out-of-sample evidence says otherwise.*

### 14.2 The funnel

```
HYPOTHESIS -> TRAIN (design freely) -> HOLDOUT (look ONCE) ->
SIMULATED PAPER -> LIVE PAPER -> MICRO-LIVE ($50-100) -> LIVE (scaled)
```

Gate thresholds are set **before** results are seen and recorded in the experiment
registry. Moving a gate to make a strategy pass is forbidden unless the change is
documented, dated, and applied to *all* strategies, not the one in front of you.

**Stage 1 requires a written economic hypothesis** answering three questions:
what is the edge, who is on the other side and why do they lose, and why does this
persist rather than being arbitraged away. If those cannot be answered, it is
indicator mining, not research.

### 14.3 Statistical machinery

**Deflated Sharpe Ratio** (`research/validation/deflated_sharpe.py`, 446 lines) —
corrects an observed Sharpe for the number of trials actually run, plus skew and
kurtosis of the return distribution. Output is a p-value: the probability that the
observed Sharpe arose from noise given the search conducted.

**Effective-K** (`research/validation/effective_k.py`, 241 lines) — counts effective
independent trials, including a multiplier for regime-bucket slicing (testing across
6 SubRegimes is not one test).

**Cost model** (`research/backtest/cost_model.py`, 356 lines) — versioned
(`v0_unverified`), applied as a conservative incremental pad over already-net returns,
doubling estimated components (DEC-2026-06-04-013). Deliberately pessimistic.

**Tier classifier** (`research/promotion/classifier.py`):

| Tier | DSR p | PF | Sharpe | N | MaxDD | Action |
|---|---|---|---|---|---|---|
| A | < 0.20 | >= 1.35 | >= 1.0 | >= 30 | < 5% | continue_full |
| B | < 0.30 | >= 1.25 | >= 0.8 | >= 20 | < 5% | continue_half |
| C | — | — | — | — | — | observe |
| D | >= 0.50 or MaxDD >= 10% | — | — | — | — | retire |

An `INSUFFICIENT_DATA` guard prevents scarce data (N = 0..4) from masquerading as
`TIER_D_REJECT` — a distinction that was actually wrong in the first Neon run and was
fixed. A **fragility rule** demotes a base-deployable strategy to Tier C when the
conservative cost scenario drops it to Tier D.

**DSR p < 0.3 is a non-negotiable floor** (DEC-2026-06-04-008).

### 14.4 Data channels

`research/data/` — sources beyond price:

- **Perp funding rates** — positioning and carry
- **ETF flows** — spot demand from regulated vehicles
- **Coinbase premium** — US vs offshore demand divergence
- **Liquidations** — forced deleveraging, with a *forward collector*
  (`liquidation_collector.py` + `scripts/run_liquidation_collector.py`) that streams
  Binance `forceOrder` events to JSONL with a causal accessor, so no lookahead
  (DEC-2026-06-04-021)
- **BTC reference series** and **cross-sectional ranking**

### 14.5 Strategy biographies and post-mortems

Every strategy has a structured biography (`research/biographies/schema.py`, 443 lines)
with an append-only decision log. Every *retired* strategy gets a generated
post-mortem (`scripts/generate_post_mortem.py`, 581 lines) with a tagged failure
pattern. DEC-2026-06-04-011: the lifecycle pipeline closes the circle — a post-mortem
completes every retirement.

Seven post-mortems exist, pattern-tagged. `docs/research/NEGATIVE_SPACE_MAP.md`
records where edge has been *proven absent*, which is treated as a first-class result.

### 14.6 The pre-registered stop/pivot gate

DEC-2026-06-04-010 fixes a date — **2026-12-01** — at which the project evaluates
whether to continue, pivot, or stop, against criteria written in advance including a
verified (not estimated) cost model. This is unusual and worth noting: the project
pre-committed to the conditions under which it would declare itself a failure.

### 14.7 Known research-layer defects (PARA-01 to PARA-12)

A self-audit conducted 2026-05-28 identified 12 methodology and correctness issues:

| ID | Severity | Issue | Status |
|---|---|---|---|
| PARA-01 | CRITICAL | Short trades simulated but unexecutable on spot | Resolved by finding spot beats futures |
| PARA-02 | HIGH | Live-paper force-close used a dimensionless ratio as a price | FIXED + historical quarantine |
| PARA-03 | HIGH | WFO selects parameters on out-of-sample data | OPEN |
| PARA-04 | HIGH | Promotions on samples far below statistical minimum | OPEN |
| PARA-05 | MEDIUM | Rolling-window backtests overlap, not independent | OPEN |
| PARA-06 | MEDIUM | Regime attribution window-level, not trade-level | OPEN |
| PARA-07 | MEDIUM | Stop/TP fills assume no gap-through | OPEN |
| PARA-08 | LOW | per-symbol total_return summed percentages | FIXED |
| PARA-09 | LOW | largest_loss mislabelled smallest win | FIXED |
| PARA-10 | PERF | O(n^2) backtest | FIXED (DEC-2026-06-04-015) |
| PARA-11 | MEDIUM | Flat slippage ignores order size | OPEN |
| PARA-12 | MEDIUM | Each strategy backtested assuming full capital | FIXED (DEC-2026-05-31-003) |

That this list exists, is severity-ranked, and is honestly marked OPEN where unfixed
is itself a meaningful engineering artifact.

---

## 15. Research findings to date

**This is the most important section of this document.**

### 15.1 The volume of work

- 120 backtest runs in bear regime — 0 passed
- 45-day bull backtest, 112 runs — 2 passed
- 90-day mixed-regime run — several promotions
- Three batches of crypto-native generators, multiple rounds each
- 11 strategies reached a KEEP or RETIRED classification

### 15.2 The retrospective DSR result (2026-06-05)

> **CORRECTED 2026-08-11 — the table below is the superseded output.**
>
> Ten of these eleven strategies had 0 to 4 recorded trades, because paper
> trading was down behind a regional exchange block. Under the corrected
> classifier (`MIN_N_FOR_CLASSIFICATION = 10`, DEC-2026-06-04-014) they are
> `INSUFFICIENT_DATA`, not `TIER_D_REJECT`. Only BTF (N=25) is a genuine
> rejection from this run.
>
> The conclusion "no strategy has a validated edge" is unchanged. The claim that
> all eleven were *shown to be worthless* is withdrawn — most were never
> measured. Section 15.3 below also understates the forward loop, which ran 11
> hypotheses and produced 7 genuine rejections, not 2.
>
> See **[RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md)** for the corrected account.

All 11 strategies were re-analysed under Deflated Sharpe with the conservative cost
model. Result (`docs/research/retrospective/PORTFOLIO_SUMMARY_2026-06-05.md`):

```
KEEP strategies surviving the DSR floor (p < 0.3):   0 of 5
KEEP at Tier A:                                       0
KEEP at Tier B:                                       0
KEEP at Tier C:                                       0
KEEP at Tier D:                                       5
RETIRED confirmed at Tier C/D:                        6 of 6
RETIRED surprises (Tier A/B, warranting re-exam):     0
```

**Every strategy landed at TIER_D_REJECT.** The five that had been classified KEEP —
including MACD_PB, which had been the portfolio's most-trusted multi-regime
performer — did not survive correction for the number of trials run.

Notably, the six previously-retired strategies were *confirmed* as correctly retired,
and there were zero false negatives. The method agreed with the prior judgment where
that judgment had been conservative, and overturned it where it had been optimistic.

### 15.3 The forward loop (2026-06-08 onward)

The forward hypothesis loop ran two full iterations after the retrospective:

- **H-2026-06-002** — price breakout-continuation (reused `donchian_atr`).
  Stage-1 quality score 14/21 (PASS_MARGINAL). Result: trending_bull PF 0.59,
  N=341, DSR p=1.0. **TIER_D FUNDAMENTAL.**
- **H-2026-06-003** — perp-funding-confirmed trend (new crypto-native generator).
  Stage-1 score 18/21 (PASS). Result: trending_bull PF 0.53, N=132, DSR p=1.0.
  **TIER_D FUNDAMENTAL.**
- A third (buy-the-dip pullback) was killed at the Stage-1 hard gate as a structural
  duplicate of existing strategies — minutes of work, no DSR trial consumed.

Both rejections occurred at large N with no capital risked. That is the funnel
working as designed.

### 15.4 Two load-bearing conclusions

1. **TRENDING_BULL continuation is a hard gap.** Both price-momentum *and*
   derivatives-flow continuation are dead there at large sample. The next hypothesis
   for that regime cell must come from a different mechanism class entirely, not
   another continuation variant.
2. **Calibration lesson.** H-003 scored *higher* at the hypothesis quality gate
   (18 vs 14) and performed *worse*. The scorecard measures mechanism plausibility,
   not expected profitability. This was recorded rather than rationalised away.

### 15.5 The spot-versus-futures finding

Spot mode (long-only) empirically **beat** futures mode (long+short with funding) for
every strategy with bidirectional signals:

- MACD_PB in choppy_bear: PF 2.33 spot vs 1.02 futures
- ICVP in choppy_bear: PF 1.28 spot vs 0.78 futures

Consequence: live futures execution was never built. The scope amendment that
permitted futures research produced the evidence that futures was unnecessary. This
is a good example of the research layer earning its cost.

### 15.6 What this means

**The system has no validated trading edge.** It also has a validation layer
rigorous enough to establish that, and that layer was pointed at the author's own
work and reported honestly.

The second fact is the more valuable one and should be presented as the headline
result, not hidden behind the first.

---

## 16. Frontend

React 19 + Vite 7 + TypeScript 5.9 + Tailwind v3 + framer-motion + Recharts +
TanStack Query + React Router. Builds cleanly in ~41 seconds.

**13 pages:** Cockpit (main dashboard), Portfolio, Strategies, Trade History, Risk,
Regime, Alerts, System, Settings, Backtest Results, plus three developer component
galleries (Dev, Dev2, Dev3 — 2,097 lines combined).

**~40 components** across `ui/` (Button, Card, Badge, Input, Select, Dropdown,
DataTable, Pagination, Tabs, Tooltip, Toast, DateRangePicker, MetricCard,
KeyboardShortcuts, ErrorBoundary), `charts/` (Area, SVGArea, Donut, Sparkline,
Benchmark), `dashboard/` (PositionsTable, TradeHistoryTable, StrategyCard,
EmergencyPanel, RiskGauge, DrawdownChart, EquityChart, ActivityFeed, Watchlist,
MarketTicker, and modals/drawers), and `layout/` (Header, Sidebar,
NotificationsPanel, Section).

**Theming:** 4 palettes (ocean, sapphire, emerald, onyx) via `data-theme` on `<html>`,
each with light and dark, switched by a `ThemeContext` that toggles `html.dark`.
Design tokens are CSS variables referenced from `tailwind.config.js`.

**Known constraint:** `tsconfig.app.json` sets `verbatimModuleSyntax: true`, so all
type-only imports must use `import type` or they crash at runtime.

**Critical gap:** the frontend makes **three** network calls in total
(`/api/v1/regime/current`, `/api/v1/regime/paper-sessions`,
`/api/v1/strategies/{id}/backtest/results`). Every other page renders hardcoded
arrays; `PortfolioPage` generates its equity curve with `Math.sin() + Math.random()`.
There are no frontend tests. See the readiness assessment, Phase 3.

---

## 17. Deployment and operations

**Container:** Python 3.11-slim, non-root `appuser`, health check via curl.

**Platform:** Railway. `railway.toml` builds from the Dockerfile and starts
`python -m scripts.run_all`. `Procfile` defines `web` and `paper` processes.

**Persistence:** a Railway volume must be mounted at `/app/data` or SQLite state
resets on every deploy. Production uses PostgreSQL on Neon.

**Scheduled jobs** (`docs/operations/RAILWAY_CRONS.md`): the daily validation report
at 09:00 UTC via `validation_report --telegram` is the operational heartbeat.

**Alerting:** Telegram. 15 trigger types — order filled, order rejected, daily loss
warning, drawdown warning, kill switch activated, circuit breaker triggered, strategy
underperforming, exchange API error, system started, system stopped, position sync
mismatch, risk limit breached, health check failed, degradation mode entered,
degradation mode recovered. Plus a scheduler and an escalation channel.

**Runbooks:** `docs/operations/kill_switch_runbook.md` exists. A general runbook does
not yet — see readiness assessment 4.4.

---

## 18. Governance

### 18.1 The decision log

113 dated architectural decisions, 2,998 lines, maintained identically in
`.claude/DECISIONS.md` and `.agent/DECISIONS.md` (verified byte-identical). Each entry
records: decision, context, rationale, alternatives considered, status, date,
implementing section, affected files, references.

Statuses include ACTIVE, SUPERSEDED (with a pointer to the superseding decision), and
LOCKED (scope decisions that may not be revisited without a PRD update).

### 18.2 The rules files

- `.claude/rules/decision-consistency.md` — decisions must be read before
  implementation; code violating a decision must be refused; new decisions must be
  filed in both locations
- `.claude/rules/zero-technical-debt.md` — backward compatibility, naming stability,
  behaviour-preserving refactors, no mixed intent, state ownership, explicit control
  flow, rollback readiness
- `.claude/rules/mvp-scope-control.md` — the locked scope, the rejection template, the
  distinction between gold-plating (forbidden) and production quality (required)

These are unusual for a solo project and are a genuine artifact: the author built an
enforcement mechanism against their own future scope creep.

---

## 19. Testing

> **SUPERSEDED 2026-08-11.** The suite is now green:
> `1,907 tests | 1,870 passed | 0 failed | 37 skipped | 0 errors`.
> The 9 failures were fixed and the 32 errors were network-dependent tests that
> now skip unless `PARAVANT_RUN_NETWORK_TESTS=1` (DEC-2026-08-11-004). The
> coverage figure below has not been re-measured since. The block is left as the
> 2026-08-08 record.

```
As of 2026-08-14:
2,054 tests | 2,017 passed | 37 skipped | 0 failed | 0 errors | ~95s
Coverage: 74% (src + research, whole suite), CI floor 72%
```

The 2026-08-08 snapshot below read `1,900 tests | 1,855 passed | 9 failed |
32 errors | 63% coverage`. All nine failures and all thirty-two errors are
resolved. The 63% figure was also measured over `tests/unit` + `tests/research`
only, which understated any module tested from `tests/integration/` — see the
correction under "Poorly covered" below (DEC-2026-08-14-004).

**Structure:** `tests/unit/` (the bulk, by subsystem), `tests/integration/`
(API, database CRUD, order flow, full system, real-world scenarios),
`tests/research/` (24 files covering the research layer),
`tests/load/`, `tests/performance/`.

**Well covered:** risk sizing 100%, risk checks 99%, time filter 100%, indicators
88-100%, data models 88-100%, health 94%, config 96-97%.

**Poorly covered** (corrected 2026-08-14): the previous entry here read
"`data/store.py` 28%". That was a measurement artifact — the CI coverage job
scoped itself to `tests/unit` + `tests/research`, while `DataStore` is tested
from `tests/integration/`, which the `test` job runs on every commit. Measured
over the whole suite `store.py` is at **100%**. The job now measures everything
(DEC-2026-08-14-004). Remaining genuinely thin: `strategy/engine.py`,
`risk/controller.py`, and `scripts/` — including the 2,111-line live loop —
which is largely unmeasured.

The 32 errors were network-dependent Binance tests that errored rather than
skipped; they now skip unless `PARAVANT_RUN_NETWORK_TESTS=1`
(DEC-2026-08-11-004). The 9 failures are all fixed. Full detail in the
readiness assessment, Section 2.1.

---

## 20. Current state at a glance

| Dimension | State |
|---|---|
| Backend application | Complete and functional; 63 endpoints; mutating 21 behind a shared `X-API-Key`, reads open |
| Risk system | Complete, best-tested subsystem in the project |
| Strategy library | 29 generators built; **0 validated** |
| Backtest engine | Complete, O(n) optimised, equivalence-gated |
| Paper trading | Complete, shares the live code path |
| Live trading | Built; kill switch OFF; no strategy passes the promotion gate |
| Research layer | Complete and rigorous; the project's differentiator |
| Research result | All 11 strategies + 2 forward hypotheses rejected |
| Frontend | Visually complete, functionally a prototype (3 API calls) |
| Tests | 2,017 tests, 74% coverage (CI floor 72%), 0 failing |
| CI | None |
| Type/lint gates | Configured but unenforced; 50 mypy + 76 ruff errors |
| Documentation | Extensive but disorganised; README two quarters stale |
| Deployment | Live on Railway; Neon Postgres; Telegram alerting |

---

## 21. Open questions for the next planning step

These are genuine forks where the answer changes what gets built. They are stated
without a recommendation because they are the operator's to decide.

1. **What is this repository *for*?** A portfolio artifact optimised for a reviewer's
   first 10 minutes, and a live trading system optimised for capital safety, want
   different things. The readiness assessment assumes the former is now primary.

2. **Positioning.** The stated goal is AI engineering roles. The repository contains
   no ML and no LLM integration. Options: present it accurately as systems and
   research engineering (relevant to AI infrastructure), or add a genuine ML module.
   Relabelling existing heuristics as "AI" is not an option that survives review.

3. **Does research continue?** The pre-registered stop/pivot gate is 2026-12-01.
   Two mechanism classes are already eliminated for trending_bull. Continuing means
   sourcing hypotheses from genuinely different mechanism classes; stopping means
   the project's finding is the null result, written up well.

4. **Frontend: finish or reframe?** Wiring 6 pages to real data is 8-12 days. The
   alternative is to reframe the UI honestly as a design prototype and lead with the
   API and research layer. Both are defensible; shipping it silently as a working
   dashboard is not.

5. **How much history to publish?** The 35 `SESSION_*` files are a genuine record of
   how the system was built with AI assistance. Deleting them is the safe choice;
   curating one honest document about the AI-assisted workflow could be more
   interesting than hiding it. This is a judgment call about audience.

6. **PARA-03 through PARA-07 and PARA-11 remain open.** These are methodology
   defects in the research layer that partially undercut its own results. Fixing them
   strengthens the central claim; leaving them documented-and-open is at least honest.
   Publishing without either is the weakest option.

---

## Appendix A — Glossary

| Term | Meaning |
|---|---|
| **DSR** | Deflated Sharpe Ratio — Sharpe corrected for number of trials, skew, kurtosis |
| **Effective K** | Effective count of independent trials, used in the DSR correction |
| **PF** | Profit Factor — gross profit / gross loss |
| **PBO** | Probability of Backtest Overfitting |
| **WFO** | Walk-Forward Optimisation |
| **SubRegime** | Fine-grained 8-value market regime classification |
| **Tier A/B/C/D** | Promotion classification; D = reject, A = full deployment |
| **READY_FOR_LIVE** | Paper classification required before live activation |
| **PARA-nn** | Research-layer defect IDs from the 2026-05-28 self-audit |
| **DEC-YYYY-MM-DD-nnn** | Architectural decision IDs in DECISIONS.md |
| **H-YYYY-MM-nnn** | Hypothesis IDs in the forward research loop |
| **Fail closed** | On ambiguity or error, take the non-trading path |
| **Negative space** | Documented regions where edge has been proven absent |
| **Observe only** | A strategy collecting paper data but blocked from router activation |

## Appendix B — Key file anchors

| Concern | File |
|---|---|
| Main loop | `src/core/orchestrator.py` |
| Live capital model and gates | `scripts/run_live_trading.py` |
| Daily operator report | `scripts/validation_report.py` |
| Risk decisions | `src/core/risk/checks.py`, `circuit_breakers.py` |
| Order lifecycle | `src/core/execution/order_manager.py` |
| Data access | `src/data/store.py` |
| Backtest | `src/core/strategy/backtest/engine.py`, `trader.py`, `metrics.py` |
| Regime routing | `src/core/strategy/regime/router.py`, `historical_classifier.py` |
| DSR | `research/validation/deflated_sharpe.py` |
| Tier classification | `research/promotion/classifier.py` |
| Research method | `docs/research/RESEARCH_PROTOCOL.md` |
| Research plan | `docs/research/RESEARCH_LAYER_PRD.md` |
| Known research defects | `docs/research/RESEARCH_FIXLIST.md` |
| Proven-absent edge | `docs/research/NEGATIVE_SPACE_MAP.md` |
| The null result | `docs/research/retrospective/PORTFOLIO_SUMMARY_2026-06-05.md` |
| Decisions | `.claude/DECISIONS.md` (= `.agent/DECISIONS.md`) |
| Gaps and plan | `docs/PRODUCTION_READINESS_ASSESSMENT.md` |
