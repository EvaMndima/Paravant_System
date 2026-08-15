# Documentation Freshness Rules

## Purpose

This rule file prevents **stale documentation**: a `.md` file that asserts
something about the system which the code no longer does.

Stale documentation is worse than absent documentation. Absent documentation
makes a reader go and check. Stale documentation makes a reader trust a claim
that is false, and in this repository those claims include things like *"there
is no authentication"* and *"the kill switch defaults off"* -- statements a
reader may act on with real money.

**Core Principle:** a change that invalidates a written claim must update that
claim in the same commit. Documentation is part of the change, not a follow-up.

**This applies whether or not the user asks for it.** "Update the docs" is not
a separate request; it is part of "make the change".

---

## Rule 1: Documentation Is Part of the Change

### Rule 1.1: Same Commit, Not Later

If a code change makes any sentence in a tracked `.md` file untrue, that
sentence is updated in the **same commit**. Not in a follow-up commit, not in a
TODO, not "when the docs get a pass".

A commit that changes behaviour and leaves a contradicting document in place is
an incomplete commit.

### Rule 1.2: The Test Is "Would a Reader Be Misled"

Update the document when a reader acting on it would now do the wrong thing.
Concretely, update when the change alters:

- **What the system does** -- behaviour, defaults, guarantees, failure modes
- **What the system requires** -- environment variables, dependencies,
  prerequisites, minimum versions
- **What is or is not safe** -- security posture, known gaps, warnings
- **Measured numbers presented as fact** -- test counts, coverage, endpoint
  counts, lint error counts, line counts
- **Status claims** -- "not implemented", "open", "complete", checkbox state
- **Names a reader will search for** -- file paths, function names, config keys,
  route paths, decision IDs

Do **not** rewrite a document for a change that leaves every claim in it true.
Churn is not freshness.

### Rule 1.3: Numbers Are Claims

A number in a document is an assertion that was true when measured. When a
change moves it, either update it or mark it as a dated measurement.

Prefer dating measurements over quietly restating them:

```markdown
As of 2026-08-14: 1,899 tests pass, 0 fail.
```

This makes a stale number self-evidently stale, which is a far weaker failure
than a confident wrong number.

---

## Rule 2: Discovery Is Mandatory, Not Optional

Never rely on memory to decide which documents mention a thing. **Search.**

### Rule 2.1: The Discovery Procedure

Before finishing any behaviour-changing task, grep the tracked markdown for the
concepts the change touched:

```bash
# The concept, the old claim, and the identifiers a reader would search for
grep -rniE "auth|X-API-Key|unauthenticated" --include=*.md .

# Anything asserting the old behaviour
grep -rn "no authentication" --include=*.md .
```

Search for the **old** claim, not the new one. The old claim is what is now
wrong, and it is what you are hunting.

### Rule 2.2: Search Terms Come From the Diff

Derive search terms mechanically from what changed: new and removed config
keys, new and removed function or class names, changed route paths, changed
defaults, changed numbers. If a symbol was added, deleted or renamed, grep for
it.

### Rule 2.3: Archived Documents Are Exempt

Files under `docs/archive/` are historical snapshots and are **deliberately not
updated**. They record what was believed at a point in time. Do not "fix" them.

Everything else tracked by git is in scope, including this file.

---

## Rule 3: Canonical Document Map

Each kind of claim has an owning document. When a change affects a category
below, that document is the first place to check.

| Category | Owning document |
|---|---|
| Security posture, known gaps, disclosure | `SECURITY.md` |
| What the project is, headline results, "what this is not" | `README.md` |
| System design, layer boundaries, data flow, failure modes | `docs/ARCHITECTURE.md` |
| Endpoint shapes, headers, status codes, request/response | `docs/API_CONTRACT.md` |
| Self-contained brief for a reader with no repo access | `docs/PROJECT_CONTEXT.md` |
| Measured state, ranked findings, publication plan | `docs/PRODUCTION_READINESS_ASSESSMENT.md` |
| Research method, gates, protocol | `docs/research/RESEARCH_PROTOCOL.md` |
| Research results and their corrections | `docs/RESEARCH_FINDINGS.md` |
| Deployment, environment variables, upgrade notes | `DEPLOYMENT.md` |
| Local setup, prerequisites | `DEVELOPMENT_SETUP.md`, `docs/ENVIRONMENT_SETUP.md` |
| Runbooks, cron jobs, operational response | `docs/operations/` |
| Architectural decisions and rationale | `.claude/DECISIONS.md` **and** `.agent/DECISIONS.md` |
| Config template and every supported variable | `.env.example` |

A single change commonly touches several. Adding a required environment
variable, for instance, touches `.env.example`, `DEPLOYMENT.md`, and whichever
document describes the behaviour it controls.

---

## Rule 4: Dual-File Synchronisation

`.claude/` and `.agent/` hold parallel copies so that different AI tools read
identical instructions. Both must be updated together.

This rule extends the existing requirement in
`.claude/rules/decision-consistency.md` (Rule 0) from `DECISIONS.md` to **every
paired file**:

- `.claude/DECISIONS.md` and `.agent/DECISIONS.md`
- `.claude/CLAUDE.md` and `.agent/SYSTEM.md`
- `.claude/rules/*.md` and `.agent/rules/*.md`

Verify after editing:

```bash
diff .claude/DECISIONS.md .agent/DECISIONS.md
diff -r .claude/rules .agent/rules
```

Empty output means synchronised. `CLAUDE.md` and `SYSTEM.md` are the exception
to byte-equality -- they differ by tool-specific framing -- but the substantive
content must match.

---

## Rule 5: Upgrade Notes for Breaking Changes

When a change breaks an existing deployment or an existing client, the owning
document gets an explicit upgrade note saying **what breaks, what to do, and
why it was done that way**.

A reader whose deployment starts crash-looping must be able to find the reason
in the documentation rather than in the source.

Example, from `DEPLOYMENT.md`:

> **Upgrading an existing deployment:** `PARAVANT_API_KEY` became mandatory on
> 2026-08-14 (DEC-2026-08-14-001). A deployment that sets `ENVIRONMENT` to
> anything other than `development` will crash-loop until the variable is set.
> That is the intended behaviour -- the alternative is silently serving
> unauthenticated order-placement endpoints.

---

## Rule 6: Corrections Are Marked, Not Erased

When a document made a claim that turned out to be **wrong** -- as opposed to a
claim that has merely become outdated -- mark the correction visibly rather
than silently replacing the text.

This repository already does this, and it is a deliberate practice:

```markdown
> **CORRECTED 2026-08-11.** The paragraph below repeats a superseded result.
> Ten of the eleven strategies had 0-4 recorded trades and are
> `INSUFFICIENT_DATA` under the corrected classifier, not `TIER_D_REJECT`.
```

The distinction:

- **Outdated** (the world moved): update in place. A version number, a test
  count, a resolved finding.
- **Wrong** (the claim was never true, or the method was flawed): keep the
  original text and mark it. Silently deleting an error destroys the record of
  having made it, which in a research repository is itself a finding.

---

## Rule 7: Never Weaken a Warning Without Replacing It

Documented limitations exist because someone found them. When implementing a
fix, do not simply delete the warning.

Replace it with an accurate statement of **what is now true and what is still
not**. A partial fix that reads as a complete one is worse than the original
warning, because the reader stops looking.

Correct:

> ### API authentication is a single shared key, and reads are not gated
>
> [...what is now protected...]
>
> What this does **not** give you: the 42 read endpoints are open; one key with
> no identities or rotation.

Incorrect:

> ### The API is authenticated

The same pattern applied again when rate limiting landed on 2026-08-14. The
warning "no rate limiting" was not deleted — it was replaced with "rate limiting
is a burst cap, not a defence against a patient attacker", followed by the three
reasons that is true (spoofable client identity, per-process buckets, sustained
abuse within the global cap). The reader who needed the original warning still
gets a warning.

---

## Rule 8: AI Assistant Behaviour

### The AI Must ALWAYS:

1. Run the Rule 2.1 discovery grep before reporting a task complete
2. Update every affected document in the same change
3. Update paired `.claude/` and `.agent/` files together
4. State in the change summary which documents were updated and which were
   deliberately left alone
5. Report documentation it found stale but did **not** update, and say why

### The AI Must NEVER:

1. Report a task complete while a tracked document contradicts the code
2. Defer documentation to a follow-up task or a TODO
3. Delete a documented limitation without replacing it with what is now true
4. Update `.claude/` without `.agent/`, or the reverse
5. Assume no document mentions a thing without grepping for it
6. Edit files under `docs/archive/` to match current behaviour

---

## Rule 9: Verification Before Completion

Before reporting any behaviour-changing task complete:

- [ ] Ran the Rule 2.1 grep for the concepts the change touched
- [ ] Searched for the **old** claim, not just the new one
- [ ] Every owning document from the Rule 3 map checked
- [ ] `.env.example` updated if configuration changed
- [ ] `DEPLOYMENT.md` carries an upgrade note if anything breaks
- [ ] Weakened warnings replaced, not deleted (Rule 7)
- [ ] Wrong claims marked as corrections, not erased (Rule 6)
- [ ] Both `.claude/` and `.agent/` copies updated and verified with `diff`
- [ ] Change summary names the documents updated and those left alone

---

## Integration with Other Rules

- **`decision-consistency.md`** -- Rule 0 there requires `DECISIONS.md` sync;
  Rule 4 here extends it to all paired files. New decisions still go in both
  `DECISIONS.md` files.
- **`zero-technical-debt.md`** -- Rule 13.2 there requires an explicit change
  summary; this file adds "which documents were updated" to that summary.
- **`mvp-scope-control.md`** -- Rule 9.1 there defines what must be documented;
  this file defines when it must be re-checked.

---

## Summary

**A change is not finished until the documentation describing it is true.**

Search for the old claim. Update the owning document. Keep the paired files in
sync. Replace warnings rather than deleting them. Mark corrections rather than
erasing them. Say what you updated and what you deliberately did not.

---

**Last Updated:** 2026-08-14
**Enforcement:** MANDATORY for all AI assistants and developers
**Applies To:** All changes in PARAVANT Trading System
**Origin:** DEC-2026-08-14-002
