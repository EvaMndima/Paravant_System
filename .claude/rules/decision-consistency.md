# Decision Consistency Enforcement Rules

## Purpose

This rule file enforces **STRICT consistency** between documented architectural decisions and actual code implementation.

**Decision files are maintained in BOTH locations for tool consistency:**
- `.claude/DECISIONS.md` - Used by Claude Code
- `.agent/DECISIONS.md` - Used by Antigravity and other agents

**CRITICAL:** Both files MUST be kept in sync. Any update to decisions requires updating BOTH files identically.

These rules prevent:
- Decision drift (code diverges from documented rationale)
- Architectural erosion (decisions get ignored over time)
- Regression of fixed issues (reverting production-grade fixes)
- Loss of institutional knowledge (why decisions were made)
- Tool inconsistency (different AI tools seeing different decisions)

**Core Principle:** Code must match documented decisions. If code needs to change, decisions must be updated first (with approval) in BOTH locations.

---

## Rule 0: DUAL-FILE SYNCHRONIZATION (MANDATORY)

**ALL decision updates MUST be applied to BOTH files:**

### Step 0.1: Update Both Files Identically

When adding or modifying ANY decision:

1. **Update `.claude/DECISIONS.md`**
2. **Update `.agent/DECISIONS.md`** with IDENTICAL content
3. **Verify synchronization:**
   ```bash
   diff .claude/DECISIONS.md .agent/DECISIONS.md
   # Should output nothing (files are identical)
   ```

### Step 0.2: Metadata Must Match

Both files must have identical:
- [ ] Decision entries (content, formatting, IDs)
- [ ] "Last Updated" date
- [ ] "Total Decisions" count
- [ ] "Next Decision ID" value
- [ ] Status markers (ACTIVE, SUPERSEDED, LOCKED)

### Step 0.3: Why Both Files?

**Tool Consistency:**
- **Claude Code** reads from `.claude/` directory
- **Antigravity** and other agents read from `.agent/` directory
- **Without sync:** Different tools see different decisions = chaos

**This is NON-NEGOTIABLE.** Failing to update both files creates decision drift between tools.

---

## Rule 1: MANDATORY Decision Check Before Implementation

**BEFORE implementing ANY feature, fix, refactor, or change:**

### Step 1.1: Read Relevant Decisions

```
1. Open `.claude/DECISIONS.md` OR `.agent/DECISIONS.md` (both are identical)
2. Search for decisions related to your work
3. Read each decision completely (not just title)
4. Identify all DEC-YYYY-MM-DD-XXX IDs that apply
```

**Note:** Both `.claude/DECISIONS.md` and `.agent/DECISIONS.md` contain identical content. Read from either location depending on which tool you're using.

### Step 1.2: Identify Affected Decisions

Ask yourself:
- Does this change affect database models? → Check DEC-2026-02-08-002, 007, 009, 010
- Does this involve timestamps? → Check DEC-2026-02-08-003
- Does this involve API endpoints? → Check DEC-2026-02-08-004, 005, 012, 013
- Does this involve queries? → Check DEC-2026-02-08-006, 011
- Does this involve logging? → Check DEC-2026-02-08-008
- Is this adding a new feature? → Check locked decisions (asset class, broker, etc.)

### Step 1.3: Verify Consistency

For each relevant decision:
- [ ] Proposed implementation matches decision rationale
- [ ] Alternatives rejected in decision are NOT being introduced
- [ ] Status is ACTIVE (not SUPERSEDED)
- [ ] No locked decisions are being violated

### Step 1.4: Document Result

In your implementation plan or commit message:
```
Decision Check:
- DEC-2026-02-08-XXX: [Decision Title] - ✅ CONSISTENT
- DEC-2026-02-08-YYY: [Decision Title] - ✅ CONSISTENT
```

---

## Rule 2: REFUSE Implementation if Inconsistent

**If proposed change is INCONSISTENT with documented decision:**

### Step 2.1: Flag the Inconsistency

**AI Assistant MUST refuse implementation and respond:**

```
❌ DECISION INCONSISTENCY DETECTED

Proposed Change: [Brief description]
Conflicts With: DEC-YYYY-MM-DD-XXX - [Decision Title]

Analysis:
- Current Decision: [What's documented]
- Proposed Change: [What you want to do]
- Conflict: [Why they're inconsistent]

Options:
1. Modify proposed change to align with decision (RECOMMENDED)
2. Update decision with user approval (requires strong justification)
3. Cancel implementation

Which option do you prefer?
```

### Step 2.2: Do NOT Proceed Without Resolution

**BLOCKING REQUIREMENT:** Cannot implement code that violates documented decisions.

---

## Rule 3: Document New Decisions During Implementation

**If implementation requires a NEW decision (not previously documented):**

### Step 3.1: Identify the Decision

New decisions required when:
- Choosing between multiple implementation approaches
- Making architectural trade-offs
- Selecting libraries/frameworks
- Defining data structures or APIs
- Setting performance targets

### Step 3.2: Document the Decision in BOTH Files

**CRITICAL:** Add to BOTH decision files (keep them in sync):

1. **Update `.claude/DECISIONS.md`** with new decision
2. **Update `.agent/DECISIONS.md`** with IDENTICAL decision (MANDATORY)

Template for both files:

```markdown
### DEC-YYYY-MM-DD-XXX: [Decision Title]
- **Decision:** [What was decided]
- **Context:** [Why this matters]
- **Rationale:** [Why this choice over alternatives]
- **Alternatives Considered:** [What else was evaluated]
- **Status:** ACTIVE
- **Date Decided:** YYYY-MM-DD
- **Implemented By:** Section X.Y
- **Affected Files:** [List files]
- **References:** [PRD sections, docs, external links]
```

**Sync Verification Checklist:**
- [ ] Decision added to `.claude/DECISIONS.md`
- [ ] Identical decision added to `.agent/DECISIONS.md`
- [ ] Both files have same "Next Decision ID" updated
- [ ] Both files have same "Last Updated" date
- [ ] Both files have same "Total Decisions" count
- [ ] Verified with: `diff .claude/DECISIONS.md .agent/DECISIONS.md` (no output = success)

### Step 3.3: Reference Decision in Code

Add comment referencing decision:

```python
# Decision: DEC-2026-02-08-015 - Bidirectional relationships
# All relationships use back_populates for object graph navigation
trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="order")
```

---

## Rule 4: Verify Decision Implementation After Changes

**AFTER completing a section or major feature:**

### Step 4.1: List Affected Decisions

Create checklist of all decisions that should be implemented:

```
Section 1.2 (Database Layer) - Decision Verification:
- [ ] DEC-2026-02-08-002: SQLAlchemy 2.0 with Mapped[T]
- [ ] DEC-2026-02-08-003: Timezone-aware timestamps
- [ ] DEC-2026-02-08-007: Input validation at model layer
- [ ] DEC-2026-02-08-009: Explicit JSON type
- [ ] DEC-2026-02-08-010: Lambda functions for mutable defaults
- [ ] DEC-2026-02-08-011: Boolean comparison with .is_()
- [ ] DEC-2026-02-08-015: Bidirectional relationships
```

### Step 4.2: Verify Each Decision

For each decision, check:

**DEC-2026-02-08-002: SQLAlchemy 2.0 with Mapped[T]**
- [ ] All models import `Mapped` from sqlalchemy.orm
- [ ] All fields use `Mapped[T]` syntax (not `Column()`)
- [ ] All mapped_column() calls use explicit types
- [ ] No deprecated SQLAlchemy 1.x patterns

**DEC-2026-02-08-003: Timezone-aware timestamps**
- [ ] All datetime fields use `datetime.now(timezone.utc)`
- [ ] No usage of `datetime.utcnow()` anywhere
- [ ] TimestampMixin uses timezone-aware defaults
- [ ] All datetime comparisons use timezone-aware values

**DEC-2026-02-08-007: Input validation at model layer**
- [ ] All numeric fields have `@validates` decorators
- [ ] Validators check for NaN with `math.isnan()`
- [ ] Validators check for Infinity with `math.isinf()`
- [ ] Validators check negative/zero values appropriately
- [ ] Validators raise ValueError with descriptive messages

**DEC-2026-02-08-010: Lambda functions for mutable defaults**
- [ ] No `default=dict` or `default=list` anywhere
- [ ] All dict/list defaults use `default=lambda: {}`
- [ ] Cast used where needed: `default=lambda: cast(dict[str, Any], {})`

### Step 4.3: Document Verification Result

In completion summary or commit:

```
Decision Verification (Section 1.2):
✅ All 7 relevant decisions verified and implemented correctly
- DEC-2026-02-08-002: VERIFIED (all models use Mapped[T])
- DEC-2026-02-08-003: VERIFIED (all timestamps timezone-aware)
- DEC-2026-02-08-007: VERIFIED (input validation comprehensive)
- DEC-2026-02-08-009: VERIFIED (explicit JSON types)
- DEC-2026-02-08-010: VERIFIED (lambda functions for defaults)
- DEC-2026-02-08-011: VERIFIED (boolean comparisons use .is_())
- DEC-2026-02-08-015: VERIFIED (bidirectional relationships)
```

---

## Rule 5: Update Decisions When Reality Changes

**When implementation reveals decision needs updating:**

### Step 5.1: Get Explicit User Approval

**BLOCKING REQUIREMENT:** Cannot change decisions without user approval.

Request approval with:
```
📝 DECISION UPDATE REQUIRED

Current Decision: DEC-YYYY-MM-DD-XXX - [Title]
Proposed Update: [What needs to change]

Reason for Update:
[Why current decision doesn't work]

Impact:
- Files Affected: [List]
- Risk Level: [LOW/MEDIUM/HIGH]
- Backward Compatibility: [YES/NO]

Proposed New Decision:
[Full decision entry]

Approve decision update?
```

### Step 5.2: Update BOTH Decision Files

**CRITICAL:** Update BOTH files identically:

1. **Update `.claude/DECISIONS.md`:**
   - Mark old decision as **SUPERSEDED**:
   ```markdown
   ### DEC-YYYY-MM-DD-XXX: [Old Decision]
   - **Status:** SUPERSEDED by DEC-YYYY-MM-DD-YYY on 2026-02-XX
   - [Rest of decision unchanged]
   ```
   - Add new decision with new ID
   - Reference superseded decision in new entry
   - Update "Last Updated", "Total Decisions", "Next Decision ID"

2. **Update `.agent/DECISIONS.md`:**
   - Make IDENTICAL changes to `.agent/DECISIONS.md`
   - Must match `.claude/DECISIONS.md` exactly
   - Same superseded markers, same new decision, same metadata

3. **Verification:**
   ```bash
   # Verify files are identical
   diff .claude/DECISIONS.md .agent/DECISIONS.md
   # Should output nothing (files are identical)
   ```

### Step 5.3: Update Affected Code

- Implement new decision across all affected files
- Add comments referencing new decision ID
- Remove old patterns

---

## Rule 6: Cross-Check Locked Decisions

**BEFORE implementing ANY feature:**

### Step 6.1: Check Locked Decisions List

Read `.claude/DECISIONS.md` OR `.agent/DECISIONS.md` section "Locked Decisions":
- DEC-2026-01-15-001: Asset Class - Crypto ONLY
- DEC-2026-01-15-002: Broker - Binance ONLY
- DEC-2026-01-15-003: Database - SQLite/PostgreSQL ONLY
- DEC-2026-01-15-004: Order Types - Market Orders ONLY
- DEC-2026-01-15-005: Architecture - Monolithic ONLY

### Step 6.2: Verify No Violations

If proposed change involves:
- Adding support for stocks/forex → ❌ BLOCKED (DEC-2026-01-15-001)
- Integrating other exchanges → ❌ BLOCKED (DEC-2026-01-15-002)
- Using MongoDB → ❌ BLOCKED (DEC-2026-01-15-003)
- Implementing limit orders → ❌ BLOCKED (DEC-2026-01-15-004)
- Splitting into microservices → ❌ BLOCKED (DEC-2026-01-15-005)

### Step 6.3: Refuse if Locked Decision Violated

**AI Assistant MUST refuse and respond:**

```
🔒 LOCKED DECISION VIOLATION

Proposed Change: [Description]
Violates: DEC-YYYY-MM-DD-XXX - [Locked Decision]
Status: LOCKED until [Review Date/Phase]

This decision is LOCKED per MVP scope control rules.
Cannot implement without:
1. PRD update (Part 2 - MVP Scope)
2. Explicit user approval
3. Documentation update
4. Timeline adjustment

See: `.claude/rules/mvp-scope-control.md` for details

Proceed anyway? (requires explicit user override)
```

---

## Rule 7: Prevent Regression of Production Fixes

**Special protection for decisions that fixed production issues:**

### Step 7.1: Identify Fix Decisions

Decisions with "FIXED" in status:
- DEC-2026-02-08-004: CORS security (was CRITICAL vulnerability)
- DEC-2026-02-08-005: Real database health checks (was fake)
- DEC-2026-02-08-010: Lambda for mutable defaults (was CRITICAL bug)

### Step 7.2: Extra Scrutiny for Changes

If change affects file listed in fix decision:
1. **READ the decision completely** (understand what was fixed)
2. **VERIFY your change doesn't reintroduce bug** (check against "Before" state)
3. **TEST the fix still works** after your change

### Step 7.3: Block Regressions

If change would reintroduce bug:

```
⚠️ PRODUCTION REGRESSION DETECTED

Change: [Description]
Would Reintroduce: [Bug that was fixed]
Original Fix: DEC-YYYY-MM-DD-XXX on YYYY-MM-DD

Example:
Change: Setting allow_origins=["*"] for convenience
Would Reintroduce: CRITICAL CORS security vulnerability (SEC-001)
Original Fix: DEC-2026-02-08-004 on 2026-02-08

This regression is BLOCKED.
Please revise your approach to maintain the fix.
```

---

## Rule 8: Decision-Code Alignment Verification

**Periodic check that code matches decisions:**

### Step 8.1: Run Decision Audit (Manual)

For each active decision:
1. Locate affected files
2. Read relevant code sections
3. Verify code matches decision rationale
4. Flag discrepancies

### Step 8.2: Discrepancy Report Format

```
Decision-Code Alignment Audit: [Section/Phase]

✅ ALIGNED:
- DEC-YYYY-MM-DD-XXX: Code matches decision (verified)

❌ MISALIGNED:
- DEC-YYYY-MM-DD-YYY: Code differs from decision
  - Decision Says: [Expected pattern]
  - Code Has: [Actual implementation]
  - Action: [Fix code OR update decision]
```

---

## Rule 9: New Developer Onboarding Check

**When new developer/AI session starts work:**

### Step 9.1: Mandatory Reading

1. Read `.claude/CLAUDE.md` OR `.agent/SYSTEM.md` (project instructions)
2. Read `.claude/DECISIONS.md` OR `.agent/DECISIONS.md` (all decisions)
3. Read `.claude/rules/decision-consistency.md` (this file)
4. Read `.claude/rules/zero-technical-debt.md` (quality rules)
5. Read `.claude/rules/mvp-scope-control.md` (scope rules)

**Note:** `.claude/` and `.agent/` files are identical - read from either location.

### Step 9.2: Confirm Understanding

Before first code change:
- [ ] I have read all decision documentation
- [ ] I understand decision consistency requirements
- [ ] I understand dual-file sync requirement (`.claude/` AND `.agent/`)
- [ ] I will check decisions before every implementation
- [ ] I will document new decisions as I make them in BOTH files
- [ ] I will not violate locked decisions without approval

---

## Rule 10: AI Assistant Behavior (Mandatory)

### AI Must ALWAYS:

1. **Read decisions BEFORE code changes** (not after)
2. **Refuse implementation if inconsistent** (don't guess or assume)
3. **Document new decisions explicitly in BOTH files** (`.claude/` AND `.agent/`)
4. **Verify decisions after completion** (check implementation matches)
5. **Get user approval for changes** (don't change decisions unilaterally)
6. **Verify file sync** after decision updates (`diff .claude/DECISIONS.md .agent/DECISIONS.md`)

### AI Must NEVER:

1. Skip decision check (claiming "it's a small change")
2. Implement first, check decisions later
3. Change decisions without updating BOTH DECISIONS.md files
4. Update only `.claude/DECISIONS.md` (must update `.agent/` too)
5. Update only `.agent/DECISIONS.md` (must update `.claude/` too)
6. Violate locked decisions without explicit override
7. Reintroduce bugs that were fixed (regression prevention)
8. Assume decisions are outdated (check status field)

### Example Correct Behavior:

```
User: "Can we add support for limit orders?"

AI Response:
"❌ LOCKED DECISION VIOLATION

Proposed: Add limit order support
Violates: DEC-2026-01-15-004 - Order Types - Market Orders ONLY
Status: LOCKED until V1

Per MVP scope control, limit orders are explicitly out of scope.
They're planned for V1 (post-MVP).

See `.claude/rules/mvp-scope-control.md` Section 1A.E

Would you like to:
1. Add limit orders to V1 backlog (RECOMMENDED)
2. Explicitly override locked decision (requires PRD update)
3. Cancel this request
"
```

### Example Incorrect Behavior (DO NOT DO):

```
User: "Can we add support for limit orders?"

AI Response:
"Sure! Let me add limit order support..."
[Implements without checking locked decisions]
```

---

## Enforcement Checklist

**Before ANY code change:**

- [ ] Read `.claude/DECISIONS.md` OR `.agent/DECISIONS.md`
- [ ] Identify relevant decision IDs
- [ ] Verify proposed change is consistent
- [ ] Check locked decisions not violated
- [ ] Document decision check in commit/plan

**During implementation:**

- [ ] Follow decision rationale exactly
- [ ] Use patterns from decision examples
- [ ] Reference decision IDs in code comments
- [ ] Document new decisions if made

**After implementation:**

- [ ] Verify all relevant decisions implemented
- [ ] Check no regressions introduced
- [ ] Update `.claude/DECISIONS.md` if needed
- [ ] Update `.agent/DECISIONS.md` identically (MANDATORY)
- [ ] Verify sync: `diff .claude/DECISIONS.md .agent/DECISIONS.md` (no output)
- [ ] Include verification in completion summary

**If inconsistency detected:**

- [ ] STOP implementation
- [ ] Flag inconsistency to user
- [ ] Get explicit approval before proceeding
- [ ] Update BOTH DECISIONS.md files with new decision
- [ ] Implement with new rationale

---

## Integration with Other Rules

This rule file works with:

- **`.claude/rules/zero-technical-debt.md`** - Decisions document "why" behind technical debt rules
- **`.claude/rules/mvp-scope-control.md`** - Locked decisions enforce MVP scope boundaries
- **`.claude/CLAUDE.md` / `.agent/SYSTEM.md`** - References decisions for all work
- **Production Code Audit** - Verifies decisions are implemented correctly

---

## Summary

**Decision consistency is MANDATORY, not optional.**

Every code change must:
1. Check decisions BEFORE implementation
2. Follow documented rationale
3. Document new decisions in BOTH `.claude/` AND `.agent/` files
4. Verify implementation matches decisions
5. Get approval for decision changes
6. Verify file sync after updates

**Refusing to change code is CORRECT BEHAVIOR when decisions are violated.**

Velocity without consistency leads to technical debt and architectural erosion. These rules protect system integrity across all AI tools.

---

**Last Updated:** 2026-02-09
**Enforcement:** MANDATORY for all AI assistants and developers
**Applies To:** All code changes in PARAVANT Trading System
**Critical Requirement:** BOTH `.claude/DECISIONS.md` AND `.agent/DECISIONS.md` must be kept in sync
