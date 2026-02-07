---
trigger: always_on
---

# Zero-Technical-Debt Engineering Rules

## Purpose

This document defines **non-negotiable engineering rules** for building, modifying, and refactoring the system using AI coding tools (Antigravity, Claude Code, Cursor, etc.).

The goal is to **prevent accidental technical debt, regressions, naming drift, integration breakage, and architectural erosion**, even under rapid iteration and vertical scaling.

These rules apply to **all code changes**, regardless of size, urgency, or perceived simplicity.

---

## 1. Prime Directive (Non-Negotiable)

**Any change must preserve full integration compatibility and must not introduce new bugs, regressions, semantic drift, or architectural degradation.**

If this cannot be guaranteed, the change **must not be implemented**.

Refusing to change code is correct behavior when safety cannot be ensured.

---

## 2. Integration Safety Rules

### 2.1 Backward Compatibility

- All existing public interfaces must remain compatible unless explicitly approved.
- Function signatures, class names, module exports, API schemas, and configuration keys must not change unintentionally.
- If a breaking change is unavoidable:
  - Provide a backward-compatible adapter or alias
  - Explicitly deprecate old behavior (never silently remove it)

### 2.2 Cross-Module Awareness

- Never refactor a file in isolation.
- Assume any exported symbol may be used elsewhere.
- Scan imports and usages across the entire codebase before making changes.

### 2.3 Dependency Discipline

- Do not introduce new dependencies unless:
  - Existing libraries or standard tools cannot reasonably solve the problem
  - The dependency is stable, maintained, and justified
- All new dependencies must be explicitly justified in comments.

---

## 3. Naming & Semantic Consistency (Zero Drift Policy)

### 3.1 Single Meaning, Single Name

- If a concept already exists, reuse the **exact same name**.
- Never rename:
  - Domain entities
  - Core objects
  - Shared data structures
  - Configuration keys

### 3.2 No Synonyms for the Same Concept

Bad:
- `TradeSignal` in one file
- `SignalTrade` in another

Good:
- `TradeSignal` everywhere

### 3.3 Semantic Stability

- Reusing a name requires preserving its original meaning.
- A name must not represent different concepts in different contexts.

### 3.4 Naming Audit Requirement

Before introducing a new name:
- Search the entire codebase
- Confirm the concept does not already exist
- If it exists, reuse the existing name

---

## 4. Refactoring Rules (Safety-First)

### 4.1 Behavior Preservation

- Refactors must not change behavior unless explicitly intended.
- Inputs, outputs, side effects, and error handling must remain unchanged.

### 4.2 Small, Verifiable Changes

- Large refactors must be broken into small, reversible steps.
- Each step must be independently safe and understandable.

### 4.3 No Mixed Intent

- Do not mix refactors with feature changes.
- One change equals one intent.

---

## 5. Bug Prevention Rules

### 5.1 Defensive Assumptions

- Assume upstream inputs may be malformed.
- Assume downstream consumers depend on existing behavior.

### 5.2 Error Handling Consistency

- Reuse existing error-handling patterns.
- Do not introduce new error styles or exception types without justification.

### 5.3 Edge Case Awareness

- Identify edge cases before writing code.
- Document assumptions when edge cases are intentionally ignored.

---

## 6. Testing & Verification Rules

### 6.1 No Change Without Verification

Every change must include at least one of:
- A new or updated test
- Explicit reasoning explaining why existing tests fully cover the change

### 6.2 Regression Protection

- Every bug fix must include a test that would fail without the fix.

### 6.3 Integration Coverage

- Tests must consider integration points, not only local logic.

---

## 7. Documentation & Intent

### 7.1 Explain the Why

- Comments should explain **why** decisions were made.
- Avoid comments that merely restate the code.

### 7.2 Architectural Alignment

- Changes must align with existing architecture.
- Do not introduce new architectural patterns casually.

---

## 8. Architectural Invariants (Do Not Violate)

The following architectural decisions are invariant and may not be changed without explicit approval:

- Direction of data flow
- Ownership of state
- Where side effects are allowed
- Sync vs async boundaries
- Inter-agent communication rules
- Separation between domain logic and infrastructure

---

## 9. System Boundaries & Ownership

### 9.1 System Boundary Rule

- Code must respect declared system, layer, and agent boundaries.
- Cross-boundary access is only allowed via explicit adapters or interfaces.
- Direct shortcuts across boundaries are prohibited.

### 9.2 Ownership Rule

- Every non-trivial module must have a clearly defined responsibility.
- Each module must explicitly state:
  - What it owns
  - What it explicitly does **not** own

---

## 10. State, Time, and Configuration Safety

### 10.1 State Authority Rule

- Each piece of mutable state must have a single authoritative owner.
- All other access must be read-only or mediated.

### 10.2 Time & Ordering Rule

- Any logic depending on time, ordering, or sequencing must explicitly document assumptions.
- Behavior must be defined for:
  - Late events
  - Duplicate events
  - Out-of-order events

### 10.3 Configuration Immutability Rule

- Configuration may be read but must not be mutated at runtime unless explicitly designed for it.

---

## 11. Observability & Control Flow

### 11.1 Observability Before Cleverness

- Increased complexity must be matched by increased observability.
- New logic must improve logs, metrics, traces, or explicit outputs where appropriate.

### 11.2 No Hidden Control Flow

- Control flow must be explicit.
- Avoid hidden side effects, implicit globals, magic behavior, or surprising execution paths.

---

## 12. Deletion, Scale, and Decisions

### 12.1 Deletion Is a First-Class Change

- Removing code is encouraged when safe.
- Removal requires clarity on what replaces the behavior or why it is no longer needed.

### 12.2 Scale Assumption Rule

- New components must state expected scale limits (frequency, data size, concurrency).
- Failure modes when limits are exceeded must be defined.

### 12.3 Decision Log Rule

- Non-obvious design decisions must be recorded in a lightweight, append-only decision log.
- Each entry must include:
  - Date
  - Decision
  - Reason
  - Tradeoffs

---

## 13. AI-Specific Enforcement Rules

### 13.1 No Assumptions

- AI must not assume missing context.
- If context is insufficient, it must ask or refuse.

### 13.2 Explicit Change Summary Required

Every code-modifying response must include:
- What changed
- Why it changed
- What was deliberately not changed
- Integration impact assessment
- The riskiest assumption involved

### 13.3 Refusal Is Correct Behavior

- If safe integration cannot be guaranteed, the AI must refuse to make changes.

---

## 14. Technical Debt Prevention

### 14.1 No Shortcuts

- No temporary hacks.
- No TODOs without explicit intent, ownership, or removal plan.

### 14.2 Consistency Over Cleverness

- Prefer boring, predictable solutions.
- Avoid novelty unless it clearly improves safety or clarity.

### 14.3 Explicit Tradeoffs

- All tradeoffs must be documented.

---

## 15. Rollback Readiness

- All changes must be easily reversible.
- No change may require data loss or cascading failures to undo.

---

## 16. Change Acceptance Checklist

Before accepting any change, confirm:

- [ ] No integration points broken
- [ ] No naming or semantic drift introduced
- [ ] No unintended behavior changes
- [ ] Existing patterns reused
- [ ] Tests updated or explicitly justified
- [ ] No unnecessary dependencies added
- [ ] Rollback is possible
- [ ] No technical debt introduced

---

## Enforcement Philosophy

Velocity without safety is a liability.

These rules exist to protect system integrity, preserve long-term velocity, and prevent silent degradation.

**End of Rules**
