"""Rate limiting for state-mutating API endpoints.

Bounds how fast the API will accept requests that change system state. The
threat this addresses is named in ``SECURITY.md``: a leaked ``PARAVANT_API_KEY``
could otherwise be used as fast as the process will serve it.

Two independent buckets, doing two different jobs:

- **Per-identity** -- fairness. Stops the realistic case (one script hammering)
  without letting one bad client deny service to everyone. Client identity is
  derived from ``X-Forwarded-For``, which is client-supplied and therefore
  spoofable, so this bucket is best-effort by construction.
- **Global** -- the actual cap. It trusts no client-supplied value, so it cannot
  be evaded by rotating a header. This is what bounds total damage.

Reuses ``TokenBucket`` from the Binance adapter (DEC-2026-02-10-002) rather than
adding a dependency. It does **not** reuse ``RateLimiter`` from that module: see
``RateLimitMiddleware`` for why blocking is the wrong policy inbound.

Decision: DEC-2026-08-14-003 - Rate limiting on state-mutating endpoints
Decision: DEC-2026-02-10-002 - Token bucket algorithm (primitive reused here)
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import math
import os
from collections import OrderedDict
from typing import Final

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from src.api.auth import MUTATING_METHODS
from src.brokers.binance.rate_limiter import TokenBucket
from src.utils.logging import get_logger

logger = get_logger(__name__)

#: Per-client allowance, requests per minute. A human operator clicking buttons
#: never approaches this; a script exceeds it in seconds. Generous on purpose --
#: the operator must never be rate-limited out of their own kill switch.
PER_CLIENT_LIMIT_ENV: Final[str] = "API_RATE_LIMIT_PER_MINUTE"
DEFAULT_PER_CLIENT_LIMIT: Final[int] = 30

#: Global allowance across all clients, requests per minute. The un-evadable cap.
GLOBAL_LIMIT_ENV: Final[str] = "API_RATE_LIMIT_GLOBAL_PER_MINUTE"
DEFAULT_GLOBAL_LIMIT: Final[int] = 120

#: Upper bound on tracked client identities. ``X-Forwarded-For`` is attacker
#: controlled, so an unbounded map would be a memory-exhaustion vector: send
#: requests with a million distinct values and the dict grows without limit.
#: Least-recently-seen entries are evicted past this point.
MAX_TRACKED_CLIENTS: Final[int] = 1024

#: Cap on a stored identity string, so one request cannot store a large key.
MAX_IDENTITY_LENGTH: Final[int] = 64

_SECONDS_PER_MINUTE: Final[float] = 60.0


def _read_limit(env_var: str, default: int) -> int:
    """Read a per-minute limit from the environment.

    Args:
        env_var: Variable name to read.
        default: Value used when unset, empty, or unparseable.

    Returns:
        The configured limit. Zero or negative disables that bucket. An
        unparseable value falls back to the default rather than raising -- a
        malformed limit must not take the API down, and the fallback is the
        safe direction because it applies a limit rather than removing one.
    """
    raw = os.getenv(env_var)
    if raw is None or not raw.strip():
        return default

    try:
        return int(raw.strip())
    except ValueError:
        logger.warning(
            "rate_limit_config_invalid",
            env_var=env_var,
            value=raw,
            fallback=default,
        )
        return default


def client_identity(request: Request) -> str:
    """Derive a stable-ish identity for the requesting client.

    Prefers the leftmost ``X-Forwarded-For`` entry, which is the original client
    when the app sits behind a proxy such as Railway. Falls back to the direct
    peer address.

    This value is **not trustworthy**. ``X-Forwarded-For`` is set by the client
    and nothing here can verify it. It is good enough for fairness between
    well-behaved clients and useless against a determined attacker, which is
    exactly why the global bucket exists and does not use this.

    Args:
        request: Incoming HTTP request.

    Returns:
        An identity string, truncated to :data:`MAX_IDENTITY_LENGTH`.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:MAX_IDENTITY_LENGTH]

    if request.client is not None:
        return request.client.host[:MAX_IDENTITY_LENGTH]

    return "unknown"


def _retry_after_seconds(bucket: TokenBucket) -> int:
    """Seconds until the bucket can serve one more request.

    Args:
        bucket: The bucket that refused the request.

    Returns:
        A whole number of seconds, at least 1, rounded up so the client does not
        retry fractionally early and get refused again.
    """
    if bucket.refill_rate <= 0:
        return 1

    deficit = 1.0 - bucket.available_tokens
    if deficit <= 0:
        return 1

    return max(1, math.ceil(deficit / bucket.refill_rate))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject state-mutating requests that exceed the configured rate.

    **Why reject rather than wait.** ``RateLimiter`` in
    ``src/brokers/binance/rate_limiter.py`` blocks with ``asyncio.sleep`` until
    tokens are available. That is right for outbound calls to Binance, where
    waiting beats being banned. It is wrong inbound: a held request occupies a
    connection and a coroutine, so blocking would let 10,000 requests become
    10,000 sleeping tasks and turn the rate limiter into a DoS amplifier. Only
    the ``TokenBucket`` primitive is shared; the policy is inverted.

    **Why gate on HTTP method.** Same reasoning as ``ApiKeyAuthMiddleware``: a
    mutating endpoint added later is covered on the day it is written, rather
    than depending on an author remembering to decorate it.

    **Why this sits inside the auth middleware.** Unauthenticated requests are
    rejected by ``ApiKeyAuthMiddleware`` before reaching here, so a flood from
    someone without a key costs a cheap 401 and consumes no rate budget. Placed
    outside auth, an anonymous flood could exhaust the global bucket and lock
    the operator out of their own kill switch.

    **Concurrency.** Bucket reads and writes happen without an intervening
    ``await``, so under a single-threaded event loop they are atomic and no lock
    is needed. Adding an ``await`` inside the critical section below would break
    that property.

    **Scope.** State lives in process memory. Running multiple uvicorn workers
    multiplies the effective limits by the worker count; the deployment runs a
    single worker. A restart resets all buckets, which is acceptable -- this
    bounds a burst, it is not an audit trail.
    """

    def __init__(self, app: object) -> None:
        """Initialise buckets from the environment.

        Args:
            app: The ASGI application being wrapped.
        """
        super().__init__(app)  # type: ignore[arg-type]

        self._per_client_limit = _read_limit(
            PER_CLIENT_LIMIT_ENV, DEFAULT_PER_CLIENT_LIMIT
        )
        self._global_limit = _read_limit(GLOBAL_LIMIT_ENV, DEFAULT_GLOBAL_LIMIT)

        # OrderedDict used as an LRU: touched entries move to the end, and
        # evictions come off the front.
        self._client_buckets: OrderedDict[str, TokenBucket] = OrderedDict()

        self._global_bucket: TokenBucket | None = None
        if self._global_limit > 0:
            self._global_bucket = TokenBucket(
                capacity=float(self._global_limit),
                refill_rate=self._global_limit / _SECONDS_PER_MINUTE,
            )

        self._rejections: int = 0

        logger.info(
            "rate_limit_configured",
            per_client_per_minute=self._per_client_limit,
            global_per_minute=self._global_limit,
            per_client_enabled=self._per_client_limit > 0,
            global_enabled=self._global_limit > 0,
            guarded_methods=sorted(MUTATING_METHODS),
        )

    def _bucket_for(self, identity: str) -> TokenBucket:
        """Return the bucket for a client, creating and evicting as needed.

        Args:
            identity: Client identity from :func:`client_identity`.

        Returns:
            The client's token bucket.
        """
        bucket = self._client_buckets.get(identity)
        if bucket is None:
            bucket = TokenBucket(
                capacity=float(self._per_client_limit),
                refill_rate=self._per_client_limit / _SECONDS_PER_MINUTE,
            )
            self._client_buckets[identity] = bucket

            # Evict least-recently-seen entries. Evicting a bucket resets that
            # client's allowance, which is a deliberate trade: bounded memory
            # matters more than perfect accounting for a client that has been
            # idle longer than 1023 other clients.
            while len(self._client_buckets) > MAX_TRACKED_CLIENTS:
                self._client_buckets.popitem(last=False)
        else:
            self._client_buckets.move_to_end(identity)

        return bucket

    def _too_many_requests(
        self, scope: str, identity: str, retry_after: int
    ) -> JSONResponse:
        """Build the 429 response.

        Args:
            scope: Which bucket refused -- ``per_client`` or ``global``.
            identity: Client identity, recorded in the log only.
            retry_after: Seconds the client should wait.

        Returns:
            A 429 JSONResponse carrying a ``Retry-After`` header.
        """
        self._rejections += 1
        logger.warning(
            "rate_limit_rejected",
            scope=scope,
            client=identity,
            retry_after_seconds=retry_after,
            total_rejections=self._rejections,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": (
                    "Rate limit exceeded for state-mutating requests. "
                    f"Retry in {retry_after}s."
                )
            },
            headers={"Retry-After": str(retry_after)},
        )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Apply rate limits to state-mutating requests.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in the chain.

        Returns:
            The downstream response, or 429 when a bucket is exhausted.
        """
        if request.method not in MUTATING_METHODS:
            return await call_next(request)

        identity = client_identity(request)

        # Per-client first: a single noisy client should be told so, rather than
        # being reported as global saturation it did not cause.
        if self._per_client_limit > 0:
            bucket = self._bucket_for(identity)
            if not bucket.try_consume(1.0):
                return self._too_many_requests(
                    "per_client", identity, _retry_after_seconds(bucket)
                )

        if self._global_bucket is not None:
            if not self._global_bucket.try_consume(1.0):
                return self._too_many_requests(
                    "global", identity, _retry_after_seconds(self._global_bucket)
                )

        return await call_next(request)
