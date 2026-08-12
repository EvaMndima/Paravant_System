"""Point-in-time feature store.

Resolves named features "as of" an instant, with one guarantee: a value is
returned only if it was knowable at that instant. The guarantee is enforced
here rather than trusted from each data channel.

Why this exists
---------------
``research/data/`` already holds six channels -- funding rates, ETF flows,
Coinbase prices, BTC thrust, cross-sectional rank, liquidations -- and each one
documents its accessor as causal. They are not wrong to. But causality was a
property each channel implemented for itself, with its own accessor name, its
own timestamp convention, and no shared test. Reviewing them one at a time,
they all look right.

Asking one uniform question of all of them found two that were not: a channel
timestamped its values with the START of the interval that produced them while
the value came from the interval's END, so a query at 10:30 could receive a
price from 11:00.

The store closes that by construction. A resolver must report *when* its value
was observed; the store computes when that observation became knowable from the
feature's declared kind, interval and publication lag, and refuses anything that
was not yet knowable. A channel cannot be causal by assertion here -- it has to
be causal arithmetically.

Scope
-----
This module owns resolution and the point-in-time guarantee. It does NOT own
fetching, caching or transport -- those stay in ``research/data/``. It does not
compute features either; a resolver is a thin adapter over a channel.

Dependency direction is unchanged: ``research/`` may import ``src/``, never the
reverse (DEC-2026-06-04-001).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from research.features.spec import FeatureSpec, FeatureValue
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LeakageError(RuntimeError):
    """Raised when a resolver returns a value that was not yet knowable.

    This is a programming error in the resolver or its channel, not a data
    condition. It fails loudly rather than degrading, because silently dropping
    leaked values would hide exactly the defect this store exists to surface.
    """


@dataclass(frozen=True)
class Observation:
    """A raw value and the timestamp its channel attaches to it.

    Attributes:
        value: The observed value.
        observed_at: The channel's timestamp for the observation. For an
            INTERVAL feature this must be the START of the period, which is what
            makes the store able to work out when the period completed.
    """

    value: float | bool
    observed_at: datetime


class Resolver(Protocol):
    """Adapter from a data channel to a single feature.

    A resolver answers: "what is the most recent observation of this feature at
    or before ``ts``, and when was it observed?" It must NOT attempt to apply
    the publication lag or interval itself -- the store does that from the
    declared spec, so the arithmetic lives in one place and is testable.
    """

    def __call__(self, symbol: str | None, ts: datetime) -> Observation | None:
        """Return the latest observation at or before ``ts``, or None."""
        ...


@dataclass(frozen=True)
class FeatureMatrix:
    """A point-in-time-correct feature matrix, ready for model training.

    Attributes:
        names: Feature names, in column order.
        timestamps: Query instants, in row order.
        rows: One list of values per timestamp, aligned to ``names``. Missing
            values are None rather than imputed -- an imputation decision
            belongs to the model, not the store.
        symbol: The symbol these features were resolved for, if any.
    """

    names: tuple[str, ...]
    timestamps: tuple[datetime, ...]
    rows: tuple[tuple[float | bool | None, ...], ...]
    symbol: str | None

    def __len__(self) -> int:
        """Return the number of rows."""
        return len(self.rows)

    def missing_rate(self) -> dict[str, float]:
        """Return the fraction of missing values per feature.

        Returns:
            Feature name to missing fraction in [0, 1]. Empty if no rows.
            A feature that is mostly missing is usually mis-specified -- its
            history does not cover the query range, or its publication lag
            pushes it beyond every query instant.
        """
        if not self.rows:
            return {name: 0.0 for name in self.names}
        total = len(self.rows)
        return {
            name: sum(1 for row in self.rows if row[i] is None) / total
            for i, name in enumerate(self.names)
        }


class PointInTimeFeatureStore:
    """Registry of features with an enforced point-in-time guarantee.

    Usage:
        store = PointInTimeFeatureStore()
        store.register(spec, resolver)
        values = store.as_of(ts, symbol="BTCUSDT")
        matrix = store.build_matrix(timestamps, symbol="BTCUSDT")
    """

    def __init__(self) -> None:
        """Initialise an empty store."""
        self._specs: dict[str, FeatureSpec] = {}
        self._resolvers: dict[str, Resolver] = {}

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered feature names in registration order."""
        return tuple(self._specs)

    def spec(self, name: str) -> FeatureSpec:
        """Return the spec for ``name``.

        Args:
            name: Registered feature name.

        Returns:
            The registered FeatureSpec.

        Raises:
            KeyError: If the feature is not registered.
        """
        if name not in self._specs:
            raise KeyError(f"feature not registered: {name!r}")
        return self._specs[name]

    def register(self, spec: FeatureSpec, resolver: Resolver) -> None:
        """Register a feature and its resolver.

        Args:
            spec: The feature specification.
            resolver: Adapter returning the latest Observation at or before a
                query instant.

        Raises:
            ValueError: If a feature of the same name is already registered.
                Re-registration is rejected rather than silently overwriting,
                because two definitions of one feature name is how a training
                set and a live path quietly diverge.
        """
        if spec.name in self._specs:
            raise ValueError(f"feature already registered: {spec.name!r}")
        self._specs[spec.name] = spec
        self._resolvers[spec.name] = resolver
        logger.debug(
            "feature_registered",
            feature=spec.name,
            kind=spec.kind.value,
            publication_lag_s=spec.publication_lag.total_seconds(),
            source=spec.source,
        )

    def as_of(
        self,
        ts: datetime,
        *,
        symbol: str | None = None,
        names: Sequence[str] | None = None,
        strict: bool = True,
    ) -> dict[str, FeatureValue]:
        """Resolve features as they were knowable at ``ts``.

        Args:
            ts: Timezone-aware UTC query instant.
            symbol: Symbol to resolve for, if the features are per-symbol.
            names: Subset of features to resolve. Defaults to all registered.
            strict: When True (default) a value that was not yet knowable raises
                LeakageError. When False it is recorded as missing and logged.
                False exists for auditing an untrusted channel without aborting;
                it is not a way to keep using one.

        Returns:
            Feature name to FeatureValue. Features with nothing knowable yet are
            present with ``value=None`` rather than omitted, so callers see a
            stable shape.

        Raises:
            ValueError: If ``ts`` is not timezone-aware.
            KeyError: If a requested feature is not registered.
            LeakageError: In strict mode, if a resolver returns a value whose
                knowable_at is after ``ts``.
        """
        if ts.tzinfo is None:
            raise ValueError("as_of requires a timezone-aware UTC datetime")

        selected = tuple(names) if names is not None else self.names
        for name in selected:
            if name not in self._specs:
                raise KeyError(f"feature not registered: {name!r}")

        resolved: dict[str, FeatureValue] = {}
        for name in selected:
            spec = self._specs[name]
            observation = self._resolvers[name](symbol, ts)

            if observation is None:
                resolved[name] = FeatureValue(
                    name=name,
                    value=None,
                    observed_at=None,
                    knowable_at=None,
                    asked_at=ts,
                )
                continue

            knowable_at = spec.knowable_at(observation.observed_at)
            if knowable_at > ts:
                # The resolver handed back something from the future. Either its
                # channel searched past ts, or the spec's interval / lag is
                # wrong. Both are defects; neither is a data condition.
                message = (
                    f"{name}: value observed at "
                    f"{observation.observed_at.isoformat()} is knowable only from "
                    f"{knowable_at.isoformat()}, which is after the query instant "
                    f"{ts.isoformat()}. "
                    f"kind={spec.kind.value} interval={spec.interval} "
                    f"publication_lag={spec.publication_lag}"
                )
                if strict:
                    raise LeakageError(message)
                logger.warning(
                    "feature_leakage_dropped",
                    feature=name,
                    observed_at=observation.observed_at.isoformat(),
                    knowable_at=knowable_at.isoformat(),
                    asked_at=ts.isoformat(),
                )
                resolved[name] = FeatureValue(
                    name=name,
                    value=None,
                    observed_at=observation.observed_at,
                    knowable_at=knowable_at,
                    asked_at=ts,
                )
                continue

            resolved[name] = FeatureValue(
                name=name,
                value=observation.value,
                observed_at=observation.observed_at,
                knowable_at=knowable_at,
                asked_at=ts,
            )

        return resolved

    def build_matrix(
        self,
        timestamps: Iterable[datetime],
        *,
        symbol: str | None = None,
        names: Sequence[str] | None = None,
        strict: bool = True,
    ) -> FeatureMatrix:
        """Resolve a feature matrix over many instants.

        This is the training-set constructor. Each row is resolved independently
        at its own instant, so a row can only ever contain information that
        existed then -- which is what makes a model trained on this matrix
        evaluable without lookahead.

        Args:
            timestamps: Timezone-aware UTC query instants. Order is preserved.
            symbol: Symbol to resolve for, if the features are per-symbol.
            names: Subset of features. Defaults to all registered.
            strict: Passed through to ``as_of``.

        Returns:
            A FeatureMatrix with one row per timestamp.

        Raises:
            ValueError: If any timestamp is naive.
            LeakageError: In strict mode, on the first leaked value.
        """
        selected = tuple(names) if names is not None else self.names
        stamps = tuple(timestamps)
        rows: list[tuple[float | bool | None, ...]] = []
        for ts in stamps:
            values = self.as_of(ts, symbol=symbol, names=selected, strict=strict)
            rows.append(tuple(values[name].value for name in selected))

        matrix = FeatureMatrix(
            names=selected, timestamps=stamps, rows=tuple(rows), symbol=symbol
        )
        logger.info(
            "feature_matrix_built",
            rows=len(matrix),
            features=len(selected),
            symbol=symbol,
            missing_rate=matrix.missing_rate(),
        )
        return matrix
