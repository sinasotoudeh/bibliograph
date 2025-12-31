"""
PostgreSQL Database Connection Manager
Handles async PostgreSQL connections using SQLAlchemy
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import structlog

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class PostgresClient:
    """PostgreSQL connection manager using SQLAlchemy async engine"""

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._is_connected = False

    async def connect(self):
        """Establish connection to PostgreSQL"""
        if self._is_connected:
            logger.warning("postgres_already_connected")
            return

        try:
            # Create async engine
            self.engine = create_async_engine(
                settings.postgres_url,
                echo=settings.debug,
                pool_pre_ping=True,
                pool_size=20,
                max_overflow=40,
            )

            # Test connection
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            self._is_connected = True
            logger.info("postgres_connected", url=settings.postgres_url.split("@")[1])

        except Exception as e:
            logger.error("postgres_connection_failed", error=str(e))
            raise

    async def disconnect(self):
        """Close PostgreSQL connection"""
        if not self._is_connected:
            logger.warning("postgres_not_connected")
            return

        try:
            if self.engine:
                await self.engine.dispose()
                self.engine = None
                self.session_factory = None

            self._is_connected = False
            logger.info("postgres_disconnected")

        except Exception as e:
            logger.error("postgres_disconnect_failed", error=str(e))
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session
        
        Usage:
            async with postgres_client.get_session() as session:
                # Use session here
        """
        if not self._is_connected or not self.session_factory:
            raise RuntimeError("PostgreSQL not connected")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> dict:
        """
        Check PostgreSQL health status
        
        Returns:
            dict: Health check result with status and details
        """
        if not self._is_connected or not self.engine:
            return {
                "status": "unhealthy",
                "message": "PostgreSQL not connected",
                "connected": False
            }
        
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()
            
            logger.debug("postgres_health_check_passed")
            return {
                "status": "healthy",
                "message": "PostgreSQL connection is healthy",
                "connected": True,
                "version": version.split()[1] if version else "unknown"
            }
            
        except Exception as e:
            logger.error("postgres_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}",
                "connected": False
            }

    @property
    def is_connected(self) -> bool:
        """Check if connected to PostgreSQL"""
        return self._is_connected


# Global instance
postgres_client = PostgresClient()
