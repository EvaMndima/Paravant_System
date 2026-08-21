"""Tests for the API key gate on state-mutating endpoints.

The contract these tests defend is not "the middleware works" but "no mutating
endpoint can ship unauthenticated". ``TestMutatingRouteCoverage`` enumerates
every route registered on the real application and asserts the property holds
for all of them, so adding an unguarded mutating endpoint is a test failure
rather than a silent exposure.

Decision: DEC-2026-08-14-001 - Static API key on state-mutating endpoints
"""
from __future__ import annotations

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.auth import (
    API_KEY_ENV_VAR,
    API_KEY_HEADER,
    MIN_API_KEY_LENGTH,
    MUTATING_METHODS,
    ApiKeyAuthMiddleware,
    get_configured_api_key,
    validate_api_key_config,
)
from src.core.exceptions import ConfigurationError

# A key at exactly the minimum accepted length.
VALID_KEY = "p" * MIN_API_KEY_LENGTH

# Path parameter placeholders are substituted with this before the request is
# made. The value never reaches a route handler -- middleware runs before
# routing, so the 401 is returned whether or not the path resolves.
_PATH_PARAM = re.compile(r"\{[^}]+\}")


@pytest.fixture
def app_with_auth() -> FastAPI:
    """Minimal app carrying only the auth middleware.

    Isolates the middleware from application startup, database initialisation
    and route dependencies, so a failure here is unambiguously an auth failure.
    """
    app = FastAPI()
    app.add_middleware(ApiKeyAuthMiddleware)

    @app.get("/thing")
    async def read_thing() -> dict[str, str]:
        return {"ok": "read"}

    @app.post("/thing")
    async def create_thing() -> dict[str, str]:
        return {"ok": "created"}

    @app.put("/thing")
    async def replace_thing() -> dict[str, str]:
        return {"ok": "replaced"}

    @app.patch("/thing")
    async def update_thing() -> dict[str, str]:
        return {"ok": "updated"}

    @app.delete("/thing")
    async def remove_thing() -> dict[str, str]:
        return {"ok": "deleted"}

    return app


class TestConfigValidation:
    """Startup-time validation of the configured key."""

    def test_missing_key_in_development_is_allowed(self, monkeypatch):
        """A new contributor running the documented quickstart must not be
        blocked by a secret they have not been told to create."""
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")

        validate_api_key_config()  # must not raise

    def test_missing_key_outside_development_aborts_startup(self, monkeypatch):
        """The failure mode this module exists to prevent: an order-placing
        API deployed with no authentication."""
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")

        with pytest.raises(ConfigurationError) as exc_info:
            validate_api_key_config()

        assert exc_info.value.code == "API_KEY_MISSING"

    def test_staging_is_treated_as_non_development(self, monkeypatch):
        """Only ``development`` relaxes the requirement. Anything else is
        treated as capable of reaching real money."""
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        monkeypatch.setenv("ENVIRONMENT", "staging")

        with pytest.raises(ConfigurationError):
            validate_api_key_config()

    @pytest.mark.parametrize("environment", ["development", "production"])
    def test_short_key_rejected_in_every_environment(self, monkeypatch, environment):
        """A weak key is worse than no key: it produces the appearance of
        protection. It is rejected even in development."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "x" * (MIN_API_KEY_LENGTH - 1))
        monkeypatch.setenv("ENVIRONMENT", environment)

        with pytest.raises(ConfigurationError) as exc_info:
            validate_api_key_config()

        assert exc_info.value.code == "API_KEY_TOO_SHORT"

    def test_valid_key_accepted(self, monkeypatch):
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        monkeypatch.setenv("ENVIRONMENT", "production")

        validate_api_key_config()  # must not raise

    def test_whitespace_only_key_is_treated_as_unset(self, monkeypatch):
        """``PARAVANT_API_KEY="   "`` is a configuration mistake, not a
        secret, and must not be accepted as one."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "   ")

        assert get_configured_api_key() is None

    def test_surrounding_whitespace_is_stripped(self, monkeypatch):
        """A trailing newline from ``export KEY=$(cat file)`` must not cause a
        mismatch that is invisible in logs."""
        monkeypatch.setenv(API_KEY_ENV_VAR, f"  {VALID_KEY}\n")

        assert get_configured_api_key() == VALID_KEY


class TestMiddlewareEnforcement:
    """Per-request behaviour of the gate."""

    def test_read_requests_are_not_gated(self, app_with_auth, monkeypatch):
        """The dashboard is read-only; gating GET would break the browser
        client for no safety gain."""
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        client = TestClient(app_with_auth)

        response = client.get("/thing")

        assert response.status_code == 200

    @pytest.mark.parametrize("method", sorted(MUTATING_METHODS))
    def test_mutating_request_without_key_is_rejected(
        self, app_with_auth, monkeypatch, method
    ):
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        client = TestClient(app_with_auth)

        response = client.request(method, "/thing")

        assert response.status_code == 401

    @pytest.mark.parametrize("method", sorted(MUTATING_METHODS))
    def test_mutating_request_with_correct_key_is_allowed(
        self, app_with_auth, monkeypatch, method
    ):
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        client = TestClient(app_with_auth)

        response = client.request(
            method, "/thing", headers={API_KEY_HEADER: VALID_KEY}
        )

        assert response.status_code == 200

    def test_incorrect_key_is_rejected(self, app_with_auth, monkeypatch):
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        client = TestClient(app_with_auth)

        response = client.post("/thing", headers={API_KEY_HEADER: "q" * 32})

        assert response.status_code == 401

    def test_key_comparison_is_not_a_prefix_match(self, app_with_auth, monkeypatch):
        """Guards against a substring or ``startswith`` comparison creeping in
        during a future refactor."""
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        client = TestClient(app_with_auth)

        response = client.post("/thing", headers={API_KEY_HEADER: VALID_KEY[:-1]})

        assert response.status_code == 401

    def test_rejection_body_does_not_distinguish_missing_from_invalid(
        self, app_with_auth, monkeypatch
    ):
        """Telling an attacker whether a key was absent or merely wrong is
        information they do not otherwise have. The distinction stays in the
        log, not the response."""
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        client = TestClient(app_with_auth)

        missing = client.post("/thing")
        invalid = client.post("/thing", headers={API_KEY_HEADER: "q" * 32})

        assert missing.status_code == invalid.status_code == 401
        assert missing.json() == invalid.json()

    def test_gate_is_disabled_when_no_key_configured(
        self, app_with_auth, monkeypatch
    ):
        """Development convenience path. Reaching here outside development is
        impossible: validate_api_key_config() aborts startup first."""
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        client = TestClient(app_with_auth)

        response = client.post("/thing")

        assert response.status_code == 200

    def test_options_is_never_gated(self, app_with_auth, monkeypatch):
        """CORS preflight must succeed without a key. If it does not, the
        browser never sends the real request and the failure surfaces as an
        opaque CORS error rather than a 401."""
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)

        assert "OPTIONS" not in MUTATING_METHODS

        client = TestClient(app_with_auth)
        response = client.options("/thing")

        assert response.status_code != 401


class TestMutatingRouteCoverage:
    """The contract test: no mutating endpoint on the real app is unguarded.

    This is what makes method-based middleware safe to rely on. A per-route
    dependency would be fail-open -- protection would depend on the author of
    every future endpoint remembering it. Here, forgetting is a test failure.
    """

    @staticmethod
    def _mutating_routes() -> list[tuple[str, str]]:
        """Enumerate (method, concrete path) for every mutating route.

        Path parameters are replaced with a placeholder. The value is never
        used: middleware runs before routing, so the 401 does not depend on
        the path resolving to a handler.
        """
        from fastapi.routing import iter_route_contexts
        from src.api.main import app

        found: list[tuple[str, str]] = []
        for context in iter_route_contexts(app.routes):
            path = context.path
            methods = context.methods or set()

            if not path.startswith("/api/v1"):
                continue

            for method in sorted(set(methods) & MUTATING_METHODS):
                found.append((method, _PATH_PARAM.sub("test-id", path)))

        return found

    def test_the_app_actually_has_mutating_routes(self):
        """Guards the suite itself: if route registration changes shape and
        the enumeration silently returns nothing, every parametrised case below
        would vacuously pass."""
        # Floor lowered from 20 to 18 on 2026-08-21: /system/start and
        # /system/stop were removed (DEC-2026-08-21-008), taking the count from
        # 21 to 19. The floor sits just under the real count so it catches an
        # enumeration that silently returns nothing, without breaking on every
        # deliberate route change.
        assert len(self._mutating_routes()) >= 18

    def test_every_mutating_route_rejects_an_unauthenticated_request(
        self, monkeypatch
    ):
        """The property under test, asserted across all routes at once so the
        failure message names every offender rather than the first."""
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        monkeypatch.setenv("ENVIRONMENT", "development")

        from src.api.main import app

        # No context manager: the lifespan startup initialises the database and
        # event bus, which this test does not need and must not depend on.
        client = TestClient(app)

        unguarded = [
            f"{method} {path}"
            for method, path in self._mutating_routes()
            if client.request(method, path).status_code != 401
        ]

        assert not unguarded, (
            "These state-mutating routes are reachable without an API key: "
            f"{unguarded}"
        )

    def test_read_routes_remain_open(self, monkeypatch):
        """The gate must not have quietly become an app-wide requirement --
        that would break the read-only dashboard."""
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        monkeypatch.setenv("ENVIRONMENT", "development")

        from src.api.main import app

        client = TestClient(app)

        assert client.get("/health").status_code == 200


class TestStartupWiring:
    """`validate_api_key_config` must actually be CALLED by the application.

    Without this, the function could be 100% covered by its own unit tests while
    the line invoking it in `main.py` was deleted, and nothing would fail. The
    unit tests prove the validator is correct; this proves it runs.
    """

    def test_startup_aborts_outside_development_without_a_key(self, monkeypatch):
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")

        from src.api.main import app

        # Entering the context manager runs the lifespan startup event.
        # validate_api_key_config() is called early in that handler, before the
        # event bus and DataStore are built, so this raises before any I/O.
        with pytest.raises(ConfigurationError) as exc_info:  # noqa: PT012
            with TestClient(app):
                pass

        assert exc_info.value.code == "API_KEY_MISSING"

    def test_startup_succeeds_in_development_without_a_key(self, monkeypatch):
        """The documented quickstart path must keep working."""
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")

        from src.api.main import app

        with TestClient(app) as client:
            assert client.get("/health").status_code == 200


class TestMiddlewareOrdering:
    """Ordering regression guard.

    Starlette makes the last-added middleware outermost. If the auth middleware
    is ever moved after ``CORSMiddleware`` in ``main.py`` it will sit outside
    it, and 401 responses will lose their CORS headers -- which a browser
    reports as an opaque network error instead of an authentication failure.
    """

    def test_401_carries_cors_headers(self, monkeypatch):
        monkeypatch.setenv(API_KEY_ENV_VAR, VALID_KEY)
        monkeypatch.setenv("ENVIRONMENT", "development")

        from src.api.main import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/orders/",
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == 401
        assert "access-control-allow-origin" in {
            k.lower() for k in response.headers
        }
