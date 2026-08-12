# Research Findings

**Compiled:** 2026-08-11
**Covers:** 2026-02-08 through 2026-06-11
**Reproduce:** every table here is generated from
`research/hypotheses/ledger.yaml` and
`docs/research/retrospective/results_2026-06-05.json`. Commands in Section 8.

---

## 1. Bottom line

**No strategy in this repository has a validated edge.** Twenty-nine signal
generators were built. Zero passed.

That is the headline, and it has not changed. What changed on 2026-08-11 is the
precision of the supporting claim. The distinction below matters more than the
result:

| Claim | Status |
|---|---|
| No strategy has a validated edge | **Established** |
| 8 subjects were rejected at a sample size where the verdict means something | **Established** |
| All 11 retrospective strategies were shown to be worthless | **Withdrawn.** 10 of them were never measured |

The rest of this document is mostly about that third row, because how it was
caught is more useful than the finding itself.

---

## 2. What was actually established

Eight subjects were rejected under Deflated Sharpe at N >= 25, which is where a
DSR verdict starts carrying information.

| Subject | Mechanism class | Regime target | N (regime) | PF | DSR p | Tag |
|---|---|---|---|---|---|---|
| BTF | Multi-timeframe bear trend | — | 25 | 0.54 | 1.000 | retired |
| H-2026-06-002 | Price breakout continuation | TRENDING_BULL | 341 | 0.59 | 1.000 | FUNDAMENTAL |
| H-2026-06-011 | BTC lead-lag, information diffusion into mid-cap alts | TRENDING_BULL | 255 | 0.44 | 1.000 | FUNDAMENTAL |
| H-2026-06-003 | Perp funding confirmation of trend | TRENDING_BULL | 132 | 0.53 | 1.000 | FUNDAMENTAL |
| H-2026-06-008 | Cross-sectional relative-strength momentum | TRENDING_BULL | 121 | 0.88 | 1.000 | FUNDAMENTAL |
| H-2026-06-007 | Spot-ETF net-flow structural demand | TRENDING_BULL | 87 | 0.44 | 1.000 | FUNDAMENTAL |
| H-2026-06-010 | Coinbase premium, US-institutional cross-venue demand | TRENDING_BULL | 75 | 0.35 | 1.000 | FUNDAMENTAL |
| H-2026-06-006 | Funding-extreme contrarian, per-symbol percentile gate | HIGH_VOL | 28 | 0.94 | 0.960 | FUNDAMENTAL |

Pooled sample sizes across all regimes run considerably higher — up to 974 for
H-002 and 918 for H-011. The regime-specific N is shown because that is the cell
the hypothesis actually made a claim about.

Every one of these has a profit factor **below 1.0**. These are not marginal
edges lost to multiple-comparisons correction; they lose money before the
correction is applied. The DSR is confirming a conclusion the raw numbers
already support.

One (H-005) returned `INSUFFICIENT_DATA` rather than a rejection — see the next
section, because that is the guard working correctly.

Two more (H-004, H-009) are `PROPOSED` and blocked, and the reason they are
blocked is worth stating precisely: **not budget, but causality.**

Both are liquidation-cascade hypotheses — buy the flush when forced selling
overshoots. Testing them needs a historical liquidation series that respects
point-in-time correctness, and no such free series exists:

| Source | Why it cannot be used |
|---|---|
| Binance `/fapi/v1/allForceOrders` | Deprecated; no longer accepts requests |
| Binance `/fapi/v1/forceOrders` | User-private, and capped at 90 days |
| Binance `forceOrder` websocket | Real-time only; no history |
| Hyperliquid `/info` | Has no market-wide liquidation request type. Verified by probing, not assumed |

The available alternative — reconstructing history from a source that would leak
information unavailable at decision time — was rejected. Instead a **forward
collector** was built (DEC-2026-06-04-021): it streams Binance `forceOrder`
events to JSONL behind a causal accessor that can only return events strictly
prior to a query timestamp. The hypotheses stay `PROPOSED` until N >= 30 accrues
in HIGH_VOL, which will take months.

Choosing to wait months rather than test against contaminated history is the
same decision as Section 3, made prospectively instead of retrospectively.

---

## 3. The error, and how it was caught

### What was reported

The retrospective run of 2026-06-05 analysed 11 strategies and reported **all
eleven** as `TIER_D_REJECT`. That result propagated into the project's own
summary documents and was, for two months, the headline finding.

### What was wrong with it

Ten of the eleven had between **0 and 4 recorded trades**:

| N | Strategies |
|---|---|
| 0 | BTP, VBB, SRC, HATP, VRB, VPT |
| 2 | MACD_PB |
| 3 | RSI_BB |
| 4 | CMF, ICVP |
| 25 | BTF |

The paper-trading process had been down behind a regional exchange block, so the
trade records the analysis read were nearly empty. A Deflated Sharpe p-value of
1.000 computed on **zero trades** is not evidence of no edge. It is a degenerate
output from a null input, and it was being printed next to the word "reject".

This is the oldest error in applied statistics — treating *absence of evidence*
as *evidence of absence* — and it is precisely the failure the research layer was
built to prevent. It was committed by the research layer.

### The fix

`research/promotion/classifier.py` gained a floor, checked **before** any
threshold so a degenerate p-value can never reach the tier logic:

```python
MIN_N_FOR_CLASSIFICATION: int = 10

if n_trades < MIN_N_FOR_CLASSIFICATION:
    return Tier.INSUFFICIENT_DATA
```

With the rationale recorded in the source (DEC-2026-06-04-014):

> A genuinely edge-less strategy with enough trades still earns `TIER_D`; only
> data *scarcity* yields `INSUFFICIENT_DATA`. The 2026-06-05 Neon run's N=0..4
> strategies were wrongly shown as `TIER_D_REJECT`; this guard prevents that
> "no data" -> "proven noise" misread.

Note the threshold's justification: below N=10 the skew and kurtosis moments the
DSR depends on are not meaningful, so the verdict is not computable *as
evidence*. This is deliberately distinct from the Tier B deployment floor of
N>=20. Ten is the floor for the verdict meaning anything; twenty is the floor
for acting on it.

### Re-running the stored results

```
                        as published    corrected
TIER_D_REJECT                    11            1
INSUFFICIENT_DATA                 0           10
```

Only BTF (N=25) survives as a genuine rejection.

### Evidence the fix works

`H-2026-06-005` was screened after the guard was added. It returned
`INSUFFICIENT_DATA` at N=4 with failure tag `FIXABLE` — explicitly distinguished
from the `FUNDAMENTAL` tag carried by the seven genuine rejections. Its ledger
entry notes the pooled DSR p of 0.61 is "meaningless at this N; reported for
completeness."

A hypothesis that cannot be measured is now recorded as unmeasured, and is
eligible to be re-run when data exists. Before the fix it would have been
retired as noise.

### What was done with the wrong report

It was kept. `docs/research/retrospective/PORTFOLIO_SUMMARY_2026-06-05.md` and
the ten unsupported per-strategy post-mortems carry a `SUPERSEDED` banner
stating what is wrong and why, with the original text unedited beneath. The
BTF post-mortem is unbannered because its verdict stands.

Deleting them would have removed the most instructive artifact in the project.

---

## 4. The calibration finding

Every hypothesis is scored 0-3 across seven dimensions before it may consume a
trial — mechanism strength, inverse crowding, crypto-native fit, regime
specificity, parameter parsimony, diversity contribution, source credibility.
Passing requires mechanism strength >= 2 and a total >= 14/21.

The scorecard was intended to predict which hypotheses were worth testing. Seven
hypotheses have both a score and a realised result:

| Hypothesis | Stage-1 score | Realised PF |
|---|---|---|
| H-003 | 18/21 | 0.53 |
| H-006 | 18/21 | 0.94 |
| H-007 | 16/21 | 0.44 |
| H-010 | 16/21 | 0.35 |
| H-011 | 16/21 | 0.44 |
| H-008 | 15/21 | 0.88 |
| H-002 | 14/21 | 0.59 |

```
Pearson r (score vs PF), n=7            +0.146
Mean PF, scores >= 16                     0.54
Mean PF, scores <  16                     0.73
```

**The scorecard has no useful predictive power over this sample, and what
little signal there is points the wrong way** — the lower-scoring half performed
better.

The honest caveat, which matters as much as the result: n=7, and every outcome
is a failure. The profit factors span 0.35 to 0.94 with no successes anywhere in
the sample. A correlation measured across a narrow band of failure cannot tell
you whether the scorecard would discriminate a genuine edge from a failure. The
correct reading is *"no evidence it predicts degree of failure"*, not *"proven
useless"* — a distinction this document is now careful about for obvious reasons.

What the scorecard does demonstrably do is enforce a written economic rationale
before any trial is consumed, and kill structural duplicates cheaply. One
hypothesis was rejected at the gate as a duplicate of an existing strategy in
minutes, without consuming a trial. That is worth keeping regardless of its
predictive value.

---

## 5. Negative space

Results recorded as findings rather than discarded. From
[research/NEGATIVE_SPACE_MAP.md](research/NEGATIVE_SPACE_MAP.md):

**TRENDING_BULL is a hard gap, probed from six independent directions.** Six
hypotheses targeted that regime cell. All six were rejected at regime-N between
75 and 341, and — this is the part that matters — they are not variations on one
idea. They are six distinct mechanism classes:

| Hypothesis | Mechanism class | Data it depends on |
|---|---|---|
| H-002 | Price breakout continuation | Price only |
| H-003 | Perp funding confirmation | Derivatives positioning |
| H-007 | Spot-ETF net-flow demand | Regulated-vehicle flows |
| H-008 | Cross-sectional relative strength | Multi-asset ranking |
| H-010 | Coinbase premium | Cross-venue price divergence |
| H-011 | BTC lead-lag diffusion | Inter-asset timing |

Every one carries the `FUNDAMENTAL` failure tag, meaning the mechanism failed
rather than the implementation. Four of the six draw on data other than price —
this is not a case of testing the same momentum idea six ways.

The operational consequence is recorded: the next hypothesis for that regime
cell must come from a mechanism class genuinely outside these six. Another
continuation variant is not a new experiment, and would consume a trial for
information already held.

**Funding-based mechanisms are 0-for-3.** H-003, H-005 and H-006 all scored
18/21 at Stage 1 and all failed. The ledger records this explicitly as a family
caveat rather than three independent disappointments.

**Spot long-only beat futures long-short.** The scope amendment permitting
futures research (DEC-2026-05-28-001) produced the evidence that futures was
unnecessary: for every strategy with bidirectional signals, spot mode
outperformed futures with funding costs applied. Live futures execution was
therefore never built. The research paid for itself by preventing work.

---

## 6. What this does NOT establish

- **That no edge exists in crypto.** The claim is that this system, over this
  period, with these 29 generators, found none.
- **That the rejections generalise across time.** All of it comes from a bounded
  market period. Regime coverage is uneven and documented in
  `docs/research/regime_dsr/COVERAGE_MATRIX_*.md`.
- **That the cost model is right.** It is `v0_unverified` — deliberately
  pessimistic, but never calibrated against real fills, because paper trading
  was down. If it is too harsh, some rejections are too harsh.
- **That the backtests are free of methodology defects.** Six are open and
  severity-ranked in [research/RESEARCH_FIXLIST.md](research/RESEARCH_FIXLIST.md):
  walk-forward selecting on out-of-sample data (PARA-03), promotions below
  statistical minimum (PARA-04), overlapping rolling windows treated as
  independent (PARA-05), window-level rather than trade-level regime attribution
  (PARA-06), stop fills assuming no gap-through (PARA-07), and flat slippage
  ignoring order size (PARA-11).

PARA-04 deserves particular note here: it is the same class of error as the one
in Section 3. The list was written before that error was caught, and named it.

### A leak found after these results were produced

A thirteenth defect was found on 2026-08-13, after the results above were
generated. Two data channels stamped values with the start of the interval that
produced them while the value came from the interval's end, so a query could
receive a price up to 59 minutes ahead of itself. It affected H-2026-06-010 and
H-2026-06-011.

It changes nothing here, and the direction matters: lookahead inflates apparent
performance. Both affected hypotheses were rejected at PF 0.35 and 0.44 against
a break-even of 1.0 — with the leak helping them. Removing it can only make
those rejections more conservative.

The response was structural rather than local. `research/features/` now requires
every feature to declare its kind, interval and publication lag, computes when
each observation became knowable, and refuses to return anything the query
instant could not have seen. Causality is no longer a property each channel
asserts about itself. Recorded as PARA-13 and DEC-2026-08-13-001.

---

## 7. The pre-registered stop

`DEC-2026-06-04-010` fixes **2026-12-01** as the date the project evaluates
whether to continue, pivot, or stop, against criteria written in advance
including a cost model verified against real fills.

The date was set before the results were known. Two mechanism classes are
already eliminated for TRENDING_BULL, and the funding family is 0-for-3.

---

## 8. Reproducing this document

```bash
# Corrected classification of the stored retrospective results
python -c "
import json
from research.promotion.classifier import classify_tier
d = json.load(open('docs/research/retrospective/results_2026-06-05.json'))
for name, r in sorted(d['strategies'].items(), key=lambda kv: -kv[1]['n']):
    t = classify_tier(dsr_p_value=r['dsr_p_value'], max_dd_pct=0.0,
                      pf=r.get('adjusted_pf', 0.0), sharpe=0.0, n_trades=r['n'])
    print(f\"{name:10} N={r['n']:>3}  published={r['tier']:16} corrected={t.value}\")
"

# The hypothesis ledger
python -c "
import yaml
for h in yaml.safe_load(open('research/hypotheses/ledger.yaml')):
    r = h.get('results') or {}
    print(h['id'], h['status'], r.get('actual_n'), r.get('actual_pf_adjusted'))
"

# Re-run a screen
python -m scripts.regime_dsr --help
python scripts/retrospective_dsr.py --help
```

---

## 9. Reading order

1. [research/RESEARCH_PROTOCOL.md](research/RESEARCH_PROTOCOL.md) — the method and what it forbids
2. [research/HYPOTHESIS_QUALITY_GATE.md](research/HYPOTHESIS_QUALITY_GATE.md) — the Stage-1 scorecard
3. [research/NEGATIVE_SPACE_MAP.md](research/NEGATIVE_SPACE_MAP.md) — where edge is proven absent
4. [research/RESEARCH_FIXLIST.md](research/RESEARCH_FIXLIST.md) — the layer's own open defects
5. [research/retrospective/](research/retrospective/) — the superseded run, kept and labelled
