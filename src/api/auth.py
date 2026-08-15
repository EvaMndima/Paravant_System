"""API key authentication for state-mutating endpoints.

Guards every request whose HTTP method can change system state
(``POST``/``PUT``/``PATCH``/``DELETE``) behind a shared secret supplied in the
``X-API-Key`` header. Read-only requests are not gated: the dashboard is a
read-only view and gating it would break the browser client for no safety gain.

The gate is applied by HTTP method in middleware rather than by a
``Depends`` on each route. That choice is deliberate and it is the whole point
of this module -- see ``ApiKeyAuthMiddleware`` for the reasoning.

Decision: DEC-2026-08-14-001 - Static API key on state-mutating endpoints
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
"""
from __future__ import annotations

import os
import secrets
from typing import Final

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from src.core.exceptions import ConfigurationError
from src.utils.logging import get_logger

logger = get_logger(__name__)

#: Environment variable holding the shared secret.
API_KEY_ENV_VAR: Final[str] = "PARAVANT_API_KEY"

#: Request header the secret is read from.
API_KEY_HEADER: Final[str] = "X-API-Key"

#: Minimum accepted key length. A short key is worse than no key because it
#: produces the appearance of protection while remaining brute-forceable, so a
#: key below this length is a hard configuration failure, not a warning.
MIN_API_KEY_LENGTH: Final[int] = 32

#: Methods treated as state-mutating. ``OPTIONS`` is deliberately absent: CORS
#: preflight must succeed without a key or the browser never sends the real
#: request and the failure surfaces as an opaque CORS error.
MUTATING_METHODS: Final[frozenset[str]] = frozenset(
    {"POST", "PUT", "PATCH", "DELETE"}
)


def get_configured_api_key() -> str | None:
    """Read the configured API key from the environment.

    Read at call time rather than import time so that tests and a reloading
    server observe changes without re-importing the module.

    Returns:
        The configured key with surrounding whitespace stripped, or None when
        the variable is unset or empty. An all-whitespace value is treated as
        unset -- it is a configuration mistake, not a secret.
    """
    raw = os.getenv(API_KEY_ENV_VAR)
    if raw is None:
        return None

    key = raw.strip()
    return key or None


def is_development() -> bool:
    """Report whether the API is running in the development environment.

    Reads ``ENVIRONMENT`` directly rather than importing ``Settings`` so that
    the auth gate has no import-time dependency on the settings module and
    cannot be disabled by a settings-loading failure.

    Returns:
        True when ``ENVIRONMENT`` is ``development`` (the default when unset).
    """
    return os.getenv("ENVIRONMENT", "development") == "development"


def validate_api_key_config() -> None:
    """Validate API key configuration, raising when it is unsafe.

    Called from the application startup event. The rules are:

    - A key shorter than :data:`MIN_API_KEY_LENGTH` is rejected in every
      environment. Weak secrets create false confidence.
    - Outside development, a missing key is rejected. Deploying an
      order-placing API with no authentication is the failure mode this module
      exists to prevent, and it must be loud rather than silent.
    - In development, a missing key disables the gate and logs a warning. This
      keeps the documented quickstart runnable by a new contributor who has
      copied ``.env.example`` and set nothing else.

    Raises:
        ConfigurationError: When the key is too short, or absent outside
            development.
    """
    key = get_configured_api_key()

    if key is None:
        if is_development():
            logger.warning(
                "api_auth_disabled",
                message=(
                    f"{API_KEY_ENV_VAR} is not set. State-mutating endpoints "
                    f"are UNAUTHENTICATED. This is permitted in development "
                    f"only. Do not expose this API to an untrusted network."
                ),
                environment=os.getenv("ENVIRONMENT", "development"),
            )
            return

        raise ConfigurationError(
            message=(
                f"{API_KEY_ENV_VAR} must be set outside development. "
                f"Refusing to start an unauthenticated trading API."
            ),
            code="API_KEY_MISSING",
            details={"env_var": API_KEY_ENV_VAR},
        )

    if len(key) < MIN_API_KEY_LENGTH:
        raise ConfigurationError(
            message=(
                f"{API_KEY_ENV_VAR} must be at least {MIN_API_KEY_LENGTH} "
                f"characters; got {len(key)}."
            ),
            code="API_KEY_TOO_SHORT",
            details={
                "env_var": API_KEY_ENV_VAR,
                "minimum_length": MIN_API_KEY_LENGTH,
                "actual_length": len(key),
            },
        )

    logger.info(
        "api_auth_enabled",
        header=API_KEY_HEADER,
        guarded_methods=sorted(MUTATING_METHODS),
    )


def _unauthorized(reason: str) -> JSONResponse:
    """Build the 401 response returned for any failed key check.

    The body is intentionally identical for a missing and an incorrect key.
    Distinguishing them tells an attacker whether a supplied key was the wrong
    *value* or the wrong *shape*, which is information they do not otherwise
    have. The distinction is preserved in the log, not in the response.

    Args:
        reason: Machine-readable cause, recorded in the log only.

    Returns:
        A 401 JSONResponse using FastAPI's ``detail`` body convention.
    """
    logger.warning("api_auth_rejected", reason=reason)
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "detail": (
                f"Missing or invalid {API_KEY_HEADER} header. "
                f"State-mutating endpoints require authentication."
            )
        },
    )


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated state-mutating requests.

    Why middleware rather than a ``Depends`` on each mutating route:

    A per-route dependency is the idiomatic FastAPI approach, and it is
    fail-open. Protection depends on the author of every future endpoint
    remembering to add it, and nothing fails when they do not -- the endpoint
    simply ships unauthenticated. For an API that can place orders and toggle
    the kill switch, a control that silently does not apply is worse than an
    absent one, because it is believed to be present.

    Gating by HTTP method is fail-closed: a mutating endpoint added tomorrow is
    covered on the day it is written. ``tests/unit/api/test_auth.py`` enumerates
    ``app.routes`` and asserts the property holds for every registered route, so
    a regression is a test failure rather than a silent exposure.

    The cost is that the requirement does not appear in the OpenAPI schema.
    That is accepted and documented in ``docs/API_CONTRACT.md``.

    This middleware must be added *before* ``CORSMiddleware`` so that it sits
    inside it in the resulting stack. Starlette makes the last-added middleware
    outermost; an auth layer outside CORS returns 401s without CORS headers,
    which a browser reports as an opaque network error rather than as an
    authentication failure.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Check the API key on state-mutating requests.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in the chain.

        Returns:
            The downstream response, or a 401 when the key check fails.
        """
        if request.method not in MUTATING_METHODS:
            return await call_next(request)

        expected = get_configured_api_key()

        # No key configured. validate_api_key_config() has already refused
        # startup outside development, so reaching here means development with
        # the gate deliberately disabled.
        if expected is None:
            return await call_next(request)

        supplied = request.headers.get(API_KEY_HEADER)
        if supplied is None:
            return _unauthorized("missing_header")

        # Constant-time comparison: a short-circuiting == leaks key content
        # through response timing.
        if not secrets.compare_digest(supplied, expected):
            return _unauthorized("invalid_key")

        return await call_next(request)
