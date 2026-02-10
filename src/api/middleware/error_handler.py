"""FastAPI error handler middleware for structured exception handling.

Catches all exceptions from API endpoints and formats them as
consistent JSON error responses with appropriate HTTP status codes.

Exception -> Status Code Mapping:
- RiskError -> 400 Bad Request
- ExecutionError -> 400 Bad Request
- StrategyError -> 400 Bad Request
- DataError -> 503 Service Unavailable
- ConfigurationError -> 500 Internal Server Error
- Unhandled Exception -> 500 Internal Server Error

Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.core.exceptions import (
    ConfigurationError,
    DataError,
    ExecutionError,
    RiskError,
    StrategyError,
    TradingSystemError,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _generate_request_id() -> str:
    """Generate a unique request ID for tracing.

    HIGH-010 fix: Uses full 128-bit UUID (32 hex chars) to prevent
    collisions. Truncating to 64 bits increases collision probability
    to unacceptable levels for production tracing.

    Returns:
        A unique request ID string with 'req_' prefix.
    """
    return f"req_{uuid.uuid4().hex}"  # Full UUID, not truncated


def _build_error_response(
    error_code: str,
    message: str,
    details: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    """Build a standardized error response body.

    Args:
        error_code: Machine-readable error code.
        message: Human-readable error message.
        details: Additional error context.
        request_id: Unique request identifier.

    Returns:
        Dictionary conforming to the API error response format.
    """
    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware that catches exceptions and returns structured JSON errors.

    All exceptions raised during request handling are caught, logged with
    context, and returned as JSON responses with appropriate HTTP status
    codes. Internal error details are hidden in production to prevent
    information leakage.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and handle any exceptions.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The response, or a JSON error response if an exception occurred.
        """
        request_id = _generate_request_id()

        try:
            response = await call_next(request)
            return response

        except RiskError as exc:
            logger.warning(
                "risk_error",
                error_code=exc.code,
                error_message=exc.message,
                details=exc.details,
                request_id=request_id,
                path=str(request.url.path),
                url=str(request.url),  # HIGH-011: Full URL with query params for debugging
                method=request.method,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=_build_error_response(
                    error_code=exc.code,
                    message=exc.message,
                    details=exc.details,
                    request_id=request_id,
                ),
            )

        except (ExecutionError, StrategyError) as exc:
            logger.warning(
                "client_error",
                error_code=exc.code,
                error_message=exc.message,
                details=exc.details,
                request_id=request_id,
                path=str(request.url.path),
                url=str(request.url),  # HIGH-011: Full URL with query params for debugging
                method=request.method,
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=_build_error_response(
                    error_code=exc.code,
                    message=exc.message,
                    details=exc.details,
                    request_id=request_id,
                ),
            )

        except DataError as exc:
            logger.error(
                "data_error",
                error_code=exc.code,
                error_message=exc.message,
                details=exc.details,
                request_id=request_id,
                path=str(request.url.path),
                url=str(request.url),  # HIGH-011: Full URL with query params for debugging
                method=request.method,
            )
            # Hide internal details in the response
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=_build_error_response(
                    error_code=exc.code,
                    message="Service temporarily unavailable",
                    details={},
                    request_id=request_id,
                ),
            )

        except ConfigurationError as exc:
            logger.error(
                "configuration_error",
                error_code=exc.code,
                error_message=exc.message,
                details=exc.details,
                request_id=request_id,
                path=str(request.url.path),
                url=str(request.url),  # HIGH-011: Full URL with query params for debugging
                method=request.method,
            )
            # Hide internal details in the response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=_build_error_response(
                    error_code=exc.code,
                    message="Internal server error",
                    details={},
                    request_id=request_id,
                ),
            )

        except TradingSystemError as exc:
            # Catch-all for any other TradingSystemError subclass
            logger.error(
                "trading_system_error",
                error_code=exc.code,
                error_message=exc.message,
                details=exc.details,
                request_id=request_id,
                path=str(request.url.path),
                url=str(request.url),  # HIGH-011: Full URL with query params for debugging
                method=request.method,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=_build_error_response(
                    error_code=exc.code,
                    message="Internal server error",
                    details={},
                    request_id=request_id,
                ),
            )

        except Exception as exc:
            # Unhandled exceptions - never expose internal details
            logger.error(
                "unhandled_error",
                error=str(exc),
                error_type=type(exc).__name__,
                request_id=request_id,
                path=str(request.url.path),
                url=str(request.url),  # HIGH-011: Full URL with query params for debugging
                method=request.method,
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=_build_error_response(
                    error_code="INTERNAL_ERROR",
                    message="An unexpected error occurred",
                    details={},
                    request_id=request_id,
                ),
            )
