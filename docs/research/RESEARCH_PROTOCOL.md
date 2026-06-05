# PARAVANT Research Protocol

**Status:** Draft for adoption
**Owner:** Nai (research + operations)
**Last Updated:** 2026-05-28
**Applies to:** All strategy research, backtesting, and promotion decisions

---

## 0. Why this document exists

70% of the work in a quant system is research, and research is where money is
silently lost long before a single live trade. The danger is not bad math --
the engine math is sound. The danger is **process**: testing many ideas,
selecting the winners on small samples, and never correcting for the fact that
you went looking. This protocol is the discipline that separates a real edge
from a backtest artifact.

**Prime directive of research:** *Assume every edge is fake until overwhelming,
multiply-corrected, out-of-sample evidence says otherwise.* Most of the job is
killing your own ideas efficiently. A process that promotes 1 strong strategy
out of 50 will out-earn one that promotes 15 weak ones, because the 15 are
dominated by false positives that bleed out live.

---

## 1. The core problem we are defending against

| Failure mode | What it looks like here | Defense |
|---|---|---|
| Multiple testing | Many strategies x symbols x params tested, winners promoted | Experiment registry + deflated Sharpe + PBO |
| Small-sample illusion | PF 4.6 on 5 trades promoted | Minimum-evidence gate, Bayesian shrinkage |
| OOS leakage | Picking params by best out-of-sample score | Strict train/holdout separation, WFO done correctly |
| Backtest-vs-reality gap | Shorts simulated but unexecutable on spot; flat slippage | Executability check, cost stress, paper-as-truth |
| Regime confounding | Strategy looks good only because the market trended | Regime-conditional attribution, benchmark-relative scoring |
| No reproducibility | Data re-fetched every run; results drift | Frozen, versioned datasets |

---

## 2. The research funnel (pre-registered gates)

Every strategy moves through these stages in order. **Gate thresholds are
decided before looking at results** and are recorded in the experiment registry.
Moving a gate to make a strategy pass is forbidden unless the gate change is
documented, dated, and justified for ALL strategies (not the one in front of you).

```
HYPOTHESIS  ->  TRAIN (design freely)  ->  HOLDOUT (look once)  ->
SIMULATED PAPER  ->  LIVE PAPER  ->  MICRO-LIVE ($50-100)  ->  LIVE (scaled)
```

### Stage 1 - Hypothesis (mandatory, written down)
No strategy enters the funnel without a one-paragraph economic hypothesis
answering:
1. **What is the edge?** (e.g. "forced deleveraging in bull pullbacks creates
   short-lived oversold dips that trend-followers buy back")
2. **Who is on the other side of the trade, and why do they lose?**
3. **Why should this persist** rather than be arbitraged away?

If you cannot answer these, it is indicator mining, not research. Indicator
mining produces edges with no mechanism, and edges with no mechanism do not
survive contact with live markets.

### Stage 2 - Train period (look freely)
- Designated TRAIN window (see Section 4). You may iterate, tune, and explore
  here as much as you like.
- Run the **robustness battery** (Section 5).
- Reject anything that only works at a knife-edge parameter value.

### Stage 3 - Holdout (look ONCE)
- A contiguous, recent period that is **never touched during design**.
- You evaluate the locked strategy on it exactly once.
- If it passes the promotion gate (Section 6) after multiple-testing correction,
  it advances. If not, it is dead -- you do NOT "tune it a bit more," because
  that contaminates the holdout and turns it into another train set.

### Stage 4 - Simulated paper
- Continuous forward simulation on live prices (current `PaperTradingEngine`).
- This is genuine out-of-sample because the data did not exist at design time.

### Stage 5 - Live paper
- Same code path, polling live data. Validates execution timing assumptions.
- This is the authoritative sample for promotion (the current
  `scripts/validation_report.py` READY_FOR_LIVE gate lives here).

### Stage 6 - Micro-live ($50-100 real)
- Smallest real capital that still exercises the real broker. Catches the
  execution edge cases simulation cannot (partial fills, spot-short failures,
  rate limits, minimum notional).

### Stage 7 - Live (scaled)
- Scale capital only as live performance confirms paper performance.

---

## 3. Degrees-of-freedom budget and the experiment registry

The single highest-leverage change to the research process.

**Rule:** every backtest run is logged to an append-only registry. Without the
count of how many things you tried, you cannot compute deflated Sharpe, PBO, or
any honest significance number -- so you are flying blind on overfitting.

Each registry row records:
- `run_id`, UTC timestamp
- `git_sha` of the code
- `data_version` / dataset hash (see Section 4)
- `template_id`, full `parameters`, symbol, timeframe
- `train_window`, `holdout_window`
- random seed (if any)
- full metrics block (Sharpe, PF, trades, maxDD, expectancy, etc.)
- stage (train / holdout / paper)

**Degrees-of-freedom budget:** before starting a hypothesis, decide the maximum
number of parameter variations you will try, and stick to it. Fewer,
theory-driven variations beat brute-force grids -- every extra variation raises
the bar a winner must clear to be believed.

---

## 4. Data discipline (reproducibility)

Today backtests re-fetch from Binance on every run, so the window shifts daily
and results are not reproducible or comparable. Fix:

1. **Frozen dataset:** snapshot OHLCV to versioned parquet files with a content
   hash. Research reads the frozen snapshot, not the live API.
2. **Point-in-time integrity:** never let a backtest see a bar that closed after
   the decision timestamp (the engine already enforces this bar-to-bar; the
   dataset must not silently extend).
3. **Explicit windows:** TRAIN, HOLDOUT, and PAPER windows are named constants
   recorded with every run. Suggested split for an 18-24 month history:
   - TRAIN: oldest ~60%
   - HOLDOUT: next ~20% (look once)
   - PAPER/forward: remaining ~20% + ongoing live
4. **Refresh cadence:** re-snapshot on a schedule (e.g. monthly), bump the
   version, and re-run -- never silently mutate the existing snapshot.

---

## 5. The robustness battery (run on TRAIN, before holdout)

A strategy must survive ALL of these before it is allowed to touch the holdout.

1. **Parameter sensitivity:** sweep each key parameter and plot the metric
   surface. Reward broad **plateaus** (stable across neighbouring values),
   reject sharp **peaks** (works only at one magic number). A peak is the
   signature of overfitting.
2. **Walk-forward, done correctly:** for each window, optimize parameters on
   in-sample, LOCK them, measure on the following out-of-sample window, then
   aggregate OOS. Report **walk-forward efficiency** = OOS performance / IS
   performance. The PRD already mandates degradation < 50% (Section 3.6.1);
   wire this into the gate. (Note: the current `scripts/sweep_tp_wfo.py`
   selects the parameter with the best average OOS PF, which is selection on
   the test set -- fix before relying on it.)
3. **Probability of Backtest Overfitting (PBO)** via Combinatorially-Symmetric
   Cross-Validation (CSCV): estimate the chance the chosen config ranks below
   median out-of-sample. Target PBO < 0.5, ideally < 0.2.
4. **Monte Carlo trade reshuffle:** randomly reorder / resample the trade
   sequence thousands of times to get a distribution of max drawdown and a
   risk-of-ruin estimate. A strategy is only as safe as its bad-luck ordering.
5. **Deflated Sharpe Ratio:** adjust the Sharpe for the number of trials run
   (from the registry) and for return skew/kurtosis. Promote on deflated, not
   raw, Sharpe.
6. **Cost stress:** re-run at 2x and 3x slippage/commission. A real edge
   survives doubled costs; a fragile one evaporates.

---

## 6. Promotion gates (principled, low-N aware)

### 6.1 The trade-frequency reality (read this first)

The PRD validation framework assumes day-trading cadence (50-150 trades / 21
days). The strategies actually built are low-frequency swing strategies (often
2-25 trades per quarter). This single mismatch is why the 100-trade backtest
gate became impossible and was silently relaxed to 30, then to 5-10 in practice.

You must consciously choose one of two paths:

- **Path A - keep low-frequency strategies:** then redesign validation around
  small N. Use longer evaluation windows (12-18 months, not 21 days), pooled
  cross-sectional evidence (same template across many symbols counts as one
  body of evidence), and Bayesian shrinkage of PF/win-rate toward a skeptical
  prior. Do NOT promote on 5-10 trades regardless of how good they look.
- **Path B - build higher-frequency strategies:** target the 15m-1H cadence so
  100+ trade samples accrue in reasonable time, and the classical gates apply.

This is a foundational decision and should be recorded as a DECISION entry.

### 6.2 Backtest -> paper gate (proposed, replace the ad-hoc Gate1=5/10)

A strategy advances to simulated paper only if, on the HOLDOUT (looked at once):
- Minimum evidence: >= 30 trades (Path B) OR pooled >= 30 trades across the
  template's symbol set with consistent sign (Path A).
- Deflated Sharpe > 0 (after trial-count correction).
- Walk-forward degradation < 50% (PRD 3.6.1).
- PBO < 0.5.
- Survives 2x cost stress with PF > 1.0.
- Beats the benchmark (Section 7).

### 6.3 Paper -> live gate (keep, it is sound)
The existing READY_FOR_LIVE rule is good and should stay:
`N >= 30 live-paper trades AND PF >= 1.35 AND Sharpe >= 1.0 AND MaxDD <= 5%`
(`scripts/validation_report.py`). Add: beats benchmark over the same window.

---

## 7. Benchmark and alpha attribution (currently missing)

Every report must compare the strategy to **buy-and-hold of the traded asset**
(and to holding BTC) over the identical window. In a bull regime everything
long makes money; the question is whether the strategy beats simply holding.
Track:
- Excess return vs buy-and-hold.
- Beta to BTC (how much of the return is just crypto market exposure).
- Whether the edge survives after subtracting beta-driven return.

A "profitable" long strategy that returns 20% while BTC returned 60% is
destroying value. Without a benchmark you cannot see this.

---

## 8. Regime-conditional research

You already classify regimes (`RegimeDetector`, `HistoricalRegimeClassifier`).
Use them at the **trade level**, not the window level:
- Tag every trade by the regime at its entry bar.
- Build a per-strategy x per-regime expectancy table WITH confidence intervals.
- Only allocate a strategy in regimes where its edge is statistically positive.
- The router should map regime -> allocation weight, not just on/off.

---

## 9. Anti-patterns (forbidden)

- Moving a gate threshold to let a specific strategy pass.
- Re-using the holdout after a strategy failed it ("just one more tweak").
- Quoting PF/Sharpe without trade count and a confidence interval.
- Promoting on < 30 trades (or < 30 pooled, Path A) of evidence.
- Selecting parameters by best out-of-sample score.
- Reporting backtest returns that include unexecutable trades (e.g. spot shorts).
- Comparing strategies on raw, not deflated, Sharpe when many were tested.

---

## 10. Cadence

| Activity | Frequency |
|---|---|
| Dataset re-snapshot + version bump | Monthly |
| Validation report review (paper) | Weekly |
| Robustness battery on new candidates | Per candidate, before holdout |
| Multiple-testing recount (deflated Sharpe / PBO) | Per promotion decision |
| Benchmark-relative review of live strategies | Monthly |
| Regime-conditional table refresh | Monthly |

---

## 11. Related documents

- `docs/research/RESEARCH_FIXLIST.md` -- concrete bugs blocking trustworthy research.
- `docs/research/PORTFOLIO_LAYER_DESIGN.md` -- the return-correlation / allocation layer.
- `docs/TRADING_SYSTEM_PRD.md` Sections 3.6, 2.2.1 (Features A, F, G) -- existing,
  partially-unimplemented specs this protocol operationalizes.
