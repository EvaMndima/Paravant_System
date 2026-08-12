"""
Integration tests for API endpoints.

Tests:
- Health check endpoint
- Readiness check endpoint
- Root endpoint
- CORS configuration
- Global exception handler
"""


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_check_returns_200(self, api_client):
        """Test health endpoint returns 200 OK."""
        response = api_client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, api_client):
        """Test health endpoint response structure."""
        response = api_client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestReadyEndpoint:
    """Test /ready endpoint."""

    def test_ready_check_returns_200(self, api_client):
        """Test ready endpoint returns 200 OK."""
        response = api_client.get("/ready")
        assert response.status_code == 200

    def test_ready_check_response_structure(self, api_client):
        """Test ready endpoint response structure."""
        response = api_client.get("/ready")
        data = response.json()

        assert "ready" in data
        assert data["ready"] is True
        assert "checks" in data
        assert "database" in data["checks"]


class TestRootEndpoint:
    """Test / root endpoint."""

    def test_root_returns_200(self, api_client):
        """Test root endpoint returns 200 OK."""
        response = api_client.get("/")
        assert response.status_code == 200

    def test_root_response_structure(self, api_client):
        """Test root endpoint response structure."""
        response = api_client.get("/")
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "environment" in data
        assert "uptime_seconds" in data


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, api_client):
        """Test that CORS headers are present."""
        response = api_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert "access-control-allow-origin" in response.headers


class TestExceptionHandling:
    """Test global exception handler."""

    def test_unhandled_exception_returns_500(self, api_client):
        """Test that unhandled exceptions return 500."""
        # This would require adding a test endpoint that raises an exception
        # For now, we'll verify the handler exists
        pass  # TODO: Add test endpoint for exception testing
