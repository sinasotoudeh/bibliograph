"""
FastAPI Application Entry Point for Bibliograph Scraper Service
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
    make_asgi_app,
)

from src.config.logging_config import setup_logging
from src.config.settings import get_settings
from src.core.database import DatabaseManager

# Import API routes
from .routes import api_router

# ─────────────────────────────────────────────
# Setup Logging & Settings
# ─────────────────────────────────────────────
setup_logging()
logger = structlog.get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────
# Prometheus Metrics
# ─────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)


# ─────────────────────────────────────────────
# Application Lifespan (Startup + Shutdown)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    - Startup: Connect to all databases
    - Shutdown: Disconnect gracefully
    """
    db_manager = DatabaseManager()
    try:
        # Startup
        logger.info("application_starting", environment=settings.environment)
        await db_manager.connect_all()
        
        # Store db_manager in app state for route handlers
        app.state.db_manager = db_manager
        
        logger.info(
            "application_started",
            environment=settings.environment,
        )
        
        yield
        
    except Exception as e:
        logger.error("application_startup_failed", error=str(e))
        raise
    finally:
        # Shutdown
        logger.info("application_shutting_down")
        await db_manager.disconnect_all()
        logger.info("application_stopped")

# ─────────────────────────────────────────────
# FastAPI App Definition
# ─────────────────────────────────────────────
app = FastAPI(
    title="BiblioGraph AI - Scraper Service",
    description="Persian Book Scraping & Data Collection API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ─────────────────────────────────────────────
# Middleware Configuration
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, 'cors_origins') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """
    Collect metrics for each HTTP request
    - Request count by method, endpoint, and status
    - Request duration histogram
    """
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=500,
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)
        
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration=duration,
        )
        raise


# ─────────────────────────────────────────────
# Mount Prometheus Metrics App
# ─────────────────────────────────────────────
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ─────────────────────────────────────────────
# Include API Routers
# ─────────────────────────────────────────────
app.include_router(api_router)


# ─────────────────────────────────────────────
# Root & Legacy Endpoints
# ─────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "service": "BiblioGraph AI - Scraper Service",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.environment,
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
        "endpoints": {
            "health": "/api/v1/health",
            "health_detailed": "/api/v1/health/detailed",
            "scraping": "/api/v1/scraping",
            "books": "/api/v1/books",
            "metrics": "/metrics",
        },
    }


@app.get("/metrics_raw", tags=["Metrics"])
async def metrics_raw():
    """
    Raw metrics access (Prometheus text format)
    Alternative endpoint for Prometheus metrics
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ─────────────────────────────────────────────
# Exception Handlers
# ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors
    """
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    
    return JSONResponse(
    content={
        "error": "Internal Server Error",
        "detail": str(exc),
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat()
    },
    status_code=500
)


# ─────────────────────────────────────────────
# Application Info
# ─────────────────────────────────────────────
logger.info(
    "fastapi_application_configured",
    title=app.title,
    version=app.version,
    environment=settings.environment,
)
