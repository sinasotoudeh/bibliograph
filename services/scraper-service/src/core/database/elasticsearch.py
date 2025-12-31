"""
Elasticsearch Client Configuration
"""

import structlog
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import (
    ConnectionError as ESConnectionError,
    NotFoundError,
    TransportError,
)

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ElasticsearchClient:
    """
    Elasticsearch client manager with connection pooling
    """

    def __init__(self):
        self._client: AsyncElasticsearch | None = None
        self._is_connected: bool = False

    async def connect(self) -> None:
        """
        Connect to Elasticsearch
        """
        if self._is_connected and self._client:
            logger.debug("elasticsearch_already_connected")
            return

        try:
            self._client = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                verify_certs=False,
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True,
            )

            # Test connection
            await self._client.info()
            self._is_connected = True

            logger.info(
                "elasticsearch_connected",
                url=settings.elasticsearch_url,
            )

        except Exception as e:
            logger.error(
                "elasticsearch_connection_failed",
                error=str(e),
                url=settings.elasticsearch_url,
            )
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from Elasticsearch
        """
        if self._client:
            try:
                await self._client.close()
                self._is_connected = False
                logger.info("elasticsearch_disconnected")
            except Exception as e:
                logger.error("elasticsearch_disconnect_error", error=str(e))

    async def health_check(self) -> dict:
        """
        Check Elasticsearch cluster health
        """
        if not self._is_connected or not self._client:
            return {
                "status": "unhealthy",
                "error": "Not connected",
            }

        try:
            health = await self._client.cluster.health()
            return {
                "status": "healthy",
                "cluster_name": health.get("cluster_name"),
                "cluster_status": health.get("status"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_shards": health.get("active_shards"),
            }

        except (ESConnectionError, TransportError) as e:
            logger.error("elasticsearch_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
            }
        except Exception as e:
            logger.error("elasticsearch_health_check_error", error=str(e))
            return {
                "status": "unhealthy",
                "error": f"Unexpected error: {str(e)}",
            }

    @property
    def client(self) -> AsyncElasticsearch:
        """
        Get the Elasticsearch client
        """
        if not self._is_connected or not self._client:
            raise RuntimeError("Elasticsearch client is not connected")
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._is_connected


# Global instance
elasticsearch_client = ElasticsearchClient()


# Convenience functions
async def get_elasticsearch_client() -> AsyncElasticsearch:
    """
    Get connected Elasticsearch client
    """
    if not elasticsearch_client.is_connected:
        await elasticsearch_client.connect()
    return elasticsearch_client.client


async def ensure_index(
    index_name: str,
    mappings: dict | None = None,
    settings: dict | None = None,
) -> None:
    """
    Ensure an index exists with given mappings and settings
    """
    client = await get_elasticsearch_client()

    try:
        exists = await client.indices.exists(index=index_name)

        if not exists:
            body = {}
            if mappings:
                body["mappings"] = mappings
            if settings:
                body["settings"] = settings

            await client.indices.create(index=index_name, body=body)

            logger.info(
                "elasticsearch_index_created",
                index=index_name,
            )
        else:
            logger.debug(
                "elasticsearch_index_exists",
                index=index_name,
            )

    except NotFoundError:
        logger.warning(
            "elasticsearch_index_not_found",
            index=index_name,
        )
    except Exception as e:
        logger.error(
            "elasticsearch_ensure_index_failed",
            index=index_name,
            error=str(e),
        )
        raise


async def delete_index(index_name: str) -> None:
    """
    Delete an index if it exists
    """
    client = await get_elasticsearch_client()

    try:
        exists = await client.indices.exists(index=index_name)

        if exists:
            await client.indices.delete(index=index_name)
            logger.info("elasticsearch_index_deleted", index=index_name)
        else:
            logger.debug("elasticsearch_index_does_not_exist", index=index_name)

    except Exception as e:
        logger.error(
            "elasticsearch_delete_index_failed",
            index=index_name,
            error=str(e),
        )
        raise
