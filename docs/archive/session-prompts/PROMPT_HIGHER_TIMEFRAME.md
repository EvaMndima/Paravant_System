# Session Prompt — Test the Higher-Timeframe Boundary of the Meta-Finding

**Purpose**: Paste the block below into a fresh Claude Code session. This is a
CHEAP boundary experiment, NOT new sourcing. The meta-finding ("public signals are
arbitraged") was established entirely at the 1H timeframe. Arbitrage is most
intense at short timeframes; behavioral/structural edges persist longer at
daily/weekly. This session re-screens the EXISTING strongest-mechanism hypotheses
at higher timeframes — reusing channels and generators already built — to test
whether the wall extends to higher TF or whether an edge survives there.

**Written 2026-06-11.** Repo on `master`, dual-file DECISIONS in sync.

---

## COPY EVERYTHING BELOW THIS LINE INTO THE NEW SESSION

---

I'm continuing PARAVANT, a personal autonomous crypto trading system. The forward
hypothesis loop ran ~10 trials, ALL at the 1H timeframe, and produced a strong
meta-finding: every public signal computable from price/flow on liquid majors at
1H is already arbitraged (0 promotions). KEY SCOPE: that finding is specific to
**1H**. This session tests its BOUNDARY — do the same mechanisms survive at HIGHER
timeframes (4H / 1D), where arbitrage is less intense and momentum/structural
edges are academically documented to persist?

**Your job: re-screen EXISTING hypotheses at higher TF. No new sourcing, no new
mechanisms.** Reuse the generators and channels already built.

## Required reading (in this order)

1. `docs/research/NEGATIVE_SPACE_MAP.md` — the meta-finding + which mechanisms
   died at 1H (the calibration table + coverage grid).
2. `docs/research/HYPOTHESIS_QUALITY_GATE.md` + `.claude/DECISIONS.md` DEC-018,
   -020 (the gate + validation-methodology: honest K includes the TIMEFRAME
   dimension; no performance peek; DSR p<0.3 floor).
3. `research/hypotheses/ledger.yaml` — the H-003 / H-006 / H-008 / H-011
   pre-registrations + verdicts (what was tested at 1H).
4. `scripts/regime_dsr.py` and `scripts/backtest_rolling.py` — to find the
   timeframe knob (see FIRST TASK).
5. `.claude/CLAUDE.md` + `.claude/rules/decision-consistency.md`.

## FIRST TASK — confirm the timeframe is parameterizable

The 10 trials ran at 1H. Confirm whether `regime_dsr.py` / `backtest_rolling.py`
accept a timeframe argument or whether 1H is hardcoded. If hardcoded, the small
justified change is to parameterize the timeframe (and the data fetch interval) —
keep it minimal, one knob. Do NOT rebuild the engine.

## Which hypotheses to re-test (and which NOT)

Do NOT re-run all ten — that is timeframe-shopping across dead ideas and inflates
effective K for low expected value. Prioritize by MECHANISM PLAUSIBILITY at higher
TF:

- **YES — momentum family** (most plausible higher-TF survivors; momentum is
  documented to work at daily/monthly horizons even where it's arbitraged intraday):
  - H-003 funding-confirmed TREND (reuse `funding_confirmed_trend.py`)
  - H-008 cross-sectional MOMENTUM (reuse `cross_sectional_momentum.py`)
- **MAYBE — only if momentum shows life**: H-011 lead-lag (it INVERTED at 1H —
  laggards keep lagging; test the inverted/relative-strength direction carefully).
- **NO — contrarian/mean-reversion** (H-006 funding-contrarian): these typically
  live at SHORTER timeframes, not higher; skip unless there is a specific reason.

## The binding constraint: thin-N at higher TF

This is the #1 risk and you must address it up front. Higher TF = far fewer trades.
Daily over the standard 540-day window is only ~540 bars; a strategy trading a few
times a month lands at N~20-40. Mitigations, in order:
- **EXTEND the lookback window** (e.g. 1000-1500+ days; daily Binance OHLCV goes
  back years) to accumulate enough higher-TF trades.
- If still below min-N, the per-regime cell is **descriptive, not gating**
  (`Tier.INSUFFICIENT_DATA`, NOT TIER_D) — report it as "untestable at this TF,"
  not as a verdict. Do not rationalize a thin-N pass.

## Honest K + pre-registration (do not timeframe-shop)

- Each (hypothesis x timeframe) is a NEW trial; effective K already includes the
  timeframe dimension (DEC-2026-06-04-002). Testing H-003 at 4H AND 1D = two more
  trials, and BOTH count in K. Do not run many TFs and keep only the best without
  counting all of them.
- PRE-REGISTER each higher-TF variant in the ledger (e.g. `H-2026-06-XXX:
  funding-confirm @ 1D`) with expected metrics and fail modes BEFORE screening.
- No performance peek pre-DSR; DSR p<0.3 remains the floor.

## Honest expectation

The meta-finding may well extend — efficient markets are efficient at most
timeframes, and confirming the wall reaches daily is itself valuable knowledge.
Momentum at daily/weekly is the single most plausible survivor based on academic
evidence; treat a pass with appropriate skepticism (high Stage-1 / clean story is
NOT a predictor — H-003 scored 18/21 at 1H and still failed). Most likely outcome:
another honest set of rejects that tightens the negative-space map to "public
signals dead across 1H AND higher TF," which would strongly point the program back
at the liquidation/hard-data lens.

## Rules you MUST follow

- One-way dependency: `src/` never imports `research/`.
- Biography YAML canonical; markdown/JSON derived.
- Dual-file DECISIONS sync (`.claude/` AND `.agent/`, verify `diff` empty). File a
  DEC only if a real decision is made (e.g. parameterizing the TF knob); routine
  verdicts live in the ledger + negative-space map.
- Zero-tech-debt; tests for any new/changed code (>=80%).
- Do NOT enable live trading. Do NOT modify Neon data. Do NOT touch Railway region.
  Do NOT source new hypotheses — this session re-screens existing ones only.

## How to start

1. Read the required docs; confirm the TF knob (FIRST TASK).
2. Pre-register H-003 and H-008 at 4H and 1D (with extended lookback for N).
3. Use TodoWrite. Pre-register -> screen at higher TF -> verdict (tag
   FUNDAMENTAL/FIXABLE/INSUFFICIENT_DATA; update the negative-space map with a
   timeframe axis). One variant at a time.

## END COPY

---

**Note for Eva**: This is the cheapest experiment available — it reuses everything
already built and just changes the timeframe. It will most likely confirm the wall
extends to higher TF (which sends you decisively to the liquidation/hard-data
lens), but momentum-at-daily is the one place a public edge could plausibly survive,
so it's worth the near-zero cost to rule in or out before abandoning public signals
entirely. Watch the thin-N constraint — extend the lookback, and accept
INSUFFICIENT_DATA as an honest non-verdict rather than forcing a thin pass.
