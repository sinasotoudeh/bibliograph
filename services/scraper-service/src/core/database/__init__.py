"""
Database clients manager
Centralizes all database connections
"""

from typing import Any, Dict

import structlog

from .elasticsearch import elasticsearch_client
from .minio_client import minio_client
from .mongodb import mongodb_client
from .postgres import postgres_client
from .redis_client import cache_client, celery_client

logger = structlog.get_logger(__name__)

__all__ = [
    "postgres_client",
    "mongodb_client",
    "cache_client",
    "celery_client",
    "elasticsearch_client",
    "minio_client",
    "DatabaseManager"
]


class DatabaseManager:
    """
    Centralized database connection manager

    Usage:
        async with DatabaseManager() as db:
            # All connections ready
            await db.postgres.health_check()

    Or manually:
        db_manager = DatabaseManager()
        await db_manager.connect_all()
        # ... use databases ...
        await db_manager.disconnect_all()
    """

    def __init__(self):
        self.postgres = postgres_client
        self.mongodb = mongodb_client
        self.cache = cache_client
        self.celery = celery_client
        self.elasticsearch = elasticsearch_client
        self.minio = minio_client
        self._connected = False

    async def connect_all(self) -> None:
        """Connect to all databases"""
        if self._connected:
            logger.warning("database_manager_already_connected")
            return

        logger.info("database_manager_connecting_all")

        try:
            # Connect to async databases
            await self.postgres.connect()
            await self.mongodb.connect()
            await self.cache.connect()
            await self.celery.connect()
            await self.elasticsearch.connect()

            # MinIO is synchronous
            self.minio.connect()

            self._connected = True
            logger.info("database_manager_all_connected")

        except Exception as e:
            logger.error("database_manager_connection_failed", error=str(e))
            # Try to disconnect already connected clients
            await self.disconnect_all()
            raise

    async def disconnect_all(self) -> None:
        """Disconnect from all databases"""
        if not self._connected:
            logger.warning("database_manager_not_connected")
            return

        logger.info("database_manager_disconnecting_all")

        # Disconnect in reverse order
        errors = []

        try:
            await self.elasticsearch.disconnect()
        except Exception as e:
            errors.append(("elasticsearch", str(e)))

        try:
            await self.celery.disconnect()
        except Exception as e:
            errors.append(("celery", str(e)))

        try:
            await self.cache.disconnect()
        except Exception as e:
            errors.append(("cache", str(e)))

        try:
            await self.mongodb.disconnect()
        except Exception as e:
            errors.append(("mongodb", str(e)))

        try:
            await self.postgres.disconnect()
        except Exception as e:
            errors.append(("postgres", str(e)))

        self._connected = False

        if errors:
            logger.warning(
                "database_manager_disconnection_errors",
                errors=errors
            )
        else:
            logger.info("database_manager_all_disconnected")

    async def health_check_all(self) -> Dict[str, Any]:
        """
        Check health of all databases

        Returns:
            Dict with health status of each service
        """
        results = {}

        # Check PostgreSQL
        try:
            results["postgres"] = await self.postgres.health_check()
        except Exception as e:
            results["postgres"] = {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }

        # Check MongoDB
        try:
            results["mongodb"] = await self.mongodb.health_check()
        except Exception as e:
            results["mongodb"] = {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }

        # Check Redis Cache
        try:
            results["redis_cache"] = await self.cache.health_check()
        except Exception as e:
            results["redis_cache"] = {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }

        # Check Redis Celery
        try:
            results["redis_celery"] = await self.celery.health_check()
        except Exception as e:
            results["redis_celery"] = {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }

        # Check Elasticsearch
        try:
            results["elasticsearch"] = await self.elasticsearch.health_check()
        except Exception as e:
            results["elasticsearch"] = {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }

        # Check MinIO
        try:
            results["minio"] = self.minio.health_check()
        except Exception as e:
            results["minio"] = {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }

        # Overall health
        all_healthy = all(
            service.get("healthy", False)
            for service in results.values()
        )

        results["overall"] = {
            "healthy": all_healthy,
            "total_services": len(results) - 1,  # Exclude 'overall'
            "healthy_services": sum(
                1 for s in results.values()
                if s.get("healthy", False)
            )
        }

        return results

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect_all()
        return False  # Don't suppress exceptions


# Singleton instance
database_manager = DatabaseManager()


# Utility functions for easy access
async def init_databases() -> None:
    """Initialize all database connections"""
    await database_manager.connect_all()


async def close_databases() -> None:
    """Close all database connections"""
    await database_manager.disconnect_all()


async def check_databases_health() -> Dict[str, Any]:
    """Check health of all databases"""
    return await database_manager.health_check_all()
