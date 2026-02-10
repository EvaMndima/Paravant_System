"""Unit tests for API Error Handler Middleware.

Verifies:
- Exception mapping to HTTP status codes
- Information hiding (Sanitization) for internal errors
- Request ID generation and tracing in logs
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from src.api.middleware.error_handler import ErrorHandlerMiddleware
from src.core.exceptions import (
    RiskError, ExecutionError, StrategyError,
    DataError, ConfigurationError, TradingSystemError
)

# Create a minimal app for testing middleware
app = FastAPI()
app.add_middleware(ErrorHandlerMiddleware)

@app.get("/risk-error")
def raise_risk_error():
    # Pass details as keyword argument or second positional
    raise RiskError("Risk limit breached", details={"limit": "max_drawdown"})

@app.get("/execution-error")
def raise_execution_error():
    raise ExecutionError("Order rejected", details={"reason": "insufficient_balance"})

@app.get("/strategy-error")
def raise_strategy_error():
    raise StrategyError("Invalid parameters", details={"param": "period"})

@app.get("/data-error")
def raise_data_error():
    raise DataError("connection_failed", details={"reason": "Database unreachable"})

@app.get("/config-error")
def raise_config_error():
    raise ConfigurationError("missing_key", details={"key": "API_KEY"})

@app.get("/system-error")
def raise_system_error():
    raise TradingSystemError("unknown_error", details={"info": "Something went wrong"})

@app.get("/unhandled-error")
def raise_unhandled_error():
    raise ValueError("Unexpected value")

@app.get("/success")
def success_endpoint():
    return {"status": "ok"}


client = TestClient(app)

class TestErrorHandlerMiddleware:
    """Test error handling middleware behavior."""

    def test_risk_error_handling(self):
        """RiskError -> 400 Bad Request."""
        response = client.get("/risk-error")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"]["code"] == "RISK_ERROR"  # Default code for RiskError
        assert data["error"]["message"] == "Risk limit breached"
        assert data["error"]["details"] == {"limit": "max_drawdown"}
        assert "request_id" in data["error"]

    def test_execution_error_handling(self):
        """ExecutionError -> 400 Bad Request."""
        response = client.get("/execution-error")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_data_error_sanitization(self):
        """DataError -> 503 Service Unavailable (Sanitized)."""
        response = client.get("/data-error")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        # Should hide internal details
        assert data["error"]["message"] == "Service temporarily unavailable"
        assert data["error"]["details"] == {}

    def test_config_error_sanitization(self):
        """ConfigurationError -> 500 Internal Server Error (Sanitized)."""
        response = client.get("/config-error")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"]["message"] == "Internal server error"

    def test_unhandled_exception_sanitization(self):
        """Unhandled Exception -> 500 Internal Server Error (Sanitized)."""
        response = client.get("/unhandled-error")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert data["error"]["message"] == "An unexpected error occurred"

    def test_successful_request_passthrough(self):
        """Middleware passes through successful requests."""
        response = client.get("/success")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}
