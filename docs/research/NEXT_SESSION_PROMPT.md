# Session Bootstrap Prompt — Research v0.5 Implementation

**Purpose**: Paste this prompt into a fresh Claude Code session to begin implementation of the Research Layer v0.5 (specifically: retrospective_dsr.py + supporting modules + show_strategy.py CLI).

**Context**: This prompt was written 2026-06-04 by a previous session that ratified Research Layer PRD v2.0 and filed DEC-2026-06-04-001 through DEC-2026-06-04-012. The previous session also wrote the implementation spec at `docs/research/RETROSPECTIVE_DSR_SPEC.md`. The current session's job is to BUILD what that spec describes.

---

## COPY EVERYTHING BELOW THIS LINE INTO THE NEW SESSION

---

I'm continuing work on PARAVANT, a personal autonomous crypto trading system. In a previous session we ratified the Research Layer PRD v2.0 and filed 12 decisions. Your job in this session is to BUILD the first artifacts of that layer.

## What you're building

**IMPORTANT — the hardest part is already built and verified.** The DSR math
module (`research/validation/deflated_sharpe.py`) and its 29-test suite
(`tests/research/test_deflated_sharpe.py`) were written and verified on
2026-06-05 (all passing, math validated from first principles to 1e-12). DO NOT
rewrite them. Build on top of them.

Two related artifacts to complete:

1. **`scripts/retrospective_dsr.py`** — applies the (already-built) Deflated Sharpe Ratio + a conservative cost model retroactively to existing 5 KEEP strategies (MACD_PB, BTP, VBB, SRC, ICVP) and 6 RETIRED strategies (BTF, CMF, RSI_BB, HATP, VRB, VPT). PRIMARY output: updates to strategy biography YAMLs at `research/biographies/<strategy_id>.yaml`. Markdown reports are DERIVED views, not canonical storage. Pools each strategy's trades across symbols into ONE DSR (not per-symbol). Reports DSR at multiple K values.

2. **`scripts/show_strategy.py`** — strategy card CLI that pretty-prints a biography YAML to the terminal. Read-only. Helps the operator review strategies without opening YAML files manually. **Build this AFTER the DSR run produces biographies worth viewing** (it has nothing to render until then).

These are Phase R0.5 priority deliverables per the PRD.

## Required reading (in this order)

1. **`docs/research/RETROSPECTIVE_DSR_SPEC.md`** — the full implementation spec (v2, revised 2026-06-05 after external review). Read every section. Sections 4 (DSR module — BUILT), 5 (cost model — realized slippage + single-pad conservatism), 5.5 (pooled not per-symbol DSR), 6 (DB-derived K + multi-K sweep), 9-10 (remaining build order + execution gate), 14 (show_strategy CLI) are most important. The header "Build status" block lists what is DONE vs REMAINING.
2. **`docs/research/RESEARCH_LAYER_PRD.md`** — context for the architecture. Focus on Sections 5, 6.1, 8, 9, 10, 13.4, and Appendix A (strategy biography schema).
3. **`.claude/CLAUDE.md`** — project rules. Especially: zero-tech-debt standards (Section 3), venv activation requirement (Section 2), structured logging (Section 11), decision consistency (Section 1).
4. **`.claude/rules/decision-consistency.md`** — dual-file sync rule. ANY decision entries you create must go in BOTH `.claude/DECISIONS.md` AND `.agent/DECISIONS.md` (verify with `diff`).
5. **`.claude/DECISIONS.md`** lines 2495-3050 approximately — read DEC-2026-06-04-001 through DEC-2026-06-04-012 to understand the architectural decisions you must honor.

## Current state of the system

- Paper trading is currently DOWN due to Railway geo-block (DEC-2026-06-01-003) — does NOT block this work; retrospective DSR uses existing trade logs from before the outage.
- Live trading kill switch is OFF (`LIVE_TRADING_ENABLED=false`). Do NOT enable it.
- Working capital: $20 paper, $100 minimum for live (per DEC-2026-05-31-003).
- 5 KEEP strategies live in `STRATEGY_CONFIG` (find it in the codebase): MACD_PB, BTP, VBB, SRC, ICVP. 6 RETIRED in 2026-05-27 to 2026-05-28 triage: BTF, CMF, RSI_BB, HATP, VRB, VPT. ICVP has `observe_only: True` flag.
- `research/` directory PARTIALLY exists: `research/__init__.py`, `research/validation/__init__.py`, `research/validation/deflated_sharpe.py` (BUILT + VERIFIED), and `requirements-research.txt` are done. You create the REMAINING subdirs (`research/backtest/`, `research/promotion/`, `research/biographies/`, `research/hypotheses/`, `research/catalog/`) per PRD Section 5.1.
- `tests/research/__init__.py` + `tests/research/test_deflated_sharpe.py` exist (29 passing). Add more test files alongside.
- Decisions DEC-2026-06-04-001 through DEC-2026-06-04-012 are FILED. Do not duplicate them.

## Architectural rules you MUST follow

These are non-negotiable per the PRD and project rules:

1. **One-way dependency**: `src/` does NOT import from `research/`. `research/` imports from `src/` freely. Violations are bugs to fix immediately.

2. **Biography YAML is canonical**: DSR results, tier classification, cost-adjusted metrics live in `research/biographies/<strategy_id>.yaml`. Markdown reports are DERIVED — never write canonical data ONLY to markdown.

3. **DSR p<0.3 is the non-negotiable statistical floor** (DEC-2026-06-04-008). A strategy with DSR p≥0.3 cannot classify as Tier A or B. No override path exists. The DSR module (`research/validation/deflated_sharpe.py`) is BUILT — use it, do not reimplement. `dsr_p_value` (LOW = good) is the gating field.

3a. **Pooled DSR, not per-symbol** (Spec 5.5): pool each strategy's cost-adjusted, quarantine-filtered per-trade returns across ALL its symbols into ONE chronological series, call `deflated_sharpe_ratio` ONCE. Per-symbol PF/Sharpe may appear in reports as DESCRIPTIVE only, never gating. DSR is not weight-averageable.

3b. **Multi-K sweep + conservative gating K** (Spec 6): report DSR at K in {115, 500, 2000} plus a DB-derived estimate. The GATING verdict uses the highest defensible (most conservative) K. If the tier flips across the K range, set `verdict_is_fragile: true` and cap at Tier C. Derive K from recorded parameter-combination counts (e.g. MACD_PB opt_001 = 96 combos), NOT a hardcoded guess. Store K and its derivation in the biography.

3c. **Realized slippage + single-pad conservatism** (Spec 5): compute slippage empirically from signal_price vs fill_price where available; only apply the 2x pad to components that remain ESTIMATED. Do NOT stack 95th-percentile spread AND 2x on the same quantity. Print per-symbol round-trip cost so the operator can sanity-check it. Charge entry-leg cost on entry notional, exit-leg cost on exit notional (Spec 5.5-pre).

3d. **Execution gate** (Spec 10.1): `retrospective_dsr.py` MUST run the DSR test suite at the top of `main()` and refuse to proceed on real data if it fails. A miscalibrated instrument is worse than none.

3e. **Sweep variance_sr like K + base-vs-conservative reporting** (Spec 6.4, 6.5): `variance_sr` is as decisive as K and is estimated from a biased 11-strategy sample — sweep it unconditionally. Report every strategy at a BASE case (measured costs, point-estimate K + variance_sr) AND a CONSERVATIVE case (padded costs, high K + variance_sr). GATE on conservative, SHOW base. `fragility = base_tier != conservative_tier`; a real-but-fragile strategy (Tier A base, Tier D conservative) is flagged for more data, NOT retired.

3f. **Operational guards** (Spec 9.1): idempotent biography writes (key appends on `run_id`, skip if present — a crash at strategy 7/11 must be safely re-runnable); recompute MaxDD on the pooled cost-adjusted series (`max_dd_pct_pooled_adjusted`), NOT the legacy backtest figure — the hard floor gates on the recomputed value.

4. **PARA-02 quarantine filter MUST be applied**: corrupt force-close trades excluded from analysis per DEC-2026-05-31-002. Reuse `_is_corrupt_force_close` from `scripts/validation_report.py` if possible (single source of truth).

5. **Dual-file DECISIONS sync**: if your work results in any new DEC entry (e.g., a tier change), file IDENTICALLY in both `.claude/DECISIONS.md` AND `.agent/DECISIONS.md`. Verify with `diff`. Next available ID is DEC-2026-06-04-013.

6. **Zero-tech-debt code quality** (project rule):
   - Full type hints (100% coverage)
   - Google-style docstrings on all public functions/classes
   - Timezone-aware datetimes (`datetime.now(timezone.utc)`, never `datetime.utcnow()`)
   - Lambda for mutable defaults (never `default={}` or `default=[]`)
   - Structured logging via `src/utils/logging.get_logger()` (never f-strings in log messages)
   - No emojis or unicode characters in code generation

7. **Venv activation**: activate `.venv\Scripts\activate` (Windows) before running any Python. `requirements-research.txt` is DONE (scipy is optional — the DSR core is pure-stdlib by design). `pip install -r requirements-research.txt` if you need scipy for the optional test cross-check or later phases.

8. **Tests required before marking complete**:
   - ~~DSR formula validated~~ DONE (29 tests passing, `tests/research/test_deflated_sharpe.py`)
   - Cost model unit tests on synthetic trades, including measured-vs-estimated pad split + hand-checked DOGE round-trip (Spec 5.3)
   - Effective-K test: DB-derived K includes parameter combinations; multi-K sweep monotonic
   - PARA-02 quarantine confirmed by test
   - Integration test confirms pooled (not per-symbol) DSR
   - show_strategy.py renders all 11 biographies without error
   - At least 80% coverage on new code

## Implementation order (suggested)

The spec lists 8 sub-tasks totaling 12-16 hours for retrospective_dsr.py + 4-6 hours for show_strategy.py. Recommended sequencing:

**Day 1** (foundation — note DSR module + requirements-research.txt already DONE):
1. Create REMAINING `research/` subdirs (`backtest/`, `promotion/`, `biographies/{active,retired}/`, `hypotheses/`, `catalog/`) per PRD Section 5.1
2. Create `research/biographies/schema.py` (Pydantic models for biography structure — Appendix A of PRD)
3. Database schema reconnaissance: read `src/data/models/` to confirm the trade-log table structure; CRITICALLY confirm whether `signal_price` and `fill_price` (or equivalents) exist — they are needed for realized slippage (Spec 5.1). Write a small probe script to read trade logs.
4. Verify the DSR module is intact: `python -m pytest tests/research/test_deflated_sharpe.py -q` (should show 29 passed, 1 skipped)

**Day 2** (math + cost model):
5. Build `research/backtest/cost_model.py` — per-symbol cost model with v0_unverified defaults
6. Build `research/validation/deflated_sharpe.py` — DSR formula from spec Section 4
7. Build `research/validation/effective_k.py` — K counting per spec Section 6
8. Unit tests for all of above

**Day 3** (orchestration + reports):
9. Build `scripts/retrospective_dsr.py` — main script, loops through 11 strategies
10. Write to biography YAMLs (PRIMARY output) per spec Section 3
11. Generate derived markdown reports per spec Section 3.1
12. Generate portfolio summary per spec Section 3.2
13. Run on all 11 strategies and check results

**Day 4** (companion tool + polish):
14. Build `scripts/show_strategy.py` — CLI per spec Section 14
15. Polish, integration tests, documentation
16. Git commit (per project commit standards — Conventional Commits)

## Honest expectations (from the spec)

- **1-3 of 5 KEEP strategies likely drop to Tier B or C** under DSR with honest cost model. This is GOOD information — don't try to "save" strategies by relaxing thresholds.
- **Most RETIRED strategies likely validated** by DSR (p>0.5 confirms our retirement decisions were correct).
- **At least one surprise possible** — a RETIRED strategy that surfaces with DSR p<0.3 warrants re-examination.
- **Cost model v0 is INTENTIONALLY conservative** (2x multiplier). Strategies surviving v0 are more likely to be real edge. Strategies failing v0 are unlikely to recover under calibrated v1.

## What you must NOT do

- Do NOT enable live trading (`LIVE_TRADING_ENABLED` stays OFF — DEC-2026-05-27-001)
- Do NOT modify production code in `src/core/strategy/generators/` (research code goes in `research/`)
- Do NOT modify trade log data in Neon database (read-only access; quarantine is a read-time filter)
- Do NOT skip the venv activation
- Do NOT skip writing tests
- Do NOT skip the dual-file DECISIONS sync if filing any decision
- Do NOT add features beyond the spec (no scope creep — PRD Section 15.1 explicitly warns against tool fetishism)
- Do NOT use any of the deferred V1 packages (Glassnode, CryptoQuant — these are deferred to capital ≥ $25k per DEC-2026-06-04-005)
- Do NOT touch the Railway region (separate operator action)
- Do NOT skip pre-implementation reading (the spec is detailed; reading it carefully saves implementation time)

## How to start

Begin by:

1. Reading the required documents listed above (in order)
2. Confirming you understand the spec by stating in plain English: "I am about to build retrospective_dsr.py which will compute DSR + conservative costs for 11 strategies, writing PRIMARY output to research/biographies/*.yaml. The strategy-card CLI show_strategy.py reads those biographies for terminal display."
3. Running the database schema reconnaissance (Day 1, step 4) to confirm table/field names before writing the cost model module
4. Asking the operator (Eva) any clarifying questions BEFORE writing significant code
5. Using TodoWrite to track progress across the implementation

## Acceptance criteria (when this session is done)

- [ ] `research/` directory tree exists per PRD Section 5.1
- [ ] `requirements-research.txt` created and installed
- [ ] Database schema confirmed — `paper_trades` table structure documented in the spec if it differs from assumptions
- [ ] `research/backtest/cost_model.py` works with unit tests passing
- [ ] `research/validation/deflated_sharpe.py` works, validated against Bailey-LdP examples
- [ ] `research/validation/effective_k.py` works with proper K counting
- [ ] `research/biographies/schema.py` defines biography structure (Pydantic models)
- [ ] `scripts/retrospective_dsr.py` runs successfully on all 11 strategies
- [ ] 11 biography YAMLs created with full classification + DSR + cost-adjusted metrics
- [ ] Markdown reports generated for all 11 strategies
- [ ] Portfolio summary report generated with headline findings
- [ ] `scripts/show_strategy.py` renders all 11 biographies cleanly
- [ ] Test coverage ≥ 80% on new code
- [ ] PARA-02 quarantine verified applied (zero corrupt trades in analysis)
- [ ] Any tier changes from KEEP strategies filed as DEC entries in BOTH `.claude/DECISIONS.md` AND `.agent/DECISIONS.md` (dual-file sync verified)
- [ ] Findings summarized for operator (Eva) review
- [ ] Git commit per Conventional Commits standard

## After this session completes

The retrospective DSR results will inform:
- Whether 5 KEEP strategies remain at full capital, demote to Tier B at 50% slice, or halt/retire
- Whether the cost model assumptions need calibration (Phase R0.5 Week 2-3 work)
- Direction for Phase R1 (statistical rigor polish)

The operator (Eva) reviews findings and ratifies any tier changes. The Railway region change happens in parallel (separate operator action) so paper trading can resume.

---

## END COPY

---

**Notes for Eva (the operator) on using this prompt**:

- Open a new Claude Code session in the project directory
- Paste the prompt content (everything between "COPY EVERYTHING BELOW THIS LINE" and "END COPY")
- The new session will read the spec, ask any clarifying questions, then start building
- You should be available for questions during database schema reconnaissance (Day 1)
- Estimated total implementation time: 2-4 focused days, depending on database schema surprises and how much help the new session needs

**This file is the snapshot of context for the next session — keep it for reference but the prompt itself is what gets pasted into the new conversation.**
