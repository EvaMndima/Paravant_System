"""Leakage audits for point-in-time features.

Two independent checks, because there are two independent ways a feature leaks
and neither test catches the other's failure mode.

1. Interval and lag correctness -- ``audit_knowability``
   Does the value's own timestamp, expanded by the feature's declared interval
   and publication lag, place it at or before the query instant? This catches a
   record whose timestamp is legitimately in the past while its CONTENT comes
   from the future: a 1-hour bar stamped with its 10:00 open, whose close is the
   price at 11:00, read at 10:30.

2. Future invariance -- ``audit_future_invariance``
   Does a query at ``t`` return the same answer whether or not observations
   after ``t`` exist in the dataset? This catches a resolver that searches past
   the query instant -- an off-by-one in a bisect, a ``<=`` that should be
   ``<``, a cache populated from the full history.

Check 2 is the intuitive one and is the one usually written. It cannot detect
the failure in check 1, because the offending record's timestamp really is in
the past; truncating the dataset at ``t`` does not remove it. The bar-alignment
defect found in this repository is exactly that shape, and a suite containing
only check 2 would have passed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from research.features.spec import FeatureSpec
from research.features.store import Observation, Resolver
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LeakageFinding:
    """One instance of a feature exposing information it should not have.

    Attributes:
        feature: Feature name.
        check: Which audit produced this, ``knowability`` or ``future_invariance``.
        asked_at: The query instant.
        detail: Human-readable description of what went wrong.
        leak_seconds: Size of the leak in seconds, where measurable.
    """

    feature: str
    check: str
    asked_at: datetime
    detail: str
    leak_seconds: float | None = None


@dataclass
class LeakageReport:
    """Result of auditing one feature.

    Attributes:
        feature: Feature name.
        instants_checked: How many query instants were exercised.
        findings: Every leak detected.
    """

    feature: str
    instants_checked: int = 0
    findings: list[LeakageFinding] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """Return True when no leak was detected."""
        return not self.findings

    @property
    def worst_leak_seconds(self) -> float:
        """Return the largest measured leak in seconds, 0.0 if none."""
        measured = [f.leak_seconds for f in self.findings if f.leak_seconds is not None]
        return max(measured) if measured else 0.0

    def summary(self) -> str:
        """Return a one-line ASCII summary suitable for a console report."""
        if self.clean:
            return f"[OK]   {self.feature}: clean over {self.instants_checked} instants"
        return (
            f"[LEAK] {self.feature}: {len(self.findings)} finding(s) over "
            f"{self.instants_checked} instants, worst {self.worst_leak_seconds:.0f}s"
        )


def audit_knowability(
    spec: FeatureSpec,
    resolver: Resolver,
    timestamps: Sequence[datetime],
    *,
    symbol: str | None = None,
) -> LeakageReport:
    """Check that every resolved value was knowable at its query instant.

    For each instant, resolves the feature and compares
    ``spec.knowable_at(observed_at)`` against the instant. A value whose
    observation had not completed -- or had completed but not yet been published
    -- is a finding.

    Args:
        spec: The feature specification, whose interval and publication_lag
            define knowability.
        resolver: The adapter under audit.
        timestamps: Timezone-aware UTC instants to exercise.
        symbol: Symbol to resolve for, if the feature is per-symbol.

    Returns:
        A LeakageReport.

    Raises:
        ValueError: If any timestamp is naive.
    """
    report = LeakageReport(feature=spec.name)
    for ts in timestamps:
        if ts.tzinfo is None:
            raise ValueError(f"{spec.name}: audit timestamps must be timezone-aware")
        report.instants_checked += 1

        observation = resolver(symbol, ts)
        if observation is None:
            continue

        knowable_at = spec.knowable_at(observation.observed_at)
        if knowable_at > ts:
            leak = (knowable_at - ts).total_seconds()
            report.findings.append(
                LeakageFinding(
                    feature=spec.name,
                    check="knowability",
                    asked_at=ts,
                    detail=(
                        f"observed_at={observation.observed_at.isoformat()} "
                        f"knowable_at={knowable_at.isoformat()} "
                        f"exceeds query instant by {leak:.0f}s "
                        f"(kind={spec.kind.value}, interval={spec.interval}, "
                        f"publication_lag={spec.publication_lag})"
                    ),
                    leak_seconds=leak,
                )
            )
    return report


def audit_future_invariance(
    spec: FeatureSpec,
    build_resolver: Callable[[Sequence[tuple[datetime, object]]], Resolver],
    observations: Sequence[tuple[datetime, object]],
    timestamps: Sequence[datetime],
    *,
    symbol: str | None = None,
) -> LeakageReport:
    """Check that observations after ``t`` cannot change the answer at ``t``.

    For each instant the resolver is rebuilt twice: once over the full dataset,
    once over only those observations timestamped at or before the instant. If
    the two disagree, the resolver is reading the future.

    Args:
        spec: The feature specification, used for its name.
        build_resolver: Factory constructing a resolver over a set of
            observations. Called once per instant per variant, so it should be
            cheap; this is an audit, not a hot path.
        observations: The full dataset as ``(timestamp, record)`` pairs. The
            timestamp is used only to truncate.
        timestamps: Timezone-aware UTC instants to exercise.
        symbol: Symbol to resolve for, if the feature is per-symbol.

    Returns:
        A LeakageReport.

    Raises:
        ValueError: If any timestamp is naive.
    """
    report = LeakageReport(feature=spec.name)
    full = build_resolver(observations)

    for ts in timestamps:
        if ts.tzinfo is None:
            raise ValueError(f"{spec.name}: audit timestamps must be timezone-aware")
        report.instants_checked += 1

        past_only = build_resolver([o for o in observations if o[0] <= ts])
        got_full = full(symbol, ts)
        got_past = past_only(symbol, ts)

        if _differs(got_full, got_past):
            report.findings.append(
                LeakageFinding(
                    feature=spec.name,
                    check="future_invariance",
                    asked_at=ts,
                    detail=(
                        "answer changed when observations after the query instant "
                        f"were removed: with_future={_describe(got_full)} "
                        f"past_only={_describe(got_past)}"
                    ),
                )
            )
    return report


def _differs(a: Observation | None, b: Observation | None) -> bool:
    """Return True when two resolver results are not equivalent."""
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    return a.value != b.value or a.observed_at != b.observed_at


def _describe(observation: Observation | None) -> str:
    """Render a resolver result for a finding message."""
    if observation is None:
        return "None"
    return f"{observation.value!r}@{observation.observed_at.isoformat()}"


def render_reports(reports: Sequence[LeakageReport]) -> str:
    """Render several reports as an ASCII block for console or CI output.

    Args:
        reports: Reports to render.

    Returns:
        A newline-joined summary, worst offenders last so the tail of a CI log
        shows the problems.
    """
    ordered = sorted(reports, key=lambda r: (r.clean, -r.worst_leak_seconds))
    lines = [r.summary() for r in ordered]
    leaking = [r for r in reports if not r.clean]
    lines.append(
        f"--- {len(reports) - len(leaking)} clean, {len(leaking)} leaking ---"
    )
    return "\n".join(lines)
