"""Feature specifications and point-in-time value types.

A ``FeatureSpec`` states, for one feature, the two facts that determine whether
a query at instant ``t`` may see it:

  1. When the underlying observation *completed* -- an interval feature such as
     a 1-hour bar close is not complete at the bar's open.
  2. How long after completion it becomes *knowable* -- a publication lag, e.g.
     ETF net flows for day D are reported on D+1.

Together these give ``knowable_at``. The store refuses to return any value whose
``knowable_at`` is after the query instant, which turns point-in-time
correctness from a convention each data channel opts into, into a property the
store enforces.

This distinction is not academic. Two channels in this repository reported a
value's timestamp as the *start* of the interval that produced it while the
value itself came from the interval's end, leaking up to 59 minutes of future
information. Each looked correct in isolation. See
``research/features/audit.py``.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta


class FeatureKind(str, enum.Enum):
    """How a feature's observation relates to its timestamp.

    Attributes:
        INSTANT: The value is observed at its timestamp and complete then. A
            perpetual funding settlement print is an instant: the rate is known
            at the settlement moment.
        INTERVAL: The value summarises a period that *begins* at its timestamp
            and is only complete at ``timestamp + interval``. A bar close is an
            interval feature; so is a daily flow total.
    """

    INSTANT = "instant"
    INTERVAL = "interval"


@dataclass(frozen=True)
class FeatureSpec:
    """Declarative description of one point-in-time feature.

    Attributes:
        name: Unique feature name, e.g. ``coinbase_close``.
        description: What the feature measures, in one line.
        kind: Whether the timestamp marks an instant or the start of an interval.
        interval: Duration of the observation window. Required and non-zero for
            ``INTERVAL`` features; must be None for ``INSTANT`` features.
        publication_lag: Delay between the observation completing and it being
            knowable to a decision maker. Zero for market data read from a live
            feed; positive for reported data such as ETF flows.
        unit: Human-readable unit, for reports and matrix headers.
        source: Module path of the channel that supplies this feature.

    Raises:
        ValueError: If the kind and interval are inconsistent, or if any
            duration is negative.
    """

    name: str
    description: str
    kind: FeatureKind
    publication_lag: timedelta
    unit: str
    source: str
    interval: timedelta | None = None

    def __post_init__(self) -> None:
        """Validate the specification.

        Raises:
            ValueError: On an empty name, a negative duration, or a
                kind/interval mismatch.
        """
        if not self.name or not self.name.strip():
            raise ValueError("FeatureSpec.name cannot be empty")
        if self.publication_lag < timedelta(0):
            raise ValueError(
                f"{self.name}: publication_lag cannot be negative "
                f"(got {self.publication_lag})"
            )
        if self.kind is FeatureKind.INTERVAL:
            if self.interval is None or self.interval <= timedelta(0):
                raise ValueError(
                    f"{self.name}: INTERVAL features require a positive interval. "
                    "This is the field that prevents a bar's close being read at "
                    "the bar's open."
                )
        elif self.interval is not None:
            raise ValueError(
                f"{self.name}: INSTANT features must not declare an interval"
            )

    def knowable_at(self, observed_at: datetime) -> datetime:
        """Return the earliest instant at which an observation may be used.

        For an INSTANT feature this is ``observed_at + publication_lag``. For an
        INTERVAL feature the observation is not complete until the interval
        elapses, so it is ``observed_at + interval + publication_lag``.

        Args:
            observed_at: Timestamp the channel attaches to the observation. For
                INTERVAL features this is the START of the period.

        Returns:
            Timezone-aware UTC instant from which the value is legitimate.

        Raises:
            ValueError: If ``observed_at`` is not timezone-aware.
        """
        if observed_at.tzinfo is None:
            raise ValueError(
                f"{self.name}: observed_at must be timezone-aware (UTC)"
            )
        end = observed_at + (self.interval or timedelta(0))
        return end + self.publication_lag


@dataclass(frozen=True)
class FeatureValue:
    """One feature resolved at a query instant.

    Attributes:
        name: The feature name.
        value: The resolved value, or None when nothing was knowable yet.
        observed_at: Timestamp the channel attached to the observation, or None.
        knowable_at: When the value became legitimate to use, or None.
        asked_at: The query instant this value was resolved for.
    """

    name: str
    value: float | bool | None
    observed_at: datetime | None
    knowable_at: datetime | None
    asked_at: datetime

    @property
    def is_missing(self) -> bool:
        """Return True when no value was knowable at the query instant."""
        return self.value is None

    @property
    def staleness(self) -> timedelta | None:
        """Return how old the value already was when queried.

        Returns:
            ``asked_at - knowable_at``, or None if the value is missing. Large
            staleness is not an error -- a daily feature queried hourly is
            legitimately up to a day stale -- but it is worth surfacing, because
            a feature that is always very stale is usually not carrying the
            information its name implies.
        """
        if self.knowable_at is None:
            return None
        return self.asked_at - self.knowable_at
