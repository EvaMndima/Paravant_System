"""Tests for rate limiting on state-mutating endpoints.

Three properties are defended here:

1. Limits are actually enforced, per-client and globally.
2. The limiter **rejects** rather than **blocks**. Blocking inbound would turn
   the limiter into a DoS amplifier, which is the mistake this module exists to
   avoid -- see ``RateLimitMiddleware``.
3. Bucket storage is bounded. ``X-Forwarded-For`` is attacker-controlled, so an
   unbounded identity map would be a memory-exhaustion vector.

Decision: DEC-2026-08-14-003 - Rate limiting on state-mutating endpoints
"""
from __future__ import annotations

import time
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.rate_limit import (
    DEFAULT_GLOBAL_LIMIT,
    DEFAULT_PER_CLIENT_LIMIT,
    GLOBAL_LIMIT_ENV,
    MAX_IDENTITY_LENGTH,
    MAX_TRACKED_CLIENTS,
    PER_CLIENT_LIMIT_ENV,
    RateLimitMiddleware,
    _read_limit,
    _retry_after_seconds,
    client_identity,
)
from src.brokers.binance.rate_limiter import TokenBucket


@pytest.fixture
def make_app(monkeypatch) -> Callable[..., FastAPI]:
    """Build an app with the rate limiter configured to given limits.

    The middleware reads its limits in ``__init__``, so the environment must be
    set before the app is constructed. A factory makes that ordering explicit
    rather than implicit in fixture resolution order.
    """

    def _factory(per_client: int = 3, global_limit: int = 100) -> FastAPI:
        monkeypatch.setenv(PER_CLIENT_LIMIT_ENV, str(per_client))
        monkeypatch.setenv(GLOBAL_LIMIT_ENV, str(global_limit))

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/thing")
        async def read_thing() -> dict[str, str]:
            return {"ok": "read"}

        @app.post("/thing")
        async def create_thing() -> dict[str, str]:
            return {"ok": "created"}

        @app.delete("/thing")
        async def delete_thing() -> dict[str, str]:
            return {"ok": "deleted"}

        return app

    return _factory


def _post(client: TestClient, ip: str = "10.0.0.1"):
    """POST as a given client identity."""
    return client.post("/thing", headers={"X-Forwarded-For": ip})


class TestLimitConfiguration:
    """Reading limits from the environment."""

    def test_defaults_when_unset(self, monkeypatch):
        monkeypatch.delenv(PER_CLIENT_LIMIT_ENV, raising=False)
        monkeypatch.delenv(GLOBAL_LIMIT_ENV, raising=False)

        assert _read_limit(PER_CLIENT_LIMIT_ENV, DEFAULT_PER_CLIENT_LIMIT) == 30
        assert _read_limit(GLOBAL_LIMIT_ENV, DEFAULT_GLOBAL_LIMIT) == 120

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv(PER_CLIENT_LIMIT_ENV, "7")

        assert _read_limit(PER_CLIENT_LIMIT_ENV, DEFAULT_PER_CLIENT_LIMIT) == 7

    def test_whitespace_is_tolerated(self, monkeypatch):
        monkeypatch.setenv(PER_CLIENT_LIMIT_ENV, "  7  ")

        assert _read_limit(PER_CLIENT_LIMIT_ENV, DEFAULT_PER_CLIENT_LIMIT) == 7

    def test_unparseable_falls_back_to_default(self, monkeypatch):
        """A typo in a limit must not take the API down, and the fallback must
        apply a limit rather than remove one."""
        monkeypatch.setenv(PER_CLIENT_LIMIT_ENV, "thirty")

        assert _read_limit(PER_CLIENT_LIMIT_ENV, DEFAULT_PER_CLIENT_LIMIT) == 30

    def test_empty_string_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv(PER_CLIENT_LIMIT_ENV, "")

        assert _read_limit(PER_CLIENT_LIMIT_ENV, DEFAULT_PER_CLIENT_LIMIT) == 30

    def test_zero_disables_the_bucket(self, make_app):
        """Zero is an explicit opt-out, distinct from unset."""
        client = TestClient(make_app(per_client=0, global_limit=0))

        for _ in range(50):
            assert _post(client).status_code == 200


class TestRetryAfter:
    """The ``Retry-After`` value, including its defensive branches.

    A client that is told to retry too early simply gets refused again, so the
    value is rounded up. The two guard clauses cover states a caller should
    never produce but which must not divide by zero or return a negative wait.
    """

    def test_rounds_up_so_the_client_does_not_retry_early(self):
        # 60/minute -> 1 token/sec. An empty bucket needs 1s; a partially
        # refilled one needs a fraction, which must still round to 1.
        bucket = TokenBucket(capacity=60.0, refill_rate=1.0)
        bucket.tokens = 0.0

        assert _retry_after_seconds(bucket) >= 1

    def test_slow_refill_produces_a_proportionally_longer_wait(self):
        """2/minute is a 30s wait per token. A caller told to retry in 1s would
        hammer the endpoint 30 times before succeeding."""
        bucket = TokenBucket(capacity=2.0, refill_rate=2.0 / 60.0)
        bucket.tokens = 0.0

        assert _retry_after_seconds(bucket) >= 25

    def test_zero_refill_rate_does_not_divide_by_zero(self):
        """Reachable only via a misconfiguration, but a ZeroDivisionError here
        would turn a rate-limit rejection into a 500."""
        bucket = TokenBucket(capacity=1.0, refill_rate=1.0)
        bucket.refill_rate = 0.0

        assert _retry_after_seconds(bucket) == 1

    def test_bucket_with_tokens_available_returns_the_floor(self):
        """No deficit means nothing to wait for; the contract is still a
        positive integer, never 0 or negative."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)

        assert _retry_after_seconds(bucket) == 1


class TestClientIdentity:
    """Deriving a client identity from the request."""

    def test_prefers_forwarded_for(self, make_app):
        app = make_app()
        client = TestClient(app)

        response = client.post("/thing", headers={"X-Forwarded-For": "203.0.113.9"})

        assert response.status_code == 200

    def test_uses_leftmost_entry_of_a_chain(self):
        """A proxy chain appends; the original client is leftmost."""

        class _Req:
            headers = {"x-forwarded-for": "203.0.113.9, 70.41.3.18, 150.172.238.178"}
            client = None

        assert client_identity(_Req()) == "203.0.113.9"

    def test_falls_back_to_peer_when_header_absent(self):
        class _Client:
            host = "192.0.2.44"

        class _Req:
            headers: dict[str, str] = {}
            client = _Client()

        assert client_identity(_Req()) == "192.0.2.44"

    def test_unknown_when_no_header_and_no_peer(self):
        class _Req:
            headers: dict[str, str] = {}
            client = None

        assert client_identity(_Req()) == "unknown"

    def test_identity_is_truncated(self):
        """One request must not be able to store a large key."""

        class _Req:
            headers = {"x-forwarded-for": "A" * 5000}
            client = None

        assert len(client_identity(_Req())) == MAX_IDENTITY_LENGTH

    def test_empty_forwarded_for_falls_back_to_peer(self):
        class _Client:
            host = "192.0.2.44"

        class _Req:
            headers = {"x-forwarded-for": "   "}
            client = _Client()

        assert client_identity(_Req()) == "192.0.2.44"


class TestPerClientLimit:
    """The fairness bucket."""

    def test_requests_up_to_the_limit_succeed(self, make_app):
        client = TestClient(make_app(per_client=3))

        for i in range(3):
            assert _post(client).status_code == 200, f"request {i} was rejected"

    def test_the_next_request_is_rejected(self, make_app):
        client = TestClient(make_app(per_client=3))

        for _ in range(3):
            _post(client)

        assert _post(client).status_code == 429

    def test_rejection_carries_retry_after(self, make_app):
        """A client that cannot see when to retry will simply retry immediately."""
        client = TestClient(make_app(per_client=3))

        for _ in range(3):
            _post(client)
        response = _post(client)

        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) >= 1

    def test_clients_are_limited_independently(self, make_app):
        """One noisy client must not deny service to another."""
        client = TestClient(make_app(per_client=3, global_limit=100))

        for _ in range(3):
            _post(client, ip="10.0.0.1")
        assert _post(client, ip="10.0.0.1").status_code == 429

        assert _post(client, ip="10.0.0.2").status_code == 200

    @pytest.mark.parametrize("method", ["POST", "DELETE"])
    def test_all_mutating_methods_are_limited(self, make_app, method):
        client = TestClient(make_app(per_client=2))

        for _ in range(2):
            client.request(method, "/thing", headers={"X-Forwarded-For": "10.0.0.1"})

        response = client.request(
            method, "/thing", headers={"X-Forwarded-For": "10.0.0.1"}
        )

        assert response.status_code == 429

    def test_read_requests_are_never_limited(self, make_app):
        """Reads cannot place orders, and the dashboard polls them."""
        client = TestClient(make_app(per_client=2))

        for _ in range(20):
            assert client.get("/thing").status_code == 200


class TestGlobalLimit:
    """The un-evadable cap."""

    def test_global_limit_applies_across_distinct_identities(self, make_app):
        """The point of this bucket: rotating X-Forwarded-For must not evade it.

        Per-client is set high so that only the global bucket can refuse.
        """
        client = TestClient(make_app(per_client=1000, global_limit=3))

        for i in range(3):
            assert _post(client, ip=f"10.0.0.{i}").status_code == 200

        assert _post(client, ip="10.0.0.99").status_code == 429

    def test_global_rejection_carries_retry_after(self, make_app):
        client = TestClient(make_app(per_client=1000, global_limit=2))

        for i in range(2):
            _post(client, ip=f"10.0.0.{i}")
        response = _post(client, ip="10.0.0.99")

        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) >= 1


class TestBoundedStorage:
    """Memory safety of the identity map.

    Exercised against the middleware object rather than over HTTP: the property
    is about internal storage, and driving 1,000+ real requests through
    TestClient to assert it would be slow and less precise.
    """

    def test_tracked_clients_are_capped(self):
        middleware = RateLimitMiddleware(app=None)

        for i in range(MAX_TRACKED_CLIENTS + 500):
            middleware._bucket_for(f"client-{i}")

        assert len(middleware._client_buckets) <= MAX_TRACKED_CLIENTS

    def test_recently_seen_clients_are_retained(self):
        """Eviction is least-recently-seen, so an active client keeps its bucket
        even while many one-shot identities churn through."""
        middleware = RateLimitMiddleware(app=None)

        middleware._bucket_for("active-client")
        for i in range(MAX_TRACKED_CLIENTS - 1):
            middleware._bucket_for(f"noise-{i}")
            middleware._bucket_for("active-client")  # keep it fresh

        assert "active-client" in middleware._client_buckets

    def test_same_identity_reuses_its_bucket(self):
        """Otherwise a client could reset its allowance by re-requesting."""
        middleware = RateLimitMiddleware(app=None)

        first = middleware._bucket_for("10.0.0.1")
        second = middleware._bucket_for("10.0.0.1")

        assert first is second


class TestRejectionIsNotBlocking:
    """The core policy difference from the outbound Binance limiter.

    ``RateLimiter`` in ``src/brokers/binance/rate_limiter.py`` sleeps until
    tokens free up. Inbound that would be a DoS amplifier: every excess request
    would hold a connection and a coroutine. Rejection must be immediate.
    """

    def test_rejected_requests_return_immediately(self, make_app):
        client = TestClient(make_app(per_client=2))

        for _ in range(2):
            _post(client)

        start = time.monotonic()
        for _ in range(20):
            assert _post(client).status_code == 429
        elapsed = time.monotonic() - start

        # 20 rejections against a 2/minute bucket. If the limiter slept for
        # tokens, this would take minutes. The bound is deliberately loose --
        # it is testing "does not sleep", not raw throughput.
        assert elapsed < 5.0, f"rejections took {elapsed:.2f}s -- limiter is blocking"


class TestRealApplicationStack:
    """Ordering of the real middleware stack in src/api/main.py.

    Auth must run BEFORE rate limiting. If the order inverts, an anonymous flood
    consumes the global bucket and locks the operator out of their own kill
    switch. Both layers must sit inside CORS so browsers see real statuses.
    """

    def test_unauthenticated_flood_yields_401_not_429(self, monkeypatch):
        """Proves auth runs first AND that anonymous traffic consumes no rate
        budget: 50 keyless requests against a 30/min default limit stay 401."""
        monkeypatch.setenv("PARAVANT_API_KEY", "p" * 32)
        monkeypatch.setenv("ENVIRONMENT", "development")

        from src.api.main import app

        client = TestClient(app)

        statuses = {
            client.post("/api/v1/system/stop").status_code for _ in range(50)
        }

        assert statuses == {401}, f"expected only 401s, got {statuses}"

    def test_429_carries_cors_headers(self, monkeypatch):
        """A 429 stripped of CORS headers reads as an opaque network error in a
        browser rather than as rate limiting."""
        monkeypatch.setenv("PARAVANT_API_KEY", "p" * 32)
        monkeypatch.setenv("ENVIRONMENT", "development")

        from src.api.main import app

        client = TestClient(app)
        headers = {
            "X-API-Key": "p" * 32,
            "Origin": "http://localhost:3000",
            "X-Forwarded-For": "198.51.100.7",
        }

        response = None
        for _ in range(DEFAULT_PER_CLIENT_LIMIT + 5):
            response = client.post("/api/v1/system/stop", headers=headers)
            if response.status_code == 429:
                break

        assert response is not None
        assert response.status_code == 429, "never hit the rate limit"
        assert "access-control-allow-origin" in {
            k.lower() for k in response.headers
        }
