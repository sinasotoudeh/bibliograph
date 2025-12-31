"""
MongoDB Client Configuration
"""

import structlog
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class MongoDBClient:
    """
    MongoDB client manager using Motor (async driver)
    """

    def __init__(self):
        self._client: AsyncIOMotorClient | None = None
        self._is_connected: bool = False

    async def connect(self) -> None:
        """
        Connect to MongoDB
        """
        if self._is_connected and self._client:
            logger.debug("mongodb_already_connected")
            return

        try:
            # Create MongoDB client - استفاده از نام‌های صحیح
            self._client = AsyncIOMotorClient(
                settings.mongo_url,  # ✅ تغییر داده شد
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
            )

            # Test connection
            await self._client.admin.command("ping")
            self._is_connected = True

            logger.info(
                "mongodb_connected",
                uri=settings.mongo_url.split("@")[-1],  # Hide credentials
            )

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(
                "mongodb_connection_failed",
                error=str(e),
                uri=settings.mongo_url.split("@")[-1],
            )
            raise
        except Exception as e:
            logger.error(
                "mongodb_unexpected_error",
                error=str(e),
            )
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from MongoDB
        """
        if self._client:
            self._client.close()
            self._is_connected = False
            self._client = None
            logger.info("mongodb_disconnected")

    async def health_check(self) -> dict:
        """
        Check MongoDB service health
        """
        if not self._is_connected or not self._client:
            return {
                "status": "unhealthy",
                "error": "Not connected",
            }

        try:
            # Ping MongoDB
            await self._client.admin.command("ping")
            
            # Get server info
            server_info = await self._client.server_info()
            
            return {
                "status": "healthy",
                "version": server_info.get("version", "unknown"),
                "databases": len(await self._client.list_database_names()),
            }

        except Exception as e:
            logger.error("mongodb_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    @property
    def client(self) -> AsyncIOMotorClient:
        """
        Get the MongoDB client
        """
        if not self._is_connected or not self._client:
            raise RuntimeError("MongoDB client is not connected")
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._is_connected

    def get_database(self, db_name: str | None = None):
        """
        Get a database instance
        """
        if not self._is_connected or not self._client:
            raise RuntimeError("MongoDB client is not connected")
        
        db_name = db_name or settings.mongo_db_name  # ✅ تغییر داده شد
        return self._client[db_name]

    def get_collection(self, collection_name: str, db_name: str | None = None):
        """
        Get a collection instance
        """
        db = self.get_database(db_name)
        return db[collection_name]


# Global instance
mongodb_client = MongoDBClient()


# Convenience function
def get_mongodb_client() -> AsyncIOMotorClient:
    """
    Get connected MongoDB client
    """
    if not mongodb_client.is_connected:
        raise RuntimeError("MongoDB client is not connected. Call connect() first.")
    return mongodb_client.client
