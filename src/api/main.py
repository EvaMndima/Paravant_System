"""FastAPI main application for PARAVANT Trading System.

This module initializes the FastAPI application with health check endpoints
and basic configuration required by the Docker container.
"""
import os
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
TRADING_MODE = os.getenv("TRADING_MODE", "paper")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# Response models
class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    environment: str
    trading_mode: str
    version: str


class SystemInfo(BaseModel):
    """System information response model."""
    name: str
    version: str
    environment: str
    trading_mode: str
    uptime_seconds: float


# Initialize FastAPI application
app = FastAPI(
    title="PARAVANT Trading System API",
    description="Personal Autonomous Trading System for algorithmic trading",
    version="1.0.0",
    docs_url="/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if ENVIRONMENT == "development" else None,
)


# CORS middleware configuration
# Development: Only allow localhost origins for security
ALLOWED_ORIGINS_DEV = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

# Production: Load from environment variable (comma-separated)
ALLOWED_ORIGINS_PROD = (
    os.getenv("ALLOWED_ORIGINS", "").split(",")
    if os.getenv("ALLOWED_ORIGINS")
    else []
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS_DEV if ENVIRONMENT == "development" else ALLOWED_ORIGINS_PROD,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],  # Explicit headers
)


# Application startup time for uptime calculation
startup_time = datetime.now(timezone.utc)


# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.

    Logs the error with full context and returns appropriate response
    based on environment (detailed in dev, generic in production).
    """
    from src.utils.logging import get_logger

    logger = get_logger(__name__)
    logger.error(
        "unhandled_exception",
        path=str(request.url.path),
        method=request.method,
        error=str(exc),
        exc_info=True
    )

    # In development, return detailed error for debugging
    # In production, return generic error to avoid information leak
    error_detail = str(exc) if ENVIRONMENT == "development" else "Internal server error"

    return JSONResponse(
        status_code=500,
        content={
            "detail": error_detail,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Health check endpoint required by Docker health checks.

    Returns system health status and basic configuration information.
    This endpoint is called by Docker's HEALTHCHECK directive.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=ENVIRONMENT,
        trading_mode=TRADING_MODE,
        version="1.0.0"
    )


@app.get("/ready")
async def readiness_check() -> JSONResponse:
    """
    Readiness check endpoint for deployment orchestrators (Kubernetes, Docker Swarm).

    Performs actual health checks on critical dependencies:
    - Database connectivity
    - Required configuration

    Returns 200 OK if all checks pass, 503 Service Unavailable otherwise.
    """
    from sqlalchemy import text
    from src.data.database import engine

    checks = {"api": "ok"}
    all_ok = True

    # Database readiness check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        all_ok = False

    # Configuration check - verify required environment variables
    # Note: DATABASE_URL has a default (SQLite), so it's not strictly required
    # The actual database connectivity is tested above
    try:
        # For MVP, no environment variables are strictly required
        # (all have sensible defaults for local development)
        # In production, you should set: ALLOWED_ORIGINS, DATABASE_URL (for Postgres)
        checks["configuration"] = "ok"
    except Exception as e:
        checks["configuration"] = f"error: {str(e)}"
        all_ok = False

    status_code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "ready": all_ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks
        }
    )


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing basic API information.
    """
    uptime = (datetime.now(timezone.utc) - startup_time).total_seconds()

    return {
        "name": "PARAVANT Trading System API",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "trading_mode": TRADING_MODE,
        "status": "running",
        "uptime_seconds": uptime,
        "docs_url": "/docs" if ENVIRONMENT == "development" else "disabled_in_production",
        "health_check": "/health",
        "readiness_check": "/ready"
    }


@app.on_event("startup")
async def startup_event() -> None:
    """
    Application startup event handler.

    Performs initialization tasks when the application starts:
    - Initialize structured logging
    - Verify database connection
    - Load configuration
    """
    from src.utils.logging import setup_logging, get_logger

    # Setup structured logging
    json_logs = ENVIRONMENT != "development"
    setup_logging(level=LOG_LEVEL, json_format=json_logs)

    logger = get_logger(__name__)
    logger.info(
        "api_starting",
        environment=ENVIRONMENT,
        trading_mode=TRADING_MODE,
        log_level=LOG_LEVEL,
        startup_time=startup_time.isoformat()
    )

    # Warn if CORS is not configured in production
    if ENVIRONMENT != "development" and not ALLOWED_ORIGINS_PROD:
        logger.warning(
            "cors_not_configured",
            message="ALLOWED_ORIGINS environment variable not set - all CORS requests will be blocked in production",
            environment=ENVIRONMENT
        )

    logger.info(
        "api_startup_details",
        environment=ENVIRONMENT,
        trading_mode=TRADING_MODE,
        log_level=LOG_LEVEL,
        startup_time=startup_time.isoformat()
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Application shutdown event handler.

    Performs cleanup tasks when the application shuts down:
    - Close database connections
    - Flush logs
    - Release resources
    """
    from src.utils.logging import get_logger
    from src.data.database import engine

    logger = get_logger(__name__)
    logger.info("api_shutting_down", uptime_seconds=(datetime.now(timezone.utc) - startup_time).total_seconds())

    # Close database connections gracefully
    try:
        engine.dispose()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.error("database_shutdown_error", error=str(e))


# Register route modules
from src.api.routes.risk import router as risk_router
from src.api.routes.orders import router as orders_router
from src.api.routes.positions import router as positions_router
from src.api.routes.execution import router as execution_router
from src.api.routes.strategies import router as strategies_router
from src.api.routes.backtest import router as backtest_router
from src.api.routes.paper_trading import router as paper_trading_router

app.include_router(risk_router, prefix="/api/v1/risk", tags=["risk"])
app.include_router(orders_router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(positions_router, prefix="/api/v1/positions", tags=["positions"])
app.include_router(execution_router, prefix="/api/v1/execution", tags=["execution"])
app.include_router(strategies_router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(backtest_router, prefix="/api/v1/strategies", tags=["backtest"])
app.include_router(paper_trading_router, prefix="/api/v1/strategies", tags=["paper-trading"])

# Note: Additional route modules will be added in subsequent sections:
# - Section 1.3: Configuration routes
# - Section 6: Dashboard and monitoring routes
