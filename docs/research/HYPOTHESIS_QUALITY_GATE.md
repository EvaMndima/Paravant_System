# Hypothesis Quality Gate — Pre-DSR Reasoning + Structural Screen

**Status:** ADOPT-BY-HAND checklist (discipline now; tooling deferred per DEC-2026-06-04-018)
**Date:** 2026-06-08
**Owner:** Eva (operator) + Claude
**Related:** DEC-2026-06-04-018 (this gate), DEC-2026-06-04-008 (Tier/DSR floor),
DEC-2026-06-04-006 (auto-discovery non-goal), DEC-2026-06-04-011 (post-mortem),
DEC-2026-06-04-014 (regime-DSR guards). PRD Sections 8 (methodology), 9 (gate).

---

## Why this exists (read once)

DSR is the EVIDENCE gate — it decides whether the data supports an edge, and it
penalizes you for the number of trials (effective K). So you must NOT spend a DSR
trial on an idea that cheaper reasoning could have rejected. This gate sits
BEFORE DSR and measures **reasoning-quality**, not evidence-quality:

- **Reasoning-quality** (this gate): is the idea well-formed, mechanism-grounded,
  feasible, novel, parsimonious? **Knowable with zero performance data.**
- **Evidence-quality** (DSR): does the data actually support it? Needs DSR.

The reframe that makes this rigorous: **a backtest is for CONFIRMATION, not
DISCOVERY.** This gate forces "have a theory first," so DSR confirms a
pre-specified theory rather than searching for one. That is what keeps K small
and any survivor credible.

**Two hard lines (DEC-2026-06-04-018), never cross them:**

1. **No performance peek before DSR.** Any pre-DSR data check is STRUCTURAL only
   (does it run, trade count, holding period, per-regime coverage). It must NOT
   compute or show PF / Sharpe / returns / drawdown. Seeing in-sample performance
   biases the eventual DSR test irreversibly. "A light backtest that shows how it
   did" is just an uncorrected backtest — the overfit trap.
2. **No algorithmic strategy generation from failures.** Failures inform HUMAN
   mechanism choice (negative-space map); they never feed a generator that emits
   new strategy specs. Remixing no-edge strategies yields no-edge strategies and
   is the DEC-2026-06-04-006 auto-discovery non-goal.

---

## STAGE 1 — Reasoning scorecard (no data, minutes)

### Hard gates — fail ANY and the idea does NOT earn a DSR trial

- [ ] **Mechanism stated.** Written causal story for *who is on the other side and
  why they keep losing* (risk premium / behavioral bias / structural flow /
  information). "It works in the backtest" is NOT a mechanism. Vague
  ("markets are inefficient") fails; concrete ("leveraged longs are force-
  liquidated at funding-rate extremes and sell into the move") passes.
- [ ] **Falsifiable fail modes.** You can state, in advance, what would make this
  FAIL. (Also feeds the pre-registration `expected_fail_modes`.)
- [ ] **Sample-size feasibility.** Estimated trades/year x testable window >= the
  minimum N for DSR to mean anything (target N>=30 in the intended regime within
  a ~18-month window). A 4-trades/year idea is untestable — do not spend a trial.
- [ ] **Not a known-dead pattern.** Scan `research/biographies/retired/` pattern-
  tags. If it matches a FUNDAMENTAL failure (e.g. classic-TA-without-edge) with no
  stated reason it is different, REJECT. If it matches a FIXABLE failure, see
  Stage 3.

### Scored dimensions — weight, then require a threshold to proceed

Score each 0-3 (0 = absent/bad, 3 = strong). Suggested pass threshold: mechanism
strength >= 2 AND total >= 14/21. Tune the threshold by hand over the first
batch; do not over-fit the rubric itself.

| Dimension | 3 (strong) | 0 (weak) |
|---|---|---|
| Mechanism strength | Names counterparty + why they persist losing | Hand-wavy / none |
| Crowding (inverse) | Novel, obscure mechanism | Textbook-famous (already arbitraged) |
| Crypto-native fit | Uses 24/7, funding, liquidations, on-chain | Transplanted equity factor |
| Regime specificity | Names the regime it works in AND why | "Works always" (red flag) |
| Parameter parsimony | 2-3 free params | 10+ knobs, filters-on-filters |
| Diversity contribution | Adds a mechanism/regime the portfolio lacks | Variation #47 of momentum |
| Source credibility | Peer-reviewed w/ OOS > Quantpedia > vetted blog | Random TradingView post |

**Anti-rationalization rule:** an LLM (or you) can invent a plausible-sounding
mechanism for noise. Treat a slick mechanism story with no data behind it as a
YELLOW flag, not green. The mechanism must name the concrete counterparty.

---

## STAGE 2 — Structural feasibility profile (BLIND data, optional)

Only for ideas that clear Stage 1. Run the generator over history and report
ONLY structure — NEVER performance:

- [ ] Runs without crashing; produces a non-degenerate trade series.
- [ ] Trade count adequate (confirms Stage-1 feasibility estimate empirically).
- [ ] Holding-period distribution matches the intended style (not 1-bar churn for
  a "swing" idea).
- [ ] Per-regime trade coverage (enough trades in the target regime).
- [ ] Turnover / net-exposure profile is sane.

**The tool must not output PF/Sharpe/returns.** If you find yourself wanting the
performance number, that is exactly the impulse this stage exists to deny until
DSR. Catches implementation bugs and "2 trades in 540 days" cheaply, without
biasing the DSR test and without inflating K (no performance selection occurred).

---

## STAGE 3 — Only now: DSR (the evidence gate)

Survivors of Stages 1-2 earn a DSR trial via `scripts/regime_dsr.py` (pooled +
per-regime, honest K, p<0.3 floor — DEC-2026-06-04-008/014). This is unchanged.

---

## Recording failures (the graveyard as a generative resource)

Every rejection is data. Record where and why it died, and tag it:

| Where it died | Cost | Tag with |
|---|---|---|
| Stage 1 (reasoning gate) | minutes, no data | reason (no-mechanism / crowded / infeasible-N / known-dead) |
| Stage 3 (DSR evidence gate) | one trial (K) | FUNDAMENTAL vs FIXABLE |

**FUNDAMENTAL vs FIXABLE — the rigorous core:**

- **FUNDAMENTAL** (no mechanism, edge decayed, never validatable): graveyard says
  *never revisit*. (MACD_PB = REGIME_SHIFT decay; RSI_BB = classic-TA-without-edge.)
- **FIXABLE near-miss** (right edge, wrong regime label; right idea, wrong universe
  or timeframe; DSR p just over the floor with thin N): a diagnosable, correctable
  flaw. **These are the highest-quality seedbed for NEW hypotheses** — they already
  cleared the mechanism gate; they just need one correction. This is how the
  graveyard generates ideas: not by remixing corpses, but by pointing at the ones
  that almost lived and naming exactly what to fix.

**Coverage map (maintain by hand for now):** a simple mechanism x regime grid,
marking each cell dead / crowded / unexplored. Direct sourcing at the unexplored
complement (TRENDING_BULL is currently uncovered).

---

## Sequencing — discipline now, tooling later (DEC-2026-06-04-018)

- **NOW (free):** use this checklist by hand on the first 5-10 hypotheses. The
  graveyard already exists (7 pattern-tagged post-mortems).
- **LATER (only if proven the bottleneck):** automate the scorecard scoring, build
  the blind structural-profile tool, make the failure taxonomy queryable, and add
  the FUNDAMENTAL/FIXABLE tag + coverage map to the biography schema. Build these
  only after the hand-applied rubric shows which dimensions actually discriminate
  and that triage (not idea-generation) is the real bottleneck.
- **NEVER:** a failure-driven strategy generator (auto-discovery non-goal).

The checklist costs nothing and works today; the software waits for evidence it is
needed.
