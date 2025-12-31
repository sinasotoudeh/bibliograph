"""
Health Check Endpoints
Provides system health status and diagnostics for all connected services.
"""

from datetime import datetime
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, status, HTTPException

from src.config.settings import get_settings
from src.core.database import DatabaseManager
from ..dependencies import get_db_manager


router = APIRouter()
logger = structlog.get_logger(__name__)
settings = get_settings()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Returns simple heartbeat data for the API container.
    """
    return {
        "status": "healthy",
        "service": "scraper-api",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
    }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Dict[str, Any]:
    """
    Detailed health check including all connected services.
    Combines per-database status and summaries into unified JSON.
    """
    logger.info("health_check_requested")

    try:
        # Collect health data from all service clients
        db_health = await db_manager.health_check_all()

        # Normalize possible response structure
        services_data = db_health.get("services", db_health)

        # Determine global status
        all_healthy = all(
            service.get("status") == "healthy" or service.get("healthy", False)
            for service in services_data.values()
        )
        overall_status = "healthy" if all_healthy else "degraded"

        response = {
            "status": overall_status,
            "service": "scraper-api",
            "version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.environment,
            "databases": services_data,
            "summary": {
                "total_services": len(services_data),
                "healthy_services": sum(
                    1
                    for s in services_data.values()
                    if s.get("status") == "healthy" or s.get("healthy", False)
                ),
                "unhealthy_services": sum(
                    1
                    for s in services_data.values()
                    if not (s.get("status") == "healthy" or s.get("healthy", False))
                ),
            },
        }

        logger.info("health_check_completed", overall_status=overall_status)
        return response

    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# ───────────────────────────── Individual Checks ─────────────────────────────

@router.get("/health/postgres", status_code=status.HTTP_200_OK)
async def postgres_health(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Dict[str, Any]:
    """Check PostgreSQL health."""
    try:
        health = await db_manager.postgres.health_check()
        return {"service": "postgresql", "timestamp": datetime.utcnow().isoformat(), **health}
    except Exception as e:
        logger.error("postgres_health_check_failed", error=str(e))
        return {
            "service": "postgresql",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/mongodb", status_code=status.HTTP_200_OK)
async def mongodb_health(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Dict[str, Any]:
    """Check MongoDB health."""
    try:
        health = await db_manager.mongodb.health_check()
        return {"service": "mongodb", "timestamp": datetime.utcnow().isoformat(), **health}
    except Exception as e:
        logger.error("mongodb_health_check_failed", error=str(e))
        return {
            "service": "mongodb",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/redis", status_code=status.HTTP_200_OK)
async def redis_health(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Dict[str, Any]:
    """Check Redis (Cache) health."""
    try:
        health = await db_manager.cache.health_check()
        return {"service": "redis", "timestamp": datetime.utcnow().isoformat(), **health}
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return {
            "service": "redis",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/elasticsearch", status_code=status.HTTP_200_OK)
async def elasticsearch_health(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Dict[str, Any]:
    """Check Elasticsearch health."""
    try:
        health = await db_manager.elasticsearch.health_check()
        return {"service": "elasticsearch", "timestamp": datetime.utcnow().isoformat(), **health}
    except Exception as e:
        logger.error("elasticsearch_health_check_failed", error=str(e))
        return {
            "service": "elasticsearch",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/minio", status_code=status.HTTP_200_OK)
async def minio_health(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Dict[str, Any]:
    """Check MinIO health."""
    try:
        health = db_manager.minio.health_check()  # Sync method
        return {"service": "minio", "timestamp": datetime.utcnow().isoformat(), **health}
    except Exception as e:
        logger.error("minio_health_check_failed", error=str(e))
        return {
            "service": "minio",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
