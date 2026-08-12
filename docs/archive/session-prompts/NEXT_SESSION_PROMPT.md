# Session Bootstrap Prompt — Continue the Forward Hypothesis Loop (Research v0.5 -> live use)

**Purpose**: Paste the block below into a fresh Claude Code session. The research
INFRASTRUCTURE is built, tested, and proven. The forward loop is LIVE and has run
TWO full iterations. This session does NOT build infrastructure — it CONTINUES
sourcing, gating, and screening NEW strategy hypotheses. That is where progress
comes from now.

**Refreshed 2026-06-09** (supersedes the 2026-06-08 "start the loop" version). The
loop has now run twice, both producing decisive TIER_D-FUNDAMENTAL rejects with no
capital risked — the funnel working. All work is on `master` (origin, `7b78007`),
dual-file DECISIONS in sync (footer 96 / next-021). TRENDING_BULL is now a
documented HARD GAP (see below).

---

## COPY EVERYTHING BELOW THIS LINE INTO THE NEW SESSION

---

I'm continuing PARAVANT, a personal autonomous crypto trading system. The research
layer's audit is closed (5 KEEP strategies = decayed bear/choppy edges, MACD_PB
retired, 7 pattern-tagged post-mortems, methodology proven by the BTF control).
The forward hypothesis loop is now LIVE and has run TWO iterations:

- **H-2026-06-002** (price breakout-continuation, reused donchian_atr): Stage-1
  14/21 PASS_MARGINAL -> trending_bull PF 0.59, N=341, DSR p=1.0 -> **TIER_D
  FUNDAMENTAL**.
- **H-2026-06-003** (perp-funding-confirmed trend, new crypto-native generator):
  Stage-1 18/21 PASS -> trending_bull PF 0.53, N=132, DSR p=1.0 -> **TIER_D
  FUNDAMENTAL**.
- A third (buy-the-dip pullback) was killed at the Stage-1 hard gate as a duplicate
  of BTP/MACD_PB — minutes, no DSR trial.

Two findings are now LOAD-BEARING for what you do next (see
`docs/research/NEGATIVE_SPACE_MAP.md`): (1) **TRENDING_BULL continuation is a HARD
GAP** — both price-momentum AND derivatives-flow continuation are dead there at
large N, so the next idea for that cell must be a DIFFERENT MECHANISM CLASS, not
another continuation variant. (2) **Calibration lesson**: H-003 scored HIGHER at
Stage 1 (18 vs 14) yet did WORSE — the scorecard measures mechanism QUALITY, not
edge; a slick crypto-native story is a yellow flag until DSR rules (DEC-018
anti-rationalization, confirmed on real data).

Your job this session is NOT to build tooling. It is to CONTINUE THE LOOP: source
-> quality-gate (reasoning scorecard, no data) -> formalize -> register -> screen
(DSR). The quality gate (DEC-2026-06-04-018,
`docs/research/HYPOTHESIS_QUALITY_GATE.md`) is a by-hand CHECKLIST. Resist building
infrastructure; if a tested hypothesis genuinely needs a new tool, add it then.

## Required reading (in this order)

1. `docs/research/RESEARCH_LAYER_PRD.md` — Sections 8 (methodology), 9 (Tier
   gate), 10 (lifecycle), Appendix B (hypothesis ledger schema).
2. `docs/research/HYPOTHESIS_QUALITY_GATE.md` — the pre-DSR quality gate
   (DEC-2026-06-04-018): reasoning scorecard + blind structural profile +
   FUNDAMENTAL/FIXABLE failure taxonomy. This is the front-end of the loop.
3. `docs/research/NEGATIVE_SPACE_MAP.md` — what's already dead and why (the
   TRENDING_BULL continuation hard gap + the Stage-1-score-vs-edge calibration
   table). Read BEFORE sourcing, so you do not re-test a dead cell.
4. `docs/research/RETROSPECTIVE_DSR_SPEC.md` — the frozen spec + the regime-DSR
   guards (Section 6.x and the DEC-2026-06-04-014 guards).
5. `.claude/CLAUDE.md` and `.claude/rules/decision-consistency.md` — project
   rules + dual-file DECISIONS sync.
6. `.claude/DECISIONS.md` — DEC-2026-06-04-008 (Tier/floor), -009 (opt-in),
   -011 (post-mortem), -012 (provability), -018 (quality gate), -019 (eval
   registration path), -020 (validation methodology: DSR != forward validation,
   optimization/MC/realism discipline), -013..-017 (audit + MACD_PB). Footer for
   next DEC ID.
7. The 5 KEEP biographies in `research/biographies/active/`, the 7 retiree
   post-mortems in `research/biographies/retired/`, and the H-002/H-003 ledger
   entries + biographies — what already failed and why, for pattern-matching.

## Current state

- ALL work is on `master`, pushed to origin (`7b78007`). Dual-file DECISIONS in
  sync (footer 96 / next-021). Work on master or a fresh feature branch.
- Live kill switch OFF (`LIVE_TRADING_ENABLED=false`). Do NOT enable it. Nothing
  is deployed; no live capital at risk.
- Paper trading is DOWN (Railway geo-block — operator action to restore).
  Backtest-based research does not need it.
- `Tier.INSUFFICIENT_DATA` exists (N=0/thin no longer reads as TIER_D_REJECT).
  Cost model still v0_unverified (conservative screen; verify vs real fills only
  when paper returns).
- Pipeline ready: `research/validation/deflated_sharpe.py` (verified DSR),
  `research/backtest/cost_model.py` (incremental-pad), `research/promotion/
  classifier.py` (Tier A/B/C/D + INSUFFICIENT_DATA), `scripts/regime_dsr.py`
  (regime-conditional backtest DSR screen), `research/hypotheses/ledger.yaml`,
  `scripts/generate_post_mortem.py` + `PostMortem` model, and
  `docs/research/NEGATIVE_SPACE_MAP.md`. Screen runs in minutes (cached) /
  ~tens of minutes (uncached).
- **Funding data channel BUILT** (H-003): `research/data/funding_rates.py`
  (fetch + cache + causal `rate_at`, leakage-guarded by construction) and
  `research/generators/funding_confirmed_trend.py`. Reuse it for any
  funding-based hypothesis (e.g. the contrarian seedbed below) — do not rebuild.

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

REGISTRATION PATH — RESOLVED (DEC-2026-06-04-019, no longer a task): new research
generators load via the factory's runtime `register_generator()` hook (so `src/`
is never edited and never imports `research/`); the eval registry feeds the SAME
regime_dsr screen. Spawn-safety note: `regime_dsr.py`'s parallel workers spawn
fresh processes and build their own factory, so a NEW research generator must be
registered INSIDE the worker, not only the parent (see DEC-019). H-002/H-003 are
already wired this way — copy that pattern.

## The research priority: a DIFFERENT MECHANISM CLASS (continuation is dead in trending_bull)

Two iterations reshaped the priority. Read `NEGATIVE_SPACE_MAP.md` first.

- **TRENDING_BULL continuation is a HARD GAP, not just uncovered.** Price-momentum
  (H-002) AND derivatives-flow (H-003) continuation both died there at large N
  (PF 0.59 / 0.53, p=1.0). Do NOT source another continuation variant for that
  cell — it will fail the same way. The next trending_bull idea must be a
  DIFFERENT MECHANISM CLASS (e.g. relative-strength/cross-sectional, breadth,
  basis/term-structure, on-chain accumulation), OR pivot to a DIFFERENT uncovered
  regime (RANGING, HIGH_VOL).
- **Highest-readiness next candidate: the funding-at-extremes CONTRARIAN seedbed.**
  It reuses the funding channel already built, but it is a GENUINELY NEW hypothesis
  (opposite direction to H-003 — fade over-crowded funding, not follow it; target
  regime HIGH_VOL / reversal, not trending_bull) so it needs its OWN
  pre-registration and Stage-1 score. NOTE: a contrarian short edge can be
  RESEARCHED/backtested (futures research is permitted, DEC-2026-05-28-001), but
  LIVE shorts remain gated by the spot-only lock until that staged plan unlocks —
  so a passing contrarian short is a research finding, not a deployable one yet.
- The decay lesson still binds: DSR p<0.3 is the gate (not PF); bias toward ideas
  that generate ENOUGH TRADES to be testable; a high Stage-1 score is NOT a
  predictor of edge (H-003 scored 18 and still failed).

## OPERATOR-REQUESTED PRIORITY (2026-06-09): the liquidation-cascade hypothesis

The operator wants to pursue a liquidation strategy and "build the liquidation
architecture." Do it the DISCIPLINED way — hypothesis-first, data-channel-on-pass
— exactly as the funding channel was built for H-003. Do NOT build a broad
"liquidation architecture" speculatively; build the minimal causal data channel a
gate-passing hypothesis actually needs.

**Why this is a strong candidate:** named counterparty (over-leveraged traders
force-liquidated at the worst price), targets an UNCOVERED regime (HIGH_VOL /
reversal — not the dead trending_bull), crypto-native, less crowded than classic
TA. Mechanism: forced de-leveraging market-sells longs (or market-buys shorts) at
any price, overshooting fair value; you provide liquidity into the cascade and
capture the snap-back.

**Direction nuance (decides deployability):**
- **LONG flush (preferred, deployable):** buy the long-liquidation flush (forced
  selling drives price below fair value -> buy the dip -> capture reversion).
  SPOT-executable, so a pass is LIVE-deployable.
- **SHORT squeeze fade (research-only):** fade a short-squeeze spike. Needs shorts
  -> gated by the spot-only live lock (DEC-2026-05-28-001); backtest is permitted,
  live is not until the staged unlock. A pass here is a research finding, not
  deployable. Prioritize the LONG version for a deployable path.

**The plan (run it through the SAME loop, in order):**
1. **Pre-register** the hypothesis (expected PF/Sharpe/N-per-year, regime=HIGH_VOL,
   explicit fail modes) BEFORE building anything.
2. **Stage-1 scorecard.** Mechanism is strong; be HONEST on two dimensions:
   (a) **crowding** — liquidation levels are publicly visible (Coinglass maps), so
   "buy when liquidations happen" is a known game; the mechanism must be MORE
   specific (e.g. cascade magnitude/velocity threshold, exhaustion signal) than
   "liquidations occurred"; (b) **feasibility/N** — big cascades are RARE, so
   reaching N>=30 in HIGH_VOL is the #1 risk; decide up front how (lower the
   cascade threshold for more/smaller events, or pool across symbols) and accept
   that below min-N the cell is descriptive, not gating.
3. **IF it clears Stage 1: build the liquidation DATA CHANNEL** — a Coinglass
   adapter mirroring `research/data/funding_rates.py`: fetch + cache + a CAUSAL
   accessor (liquidation data as-known-at-decision-time; leakage-guarded by
   construction; no revised/future values). FREE Coinglass tier only — paid
   alt-data is deferred to >=$25k capital (DEC-2026-06-04-005). THIS is the
   "architecture," and it is justified because a gate-passing hypothesis needs it.
4. **Implement** the generator in `research/generators/`, register via the factory
   hook (DEC-019), spawn-safe (register inside the worker).
5. **Screen** via `python -m scripts.regime_dsr --strategy <id>` (pooled +
   per-regime, honest K). Verdict -> biography; tag FUNDAMENTAL/FIXABLE; update the
   negative-space map.

If Stage 1 fails (most likely on crowding or N-feasibility), STOP — no data
channel, no DSR trial, record the reason. The discipline is what makes this cheap.

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

## The non-negotiable guards (DEC-2026-06-04-014, -008, -018, -020)

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

- **Restore paper trading** (Railway geo-block, operator action). Once back, the
  ONE existing watchlist candidate is **VBB** (its choppy_bear/choppy_bull edge is
  the only one that persists weakly into the present) — paper-validate it IN-REGIME
  via the router, never unconditionally. This is separate from sourcing new
  hypotheses; do not let it gate the research loop.
- **Cost-model verification** — verify the v0 cost model against real fills only
  after paper data returns. Until then, every verdict is the conservative screen.

(Done already: branch merged + pushed to origin; MACD_PB retired w/ post-mortem
(DEC-017); registration path resolved (DEC-019); validation-methodology principles
filed (DEC-020). The loop has run twice — H-002/H-003 both TIER_D FUNDAMENTAL.)

## Rules you MUST follow

- One-way dependency: `src/` never imports `research/`.
- Biography YAML canonical; markdown/JSON derived.
- Dual-file DECISIONS sync (`.claude/` AND `.agent/`, verify `diff` empty).
- Zero-tech-debt: full type hints, Google docstrings, timezone-aware datetimes,
  structured logging, no emojis/unicode in code. Tests for new code (>=80%).
- Do NOT enable live trading. Do NOT modify Neon data. Do NOT touch Railway region.
- Do NOT build new infrastructure unless a tested hypothesis demonstrably needs it.

## How to start

1. Read the required docs — ESPECIALLY `NEGATIVE_SPACE_MAP.md` + the H-002/H-003
   ledger entries — so the dead cells and the calibration lesson are in your head
   before you source.
2. Pick the target: either a NEW MECHANISM CLASS for trending_bull (NOT another
   continuation variant), or a DIFFERENT uncovered regime (RANGING / HIGH_VOL).
   The highest-readiness option is the funding-at-extremes contrarian seedbed
   (reuses the funding channel; needs its own pre-registration; research-only for
   live shorts per the spot lock).
3. Use TodoWrite. Source -> Stage 1 reasoning scorecard (hard gates + score) ->
   formalize (pre-register) -> implement+register (factory hook, DEC-019) ->
   Stage 2 blind structural profile (optional) -> Stage 3 DSR screen -> verdict
   (tag FUNDAMENTAL/FIXABLE; update the negative-space map). One hypothesis at a
   time; most fail cheaply at the scorecard — that is success, not failure.

## END COPY

---

**Note for Eva**: The loop is live and self-evidently working — two decisive
rejects, no capital risked, and the quality gate already killing a duplicate at
Stage 1 for free. The bottleneck now is GOOD, GENUINELY-DIFFERENT IDEAS, not
tooling. Three things the new session must internalize: (1) trending_bull
continuation is DEAD (two mechanism classes failed at large N) — the next idea for
that cell must be a different mechanism class, or aim at another regime; (2) a high
Stage-1 score does NOT predict edge (H-003 scored 18/21 and still failed) — the
scorecard rations DSR trials, it does not forecast winners; (3) the graveyard +
negative-space map are now live libraries — consult them before sourcing. The
funding channel is built and reusable for the contrarian seedbed.
