# PARAVANT Research Bugs and Correctness Fix-List

**Status:** Findings from research-layer audit, 2026-05-28
**Scope:** Bugs and correctness issues that distort research results or the
backtest-to-live mapping. Ordered by money-impact.
**Note:** This is a findings/plan document. No code has been changed. Items that
touch locked decisions (PARA-01) require a DECISIONS.md entry before fixing.

---

## Severity legend

- **CRITICAL** -- directly causes promoted strategies to overstate realizable edge.
- **HIGH** -- corrupts research data or biases promotion decisions.
- **MEDIUM** -- weakens conclusions or skews specific metrics.
- **LOW** -- localized metric inaccuracy.
- **PERF** -- performance; indirectly fuels overfitting by forcing small samples.

---

## Summary table

| ID | Sev | Issue | Location |
|----|-----|-------|----------|
| PARA-01 | CRITICAL | Short trades simulated but unexecutable on spot | `scripts/run_live_trading.py:1257`; 17 generators |
| PARA-02 | HIGH | Live-paper force-close uses a nonsense price | `src/core/strategy/paper/engine.py:598-605` |
| PARA-03 | HIGH | WFO selects parameters on out-of-sample data | `scripts/sweep_tp_wfo.py:519-523` |
| PARA-04 | HIGH | Promotions on samples far below statistical minimum | `validator.py:92`; `sweep_tp_wfo.py:64`; practice |
| PARA-05 | MEDIUM | Rolling-window backtests are not independent | `scripts/backtest_rolling.py:440-457` |
| PARA-06 | MEDIUM | Regime attribution is window-level, not trade-level | `scripts/backtest_rolling.py:400-414` |
| PARA-07 | MEDIUM | Stop/TP fills assume no gap-through | `src/core/strategy/backtest/trader.py:400-447` |
| PARA-08 | LOW | per-symbol total_return sums percentages | `src/core/strategy/backtest/metrics.py:568` |
| PARA-09 | LOW | largest_loss mislabels smallest win | `src/core/strategy/backtest/metrics.py:235` |
| PARA-10 | PERF | O(n^2) backtest; uncached array rebuilds | `engine.py:143`; `market_data.py:262-269` |
| PARA-11 | MEDIUM | Flat slippage ignores order size (PRD specs size-aware) | `backtest/types.py:84` vs PRD 3.6.2.1 |
| PARA-12 | MEDIUM | Each strategy backtested assuming full capital | `backtest/types.py:87`; no portfolio capital model |

---

## PARA-01 (CRITICAL) -- Short trades are simulated but cannot execute on spot

**Where:**
- 17 of 29 generators emit `SignalDirection.SHORT`.
- Backtest credits short P&L: `src/core/strategy/backtest/portfolio.py:237-241`.
- Paper trading is pure simulation (reuses `SimulatedTrader`):
  `src/core/strategy/paper/engine.py:99`.
- Live path maps SHORT to a spot SELL: `scripts/run_live_trading.py:1257`
  (`order_side = "buy" if sig_dir == "LONG" else "sell"`).

**Problem:** Locked decisions (PRD 1.7; `.claude` DEC-2026-01-15-002/004) restrict
to Binance **spot** + **market** orders. On spot you cannot sell an asset you do
not hold, so a SHORT signal cannot be executed. Backtest and paper both book
short profits that live trading cannot realize.

**Impact:** Every strategy with a short side overstates realizable edge.
Strategies whose edge is mostly short are phantoms. This is also a
locked-decision-vs-implementation inconsistency.

**Fix options (requires a DECISION):**
- A) Long-only on spot: disable short signal emission, re-run the full funnel
  long-only. Many strategies will fail -- that is information you want.
- B) Move shorts to Binance Futures/perps: breaks the spot lock; must then model
  funding cost and liquidation. New DECISION + PRD update required.

**Do not fix in code until the decision is made.** Flag, then decide.

---

## PARA-02 (HIGH) -- Live-paper force-close uses a dimensionless ratio as a price

**Where:** `src/core/strategy/paper/engine.py:598-605`
```python
price=last_point.equity / max(1.0, last_point.position_value)
      if last_point.position_value > 0 else last_point.equity
```

**Problem:** `equity / position_value` is a ratio (~1.x), not a market price.
On manual stop with an open position, the final trade closes at ~$1-2 instead
of the market price.

**Impact:** Corrupts the session trade log and equity curve -- the exact data
`scripts/validation_report.py` uses for live-promotion decisions.

**Fix sketch:** pass the actual last close price. The engine already records
`current_price` per bar in `_process_live_bar`; retain the last bar's close and
force-close at that, mirroring `BacktestEngine` which force-closes at
`last_bar.close`.

---

## PARA-03 (HIGH) -- Walk-forward optimizer selects parameters on the OOS set

**Where:** `scripts/sweep_tp_wfo.py:519-523` -- `optimal_rr` is chosen as the
`risk_reward_ratio` with the highest **average OOS profit factor**.

**Problem:** Choosing the parameter by best out-of-sample score is selection on
the test set, which defeats the purpose of OOS. The plateau analysis
(`robustness_plateau`) partially mitigates by favouring stable regions, but the
headline "UPDATE RECOMMENDED" value is OOS-fit.

**Impact:** TP/stop recommendations look more robust than they are; the OOS PF
is no longer an honest generalization estimate.

**Fix sketch:** implement proper WFO -- for each window, pick the best IS
parameter, LOCK it, evaluate on the following OOS window, then aggregate the
locked-parameter OOS results. Report walk-forward efficiency (OOS/IS).

---

## PARA-04 (HIGH) -- Promotions happen on samples far below statistical minimum

**Where:**
- Backtest validator floor: `src/core/strategy/backtest/validator.py:92`
  (`min_num_trades = 30`).
- WFO sparse threshold: `scripts/sweep_tp_wfo.py:64` (`MIN_OOS_TRADES = 3`).
- Practice (per project memory): promotions at Gate1=10, Gate1=5, and OBSERVE
  calls at 2-4 trades.

**Problem:** PF/Sharpe on 3-10 trades is noise. With 8 symbols x dozens of
strategies, spectacular small-N sequences appear by chance.

**Impact:** The promoted set is contaminated with false positives.

**Fix sketch:** adopt the principled gates in `RESEARCH_PROTOCOL.md` Section 6:
minimum 30 trades (or 30 pooled across a template's symbols, Path A), deflated
Sharpe, PBO, cost-stress. Decide Path A vs Path B (trade frequency) first.

---

## PARA-05 (MEDIUM) -- Rolling-window backtests overlap and are not independent

**Where:** `scripts/backtest_rolling.py:440-457`. Each 60-day window is sliced as
`[window_start - 35d, window_end]`, and warmup-prefix trades count toward window
metrics.

**Problem:** Consecutive windows share ~35 days; trades in the overlap are
double-counted. Windows are correlated, so the coefficient of variation across
windows understates true variance.

**Impact:** STABLE_EDGE / OVERFIT verdicts are biased optimistic.

**Fix sketch:** compute warmup indicators from the prefix but only count trades
whose entry falls within the nominal (non-overlapping) window; or use fully
disjoint windows with a separate warmup buffer that never contributes trades.

---

## PARA-06 (MEDIUM) -- Regime attribution is window-level, not trade-level

**Where:** `scripts/backtest_rolling.py:400-414` tags an entire 60-day window
with one dominant regime.

**Problem:** A 60-day window spans multiple sub-regimes. Trades opened in a
different sub-regime than the window label are mis-attributed.

**Impact:** Weakens the "which strategy works in which regime" conclusion -- the
most decision-relevant output.

**Fix sketch:** the per-bar classifier already exists
(`HistoricalRegimeClassifier.classify_series`). Tag each trade by the regime at
its entry bar and aggregate per-regime at the trade level.

---

## PARA-07 (MEDIUM) -- Stop/TP fills assume no gap-through

**Where:** `src/core/strategy/backtest/trader.py:400-447`. A hit stop fills at
exactly the stop price + slippage.

**Problem:** When a bar gaps through the stop (opens beyond it), the realistic
fill is at the bar open, which is worse. The model is optimistic on gaps.

**Impact:** Understates tail losses precisely during crashes -- when survival
matters most.

**Fix sketch:** if `bar.open` is already beyond the stop (below for long, above
for short), fill at `bar.open` rather than the stop level, then apply slippage.

---

## PARA-08 (LOW) -- per-symbol total_return sums percentage returns

**Where:** `src/core/strategy/backtest/metrics.py:568`
(`total_return = sum(t.return_pct for t in sym_trades)`).

**Problem:** Summed per-trade percentages are not a compounded return and are
not comparable to the portfolio-level `total_return_pct`.

**Fix sketch:** compound the per-trade returns, or sum realized PnL and divide
by the per-symbol capital base.

---

## PARA-09 (LOW) -- largest_loss mislabels the smallest win

**Where:** `src/core/strategy/backtest/metrics.py:235`
(`largest_loss = min(all_pnl)`).

**Problem:** When all trades are positive, `min(all_pnl)` returns the smallest
win, reported as "largest loss".

**Fix sketch:** compute `largest_loss` over losing trades only; default to 0.0
when there are none.

---

## PARA-10 (PERF) -- O(n^2) backtest from re-slicing and uncached array rebuilds

**Where:**
- `src/core/strategy/backtest/engine.py:143` re-slices the full series each bar.
- `src/data/market_data.py:262-269` (`closes`, `highs`, `lows`, ...) rebuild a
  numpy array from the candle list on every access; generators recompute all
  indicators from scratch each bar.

**Problem:** For a 180-day 1H run (~4,300 bars) this is millions of redundant
operations per indicator per backtest, and sweeps run hundreds of backtests.

**Impact (the important part):** slow backtests force small samples and narrow
searches -- which is causally upstream of the overfitting risk. Speeding this up
buys statistical rigor (more data, more symbols, real cross-validation).

**Fix sketch:** precompute indicators once over the full series and index into
them per bar (vectorized / incremental), or cache the numpy arrays on
`OHLCVSeries` since candles are immutable.

---

## PARA-11 (MEDIUM) -- Flat slippage ignores order size; PRD specs size-aware

**Where:** `src/core/strategy/backtest/types.py:84` (`slippage_rate = 0.0005`,
flat). PRD 3.6.2.1 and Feature F specify
`0.05% + (order_size / daily_volume) * 0.5%`.

**Problem:** Backtest costs are optimistic and uniform across symbols; DOGE/AVAX
at size slip more than BTC. The size-aware model the PRD already designed is not
implemented in the backtest.

**Fix sketch:** implement the PRD slippage model in the simulated trader, keyed
off symbol average volume; add the 2x/3x cost-stress runs from the protocol.

---

## PARA-12 (MEDIUM) -- Each strategy backtested assuming the full capital base

**Where:** `src/core/strategy/backtest/types.py:87`
(`position_size_pct = 0.35` of the full $10k), single-position portfolio.

**Problem:** Every strategy is evaluated in isolation as if it owns 35% of the
full account. The live portfolio of ~9 strategies cannot each deploy 35%;
reported per-strategy returns are not additive.

**Impact:** No model for how strategies share capital -- portfolio returns and
risk cannot be derived from the per-strategy backtests.

**Fix sketch:** addressed by the portfolio layer
(`docs/research/PORTFOLIO_LAYER_DESIGN.md`): a portfolio backtest that allocates
shared capital across concurrent strategies with reserves and per-strategy caps.

---

## Suggested fix order

1. PARA-01 decision (long-only vs futures) -- everything downstream depends on it.
2. PARA-02, PARA-09, PARA-08 -- quick correctness fixes to stop data corruption.
3. PARA-10 -- speed, which unblocks rigorous sampling.
4. PARA-03, PARA-04, PARA-05, PARA-06 -- methodology fixes for trustworthy gates.
5. PARA-07, PARA-11 -- realism (gaps, size-aware costs) + cost stress.
6. PARA-12 -- via the portfolio layer.
