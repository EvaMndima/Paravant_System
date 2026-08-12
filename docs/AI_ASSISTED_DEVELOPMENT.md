# Building PARAVANT with AI Assistance

**Written:** 2026-08-11
**Covers:** 2026-02-08 to 2026-08-13, 131 commits, one human author

PARAVANT is roughly 120,000 lines written over six months by one person working
with AI coding assistants. The most transferable thing it produced is not the
trading system. It is a fairly precise picture of where that way of working
holds up, where it breaks, and what has to be built to catch the breaks.

Sections 3 and 4 are the ones worth your time. Section 3 is what worked.
Section 4 is eight failure modes, each with the mechanism that produced it, how
long it survived, and what now prevents it.

The repository previously contained 35 `SESSION_*_IMPLEMENTATION_PROMPT.md`
files at its root -- the raw prompts. They were replaced by this document, and
remain in git history at tag `pre-cleanup`.

---

## 1. What was built

| Layer | Files | Lines |
|---|---|---|
| `src/` application | 167 `.py` | 49,184 |
| `tests/` | 134 `.py` | 36,876 |
| `frontend/src/` | 90 `.ts`/`.tsx` | 17,187 |
| `scripts/` operational entrypoints | 25 | 11,900 |
| `research/` validation library | 32 `.py` | 6,461 |

*As of 2026-08-13; `python scripts/doc_stats.py` regenerates this table.*

A crypto trading system: Binance data ingestion, 19 indicators, 29 signal
generators, a layered risk system, an order state machine, backtest and paper
engines sharing the live code path, a FastAPI surface of 63 endpoints, a React
dashboard, and a statistical research layer whose purpose is to reject the
system's own strategies.

It found no trading edge. Eight subjects were rejected under Deflated Sharpe at
a sample size where the verdict carries information; ten more were initially
reported as rejected until the system's own guard established they had never had
enough data to reject at all. That correction is itself the most instructive
result, and is written up in [RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md).

---

## 2. The working method

Work proceeded in numbered sessions. Each session had a written prompt stating
scope, the decisions it had to honour, and its acceptance criteria; the
assistant implemented against that prompt; a separate verification pass checked
the result against the criteria. The prompts were versioned in the repository
while the work was live.

Three things sat underneath every session and did most of the real work:

**`.claude/DECISIONS.md`** -- 122 dated decision entries across 3,169 lines,
each recording the decision, its context, its rationale, the alternatives
considered and rejected, and its status. Maintained identically in `.agent/` so
that different assistants could not diverge on what had been decided.

**`.claude/rules/`** -- three enforcement files:

- `decision-consistency.md` requires reading the decision log *before*
  implementing, and requires refusing work that contradicts an active decision.
- `zero-technical-debt.md` covers backward compatibility, naming stability,
  behaviour-preserving refactors, one-intent-per-change, and rollback readiness.
- `mvp-scope-control.md` lists locked scope decisions and gives an explicit
  template for rejecting out-of-scope requests.

**The scope lock.** Crypto only, Binance only, spot only, market orders only,
monolith only. Each locked with a review date rather than a vague intention.

The rules exist because an assistant that always agrees is a liability. Their
practical function is to give it grounds to say no -- to a request, and to the
author.

---

## 3. What worked

### 3.1 Written decisions with rejected alternatives

The single highest-value artifact. 71 distinct decision IDs are referenced in
source comments, so the rationale is reachable from the code rather than only
from a document nobody opens.

The part that mattered most was recording *rejected* alternatives. Without it,
the same question gets reopened every few weeks and answered differently
depending on what the assistant last saw. With it, reopening a decision costs
one grep.

### 3.2 Rules that produce refusals

Scope creep is the natural failure mode of a capable assistant and an
enthusiastic author. Encoding the scope lock as a rule file with a rejection
template converted "should we add limit orders?" from a conversation into a
lookup.

### 3.3 Building the thing that grades you

The research layer is the strongest engineering in the repository, and it was
built to reject the project's own output. Deflated Sharpe Ratio, effective-trial
counting, gates fixed before results are seen, a cost model deliberately biased
pessimistic, and a pre-registered date at which the project evaluates whether to
stop.

That machinery was then pointed at six months of the author's own work and
returned: nothing here is real. It was reported rather than re-tuned.

This generalises past trading. An assistant will help you build a thing and will
also help you believe in it. The countermeasure is to build the adversarial
evaluator *first*, while you have no results to protect.

### 3.4 Mechanical verification of what is mechanically verifiable

Where a property could be checked by machine, it held up well: 19 indicators at
88-100% coverage, risk sizing at 100%, an equivalence test proving an O(n)
backtest path returns results identical to the O(n^2) path it replaced.

---

## 4. Where it failed, and how each was caught

Eight failure modes. All eight were found by a systematic pre-publication
review of this repository -- reading the code against its own claims, running
its documented commands, and asking one uniform question of subsystems that had
only ever been reviewed individually. None was reported by a user, and none was
found by the test suite.

That last point is the finding. A 1,900-test suite at 63% coverage was green
throughout, because these defects are not the kind a conventional suite is
shaped to detect.

They share a shape: **locally correct code that is globally disconnected, plus
verification that agreed with the code instead of checking it.**

Seven of the eight are fixed, each with a mechanism that prevents recurrence
rather than a one-off patch. The eighth is open and documented.

### 4.1 Verification shaped like the defect

The worst one. `StartupChecklist._check_strategies` called
`StrategyEngine.create_strategy()` with four keyword arguments that do not
exist on its signature, and read three attributes the `Strategy` model does not
have plus one it never had. Every call raised. A bare `except Exception`
reported the result as "Strategy <name> validation failed", so the message
blamed the data.

It survived roughly six months. The reason is the important part: every
orchestrator test passed `MagicMock()` as the strategy engine, and a mock
accepts any call with any arguments. Worse, the fixture in `test_all_checks_pass`
described its strategy using the same non-existent field names the broken code
expected -- and named a template that does not exist. **The test had been
written to match the defect rather than the model, and then asserted that a
check which could never pass in production did pass.**

An assistant asked to write a test for code it just wrote will tend to encode
the same misunderstanding twice. Two artifacts, one belief, and a green tick.

The fix (DEC-2026-08-11-001) validates against `TemplateManager` directly and
writes nothing, with five tests exercising a real `StrategyEngine`. Programming
errors now propagate instead of being reported as check failures
(DEC-2026-08-11-002) -- swallowing them is what made the defect undiagnosable.

### 4.2 Unintegrated completeness

`src/core/orchestrator.py` is 1,850 lines implementing an eight-step startup
sequence, a kill-switch-first main loop, entry-timing coordination, graceful
degradation, and emergency shutdown with position reconciliation. It is
coherent, documented, and 71% covered by tests.

Nothing calls it. `set_orchestrator()` is defined in the API layer and invoked
nowhere, so the module-level handle is permanently `None` and `/system/start`
and `/system/stop` cannot work. The system that actually deploys is
`scripts/run_live_trading.py`, which independently reimplements the loop.

No test failed, because the orchestrator's tests test the orchestrator. Local
coherence is not integration, and a test suite scoped to a module cannot tell
you the module is orphaned. This is recorded rather than quietly deleted; it is
a real duplication and it is unresolved.

### 4.3 Namespace collisions from incremental refactors

`src/core/strategy/regime.py` and `src/core/strategy/regime/` both existed.
CPython resolves packages before same-named modules, so the file had been dead
since the package was created. A later session had migrated its contents into
`regime/manual.py` and correctly re-exported them -- and left the original in
place.

Each session was right about its own scope. Nobody was responsible for the
seam.

### 4.4 Documentation drifting off the system

`README.md` was last modified in the initial commit and then described the
project for six months while the project changed underneath it. It advertised
six strategy templates when 29 generators existed, and never mentioned the
research layer -- the most interesting thing in the repository.

Prose has no test suite. It rots silently in a way code does not.

### 4.5 Build artifacts nobody owned

`.claude/skills` and `.agent/skills` were committed as gitlinks with no
`.gitmodules` file, so any fresh clone produced two empty directories that
`git submodule update --init` could not repair. It never broke a local machine,
so it was never noticed.

### 4.6 An audit that read the signature but not the body

Near the end, an AI audit reviewed the repository and correctly identified the
defect in 4.1. Its recommended fix was to correct the keyword arguments to match
the real signature.

That fix would have made things worse. `create_strategy()` persists -- it calls
`DataStore.save_strategy()` and hardcodes `StrategyStatus.DRAFT`, with no
parameter to opt out. Corrected keyword arguments would have converted a loud
`TypeError` into a silent write of one duplicate strategy row per active
strategy, on every startup, forever.

The audit read the function's signature and not its body. The lesson is narrow
and worth stating precisely: **an AI review is a strong generator of leads and a
weak source of verdicts.** Every finding in that audit was checked against the
source before it was acted on, and this one changed under inspection.

### 4.7 A test that documented a workaround instead of a bug

`LiquidationStore` partitioned written events into date directories keyed on
**wall-clock flush time**, while the reader derived candidate directories from
the query window, expressed in **trade time**. Two clocks, one partition scheme.
They agree only while events are flushed on the same UTC day they occurred; any
wider gap wrote the event to disk and made it invisible to every subsequent
query.

What makes this a section-4 story rather than an ordinary bug: there was a
passing test called
`test_store_read_window_spans_midnight_partition_padding`, documenting that
"an event flushed under the NEXT day's dir is still found by date padding". The
divergence had been noticed at the midnight boundary and papered over with a
one-day read pad, and the test then encoded the workaround as intended
behaviour. **A test that documents a workaround makes a design flaw look like a
design.** The general case survived because the specific case was covered.

Caught only because a failing test in an unrelated cleanup pass was investigated
rather than adjusted. The obvious fix -- change the assertion -- would have
buried it.

### 4.8 Nobody ran the quickstart

`scripts/init_db.py` printed a check-mark emoji on success. On a default Windows
console (cp1252) that raises `UnicodeEncodeError`. The bare `except Exception`
around it then attempted to print a cross-mark emoji, which raised again,
unhandled. The database was created correctly, and the script exited 1 with a
traceback.

The first command in the project's own README failed on the author's own
platform, for months, and 1,900 passing tests said nothing about it -- because
tests import modules and call functions, and nobody had run the documented
entrypoint end to end. Eleven other files carried the same latent crash,
including `run_live_trading.py`, where a raising `print` inside the loop is an
availability failure with capital at stake.

Two lessons, and the second is the general one. Emoji in program output is a
portability bug, not a style preference. And a test suite verifies the code you
told it about; the README is a claim about behaviour, and nothing was checking
it.

---

## 5. What this suggests

1. **Mocks are where AI-assisted verification goes to die.** A mock accepts any
   call. Where an interface boundary matters, at least one test must cross it
   for real. The single most valuable test added during cleanup constructs a
   real `StrategyEngine`.

2. **Ask what would fail if this module were deleted.** If the answer is "only
   its own tests", it is not integrated. Nothing in a conventional suite asks
   this question.

3. **Write the decision, the alternatives, and why they lost.** Context windows
   end; the log does not. This is cheap and it compounds.

4. **Give the assistant grounds to refuse.** A rule file it must read before
   implementing is the closest available thing to a second opinion.

5. **Build the evaluator before you have results to defend.** The DSR layer
   could return "all of it is noise" because it was designed before there was
   anything to protect.

6. **Treat AI review as leads, not verdicts.** Section 4.6 is one audit finding
   away from a data-corruption bug shipped in the name of fixing a bug.

7. **Documentation needs an owner or it will lie.** Six months of accurate code
   and a stale README is a net-negative repository for a first-time reader.

8. **Run your own quickstart, on a clean machine, before you publish it.**
   Section 4.8 is the cheapest possible bug to find and the most expensive one
   to ship. A test suite checks the code it was pointed at; a README is an
   unverified claim about behaviour until somebody executes it.

9. **When a test fails during unrelated work, investigate before adjusting.**
   Sections 4.7 and 4.1 were both found that way, and in both cases the
   convenient fix -- change the assertion -- would have preserved the defect
   and produced a green suite. The pressure to make a red test green is exactly
   when the bug is easiest to bury.

---

## 6. Disclosure

The code in this repository was written by one person working with AI coding
assistants throughout. The architecture, the scope decisions, the research
methodology, and every judgment call recorded in `DECISIONS.md` are the author's.
The implementation was largely assistant-generated against written specifications
and then reviewed.

This document was itself drafted with assistance, and verified against the
source. Every figure in Section 1 is reproducible with
`python scripts/doc_stats.py`. Every defect in Section 4 was confirmed by
reading the code before it was written up.

Status of the eight:

| | Failure mode | Status |
|---|---|---|
| 4.1 | Verification shaped like the defect | Fixed; five tests now run against a real engine |
| 4.2 | Unintegrated completeness | **Open**, documented in ARCHITECTURE.md section 10 |
| 4.3 | Namespace collision | Fixed; shadowed module removed |
| 4.4 | Documentation drifting off the system | Fixed; figures now generated, not typed |
| 4.5 | Build artifacts nobody owned | Fixed; broken gitlinks untracked |
| 4.6 | An AI audit that read a signature but not a body | Caught in review; the recommended fix was not applied |
| 4.7 | A test documenting a workaround instead of a bug | Fixed; partition key corrected, two regression tests |
| 4.8 | Nobody ran the quickstart | Fixed; CI now runs it on Linux and Windows |

Each fix is a mechanism rather than a patch: a real-engine test, a CI job that
executes the documented quickstart, a feature store that computes knowability
instead of trusting it. The distinction matters, because every one of these
defects survived a green test suite.
