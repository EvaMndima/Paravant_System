# Building PARAVANT with AI Assistance

**Written:** 2026-08-11. **Extended:** 2026-08-17 with a second pass (section 4.9 onward).
**Covers:** 2026-02-08 to 2026-08-17, 149 commits, one human author

PARAVANT is roughly 120,000 lines written over six months by one person working
with AI coding assistants. The most transferable thing it produced is not the
trading system. It is a fairly precise picture of where that way of working
holds up, where it breaks, and what has to be built to catch the breaks.

Sections 3, 4 and 6 are the ones worth your time. Section 3 is what worked.
Section 4 is fifteen failure modes, each with the mechanism that produced it,
how long it survived, and what now prevents it. Section 6 is the part that
generalises: the moves that found them, stated so they can be run against a
codebase that is not this one.

The repository previously contained 35 `SESSION_*_IMPLEMENTATION_PROMPT.md`
files at its root -- the raw prompts. They were replaced by this document, and
remain in git history at tag `pre-cleanup`.

---

## 1. What was built

| Layer | Files | Lines |
|---|---|---|
| `src/` application | 169 `.py` | 49,745 |
| `tests/` | 139 `.py` | 38,718 |
| `frontend/src/` | 98 `.ts`/`.tsx` | 18,139 |
| `scripts/` operational entrypoints | 25 | 12,056 |
| `research/` validation library | 32 `.py` | 6,493 |

*As of 2026-08-17; `python scripts/doc_stats.py` regenerates this table. That
script had an off-by-one in one of its figures until 2026-08-17 -- see 4.12.*

A crypto trading system: Binance data ingestion, 14 indicators, 29 signal
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

**`.claude/DECISIONS.md`** -- 131 dated decision entries across 3,433 lines,
each recording the decision, its context, its rationale, the alternatives
considered and rejected, and its status. Maintained identically in `.agent/` so
that different assistants could not diverge on what had been decided.

**`.claude/rules/`** -- four enforcement files:

- `decision-consistency.md` requires reading the decision log *before*
  implementing, and requires refusing work that contradicts an active decision.
- `zero-technical-debt.md` covers backward compatibility, naming stability,
  behaviour-preserving refactors, one-intent-per-change, and rollback readiness.
- `mvp-scope-control.md` lists locked scope decisions and gives an explicit
  template for rejecting out-of-scope requests.
- `documentation-freshness.md` (added 2026-08-14) requires that a change which
  invalidates a written claim updates that claim in the same commit, and that
  repeated figures are derived from the code rather than copied between
  documents. It was written after 4.11.

**The scope lock.** Crypto only, Binance only, spot only, market orders only,
monolith only. Each locked with a review date rather than a vague intention.

### 2.1 The frontend came from somewhere else

The backend and research layers were written against written specifications in
this repository. The frontend was not. It began as a visual prototype built in
Google AI Studio and was then ported here, rebuilt on Tailwind v3 in March 2026
after a v4 dark-mode failure. The original prototype files are vendored under
`docs/design/references/` and the extracted conventions are in
`docs/design/DESIGN_GUIDE.md`.

This is worth stating for two reasons.

It explains the shape of the code. 46 of the outstanding eslint findings are
`react-hooks/static-components` -- components declared inside other components.
That is a systematic artifact of how the prototype was generated, not scattered
carelessness, and it is concentrated in exactly the files that came across.

And it is the honest description of the work. Productionising a generated
prototype -- porting it onto a real design-token system, a theme context, path
aliases and a type-checked build -- is real engineering, but it is not the same
claim as designing a dashboard from scratch, and the two should not be allowed
to blur.

The rules exist because an assistant that always agrees is a liability. Their
practical function is to give it grounds to say no -- to a request, and to the
author.

---

## 3. What worked

### 3.1 Written decisions with rejected alternatives

The single highest-value artifact. 74 distinct decision IDs are referenced in
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

Where a property could be checked by machine, it held up well: risk sizing at
100% coverage, an equivalence test proving an O(n) backtest path returns results
identical to the O(n^2) path it replaced.

> **CORRECTED 2026-08-21.** This paragraph opened with a claim of nineteen
> indicators at 88-100% coverage. That figure was wrong in both halves. Five of the nineteen are
> scaffolding -- the ABC, the factory, the caching wrapper, shared helpers, the
> resampler -- so the real count is 14, and their coverage runs 33-100% (87%
> aggregate), with Keltner at 33% and Ichimoku at 69%.
>
> It is left marked rather than silently replaced because of where it sat. A
> section arguing that machine-checkable properties held up was itself resting
> on a figure nobody had checked by machine. `test_doc_consistency.py` asserted
> the number and passed, because its own `count_indicators()` counted the same
> five scaffolding modules -- the check and the claim shared a mistake, which is
> the failure mode a check is supposed to make impossible.
>
> The section's argument survives the correction; its example did not.

---

## 4. Where it failed, and how each was caught

Sections 4.1-4.8 are the first pass: eight failure modes, all found by a
systematic pre-publication review of this repository -- reading the code against its own claims, running
its documented commands, and asking one uniform question of subsystems that had
only ever been reviewed individually. None was reported by a user, and none was
found by the test suite.

That last point is the finding. A 1,900-test suite at 63% coverage was green
throughout, because these defects are not the kind a conventional suite is
shaped to detect.

They share a shape: **locally correct code that is globally disconnected, plus
verification that agreed with the code instead of checking it.**

Seven of the eight are fixed, each with a mechanism that prevents recurrence
rather than a one-off patch. The eighth -- 4.2 -- is open and documented.

Section 4B covers a second pass a week later, and what the mechanisms built
here then caught.

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

## 4B. The second pass, and what the first pass missed

Sections 4.1-4.8 came from one systematic review in August 2026. Sections
4.9-4.15 came from a second pass a week later, hardening the repository for
publication: adding API authentication, rate limiting, frontend tests, and
dependency scanning.

Two things about the second batch are worth more than the defects themselves.

**The mechanisms built in the first pass found most of the second batch.** The
consistency test written after 4.11 caught 4.12. The frontend tests written to
make refactoring safe immediately exposed 4.14 and 4.15. The first pass produced
the instruments; the second pass is what they detected.

**Three of the seven were errors in the fixes from the first pass**, not in the
original code. 4.4 was fixed by generating figures rather than typing them, and
4.12 is an error in the generator. That is the honest shape of this work:
remediation introduces its own defects, at a lower rate, and needs the same
scrutiny as the thing it remediates.

### 4.9 A metric that measured something other than its name

The CI coverage job ran `pytest tests/unit tests/research`. The CI test job ran
`pytest tests/`. Any module whose tests live in `tests/integration/` therefore
reported near-zero coverage while being fully exercised on every commit.

`src/data/store.py` -- a 1,332-line data facade -- read **28%** against an
actual **100%**. On the strength of that number it was ranked as a finding in an
otherwise careful readiness assessment, with a task to "raise it to 80%".

The dangerous property is that the number was precise, official, enforced by a
CI floor, and wrong in one consistent direction. The work it prescribed was to
write unit tests duplicating coverage that already existed -- days of effort
whose only effect would have been to move a number.

Caught by measuring before writing, which took ninety seconds. Fixed by scoping
the coverage job to the whole suite and raising the floor 62 -> 72.

### 4.10 Configuration that reads as safe

`docker-compose.yml` contained `BINANCE_TESTNET: ${BINANCE_TESTNET:-true}`.

Docker Compose interpolates `${VAR}` from a local `.env` **independently of the
`env_file:` key**. On a development machine whose `.env` selects mainnet, that
line resolved to `"false"`. A container intended as a local demo was configured
against real markets.

The default is not what makes it safe; the absence of an override is. The line
looks like a safe default and behaves like an inherited one. Nothing about
reading it suggests otherwise, which is why it survived review.

Fixed by hardcoding live-affecting settings rather than interpolating them, and
by passing no exchange credentials into the container at all, so the failure
mode requires two independent mistakes rather than one.

### 4.11 A number that was wrong from birth and spread by copying

The readiness assessment stated "fourteen route modules". `PROJECT_CONTEXT.md`
repeated it twice. `ARCHITECTURE.md` said 13.

There were thirteen -- in every commit, including the one the assessment was
written against. It was not drift. It was wrong when written and had been copied
into two more documents by an author reading the assessment rather than the
repository.

Three documents agreeing is not corroboration when two are transcriptions of the
third. The same failure had already occurred in a second place nobody was
looking: `.agent/rules/mvp-scope-control.md` was missing an amendment its
`.claude/` twin carried, so non-Claude assistants were reading a scope rule that
forbade work which had been permitted for eleven weeks.

Fixed by `tests/unit/test_doc_consistency.py`, which computes each repeated
figure from the repository and fails if any document disagrees, and by
`tests/unit/test_governance_sync.py`, which asserts the paired rule files are
identical.

### 4.12 The generated figure with the error generated into it

Section 4.4's fix was "figures now generated, not typed" -- `scripts/doc_stats.py`
regenerates the table in section 1.

That script counted decisions with the pattern `^### DEC-`, which also matches
the `### DEC-YYYY-MM-DD-XXX: Decision Title` **template** near the top of
`DECISIONS.md`. It reported 132 where there were 131. The same off-by-one had
already been made by hand once, in the `DECISIONS.md` footer, and corrected
there -- while remaining in the tool built to prevent hand-maintained figures
from being wrong.

Caught by cross-checking the script against an independent count while writing
this section, which is the only reason it surfaced at all.

The lesson is not "automate less". It is that **replacing a human-maintained
number with a generated one moves the error into the generator, where it is
harder to see because it is trusted.** The generator needs the scrutiny the
figure used to get.

### 4.13 A tolerance narrower than the platform's resolution

`test_bucket_refill_partial_second` slept 10ms and asserted the token bucket had
refilled by no more than 0.15 tokens -- 5ms of slack, against a default Windows
timer granularity of roughly 15.6ms.

It passed alone and failed under load. It had presumably been failing
intermittently since it was written, on a machine idle enough that nobody saw it.

Fixed by driving a controlled clock instead of sleeping, so the assertion tests
the refill arithmetic rather than the scheduler, and can be exact rather than a
tolerance band. Widening the tolerance was the tempting fix and would have
removed the test's ability to distinguish correct refill from approximately
correct refill.

A related failure surfaced in the same suite: Vitest defaults to one worker per
core, each with its own jsdom, and the combined heap footprint produced a fatal
out-of-memory that killed a *different* test file on each run. A
non-deterministic failure in CI is indistinguishable from a real one and teaches
everybody to press re-run.

### 4.14 Prototype seed data that became a failure mode

`PositionsTable` rendered six hardcoded equity positions -- NVDA, MSFT, TSLA,
AAPL, GOOGL -- whenever its `data` prop was `undefined`. In a system that trades
crypto only.

As prototype seed data this is reasonable and it is how the component was
generated. As a failure mode it is a silent falsification: any future fetch that
returned `undefined` would have presented fabricated holdings, with plausible
quantities and P&L, as real positions. An empty array correctly showed the empty
state, so the defect was invisible in every case anybody had exercised.

Found by writing the component's first test. Fixed by removing the fallback
before wiring real data, so the wiring could not inherit it.

### 4.15 A guard that only ever read its initial value

`useRegimeState` fell back to an "unknown" regime on a failed poll, guarded by
`if (regime === null)` so that a transient failure would not discard a good
reading. The effect's dependency array is empty, so `regime` was captured from
the first render and was always `null`. The guard never guarded anything.

One network blip therefore replaced a valid regime with `unknown` -- and the
strategy router reads regime state to decide whether strategies activate, where
`UNKNOWN` means they do not. A blip silenced trading until the next successful
poll.

Ordinary as a React defect. Notable for how it was found: by writing the first
test that had ever existed for that hook. **The first test for untested code is
a diagnostic instrument before it is a safety net**, and it pays for itself
before it protects anything.

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

10. **Check what a metric measured, not what it is called.** A coverage figure
    is a claim about a measurement, not about the code. Section 4.9's was
    precise, enforced, and wrong by 72 percentage points, and it had already
    generated a work item. Measuring before acting cost ninety seconds and
    saved several days of writing tests for code that was already covered.

11. **Automating a maintained figure moves the error into the generator.**
    Section 4.12 is the fix for 4.4 carrying its own off-by-one. Generated
    numbers are trusted more and inspected less, which is the whole benefit and
    the whole risk. Cross-check a generator against an independent count at
    least once.

12. **Seed data becomes a lie the moment a real code path can produce absence.**
    Section 4.14 was harmless for as long as every caller passed data, and would
    have become a fabricated portfolio the first time a fetch failed. Remove the
    fallback before wiring the real source, not after.

13. **Write the first test for untested code before you change it.** In sections
    4.14 and 4.15 the tests exposed the defects immediately -- not by failing,
    but by forcing someone to state what the code was supposed to do. The first
    test is a diagnostic instrument before it is a safety net.

---

## 6. What transfers to an unfamiliar codebase

Almost none of this is about trading. The defects above were found by a small
number of moves that work on any system whose claims have not been checked
recently -- which describes most systems, and nearly all rapidly generated ones.

In rough order of yield per hour:

1. **Run the documented entrypoint on a clean machine.** Not the test suite --
   the first command in the README. Section 4.8 was a project whose own
   quickstart exited 1 with a traceback on the author's platform, for months,
   under 1,900 passing tests. Also try `docker compose up`: in this repository
   it failed on a fresh clone because a gitignored file was a hard requirement.

2. **Read the project's claims about itself, then check three at random.** Its
   README, its assessment, its architecture document. In this repository the
   assessment's own ranked finding #11 evaporated on measurement (4.9), and a
   figure repeated across three documents had never been true (4.11). Documents
   are the cheapest place to find out whether anybody has been checking.

3. **Ask what would fail if this module were deleted.** If the answer is "only
   its own tests", it is not integrated. This repository has 1,850 lines of
   orchestrator, coherent and 71%-covered, that nothing calls -- while the
   process that actually deploys reimplements the same loop (4.2).

4. **Find the mocks at interface boundaries.** A mock accepts any call with any
   arguments, so a test built on one asserts that the code agrees with itself.
   Section 4.1 survived six months that way, and the fixture had been written to
   match the defect rather than the model.

5. **Grep the test names for workarounds.** A test whose name describes a
   compensation -- padding, tolerance, retry, fallback -- is often a design flaw
   that was noticed and accommodated. Section 4.7 was named for its workaround
   and passed for months while the general case was broken.

6. **Check what each CI gate actually gates.** Scope, not existence. Section 4.9
   was a coverage job measuring a subset of what the test job ran. A gate that
   measures the wrong thing is worse than no gate, because it is cited.

7. **Read the configuration for inherited values.** Anything of the form
   "default unless overridden" needs to be checked against what actually
   overrides it in each environment. Section 4.10 read as a safe default and
   behaved as an inherited one.

8. **Write the first test where there are none, before changing anything.** Not
   for coverage. For diagnosis -- see lesson 13.

What this does not transfer to: any claim that the resulting system is correct.
Every defect above was found by one of these moves, and the honest conclusion
after two passes is that a third would find more. The value of the method is
that it converts unknown unknowns into a list, not that it empties the list.

---

## 7. Disclosure

The code in this repository was written by one person working with AI coding
assistants throughout. The architecture, the scope decisions, the research
methodology, and every judgment call recorded in `DECISIONS.md` are the author's.
The implementation was largely assistant-generated against written specifications
and then reviewed.

This document was itself drafted with assistance, and verified against the
source. Every figure in Section 1 is reproducible with
`python scripts/doc_stats.py`. Every defect in Section 4 was confirmed by
reading the code before it was written up.

Status of the fifteen:

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
| 4.9 | A metric that measured something other than its name | Fixed; coverage job scoped to the whole suite, floor 62 -> 72 |
| 4.10 | Configuration that reads as safe | Fixed; live-affecting settings hardcoded, no credentials in the container |
| 4.11 | A number wrong from birth, spread by copying | Fixed; counts derived from the repository and asserted by test |
| 4.12 | The generated figure with the error generated in | Fixed; full ID pattern, cross-checked against an independent count |
| 4.13 | A tolerance narrower than the platform's resolution | Fixed; controlled clock, and the test runner serialised |
| 4.14 | Prototype seed data that became a failure mode | Fixed; fallback removed before real data was wired |
| 4.15 | A guard that only ever read its initial value | Fixed; updater form, with both branches asserted separately |

Each fix is a mechanism rather than a patch: a real-engine test, a CI job that
executes the documented quickstart, a feature store that computes knowability
instead of trusting it, a test that derives documented figures from the code.
The distinction matters, because every one of these defects survived a green
test suite.

Three of the second batch were defects in fixes from the first. That is
reported rather than smoothed over, because it is the load-bearing caveat: this
method reduces the defect rate of remediation, it does not zero it, and a third
pass would find more.
