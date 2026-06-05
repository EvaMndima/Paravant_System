# PARAVANT Portfolio / Return-Correlation Layer -- Design Sketch

**Status:** Design proposal (not yet built)
**Last Updated:** 2026-05-28
**Depends on:** `RESEARCH_PROTOCOL.md`, `RESEARCH_FIXLIST.md` (PARA-12)
**PRD basis:** This operationalizes PRD Feature A (2.2.1), Feature G (2.2.1), and
the deferred "Strategy correlation analysis" / "Portfolio rebalancing" items in
2.3. The PRD precondition for those ("needs multiple strategies running") is now
met -- ~9 strategies run in live paper -- so this should be pulled forward.

---

## 1. The problem this solves

The system currently promotes strategies **one at a time, in isolation**. There
is no object that represents "the portfolio" and no measurement of how strategies
behave **together**. Two concrete consequences:

1. **Config-similarity != return-correlation.** `src/core/strategy/similarity.py`
   compares template, parameters, symbols, and entry-logic text. Two strategies
   that score 0% similar there can be 95% **return-correlated** -- e.g. five
   different long-bull strategies that all buy BTC dips fire together and stop
   out together. The system's own live code already saw this: the
   `MAX_CONCURRENT_SAME_DIRECTION` cap in `scripts/run_live_trading.py:386-395`
   was added after 5 BTF-short sessions stopped out simultaneously for ~$395.
   That cap is a band-aid over a missing portfolio risk model.

2. **Capital is double-counted.** Each backtest assumes it owns 35% of the full
   account (`backtest/types.py:87`). Nine strategies cannot each deploy 35%, so
   the per-strategy returns are not additive and portfolio risk is unknown.

The goal: a layer that measures the **joint return behaviour** of strategies and
allocates shared capital so that portfolio-level drawdown and volatility are
controlled -- this is what "building a strategy portfolio" actually means.

---

## 2. Design principles

- Reuse, do not duplicate. Strategy return streams already exist implicitly in
  `PaperTradingSession.trade_log` / `equity_curve` and in backtest results.
- Correlation is measured on **returns**, not configuration.
- Start with assumption-light allocation (risk parity) before anything fancier.
- The portfolio layer is **read-mostly** at first: it produces weights and
  warnings that inform `run_live_trading.py`, not a rewrite of execution.
- Everything is regime-aware: correlations and allocations differ by regime.

---

## 3. Data model

### 3.1 Strategy return stream
The atomic input is a per-strategy time series of returns at a fixed cadence
(daily recommended for crypto 24/7).

```
StrategyReturnStream:
  strategy_id: str
  symbol: str
  template_id: str
  cadence: "1d"
  points: list[(timestamp_utc, return_fraction, equity)]
  source: "backtest" | "sim_paper" | "live_paper" | "live"
  data_version: str        # ties to the frozen dataset (protocol Section 4)
```

Build it by resampling each strategy's equity curve to daily and taking
day-over-day returns -- the same logic `metrics.py:_compute_daily_returns`
already uses. For live/paper, derive from `PaperTradingSession.equity_curve`.

### 3.2 Return matrix
Align all strategy streams on a common daily index (outer join, fill flat days
with 0 return when a strategy holds no position):

```
ReturnMatrix:  index = dates,  columns = strategy_ids,  values = daily returns
```

This single object powers correlation, covariance, and portfolio simulation.

---

## 4. Components

### 4.1 ReturnStreamStore
- Builds and caches `StrategyReturnStream` from backtest results and paper
  sessions.
- Persists to the DB alongside `PaperTradingSession` (no new external dependency).
- Keyed by `(strategy_id, source, data_version)` for reproducibility.

### 4.2 CorrelationEngine
- Produces the `ReturnMatrix` and computes:
  - Pearson and rank (Spearman) correlation matrices.
  - Rolling correlation (e.g. 30/60-day) to catch correlations that spike to 1.0
    in stress -- the dangerous kind.
  - Covariance matrix (for volatility-aware allocation).
- Flags **clusters** of strategies with correlation > 0.7 (the PRD Feature A
  threshold) -- this is the return-based replacement for the config-based
  `similarity.py` warning.
- Regime-conditional variants: compute correlations separately within each
  regime label from `HistoricalRegimeClassifier`.

### 4.3 Allocator
Turns the covariance/correlation into capital weights. Implement in stages:

1. **Risk parity (lite)** -- first target, matches PRD Feature G
   "Equal risk contribution". Each strategy contributes equal volatility to the
   portfolio; weights ~ inverse volatility, then adjusted for correlation.
   Robust and assumption-light -- good default.
2. **Volatility targeting** -- scale gross exposure so portfolio annualized vol
   hits a target (e.g. 10-15%).
3. **Fractional Kelly cap** -- size by edge but cap at a fraction (1/4 to 1/2)
   of full Kelly; full Kelly is too aggressive and overestimates edge on small
   samples. The WFO already computes a Kelly fraction
   (`sweep_tp_wfo.py:oos_metrics`) -- reuse, but cap and shrink it.
4. **(Later) constrained mean-variance** -- only once return estimates are
   trustworthy; mean-variance is fragile to noisy expected-return inputs.

Hard constraints from PRD Feature G:
- `minimum_cash_reserve_pct: 20%`, `emergency_buffer_pct: 10%`.
- `new_strategy_max_pct: 5%`, `proven_strategy_max_pct: 15%`.
- Per-symbol exposure caps from Feature A: BTC <= 40%, ETH <= 30%, correlated
  cluster <= 60%.

### 4.4 PortfolioRiskMonitor
- Given current open positions + weights, computes:
  - Portfolio mark-to-market equity, volatility, and current drawdown.
  - Aggregate per-asset exposure (replaces the crude same-direction counter).
  - Marginal contribution to risk per strategy (which strategy is driving
    portfolio risk right now).
- Emits warnings/blocks consumed by `run_live_trading.py` before entries.

### 4.5 Portfolio backtester (addresses PARA-12)
A thin orchestration over the existing `BacktestEngine` that:
- Runs all strategies over the SAME period on the frozen dataset.
- Allocates shared capital per the Allocator with reserves and caps.
- Produces a true **portfolio equity curve** with portfolio-level Sharpe,
  max drawdown, and correlation diagnostics -- the number that actually matters,
  rather than nine isolated single-strategy curves.

---

## 5. Integration points (existing code)

| Existing | Change |
|---|---|
| `src/core/strategy/similarity.py` | Keep for anti-clone generation, but stop treating it as a diversification measure; add a note pointing to CorrelationEngine. |
| `scripts/run_live_trading.py:386-395` | Replace `MAX_CONCURRENT_SAME_DIRECTION` heuristic with PortfolioRiskMonitor exposure checks. |
| `scripts/validation_report.py` | Add portfolio-level rows: combined Sharpe, combined maxDD, top correlated cluster. |
| `PaperTradingSession` (`src/data/models`) | Source of live/paper return streams. |
| `HistoricalRegimeClassifier` | Feeds regime-conditional correlation/allocation. |
| `backtest/types.py` (`position_size_pct`) | Superseded for portfolio runs by Allocator weights. |

---

## 6. Phased rollout

- **Phase 1 (measurement only):** ReturnStreamStore + CorrelationEngine. Output
  a correlation matrix and cluster report for the current ~9 paper strategies.
  Zero behaviour change -- pure insight. This alone tells you whether your
  "diversified" book is really one bet.
- **Phase 2 (portfolio backtest):** the Phase-5 portfolio backtester so promotion
  decisions can be made on portfolio impact, not isolated performance.
- **Phase 3 (allocation):** risk-parity Allocator + PortfolioRiskMonitor wired
  into live paper as advisory (warn, do not block).
- **Phase 4 (enforcement):** Monitor blocks entries that breach exposure/reserve
  caps; Allocator weights drive real sizing.

---

## 7. Metrics this layer must expose

- Portfolio Sharpe, Sortino, max drawdown, volatility (annualized).
- Pairwise correlation matrix + rolling correlation; largest correlated cluster.
- Per-strategy marginal contribution to risk.
- Diversification ratio (weighted avg vol / portfolio vol).
- Per-asset and per-regime aggregate exposure.
- Portfolio return vs buy-and-hold BTC (benchmark, per protocol Section 7).

---

## 8. Open questions to resolve before building

1. **Return cadence:** daily is recommended; confirm it is granular enough given
   low trade frequency, or use per-trade returns aligned to a calendar.
2. **Spot-short decision (PARA-01):** until resolved, return streams from
   short-heavy strategies are not realizable -- exclude or mark them.
3. **Estimation window:** how much history before correlations are trustworthy?
   (Crypto correlations are unstable; prefer rolling + regime-conditional.)
4. **Path A vs Path B trade frequency** (protocol Section 6.1) -- determines
   whether daily returns have enough non-flat days to estimate covariance well.
5. **Rebalance trigger:** PRD says monthly or on retirement; confirm acceptable
   given costs.

---

## 9. Why this is the highest-value next build

The research engine, regime classifier, and validation pipeline already exist
and mostly work. The missing piece between "a pile of individually-passing
strategies" and "a portfolio that compounds with controlled drawdown" is exactly
this layer. It is also the cheapest insurance against the failure the system
already experienced once (the correlated BTF stop-out): when one bet goes wrong,
a real portfolio loses one unit of risk, not five.
