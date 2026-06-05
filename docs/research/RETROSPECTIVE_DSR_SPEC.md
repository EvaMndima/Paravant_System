# `scripts/retrospective_dsr.py` — Implementation Spec

**Status:** SPEC v2 — DSR math module BUILT + VERIFIED (29 tests passing); remaining orchestration awaiting implementation session
**Date:** 2026-06-04 (revised 2026-06-05 after external review + DSR module verification)
**Owner:** Eva + Claude
**Phase:** Research v0.5 — Week 1, Day 1-3 (highest-priority first artifact per DEC-2026-06-04-001)

**Build status (2026-06-05):**
- DONE + VERIFIED: `research/validation/deflated_sharpe.py` + `tests/research/test_deflated_sharpe.py` (29 tests passing, math validated from first principles to 1e-12)
- DONE: `research/__init__.py`, `research/validation/__init__.py`, `requirements-research.txt`
- REMAINING (next session): cost model, DB trade-log reader, tier classifier, orchestration, biography writer, derived reports, `show_strategy.py`

**Related:**
- `docs/research/RESEARCH_LAYER_PRD.md` v2.0 (Section 6.1, 8.5, 9 — Tier classification)
- DEC-2026-06-04-002 (mandatory methodology primitives)
- DEC-2026-06-04-008 (Tier A/B/C/D classification)

---

## 1. Purpose

Apply the Deflated Sharpe Ratio (Bailey/Lopez de Prado 2014) and a conservative per-symbol cost model **retroactively** to the existing 5 KEEP strategies (MACD_PB, BTP, VBB, SRC, ICVP) and the 6 RETIRED strategies (BTF, CMF, RSI_BB, HATP, VRB, VPT). Output is a markdown report per strategy with Tier A/B/C/D classification under honest methodology.

**Why this runs FIRST**: highest information-to-effort ratio in the entire Research Layer roadmap. Uses existing trade logs (no new tooling required beyond the DSR calculation), takes days not weeks, and could materially change the strategy portfolio BEFORE any live capital is risked. Honest expectation per PRD Section 14.1: 1-3 of the 5 KEEP strategies likely fall to Tier B or C under honest methodology.

## 2. Inputs

### 2.1 Trade Logs Source

The script reads from the existing Neon database (read-only, no writes):
- Table: `paper_trades` (or whatever the existing trade table is — to be verified during implementation)
- Filter: per-strategy, per-symbol, per-session
- Required fields: `entry_price`, `exit_price`, `entry_time`, `exit_time`, `quantity`, `side`, `symbol`, `template_id`, `session_id`, `force_close` (for PARA-02 quarantine filtering)

### 2.2 Strategy Universe (Hardcoded for v0.5)

```python
KEEP_STRATEGIES = [
    "MACD_PB",   # DOGE, AVAX
    "BTP",       # BTC, ETH, BNB, DOGE
    "VBB",       # BTC, ETH, SOL
    "SRC",       # BTC, ETH, SOL
    "ICVP",      # 7 symbols
]

RETIRED_STRATEGIES = [
    "BTF",       # PF 0.75 live — the cautionary tale
    "CMF",       # POOR all 3 bear/chop regimes
    "RSI_BB",    # PF 0.06-0.41 across regimes
    "HATP",      # 231 trades, POOR all 4 regimes (BTF-pattern overfit)
    "VRB",       # BTC-only, no robust verdict
    "VPT",       # PF 1.00, loses after slippage
]
```

### 2.3 Cost Model Parameters

For the retrospective analysis (no time to validate cost models against 10+ fills per symbol yet, per DEC-2026-06-04-002):

```python
# v0 default cost model (2x conservative per PRD Section 8.2)
DEFAULT_SPREAD_PCT_BY_SYMBOL = {
    "BTCUSDT":  0.02,  # tight spread
    "ETHUSDT":  0.04,
    "BNBUSDT":  0.05,
    "SOLUSDT":  0.08,
    "AVAXUSDT": 0.10,
    "DOGEUSDT": 0.15,  # widest spread of the set
    "XRPUSDT":  0.08,
    # Add others as needed — DEFAULTS to 0.20% if symbol not listed (extra conservative)
}

BINANCE_TAKER_FEE_PCT = 0.10  # 0.075 with BNB, but assume worst case 0.10 for safety
SLIPPAGE_PCT_DEFAULT = 0.05  # per-side default; doubled by 2x conservative multiplier

# Total round-trip cost per trade:
# round_trip_cost_pct = 2 * (spread/2 + fee + slippage) * conservative_multiplier (2x)
# Where spread/2 because you cross half the spread on each side
```

**Verification gate**: This is the UNVERIFIED cost model. Any strategy that survives this conservative cost model is more likely to be real edge. Any strategy that fails this model needs the calibrated (verified) cost model in a follow-up run before final verdict — but a strategy failing the 2x-conservative model is very unlikely to recover under the calibrated one.

## 3. Outputs

**Data architecture clarification (updated 2026-06-04 per operator feedback)**:

The PRIMARY outputs are updates to canonical strategy data (biography YAML + decision log). Markdown reports and JSON are DERIVED views for human consumption — they can be regenerated from the canonical data at any time.

| Layer | Output | Status |
|---|---|---|
| **PRIMARY** | `research/biographies/<strategy_id>.yaml` updates — DSR p-value, tier classification, cost-adjusted metrics, run timestamp | Canonical (source of truth) |
| **PRIMARY** | `research/hypotheses/ledger.yaml` status field updated based on new tier | Canonical |
| **PRIMARY** | Decision filed in `DECISIONS.md` (both `.claude/` and `.agent/`) if classification changes (e.g., MACD_PB demotes from TIER_A to TIER_B) | Canonical |
| **DERIVED** | Per-strategy markdown report at `docs/research/retrospective/<strategy_id>_<YYYY-MM-DD>.md` | Generated from biography; can be regenerated any time |
| **DERIVED** | Portfolio summary report at `docs/research/retrospective/PORTFOLIO_SUMMARY_<YYYY-MM-DD>.md` | Generated from all biographies |
| **DERIVED** | JSON output at `docs/research/retrospective/results_<YYYY-MM-DD>.json` | Generated from biographies for programmatic use |

**Flow**:
1. Compute DSR + cost-adjusted metrics from trade logs in database (Layer 4 / Neon)
2. WRITE result into `research/biographies/<strategy_id>.yaml` — this is the canonical update
3. UPDATE `research/hypotheses/ledger.yaml` status field
4. IF classification changed: file decision in `.claude/DECISIONS.md` AND `.agent/DECISIONS.md` (dual-file sync per Rule 0)
5. RENDER markdown report from biography (derived)
6. RENDER portfolio summary report from all biographies (derived)
7. RENDER JSON from biographies (derived)

**Critical property**: If the markdown report is deleted, it can be regenerated from biography YAML in one command. If the biography YAML is corrupted, it can be reconstructed from database trade logs + this script. **The biography is the strategy's identity**; markdown is a presentation layer.

### 3.0 Biography YAML Update Schema (PRIMARY OUTPUT)

After each retrospective DSR run, the strategy biography is updated as follows:

```yaml
# research/biographies/MACD_PB.yaml (excerpt — fields added/updated by this script)

current_classification: TIER_A_FULL_READY  # or TIER_B, TIER_C, TIER_D

classification_history:
  # APPEND new entry, do not overwrite existing
  - date: 2026-06-04
    classification: TIER_A_FULL_READY
    triggered_by: retrospective_dsr_run_20260604
    cost_model_version: v0_unverified
    dsr_p_value: 0.18
    notes: "Initial retrospective DSR with conservative cost model"

statistical_validation_history:
  # APPEND new entry
  - run_date: 2026-06-04
    run_id: retrospective_dsr_run_20260604
    cost_model_version: v0_unverified
    effective_k: 115
    pf_raw: 1.62
    pf_adjusted: 1.43  # after honest cost model
    sharpe_raw: 1.34
    sharpe_adjusted: 1.18
    max_dd_pct_adjusted: 4.2
    n_trades_analyzed: 47
    skewness: -0.18
    kurtosis: 3.42
    dsr_z_score: 1.06
    dsr_p_value: 0.18
    pbo_score: null  # not computed in retrospective; comes in Phase R1
    hard_floor_status:
      dsr_passed: true
      max_dd_passed: true
      cost_model_verified: false  # v0 unverified
      leakage_check: not_run  # not part of retrospective scope
    classified_tier: TIER_A_FULL_READY
    classification_reasoning: "All gates passed; DSR p=0.18 well below TIER_A 0.2 threshold"

decision_log:
  # APPEND if classification changed
  - DEC-2026-06-04-XXX: "Retrospective DSR confirmed Tier A classification with v0 cost model"
```

### 3.1 Per-Strategy Markdown Report (DERIVED)

Path: `docs/research/retrospective/<strategy_id>_<YYYY-MM-DD>.md`

Format:

```markdown
# Retrospective DSR Analysis: <STRATEGY_ID>

**Date:** YYYY-MM-DD
**Cost Model:** v0 (UNVERIFIED — 2x conservative multiplier applied)
**Status at Time of Analysis:** KEEP_LIVE | RETIRED

## Summary

**Tier Classification:** TIER_A | TIER_B | TIER_C | TIER_D
**DSR p-value:** 0.XX (probability true Sharpe > 0)
**Recommended Action:** Continue at 100% slice | Continue at 50% slice | Halt and re-evaluate | Retire

## Raw Metrics (Before Cost Model)

| Symbol | N | PF | Sharpe | MaxDD% |
|--------|---|----|----|--------|
| ...    |   |    |    |        |
| **TOTAL** | sum | weighted | weighted | max |

## Adjusted Metrics (After Conservative Cost Model)

| Symbol | N | PF (adj) | Sharpe (adj) | MaxDD% (adj) | Delta PF |
|--------|---|----------|--------------|--------------|----------|
| ...    |   |          |              |              |          |
| **TOTAL** | sum | weighted | weighted | max | delta |

## DSR Calculation

- Effective K (number of trials counted): X
  - Strategies tested in ledger: ~15 historical hypotheses
  - Symbols tested: X
  - Parameter variations attempted: X (where known)
- Observed Sharpe (adjusted): X.XX
- Skew: X.XX
- Kurtosis: X.XX
- Deflated Sharpe Ratio z-score: X.XX
- **DSR p-value: 0.XX**

## Tier Classification Reasoning

[explanation of why this tier]

## Hard Floor Status

- DSR p<0.3 floor: PASSED | FAILED
- MaxDD<5%: PASSED | FAILED
- Cost model verified: FALSE (v0 model, defaults applied)
- Leakage check: NOT RUN (will be added in eval_research_strategy.py)

## Honest Caveats

- Cost model is UNVERIFIED. Strategies near classification boundaries should be re-evaluated with verified cost model.
- N may be small (per PRD Section 3.4); DSR at small N has wide CI.
- This analysis uses paper trading + live data; no separate backtest re-run.

## Recommendation

[KEEP at full allocation | DEMOTE to Tier B at 50% | HALT pending re-evaluation | RETIRE]
```

### 3.2 Portfolio-Level Summary Report (DERIVED)

Path: `docs/research/retrospective/PORTFOLIO_SUMMARY_<YYYY-MM-DD>.md`

**Generated from**: rolling up all `research/biographies/*.yaml` files. Can be regenerated any time from biographies.

A single markdown table summarizing all 11 strategies, sortable by DSR p-value, with the operator-facing verdict:

```markdown
# Retrospective DSR Portfolio Summary

**Date:** YYYY-MM-DD
**Strategies Analyzed:** 11 (5 KEEP, 6 RETIRED)
**Cost Model:** v0 UNVERIFIED (2x conservative)

| Strategy | Status | Tier | DSR p | PF (adj) | Sharpe (adj) | N | Action |
|----------|--------|------|-------|----------|--------------|---|--------|
| ...      |        |      |       |          |              |   |        |

## Headline Findings

[N of 5 KEEP strategies survive DSR p<0.3]
[N of 5 KEEP strategies maintain Tier A]
[N of 5 KEEP strategies drop to Tier B at 50% slice]
[N of 5 KEEP strategies drop to Tier C or below — recommend halt/review]
[Validation of RETIRED strategies — did our retirement decisions align with DSR?]

## Decisions Triggered

[List of DEC entries that should be filed based on these findings — e.g., demote MACD_PB to Tier B if applicable]
```

### 3.3 JSON Output (DERIVED — for programmatic consumption)

Path: `docs/research/retrospective/results_<YYYY-MM-DD>.json`

**Generated from**: biography YAML files. Can be regenerated any time.

```json
{
  "run_date": "2026-06-XX",
  "cost_model_version": "v0_unverified",
  "strategies": {
    "MACD_PB": {
      "tier": "TIER_A",
      "dsr_p_value": 0.18,
      "raw_pf": 1.62,
      "adjusted_pf": 1.43,
      "n": 47,
      "passes_hard_floor": true,
      "recommended_action": "continue_full"
    },
    ...
  },
  "portfolio_summary": {
    "keep_surviving_dsr": 3,
    "keep_demoted_to_tier_b": 1,
    "keep_failing_dsr": 1,
    "retired_validated_by_dsr": 5,
    "retired_should_have_been_kept": 1
  }
}
```

## 4. DSR Module — BUILT AND VERIFIED (2026-06-05)

**The inline pseudo-code that was here in the first draft had real correctness bugs** (flagged by external review 2026-06-05): a units mismatch in the expected-max-Sharpe term, a missing cross-sectional-variance scaling, no guard on the variance term, and an unpinned kurtosis convention. Rather than ship buggy pseudo-code, the corrected module was **written and verified before this spec was finalised**.

**Canonical implementation**: `research/validation/deflated_sharpe.py` (already created and tested).
**Tests**: `tests/research/test_deflated_sharpe.py` — 29 tests, all passing (1 scipy cross-check skips when scipy absent). Run with:
```bash
python -m pytest tests/research/test_deflated_sharpe.py -q
```

### 4.1 What the module provides

| Function | Purpose |
|---|---|
| `normal_cdf(x)` | Standard normal CDF via `math.erf` (exact, stdlib) |
| `normal_ppf(p)` | Inverse normal CDF via Acklam's algorithm (~1.15e-9, stdlib) |
| `sample_sharpe(returns)` | Per-trade Sharpe (sample std, ddof=1) — matches `_sharpe_per_trade` |
| `sample_skewness(returns)` | Method-of-moments skewness |
| `sample_kurtosis(returns)` | RAW (non-excess) kurtosis; normal = 3.0 |
| `probabilistic_sharpe_ratio(...)` | PSR with variance guard |
| `expected_max_sharpe(variance_sr, n_trials)` | Selection-bias benchmark (Bailey-LdP, inverse-normal form) |
| `deflated_sharpe_ratio(...)` | Full DSR → `DeflatedSharpeResult` |

### 4.2 The four corrections (vs the original buggy draft)

1. **Per-trade framing, documented.** DSR computed on per-trade ("per-bet") returns, NOT a reconstructed daily equity curve. Rationale: (a) consistency with the existing live promotion gate which already uses per-trade Sharpe (`_sharpe_per_trade`, DEC-2026-05-27-004); (b) per-trade returns are closer to IID than daily returns (consecutive daily returns while holding one multi-day position are serially correlated, violating the PSR formula's IID assumption MORE than per-trade returns do); (c) no mark-to-market OHLCV dependency. Trade-off documented: per-trade Sharpe is not annualised.

2. **Units consistency.** `expected_max_sharpe` uses the full Bailey-LdP estimator `sqrt(variance_sr) * [(1-gamma)*Phi_inv(1-1/K) + gamma*Phi_inv(1-1/(K*e))]` scaled by the per-trade Sharpe cross-sectional variance, so the benchmark and the observed Sharpe are in identical per-trade units. The original `sqrt(2*ln(K))` term was unit-mismatched and is removed.

3. **Variance guard.** `probabilistic_sharpe_ratio` raises `ValueError` if `1 - skew*SR + ((kurt-1)/4)*SR**2 <= 0`. Mathematical note discovered during verification: for any VALID distribution `kurt >= 1 + skew**2`, which makes this term provably non-negative for moment-consistent inputs — so it can only fire if EXCESS kurtosis is mistakenly passed where RAW is required. The guard is therefore a tripwire for the Fisher footgun (see #4).

4. **Kurtosis convention pinned.** `sample_kurtosis` returns RAW kurtosis (normal = 3.0), not excess (normal = 0.0). A test asserts a near-normal sample returns ~3.0, so the `scipy.stats.kurtosis` excess-default footgun cannot silently corrupt every number.

### 4.3 Interpretation

- `DeflatedSharpeResult.dsr` — probability the true Sharpe exceeds the expected-max-under-null. HIGH (→1) is GOOD.
- `DeflatedSharpeResult.dsr_p_value` — `1 - dsr`. LOW (→0) is GOOD. This is what the PRD Tier floors gate against: Tier A p<0.2, Tier B p<0.3, reject at p>=0.5.

### 4.4 Verified worked example — why effective K is decisive

Running the verified module on a plausible MACD_PB-like sample (per-trade Sharpe 0.51, N=47, skew −0.23, raw kurtosis 2.46, `variance_sr=0.02`):

| K | E[max SR] | DSR | DSR p-value | Verdict |
|---|---|---|---|---|
| 1 | 0.0000 | 0.9992 | 0.0008 | TIER_A |
| 23 | 0.2774 | 0.9248 | 0.0752 | TIER_A |
| 115 | 0.3648 | 0.8159 | 0.1841 | TIER_A |
| 500 | 0.4317 | 0.6871 | 0.3129 | **BELOW FLOOR** |
| 2000 | 0.4875 | 0.5571 | 0.4429 | **BELOW FLOOR** |

**The same strategy is Tier A at K=115 but fails the floor at K>=500.** This is exactly the fragility the external review warned about: a hardcoded optimistic K manufactures a Tier-A verdict that an honest K (including parameter combinations) erases. This is why Section 6 mandates a multi-K sensitivity sweep and DB-derived K, not a single hardcoded guess.

## 5. Cost Application Logic

**Revised 2026-06-05 per external review.** Two corrections from the first draft:
(1) compute REALIZED slippage from actual fills where the data exists, instead
of assuming a flat 0.05%; (2) do NOT stack a 95th-percentile spread AND a 2x
multiplier blindly — that double-counts conservatism and risks rejecting real
edge (being too harsh has a cost too).

### 5.1 Slippage — measure it, don't guess it

The database holds signal prices (price when the strategy fired) and actual
fill prices. Where BOTH exist, compute realized slippage empirically:

```python
def realized_slippage_pct(trade: dict) -> float | None:
    """Realized slippage from signal price vs actual fill. None if unavailable."""
    signal = trade.get("signal_price")
    fill = trade.get("fill_price") or trade.get("entry_price")
    if signal is None or fill is None or signal <= 0:
        return None
    # Slippage is always adverse-signed as a cost (abs of the deviation).
    return abs(fill - signal) / signal * 100.0
```

Per-symbol slippage = median (or 75th percentile, conservative) of realized
slippage across that symbol's trades. Fall back to the assumed default ONLY for
symbols with no signal-price data. **This is the cheapest credibility win in the
script** — we are sitting on the data that makes slippage empirical.

### 5.2 Conservatism — apply it ONCE, not twice

Decision (resolves the double-counting flagged in review): the v0 cost model
uses **measured/median realized slippage + 95th-percentile spread + taker fee**,
and applies the 2x multiplier ONLY to the components that remain ESTIMATED (the
spread where per-symbol order-book history is unavailable). Components that are
MEASURED from real fills are NOT additionally 2x'd — measuring already removed
the need to pad them. Concretely:

```python
def apply_cost_model(trade: dict, cost_model: CostModel) -> float:
    """Return the per-trade return (%) after subtracting round-trip costs.

    Conservatism is applied ONCE: estimated components get the 2x pad;
    measured components (realized slippage) do not. This avoids stacking
    95th-percentile + 2x on the same quantity (which would reject real edge).
    """
    symbol = trade["symbol"]
    raw_return_pct = pct_return(trade)  # sign-aware (handles SHORT)

    # Spread: 95th-percentile per-symbol if measured; else default x 2x pad.
    if symbol in cost_model.measured_spreads_pct:
        spread_pct = cost_model.measured_spreads_pct[symbol]  # already p95, no extra pad
    else:
        spread_pct = cost_model.default_spread_pct * cost_model.estimate_pad  # 2x

    # Slippage: realized if available (no pad); else default x 2x pad.
    realized = realized_slippage_pct(trade)
    if realized is not None:
        slippage_pct = realized  # measured -> no extra pad
    else:
        slippage_pct = cost_model.slippage_pct_default * cost_model.estimate_pad  # 2x

    fee_pct = cost_model.binance_taker_fee_pct  # known exactly, never padded

    # Cross half the spread per side; fee + slippage charged per side.
    cost_per_side_pct = spread_pct / 2.0 + fee_pct + slippage_pct
    round_trip_cost_pct = 2.0 * cost_per_side_pct
    return raw_return_pct - round_trip_cost_pct
```

### 5.3 Hand-checked worked example (DOGE)

Walk one trade by hand to confirm the round-trip number is intended, per review:

- DOGE measured spread (p95) = 0.15%, taker fee = 0.075% (BNB) or 0.10%, realized slippage (measured) = 0.04%
- cost_per_side = 0.15/2 + 0.10 + 0.04 = 0.075 + 0.10 + 0.04 = 0.215%
- round_trip = 2 x 0.215 = **0.43%** per round trip

That is plausible for DOGE and does NOT double-pad (spread is p95 but not also 2x'd; slippage is measured, not 2x'd; only truly-estimated components get the 2x). Compare to the original draft's `2 x (0.075 + 0.10 + 0.05) x 2 = 0.90%`, which 2x'd everything including the fee — too harsh. The runner MUST print the per-symbol round-trip cost so the operator can sanity-check it before trusting any verdict.

### 5.4 Realized-cost reconciliation note

Even in v0 (unverified), recording realized slippage where available begins the
calibration that Phase R0.5 Week 2-3 completes (upgrading the cost model from
v0_unverified to v1_verified by validating against >=10 fills per symbol per
DEC-2026-06-04-002). The biography stores which components were MEASURED vs
ESTIMATED per symbol, so the audit trail shows exactly how conservative each
number is.

### 5.5-pre Notional base (specify per leg)

Costs are in percentage of NOTIONAL, and entry vs exit notional differ when the
price moved (a +40% DOGE winner has a 40%-larger exit notional). Specify
explicitly: **entry-leg cost is charged on entry notional; exit-leg cost is
charged on exit notional.** In pure return-percentage space this means the
exit-side cost percentage is applied to the gross return leg, not the entry
basis. The implementation must document and test this on a large-winner trade so
the round-trip cost is not silently understated on big moves.

## 5.5 Per-Symbol vs Pooled DSR (Resolved 2026-06-05)

**Decision: pool a strategy's trades across its symbols into ONE return series and compute ONE DSR per strategy.** DSR is NOT weight-averageable across symbols, so the original report templates showing per-symbol DSR rows with a "weighted TOTAL" were wrong.

Rationale:
- The honest question for a multi-symbol strategy is portfolio-level: "does this strategy have edge as deployed (across its basket)?" — not "does it have edge on DOGE specifically?"
- Pooling also fixes the small-N-per-cell problem: MACD_PB on DOGE alone might be N=20, but pooled across DOGE+AVAX it is N=47, where DSR is more meaningful.
- The gating DSR p-value is computed ONCE on the pooled per-trade return series.

Per-symbol PF/Sharpe MAY still be shown in the derived markdown report as DESCRIPTIVE breakdown (useful for spotting a strategy carried by one symbol), but they are NOT gating numbers and carry no Tier weight. The report must label them "descriptive, not gating."

Implementation: concatenate all of a strategy's (cost-adjusted, quarantine-filtered) per-trade returns across symbols in chronological order, then call `deflated_sharpe_ratio` once on that pooled series.

**Documented v0 limitation (not a blocker):** chronological concatenation across symbols produces a series whose serial-correlation structure is an accident of which symbol fired when, and trades that overlapped in time (concurrent, correlated risk) are treated as sequential. This is fine for the Sharpe POINT ESTIMATE but slightly distorts the skew/kurtosis that feed the variance term, and it must NOT be mistaken for a true multi-asset equity curve. A future phase that reconstructs a per-bar portfolio equity curve (with concurrent positions properly netted) would supersede this; v0 accepts the approximation and records it as a caveat in the biography so it is not later read as more rigorous than it is.

---

## 6. Effective K Counting (Revised 2026-06-05 — DB-derived + multi-K sweep)

**The original hardcoded `K=115` is rejected.** Section 4.4's worked example proves why: the same strategy is Tier A at K=115 but fails the floor at K>=500. A single hardcoded, memory-derived K both (a) biases optimistic and (b) is not reproducible from data, defeating the provability purpose (DEC-2026-06-04-012).

### 6.1 Derive K from the database where possible

Count the EFFECTIVE number of trials as the actual hypothesis search space that was executed, reconstructed from records rather than memory:

```python
def derive_effective_k(db) -> dict:
    """Reconstruct effective K from recorded backtest/optimization runs.

    effective_K = sum over all hypotheses of (parameter combinations tested
                  x symbols tested x timeframes tested)

    Where a strategy's optimization history records combinations (e.g.
    MACD_PB opt_001 tested 96 combinations), use the real number. Where only
    the final config survives with no recorded sweep, count >=1 per symbol x
    timeframe and FLAG it as a lower bound (the true K is higher).
    """
    ...
```

Critically: MACD_PB's own biography shows `opt_001` tested 96 parameter combinations. So the honest K for ONE strategy's optimization is ~96, and across ~23 hypotheses x ~5 symbols x parameter combos the portfolio-level effective K is in the THOUSANDS, not 115. The DB-derived count must include parameter combinations or it reproduces the exact undercount the PRD repudiated.

### 6.2 Where K must be estimated, store the derivation

For historical runs where the parameter-combination count was not recorded, estimate it, but write BOTH the estimate AND its derivation into the biography:

```yaml
effective_k_derivation:
  method: "db_reconstructed_partial"   # or "estimated" or "db_exact"
  hypotheses_counted: 23
  symbols_per_hypothesis_avg: 5
  param_combos_recorded: 412           # summed from optimization_history where present
  param_combos_estimated: 800          # estimated for runs with no recorded sweep
  effective_k_point_estimate: 2000
  is_lower_bound: true
  notes: "Param-combo counts missing for research waves 1-2; estimated at 50/strategy."
```

This makes K auditable — a future reader can see how the number was reached and challenge it, rather than trusting "project memory."

### 6.3 Multi-K sensitivity sweep (MANDATORY)

Every strategy's DSR is reported at **multiple K values** — at minimum `[115, 500, 2000]`, plus the DB-derived point estimate. The report shows the Tier verdict at each K. If a strategy is Tier A at low K but fails at high K, that fragility IS the finding and must be surfaced, not hidden:

```yaml
dsr_k_sensitivity:
  - k: 115
    dsr_p_value: 0.18
    tier: TIER_A
  - k: 500
    dsr_p_value: 0.31
    tier: BELOW_FLOOR
  - k: 2000
    dsr_p_value: 0.44
    tier: BELOW_FLOOR
  derived_k_estimate: 2000
  gating_k_used: 2000          # the CONSERVATIVE choice gates the verdict
  verdict_is_fragile: true     # flips tier across the K range
```

**The gating verdict uses the conservative (highest defensible) K**, typically the DB-derived estimate. A strategy whose Tier depends on an optimistic K is treated as not-yet-proven (`verdict_is_fragile: true` → at most Tier C until more data narrows the uncertainty).

### 6.4 variance_sr is a second decisive knob — sweep it like K (MANDATORY)

`deflated_sharpe_ratio` needs `variance_sr` (cross-sectional variance of per-trade Sharpe estimates across trials). It enters `expected_max_sharpe` directly: larger `variance_sr` -> larger benchmark -> lower DSR -> higher p-value -> harder to pass. **It is as decisive as K, and the original "expose it as a swept parameter if uncertain" was too soft.** Make the sweep UNCONDITIONAL.

The problem with estimating it from the 11 analyzed strategies: (a) 11 points gives the variance estimate a large standard error; (b) those 11 are NOT a random sample of the hypothesis space — they are survivors + retirees we kept records for, a SELECTED set, so their Sharpe dispersion is a biased estimate of the true cross-trial dispersion. So treat `variance_sr` exactly like K: derive a point estimate, AND sweep across a plausible range, AND flag fragility if the Tier flips across the range. Store the value + derivation in each biography.

Default sweep grid: `variance_sr in {0.5x, 1.0x, 2.0x}` of the point estimate derived from the 11 strategies' Sharpe dispersion.

### 6.5 Base case vs conservative case (the unifying frame — gate conservative, SHOW base)

**This is the most important reporting structure in the retrospective.** Two corrections compound: subtracting costs lowers the Sharpe that goes INTO the DSR, and the DSR then deflates for selection bias. Both are deliberately conservative. Stack 2x-padded estimated spreads + highest-defensible K + high `variance_sr`, and you can manufacture a Tier-D verdict out of a strategy with real (if modest) edge. Being too harsh has a cost too.

The resolution: report every strategy at TWO operating points, and let the GAP between them diagnose the verdict.

| Case | Cost model | K | variance_sr | Role |
|---|---|---|---|---|
| **BASE** | measured costs (no extra pad) | DB-derived point estimate | point estimate | the realistic read |
| **CONSERVATIVE** | padded estimated components | highest defensible (e.g. 2000) | high end of sweep | the worst-case read |

- **Gate on the CONSERVATIVE case** (the hard floor uses it). A strategy only deploys if it survives the worst-case assumptions.
- **But SHOW the BASE case**, because the gap is the finding:
  - Tier A base AND Tier A conservative -> robust real edge.
  - Tier A base, Tier D conservative -> **real-but-fragile** edge (the "works but misses the strict gate by assumptions" case). Not deployed, but NOT the same as no edge — flag for more data, do not retire.
  - Tier D base AND Tier D conservative -> genuinely no edge. Safe to retire.

The current spec collapsed these into one number; that hid whether a rejection means "no edge" or "killed by stacked worst-cases." The biography stores both cases and the diagnosis (`base_tier`, `conservative_tier`, `fragility = base_tier != conservative_tier`).

This frame unifies the K sweep (6.3) and the variance_sr sweep (6.4): the conservative case is the high end of both sweeps; the base case is the point estimate of both. It also directly serves the operator's original design intent (DEC-2026-06-04-008): a real-but-fragile strategy is exactly the "works but does not pass the strict gate" case the Tier system was built to handle without an override path.

## 7. PARA-02 Quarantine Filter (REQUIRED)

Per DEC-2026-05-31-002, force-closed trades from prior data corruption MUST be excluded from analysis:

```python
def is_quarantined(trade: dict) -> bool:
    """Return True if trade should be excluded per PARA-02 quarantine."""
    if trade.get("force_close") and trade.get("forced_pnl_zero"):
        return True
    # Additional quarantine criteria per DEC-2026-05-31-002...
    return False
```

Use the existing `_is_corrupt_force_close` helper from `scripts/validation_report.py` if reusable — single source of truth principle.

## 8. CLI Interface

```bash
python -m scripts.retrospective_dsr [options]

Options:
  --strategy <id>        Analyze single strategy (default: all KEEP + RETIRED)
  --symbol <symbol>      Filter to single symbol
  --output-dir <path>    Override default docs/research/retrospective/
  --cost-model <ver>     Use specific cost model version (default: v0_unverified)
  --json-only            Skip markdown reports, output JSON only
  --verbose              Show per-trade computation
```

## 9. Implementation Order (Sub-Tasks)

DSR module (the hardest, most correctness-critical part) is DONE. Remaining estimated: 8-12 hours over 1-2 days.

1. ~~DSR module + tests~~ **DONE 2026-06-05** (`deflated_sharpe.py`, 29 tests passing)
2. **Hour 1-2**: Database schema reconnaissance — confirm trade-log table structure, identify signal_price/fill_price fields (needed for realized slippage, Section 5.1), handle force-close quarantine
3. **Hour 3-4**: Cost model module (`research/backtest/cost_model.py`) per Section 5 — measured-vs-estimated component split, realized slippage, single-pad conservatism
4. **Hour 5**: Effective-K derivation (`research/validation/effective_k.py`) per Section 6 — DB-reconstructed + multi-K sweep + variance_sr estimation
5. **Hour 6**: Tier classifier (`research/promotion/classifier.py` minimal) — applies hard floors + Tier A/B/C/D per DEC-2026-06-04-008, uses conservative (highest) K, sets `verdict_is_fragile`
6. **Hour 7-8**: Main script (`scripts/retrospective_dsr.py`) — pooled per-strategy loop (Section 5.5), writes biography YAMLs (PRIMARY output)
7. **Hour 9-10**: Derived markdown + portfolio summary + JSON rendering
8. **Hour 11-12**: Integration tests + dry-run validation

### 9.1 Operational guards (do not skip)

Two failure modes that are invisible until they bite:

1. **Idempotent biography writes.** The same run both classifies AND writes the biography. A crash at strategy 7 of 11 leaves 6 updated and 5 not; a naive re-run double-appends to `classification_history` / `statistical_validation_history`. Make the write idempotent: key every appended entry on `run_id`, and SKIP append if an entry with that `run_id` already exists (or stage all 11 results then commit in one pass). A half-finished run must be safely re-runnable.

2. **MaxDD is recomputed on the pooled, cost-adjusted series — NOT the legacy backtest figure.** The hard floor gates on `MaxDD < 5%`. The MaxDD that gates MUST be computed from the same pooled, cost-adjusted, quarantine-filtered per-trade series the DSR uses — not the 3.5-4.2% backtest numbers carried in the biography from earlier work. Carrying the legacy figure would make the floor measure the wrong thing. Recompute it in this run and store it as `max_dd_pct_pooled_adjusted`.

## 10. Tests Required (Minimum)

- ~~`test_deflated_sharpe.py`: validate DSR math from first principles~~ **DONE 2026-06-05 (29 tests passing; keystone = exact PSR-normal reduction to 1e-12)**
- `test_cost_model.py`: verify cost application on synthetic trades, including the measured-vs-estimated pad split and the hand-checked DOGE round-trip (Section 5.3)
- `test_effective_k.py`: verify DB-derived K includes parameter combinations; multi-K sweep produces monotonic deflation
- `test_retrospective_main.py`: integration test with synthetic strategy data; confirms pooled (not per-symbol) DSR; confirms base-vs-conservative cases both reported and the gate uses the conservative one; confirms idempotent re-run (no double-append on second run with same run_id); confirms MaxDD is recomputed on the pooled series
- `test_cost_model.py` additions: notional-base test on a large-winner trade (exit-leg cost on exit notional, not entry)
- `test_para_02_quarantine.py`: confirm corrupt trades excluded (reuse `_is_corrupt_force_close`)

### 10.1 Execution Gate (MANDATORY per external review)

`scripts/retrospective_dsr.py` MUST refuse to run on real data unless the DSR
test suite passes. Implement as a pre-flight check:

```python
def _assert_dsr_math_verified() -> None:
    """Refuse to run on real data unless the DSR math tests pass.

    A miscalibrated capital-gating instrument that LOOKS rigorous is worse than
    none. The keystone test (exact PSR-normal reduction) must pass before any
    real strategy is classified.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/research/test_deflated_sharpe.py", "-q"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            "DSR math verification FAILED. Refusing to classify strategies on "
            "an unverified instrument. Fix tests/research/test_deflated_sharpe.py first."
        )
```

Run this at the top of `main()` before any database read.

## 11. Acceptance Criteria

The retrospective DSR run is COMPLETE when:

1. **PRIMARY**: All 11 strategies (5 KEEP + 6 RETIRED) have biography YAML files with `current_classification`, `classification_history`, and `statistical_validation_history` populated
2. **PRIMARY**: `research/hypotheses/ledger.yaml` status fields updated to reflect new tier classifications
3. **PRIMARY**: Decisions filed in BOTH `.claude/DECISIONS.md` AND `.agent/DECISIONS.md` for any tier changes (with `diff` verified identical per Rule 0)
4. **DERIVED**: Per-strategy markdown reports generated (one per strategy)
5. **DERIVED**: Portfolio summary report generated with headline findings
6. **DERIVED**: JSON output validates against schema
7. PARA-02 quarantine confirmed applied (zero quarantined trades in any analysis)
8. Cost model version + assumptions are documented in every biography update (audit trail)
9. Operator review completed; any tier changes ratified via decision-log entry

**Verification**: From a clean state, deleting all derived markdown reports and re-running the report-generation step should produce identical output from the biography YAMLs. This proves biographies are the canonical source.

## 12. Honest Expectations

Per PRD Section 14.1, the most likely outcome:

- **1-3 of the 5 KEEP strategies fall to Tier B or Tier C** under DSR with conservative cost model
- **Most RETIRED strategies validated by DSR** (i.e., DSR p>0.5 confirms our retirement decisions were right)
- **At least 1 RETIRED strategy might surprise** (DSR p<0.3) — these warrant re-examination
- **The cost model alone might explain some of the BTF live degradation** (PF 0.75 vs backtest)

These outcomes are GOOD information. Resist the urge to find ways to "save" a strategy that fails DSR — the floor is non-negotiable for a reason (DEC-2026-06-04-008).

## 13. Follow-Ups After This Spec Is Implemented

Once `retrospective_dsr.py` produces results:

1. **File a DEC entry per tier change** for any KEEP strategy that drops to Tier B or C
2. **If a KEEP strategy drops to Tier D** (DSR p>=0.5): file an urgent retirement decision
3. **If a RETIRED strategy surprises with DSR p<0.3**: file a hypothesis for re-examination
4. **Begin cost model calibration** (Phase R0.5 Week 2-3) using paper-trading fills to upgrade from v0_unverified to v1_verified
5. **Re-run retrospective with v1_verified cost model** once available, file follow-up reports

---

## 14. Companion Tool: `scripts/show_strategy.py` (Strategy Card CLI)

**Purpose**: Pretty-print a strategy's biography to the terminal for quick review. Avoids the friction of opening YAML files or generating markdown when you just want to see the current state of a strategy.

**Why this exists**: Per the data-architecture clarification, the biography YAML is the canonical strategy record. A CLI that renders it readably gives the operator instant access without intermediate steps.

### 14.1 CLI Interface

```bash
python -m scripts.show_strategy <strategy_id> [options]

Options:
  --section <name>   Show only a specific biography section:
                       hypothesis | parameters | optimization | backtest |
                       paper | live | decay | post_mortem | decisions
  --history          Show full history rather than current-state-only
                     (default: current state + summary of history)
  --verbose          Include all fields including null/empty
  --json             Output raw JSON for programmatic use
  --no-color         Disable terminal color output
```

### 14.2 Default Output (Current-State Summary)

When called as `python -m scripts.show_strategy MACD_PB`:

```
========================================================================
  Strategy: MACD_PB
  Status: ACTIVE_LIVE
  Current Classification: TIER_A_FULL_READY
========================================================================

HYPOTHESIS
  ID: H-2025-12-014
  Source: Quantpedia #43 + Robot Wealth 2024-03-15
  Regime Target: TRENDING_BULL (actual edge: CHOPPY_BEAR per retag 2026-05-28)
  Pre-Registered: PF=1.5, Sharpe=1.2, N=12/year

CURRENT PARAMETERS (v1.1.0)
  ema_fast: 10
  ema_slow: 30
  signal: 9
  symbols: [DOGEUSDT, AVAXUSDT]

LATEST STATISTICAL VALIDATION (2026-06-04)
  Cost Model: v0_unverified
  PF (adjusted): 1.43  (raw: 1.62)
  Sharpe (adjusted): 1.18  (raw: 1.34)
  N: 47
  Effective K: 115
  DSR p-value: 0.18  [TIER_A floor: PASSED]
  MaxDD: 4.2%  [PASSED]

LIVE STATUS
  Deployed: 2026-04-15
  Live trades: 3
  Live PF: 1.21
  Capital slice: 100% (TIER_A)
  Decay status: STABLE

LIFECYCLE SUMMARY
  Total versions: 2 (v1.0.0, v1.1.0)
  Total optimization attempts: 2 (1 successful, 1 no-improvement)
  Total paper sessions: 2
  Total decay events: 0
  Days since proposal: 177

RECENT DECISIONS
  DEC-2026-06-04-XXX: Retrospective DSR confirmed TIER_A (2 days ago)
  DEC-2026-05-28-002: Triage review - KEEP (7 days ago)
  DEC-2026-04-15-XXX: Promoted to TIER_A, deployed at 100% slice (50 days ago)

========================================================================
  For full history: python -m scripts.show_strategy MACD_PB --history
========================================================================
```

### 14.3 Section View

When called as `python -m scripts.show_strategy MACD_PB --section optimization`:

```
========================================================================
  Strategy: MACD_PB - Optimization History
========================================================================

opt_001 (2026-03-15)
  Type: walk_forward_grid_search
  Param space: ema_fast: [8-15], ema_slow: [25-35], signal: [7-12]
  Combinations tested: 96
  Walk-forward windows: 12
  Result: SUCCESSFUL
  PF: 1.62 → 1.71
  Led to: v1.1.0
  PBO score: 0.18

opt_002 (2026-04-22)
  Type: bayesian_optimization
  Param space: all params
  Iterations: 100
  Result: NO_IMPROVEMENT
  Notes: "Converged to v1.1.0 parameters; no robust improvement found"
========================================================================
```

### 14.4 Implementation Requirements

- **Read-only**: NEVER writes to biography YAML or any other file
- **Color output**: use ANSI colors for status (green for TIER_A, yellow for TIER_B, red for TIER_D); respect `--no-color` flag
- **No external dependencies beyond stdlib + PyYAML**: keep it light
- **Fast**: under 100ms for a single strategy (no DB queries; reads YAML only)
- **Graceful errors**: if `<strategy_id>` doesn't exist, list available strategies and exit cleanly
- **Available IDs**: list comes from globbing `research/biographies/active/*.yaml` + `research/biographies/retired/*.yaml`

### 14.5 Implementation Order

This is Phase R0.5 follow-up work (after retrospective_dsr.py). Estimated: 4-6 hours.

1. **Hour 1**: YAML loading + schema validation (use the schema from PRD Appendix A)
2. **Hour 2-3**: Default summary view renderer with ANSI color
3. **Hour 4**: Section view renderer (one renderer per section type)
4. **Hour 5**: Unit tests + CLI argument handling
5. **Hour 6**: Documentation + integration with `scripts/__init__.py`

### 14.6 Acceptance Criteria

- All 11 biographies (5 KEEP + 6 RETIRED) render without error
- Default view produces ≤ 50 lines (readable in one terminal screen)
- `--section` flag works for all 9 section types
- `--json` produces valid JSON parseable by `json.loads()`
- `--no-color` produces output usable in pipes/redirects
- Unit tests cover at least 80% of rendering code

### 14.7 Why Not Just Read the YAML?

YAML is human-readable in principle, but biographies grow to 200+ lines per strategy with deep nesting. The CLI extracts the headline and hides verbose history fields unless `--history` is requested. It's the difference between `cat biography.yaml` (200 lines of mostly noise) and `show_strategy MACD_PB` (50 lines of what you want to know).

---

**End of Spec**

---

## SPEC FROZEN — 2026-06-05

This spec is **frozen for implementation**. It has been through three rounds of external review; the hard, correctness-critical part (the DSR math module) is built and verified (29 tests passing); and the remaining work is plumbing: read trades, subtract costs, derive K + variance_sr with sweeps, call the verified DSR function, classify, write biography YAML, render derived reports.

**No further spec revision before a run.** The next action that produces value is BUILDING and RUNNING it on the eleven strategies. The finding — how many of the five KEEP strategies survive honest costs and an honest K — is worth more than any further polish on the instrument. Any new idea that arrives after this point gets noted as a follow-up in the biography or a fresh decision entry, NOT folded into another spec round.

Estimated remaining implementation: 8-12 hours (the DSR module, the hardest part, is already done). `show_strategy.py`: 4-6 hours, AFTER the run produces biographies worth viewing.
