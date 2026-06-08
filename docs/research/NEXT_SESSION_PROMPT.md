# Session Bootstrap Prompt — Start the Forward Hypothesis Loop (Research v0.5 -> live use)

**Purpose**: Paste the block below into a fresh Claude Code session. The research
INFRASTRUCTURE is built, tested, and proven on real data. This session does NOT
build more infrastructure — it USES the pipeline to source, formalize, and test
NEW strategy hypotheses. That is where progress comes from now.

**Written 2026-06-08**, replacing the two earlier build-phase prompts (now
deleted). State: the audit of the 5 KEEP strategies is complete — they are
decayed bear/choppy-regime strategies, none currently DSR-validated. The pipeline
(regime-conditional backtest DSR) is on branch `feat/research-retrospective-dsr`,
97 tests green, NOT yet merged.

---

## COPY EVERYTHING BELOW THIS LINE INTO THE NEW SESSION

---

I'm continuing PARAVANT, a personal autonomous crypto trading system. The research
layer's audit phase is FULLY CLOSED: the 5 existing KEEP strategies were screened
with regime-conditional backtest DSR and found to be decayed bear/choppy-regime
strategies (real edges at promotion that faded as the market turned bull; none
passes the DSR p<0.3 floor). MACD_PB is RETIRED (regime-shift decay, DEC-017), and
all 7 retirees now have structured, pattern-tagged post-mortems (the graveyard is a
live library). The methodology is PROVEN — it caught MACD_PB's fragility that
PF-based promotion missed, and BTF (the known-bad control, N=997) returned Tier D
in every regime.

Your job this session is NOT to build more tooling. It is to START THE FORWARD
HYPOTHESIS LOOP: source -> quality-gate (reasoning scorecard, no data) ->
formalize -> register -> screen (DSR) new strategy ideas through the pipeline that
already exists. The quality gate (DEC-2026-06-04-018,
`docs/research/HYPOTHESIS_QUALITY_GATE.md`) is a by-hand CHECKLIST that kills weak
ideas BEFORE they cost a DSR trial — use it, do not build it into tooling yet.
Resist building new infrastructure; if a tested hypothesis genuinely needs a new
tool, add it then, not before.

## Required reading (in this order)

1. `docs/research/RESEARCH_LAYER_PRD.md` — Sections 8 (methodology), 9 (Tier
   gate), 10 (lifecycle), Appendix B (hypothesis ledger schema).
2. `docs/research/HYPOTHESIS_QUALITY_GATE.md` — the pre-DSR quality gate
   (DEC-2026-06-04-018): reasoning scorecard + blind structural profile +
   FUNDAMENTAL/FIXABLE failure taxonomy. This is the front-end of the loop.
3. `docs/research/RETROSPECTIVE_DSR_SPEC.md` — the frozen spec + the regime-DSR
   guards (Section 6.x and the DEC-2026-06-04-014 guards).
4. `.claude/CLAUDE.md` and `.claude/rules/decision-consistency.md` — project
   rules + dual-file DECISIONS sync.
5. `.claude/DECISIONS.md` — read DEC-2026-06-04-008 (Tier/floor), -009 (opt-in),
   -011 (post-mortem), -012 (provability), -018 (the pre-DSR quality gate),
   -013/-014/-015/-016/-017 (the audit findings, regime-DSR, MACD_PB retirement).
   Check the footer for the next DEC ID.
6. The 5 KEEP biographies in `research/biographies/active/` and the 7 retiree
   post-mortems in `research/biographies/retired/` — so you understand what already
   failed and why (decay vs the NEVER_VALIDATED subtypes), and so you can pattern-
   match new hypotheses against known failure modes.

## Current state

- ALL prior research work is MERGED TO MASTER (7 commits through `34e6db8`),
  tests green (102 research + 3 equivalence + 130 backtest). The local master is
  NOT pushed to origin — ask the operator whether to push. Work on master or a
  fresh feature branch.
- Live kill switch OFF (`LIVE_TRADING_ENABLED=false`). Do NOT enable it. Nothing
  is deployed; no live capital at risk.
- Paper trading is DOWN (Railway geo-block — operator action to restore).
  Backtest-based research does not need it.
- `Tier.INSUFFICIENT_DATA` now exists: N=0/thin no longer masquerades as
  TIER_D_REJECT. Cost model is still v0_unverified (conservative screen; verify
  against real fills only when paper data returns).
- Pipeline ready: `research/validation/deflated_sharpe.py` (verified DSR),
  `research/backtest/cost_model.py` (incremental-pad), `research/promotion/
  classifier.py` (Tier A/B/C/D + INSUFFICIENT_DATA), `scripts/regime_dsr.py`
  (regime-conditional backtest DSR screen), `research/hypotheses/ledger.yaml`,
  `scripts/generate_post_mortem.py` + the `PostMortem` model. The screen evaluates
  a registered strategy in minutes (cached) / ~tens of minutes (uncached).

## HOW THE EVAL ACTUALLY WORKS (the one piece of enabling glue — read this)

`scripts/regime_dsr.py` screens strategies REGISTERED in
`scripts/backtest_rolling.py` (`STRATEGY_PARAMS`, `STRATEGY_SYMBOLS`, and
`STRATEGY_UNIVERSE`), selected with `--strategy <id>`. It evaluates the EXISTING
registered set; a brand-new hypothesis is NOT screenable until it is registered
there with a working generator. So to test a new idea you (a) write its generator,
(b) register its params/symbols/status, then (c) run
`python -m scripts.regime_dsr --strategy <new_id>`. There is NO separate
`eval_research_strategy.py` to build — regime_dsr IS the eval. Do NOT build a
parallel eval tool.

FIRST SMALL TASK (resolve before sourcing): decide the registration path for new
research generators. Either (pragmatic) register them in `backtest_rolling`'s
config the way existing strategies are, OR (cleaner, per the PRD one-way
dependency) extend regime_dsr to also load generators from `research/generators/`.
Pick one, document it in a one-line decision, and keep it consistent. This is the
only glue the forward loop needs.

## The research priority: REGIME-DIRECTED hypotheses for the UNCOVERED regime

The audit's central finding shapes what to test:

- All 5 existing strategies are bear/choppy-regime strategies. **TRENDING_BULL is
  uncovered** AND the market has turned bull. So a validated bull/trend strategy
  fills the gap AND matches the current regime — highest value.
- The decay lesson: do NOT promote on PF alone. The DSR p<0.3 floor is the gate.
  MACD_PB's promotion-era edge (PF 1.97, N=8) had DSR p=0.569 — real but
  not-yet-proven — and it decayed. Require DSR validation, and bias toward
  strategies that generate ENOUGH TRADES to be testable (thin N was the trap).

## The loop (per hypothesis) — the QUALITY GATE comes BEFORE DSR

Full gate detail: `docs/research/HYPOTHESIS_QUALITY_GATE.md` (DEC-2026-06-04-018).
It is a by-hand CHECKLIST — use it, do not build it into tooling yet.

1. **SOURCE.** Read a credible source (Quantpedia, Robot Wealth, arXiv q-fin, CSS
   Analytics — see `docs/research/READING_QUEUE.md` if present, or PRD Appendix E
   for the source tiers). Target trend-following / bull-regime ideas first.
2. **STAGE 1 — REASONING SCORECARD (no data; most ideas die here, cheaply, with NO
   DSR trial spent).** Apply the HARD GATES: mechanism stated (who is on the other
   side and why they keep losing — "works in the backtest" is not a mechanism);
   falsifiable fail modes; sample-size feasibility (can it ever reach N>=30 in its
   regime within the window?); and NOT a known-dead graveyard pattern (scan
   `research/biographies/retired/` tags — if your "RSI mean-reversion" matches
   RSI_BB's classic-TA-without-edge, you need a reason it differs, or skip it).
   Then score the weighted dimensions (mechanism strength, inverse-crowding,
   crypto-native fit, regime specificity, parsimony, diversity, source). Fail a
   hard gate or miss the threshold -> REJECT without a DSR trial; record the reason
   in the graveyard. ANTI-RATIONALIZATION: a slick mechanism story with no data is
   a YELLOW flag — the mechanism must name the concrete counterparty.
3. **FORMALIZE (pre-register).** Survivors only: write the hypothesis into
   `research/hypotheses/ledger.yaml` with expected PF/Sharpe/N-per-year, regime
   target, and fail modes — BEFORE backtesting (PRD Appendix B). Results that
   dramatically EXCEED the pre-registration are a red flag (overfit/leakage).
4. **IMPLEMENT + REGISTER.** Write the generator in `research/generators/<name>.py`
   (reuse `src/core/strategy/` indicators; never touch `src/` production code), then
   register it on the chosen eval path (see "HOW THE EVAL ACTUALLY WORKS").
5. **STAGE 2 — BLIND STRUCTURAL PROFILE (optional; data but NO performance).**
   Confirm it runs, trade count adequate, holding-period/turnover/per-regime
   coverage sane. Report STRUCTURE ONLY — NEVER PF/Sharpe/returns. Seeing
   performance before DSR biases the real test irreversibly.
6. **STAGE 3 — SCREEN (DSR, the evidence gate).** Run
   `python -m scripts.regime_dsr --strategy <id>` for pooled + per-regime DSR with
   honest K. Write the verdict to the biography (canonical YAML).
7. **VERDICT + DECISION.** Clears DSR p<0.3 in a regime with adequate N ->
   paper-trading candidate (when Railway paper is restored); file a DEC entry
   (dual-file) if KEEP. Most ideas fail — that is the funnel working. Tag every
   failure **FUNDAMENTAL** (no mechanism / decayed -> never revisit) vs **FIXABLE**
   (right edge wrong regime label, wrong universe/timeframe, or DSR p just over the
   floor with thin N -> diagnosable near-miss = seedbed for a corrected hypothesis)
   and log it in the graveyard.

## The non-negotiable guards (DEC-2026-06-04-014, -008, -018)

- **Screen, not deployment gate.** Backtest edge degrades live; a DSR pass means
  "worth paper-trading", not "deploy". Paper/live remains the real gate.
- **DSR p<0.3 is the floor.** No override path. p>=0.3 cannot be Tier A/B.
- **Honest K** = param-combos x symbols x timeframes x regime-buckets. Regime-
  shopping (test 8 regimes, keep the best) needs the regime-bucket penalty.
- **Causal regime tagging** (no future bars in the regime label).
- **Coarse buckets where N is thin**; per-bucket results below min-N are
  descriptive, not gating.
- **No performance peek before DSR** (DEC-2026-06-04-018). Pre-DSR data checks are
  STRUCTURAL only (runs / trade count / coverage); never compute or show
  PF/Sharpe/returns before DSR — it biases the real test irreversibly.
- **No failure-driven strategy generator** (DEC-2026-06-04-006/-018). Failures
  steer HUMAN mechanism choice (negative-space map); they never feed an algorithm
  that emits new strategy specs.

## Parallel operator tracks (NOT this session's work; surface, don't block on them)

- **Push master to origin** — the 7 research commits are local-only. Operator's
  call; offer it.
- **Restore paper trading** (Railway geo-block, operator action). Once back, the
  ONE existing watchlist candidate is **VBB** (its choppy_bear/choppy_bull edge is
  the only one that persists weakly into the present) — paper-validate it IN-REGIME
  via the router, never unconditionally. This is separate from sourcing new
  hypotheses; do not let it gate the research loop.
- **Cost-model verification** — verify the v0 cost model against real fills only
  after paper data returns. Until then, every verdict is the conservative screen.

(The earlier "merge the branch" and "ratify MACD_PB" decisions are DONE — merged to
master, MACD_PB retired with post-mortem in DEC-2026-06-04-017.)

## Rules you MUST follow

- One-way dependency: `src/` never imports `research/`.
- Biography YAML canonical; markdown/JSON derived.
- Dual-file DECISIONS sync (`.claude/` AND `.agent/`, verify `diff` empty).
- Zero-tech-debt: full type hints, Google docstrings, timezone-aware datetimes,
  structured logging, no emojis/unicode in code. Tests for new code (>=80%).
- Do NOT enable live trading. Do NOT modify Neon data. Do NOT touch Railway region.
- Do NOT build new infrastructure unless a tested hypothesis demonstrably needs it.

## How to start

1. Read the required docs + the 5 KEEP regime-DSR verdicts + the 7 retiree
   post-mortems (so the graveyard is in your head before you source).
2. Resolve the FIRST SMALL TASK: the registration path for new generators (see
   "HOW THE EVAL ACTUALLY WORKS"). One short decision, then never reopen it.
3. State the regime gap you're targeting (TRENDING_BULL) and the first 1-3
   hypotheses you'll source.
4. Use TodoWrite. Source -> Stage 1 reasoning scorecard (hard gates + score) ->
   formalize (pre-register) -> implement+register -> Stage 2 blind structural
   profile (optional) -> Stage 3 DSR screen -> verdict (tag FUNDAMENTAL/FIXABLE).
   One hypothesis at a time; let the funnel work. Most will fail at the scorecard,
   cheaply — that is success, not failure.

## END COPY

---

**Note for Eva**: This is the pivot from building to using, and the audit is fully
closed (merged to master, MACD_PB retired, graveyard populated). The pipeline is
proven; the bottleneck now is GOOD IDEAS, not tooling. The fastest path to a
deployable strategy is to push trend/bull hypotheses through the gate and let most
fail honestly until one survives. Two things the new session must know that aren't
obvious: (1) a new hypothesis must be REGISTERED before regime_dsr can screen it —
that one small glue step is the only "build" left; (2) the graveyard is now a live
library — check it before testing, so you don't re-pay for a known-dead pattern.
When Railway paper is restored, VBB is the one existing watchlist candidate to
paper-validate in-regime.
