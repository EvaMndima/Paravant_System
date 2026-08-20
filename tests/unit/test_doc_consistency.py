"""Cross-document consistency: repeated counts must match the code and each other.

`test_governance_sync.py` keeps `.claude` and `.agent` in step.
`documentation-freshness.md` Rules 1-9 keep a document true against the code.
This file covers the third failure mode: documents that are each individually
plausible and collectively contradictory.

The mechanism is deliberately narrow. For each count that appears in more than
one tracked document, ground truth is computed **from the repository** and every
documented mention is asserted against it. Ground truth is never another
document -- that is how the error this file was written after propagated:
"14 route modules" appeared in the readiness assessment and was copied into
`PROJECT_CONTEXT.md` twice. There were always 13, in every commit, including the
one the assessment was written against.

Scope, per Rule 11.3: counts that churn every commit (test totals, coverage
percentages) are deliberately NOT asserted here. They are stated once, dated, in
their owning document. Asserting them across five files would produce a test
that fails on every unrelated commit, and a test like that gets deleted.

**Known limitation, and it has already caught someone out (me).** These patterns
match prose, so they cannot distinguish a live claim from a *quotation of a
retired one*. Writing "three documents once claimed 14 route modules" in a
document fails this test, correctly by its own rules and unhelpfully in intent.
Spell such references as words -- "fourteen route modules" -- rather than
loosening the pattern. A narrow pattern with an occasional awkward workaround is
worth more than a broad one that stops catching the thing it was written for.

Decision: DEC-2026-08-16-002 - Cross-document consistency is enforced by test
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Tracked, reader-facing documents. `docs/archive/` is excluded by rule: those
# are frozen historical snapshots and are supposed to disagree with the present.
LIVE_DOCS: tuple[str, ...] = (
    "README.md",
    # Added 2026-08-21. It was outside this list and drifted to "120 dated
    # architectural decisions" -- the documentation index, the one file whose
    # whole job is pointing readers at the right document, carrying a wrong
    # count of the thing it points at.
    "docs/README.md",
    "SECURITY.md",
    "DEPLOYMENT.md",
    "DEVELOPMENT_SETUP.md",
    "docs/PROJECT_CONTEXT.md",
    "docs/ARCHITECTURE.md",
    "docs/API_CONTRACT.md",
    "docs/RESEARCH_FINDINGS.md",
    "docs/PRODUCTION_READINESS_ASSESSMENT.md",
    # Added 2026-08-21, and it was the worst offender. Section 3.4, headed
    # "Mechanical verification of what is mechanically verifiable", cited
    # "19 indicators at 88-100% coverage" as its evidence that machine-checkable
    # properties held up. The figure was wrong in both halves and this file --
    # which asserted the same number elsewhere and passed -- could not see it,
    # because its own count_indicators() shared the miscount.
    "docs/AI_ASSISTED_DEVELOPMENT.md",
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _prose(relative: str) -> str:
    """Document text with all runs of whitespace collapsed to single spaces.

    Prose in this repository is hard-wrapped at ~80 columns, so a phrase worth
    asserting is usually split across a line break. Searching the raw text for
    "None has a validated edge" fails purely because a newline sits between
    "has" and "a", which tells you nothing about the document's meaning.
    """
    return re.sub(r"\s+", " ", _read(relative))


# ---------------------------------------------------------------------------
# Ground truth, computed from the repository
# ---------------------------------------------------------------------------


def count_route_modules() -> int:
    """API route modules under src/api/routes, excluding the package marker."""
    return len(
        [p for p in (REPO_ROOT / "src/api/routes").glob("*.py") if p.stem != "__init__"]
    )


def count_signal_generators() -> int:
    """Signal generator implementations, excluding shared scaffolding."""
    excluded = {"__init__", "base", "registry", "types"}
    return len(
        [
            p
            for p in (REPO_ROOT / "src/core/strategy/generators").glob("*.py")
            if p.stem not in excluded
        ]
    )


#: Modules in the indicators package that are not indicators. The ABC, the
#: factory, the caching wrapper, shared helpers, and the timeframe resampler.
INDICATOR_SCAFFOLDING = frozenset(
    {"__init__", "base", "factory", "cached", "utils", "resample"}
)


def count_indicators() -> int:
    """Indicator implementations, excluding shared scaffolding.

    This counted every module in the package until 2026-08-21 and returned 19,
    which is what "19 indicators" in README.md and PROJECT_CONTEXT.md was
    asserted against. The test passed and the documents were still wrong: five
    of the nineteen are scaffolding. A consistency check is only as good as its
    definition of the thing being counted, and this one had been asserting that
    two documents agreed with a miscount.

    Cross-checked against ``IndicatorFactory._registry``, which registers the
    same 14 classes under 20 keys (six are aliases). Two independent derivations
    agreeing is what makes 14 defensible where 19 was not.
    """
    return len(
        [
            p
            for p in (REPO_ROOT / "src/core/indicators").glob("*.py")
            if p.stem not in INDICATOR_SCAFFOLDING
        ]
    )


#: Decision-ID shape. Deliberately requires the full ID rather than the
#: ``### DEC-`` prefix: the loose form matched the template heading near the top
#: of DECISIONS.md and reported 132 where there were 131. Kept byte-identical to
#: the pattern in ``scripts/doc_stats.py`` so the tool and this test cannot
#: disagree -- two anti-drift mechanisms that drift apart are worse than one.
_DECISION_HEADING = r"^### DEC-\d{4}-\d{2}-\d{2}-\d{3}:"
_DECISION_ID = r"DEC-20\d\d-\d\d-\d\d-\d\d\d"

#: The same ID shape in POSIX ERE, for ``git grep -E``, which does not
#: understand the Perl ``\d`` escape and silently matches nothing when handed
#: one. ``doc_stats.py`` carries both forms for this reason; so does this file.
_DECISION_ID_ERE = r"DEC-20[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{3}"

#: Trees ``doc_stats.py`` scans for decision references. ``tests/`` is excluded
#: there and excluded here for the same reason: a decision ID quoted in a test
#: name is not the code implementing that decision.
_DECISION_SOURCE_TREES = ("src/*", "scripts/*", "research/*")


def count_decisions() -> int:
    """Dated decision entries in the log."""
    text = _read(".claude/DECISIONS.md")
    return len(re.findall(_DECISION_HEADING, text, re.MULTILINE))


def count_decision_ids_in_source() -> int:
    """Distinct decision IDs referenced from the source trees.

    Uses ``git grep`` over TRACKED files with the same pathspec and pattern as
    ``scripts/doc_stats.py``, rather than a filesystem walk. That is deliberate.

    A ``rglob("*.py")`` walk returns 72 where the tool returns 74, because 20 of
    the referencing files are strategy biographies and the hypothesis ledger --
    ``research/biographies/*.yaml`` and ``research/hypotheses/ledger.yaml``. Two
    anti-drift mechanisms measuring the same name differently is the defect this
    file exists to catch, so the test mirrors the tool exactly instead of
    forming its own opinion.
    """
    result = subprocess.run(
        ["git", "grep", "-ohE", _DECISION_ID_ERE, "--", *_DECISION_SOURCE_TREES],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    found = set(re.findall(_DECISION_ID, result.stdout))

    # Guard the guard. `git grep` exits 1 on "no matches", which is also what a
    # bad pathspec, a missing git, or a Perl escape handed to -E produces. An
    # empty result must fail loudly rather than silently assert against zero --
    # the first version of this function did exactly that and reported a
    # repository containing 0 decision IDs.
    assert found, (
        "git grep returned no decision IDs. This is a broken measurement, not a "
        f"repository with none. stderr: {result.stderr.strip()!r}"
    )
    return len(found)


def count_api_endpoints() -> int:
    """Routes registered under /api/v1.

    Imports the real app rather than counting decorators, so a router that is
    defined but never included is not counted.
    """
    from src.api.main import app

    return len(
        [r for r in app.routes if str(getattr(r, "path", "")).startswith("/api/v1")]
    )


def count_mutating_endpoints() -> int:
    """Routes under /api/v1 whose method can change state."""
    from src.api.auth import MUTATING_METHODS
    from src.api.main import app

    return sum(
        len(set(getattr(route, "methods", None) or set()) & MUTATING_METHODS)
        for route in app.routes
        if str(getattr(route, "path", "")).startswith("/api/v1")
    )


# ---------------------------------------------------------------------------
# Claim specifications
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Claim:
    """A count that appears in prose and is derivable from the codebase.

    Attributes:
        name: Human label used in failure messages.
        truth: Callable returning the value computed from the repository.
        pattern: Regex with one capturing group around the number. Written to
            match how the claim is actually phrased, not every phrasing that
            could exist -- a pattern that matches too much produces false
            failures on unrelated prose.
    """

    name: str
    truth: object
    pattern: str


CLAIMS: tuple[Claim, ...] = (
    Claim("route modules", count_route_modules, r"(\d+) route modules"),
    Claim("signal generators", count_signal_generators, r"(\d+) signal generators"),
    Claim("indicators", count_indicators, r"(\d+) (?:technical )?indicators"),
    # The negative lookahead separates the endpoint TOTAL from the
    # state-mutating SUBSET, which is phrased "21 endpoints mutate state" in
    # PROJECT_CONTEXT.md. Without it this pattern reports a contradiction
    # between two claims that are both correct and about different things --
    # a false positive is how a consistency test earns a reputation for noise
    # and gets disabled.
    Claim("api endpoints", count_api_endpoints, r"(\d+) endpoints(?!\s+mutate)"),
    Claim(
        "state-mutating endpoints",
        count_mutating_endpoints,
        r"(\d+) state-mutating endpoints",
    ),
    # Added 2026-08-21. This number was stated in five places across four
    # documents and had FOUR different values: 122 twice in README.md, 113 in
    # PRODUCTION_READINESS_ASSESSMENT.md, 120 in docs/README.md, and 131 -- the
    # only correct one -- in PROJECT_CONTEXT.md. Nothing failed, because the
    # count was derivable from the repository and simply was not being derived.
    # `doc_stats.py` had computed it correctly the whole time.
    #
    # The optional `dated` and `architectural` words cover every phrasing in
    # use: "131 dated architectural decisions", "131 decisions with rationale",
    # "131 dated decisions with rationale and alternatives", "131 decisions,
    # dual-maintained".
    #
    # The negative lookahead excludes "21 decisions filed in one day" in
    # PROJECT_CONTEXT.md's timeline, which is a per-day count and not this
    # claim -- the same technique, and the same reasoning, as the `endpoints`
    # lookahead above. There is no suffix common to all seven real mentions to
    # match on positively, so the discriminator has to be negative.
    Claim(
        "decisions",
        count_decisions,
        r"(\d+) (?:dated )?(?:architectural )?decisions(?! filed)",
    ),
    Claim(
        "decision IDs in source",
        count_decision_ids_in_source,
        r"(\d+) distinct IDs",
    ),
)


def _mentions(pattern: str) -> list[tuple[str, int, int]]:
    """Find (document, line number, claimed value) for every match."""
    found: list[tuple[str, int, int]] = []
    compiled = re.compile(pattern)
    for doc in LIVE_DOCS:
        for lineno, line in enumerate(_read(doc).splitlines(), start=1):
            for match in compiled.finditer(line):
                found.append((doc, lineno, int(match.group(1))))
    return found


class TestCountsMatchTheCode:
    """Every documented count equals what the repository actually contains."""

    @pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: c.name)
    def test_documented_count_matches_ground_truth(self, claim: Claim):
        expected = claim.truth()  # type: ignore[operator]
        wrong = [
            f"{doc}:{lineno} says {value}"
            for doc, lineno, value in _mentions(claim.pattern)
            if value != expected
        ]

        assert not wrong, (
            f"{claim.name}: the repository contains {expected}. "
            f"These documents disagree: {wrong}"
        )

    @pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: c.name)
    def test_claim_is_actually_stated_somewhere(self, claim: Claim):
        """Guards the test itself.

        If a phrasing changes so the pattern stops matching, the check above
        passes vacuously over an empty list and silently stops protecting
        anything -- the same trap `test_the_app_actually_has_mutating_routes`
        guards against in the auth suite.
        """
        assert _mentions(claim.pattern), (
            f"{claim.name}: no document matches {claim.pattern!r} any more. "
            f"Either the phrasing changed and this pattern needs updating, or "
            f"the claim was dropped and this Claim should be removed."
        )


class TestNoContradictionsBetweenDocuments:
    """Rule 10.3: two documents disagreeing is a defect, not emphasis."""

    @pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: c.name)
    def test_all_documents_agree_with_each_other(self, claim: Claim):
        by_value: dict[int, list[str]] = {}
        for doc, lineno, value in _mentions(claim.pattern):
            by_value.setdefault(value, []).append(f"{doc}:{lineno}")

        assert len(by_value) <= 1, (
            f"{claim.name} is stated inconsistently across documents: "
            f"{ {v: locs for v, locs in by_value.items()} }"
        )


class TestNarrativeConsistency:
    """The framing of the headline result must not diverge between documents.

    The null result is the most consequential claim in the repository. It is
    restated in several places by necessity -- the README cannot omit it and
    `PROJECT_CONTEXT.md` is meant to be readable standalone. Rule 10.2 allows
    that; these assert the restatements stay compatible.
    """

    def test_readme_states_no_validated_edge(self):
        # The framing shifted on 2026-08-16 from "built to prove its strategies
        # don't work" to a validation-system framing. The result must stay
        # prominent under any framing -- softening it while reframing is the
        # specific risk that change carried.
        assert "None has a validated edge" in _prose("README.md")

    def test_research_findings_states_no_validated_edge(self):
        assert "No strategy in this repository has a validated edge" in _prose(
            "docs/RESEARCH_FINDINGS.md"
        )

    def test_no_document_claims_a_validated_strategy(self):
        """A phrase that would contradict the headline everywhere else."""
        forbidden = re.compile(
            r"(validated edge (was|has been) found|a strategy (that )?passed"
            r"|profitable strategy (was )?found)",
            re.IGNORECASE,
        )
        offenders = [
            f"{doc}:{lineno}"
            for doc in LIVE_DOCS
            for lineno, line in enumerate(_read(doc).splitlines(), start=1)
            if forbidden.search(line)
        ]

        assert not offenders, f"contradicts the headline null result: {offenders}"

    def test_security_and_readme_agree_the_api_is_only_partly_protected(self):
        """Both must disclose the gap, not just the fix (Rule 7)."""
        readme = _prose("README.md").lower()
        security = _prose("SECURITY.md").lower()

        assert "read endpoints are open" in security
        assert "read endpoints are open" in readme or "reads" in readme
