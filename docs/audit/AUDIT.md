# PARAVANT — Pre-Publication Repository Audit

**Audit date:** 2026-08-08
**Commit audited:** `622ac49` (master), plus 71 uncommitted working-tree changes
**Reviewer stance:** staff engineer, pre-open-source review, skeptical of AI-assisted code
**Scope:** read-only. No code was modified, refactored, or deleted.

---

## 0. Verdict up front

The engineering underneath this repo is better than the repo itself. There is a real
system here: 66,557 lines of Python across `src/`, `scripts/`, and `research/`; 1,884 test
functions; 71% line coverage; zero bare `except:` clauses; a research layer with a
stdlib-only Deflated Sharpe Ratio implementation at 100% coverage; and a 102-commit history
with disciplined conventional-commit messages carrying decision IDs.

That work is currently invisible, and three things actively misrepresent it:

1. **The headline claims do not survive contact with the code.** There are no agents. There
   is no vectorbt, no backtrader, no Optuna. Section 7 documents this in detail. This is the
   single highest-risk item in the audit, because a reviewer who checks one claim and finds
   it false stops believing the rest.
2. **`git clone && pytest` is red.** 9 failures and 32 errors, the errors being live network
   calls to Binance testnet from the default test invocation.
3. **The README and architecture doc were last touched on the initial commit and describe a
   system that no longer exists.**

Nothing here is unfixable. Most of it is a weekend. But publishing as-is would be worse than
not publishing.

---

## 1. Secrets and publication safety

**Status: clean. This is the one dimension that needs no work.**

| Check | Result |
| --- | --- |
| `.env` tracked in git | No — `git ls-files --error-unmatch .env` fails. Ignored at [.gitignore:36](../../.gitignore#L36) |
| Secrets in git history (pickaxe: Telegram bot tokens, `sk-ant-`, `BINANCE_API_SECRET=`) | Zero hits across all refs |
| Key-shaped strings in tracked files (`sk-`, `xox*-`, `AKIA*`, `ghp_`, PEM headers, Telegram `NNNNNNNNN:AA…`) | One hit only: [tests/unit/core/test_errors.py:457](../../tests/unit/core/test_errors.py#L457), a fake `sk-abcdefghij1234567890` used as a redaction-test fixture. Correct and intentional. |
| Files ever added to history matching `.env`/`.db`/`.sqlite`/`credential`/`.pem`/`.key`/`.log`/dump | Only `.env.example` |
| `data/trading.db` (4.4 MB, real paper-trade records) | Untracked. Only `data/.gitkeep` is tracked. |
| `backend.log` (333 KB), `paper_trading_test.log` (33 KB), `.coverage` | All untracked, all covered by `.gitignore` |
| `logs/` | Only `logs/.gitkeep` tracked |

`.env.example` at the repo root is a correct, complete template with no real values.

### Judgement calls, not leaks

- **`.claude/DECISIONS.md` and `.agent/DECISIONS.md` are 267 KB each and byte-identical**
  (verified via `diff`). Publishing them exposes your full internal decision log, including
  live capital sizing (`LIVE_CAPITAL >= $100`), the kill-switch design, and every strategy
  that failed. This is not a security problem — it is arguably your best evidence of
  engineering judgement — but it is a deliberate choice you should make consciously rather
  than by omission.
- **Repo weight.** [docs/design/pdf/themes.pdf](../design/pdf/) alone is 15.5 MB; tracked
  design PDFs and screenshots total roughly 25 MB. A `git clone` of a trading system that is
  mostly design PDFs is a strange first impression, and it is slow.
- **No financial or legal exposure** beyond the ordinary. There is a risk disclaimer gap
  (Section 8), which matters for a public repo that can place real orders.

---

## 2. First impression

**Read as a stranger: the root directory is the problem, not the code.**

`ls` at the repo root returns, before you reach anything that looks like software:

- **35 `SESSION_*.md` / `PHASE_*.md` files totalling 1,048,887 bytes** (~1.05 MB). These are
  AI implementation prompts and verification checklists —
  `SESSION_4A_IMPLEMENTATION_PROMPT.md` is 74 KB, `SESSION_3A_IMPLEMENTATION_PROMPT.md` is
  64 KB. All 35 are tracked.
- **17 loose Python scripts totalling 3,895 lines**: `test_backtest.py`,
  `test_backtest_complete.py`, `test_backtest_direct.py`, `test_debug.py`, `test_network.py`,
  `test_system.py`, `run_final.py`, `run_donchian_test.py`, `run_round2_refinements.py`,
  `create_strategy_variations.py`, `create_strategy_variations_correct.py`, and others. All
  tracked. `create_strategy_variations.py` and `create_strategy_variations_correct.py`
  sitting side by side is its own sentence.
- `backend.log`, `paper_trading_test.log`, `.coverage` (untracked, but present locally — they
  will not ship, though they signal the working style).

**This is the single most damaging thing in the repo, and it is also the cheapest to fix.**
A reviewer's model of you forms here. `SESSION_4A_IMPLEMENTATION_PROMPT.md` at the top level
tells them, before they read a line of code, that this was prompt-driven and never tidied.
`test_backtest_direct.py` next to `test_backtest_complete.py` next to `test_debug.py` tells
them nothing was ever consolidated. Combined, they invite exactly the skepticism you asked me
to check for.

### Can someone understand what this does in 60 seconds?

Partially. [README.md](../../README.md) opens with a clear one-liner and an MVP feature list.
But it describes a February system: "Strategy Library: 6 pre-built templates" when
`config/templates/` holds 14 YAML files and `src/core/strategy/generators/` holds 29
generators. It never mentions the regime router, the sub-regime detector, the paper-trading
promotion pipeline, the research/DSR layer, or the Railway deployment — i.e. the majority of
what you actually built.

### Can someone install and run it in under 10 minutes?

Probably, but with two failure modes:

- **A missing dependency.** `requests` is imported by four files —
  [research/data/coinbase_prices.py](../../research/data/coinbase_prices.py),
  [research/data/etf_flows.py](../../research/data/etf_flows.py),
  [research/data/funding_rates.py](../../research/data/funding_rates.py),
  [scripts/regime_dsr.py](../../scripts/regime_dsr.py) — and appears in **neither**
  `requirements.txt` nor `requirements-research.txt`. It installs today only as a transitive
  dependency of `python-binance`.
- **README step 5 (`uvicorn src.api.main:app --reload`) starts the API, which is not the
  system.** The actual trading system is `python -m scripts.run_all`
  ([railway.toml](../../railway.toml)). The README never mentions it.

---

## 3. Structural coherence

### 3.1 Two orchestration implementations; the tested one is dead

This is the most serious structural finding.

[src/core/orchestrator.py](../../src/core/orchestrator.py) is 1,800 lines / 575 statements,
sits at **71% test coverage** via [tests/unit/test_orchestrator.py](../../tests/unit/test_orchestrator.py)
(24 tests), and is **never instantiated in production code.**

Proof:
- No file outside `tests/` imports it. `git grep "from src.core.orchestrator"` returns only
  test files.
- [src/api/routes/system.py:116](../../src/api/routes/system.py#L116) declares
  `_orchestrator: Any | None = None` and offers `set_orchestrator()` at line 157.
- [src/api/main.py:308](../../src/api/main.py#L308) calls
  `init_system_routes(store=store, event_bus=event_bus)` — **without the `orchestrator`
  argument**. `set_orchestrator()` is never called anywhere in `src/` or `scripts/`.
  `_orchestrator` is therefore permanently `None` in production.
- mypy confirms it has rotted: [src/core/orchestrator.py:464-469](../../src/core/orchestrator.py#L464-L469)
  calls `StrategyEngine.create_strategy()` with keyword arguments `template`, `symbol`,
  `account_id`, `status` that **do not exist on that method**, and reads `Strategy.template`,
  `.symbol`, `.account_id`, `.params` — none of which are attributes of the model. This code
  would raise `TypeError` on the first call. It is untestable in that path and it is not
  tested in that path.

Meanwhile the real production entry point,
[scripts/run_live_trading.py](../../scripts/run_live_trading.py) at **2,111 lines**, imports
none of the core orchestration, risk, or execution machinery:

```
from src.brokers.binance.client        import BinanceClient
from src.brokers.binance.execution     import BinanceExecutionAdapter
from src.brokers.binance.rate_limiter  import RateLimiter
from src.core.alerting.channels.telegram import TelegramChannel
from src.core.alerting.manager         import Alert, AlertLevel
from src.core.strategy.backtest.types  import BacktestConfig
from src.core.strategy.factory         import SignalGeneratorFactory
from src.core.risk.types               import OrderRequest
from src.core.strategy.regime.*        import RegimeDetector, SubRegime, SubRegimeDetector
from src.data.*                        import init_db, OHLCV, MarketDataFetcher, DataStore
from src.utils.logging                 import get_logger
```

Absent: `RiskController`, `OrderManager`, `PositionTracker`, `Orchestrator`,
`core.monitoring`. The script reimplements the risk pipeline inline — its own comment at
[scripts/run_live_trading.py:968](../../scripts/run_live_trading.py#L968) says
*"Kill switch — always checked first, consistent with risk controller pipeline"*, which is an
admission that a second, parallel implementation exists.

**Why this matters more than any lint count:** your 71% coverage figure largely measures code
that does not run. A staff engineer who traces one order from signal to fill will find that
the heavily tested `src/core/risk/controller.py` (739 lines) and
`src/core/execution/order_manager.py` (843 lines) are bypassed by the script that trades real
money. That is the finding that makes someone doubt the author understands their own system —
and it is exactly the impression you asked me to locate.

### 3.2 A module Python cannot import

Both `src/core/strategy/regime.py` (5,906 bytes) **and** the package
`src/core/strategy/regime/` exist. The package always wins:

```
>>> import src.core.strategy.regime as r; print(r.__file__)
D:\Eva\Projects\Paravant_System\src\core\strategy\regime\__init__.py
```

`regime.py` is unreachable by any import statement. Coverage confirms it: **0%, 62/62
statements missed**. Its docstring is byte-identical to
[src/core/strategy/regime/manual.py](../../src/core/strategy/regime/manual.py) — it is the
pre-rebuild original, superseded and never deleted. A textbook March-2026 leftover.

### 3.3 Empty and orphaned packages

- [src/domain/__init__.py](../../src/domain/__init__.py) — **1 byte**. The `src/domain/`
  package contains nothing else. A domain layer that was planned and never built.
- [src/core/account/__init__.py](../../src/core/account/__init__.py) — 34 bytes, no other
  files.
- `src/core/monitoring/` — imported only by `src/core/orchestrator.py`, i.e. only by dead
  code. Dead by transitivity.
- [src/core/event_bus.py](../../src/core/event_bus.py) — 75 statements, **0% coverage**. It
  is wired into `src/api/main.py` for SSE, so it is not dead, but the "in-process EventBus"
  called out as a core architectural decision (`DEC-2026-01-15-005`) has no tests at all.

### 3.4 Config/code drift

14 template YAMLs in `config/templates/` back 29 generators in
`src/core/strategy/generators/`. **15 generators have no template file:**
`adx_directional_thrust`, `bull_trend_pullback`, `crypto_wick_reversal`,
`ema_ribbon_expansion`, `heikin_ashi_trend_pulse`, `keltner_channel_continuation`,
`multi_tf_confluence`, `obv_trend_divergence`, `realized_vol_compression_breakout`,
`roc_momentum_surge`, `rsi_divergence_reversal`, `stoch_rsi_bull_cross`,
`trend_acceleration_momentum`, `volume_balance_breakout`, `vpt_momentum`.

They are all registered in `_DEFAULT_GENERATORS`
([src/core/strategy/factory.py:49](../../src/core/strategy/factory.py#L49)) and exported in
`__all__` (29 entries), so they are reachable in code — but a YAML-driven configuration model
that only covers half the generators is a split-brain design, and the registry docstring
([src/core/strategy/generators/__init__.py](../../src/core/strategy/generators/__init__.py))
still advertises "Original (7) + Bear (6) + Bull (11)" = **24**, omitting the five
crypto-native generators added later. Four different counts of the same thing (6 / 7 / 14 /
24 / 29) appear across README, tests, docstring, config, and code.

### 3.5 God modules

| File | Lines |
| --- | --- |
| [scripts/run_live_trading.py](../../scripts/run_live_trading.py) | **2,111** |
| [src/core/orchestrator.py](../../src/core/orchestrator.py) | 1,800 (dead) |
| [src/data/store.py](../../src/data/store.py) | 1,332 |
| [scripts/retrospective_dsr.py](../../scripts/retrospective_dsr.py) | 1,207 |
| [scripts/regime_dsr.py](../../scripts/regime_dsr.py) | 1,050 |
| [scripts/run_paper_trading.py](../../scripts/run_paper_trading.py) | 947 |

A 2,111-line script holding the live-trading loop, tier activation, capital allocation,
promotion gating, degradation checks, regime matching, and order submission is the file a
reviewer will open to judge you, because it is the one that trades. It should be a package.

**No circular imports were found.** The one-way `src/` → never-imports-`research/` rule stated
in [requirements-research.txt](../../requirements-research.txt) holds in practice.

---

## 4. Incompleteness

### 4.1 TODO / FIXME / HACK / XXX — complete list (4 total)

| Marker | Location |
| --- | --- |
| TODO | [frontend/src/components/layout/Header.tsx:152](../../frontend/src/components/layout/Header.tsx#L152) — `open shortcuts modal` |
| TODO | [frontend/src/components/layout/Header.tsx:227](../../frontend/src/components/layout/Header.tsx#L227) — `open emergency panel` |
| TODO | [tests/integration/test_api_endpoints.py:94](../../tests/integration/test_api_endpoints.py#L94) — `Add test endpoint for exception testing` |

Zero `FIXME`, zero `HACK`, zero `XXX` across `src/`, `scripts/`, `research/`, `tests/`, and
`frontend/src/`. **This is genuinely excellent and unusual.** Say so on the record.

### 4.2 Stubs

- `raise NotImplementedError` outside abstract methods in `src/`: **0**.
- 14 bare `pass` bodies in `src/`, all of which are exception-handling or protocol stubs on
  inspection; one is a swallowed exception (see 5.4).

### 4.3 Features documented with no implementation behind them

- **`research/optimization/bayesian.py`** — specified twice in
  [docs/research/RESEARCH_LAYER_PRD.md:285](../research/RESEARCH_LAYER_PRD.md#L285) and
  [:473](../research/RESEARCH_LAYER_PRD.md#L473) as "Optuna-backed Bayesian optimization".
  **The file does not exist.** There is no `research/optimization/` directory at all.
- **VectorBT backtesting** — [docs/ARCHITECTURE.md:666](../ARCHITECTURE.md#L666) lists it as
  the backtesting layer. Not installed, not imported, not used. The real backtester is
  hand-written at [src/core/strategy/backtest/engine.py](../../src/core/strategy/backtest/engine.py).
- **CCXT multi-exchange** — [docs/ARCHITECTURE.md:667](../ARCHITECTURE.md#L667) lists
  "CCXT, python-binance — Multi-exchange support". CCXT: zero imports. Also directly
  contradicts locked decision `DEC-2026-01-15-002` (Binance only).
- **Orchestrator-backed system status** — `src/api/routes/system.py` has a whole enrichment
  branch (`if _orchestrator is not None:` at line 223) that can never execute.

### 4.4 Config keys nothing reads

Declared dependencies with **zero imports anywhere** in `src/`, `scripts/`, or `research/`:

| Package | Declared in | Imports found |
| --- | --- | --- |
| `httpx>=0.26.0` | requirements.txt, pyproject.toml | 0 |
| `tenacity>=8.2.0` | requirements.txt, pyproject.toml | 0 |
| `aiosqlite>=0.19.0` | requirements.txt, pyproject.toml | 0 |
| `psycopg2-binary>=2.9.0` | requirements.txt | 0 |
| `python-telegram-bot>=20.7` | pyproject.toml:40 only | 0 |
| `optuna>=3.4` | requirements-research.txt | 0 |
| `arch>=6.2`, `jupyter`, `seaborn`, `plotly` | requirements-research.txt | 0 |

`tenacity` is the notable one: it is declared, and there is no retry decorator anywhere, which
connects to the missing-retry finding in 5.4.

---

## 5. Engineering maturity signals

### 5.1 Tests — the number is good, the run is not

| Metric | Value |
| --- | --- |
| Test files | 116 |
| Test functions | **1,884** |
| Test LOC | 36,022 |
| Coverage (full suite, `--cov=src`) | **71%** (14,082 statements, 4,030 missed) |
| Coverage (unit + research only) | 60% |
| Result of bare `pytest` | **9 failed, 1,855 passed, 4 skipped, 32 errors** in 172 s |

A 1,884-test suite at 71% is a real asset. It is undermined by the fact that the documented
command produces red output.

**The 32 errors are all live network calls.** Every one is an
`SSLCertVerificationError` / `MaxRetryError` against `https://testnet.binance.vision/api/v3/ping`,
raised from [tests/integration/test_binance_client.py](../../tests/integration/test_binance_client.py)
and [tests/integration/test_symbol_refresh.py](../../tests/integration/test_symbol_refresh.py).
`pyproject.toml` defines a `binance` marker but `addopts` does not deselect it, so the default
invocation hits the internet. On a reviewer's laptop behind a corporate proxy, or on a plane,
this is 32 errors and a closed tab.

**The 9 failures split into two classes:**

*Environment contamination (3).* [src/core/config/settings.py:52](../../src/core/config/settings.py#L52)
sets `env_file=".env"` with no test isolation, so `tests/unit/core/config/test_config.py::TestSettingsSchema::test_settings_defaults`
asserts `binance_testnet is True` and reads your real `.env`, which sets it False. There is a
`tests/conftest.py` but it does not neutralise settings. These would pass on a clean clone —
which means **you have been running a red suite locally and not investigating.**

*Genuine stale assertions (6).* These fail everywhere:
- `TestTemplates::test_template_manager_loads_all_templates` — `assert 14 == 7`
- `TestConfigLoader::test_config_loader_loads_all_sources` — `assert 14 == 7`
- `TestRsiBbMeanReversion::test_properties` — `assert 210 == 50` (`min_bars_required`)
- `TestRsiBbMeanReversion::test_missing_parameter_raises` — `DID NOT RAISE SignalGenerationError`
- `TestDonchianAtr::test_missing_parameter_raises` — `DID NOT RAISE SignalGenerationError`
- `tests/research/test_liquidations.py::test_collector_flush_writes_and_clears`

Templates were added from 7 to 14 and the assertions were never updated. Two generators
stopped validating their required parameters and the tests that caught it were left failing.
**That last pair is a real behavioural regression sitting in the open**, not just a stale
number.

### 5.2 What is critical and untested

| Module | Coverage | Why it matters |
| --- | --- | --- |
| [src/brokers/binance/client.py](../../src/brokers/binance/client.py) | **13%** | The network boundary to a live exchange |
| [src/core/event_bus.py](../../src/core/event_bus.py) | **0%** | Named as a core architectural decision |
| [src/api/main.py](../../src/api/main.py) | 0% (unit) | The documented entry point |
| `src/api/routes/{accounts,backtest,dashboard,events,paper_trading,pnl,regime,strategies,system}.py` | 0% (unit) | 9 of 14 route modules |
| [src/core/alerting/channels/telegram.py](../../src/core/alerting/channels/telegram.py) | 22% | The only operator-notification path |
| [scripts/run_live_trading.py](../../scripts/run_live_trading.py) | not measured | 2,111 lines that place real orders; only `_can_activate_tier` and the promotion gate are covered, via `tests/unit/scripts/` |

The inversion is stark: 71% coverage on a dead orchestrator, 13% on the live broker client.

### 5.3 Types and lint — both configured, neither passing

**mypy** (`disallow_untyped_defs = true`, `warn_return_any = true` in pyproject.toml —
a strict config, which is to your credit):
> **50 errors in 16 files (checked 169 source files)**

Real bugs among them, not just annotation noise:
- [src/core/orchestrator.py:464-469](../../src/core/orchestrator.py#L464-L469) — calls a
  method with four nonexistent keyword args and reads four nonexistent attributes (see 3.1).
- [src/core/strategy/paper/engine.py:664](../../src/core/strategy/paper/engine.py#L664) —
  `"OHLCVSeries" has no attribute "__iter__" (not iterable)`. That is an iteration over a
  non-iterable in the paper-trading engine.
- [src/core/strategy/generators/rsi_divergence_reversal.py:184,224](../../src/core/strategy/generators/rsi_divergence_reversal.py#L184) —
  assigning `str` into a `float` target.
- ~20 `dict[str, object]` vs `dict[str, float]` mismatches on `TradingSignal.indicators`
  across seven generators — a genuine type-model disagreement, since generators want to pass
  strings and the signal type forbids it.

**ruff** — **290 errors** on the exact command the README publishes:

| Scope | Errors |
| --- | --- |
| `src/` | 37 |
| `tests/` | 214 |
| `scripts/` + `research/` | 39 |

By code: `F401` unused import ×176, `F841` unused variable ×29, `F821` **undefined name** ×27,
`E712` `== True` comparison ×19, `F541` f-string without placeholders ×16, `E402` ×14,
`F811` redefinition ×3. 194 are auto-fixable with `ruff check --fix`.

All 27 `F821` are in [tests/unit/test_risk_controller.py](../../tests/unit/test_risk_controller.py)
— `Any` and `RiskController` used in annotations but never imported. It runs only because the
file has `from __future__ import annotations`, so the names are never evaluated. Harmless at
runtime, but it means ~500 lines of that file's type annotations are decorative.

**There is no `black --check`, no `ruff`, no `mypy` gate anywhere.** README section
"Code Quality" tells a reader to run three commands, all three of which fail.

### 5.4 Error handling

**Zero bare `except:` clauses** across `src/`, `scripts/`, and `research/`. That is a real
discipline signal and worth stating plainly.

Weaknesses:
- One swallowed exception: [src/core/strategy/paper/engine.py:469](../../src/core/strategy/paper/engine.py#L469)
  (`except Exception: … pass`).
- **No retry logic around broker or network calls.** `tenacity` is a declared dependency with
  zero imports; there is no `@retry`, no backoff decorator, no reconnection wrapper in
  [src/brokers/binance/client.py](../../src/brokers/binance/client.py). For a system whose own
  MVP rules mandate "retry logic with exponential backoff" for Binance failures
  (`.claude/rules/mvp-scope-control.md`, accepted-request example), this is a documented
  requirement with no implementation. There **is** a rate limiter
  ([src/brokers/binance/rate_limiter.py](../../src/brokers/binance/rate_limiter.py), 81%
  covered) and a genuinely thoughtful geo-block fail-fast path
  ([src/utils/geo_block.py](../../src/utils/geo_block.py), 100% covered) — so the gap is
  specifically retries, not resilience in general.

### 5.5 Logging

`structlog` throughout, via [src/utils/logging.py](../../src/utils/logging.py) (86% covered).
Only 10 `print()` calls in all of `src/`, concentrated in
[src/core/config/symbols.py](../../src/core/config/symbols.py) (4) and
[src/data/store.py](../../src/data/store.py) (3). The `print()` usage in
[scripts/run_all.py](../../scripts/run_all.py) is correct — it is a supervisor writing to
Railway's stdout. **Good.**

### 5.6 Dependencies and reproducibility

- **Three requirements files that disagree with each other and with `pyproject.toml`.**
  `pyproject.toml` declares `python-telegram-bot`; `requirements.txt` does not.
  `requirements.txt` declares `psutil`, `psycopg2-binary`, `aiohttp`; `pyproject.toml` does
  not. A reader cannot tell which is authoritative.
- **No lockfile for Python.** Everything is `>=`, nothing is pinned. `pip install -r
  requirements.txt` in six months resolves differently. No `uv.lock`, no `poetry.lock`, no
  `requirements.lock`.
- **`requests` used but undeclared** (Section 2).
- Frontend is better: [frontend/package-lock.json](../../frontend/package-lock.json) exists
  and is committed. `node_modules/` and `dist/` correctly untracked.

### 5.7 CI

**None.** No `.github/`, no `.gitlab-ci.yml`, no `.circleci`, nothing. For a repo being
presented as a work sample, the absence of a green badge is the loudest possible statement
that the tests are not trusted — especially given they are currently red.

### 5.8 Docker

[Dockerfile](../../Dockerfile) is competent: `python:3.11-slim`, a non-root `appuser`,
`PYTHONDONTWRITEBYTECODE`, `--no-cache-dir`, explicit `mkdir` + `chown` for data/logs volumes.
`COPY . .` after dependency install is the right layer order.

Two gaps: it copies the entire repo including the 25 MB of design PDFs (`.dockerignore` exists
but does not exclude `docs/`), and `docker-compose.yml` at the root is referenced by the README
but the actual deployment is Railway via [railway.toml](../../railway.toml) — two deployment
stories, one documented, the other real.

### 5.9 Migrations

Linear and coherent. Six files in [alembic/versions/](../../alembic/versions/), date-prefixed,
one initial schema plus five focused additive migrations. No branching, no merge revisions, no
orphans. **Clean — no action needed.**

---

## 6. Architecture legibility

### 6.1 Is the design visible from the layout?

The package layout is genuinely readable: `src/{api,brokers,core,data,domain,utils}` with
`core/{alerting,config,execution,indicators,risk,strategy}` is a layout a reviewer can
navigate without help. Indicator and generator modules are one-concept-per-file with
consistent naming. **This is the strongest structural thing in the repo.**

What is *not* visible is the thing you describe as the headline: there is no agent layer to
see, because there is no agent layer (Section 7).

### 6.2 Is the async lifecycle traceable from a single entry point?

No — and the trail actively misleads.

- `README.md` points to `uvicorn src.api.main:app`. That starts a read-only dashboard API.
- `railway.toml` `startCommand` is `python -m scripts.run_all`. That is the real system.
- `scripts/run_all.py` is a **synchronous subprocess supervisor** — it spawns
  `scripts.run_paper_trading` and (behind `LIVE_TRADING_ENABLED`) `scripts.run_live_trading`
  as separate OS processes, each with its own event loop.
- `Procfile` describes a third topology: `paper:` + `web:` as two Railway services.

So "the async lifecycle" is: two independent asyncio processes under a blocking supervisor,
plus an unrelated FastAPI app, described three different ways in three files, and documented
in none of them. The pipeline you describe as *signal generation → confirmation → backtest and
optimization → paper trading → monitoring* does exist — it is spread across
`src/core/strategy/factory.py` → `generators/` → `src/core/strategy/backtest/engine.py` →
`src/core/strategy/paper/engine.py` → `scripts/validation_report.py` → the promotion gate in
`scripts/run_live_trading.py` — but **nothing in the repo draws that line.** You have to
reconstruct it by reading 2,111 lines.

### 6.3 Where specifically a new engineer gets lost

1. **Minute 2.** Root directory. Which of the 17 loose scripts is real? None. Nothing says so.
2. **Minute 5.** They open `src/core/orchestrator.py` because it is called *orchestrator*,
   read 1,800 lines, and only later discover it is never instantiated.
3. **Minute 8.** They look for the risk checks in a live order and find that
   `src/core/risk/controller.py` is not in the live path; the checks are reimplemented inline
   at `scripts/run_live_trading.py:968`.
4. **Minute 12.** They try to reconcile `regime.py` with `regime/` and cannot import the
   former.
5. **Throughout.** They cannot find the agents, vectorbt, or Optuna, because none exist.

Items 2, 3, and 5 are where "the author does not fully understand their own system" forms.
Item 3 is the one that would end the review for a trading role specifically.

---

## 7. Claim verification

**Read this section before updating your CV.** Every claim below was checked three ways:
import statements, plain-text mentions across all tracked files, and installed packages in
`.venv`.

### 7.1 vectorbt — NOT PRESENT

- Imports in any `.py` file: **0**
- Present in `requirements.txt` / `requirements-dev.txt` / `requirements-research.txt` /
  `pyproject.toml`: **no**
- Installed in `.venv/Lib/site-packages`: **no**
- Only appearances anywhere: [docs/ARCHITECTURE.md:666](../ARCHITECTURE.md#L666) (stack table)
  and [:691](../ARCHITECTURE.md#L691) (aspirational version pin) — a document last modified on
  the initial commit.

**The backtester is entirely your own**: [src/core/strategy/backtest/](../../src/core/strategy/backtest/)
— `engine.py`, `metrics.py`, `portfolio.py`, `result.py`, `trader.py`, `types.py`,
`validator.py`, driven by pandas/numpy. That is a *stronger* claim than "used vectorbt", and it
is true. Rewrite the CV line accordingly.

### 7.2 backtrader — NOT PRESENT

- Imports: **0**. Mentions anywhere in the repo, including docs: **0**. It did not survive the
  rebuild because it appears never to have been here.

### 7.3 Optuna — DECLARED, NEVER USED

- Imports: **0**
- Declared at [requirements-research.txt:22](../../requirements-research.txt#L22) with the
  comment "Bayesian parameter optimization (Phase R3)" — i.e. explicitly future work
- Installed in `.venv`: **no**
- [docs/research/RESEARCH_LAYER_PRD.md:285](../research/RESEARCH_LAYER_PRD.md#L285) and
  [:473](../research/RESEARCH_LAYER_PRD.md#L473) describe `research/optimization/bayesian.py`
  as "Optuna-backed". **That file and that directory do not exist.**

What you actually do for optimization is grid/parameter sweeps in
[scripts/sweep_tp_wfo.py](../../scripts/sweep_tp_wfo.py) (797 lines),
[scripts/sweep_bull_params.py](../../scripts/sweep_bull_params.py),
[scripts/sweep_stop_multiplier.py](../../scripts/sweep_stop_multiplier.py), plus walk-forward
and Deflated-Sharpe screening. **Claim walk-forward optimization and DSR-based multiple-testing
correction. Do not claim Optuna.**

### 7.4 CCXT — NOT PRESENT

Zero imports. Claimed at [docs/ARCHITECTURE.md:667](../ARCHITECTURE.md#L667). Also contradicts
locked decision `DEC-2026-01-15-002`.

### 7.5 "21 specialized agents" — NOT SUPPORTED BY THE CODE

This is the finding most likely to damage you, so here is the full evidence:

- The literal string `21` as a count of agents/strategies/generators/templates appears
  **nowhere** in the repository.
- There is **no** `Agent` class, no `AGENT_REGISTRY`, no `agents` module, no agent base class,
  no agent lifecycle. `git grep -E "AGENT_REGISTRY|class .*Agent\b|AGENTS\s*="` over the entire
  repo returns exactly one hit, and it is a mock (below).
- No file in `src/`, `scripts/`, or `research/` has "agent" in its name.
- Only three `.py` files contain the substring "agent" at all, and all three are references to
  the `.agent/DECISIONS.md` file path in
  [scripts/retrospective_dsr.py](../../scripts/retrospective_dsr.py).
- `.claude/agents/` is an **empty directory**.
- The single registry-shaped hit is
  [docs/design/references/components/pages/NotificationsPage.tsx:49](../design/references/components/pages/NotificationsPage.tsx#L49):
  ```js
  const agents = ['Alpha Seeker', 'Momentum Prime', 'Macro Sentinel', 'Arb Hunter'];
  ```
  Four hardcoded strings in a UI mock.

**What "agent" actually means in this repo** is a UI synonym for *strategy*:
`Header.tsx:19` maps `'Agents': '/strategies'`, and `StrategyCard.tsx` uses aria-labels
"Pause Agent" / "Resume Agent". The nearest true countable thing is **29 signal generators**
in `src/core/strategy/generators/` plus **7** in `research/generators/`.

**If a reviewer greps for "agent" — and for a claim that specific, they will — they find four
fake names in a React mock.** This is the highest-severity item in the audit. Either build an
agent abstraction or change the claim to what is true and still impressive: *29 pluggable
signal-generation strategies behind a common `SignalGenerator` ABC, routed at runtime by a
regime-aware dispatcher.*

### 7.6 Libraries this code actually uses today

Derived from every `import` / `from` statement in `src/`, `scripts/`, `research/`, filtered
against `sys.stdlib_module_names`:

**Runtime:** `fastapi`, `starlette`, `pydantic`, `pydantic_settings`, `sqlalchemy`, `alembic`
(CLI only), `pandas`, `numpy`, `python-binance` (`binance`), `requests`, `aiohttp`,
`structlog`, `psutil`, `pyyaml` (`yaml`), `python-dotenv` (`dotenv`).

**Dev/test:** `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `black`, `ruff`, `mypy`.

**Frontend:** React, Vite, TypeScript, Tailwind v3, framer-motion.

That is the honest stack. It is a perfectly respectable one.

### 7.7 Hard counts you can quote

| Metric | Value | How measured |
| --- | --- | --- |
| Tracked files | 769 | `git ls-files \| wc -l` |
| Python files (tracked) | 378 | by extension |
| **Python LOC — `src/`** | **49,291** | `git ls-files 'src/**/*.py' \| xargs wc -l` |
| Python LOC — `tests/` | 36,022 | same |
| Python LOC — `scripts/` | 11,865 | same |
| Python LOC — `research/` | 5,401 | same |
| Python LOC — loose root scripts | 3,895 | same (deletion candidates) |
| **Meaningful Python LOC (src + scripts + research)** | **66,557** | sum |
| Frontend LOC (`.ts`/`.tsx`/`.css`) | 16,825 | `git ls-files 'frontend/src/**'` |
| Test files | 116 | files matching `test_*` |
| **Test functions** | **1,884** | `grep -c "def test_"` |
| **Line coverage of `src/`** | **71%** | `pytest --cov=src`, 14,082 stmts / 4,030 missed |
| Signal generators (`src/`) | 29 | file count, `__all__` = 29 |
| Signal generators (`research/`) | 7 | file count |
| Strategy template YAMLs | 14 | `config/templates/*.yaml` |
| Indicator modules | 19 | `src/core/indicators/*.py` |
| API route modules | 14 | `src/api/routes/*.py` |
| SQLAlchemy models | 13 | `src/data/models/*.py` |
| Alembic migrations | 6 | `alembic/versions/` |
| Agents | **0** | see 7.5 |
| Git commits | 102 | 2026-02-08 → 2026-06-11 |
| Uncommitted changes | 71 files | `git status --porcelain` |
| mypy errors | 50 in 16 files | `mypy src/` |
| ruff errors | 290 | `ruff check src/ tests/ scripts/ research/` |
| TODO/FIXME/HACK/XXX | 4 | full-tree grep |

**Safe CV phrasing:** *"~66k lines of production Python, 1,884 tests at 71% line coverage,
29 pluggable strategy generators, deployed to Railway with a fail-closed live-trading kill
switch."* Every number in that sentence is verifiable from this repo.

---

## 8. Documentation audit

### 8.1 What exists

| Doc | Lines / count | State |
| --- | --- | --- |
| [README.md](../../README.md) | 157 | **Last commit 2026-02-08 "Initial commit"** |
| [docs/ARCHITECTURE.md](../ARCHITECTURE.md) | 1,656 | **Last commit 2026-02-08 "Initial commit"** |
| [docs/TRADING_SYSTEM_PRD.md](../TRADING_SYSTEM_PRD.md) | 242 KB | Modified, uncommitted |
| `docs/0X_PHASE_*.md` | 9 files | Historical build plans |
| [docs/API_CONTRACT.md](../API_CONTRACT.md), [docs/INDICATOR_SPECIFICATION.md](../INDICATOR_SPECIFICATION.md), [docs/DATABASE_SEED_DATA.md](../DATABASE_SEED_DATA.md), [docs/ENVIRONMENT_SETUP.md](../ENVIRONMENT_SETUP.md) | 4 | Exist; all README links resolve |
| `docs/research/` | 11 `.md` + 32 others | **Current and genuinely good** |
| `docs/operations/RAILWAY_CRONS.md` | 2 files | Current |
| `.claude/DECISIONS.md` / `.agent/DECISIONS.md` | 267 KB each, in sync | **Current and exceptional** |
| `docs/validation/` | **0 files** | Empty tracked directory |
| Root `SESSION_*` / `PHASE_*` | 35 files, 1.05 MB | Build scaffolding; not documentation |

### 8.2 Documentation that describes behaviour the code no longer has

This is the list to act on:

| Claim | Location | Reality |
| --- | --- | --- |
| "Strategy Library: 6 pre-built templates" | [README.md:11](../../README.md#L11) | 14 YAMLs, 29 generators |
| "Backtesting \| VectorBT" | [ARCHITECTURE.md:666](../ARCHITECTURE.md#L666) | Hand-written engine |
| `vectorbt>=0.25.0` | [ARCHITECTURE.md:691](../ARCHITECTURE.md#L691) | Not a dependency |
| "Broker SDK \| CCXT, python-binance — Multi-exchange support" | [ARCHITECTURE.md:667](../ARCHITECTURE.md#L667) | Binance only; CCXT absent; contradicts `DEC-2026-01-15-002` |
| `research/optimization/bayesian.py` — "Optuna-backed" | [RESEARCH_LAYER_PRD.md:285,473](../research/RESEARCH_LAYER_PRD.md#L285) | File and directory do not exist |
| "Run the system: `uvicorn src.api.main:app`" | [README.md:57](../../README.md#L57) | Real entry point is `python -m scripts.run_all` |
| "Lint: `ruff check src/ tests/`" | [README.md:102](../../README.md#L102) | 251 errors in that scope |
| "Type check: `mypy src/`" | [README.md:105](../../README.md#L105) | 50 errors |
| "Run tests: `pytest`" | [README.md:86](../../README.md#L86) | 9 failed, 32 errors |
| MVP scope: "❌ Advanced backtesting (walk-forward, Monte Carlo)" | [README.md:132](../../README.md#L132) | Walk-forward **is** implemented (`scripts/sweep_tp_wfo.py`), as is DSR. README undersells you. |

`ARCHITECTURE.md` contains **no mention** of `run_live_trading`, `run_paper_trading`,
`run_all`, the regime router, the sub-regime detector, the promotion gate, or the research
layer — i.e. none of the last four months.

### 8.3 What is missing

| Needed | Status |
| --- | --- |
| Architecture doc reflecting the current system | **Missing** (the existing one is stale) |
| Architecture **diagram** | **Missing entirely** — no diagram anywhere |
| Data-flow trace: signal → confirmation → backtest → paper → promotion → live | **Missing** — reconstructible only by reading source |
| Quickstart that starts the actual trading system | **Missing** |
| Configuration reference (env vars: `LIVE_TRADING_ENABLED`, `LIVE_CAPITAL_USDT`, `PER_STRATEGY_ALLOCATION_PCT`, `MAX_STRATEGIES_LIVE_CONCURRENT`, `CAPITAL_RESERVE_FRACTION`, `POSITION_SIZE_FRACTION`) | **Missing** — these live only in `DECISIONS.md` prose and inline code |
| Strategy/generator catalogue | **Missing** — closest is the stale 24-entry docstring in `generators/__init__.py` |
| Design decisions and tradeoffs | **Present and outstanding** — `DECISIONS.md` is the best artifact in the repo, and no reader will ever find it |
| Known limitations | **Missing** |
| **Risk disclaimer** | **Missing.** [README.md:139-146](../../README.md#L139) has operational safety tips but no "this software can lose real money; no warranty; not financial advice" notice. For a public repo that places live Binance orders, this is a genuine legal gap, not a formality. |
| License text | **`LICENSE` file absent** — README:150 says "MIT" with no file. GitHub will show no license. |

### 8.4 One line of praise, as requested

`docs/research/` and `.claude/DECISIONS.md` are the best things in this repository. The
retrospective-DSR methodology, the pre-registered hypothesis ledger, the honest
`REJECTED (FUNDAMENTAL)` verdicts on your own strategies, and the strategy post-mortems
demonstrate research integrity that most quant candidates cannot show. **They are buried three
directories deep and referenced from nothing.** Surfacing them is the highest-leverage
documentation work available to you.

---

## 9. What is genuinely good — for the record

- **Zero bare `except:`** across 66k lines. Rare.
- **Four TODOs total.** Rarer.
- **102 commits of disciplined conventional-commit history** with decision IDs in the
  subjects — `feat(live): auto-promotion gate -- require READY_FOR_LIVE before tier activation`.
  A reviewer who runs `git log --oneline` sees a professional.
- **[scripts/run_all.py](../../scripts/run_all.py)** — 147 lines, fail-closed live-trading
  switch, geo-block non-restart contract, bounded restarts, signal forwarding, every decision
  cited inline. Show this file.
- **[research/validation/deflated_sharpe.py](../../research/validation/deflated_sharpe.py)** —
  100% coverage, deliberately stdlib-only so the instrument gating real capital carries no
  dependency drift. The reasoning is documented in `requirements-research.txt`. This is senior
  judgement, plainly displayed.
- **`src/core/execution/quality.py`** (256 stmts, **99%**), `position_tracker.py` (93%),
  `src/core/indicators/` (mostly 90%+), `research/` (mostly 87–100%).
- **Alembic migrations**: linear, additive, no branches.
- **Dockerfile**: non-root user, correct layer ordering.
- **`.gitignore`**: comprehensive and commented, including deliberate research-artifact rules.
- **`DECISIONS.md` dual-file sync**: verified identical via `diff`. The process you defined,
  you followed.

---

## 10. Where the "AI-assisted, author doesn't understand it" impression forms

Ranked by how fast a skeptical reviewer hits it:

1. **Root directory, ~10 seconds.** 35 `SESSION_*_IMPLEMENTATION_PROMPT.md` files. This is
   literally the prompt log. Nothing else in the audit matters if they stop here.
2. **`create_strategy_variations.py` vs `create_strategy_variations_correct.py`, ~30 seconds.**
   Two files, one named "correct". The reviewer infers the first was broken and never removed.
3. **`pytest`, ~3 minutes.** 32 network errors and 6 stale assertions including `assert 14 == 7`.
   The inference: tests were generated, passed once, and were never re-read.
4. **`src/core/orchestrator.py`, ~5 minutes.** 1,800 lines, 71% covered, calls methods that
   do not exist, never instantiated. The inference: code was produced, tested against itself,
   and never integrated.
5. **`scripts/run_live_trading.py:968`, ~10 minutes.** The live path reimplements the risk
   pipeline instead of importing the tested `RiskController`. For a trading role this is the
   fatal one — it says the author does not know which of their own two risk implementations
   is authoritative.
6. **Grepping for "agent", any time.** Four hardcoded names in a React mock.
7. **`EmergencyPanel.tsx:21-26`.** Hardcoded fake positions in **NVDA, TSLA, AMD, SPY** with
   fabricated P&L up to $22,522.50 — equities, in a repo whose locked decision
   `DEC-2026-01-15-001` is crypto-only. Twelve frontend files use `Math.random()` to simulate
   data. If a reviewer opens the UI code expecting a dashboard over your real system, they
   find a mockup. Label it as a prototype or wire it up; do not leave it ambiguous.

---

## 11. Summary table

| Dimension | Grade | One-line justification |
| --- | --- | --- |
| Secrets / publication safety | **A** | Nothing leaked, working tree or history. No action required. |
| First impression | **D** | 35 prompt files and 17 loose scripts at root; stale README. |
| Structural coherence | **D+** | Dead 1,800-line orchestrator, unimportable `regime.py`, live path bypasses the tested core. |
| Incompleteness | **B+** | 4 TODOs, 0 stubs; but documented modules that do not exist. |
| Engineering maturity | **C+** | 1,884 tests and 71% coverage, undercut by a red suite, 290 lint errors, 50 mypy errors, no CI, no lockfile. |
| Architecture legibility | **C-** | Good package layout; untraceable lifecycle, three conflicting entry points, no diagram. |
| Claim accuracy | **F** | Agents, vectorbt, backtrader, Optuna, CCXT: none present. |
| Documentation | **D** | README and ARCHITECTURE frozen at the initial commit; no license file, no risk disclaimer, no diagram. Research docs are an A on their own. |

See [ROADMAP.md](ROADMAP.md) for the prioritized plan.
