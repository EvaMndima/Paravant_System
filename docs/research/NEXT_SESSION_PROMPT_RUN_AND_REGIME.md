# Session Bootstrap Prompt — Run Retrospective DSR, Ratify, Merge, then Scope Regime-Conditional DSR

**Purpose**: Paste the block below into a fresh Claude Code session. It covers the
remaining Phase R0.5 work (run the retrospective on Neon, review, ratify tier
changes, merge) and then scopes the next capability (regime-conditional backtest
DSR).

**Written 2026-06-05** by the session that built + reviewed the retrospective DSR
tooling. Current state: tooling built, code-reviewed, cost diagnostic added.
Branch `feat/research-retrospective-dsr` (latest commit `27517ef`), 77 tests
passing. NOT merged to master.

---

## COPY EVERYTHING BELOW THIS LINE INTO THE NEW SESSION

---

I'm continuing PARAVANT, a personal autonomous crypto trading system. The Phase
R0.5 retrospective DSR tooling is BUILT, code-reviewed, and committed on branch
`feat/research-retrospective-dsr` (commit `27517ef`, 77 research tests passing).
The DSR math module is verified from first principles. Your job this session has
two phases. Do Phase A first; Phase B only after Phase A is complete.

## Required reading (in this order)

1. `docs/research/RETROSPECTIVE_DSR_SPEC.md` — the frozen spec (read the header
   build-status block, Sections 4, 5, 5.5, 6.4, 6.5, 9.1, 12).
2. `docs/research/RESEARCH_LAYER_PRD.md` — Sections 8, 9, 10, 13.4, Appendix A.
3. `.claude/CLAUDE.md` — project rules (zero-tech-debt, venv, structured logging,
   decision consistency).
4. `.claude/rules/decision-consistency.md` — dual-file DECISIONS sync rule.
5. `.claude/DECISIONS.md` — read DEC-2026-06-04-001 through the latest (check the
   footer for the next available DEC ID; DEC-2026-06-04-013 is already filed).

## Current state

- On branch `feat/research-retrospective-dsr`. Master is untouched.
- `research/validation/deflated_sharpe.py` (verified), `cost_model.py`,
  `effective_k.py`, `promotion/classifier.py`, `biographies/schema.py`,
  `scripts/retrospective_dsr.py`, `scripts/show_strategy.py` all built + tested.
- Live kill switch OFF (`LIVE_TRADING_ENABLED=false`). Do NOT enable it.
- Paper trading is DOWN (Railway geo-block) — does not block this work.
- Real trade data lives ONLY in Neon. Local `.env` points at an empty SQLite.
- Cost reality (DEC-2026-06-04-013): recorded `return_pct` is already net of the
  simulator's costs (percent units); the conservative case subtracts only the
  incremental pad; slippage is estimated/padded (no signal/fill prices).

## PHASE A — Run the retrospective, review, ratify, merge

### A1. Operator runs the retrospective (NOT you)

The real run is the OPERATOR's action, to keep prod Neon credentials out of the
agent environment (read-only-Neon discipline). Tell the operator (Eva) to run,
from an activated venv, with the read-only Neon URL set:

```
.venv\Scripts\activate
$env:DATABASE_URL = '<read_only_neon_url>'
python -m scripts.retrospective_dsr
```

This writes 11 biographies to `research/biographies/{active,retired}/` plus
markdown + portfolio summary + JSON to `docs/research/retrospective/`. It is
read-only against Neon. If the operator has already run it, proceed to A2.

### A2. Review the outputs (this is your main job)

Read the generated biographies and `docs/research/retrospective/PORTFOLIO_SUMMARY_*.md`. Check, in this order:

1. **BTF is the calibration control.** BTF is the known-bad strategy (Q1 100% WR
   -> live PF 0.75). If BTF comes back with a deployable/low-p verdict, the
   instrument is BROKEN — STOP and investigate before trusting anything else.
   Expect BTF at Tier D.
2. **The booked/incremental cost diagnostic.** In the run log, check the
   `operator_cost_check` lines and any `booked_cost_near_zero` WARNING. If mean
   booked cost is ~0 across strategies, the historical records lack the
   commission/slippage fields and the conservative case is DOUBLE-CHARGING — do
   NOT trust any Tier-D verdict until that is resolved. This is the single most
   important data-integrity check.
3. **Read base + gap + ranking, not just the conservative tier.** The
   conservative gate is deliberately brutal (gating K + high variance_sr); most
   strategies may land Tier C/D under it. The signal is in: the BASE-case tier,
   the GAP (`verdict_is_fragile` / base_tier vs conservative_tier), and the
   ranking by DSR p-value. A Tier-A-base / Tier-D-conservative strategy is
   real-but-fragile (more data, not retire); Tier D in BOTH is genuinely dead.
4. **variance_sr sanity.** Eyeball the derived `variance_sr` point estimate. If
   it looks inflated by including the terrible RETIRED strategies, note it — the
   BASE case is the more honest read at v0.

### A3. Ratify tier changes (operator-approved, dual-file)

For any KEEP strategy whose retrospective verdict differs from its current live
status (e.g. MACD_PB -> Tier B at 50% slice, or a strategy -> Tier C/D):

- File a decision in BOTH `.claude/DECISIONS.md` AND `.agent/DECISIONS.md`
  (identical; verify `diff` is empty). Use the next available DEC ID from the
  footer.
- These are RECOMMENDATIONS requiring operator ratification (opt-in,
  DEC-2026-06-04-009). Do NOT auto-change live config. Present the verdicts and
  let the operator decide; record the decision they make.
- Update the relevant biography `decision_log` and `current_classification`.

### A4. Commit + merge

- Commit the generated biographies + reports to the branch (they are canonical
  YAML — committing starts the git-versioned audit trail).
- Run the full research suite: `python -m pytest tests/research/ -q` (expect 77
  passed, 1 skipped).
- Merge `feat/research-retrospective-dsr` into master ONLY after the run produced
  sane output and BTF passed the calibration check. `research/` does not deploy
  to Railway (one-way dependency, not in `requirements.txt`), so merging is
  low-stakes — but validate real-data output first.

## PHASE B — Scope (do NOT fully build yet) regime-conditional backtest DSR

This is the next capability: tell us, off the gate, what strategy belongs in
which regime, by computing DSR PER REGIME on historical backtest data — BEFORE
paper trading. It directly answers the portfolio-construction question and
produces a regime-coverage matrix (strategy x regime -> verdict) that reveals
gaps (e.g. TRENDING_BULL uncovered).

### B1. File a hypothesis-ledger entry + a decision

- Add an entry to `research/hypotheses/ledger.yaml` (create it if absent, per PRD
  Appendix B) describing regime-conditional backtest DSR.
- File a decision (both DECISIONS.md files) capturing the design + the
  non-negotiable guards below.

### B2. The design + the guards (these are the whole point)

Regime-conditional DSR computes DSR separately within each regime bucket of a
strategy's BACKTEST trades. The guards that keep it honest:

1. **It is a SCREEN, not a deployment gate.** Backtest edge degrades live. This
   tells you which strategy x regime pairs are WORTH paper-trading; paper/live
   remains the deployment gate. Never let a regime-DSR-validated backtest bypass
   paper validation.
2. **K must count regime-buckets as trials.** Effective K =
   param-combos x symbols x timeframes x REGIME-BUCKETS. Testing 8 regimes and
   keeping the best is selection bias across regimes; if K does not penalize it,
   the deflation is fake. Reuse `research/validation/effective_k.py` and extend
   the K derivation to include the regime-bucket count.
3. **Causal regime tagging (leakage check).** Each trade is tagged with the
   SubRegime active AT ENTRY using only data available at that time. The
   `historical_classifier` (`src/core/strategy/regime/historical_classifier.py`)
   is reused by the live detector so it should be causal — but verify explicitly
   (no future bars in the regime label) and add a leakage test.
4. **Coarse buckets where N is thin.** Splitting trades across 8 SubRegimes
   leaves too few per bucket for DSR. Start with coarse buckets (bull/bear/chop);
   use finer SubRegimes only where per-bucket N supports it. Per-bucket results
   below a minimum N are DESCRIPTIVE, not gating.
5. **DSR is necessary, not sufficient.** A regime-DSR pass means the backtest
   edge is distinguishable from selection-bias luck — a strong screen, not a
   guarantee of live performance.

### B3. Reuse, do not reinvent

- DSR: `research/validation/deflated_sharpe.py` (built, verified).
- K: `research/validation/effective_k.py` (extend for regime-buckets).
- Regime labels: `src/core/strategy/regime/historical_classifier.py`.
- Backtest engine: `src/core/strategy/backtest/` (research imports from src/).
- Biography `regime_coverage` fields already exist (PRD Appendix A).

### B4. BTF as the first regime-conditional subject

Once built, re-backtest BTF over its FULL history (not the thin Q1 live sample)
with regime tagging, to ask honestly: did BTF ever have real (DSR-validated)
edge in a specific regime, or was it overfit throughout? Expect the answer to be
limited by BTF's thin data — but this is the right way to ask the question.

## Architectural rules you MUST follow (both phases)

- One-way dependency: `src/` never imports `research/`; `research/` imports
  `src/` freely.
- Biography YAML is canonical; markdown/JSON are derived.
- DSR p<0.3 is the non-negotiable deployment floor (DEC-2026-06-04-008); no
  override path.
- Dual-file DECISIONS sync (`.claude/` AND `.agent/`, verify `diff` empty).
- Zero-tech-debt: full type hints, Google docstrings, timezone-aware datetimes,
  structured logging via `src/utils/logging.get_logger()`, no emojis/unicode in
  code.
- Tests for all new code (>=80% coverage). Run `python -m pytest tests/research/ -q`.
- Do NOT enable live trading. Do NOT modify Neon data (read-only). Do NOT touch
  the Railway region.

## How to start

1. Read the required documents.
2. State in plain English what Phase A and Phase B are.
3. Ask the operator whether the Neon run (A1) has been done yet; if so, go
   straight to A2 review; if not, give them the exact command and wait.
4. Use TodoWrite to track progress.
5. Do Phase A fully (run review -> ratify -> merge) before starting Phase B.

## END COPY

---

**Note for Eva**: Phase A is the immediate next step and produces THE finding
(how many of your 5 KEEP strategies survive honest costs). Phase B (regime-
conditional DSR) is the next capability — the session should SCOPE and file it,
but only fully build it after Phase A merges and you have decided to proceed.
Keep them separate so the run is not blocked by the new build.
