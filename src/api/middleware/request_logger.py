"""HTTP request logging middleware for API observability.

Logs every HTTP request with method, path, status code, and duration.
Skips /health and /ready endpoints to reduce noise from Docker health checks.

Follows the same BaseHTTPMiddleware pattern as error_handler.py.

Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Paths to skip logging (high-frequency health checks)
_SKIP_PATHS: frozenset[str] = frozenset({"/health", "/ready"})


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all HTTP requests with timing information.

    Logs structured data for each request:
    - method: HTTP method (GET, POST, etc.)
    - path: Request path
    - status_code: Response status code
    - duration_ms: Request duration in milliseconds
    - client_ip: Client IP address

    Skips /health and /ready to avoid log noise from Docker health checks.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and log timing information.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in the chain.

        Returns:
            Response from the next handler.
        """
        path = request.url.path

        # Skip noisy health check endpoints
        if path in _SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        # Extract client IP (supports X-Forwarded-For from reverse proxy)
        client_ip = request.headers.get(
            "x-forwarded-for", request.client.host if request.client else "unknown"
        )

        logger.info(
            "http_request",
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
        )

        return response
