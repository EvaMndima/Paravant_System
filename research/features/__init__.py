"""Point-in-time feature store for the research layer.

Resolves named features "as of" an instant and refuses to return anything that
was not knowable then. See ``research/features/store.py`` for the guarantee and
``research/features/audit.py`` for the two leakage checks.
"""

from research.features.audit import (  # noqa: F401
    LeakageFinding,
    LeakageReport,
    audit_future_invariance,
    audit_knowability,
    render_reports,
)
from research.features.spec import (  # noqa: F401
    FeatureKind,
    FeatureSpec,
    FeatureValue,
)
from research.features.store import (  # noqa: F401
    FeatureMatrix,
    LeakageError,
    Observation,
    PointInTimeFeatureStore,
    Resolver,
)

__all__ = [
    "FeatureKind",
    "FeatureSpec",
    "FeatureValue",
    "FeatureMatrix",
    "LeakageError",
    "LeakageFinding",
    "LeakageReport",
    "Observation",
    "PointInTimeFeatureStore",
    "Resolver",
    "audit_future_invariance",
    "audit_knowability",
    "render_reports",
]
