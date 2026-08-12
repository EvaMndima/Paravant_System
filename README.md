# PARAVANT

**An autonomous crypto trading system, and a validation layer built to prove
its own strategies don't work.**

It worked, and the most instructive thing it did was catch an error in its own
reporting.

After four months and 29 signal generators, **no strategy in this repository has
a validated edge.** Three were rejected outright at adequate sample size under
Deflated Sharpe. Ten more were initially reported as rejected — until the
system's own guard established that they had never had enough data to reject,
and reclassified them as *unmeasurable*.

The difference between "proven worthless" and "never actually measured" is the
whole discipline. Getting it wrong in the safe direction, then catching it, is
the result this repository exists to report. The trading engine is the
supporting cast.

---

## Why this might be interesting

Most trading repositories show you a backtest that made money. This one shows
you the machinery that determines whether a backtest that made money *means*
anything, applied adversarially to its author's own six months of work until it
returned `no`.

The core question the research layer answers is:

> Did this result come from signal, or from running enough experiments that
> something had to look good?

That is the multiple-comparisons problem. It is why a strategy with a Sharpe of
2.0 discovered on the 200th configuration is worth less than one discovered on
the 2nd — and it is structurally the same problem that makes benchmark numbers
hard to trust anywhere results are searched for rather than predicted: model
evaluation, A/B testing, hyperparameter search, LLM benchmarks.

The defenses implemented here are the standard ones for that class of problem:

| Failure mode | Defense implemented |
|---|---|
| Many experiments, best one reported | Deflated Sharpe Ratio + effective-trial counting |
| Gates moved to fit the result | Thresholds pre-registered before results are seen |
| Test set used for selection | Strict train/holdout separation, holdout looked at once |
| Small-sample illusion | Minimum-evidence gate, `INSUFFICIENT_DATA` distinct from `REJECT` |
| Confounding | Regime-conditional attribution across 8 market states |
| Optimistic cost assumptions | Versioned cost model, deliberately pessimistic |
| Negative results discarded | Negative-space map treats "no edge here" as a finding |

A written protocol (`docs/research/RESEARCH_PROTOCOL.md`) forbids moving a gate
to make a strategy pass, and a pre-registered date — 2026-12-01 — fixes when the
project evaluates whether to stop, against criteria written in advance.

---

## The result

Three strategies were rejected at a sample size large enough for the verdict to
mean something:

| Subject | Source | N | Profit factor | DSR p | Verdict |
|---|---|---|---|---|---|
| BTF (bear trend follower) | Recorded trades | 25 | 0.54 | 1.000 | `TIER_D` reject |
| H-2026-06-002 (price breakout continuation) | Backtest | 341 | 0.59 | 1.000 | `TIER_D` reject |
| H-2026-06-003 (funding-confirmed trend) | Backtest | 132 | 0.53 | 1.000 | `TIER_D` reject |

A fourth hypothesis was killed at the quality gate as a structural duplicate of
an existing strategy, before it consumed a trial.

### The part worth reading

The 2026-06-05 retrospective originally reported **all eleven** strategies as
`TIER_D_REJECT`. That report was wrong, and the project's own tooling is what
established it.

Ten of the eleven had between **0 and 4 recorded trades**. The paper-trading
process had been down behind a regional exchange block, so the trade records the
analysis read were nearly empty. A Deflated Sharpe p-value of 1.000 computed on
zero trades is not a finding — it is a null input producing a degenerate output,
and it was being printed next to the word "reject".

The fix was a floor (`MIN_N_FOR_CLASSIFICATION = 10`) checked *before* any
threshold, returning a distinct `INSUFFICIENT_DATA` verdict. From
[`research/promotion/classifier.py`](research/promotion/classifier.py):

> A genuinely edge-less strategy with enough trades still earns `TIER_D`; only
> data *scarcity* yields `INSUFFICIENT_DATA`. The 2026-06-05 run's N=0..4
> strategies were wrongly shown as `TIER_D_REJECT`; this guard prevents that
> "no data" -> "proven noise" misread.

Re-running the stored 2026-06-05 results through the corrected classifier:

```
                        as published    corrected
TIER_D_REJECT                    11            1
INSUFFICIENT_DATA                 0           10
```

This is the oldest error in applied statistics — treating absence of evidence as
evidence of absence — and it is the exact failure the whole research layer was
built to prevent, committed by that research layer, caught by it, and left in
the repository with the superseded report still in place and marked.

**None of this changes the bottom line: zero validated strategies.** It changes
how much of that is *demonstrated* versus merely *unmeasured*, which is a
distinction worth being precise about.

### What was concluded

Trending-bull continuation is a hard gap across two distinct mechanism classes
(price momentum and derivatives flow), both rejected at large N. The next
hypothesis for that regime must come from a different mechanism class entirely.

A calibration lesson was recorded alongside it: H-003 scored *higher* at the
hypothesis-quality gate (18/21 vs 14/21) and performed *worse*. The scorecard
measures mechanism plausibility, not expected profitability. That was written
down rather than explained away.

Full write-up: **[docs/RESEARCH_FINDINGS.md](docs/RESEARCH_FINDINGS.md)**

---

## Architecture

Three processes from one image: a read/query API, a paper-trading loop, and a
live loop behind a default-off kill switch. Paper and live share the entire code
path and diverge only at the execution interface, which is what makes paper
results usable as a promotion gate.

```mermaid
flowchart TD
    A[Binance REST] --> B[MarketDataFetcher]
    B --> C[OHLCVSeries, cached]
    C --> D[IndicatorFactory, cached]
    D --> E[SignalGenerator]
    E --> F{RegimeRouter<br/>allowed in this regime?}
    F -->|no| Z[No trade]
    F -->|yes| G{RiskController}
    G --> H[kill switch, checked first<br/>daily / weekly loss<br/>max drawdown<br/>open positions<br/>concentration<br/>position size<br/>portfolio correlation<br/>5 circuit breakers]
    H -->|rejected| Y[Logged + alerted]
    H -->|approved| I[PositionSizer]
    I --> J[OrderManager<br/>state machine]
    J --> K[ExecutionInterface]
    K --> L[BinanceExecution]
    K --> M[PaperExecution]
    L --> N[PositionTracker]
    M --> N
    N --> O[(DataStore)]
    O --> P[ExecutionQuality<br/>slippage, fill rate]
    O --> Q[Telegram alerts]
```

The research layer sits alongside and may import from `src/`, but `src/` may
never import from `research/`. That one-way boundary means research experiments
cannot change live behaviour, and the research tree could be deleted without
breaking the trading system.

```mermaid
flowchart LR
    H[Hypothesis<br/>written economic rationale] --> Q{Quality gate<br/>scored /21}
    Q -->|fail| X[Killed, no trial consumed]
    Q -->|pass| T[Train<br/>design freely]
    T --> O[Holdout<br/>looked at ONCE]
    O --> D{Deflated Sharpe<br/>p < 0.3 floor}
    D -->|fail| R[Tier D, retired<br/>+ post-mortem]
    D -->|pass| S[Simulated paper]
    S --> L[Live paper]
    L --> G{READY_FOR_LIVE<br/>N>=30, PF>=1.35<br/>Sharpe>=1.0, DD<=5%}
    G -->|fail| R
    G -->|pass| M[Micro-live, $50-100]
    M --> V[Live, scaled]
```

Every strategy that reaches `Tier D` gets a generated post-mortem with a tagged
failure pattern, and every strategy carries an append-only biography. Retirement
is a completed process, not a deletion.

Deeper detail: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** ·
**[docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)**

---

## What is in here

| Layer | Files | Lines | Notes |
|---|---|---|---|
| `src/` application | 167 `.py` | 49,144 | API, risk, execution, indicators, strategies |
| `tests/` | 133 `.py` | 36,363 | 1,905 tests, 63% coverage |
| `frontend/src/` | 89 `.ts`/`.tsx` | 17,128 | React 19 dashboard — see caveat below |
| `scripts/` | 24 | 11,865 | Live loop, paper loop, sweeps, reporting |
| `research/` | 27 `.py` | 5,411 | DSR, effective-K, cost model, biographies |

Highlights:

- **Risk layer** — 8 pre-trade checks, 5 circuit breakers with state that
  survives restart, kill switch, dead man's switch, time/event/volatility
  filters. Position sizing at 100% coverage, checks at 99%.
- **Live capital model** — per-strategy capital slicing, a concurrency cap, an
  85% capital reserve, and a minimum-notional guard that calls `sys.exit(1)`
  rather than rounding an order up to the exchange minimum.
- **Promotion gate** — a strategy cannot go live until its pooled paper record
  is classified `READY_FOR_LIVE`. Fails *open* on a database error so a restart
  is not blocked; fails *closed* on a clear non-ready verdict.
- **19 indicators**, each independently tested at 88-100% coverage.
- **29 signal generators**, of which 0 are validated. That ratio is the point.
- **116 dated architectural decisions** with rationale and rejected
  alternatives, referenced by 69 distinct IDs from source comments.

---

## Quickstart

```bash
git clone <this repo> && cd Paravant_System

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
cp .env.example .env            # placeholders are fine for a read-only run

python scripts/init_db.py
uvicorn src.api.main:app --reload
```

Then open <http://localhost:8000/docs> for the interactive API.

Live trading additionally requires `LIVE_TRADING_ENABLED` to be set explicitly.
It is deliberately absent from `.env.example`, so a fresh clone cannot trade by
accident.

Frontend:

```bash
cd frontend && npm install && npm run dev
```

Research tooling:

```bash
python scripts/retrospective_dsr.py --help    # the DSR analysis
python scripts/validation_report.py --help    # daily operator report
```

---

## What this is not

Stated plainly, because a reviewer will find all of it anyway.

- **Not a profitable trading system.** No strategy here passes its own
  validation gates. If it had an edge, this README would be a different
  document and probably would not exist.
- **Not authenticated.** All 63 API endpoints are open, including 21 that mutate
  state. Do not expose it to a network you do not control. See
  [SECURITY.md](SECURITY.md).
- **The dashboard is a prototype.** 17,000 lines of React that make three real
  network calls. Every other page renders static seed data and the simulated
  ticker is labelled as such in code. It is honest in the source and it is not
  finished.
- **Not machine learning.** There is no model here. This is systems engineering
  and quantitative research methodology. The overlap with AI engineering is the
  evaluation discipline, not the algorithms.
- **Not fully clean.** 9 tests fail on `master`, 32 network-dependent
  integration tests error rather than skip without exchange credentials, and
  static analysis reports outstanding errors against a config that claims strict
  typing. All of it is enumerated in
  [docs/PRODUCTION_READINESS_ASSESSMENT.md](docs/PRODUCTION_READINESS_ASSESSMENT.md),
  which was written to be uncomfortable rather than flattering.
- **Not built alone in the conventional sense.** It was built by one person
  working with AI coding assistants throughout. What that was actually like,
  including six specific defects it produced and how long each survived, is in
  [docs/AI_ASSISTED_DEVELOPMENT.md](docs/AI_ASSISTED_DEVELOPMENT.md).

---

## Documentation

**Start here**

- [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) — complete briefing; readable without opening a source file
- [docs/research/RESEARCH_PROTOCOL.md](docs/research/RESEARCH_PROTOCOL.md) — the method, and what it forbids
- [docs/AI_ASSISTED_DEVELOPMENT.md](docs/AI_ASSISTED_DEVELOPMENT.md) — what AI-assisted development actually broke

**The result**

- [docs/research/retrospective/](docs/research/retrospective/) — per-strategy DSR post-mortems
- [docs/research/NEGATIVE_SPACE_MAP.md](docs/research/NEGATIVE_SPACE_MAP.md) — where edge is proven absent
- [docs/research/RESEARCH_FIXLIST.md](docs/research/RESEARCH_FIXLIST.md) — the research layer's own known defects, six still open

**Engineering**

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/API_CONTRACT.md](docs/API_CONTRACT.md) · [docs/INDICATOR_SPECIFICATION.md](docs/INDICATOR_SPECIFICATION.md)
- [.claude/DECISIONS.md](.claude/DECISIONS.md) — 116 decisions with rationale and rejected alternatives
- [docs/operations/](docs/operations/) — kill-switch runbook, scheduled jobs
- [docs/PRODUCTION_READINESS_ASSESSMENT.md](docs/PRODUCTION_READINESS_ASSESSMENT.md) — measured gaps and the plan

---

## Development

```bash
pytest                                        # full suite
pytest -m unit                                # fast path
pytest --cov=src --cov=research --cov-report=term

ruff check src/ research/ scripts/
mypy src/
black src/ tests/
```

---

## License

MIT, with a financial-software risk notice. See [LICENSE](LICENSE).

This software can place real orders and lose real money. It is published as an
engineering artifact, not as investment advice, and it comes with no warranty.
