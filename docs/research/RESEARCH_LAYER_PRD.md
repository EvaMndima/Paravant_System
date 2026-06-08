# PARAVANT Research Layer — Product Requirements Document

**Status:** PROPOSED v2.0 (incorporates external critique, hybrid promotion model)
**Version:** 2.0
**Date:** 2026-06-04
**Previous Version:** v1.0 (2026-06-01) — superseded
**Owner:** Eva (operator/researcher) + Claude (implementation assistant)

**Related Documents:**
- `TRADING_SYSTEM_PRD.md` — parent PRD for the trading system
- `.claude/DECISIONS.md` / `.agent/DECISIONS.md` — architectural decision log
- `.claude/rules/zero-technical-debt.md` — code quality rules
- `.claude/rules/mvp-scope-control.md` — MVP scope boundaries
- `docs/research/RESEARCH_PROTOCOL.md` — current research protocol
- `docs/research/RESEARCH_FIXLIST.md` — PARA audit findings
- `docs/research/PORTFOLIO_LAYER_DESIGN.md` — portfolio capital model

**Changes from v1.0:**
- Compressed scope: "Research v0.5" milestone (3-4 weeks) replaces "MVP" as the first ship target
- Added: cost modeling and leakage detection as Phase 0 primitives
- Added: hybrid TIER A/B/C/D promotion model (replaces binary auto-promote)
- Added: DSR p-value as non-negotiable statistical floor
- Added: full-circle strategy lifecycle including post-mortem closure
- Added: decay-through-optimization workflow
- Added: explicit "which game" framing (provability + capital trajectory)
- Added: explicit stop/pivot gate with pre-registered criteria
- Fixed: multiple-testing math (removed homemade formula, DSR is the correction)
- Fixed: effective-K counting (parameter combos × symbols × timeframes, not just ledger entries)
- Fixed: BTF post-mortem framing (cost-blindness + thin sample, not pure selection bias)
- Demoted: V2/V3/Mature phases to Appendix D (conditional future capabilities)
- Deferred: paid alt-data to $25k+ capital threshold (not calendar date)
- Removed: capacity analysis (not relevant at retail scale)

---

## Table of Contents

1. Executive Summary
2. Why This Exists
3. Realistic Capability Framing
4. Explicit Non-Goals
5. Architecture
6. The Build Plan (Compressed)
7. Scope Tiers
8. Core Methodology Requirements
9. Hybrid Promotion Model
10. Strategy Lifecycle Pipeline (Full Circle)
11. Data Sources
12. Tools and CLIs
13. Cross-Cutting Capabilities
14. Success Metrics
15. Risks and Mitigations
16. Decision References
17. Glossary
18. Approval and Status

**Appendices:**
- A: Strategy Biography Schema
- B: Hypothesis Ledger Schema
- C: Post-Mortem Template
- D: Conditional Future Phases (R4-R8)
- E: Source Tier Rankings
- F: Phase Sequencing Visual

---

## 1. Executive Summary

This PRD defines the **PARAVANT Research Layer** — a research-grade extension to the existing trading system that turns ad-hoc strategy backtesting into a reproducible, statistically rigorous, institutional-methodology research pipeline with full-circle lifecycle tracking.

The research layer is **NOT** a separate project. It extends the existing repository as a top-level `research/` module with strict one-way dependencies on the production code under `src/`. It does **NOT** require advancing PARAVANT to V1 or V2 — the MVP scope rules (crypto-only, Binance-only, spot-long-only, market orders) remain locked. The research layer operates entirely upstream of live execution.

**The compressed roadmap**: Research v0.5 ships in 3-4 weeks with the safety primitives that prevent the most common failure modes (cost-blindness, lookahead, selection bias). Phases R1-R3 add the methodology backbone over months 2-4. **A pre-registered stop/pivot gate** at month 6 evaluates whether the approach is producing validated survivors. Conditional future phases (R4-R8) are in Appendix D, built only if earlier phases produce signal.

**The realistic goal** is NOT to replicate Renaissance Technologies. It is to build **the most rigorous, disciplined, well-instrumented solo crypto quant operation that retail constraints allow** — with audit-grade documentation that could support external capital if that path materializes, but operates equally well as personal infrastructure that scales with the operator's actual capital trajectory.

The Renaissance comparison serves only as a north-star calibration of methodology, not as a target outcome.

---

## 2. Why This Exists

### 2.1 The Problem

The PARAVANT trading system has matured to a production-quality MVP with rigorous live-execution discipline (kill switch, demotion guardrail, auto-promotion gate, decision audit trail). But the **research layer that feeds strategies into the system is ad-hoc**:

- Hypotheses are tested manually with no formal pre-registration
- No multiple-testing correction applied across strategies tested
- Walk-forward validation not enforced
- No Deflated Sharpe Ratio computation (Bailey/Lopez de Prado standard)
- **No per-symbol cost modeling** — transaction costs, spreads, and slippage are not properly modeled in backtests
- **No leakage detection** — backtest could be using future information
- No feature catalog — features re-implemented per strategy
- No alt-data integration (on-chain, funding rates, OI)
- No institutional memory beyond the audit log
- No calibration framework (pre-registered expectations vs actual results)
- No strategy decay monitoring beyond the demotion guardrail
- **No post-mortem completion** — retired strategies become dead weight instead of learning artifacts

The result is a research process that is structurally vulnerable to:
- **Cost-blindness**: backtest PF 1.5 collapses to live PF <1 because realistic costs were not modeled
- **Lookahead leakage**: backtest accidentally uses information unavailable at trade time
- **Selection bias**: testing many strategies, keeping winners, ignoring the multiple-testing burden
- **Thin-sample overfit**: Q1-only high-WR results that are statistical noise

The recently-retired BTF strategy (Q1 100% WR → live PF 0.75) likely failed from a combination of all four, not from any single cause.

### 2.2 The Opportunity

The methodology gap between retail and institutional quant research is the **most closeable gap** in the retail-vs-institutional comparison. The math is published and free. Deflated Sharpe ratio, walk-forward validation, conservative cost modeling, leakage detection — all are accessible to any disciplined practitioner. A retail trader who applies these methods operates at a methodological level higher than 99% of retail traders and matches small institutional shops.

The research layer's purpose is to **bake these methods into tooling** so they are not optional or memory-dependent. Once methodology is enforced by the system, the operator's job becomes idea generation, hypothesis quality, and judgment — the parts where human creativity actually matters.

### 2.3 Honest Framing

This document explicitly rejects the framing of "build AI that finds edges autonomously." That is not achievable, not for retail, not for institutional, not for Renaissance Technologies. What IS achievable is a system that:

- Tracks every hypothesis with cradle-to-grave audit
- Enforces statistical rigor mechanically
- Surfaces regime coverage gaps visually
- Catalogs failure modes so they are not repeated
- Calibrates the operator's hypothesis quality over time
- Integrates accessible alt-data sources
- Accelerates research throughput through tooling

That is institutional-grade methodology applied at retail scale. That is the target.

### 2.4 Which Game Are We Playing

At current capital scale ($20 paper, $100 live floor per DEC-2026-05-31-003), the research layer **cannot serve the trading PRD's "reliably generates income" mission on any near horizon**. Even a spectacular 50% annual return on $100 produces $50 — not income.

This PRD explicitly chooses a **hybrid framing** that the operator has confirmed:

1. **Build for provability**: rigorous, audited, honest-cost track record. Strategy biographies, decision logs, DSR-validated metrics. If the path opens to attract external capital (raise, prop allocation, licensing), the rigor IS the product.

2. **Build for the operator's actual future capital trajectory**: whatever capital materializes over the next 24 months from other sources (work, savings, business) finds a research-ready system waiting for it.

What this hybrid framing does NOT do:
- Promise near-term income (the math doesn't work at this capital)
- Frame the system as "preparing for a fundraise" (no fundraise is planned)
- Justify shortcuts on rigor ("it's only $100, doesn't matter") — the rigor is the asset
- Justify scope creep ("more features = more impressive") — provability values discipline over breadth

What it DOES:
- Every strategy biography is allocator-grade auditable
- Every promotion decision is documented with reasoning
- Every failure produces a post-mortem extractable as a learning artifact
- The system itself is the deliverable, durable independent of any specific strategy

---

## 3. Realistic Capability Framing

### 3.1 What This Layer CAN Match (Institutional Grade)

| Capability | Achievable Ceiling | Why |
|---|---|---|
| **Statistical methodology** | ~95% | The math is published. DSR, walk-forward, leakage detection — accessible to anyone with discipline. |
| **Backtest infrastructure** | ~85% | Software is cheap. CPU is cheap. Rolling backtest with regime tagging matches institutional rigor. |
| **Cost modeling** | ~80% | Per-symbol spread/fee/slippage models possible with available data. |
| **Strategy library** | ~80% | Same papers, blogs, Quantpedia entries as academic researchers. |
| **Research velocity** | ~70% | Disciplined solo + good tooling = 50+ ideas/year tested. |
| **Risk management** | ~90% | Position sizing, drawdown limits, kill switches all retail-accessible. |
| **Institutional memory** | ~80% | Hypothesis ledger + strategy biographies + post-mortems + decision log = institutional knowledge management. |

### 3.2 What This Layer CANNOT Match (Structural Retail Limits)

| Capability | Realistic Ceiling | Why |
|---|---|---|
| **Proprietary data** | ~5% | Renaissance has tick data back decades, satellite imagery, ship tracking, anonymized credit card data. Inaccessible. |
| **Co-location/latency** | ~5% | Microsecond latency requires exchange floor space. |
| **Prime brokerage** | 0% | Binance retail account vs JPMorgan PB with dark pool access. |
| **Human capital** | ~5% | 100+ PhDs in concert vs 1 operator + LLM assistant. LLM is a tool, not a colleague. |
| **Capital efficiency** | ~10% | They borrow at LIBOR+50bps. Retail crypto borrow costs are punitive. |
| **Information edge** | ~10% | Private datasets, expert networks, government policy contacts. Not retail-accessible. |
| **Internal market making** | 0% | Requires institutional capital + regulatory approval. |

### 3.3 The Achievable Ceiling

**Overall effective edge-generation capability vs institutional grade: approximately 25-30%.**

This sounds low until calibrated against the relevant competitive set:
- You are NOT competing against Renaissance Technologies. They operate in a different size class.
- You ARE competing against other retail traders, the majority of whom are completely undisciplined.
- The marginal retail trader has approximately 0% systematic edge.
- Methodology + discipline alone places you in the top 5% of retail.

**Realistic outcome distribution** (over 2-year horizon, solo retail crypto, $100-$10,000 starting capital):

- **Top 5% retail outcome**: 5-10 statistically-validated strategies in live deployment, 15-40% annualized returns with controlled drawdowns, methodology genuinely matching institutional standards.
- **Median outcome**: 2-3 working strategies, 5-20% annualized returns with bigger drawdowns, capital preserved, significant domain expertise built.
- **Pessimistic outcome**: 0-1 working strategy, -10% to +5% annualized, capital preserved (the most important outcome), substantial learning foundation for future iteration.

### 3.4 The Sample-Size Constraint (Binding Constraint at Small Scale)

**This is the binding constraint at current scale and the most important honest framing in this section.**

At $100-$10,000 capital trading 4H/1D timeframes on a handful of symbols:
- Each strategy generates ~12 trades per quarter
- Reaching N=30 takes 7-8 months per strategy
- DSR confidence intervals at N=47 are enormous
- Statistics cannot manufacture signal from thin samples

Implications baked into this PRD:
- **Hypothesis prioritization biases toward strategies that produce more trades** (more symbols, more entries, lower timeframes within reason)
- **All metrics carry confidence intervals**, not point estimates
- **No conclusion is treated as final** at N<100 across regimes
- **Position sizing accounts for uncertainty**, not just expected return
- **The number of independent bets is the binding constraint**, not methodology sophistication — and no methodology can fix this

CPCV (Combinatorial Purged CV) reveals instability at small N but does NOT create statistical power. Nothing fixes too-few-independent-bets except more bets. The system acknowledges this and structures research accordingly.

---

## 4. Explicit Non-Goals

This section is as important as the in-scope section. These are capabilities the research layer **explicitly will not pursue**, either because they are structurally inaccessible to retail or because the academic literature is clear that they do not produce sustainable edge.

### 4.1 Permanent Non-Goals (Structural)

| Non-Goal | Why |
|---|---|
| **Price-direction ML models** | The financial ML literature is increasingly clear that pure price prediction does not produce sustained edge. Random walk component dominates. LSTM/Transformer on OHLCV almost always overfits. |
| **Deep reinforcement learning agents** | RL agents trained on backtests fail catastrophically in production. Academic exercise only. |
| **Auto-discovered strategies (no human in the loop)** | Strategies discovered without human hypothesis generation produce spurious correlations. |
| **HFT / microstructure strategies** | Retail latency makes the system structurally uncompetitive. |
| **Tick-data infrastructure** | Storage and processing cost prohibitive. Marginal value over OHLCV at our timeframes. |
| **Proprietary alt-data licensing** | Institutional alt-data costs five to seven figures per year. Out of structural reach. |
| **Co-location at exchanges** | Microsecond latency requires renting exchange data center space. |
| **Internal market making** | Requires institutional capital + regulatory approval. |
| **Capacity analysis (size-driven slippage modeling)** | Not relevant at $100-$10k account size. You cannot move BTCUSDT enough to matter. Defer until capital ≥ $25k. |

### 4.2 Deferred Non-Goals (Not in MVP, may revisit later)

| Deferred | Until | Why |
|---|---|---|
| Multi-broker support | V1 of trading system | Locked decision DEC-2026-01-15-002 |
| Other asset classes (stocks, forex) | V1 of trading system | Locked decision DEC-2026-01-15-001 |
| Limit orders | V1 of trading system | Locked decision DEC-2026-01-15-004 |
| WebSocket real-time data | V2 of trading system | Polling sufficient for current strategies |
| Live futures execution | Step 4 of DEC-2026-05-28-001 | Research-layer futures backtest already permitted |
| Paid alt-data (Glassnode, CryptoQuant) | Capital ≥ $25,000 | Subscription cost ($816/year) mathematically cannot pay back at sub-$25k capital |

### 4.3 Aspirational Research-Only Capabilities

The following may be researched as intellectual exercises but will NOT enter live deployment without explicit unlocking via a new locked-decision review:

- Statistical arbitrage research (cross-exchange basis trades)
- Term-structure research (futures basis trades)
- Cross-asset correlation studies (BTC dominance regimes)
- Volatility surface modeling

---

## 5. Architecture

### 5.1 Directory Structure

```
paravant_system/
├── src/                            # Production code (existing, unchanged)
│   ├── core/strategy/generators/   # Production strategy code
│   ├── core/strategy/regime/       # SubRegime detector (shared truth)
│   └── ...
├── research/                       # NEW — Research Layer
│   ├── __init__.py
│   ├── hypotheses/                 # Hypothesis ledger + lifecycle
│   │   ├── ledger.yaml             # All hypotheses, statuses, results
│   │   └── lifecycle.py            # State machine for hypothesis status
│   ├── biographies/                # NEW — Strategy biographies (full circle)
│   │   ├── active/                 # Currently active strategies
│   │   ├── retired/                # Retired strategies with post-mortems
│   │   └── schema.py               # Biography data structure
│   ├── features/                   # Feature factory
│   │   ├── catalog.yaml            # Feature metadata
│   │   ├── library/                # Standard feature implementations
│   │   └── dag.py                  # Feature dependency graph
│   ├── backtest/                   # Research backtest extensions
│   │   ├── walk_forward.py         # Walk-forward harness
│   │   ├── multi_window.py         # Multi-window rolling
│   │   ├── cost_model.py           # NEW — Per-symbol cost modeling
│   │   └── leakage_check.py        # NEW — Lookahead detection
│   ├── optimization/               # Parameter optimization
│   │   ├── grid.py                 # Grid search with walk-forward
│   │   ├── bayesian.py             # Optuna-backed Bayesian opt
│   │   └── robust_zones.py         # Robust-zone identification
│   ├── validation/                 # Statistical validation
│   │   ├── deflated_sharpe.py      # Bailey/Lopez de Prado DSR
│   │   ├── effective_k.py          # Proper K counting
│   │   ├── cpcv.py                 # Combinatorial Purged CV (deferred)
│   │   ├── reality_check.py        # White's Reality Check (deferred)
│   │   └── pbo.py                  # Probability of Backtest Overfitting
│   ├── data/                       # Data adapters
│   │   ├── funding_rates.py        # Binance futures funding (free)
│   │   └── open_interest.py        # OI data (free)
│   ├── promotion/                  # NEW — Tier-based promotion
│   │   ├── classifier.py           # TIER A/B/C/D classification
│   │   ├── floors.py               # Non-negotiable statistical floors
│   │   └── operator_review.py      # Tier B review interface
│   ├── decay/                      # NEW — Decay-through-optimization
│   │   ├── detection.py            # Decay event detection
│   │   ├── diagnosis.py            # Auto-diagnosis of decay cause
│   │   └── reoptimization.py       # Re-optimization workflow
│   ├── reporting/                  # Research reports
│   │   ├── strategy_card.py        # Strategy biography rendering
│   │   ├── post_mortem.py          # Post-mortem template + generation
│   │   └── calibration.py          # Pre-reg vs actual tracking
│   ├── notebooks/                  # Exploratory Jupyter notebooks (R6+)
│   ├── catalog/                    # Strategy/feature/result catalog
│   │   ├── strategies.yaml         # Auto-discovered registry
│   │   ├── results/                # Per-hypothesis markdown reports
│   │   └── post_mortems/           # Failure analyses (full circle closure)
│   └── generators/                 # Research-stage strategy code
│       └── <strategy_name>.py      # Promoted to src/ once validated
├── scripts/                        # CLI tools
│   ├── eval_research_strategy.py   # Phase R0 main CLI
│   ├── retrospective_dsr.py        # NEW — Run DSR on existing strategies
│   ├── sweep_params.py             # Phase R3 optimization CLI
│   ├── promote_to_production.py    # Research → src/ promotion
│   ├── classify_strategy.py        # NEW — Tier A/B/C/D classification
│   ├── generate_post_mortem.py     # NEW — Post-mortem generation
│   └── ...
├── tests/
│   ├── unit/                       # Production code tests (strict)
│   └── research/                   # Research code tests
├── requirements.txt                # Production deps
├── requirements-research.txt       # Research-only deps (sklearn, scipy, optuna, statsmodels)
```

### 5.2 Dependency Rules (CRITICAL)

**Rule**: `src/` does **NOT** import from `research/`. `research/` imports from `src/` freely.

This is a one-way dependency, enforced at import-graph review. If production code is ever caught importing from `research/`, it is a bug to be fixed immediately.

Rationale:
- Production code must be stable, audited, zero-tech-debt
- Research code is intentionally more exploratory
- One-way dependency means research can evolve without destabilizing production
- Strategies graduate from research to production by moving the file, not by adding cross-imports

### 5.3 Integration With Existing System

The research layer reuses existing production infrastructure:

| Existing | Used By Research For |
|---|---|
| `src/core/data/` (Binance data fetchers) | Historical OHLCV |
| `src/core/strategy/regime/` (SubRegime detector) | Regime tagging — same truth source as live |
| `src/core/strategy/generators/` (base classes) | Strategy generator framework |
| `src/core/backtest/backtest_rolling.py` | Underlying backtest engine |
| `STRATEGY_CONFIG` | Production strategy registry (research reads, never writes) |
| `.claude/DECISIONS.md` / `.agent/DECISIONS.md` | Decision audit |
| `validation_report` infrastructure | Paper-trading classification helpers |
| Auto-promotion gate (DEC-2026-06-01-001/002) | Trading-system-side promotion (extended by Tier system) |

### 5.4 Database Schema

Research adds tables with `research_` prefix:

| Table | Purpose |
|---|---|
| `research_hypotheses` | Hypothesis ledger entries (mirrors `ledger.yaml`) |
| `research_biographies` | Strategy biographies (full lifecycle records) |
| `research_results` | Backtest results linked to hypotheses |
| `research_features` | Feature catalog metadata |
| `research_calibration` | Pre-registered expectations vs actual outcomes |
| `research_post_mortems` | Failure analyses |
| `research_decay_events` | Strategy decay observations |
| `research_reoptimizations` | Re-optimization attempts and outcomes |
| `research_classifications` | TIER A/B/C/D classifications with timestamps |

YAML files in `research/` directory remain the human-editable canonical source. Database tables are projections for querying. A sync script keeps them aligned.

### 5.5 Dependencies

`requirements-research.txt` adds packages NOT permitted in production code:

```
scipy>=1.11
statsmodels>=0.14
scikit-learn>=1.3
optuna>=3.4
arch>=6.2              # for GARCH and tail-risk modeling
PyYAML>=6.0
jupyter>=1.0           # R6+
matplotlib>=3.8
seaborn>=0.13
plotly>=5.18           # interactive sensitivity plots
```

Installed with: `pip install -r requirements-research.txt`

Production CI continues to install only `requirements.txt` — research deps never touch production deployment.

---

## 6. The Build Plan (Compressed)

The previous version's 30-week, 8-phase roadmap is replaced with a compressed Research v0.5 milestone followed by phases gated on outcomes.

### 6.1 Research v0.5 — Foundation + Safety (Weeks 1-4)

**Goal**: Ship the minimum viable research workflow PLUS the safety primitives that prevent the most common failure modes. Operator productive on day one; first hypotheses through the pipeline by end of week 4.

**This is what we build first. Everything after this is conditional on v0.5 producing signal.**

**Deliverables**:

Foundation:
- `research/` directory scaffold
- `research/hypotheses/ledger.yaml` schema + 3 seed hypotheses
- `research/biographies/` schema for strategy biographies
- `research/catalog/strategies.yaml` (auto-discovered registry)
- `requirements-research.txt`

Methodology core (4 primitives):
- `research/backtest/cost_model.py` — **per-symbol cost modeling** (spread + fee + slippage), conservative defaults using 95th percentile historical spread
- `research/backtest/leakage_check.py` — **lookahead detection** (future timestamps in features, survivor bias, etc.)
- `research/backtest/walk_forward.py` — walk-forward harness
- `research/validation/deflated_sharpe.py` — DSR with proper effective-K counting

Promotion infrastructure:
- `research/promotion/classifier.py` — TIER A/B/C/D classification
- `research/promotion/floors.py` — non-negotiable statistical floors (DSR p<0.3, MaxDD<10%)

CLIs:
- `scripts/retrospective_dsr.py` — **APPLY DSR TO EXISTING KEEP STRATEGIES FIRST** (highest-information first action)
- `scripts/eval_research_strategy.py` — full evaluation pipeline
- `scripts/classify_strategy.py` — generate Tier classification report

Documentation:
- `docs/research/READING_QUEUE.md` (source tier rankings)
- Pre-registered "verified cost model" criteria (see Section 14.2)
- Pre-registered stop/pivot gate (see Section 14.2)

**Operator capability after v0.5**:
1. Run retrospective DSR on existing 5 KEEP strategies (days of work, not weeks)
2. Read source → write hypothesis YAML → implement generator → run CLI → get Tier A/B/C/D verdict → log in ledger
3. Every backtest accounts for realistic per-symbol costs
4. Every backtest checked for leakage

**Critical first action (week 1, days 1-3)**:
Apply DSR + honest cost model retroactively to the existing 5 KEEP strategies (MACD_PB, BTP, VBB, SRC, ICVP). **This costs almost nothing and could reveal that 2-3 of the 5 are statistical noise BEFORE any capital is risked.** No other action in this PRD has a higher ratio of information value to effort.

### 6.2 Phase R1 — Statistical Rigor Polish (Weeks 5-8)

**Goal**: Round out the methodology toolkit with PBO and pre-registration enforcement.

**Deliverables**:
- `research/validation/pbo.py` — Probability of Backtest Overfitting
- Pre-registration enforcement at CLI level (refuses to evaluate if `expected_pf`/`expected_sharpe` missing)
- Calibration tracking: pre-reg vs actual delta per hypothesis
- Effective K calculation refined (parameter combos × symbols × timeframes properly counted)

### 6.3 Phase R2 — Feature Engineering (Weeks 9-12)

**Goal**: Feature factory with catalog and per-feature backtesting.

**Deliverables**:
- `research/features/catalog.yaml` — searchable feature registry
- `research/features/library/` — standard implementations (technical indicators, volume profile, statistical features)
- `research/features/dag.py` — dependency graph
- `scripts/eval_feature.py` for testing single signals
- Feature correlation matrix generator

### 6.4 Phase R3 — Optimization (Weeks 13-16)

**Goal**: Real optimization with overfit prevention baked in.

**Deliverables**:
- `research/optimization/grid.py` — walk-forward grid search
- `research/optimization/bayesian.py` — Optuna-backed Bayesian optimization
- `research/optimization/robust_zones.py` — robust parameter region identification
- Sensitivity analysis plots
- `scripts/sweep_params.py` CLI

### 6.5 Phase R3.5 — Decay Workflow (Schema in v0.5, Automated Engine Conditional)

**Decision baked in 2026-06-04 per external review**: The automated decay engine is DEFERRED from the originally-scheduled weeks 17-18 to NEED-DRIVEN activation. We have zero live strategies at v0.5 ship — cannot validate a decay-detection-diagnosis-reoptimization subsystem against a problem that does not yet exist.

**v0.5 (Weeks 1-4) includes** (cheap discipline):
- Biography schema captures decay events as data (`research/biographies/schema.py` includes `decay_events` and `reoptimization_history` fields)
- Operators can manually log decay events and re-optimization attempts in biographies
- Post-mortem TEMPLATE defined (Appendix C); generation is initially manual

**Conditional — triggered when first live strategy shows decay, NOT calendar-scheduled**:
- `research/decay/detection.py` — automated rolling PF degradation detection
- `research/decay/diagnosis.py` — automated regime-shift vs parameter-drift classification
- `research/decay/reoptimization.py` — automated re-optimization workflow
- `scripts/generate_post_mortem.py` — automated post-mortem generation

**Why deferred**: Building automated decay detection now is tooling for a problem that won't exist until ~month 8 — exactly the over-building instinct the PRD warns against (Section 15.1). Manual biography updates cover the institutional-memory function at v0.5. Automation is justified by an actual decay event, not by a calendar.

### 6.6 Pivot/Stop Gate (End of Week 24, ~Month 6)

See Section 14.2 for full pre-registered criteria. Summary:

- **After 20 hypotheses tested with verified cost model + leakage checks pass, if zero have survived DSR (p<0.3), STOP and reassess.**
- **Hard date**: 2026-12-01. Failures count after this date regardless of methodology validation status.

This protects against the "never finish building" trap — building tooling forever while producing zero validated strategies.

### 6.7 Conditional Future Phases (R4-R8)

**These are in Appendix D, not the spine of this PRD.**

Build only if the v0.5 + R1-R3 funnel produces at least one validated survivor by the stop/pivot gate. If no survivors, the conditional phases are not built — instead, reassess whether the entire approach has structural issues.

If survivors exist, the conditional roadmap covers: alt-data integration, advanced validation (CPCV, Reality Check), notebook environment, source ingestion pipeline, polish + knowledge management.

---

## 7. Scope Tiers

The scope tiers from PRD v1.0 are restructured:

### MVP — Research v0.5 + R1-R3.5 (Months 1-4)

**In Scope**: Foundation + cost modeling + leakage detection + DSR + walk-forward + PBO + feature factory + optimization + decay workflow + tier-based promotion + strategy biographies + post-mortem closure.

**Operator gains**:
- 10x research throughput vs current ad-hoc workflow
- Methodology genuinely matching institutional standards on the parts that matter most
- Cost-realistic backtests
- Leakage-protected evaluations
- Full-circle strategy lifecycle tracking
- Audit-grade documentation (provability path)

**What MVP does NOT include**: Paid alt-data, CPCV, notebook environment, source ingestion automation, LLM-assisted hypothesis generation.

**Success metric** (see Section 14): At least 1 strategy validated through full pipeline with DSR p<0.2 by stop/pivot gate.

### Conditional Future Tiers

See Appendix D. Each is gated on the previous tier producing validated survivors.

---

## 8. Core Methodology Requirements

These are mandatory primitives that ALL strategy evaluation must use. They are not optional. They are enforced by `eval_research_strategy.py`.

### 8.0 Pre-DSR Quality Gate (precedes everything below)

**Added 2026-06-08 — DEC-2026-06-04-018. Full checklist: `docs/research/HYPOTHESIS_QUALITY_GATE.md`.**

A reasoning-quality gate sits UPSTREAM of DSR so a DSR trial is spent only on theoretically-sound, feasible, non-duplicate hypotheses. DSR is the EVIDENCE gate and it deflates by effective K, so every idea tested raises the bar for every survivor — the gate keeps research in confirmation mode (theory first), not search/data-mining mode. Three stages:

- **Stage 1 — reasoning scorecard (no data):** hard gates (mechanism stated; falsifiable fail modes; sample-size feasibility; not a known-dead graveyard pattern) plus scored dimensions (mechanism strength, inverse-crowding, crypto-native fit, regime specificity, parameter parsimony, diversity, source credibility). Most ideas die here, cheaply, with no DSR trial spent.
- **Stage 2 — blind structural feasibility profile (optional; data but NO performance):** confirm it runs, trade count adequate, holding-period/turnover/per-regime coverage sane — reporting structure ONLY.
- **Stage 3 — DSR** (8.1-8.9 below), the unchanged evidence gate.

Failures are tagged FUNDAMENTAL (never revisit) vs FIXABLE (diagnosable near-miss = seedbed for a corrected hypothesis); a mechanism x regime coverage map directs sourcing at the unexplored complement.

**Two hard lines (non-negotiable):** (1) no performance peek before DSR — pre-DSR data checks are STRUCTURAL only; computing/showing PF/Sharpe/returns pre-DSR irreversibly biases the test. (2) No algorithmic strategy generation from failures — failures steer HUMAN mechanism choice, never a spec-generator (the DEC-2026-06-04-006 auto-discovery non-goal).

Sequencing: adopted NOW as a by-hand checklist; automated tooling DEFERRED until the rubric proves which dimensions discriminate and that triage is the bottleneck.

### 8.1 Pre-Registration

Every hypothesis MUST declare BEFORE backtest:
- Expected profit factor (`expected_pf`)
- Expected Sharpe ratio (`expected_sharpe`)
- Expected regime fit (which SubRegime)
- Expected fail modes (what would cause this to fail?)
- Parameter ranges to test

The evaluation CLI refuses to run if pre-registration fields are missing.

**Why**: Pre-registration eliminates the "I knew it would work" bias. If actual results dramatically exceed pre-registration (e.g., PF 3.0 vs expected 1.5), that is a RED FLAG (likely overfit or leakage), not a green light.

### 8.2 Per-Symbol Cost Modeling

**This is THE most likely cause of historical backtest-to-live degradation in this system.** Treated as a first-class methodology primitive in v0.5.

Components:
- **Spread**: per-symbol historical spread, use 95th percentile (conservative)
- **Fee**: Binance spot taker 0.1% (0.075% with BNB if applicable)
- **Slippage**: per-symbol historical slippage from existing execution data
- **Round-trip cost**: entry + exit costs both modeled

Validation:
- Cost model "verified" only when validated against at least 10 real paper-trading fills per symbol
- Until verified, costs default to **double the calculated estimate** (extra-conservative)
- Cost model versions tracked; backtests linked to cost model version

Why critical: on a strategy with 2.8% average wins and 1.4% average losses, a 0.5% round-trip cost flips PF from 1.5 to <1.0. Backtest results without honest cost modeling are systematically optimistic.

### 8.3 Leakage Detection

Checks for common lookahead-bias patterns:
- Future timestamps in feature lookback windows
- Features computed using bars not available at trade decision time
- Survivor bias in symbol universe (only symbols that still exist tested)
- Restatement bias in fundamental/on-chain data (revised values used instead of as-known-at-time)
- Index reconstitution effects (asset added to index after price moved)

CLI refuses to evaluate if leakage check not passed.

### 8.4 Walk-Forward Validation

For ANY parameter optimization, walk-forward is mandatory:
- Train on rolling 6-month window
- Test on next 1-month window (out-of-sample)
- Slide forward, repeat
- Aggregate test-window results — those are the honest performance

The optimizer NEVER sees the test data during parameter selection.

**Why**: Single-window optimization on full history is the #1 cause of overfit. Walk-forward eliminates this by structure.

### 8.5 Deflated Sharpe Ratio (DSR)

**This is the non-negotiable statistical floor for all promotion decisions. See Section 9 for how this binds.**

Bailey/Lopez de Prado 2014 formula. Adjusts observed Sharpe for:
1. Selection bias from effective number of trials (proper K)
2. Higher moments of return distribution (skew, kurtosis)
3. Sample size

Returns the probability that the true Sharpe > 0. A strategy with observed Sharpe 1.5 but DSR p-value 0.4 means there is only a 60% probability the edge is real — not a green light.

**Effective K counting** (corrected from PRD v1.0):
```
effective_K = total_hypotheses_ledger * parameter_combinations_per_hypothesis * symbols_tested * timeframes_tested
```

A grid search of 100 parameter combos × 5 symbols × 3 timeframes = 1,500 effective trials per hypothesis, not 1. The PRD v1.0 undercounted this by 2-3 orders of magnitude. Fixed in v2.0.

**Why DSR is the floor**: every other metric (PF, Sharpe, MaxDD) can produce binary thresholds where a strategy at 1.34 PF is treated categorically differently from 1.36 PF — but these are statistically indistinguishable. DSR encodes the probability that the edge is real, not a binary pass/fail. It's the right tool for a non-binary decision.

### 8.6 Combinatorial Purged Cross-Validation (CPCV) — DEFERRED

Lopez de Prado 2018. Proper cross-validation for time-series with overlapping samples.

**Honest caveat**: CPCV reveals instability across reused samples but does NOT create statistical power. At small N, after purging overlapping samples, each test fold can shrink to a handful of trades. CPCV is a diagnostic tool, not a small-sample fix.

**Status**: Deferred to conditional future phase. Build when there is a survivor worth subjecting to it. Do NOT sell internally as solving the small-sample problem — nothing fixes too-few-independent-bets except more bets.

### 8.7 Statistical Significance Testing — DEFERRED

White's Reality Check or Hansen's SPA test. Deferred to conditional future phase.

### 8.8 Probability of Backtest Overfitting (PBO)

Bailey/Lopez de Prado. Built in Phase R1. PBO > 0.5 means the strategy's apparent edge is more likely overfitting than real signal — reject regardless of other metrics.

### 8.9 The Removed Item: Homemade Multiple-Testing Formula

PRD v1.0 had:
```
adjusted_pf_threshold = base_pf_threshold * (1 + 0.05 * ln(K))
```

**This is removed.** It was not Bonferroni-equivalent and the 0.05 coefficient was arbitrary. DSR already incorporates selection bias correctly via effective K. Carrying both was redundant; keeping only DSR is correct.

---

## 9. Hybrid Promotion Model

**This is the most significant architectural addition in v2.0.** It replaces the previous binary auto-promotion gate with a graduated tier system that preserves rigor while acknowledging that markets are not binary.

### 9.1 The Tier System (A/B/C/D)

Every backtested strategy receives a Tier classification based on objective criteria:

| Tier | Name | Hard Floor | Soft Thresholds | Action | Capital Allocation |
|---|---|---|---|---|---|
| **A** | FULL_READY | DSR p<0.2, MaxDD<5% | PF≥1.35, Sharpe≥1.0, N≥30 | System recommends deployment | 100% of per-strategy slice |
| **B** | PROVISIONAL_READY | DSR p<0.3, MaxDD<5% | PF≥1.25, Sharpe≥0.8, N≥20 | System recommends reduced-capital deployment | 50% of per-strategy slice |
| **C** | NEEDS_WORK | DSR p<0.5, MaxDD<10% | Multiple soft thresholds missed | Cannot deploy — needs more data or re-optimization | 0% |
| **D** | REJECT | DSR p≥0.5 OR MaxDD≥10% | N/A | Auto-shelved | 0% |

**Classification is mechanical, based on objective criteria. There is no manual override.**

### 9.2 Hard Floors (Non-Negotiable)

The following floors apply to ALL tiers. A strategy that violates any hard floor cannot be promoted at ANY allocation, regardless of any other consideration:

1. **DSR p-value < 0.3** (statistical edge must have ≥70% probability of being real)
2. **MaxDD < 5%** for TIER A and B, < 10% absolute maximum for TIER C consideration
3. **Cost model verified** (no deployment from un-verified cost backtests)
4. **Leakage check passed** (no deployment if leakage detected)
5. **Effective K accounted for** in DSR calculation

**These floors are the line that separates "graduated rigor" from "human override defeats rigor." They cannot be relaxed without an explicit PRD update and decision-log entry.**

### 9.3 Tier A: FULL_READY

A strategy classifies as Tier A when ALL of:
- DSR p-value < 0.2 (80% probability edge is real)
- MaxDD < 5%
- PF ≥ 1.35
- Sharpe ≥ 1.0
- N ≥ 30 trades
- Cost model verified
- Leakage check passed
- PBO < 0.5

**System action**: Notification — "Strategy X is FULL_READY. Review biography and click DEPLOY to allocate at full capacity."

**Operator action**: Per Decision B (opt-in deployment), explicit operator click required to deploy live. System does NOT auto-deploy.

**Capital allocation on deployment**: 100% of per-strategy slice (per DEC-2026-05-31-003 portfolio capital model).

### 9.4 Tier B: PROVISIONAL_READY

A strategy classifies as Tier B when:
- DSR p-value < 0.3 (still passing the statistical floor)
- MaxDD < 5%
- Critical metrics pass at relaxed thresholds:
  - PF ≥ 1.25 (relaxed from 1.35)
  - Sharpe ≥ 0.8 (relaxed from 1.0)
  - N ≥ 20 (relaxed from 30 — this is the most common reason for Tier B vs A)
- Cost model verified
- Leakage check passed

**System action**: Notification — "Strategy X is PROVISIONAL_READY. Review biography and click DEPLOY for reduced-capital allocation."

**Operator action**: Review the strategy's biography (Section 13.4) before deploying. Click DEPLOY to allocate at REDUCED capacity.

**Capital allocation on deployment**: **50% of per-strategy slice**. This is the recognition that "almost-passing" metrics deserve smaller bets, not zero bets.

**Why Tier B exists**: A strategy with N=20 but excellent metrics + clean DSR is statistically distinguishable from a strategy with N=20 and poor metrics. Treating them identically (both rejected because N<30) is the methodology error the operator correctly identified. Tier B addresses this by deploying smaller, not by waiving criteria.

**Tier B safeguards** (preventing methodology theater):
- DSR p<0.3 is non-negotiable (still must pass statistical floor)
- Reduced capital means smaller losses if Tier B strategies underperform
- Operator-deployment decisions tracked separately in calibration framework
- Quarterly review: are Tier B deployments performing worse than Tier A? If yes, tighten Tier B criteria.

**Honest note on Tier B as modal year-1 deployment** (baked in 2026-06-04 per external review): Given the system produces ~12 trades per quarter at 4H/1D timeframes (Section 3.4), most year-1 deployments will be Tier B, NOT Tier A. Tier A (N≥30) requires 7-8 months of paper accumulation per strategy; Tier B (N≥20) is reachable in ~5 months. The "most live capital runs on N=20-29 strategies at 50% slice" framing IS the year-1 steady state — Tier A is the exception, not the norm. The N≥20 floor (raised from initial N≥15 proposal per external review 2026-06-04) hedges against DSR's reduced reliability at very small N: below N≈20, skew and kurtosis estimates that DSR depends on become structurally unmeasurable, weakening "DSR p<0.3" as evidence. N≥20 + 50% slice + DSR p<0.3 is the conscious modal deployment posture for year 1.

### 9.5 Tier C: NEEDS_WORK

A strategy classifies as Tier C when:
- DSR p-value 0.3-0.5 (insufficient evidence of real edge)
- OR multiple soft thresholds missed
- OR MaxDD 5-10% (acceptable for further work but not deployment)

**System action**: Notification — "Strategy X is NEEDS_WORK. Options: gather more data (run longer paper trading), re-optimize parameters, or shelve."

**Operator action**: Cannot deploy. Must either improve the strategy or shelve it.

**Capital allocation**: 0%.

### 9.6 Tier D: REJECT

A strategy classifies as Tier D when:
- DSR p-value ≥ 0.5 (≥50% probability the apparent edge is luck) — strategy is statistical noise
- OR MaxDD ≥ 10% — unacceptable risk
- OR leakage detected — backtest is invalid
- OR PBO > 0.5 — strategy is structurally overfit

**System action**: Auto-shelved. Post-mortem generated. Added to research/biographies/retired/.

**Operator action**: None required. Strategy added to graveyard with documented reasons.

### 9.7 Opt-In Deployment

**Per Decision B confirmed by operator on 2026-06-04**: All deployments require explicit operator action. System NEVER auto-deploys.

This honors the trading PRD's locked decision (Section 1.7: "Autonomy model: Human approval for live deployment") and overrides the previous opt-out behavior of DEC-2026-06-01-001.

**Updated promotion flow**:
1. System classifies strategy (Tier A/B/C/D)
2. System sends notification with classification and biography link
3. Operator reviews biography
4. Operator clicks DEPLOY (or chooses not to)
5. If DEPLOY: capital allocation per tier (100% Tier A, 50% Tier B)
6. Decision logged with reasoning

**DEC-2026-06-01-001 needs update** to reflect this — the auto-promotion gate now NOTIFIES rather than auto-deploys.

### 9.8 Trading PRD Integration

The auto-promotion gate from the trading system (DEC-2026-06-01-001/002) becomes the **classification layer** of the Tier system. DSR is layered ON TOP of the existing gates, not beside them.

Updated promotion criteria reconciled with trading PRD:

| Old (trading PRD) | New (with research layer Tier system) |
|---|---|
| N≥30, PF≥1.35, Sharpe≥1.0, MaxDD≤5% | Tier A criteria (all above + DSR p<0.2 + cost verified + leakage clean) |
| "Operator must override to NOT deploy" | "Operator must click DEPLOY (opt-in)" |
| Binary pass/fail | Tier A/B/C/D classification |
| No DSR | DSR p<0.3 is the floor for any deployment |
| No cost verification | Cost model verified is the floor |

This change requires updates to: `scripts/run_live_trading.py` (`_paper_strategy_classification` and `_tier1_activation_blocked`), `validation_report`, and DEC-2026-06-01-001/002.

### 9.9 N Source for Tier Classification (Backtest vs Live)

**Decision baked in 2026-06-04 per external review**: Tier classification uses BACKTEST N as the primary signal at Stage 7. Live performance never re-tiers a strategy UPWARD; downward movement only via the decay guardrail (Stage 10).

Rationale:
- Stage 7 (classification) precedes Stage 8 (paper) and Stage 9 (live) — so backtest N is the only N available at classification time
- A strategy classifies Tier A on backtest N=54 then deploys with live N=3; this is acknowledged and acceptable
- Backtest N is also "few independent bets" at 2 years of 4H/1D data — be honest that Tier A on backtest N=47 carries less weight than the name "FULL_READY" suggests
- Live performance ALWAYS counts via the decay guardrail (Stage 10), but only in the demotion direction — a strategy can fall in tier or retire from live data, never rise in tier from live data alone

This is intentional: the tier represents validated edge at classification time; live performance either confirms (continued deployment) or contradicts (decay → re-opt or retire). Re-classifying upward from live trades would defeat the discipline of the gate.

The Section 3.4 framing ("N=30 takes 7-8 months") refers to LIVE accumulation, a different number than backtest N used for tier classification. These must not be conflated.

---

## 10. Strategy Lifecycle Pipeline (Full Circle)

Every strategy traverses an 11-stage pipeline. The pipeline is a CIRCLE — failed strategies feed lessons back into future hypothesis generation via post-mortems.

```
                              ┌─────────────────────┐
                              │  STAGE 1: SOURCING  │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 2: HYPOTHESIS│
                              │   FORMALIZATION     │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 3:           │
                              │  IMPLEMENTATION     │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 4: COST +    │
                              │  LEAKAGE CHECK      │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 5: ROBUSTNESS│
                              │  TESTING            │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 6:           │
                              │  OPTIMIZATION       │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 7: STAT      │
                              │  VALIDATION + TIER  │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 8: PROMOTION │
                              │  TO PAPER           │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 9: LIVE      │
                              │  DEPLOYMENT         │
                              └──────────┬──────────┘
                                         ↓
                              ┌─────────────────────┐
                              │  STAGE 10: DECAY    │
                              │  → RE-OPT or RETIRE │
                              └─────┬─────────┬─────┘
                                    ↓         ↓
                              [Re-optimize]  [Retire]
                                    ↓         ↓
                                back to ┌──────────────────┐
                                stage 5 │ STAGE 11:        │
                                        │ POST-MORTEM      │
                                        │ (closes circle)  │
                                        └────────┬─────────┘
                                                 ↓
                                    Feeds into Stage 1
                                    of future hypotheses
                                    via pattern matching
```

### Stage-by-Stage Detail

**Stage 1: Sourcing**
- Input: External sources (papers, blogs, on-chain reports, post-mortems from previous strategies)
- Output: Raw idea text
- Tooling: Reading queue + (V2+) source ingestion pipeline

**Stage 2: Hypothesis Formalization**
- Input: Raw idea
- Output: Structured hypothesis YAML in ledger
- Gate: Pre-registration fields complete (expected_pf, expected_sharpe, regime_target, fail_modes)

**Stage 3: Implementation**
- Input: Hypothesis YAML
- Output: `research/generators/<name>.py` (inherits BaseGenerator)
- Gate: Generator passes unit tests, type-checks

**Stage 4: Cost + Leakage Check**
- Input: Generator code + backtest specification
- Output: Cost-model applied, leakage check passed
- Gate: Cost model must be verified OR cost defaults to 2x estimate. Leakage check must return CLEAN.
- Tooling: `research/backtest/cost_model.py`, `research/backtest/leakage_check.py`

**Stage 5: Robustness Testing**
- Input: Cost-modeled, leakage-checked strategy
- Output: Multi-window rolling backtest with per-SubRegime breakdown
- Gate: Performance consistent across windows (CV < 0.5)
- Tooling: `scripts/eval_research_strategy.py` (full)

**Stage 6: Optimization (Optional)**
- Input: Robust strategy + parameter ranges
- Output: Robust parameter zone with sensitivity heatmap
- Gate: PBO < 0.5 (overfit probability acceptable)
- Tooling: `scripts/sweep_params.py`

**Stage 7: Statistical Validation + Tier Classification**
- Input: Optimal-zone strategy
- Output: DSR p-value, effective-K, Tier A/B/C/D classification
- Gate: Hard floors enforced (DSR p<0.3 minimum)
- Tooling: `research/validation/*` + `scripts/classify_strategy.py`

**Stage 8: Promotion to Paper**
- Input: Tier A or B strategy
- Output: File moved `research/generators/` → `src/core/strategy/generators/`, STRATEGY_CONFIG entry added, paper trading started, biography created
- Gate: Production code quality standards met
- Tooling: `scripts/promote_to_production.py`

**Stage 9: Live Deployment**
- Input: Paper-validated strategy with current Tier classification
- Output: Live capital allocation (100% slice for Tier A, 50% for Tier B)
- Gate: Operator clicks DEPLOY (opt-in per Decision B)
- Tooling: `scripts/run_live_trading.py` (updated)

**Stage 10: Decay → Re-Optimize or Retire**
- Input: Live strategy showing decay (PF declining, regime shift, etc.)
- Detection: `research/decay/detection.py` monitors rolling PF
- Diagnosis: `research/decay/diagnosis.py` classifies cause (regime shift vs parameter drift)
- Output:
  - If re-optimizable: parameters adjusted, strategy goes back to Stage 5 as new version (v1.1, v2.0, etc.)
  - If not re-optimizable: retirement decision logged, advances to Stage 11
- Tooling: `research/decay/*`

**Stage 11: Post-Mortem (Closes the Circle)**
- Input: Retired strategy
- Output: Full post-mortem document (see Appendix C template)
- Components:
  - What happened (lifecycle summary)
  - Why it failed (causal analysis)
  - Lessons extractable (regime-shift signal, parameter-decay pattern, market-microstructure change, etc.)
  - Pattern tags for future hypothesis matching
- **Critical**: post-mortem is indexed and queryable. Future hypotheses get matched against retired strategies to surface relevant lessons: "this hypothesis is similar to H-2025-XX which failed because of regime-detector lag — same risk applies here."
- Tooling: `scripts/generate_post_mortem.py`

**The full circle**: post-mortems flow back into Stage 1 (sourcing) as institutional memory. The strategy graveyard is not a memorial — it is a learning library that actively shapes future research direction.

---

## 11. Data Sources

### 11.1 Current (Already Available)

| Source | Type | Cost | Used For |
|---|---|---|---|
| Binance Spot OHLCV | Price/volume | Free (API) | All current strategies |
| Binance Futures funding | Derivatives | Free (API) | R0 additions (funding rate features) |
| Binance Futures OI | Derivatives | Free (API) | R0 additions (OI divergence) |
| SubRegime classifications | Internal | Free (computed) | Regime-aware research |
| Historical spread/slippage from paper trading | Internal | Free (computed) | Cost model calibration |

### 11.2 Research v0.5 Additions

None beyond existing. v0.5 uses existing data only. The methodology core (cost modeling, leakage detection, DSR) is the value-add.

### 11.3 Free Crypto-Native Additions (R1-R3.5)

| Source | Type | Cost | Purpose |
|---|---|---|---|
| Fear & Greed Index | Sentiment | Free | Sentiment regime classification |
| CoinGecko / CoinMarketCap (public APIs) | Reference | Free | Symbol metadata, market cap |

### 11.4 Paid Alt-Data — DEFERRED to Capital Threshold

| Source | Cost | Defer Until |
|---|---|---|
| Glassnode Studio | $39-$799/month | Working capital ≥ $25,000 |
| CryptoQuant | $29-$499/month | Working capital ≥ $25,000 |
| Coin Metrics Network Data Pro | Variable | Working capital ≥ $50,000 |
| Delphi Digital | Variable | Working capital ≥ $100,000 |

**Rationale**: At $1k-$10k working capital, $68/month subscription is 8-80% of realistic annual returns. The math doesn't work. Defer until subscription cost is structurally affordable.

### 11.5 Explicitly Excluded Data Sources

- **Tick-level order book data**: storage and processing costs prohibitive
- **Twitter sentiment via paid API**: signal density too low for cost
- **Custom satellite imagery / shipping data**: institutional-cost alt-data
- **Proprietary expert network access**: not retail-available
- **Bloomberg Terminal data feeds**: cost prohibitive

---

## 12. Tools and CLIs

### 12.1 v0.5 CLIs (Built First)

| CLI | Purpose |
|---|---|
| `scripts/retrospective_dsr.py` | **PRIORITY 1**: Apply DSR + honest cost model to existing 5 KEEP strategies |
| `scripts/eval_research_strategy.py <hypothesis_id>` | Full evaluation pipeline (stages 4-7) |
| `scripts/classify_strategy.py <strategy_id>` | Tier A/B/C/D classification with reasoning |
| `scripts/verify_cost_model.py <symbol>` | Validate cost model against actual paper fills |
| `scripts/check_leakage.py <generator_id>` | Standalone leakage check |

### 12.2 R1-R3 CLIs

| CLI | Phase | Purpose |
|---|---|---|
| `scripts/eval_feature.py <feature_id>` | R2 | Backtest a single feature in isolation |
| `scripts/sweep_params.py <hypothesis_id>` | R3 | Walk-forward parameter sweep with robust-zone identification |

### 12.3 R3.5 CLIs (Decay Workflow)

| CLI | Purpose |
|---|---|
| `scripts/check_decay.py <strategy_id>` | Diagnose decay (regime-shift vs parameter drift) |
| `scripts/reoptimize.py <strategy_id>` | Trigger re-optimization workflow |
| `scripts/generate_post_mortem.py <strategy_id>` | Generate post-mortem document |
| `scripts/match_to_post_mortems.py <hypothesis_id>` | Find similar past failures |

### 12.4 Promotion CLIs

| CLI | Purpose |
|---|---|
| `scripts/promote_to_production.py <hypothesis_id>` | Move strategy from research/ to src/ |
| `scripts/deploy_live.py <strategy_id>` | Opt-in deployment to live (per Tier classification) |

---

## 13. Cross-Cutting Capabilities

### 13.1 Survival/Risk Overlay

The research layer's outputs feed into risk decisions:

- **Position-sizing recommendation**: per strategy, based on backtest drawdown distribution + DSR confidence
- **Drawdown budget tracking**: aggregate drawdown across all live strategies; alert if exceeds threshold
- **Black-swan stress tests**: stress-test new strategies against historical crisis windows (March 2020 COVID crash, May 2021 China ban, FTX collapse Nov 2022, March 2023 banking crisis)
- **Counterparty risk monitoring**: track Binance proof-of-reserves data; alert on anomalies

### 13.2 Calibration Framework

Track operator hypothesis quality over time:

- Every hypothesis has `expected_pf` pre-registered
- After backtest, compute delta: `actual_pf - expected_pf`
- Aggregate deltas across hypotheses to compute operator's systematic bias (over/under-optimism)
- Break down by regime, by source, by hypothesis type
- **Track promotion type**: did Tier B deployments underperform Tier A? If yes, tighten Tier B.
- Output: monthly calibration report showing operator improvement trajectory

**Why**: Most operators have systematic biases they cannot see. Calibration tracking surfaces them. This is the genuine "smarter over time" capability — the system makes the operator's biases visible and correctable.

### 13.3 Decay Monitoring and Succession

Live strategies decay. The research layer supports this:

- **Decay detection**: rolling PF computed on live strategies; trend test for degradation
- **Auto-demotion**: existing demotion guardrail extended with regime-conditional logic
- **Succession queue**: list of next-up strategies ready to replace decaying ones
- **Causal analysis**: when retired, post-mortem records WHY (regime shift, parameter drift, market structure change)

### 13.4 Strategy Biography (Expanded — Full Circle Tracking)

**This is the institutional memory layer.** Every strategy has a continuous biography from hypothesis to (eventual) retirement. The biography is the operator's primary tool for reviewing strategies, especially Tier B candidates pending deployment decision.

**See Appendix A for the full schema.** Components:

- **Hypothesis history**: all hypothesis versions over time
- **Parameter history**: every parameter change with reasoning
- **Backtest history**: every backtest result, linked to cost model version + leakage check status
- **Optimization history**: every optimization attempt (successful and failed)
- **Paper trading history**: every paper session with performance + alignment metrics
- **Live deployment history**: every live deployment with capital allocation + Tier classification
- **Decay event history**: every detected decay event with diagnosis
- **Re-optimization history**: every re-opt attempt with outcome
- **Decision log**: every decision referenced (DEC IDs from DECISIONS.md)
- **Post-mortem** (if retired): full causal analysis with lessons extracted

**Critical property**: the biography is the SAME for active and retired strategies. Retirement adds the post-mortem section but does not change the data structure. This makes "active vs retired" a status field, not a structural divide.

**Operator interface**: when reviewing a strategy for Tier B deployment decision, operator opens the biography page and sees the complete journey. This supports informed deployment decisions without enabling override-of-hard-floors (which remain non-negotiable per Section 9.2).

---

## 14. Success Metrics

### 14.1 Research v0.5 Success Metrics

**By end of week 4**:
- All v0.5 deliverables operational
- Retrospective DSR analysis of 5 existing KEEP strategies completed
- Cost model has at least 1 symbol validated (against 10+ real paper fills)
- 3 seed hypotheses entered in ledger with full pre-registration
- At least 1 hypothesis classified through full pipeline (Tier A/B/C/D verdict)

**Honest expectation**: 1-3 of the 5 KEEP strategies likely fall to Tier B or C after retrospective DSR with honest cost modeling. This is the most valuable possible first-quarter outcome.

### 14.2 Stop/Pivot Gate (Pre-Registered)

**Hard date: 2026-12-01.** By this date:

**If approach is working** (continue building):
- At least 1 strategy has reached Tier A or stable Tier B classification
- At least 10 hypotheses have been tested through full pipeline
- Cost model verified for 3+ symbols
- Calibration delta < ±30% on average (operator's hypothesis expectations roughly accurate)

**If approach is NOT working** (STOP and reassess):
- 20+ hypotheses tested with verified cost model + clean leakage checks
- Zero have achieved Tier A or B classification
- DSR p-values consistently > 0.5 (strategies indistinguishable from noise)

**Pre-registered "verified cost model" definition** (to prevent escape-hatch drift):
- Cost model is "verified" only when validated against ≥10 actual paper trading fills per symbol
- Validation must show actual fills within 20% of cost model prediction (otherwise model is wrong, recalibrate)
- All symbols used in stop-gate-counting hypotheses must have verified cost models

**If hard date arrives without methodology verification**: failures count anyway. The stop gate fires. No further development of Phase R4+ until reassessment.

**Honest note on which criterion fires (baked in 2026-06-04 per external review)**: The "20 verified hypotheses zero survivors" branch requires verified cost models for all symbols used. The existing 5 KEEP strategies' symbols verify quickly from existing trade logs. NEW symbols introduced during research require months of paper fills before their cost model can be verified — slowing the soft-criterion clock for newly-introduced symbols. Realistic expectation: **the 2026-12-01 hard date will likely fire before the "20 verified hypotheses" soft criterion is fully met for newly-introduced symbols.** This is acceptable: the hard date is the protection-of-record against escape-hatch drift; the soft criterion functions as an additional honest-check on the same axis. Both protect against the same failure mode (perpetual research without deployment). Plan accordingly: do not rely on the soft criterion to fire before the hard date.

### 14.3 R1-R3.5 Success Metrics

- 30+ hypotheses in ledger by end of R3.5 (month 4)
- Median idea-to-Tier-verdict cycle time under 7 days
- At least 2 strategies in Tier A or B
- Decay-through-optimization workflow validated on at least 1 strategy
- At least 1 post-mortem generated (graveyard not empty)

### 14.4 System-Level North-Star Metrics

| Metric | Target by Month 6 | Target by Month 12 | Target by Month 24 |
|---|---|---|---|
| Hypotheses in ledger | 20+ | 50+ | 100+ |
| Tier A or B strategies in live | 1-2 | 3-5 | 5-10 |
| Median idea-to-verdict days | 7 | 4 | 2 |
| DSR-validated false-positive rate | <30% | <20% | <10% |
| Operator calibration delta | <±30% | <±20% | <±15% |
| Regime coverage | 3 of 8 SubRegimes | 5 of 8 SubRegimes | 6 of 8 SubRegimes |
| Post-mortems in graveyard | 3+ | 10+ | 25+ |

---

## 15. Risks and Mitigations

### 15.1 Tool Fetishism

**Risk**: Operator spends months building tools and never sources/tests ideas.
**Mitigation**: Research v0.5 ships in 4 weeks and forces immediate use. Hypothesis ledger entries required from day one. Retrospective DSR (week 1) produces real findings before scaffold complete.

### 15.2 Methodology Theater

**Risk**: Sophisticated stats produced but findings ignored when inconvenient.
**Mitigation**: Decisions traced via DECISIONS.md. Tier classification is mechanical. Hard floors (Section 9.2) cannot be overridden. Calibration framework tracks whether operator deployment decisions correlated with actual performance.

### 15.3 The "Never Finish Building" Trap (NEW)

**Risk**: 2 years of tooling, zero deployed strategies, rigor as alibi for not deploying.
**Mitigation**: Pre-registered stop/pivot gate at 2026-12-01 (Section 14.2). Research v0.5 ships in 4 weeks. Phase R4+ are conditional, not committed. Hard date applies regardless of methodology validation status.

### 15.4 Confirmation Bias via Override (NEW)

**Risk**: Operator promotes strategies that "almost pass" via override path, defeating rigor.
**Mitigation**: NO override path exists. Tier system is mechanical. Hard floors (DSR p<0.3, MaxDD<5%) cannot be relaxed without explicit PRD update and decision-log entry. Tier B exists to handle "almost-passing" without operator override — it deploys mechanically at reduced capital, not via human judgment.

### 15.5 Cost-Blindness (NEW)

**Risk**: Backtests systematically overstate returns by ignoring realistic per-symbol costs.
**Mitigation**: Cost modeling is a first-class R0 primitive. Cost model must be VERIFIED against real fills before being used for deployment-relevant backtests. Until verified, costs default to 2x estimate (extra-conservative).

### 15.6 Sample-Size Inflation

**Risk**: Strategies pass thresholds at N=20-30 by chance; effective K undercounted.
**Mitigation**: Effective K properly counted (parameter combos × symbols × timeframes). DSR uses correct K. Tier A requires N≥30 minimum. Calibration tracks whether smaller-N deployments underperform.

### 15.7 Calibration Bias from Operator

**Risk**: Operator unconsciously sets `expected_pf` to match what they "know" will pass thresholds, defeating pre-registration.
**Mitigation**: Calibration report tracks expected vs actual delta. Systematic bias surfaces visually. Periodic operator self-review.

### 15.8 LLM Confabulation (Conditional)

**Risk**: If LLM-assisted hypothesis suggestion is added in conditional future phase, produces plausible-sounding but spurious ideas.
**Mitigation**: LLM suggestions enter same ledger pipeline with same pre-registration and validation requirements. Source field marked as "llm-assist" for retrospective analysis. K accounts for LLM-generated trials.

### 15.9 Sustainability Burnout

**Risk**: 70% time allocation over 2 years on solo effort produces burnout.
**Mitigation**: Cadence planning. Quarterly rest weeks. System operates without operator for stretches (paper trading runs unattended). Phase-by-phase delivery so motivation refreshes with each shipped phase.

### 15.10 Edge Decay Faster Than Replacement

**Risk**: Strategies decay faster than research layer can replace them.
**Mitigation**: Succession queue maintained. Decay detection alerts trigger increased research velocity. Decay-through-optimization workflow (Section 6.5) attempts to recover decayed strategies before retirement.

### 15.11 Operational Risk

**Risk**: FTX-style counterparty event, geo-block, API ban, etc. invalidates research findings.
**Mitigation**: Research layer designed broker-agnostic where possible. Counterparty risk monitoring. Geo-block fail-fast already implemented (DEC-2026-06-01-003).

### 15.12 The "Never Deploy" Trap

**Risk**: Operator perpetually researches and never deploys.
**Mitigation**: Tier A/B classifications generate notifications. Calibration report flags strategies that have been READY (Tier A or B) for >2 weeks without deployment decision.

---

## 16. Decision References

This PRD will generate the following decisions in `.claude/DECISIONS.md` and `.agent/DECISIONS.md` (proposed IDs, to be confirmed upon ratification):

| ID (proposed) | Decision |
|---|---|
| DEC-2026-06-XX-001 | Adopt Research Layer PRD v2.0; structure as `research/` top-level module with one-way `src/` dependency |
| DEC-2026-06-XX-002 | Mandatory methodology primitives: pre-registration, cost modeling, leakage detection, DSR, walk-forward |
| DEC-2026-06-XX-003 | Hypothesis ledger + strategy biography as canonical research truth |
| DEC-2026-06-XX-004 | Strategy graduation path: research/generators/ → src/ via promote_to_production.py |
| DEC-2026-06-XX-005 | Paid alt-data deferred to capital threshold ≥ $25,000 (not calendar date) |
| DEC-2026-06-XX-006 | Permanent non-goals: price-prediction ML, deep RL, auto-discovered strategies, HFT, tick data, proprietary alt-data, co-location, capacity analysis below $25k capital |
| DEC-2026-06-XX-007 | Research layer does NOT advance MVP scope; locked trading decisions remain in force |
| DEC-2026-06-XX-008 | Hybrid Tier A/B/C/D promotion model with DSR p<0.3 as non-negotiable statistical floor |
| DEC-2026-06-XX-009 | Opt-in deployment for ALL tiers (overrides DEC-2026-06-01-001's opt-out behavior) |
| DEC-2026-06-XX-010 | Pre-registered stop/pivot gate at 2026-12-01 with verified-cost-model criteria |
| DEC-2026-06-XX-011 | Strategy lifecycle pipeline closes the circle: post-mortem completes every retired strategy |
| DEC-2026-06-XX-012 | Provability + future-capital-trajectory framing (audit-grade documentation as durable asset) |

Decisions to be filed and synced upon PRD ratification. **DEC-2026-06-01-001/002 require updates** to reflect opt-in promotion and Tier system integration.

---

## 17. Glossary

| Term | Definition |
|---|---|
| **Biography** | Complete lifecycle record of a strategy from hypothesis to retirement, including all versions, decisions, results, and post-mortem if applicable |
| **CPCV** | Combinatorial Purged Cross-Validation (Lopez de Prado 2018) — proper CV for time series. Deferred to conditional future phase. |
| **Cost model** | Per-symbol modeling of spread, fees, and slippage applied to all research-stage backtests |
| **DSR** | Deflated Sharpe Ratio (Bailey/Lopez de Prado 2014) — Sharpe adjusted for selection bias via effective K. The non-negotiable statistical floor in the Tier system. |
| **Effective K** | The true count of trials = ledger entries × parameter combos × symbols × timeframes. Used in DSR calculation. |
| **Hard floor** | Non-negotiable promotion criterion (DSR p<0.3, MaxDD<5%, cost verified, leakage clean) that cannot be overridden |
| **Hypothesis** | Pre-registered claim that a specific signal/pattern produces edge in a specific regime |
| **Leakage detection** | Automated check for lookahead bias, survivor bias, restatement bias, etc. in backtest setup |
| **PBO** | Probability of Backtest Overfitting (Bailey/Lopez de Prado) |
| **Post-mortem** | Causal analysis filed when strategy retires, closing the full-circle lifecycle |
| **Pre-registration** | Writing down expected results before backtesting; prevents post-hoc rationalization |
| **Provability framing** | Building the research layer to allocator-grade auditability standards as the durable asset |
| **Regime** | Market state (TRENDING_BULL, CHOPPY_BEAR, etc.) as classified by SubRegime detector |
| **Stop/pivot gate** | Pre-registered decision point at 2026-12-01: continue or reassess based on whether validated survivors exist |
| **SubRegime** | Fine-grained 8-state market regime classification |
| **Tier A/B/C/D** | Mechanical classification system for promotion: FULL_READY (A), PROVISIONAL_READY (B), NEEDS_WORK (C), REJECT (D) |
| **Walk-forward** | Optimization technique: rolling train/test windows, test data never seen during parameter selection |

---

## 18. Approval and Status

**Status**: PROPOSED v2.0 — awaiting operator ratification.

**Approval signatures required**:
- Operator (Eva) — confirmed Decision A (provability + capital trajectory) and Decision B (opt-in deployment + tier system) on 2026-06-04

**Upon approval**:
1. Decisions DEC-2026-06-XX-001 through DEC-2026-06-XX-012 filed in both `.claude/DECISIONS.md` and `.agent/DECISIONS.md`
2. DEC-2026-06-01-001/002 amended for opt-in promotion + Tier integration
3. Research v0.5 implementation begins (week 1 priority: retrospective DSR script)
4. Cross-reference added to `TRADING_SYSTEM_PRD.md` Part 2
5. Cross-reference added to `docs/00_MVP_TASK_INDEX.md`

**Last Updated**: 2026-06-04
**Enforcement**: This document, once approved, governs all research-layer work. Modifications require explicit operator approval and dual-file decision log update.

---

## Appendix A: Strategy Biography Schema

The biography is the institutional memory layer. Every strategy has one — active and retired alike. Same schema, retirement adds the post-mortem section.

```yaml
strategy_id: MACD_PB
status: ACTIVE_LIVE  # ACTIVE_RESEARCH | ACTIVE_PAPER | ACTIVE_LIVE | RETIRED
current_classification: TIER_A_FULL_READY  # A/B/C/D
classification_history:
  - date: 2026-04-15
    classification: TIER_A_FULL_READY
    triggered_by: DEC-2026-04-15-XXX
  - date: 2026-03-16
    classification: TIER_B_PROVISIONAL_READY
    triggered_by: backtest_v1.1.0_completion

# === HYPOTHESIS HISTORY ===
hypothesis_history:
  - version: "1.0.0"
    proposed_date: 2025-12-10
    proposed_by: operator
    source: "Quantpedia #43 + Robot Wealth 2024-03-15"
    rationale: |
      MACD pullback should work in trending markets — pullbacks to MACD signal
      line offer better risk/reward than chasing breakouts. Hypothesis: in
      TRENDING_BULL regimes, MACD signal crossovers after pullback to zero
      line produce positive expectancy.
    expected_pf: 1.5
    expected_sharpe: 1.2
    expected_n_per_year: 12
    regime_target: TRENDING_BULL
    expected_fail_modes:
      - "Chop-day false signals"
      - "Regime detector lag at transitions"
      - "Funding cost erosion if used on futures"

# === PARAMETER HISTORY ===
parameter_history:
  - version: "1.0.0"
    date: 2025-12-10
    params: {ema_fast: 12, ema_slow: 26, signal: 9}
    reason: "Standard MACD defaults from literature"
  - version: "1.1.0"
    date: 2026-03-15
    params: {ema_fast: 10, ema_slow: 30, signal: 9}
    reason: "Walk-forward optimization found faster signals improve choppy_bull edge"
    optimization_attempt: opt_001
    
# === OPTIMIZATION HISTORY ===
optimization_history:
  - attempt_id: opt_001
    date: 2026-03-15
    type: walk_forward_grid_search
    param_space: "ema_fast: [8-15], ema_slow: [25-35], signal: [7-12]"
    n_combinations_tested: 96
    walk_forward_windows: 12
    result: SUCCESSFUL
    pf_before: 1.62
    pf_after: 1.71
    led_to_version: "1.1.0"
    pbo_score: 0.18
  - attempt_id: opt_002
    date: 2026-04-22
    type: bayesian_optimization
    param_space: "all params"
    n_iterations: 100
    result: NO_IMPROVEMENT
    led_to_version: null
    notes: "Bayesian optimizer converged to v1.1.0 parameters; no robust improvement found"

# === BACKTEST HISTORY ===
backtest_history:
  - version: "1.0.0"
    date: 2025-12-12
    cost_model_version: "0.1"
    cost_model_verified: false  # used 2x default
    leakage_check: PASSED
    pf: 1.62
    sharpe: 1.34
    max_drawdown_pct: 3.8
    n_trades: 47
    dsr_p_value: 0.18
    effective_k: 8
    classification_at_time: TIER_B
    windows_tested: 5
    cv_across_windows: 0.18
  - version: "1.1.0"
    date: 2026-03-16
    cost_model_version: "1.0"
    cost_model_verified: true  # validated against 23 paper fills
    leakage_check: PASSED
    pf: 1.71
    sharpe: 1.45
    max_drawdown_pct: 3.5
    n_trades: 54
    dsr_p_value: 0.12
    effective_k: 104  # includes opt_001 grid search
    classification_at_time: TIER_A
    pbo_score: 0.18

# === PAPER TRADING HISTORY ===
paper_trading_history:
  - session_id: ps_001
    start: 2026-01-15
    end: 2026-02-12
    version_tested: "1.0.0"
    trades: 12
    pf: 1.43
    alignment_with_backtest: 0.78
    notes: "Aligned within expected bounds. PF lower than backtest by 11%, normal degradation."
  - session_id: ps_002
    start: 2026-03-20
    end: 2026-04-12
    version_tested: "1.1.0"
    trades: 18
    pf: 1.58
    alignment_with_backtest: 0.85
    notes: "Stronger alignment with v1.1.0. Operator confidence increased."

# === LIVE DEPLOYMENT HISTORY ===
live_deployment_history:
  - deployment_id: live_001
    deployed_date: 2026-04-15
    version: "1.1.0"
    capital_allocation_pct: 100  # TIER A = full slice
    classification_at_deployment: TIER_A_FULL_READY
    promotion_type: SYSTEM_RECOMMENDED
    operator_approval: OPT_IN_CONFIRMED
    operator_reasoning: "All gates passed cleanly, DSR p=0.12, cost model verified. Deploying at full slice."
    decision_reference: DEC-2026-04-15-XXX
    trades_to_date: 3
    pf_to_date: 1.21
    status: ACTIVE

# === DECAY EVENTS ===
decay_events: []  # none yet

# === RE-OPTIMIZATION HISTORY ===
reoptimization_history: []  # decay-triggered re-opts, separate from voluntary opts

# === DECISION LOG ===
decision_log:
  - DEC-2025-12-10-XXX: "Initial hypothesis registered"
  - DEC-2026-03-15-XXX: "Re-optimization approved, v1.1.0 created"
  - DEC-2026-04-15-XXX: "Promoted to TIER_A_FULL_READY, deployed at 100% slice"
  - DEC-2026-05-28-002: "Triage review — KEEP"
  - DEC-2026-05-28-XXX: "Regime retag (trending_bull → choppy_bear primary)"

# === CORRELATION WITH PORTFOLIO ===
correlation_with_portfolio:
  BTP: 0.12
  VBB: 0.18
  SRC: 0.31
  ICVP: 0.09

# === POST-MORTEM (only populated if RETIRED) ===
post_mortem: null  # see Appendix C for template
```

---

## Appendix B: Hypothesis Ledger Entry Schema

```yaml
- id: H-YYYY-MM-NNN
  name: "Short descriptive name"
  status: PROPOSED | IMPLEMENTED | BACKTESTED | TIER_A | TIER_B | TIER_C | TIER_D | RETIRED
  proposed_date: YYYY-MM-DD
  proposed_by: operator | llm_suggest | source_ingestion | post_mortem_match
  source: "Reference (paper title, blog post, etc.)"
  
  # PRE-REGISTRATION (refused at CLI level if missing)
  hypothesis: |
    Multi-line description of:
    - What pattern is hypothesized to exist
    - In what regime
    - Why it should produce edge
    - Theoretical justification
  
  regime_target: SubRegime enum value
  expected_pf: float
  expected_sharpe: float
  expected_n_per_year: int
  expected_fail_modes:
    - "..."
  
  # PARAMETERS
  parameters:
    param_name: [list of values OR range]
  
  features_used:
    - feature_id (from feature catalog)
  
  # EFFECTIVE K (auto-calculated)
  effective_k_at_proposal: int
  effective_k_after_optimization: int  # populated post-optimization
  
  # IMPLEMENTATION
  implementation_file: research/generators/<name>.py
  
  # POST-MORTEM PATTERN MATCHING
  similar_retired_strategies:
    - strategy_id: STRAT_XXX
      similarity_score: 0.78
      relevant_lessons:
        - "Failed due to regime detector lag at transitions"
        - "Consider adding regime confirmation requirement"
  
  # RESULTS (populated post-evaluation)
  results:
    classified_tier: TIER_A | TIER_B | TIER_C | TIER_D
    backtest_date: YYYY-MM-DD
    actual_pf: float
    actual_sharpe: float
    actual_n: int
    delta_from_expected_pf: float
    dsr_p_value: float
    pbo_score: float
    cost_model_verified: bool
    leakage_check: PASSED | FAILED
    
  # PROMOTION PATH (populated if promoted)
  promotion_path:
    promoted_to_production_date: YYYY-MM-DD | null
    production_file: src/core/strategy/generators/<name>.py | null
    paper_trading_started: YYYY-MM-DD | null
    live_deployment_date: YYYY-MM-DD | null
    live_capital_pct: 100 | 50 | null  # Tier A=100, Tier B=50
    
  # BIOGRAPHY POINTER
  biography_file: research/biographies/active/<strategy_id>.yaml
```

---

## Appendix C: Post-Mortem Template

When a strategy retires, a post-mortem is generated. This is what closes the full-circle lifecycle.

```yaml
post_mortem:
  strategy_id: STRAT_XXX
  retirement_date: YYYY-MM-DD
  retirement_decision: DEC-YYYY-MM-DD-XXX
  decision_maker: operator | system_auto
  
  # === LIFECYCLE SUMMARY ===
  lifecycle_summary:
    proposed_date: YYYY-MM-DD
    first_live_deployment: YYYY-MM-DD
    retirement_date: YYYY-MM-DD
    total_lifespan_days: int
    total_versions: int  # v1.0, v1.1, v2.0, etc.
    total_optimization_attempts: int
    total_reoptimization_attempts: int  # decay-triggered
    
    peak_classification: TIER_A | TIER_B
    final_classification: TIER_C | TIER_D | DECAYED
    
    cumulative_live_pnl_pct: float
    cumulative_live_trades: int
    final_live_pf: float
    
  # === RETIREMENT CAUSE ===
  primary_cause: REGIME_SHIFT | PARAMETER_DECAY | MARKET_STRUCTURE_CHANGE | NEVER_VALIDATED | STATISTICAL_NOISE | OPERATIONAL_FAILURE
  
  causal_analysis: |
    Multi-paragraph analysis of why the strategy failed.
    
    Example:
    "MACD_PB began showing decay in 2026-08 when BTC entered a strong trending phase
    after months of choppy_bear. Re-optimization (reopt_001) found new parameters
    but with significantly lower DSR p-value (0.34 vs original 0.12), indicating
    the apparent improvement was overfit. The strategy's edge in choppy regimes
    appears to have decayed as more participants traded similar MACD pullback
    patterns. Retirement chosen over further re-optimization to preserve research
    capacity for strategies with cleaner regime fit."
  
  contributing_factors:
    - "Crowding: similar strategies likely being traded by other quants"
    - "Regime shift: extended bear-to-bull transition unfavorable to choppy-regime strategies"
    - "Parameter sensitivity: returns degrade rapidly with small parameter changes (sensitivity score 0.34)"
  
  # === LESSONS EXTRACTED ===
  lessons:
    - lesson_id: LESS-YYYY-MM-001
      category: REGIME_FIT
      description: "Strategies with edge confined to single SubRegime carry concentration risk when that regime is exited"
      pattern_tags: ["single-regime", "choppy-bear-only", "regime-dependent"]
      applies_to_future_hypotheses_in: ["TRENDING_BULL", "CHOPPY_BEAR"]
      
    - lesson_id: LESS-YYYY-MM-002
      category: REOPTIMIZATION_LIMITS
      description: "Re-optimization that significantly degrades DSR is a retirement signal, not an improvement signal"
      pattern_tags: ["reoptimization-decay", "dsr-degradation"]
      applies_to_future_hypotheses_in: ["all"]
  
  # === PATTERN TAGS (for future matching) ===
  pattern_tags:
    - macd-based
    - pullback-entry
    - choppy-regime
    - multi-symbol
    - retired-by-decay
    - reoptimization-failed
    
  # === RELATED STRATEGIES ===
  similar_active_strategies:
    - strategy_id: STRAT_YYY
      similarity_score: 0.65
      shared_risk_factors:
        - "Both depend on choppy-bear regime"
        - "Both sensitive to regime transitions"
      recommended_monitoring: "Watch STRAT_YYY for similar decay signals"
  
  # === GRAVEYARD INDEX METADATA ===
  searchable_terms:
    - "MACD pullback"
    - "Choppy bear retired"
    - "2026 crowding casualty"
  
  feeds_back_to:
    - "Future MACD-based hypotheses should check this post-mortem"
    - "Hypothesis matching algorithm uses pattern_tags to surface during Stage 2"
```

**The post-mortem is searchable and feeds back into hypothesis matching.** When a new MACD-based hypothesis is proposed, the system surfaces relevant retired strategies' post-mortems: "this hypothesis shares pattern tags with STRAT_XXX which was retired due to regime-shift decay. Review similar_active_strategies for current exposure."

This is what closes the circle. The graveyard is a library.

---

## Appendix D: Conditional Future Phases (R4-R8)

**These are NOT committed work.** They are described here so that the long-term direction is documented, but each is built only if earlier phases produce validated survivors and the stop/pivot gate at 2026-12-01 confirms continuation.

### Phase R4: Alt-Data Integration (Conditional — months 5-7 IF survivors exist AND capital ≥ $25k)

- `research/data/glassnode.py` — Glassnode API adapter (PAID)
- `research/data/cryptoquant.py` — CryptoQuant API adapter (PAID)
- Local cache layer
- Feature library extensions: on-chain features (SOPR, NUPL, exchange flows), derivatives features (funding, OI, basis)

### Phase R5: Advanced Validation (Conditional — months 6-9 IF survivors exist)

- `research/validation/cpcv.py` — Combinatorial Purged CV
- `research/validation/reality_check.py` — White's Reality Check + SPA test
- Bootstrap confidence intervals
- Strategy resampling (Monte Carlo of trade order)

### Phase R6: Notebook Environment (Conditional — months 7-10)

- Jupyter kernel with pre-loaded data fixtures
- Notebook templates
- Interactive backtest widget

### Phase R7: Source Ingestion (Conditional — months 9-12)

- Paper PDF parser
- Blog scraper (curated source list)
- Idea extraction (LLM-assisted)
- Citation graph
- RSS aggregator

### Phase R8: Polish + Knowledge Management (Conditional — months 12-15)

- Research dashboard (local web UI)
- Annual review framework
- Strategy graveyard search interface

### Mature (Conditional — months 18-24)

- Risk modeling extensions (tail risk, regime correlation)
- Multi-strategy portfolio optimizer
- Cross-strategy correlation tracking
- Knowledge graph linking hypotheses, features, regimes, outcomes

---

## Appendix E: Source Tier Rankings

### Tier 1 (Highest Signal Density)
- Quantpedia (https://quantpedia.com) — ~$300/year — 700+ strategies catalogued
- CryptoQuant Research blog — crypto-native, on-chain signals (free blog)
- Glassnode Insights — on-chain analytics translated to signals (free blog)
- arXiv q-fin.PM and q-fin.TR — crypto-filtered papers

### Tier 2 (High Signal, Curation Required)
- SSRN finance papers, sorted by downloads, crypto-filtered
- Robot Wealth blog (Kris Longmore)
- Building Alpha blog
- CSS Analytics (David Varadi)
- Two Centuries Investments

### Tier 3 (Moderate Signal)
- Quantocracy daily aggregator
- System Trader Show podcast
- Cryptoeconomic Systems journal
- Coin Metrics State of the Network reports

### Tier 4 (Low Signal, Use Only Curated Accounts)
- Twitter (FinTwit) — only after identifying ~10-20 high-quality accounts
- Reddit r/algotrading — occasional gems amid noise

### Tier 5 (Avoid for Sourcing)
- General crypto Twitter / YouTube
- TradingView ideas (TA without statistical rigor)
- Discord / paid signals (adverse selection)

---

## Appendix F: Phase Sequencing Visual

```
WEEK:     1    2    3    4 | 5    6    7    8 | 9   10   11   12 | 13  14  15  16 | 17  18 | 19....24 |
PHASE:   R0.5 R0.5 R0.5 R0.5| R1   R1   R1   R1 | R2   R2   R2   R2 | R3   R3  R3  R3 | R3.5 R3.5| BUFFER  |
           Foundation     |  Stat Rigor       |   Feature Eng     |  Optimization | Decay  | Reserve |
           + Safety       |                   |                   |                |        |         |
                                                                                                          ↓
                                                                                              ┌──────────────────────┐
                                                                                              │ STOP/PIVOT GATE      │
                                                                                              │ 2026-12-01 (Month 6) │
                                                                                              │                      │
                                                                                              │ Decision based on    │
                                                                                              │ validated survivors. │
                                                                                              └──────────────────────┘
                                                                                                          ↓
                                                                          If survivors exist: Phase R4+ (Appendix D)
                                                                          If no survivors: STOP and reassess
```

**Critical first action (Week 1, Days 1-3)**: Retrospective DSR on existing 5 KEEP strategies. This precedes scaffold building because it uses existing trade logs and could materially change the strategy of the entire research layer.

---

*End of PARAVANT Research Layer PRD v2.0*

**Document Status:** PROPOSED v2.0 — awaiting ratification
**Next Review:** After Research v0.5 completion (Week 4) AND at stop/pivot gate (2026-12-01)
**Change Control:** All changes require operator approval and dual-file decision log update (`.claude/DECISIONS.md` AND `.agent/DECISIONS.md`)
