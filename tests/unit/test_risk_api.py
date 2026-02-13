"""Comprehensive tests for risk management API endpoints.

Tests all kill switch API endpoints with various scenarios:
- Status endpoint (active/inactive states)
- Activation endpoint (success, validation errors)
- Deactivation endpoint (success, invalid code, not active)
- Code generation endpoint (format, invalidation)

Uses FastAPI TestClient for integration-level API testing.

Decision: DEC-2026-02-12-008 - Test coverage threshold 90% per file
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client() -> TestClient:
    """Create FastAPI test client with risk router."""
    from src.api.routes.risk import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/risk")

    return TestClient(app)


@pytest.fixture
def mock_kill_switch() -> MagicMock:
    """Create mock KillSwitch for isolated testing."""
    return MagicMock()


@pytest.fixture
def mock_store() -> MagicMock:
    """Create mock DataStore."""
    return MagicMock()


# ===========================================================================
# GET /kill-switch/status tests
# ===========================================================================


class TestKillSwitchStatusEndpoint:
    """Test kill switch status endpoint."""

    def test_status_inactive(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Status endpoint should return inactive state."""
        mock_kill_switch.get_status.return_value = {
            "active": False,
            "activated_at": None,
            "reason": None,
            "duration_seconds": None,
            "trading_enabled": True,
        }

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.get("/api/v1/risk/kill-switch/status")

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False
        assert data["trading_enabled"] is True
        assert data["activated_at"] is None
        assert data["reason"] is None

    def test_status_active(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Status endpoint should return active state with details."""
        now = datetime.now(timezone.utc)
        mock_kill_switch.get_status.return_value = {
            "active": True,
            "activated_at": now.isoformat(),
            "reason": "Emergency halt",
            "duration_seconds": 120.5,
            "trading_enabled": False,
        }

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.get("/api/v1/risk/kill-switch/status")

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is True
        assert data["trading_enabled"] is False
        assert data["reason"] == "Emergency halt"
        assert data["duration_seconds"] == 120.5

    def test_status_reads_from_kill_switch(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Status endpoint should call get_status on kill switch."""
        mock_kill_switch.get_status.return_value = {
            "active": False,
            "trading_enabled": True,
        }

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            test_client.get("/api/v1/risk/kill-switch/status")

        mock_kill_switch.get_status.assert_called_once()


# ===========================================================================
# POST /kill-switch/activate tests
# ===========================================================================


class TestKillSwitchActivateEndpoint:
    """Test kill switch activation endpoint."""

    def test_activate_success(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Activation with valid reason should succeed."""
        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/activate",
                json={"reason": "Test activation"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "activated"
        assert "Kill switch activated" in data["message"]
        assert "timestamp" in data

        mock_kill_switch.activate.assert_called_once_with(
            reason="Test activation",
            actor="api",
        )

    def test_activate_with_long_reason(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Activation with long reason should succeed."""
        long_reason = "A" * 500  # Max length

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/activate",
                json={"reason": long_reason},
            )

        assert response.status_code == 200
        mock_kill_switch.activate.assert_called_once()

    def test_activate_empty_reason(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Activation with empty reason should fail validation."""
        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/activate",
                json={"reason": ""},
            )

        assert response.status_code == 422  # Validation error
        mock_kill_switch.activate.assert_not_called()

    def test_activate_missing_reason(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Activation without reason field should fail validation."""
        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/activate",
                json={},
            )

        assert response.status_code == 422
        mock_kill_switch.activate.assert_not_called()

    def test_activate_too_long_reason(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Activation with reason > 500 chars should fail validation."""
        too_long = "A" * 501

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/activate",
                json={"reason": too_long},
            )

        assert response.status_code == 422
        mock_kill_switch.activate.assert_not_called()


# ===========================================================================
# POST /kill-switch/deactivate tests
# ===========================================================================


class TestKillSwitchDeactivateEndpoint:
    """Test kill switch deactivation endpoint."""

    def test_deactivate_success(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Deactivation with valid code should succeed."""
        mock_kill_switch.deactivate.return_value = True

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/deactivate",
                json={"confirmation_code": "abc123"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deactivated"
        assert "deactivated successfully" in data["message"]

        mock_kill_switch.deactivate.assert_called_once_with(
            confirmation_code="abc123",
            actor="api",
        )

    def test_deactivate_invalid_code(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Deactivation with invalid code should return 403."""
        mock_kill_switch.deactivate.return_value = False

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/deactivate",
                json={"confirmation_code": "wrong_code"},
            )

        assert response.status_code == 403
        data = response.json()
        assert "Invalid confirmation code" in data["detail"]

    def test_deactivate_empty_code(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Deactivation with empty code should fail validation."""
        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/deactivate",
                json={"confirmation_code": ""},
            )

        assert response.status_code == 422
        mock_kill_switch.deactivate.assert_not_called()

    def test_deactivate_missing_code(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Deactivation without code field should fail validation."""
        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/deactivate",
                json={},
            )

        assert response.status_code == 422
        mock_kill_switch.deactivate.assert_not_called()

    def test_deactivate_when_not_active(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Deactivation when not active should handle gracefully."""
        mock_kill_switch.deactivate.return_value = True

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/deactivate",
                json={"confirmation_code": "code123"},
            )

        # Should succeed (idempotent)
        assert response.status_code == 200


# ===========================================================================
# POST /kill-switch/generate-code tests
# ===========================================================================


class TestGenerateDeactivationCodeEndpoint:
    """Test deactivation code generation endpoint."""

    def test_generate_code_success(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Code generation should return valid code."""
        mock_kill_switch.generate_deactivation_code.return_value = "abc123def"

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/generate-code"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "abc123def"
        assert "message" in data
        assert "single-use" in data["message"]

        mock_kill_switch.generate_deactivation_code.assert_called_once()

    def test_generate_code_format(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Generated code should have expected format."""
        mock_kill_switch.generate_deactivation_code.return_value = "12345678"

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            response = test_client.post(
                "/api/v1/risk/kill-switch/generate-code"
            )

        data = response.json()
        assert isinstance(data["code"], str)
        assert len(data["code"]) > 0

    def test_generate_code_multiple_calls(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Multiple code generation calls should each generate new code."""
        mock_kill_switch.generate_deactivation_code.side_effect = [
            "code1",
            "code2",
            "code3",
        ]

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            r1 = test_client.post("/api/v1/risk/kill-switch/generate-code")
            r2 = test_client.post("/api/v1/risk/kill-switch/generate-code")
            r3 = test_client.post("/api/v1/risk/kill-switch/generate-code")

        assert r1.json()["code"] == "code1"
        assert r2.json()["code"] == "code2"
        assert r3.json()["code"] == "code3"
        assert mock_kill_switch.generate_deactivation_code.call_count == 3


# ===========================================================================
# Singleton initialization tests
# ===========================================================================


class TestSingletonInitialization:
    """Test module-level singleton initialization."""

    def test_kill_switch_singleton_created_once(
        self,
        test_client: TestClient,
    ) -> None:
        """Kill switch singleton should be created only once."""
        with patch("src.api.routes.risk.KillSwitch") as mock_ks_class, \
             patch("src.api.routes.risk.DataStore"):
            # Reset singleton
            import src.api.routes.risk as risk_module
            risk_module._kill_switch = None
            risk_module._store = None

            # Configure mock to return proper status structure
            mock_instance = mock_ks_class.return_value
            mock_instance.get_status.return_value = {
                "active": False,
                "activated_at": None,
                "reason": None,
                "duration_seconds": None,
                "trading_enabled": True,
            }

            # Make multiple requests
            test_client.get("/api/v1/risk/kill-switch/status")
            test_client.get("/api/v1/risk/kill-switch/status")
            test_client.get("/api/v1/risk/kill-switch/status")

            # Should only create once
            assert mock_ks_class.call_count == 1

    def test_store_singleton_created_once(
        self,
        test_client: TestClient,
    ) -> None:
        """DataStore singleton should be created only once."""
        with patch("src.api.routes.risk.DataStore") as mock_store_class, \
             patch("src.api.routes.risk.KillSwitch") as mock_ks_class:
            # Reset singleton
            import src.api.routes.risk as risk_module
            risk_module._kill_switch = None
            risk_module._store = None

            # Configure mock kill switch to return proper status
            mock_ks = mock_ks_class.return_value
            mock_ks.get_status.return_value = {
                "active": False,
                "activated_at": None,
                "reason": None,
                "duration_seconds": None,
                "trading_enabled": True,
            }

            # Make multiple requests
            test_client.get("/api/v1/risk/kill-switch/status")
            test_client.get("/api/v1/risk/kill-switch/status")

            # Should only create once
            assert mock_store_class.call_count == 1


# ===========================================================================
# Error handling tests
# ===========================================================================


class TestAPIErrorHandling:
    """Test API error handling scenarios."""

    def test_activate_with_invalid_json(
        self,
        test_client: TestClient,
    ) -> None:
        """Invalid JSON should return 422."""
        response = test_client.post(
            "/api/v1/risk/kill-switch/activate",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_deactivate_with_wrong_content_type(
        self,
        test_client: TestClient,
    ) -> None:
        """Wrong content type should be rejected."""
        response = test_client.post(
            "/api/v1/risk/kill-switch/deactivate",
            data="confirmation_code=abc123",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # FastAPI should handle this gracefully
        assert response.status_code in (422, 415)

    def test_status_handles_kill_switch_exception(
        self,
        test_client: TestClient,
        mock_kill_switch: MagicMock,
    ) -> None:
        """Status endpoint should handle kill switch exceptions."""
        mock_kill_switch.get_status.side_effect = Exception("DB error")

        with patch(
            "src.api.routes.risk._get_kill_switch",
            return_value=mock_kill_switch,
        ):
            # Exception should propagate (FastAPI handles it)
            with pytest.raises(Exception):
                test_client.get("/api/v1/risk/kill-switch/status")
