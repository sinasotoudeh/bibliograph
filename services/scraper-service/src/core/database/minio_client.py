"""
MinIO Client Configuration
"""

import structlog
from minio import Minio
from minio.error import S3Error

from src.config.settings import get_settings  # ✅ مسیر درست

logger = structlog.get_logger(__name__)
settings = get_settings()


class MinioClient:
    """
    MinIO client manager for object storage
    """

    def __init__(self):
        self._client: Minio | None = None
        self._is_connected: bool = False

    def connect(self) -> None:
        """
        Connect to MinIO
        """
        if self._is_connected and self._client:
            logger.debug("minio_already_connected")
            return

        try:
            self._client = Minio(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )

            # Test connection by checking if client can list buckets
            self._client.list_buckets()
            self._is_connected = True

            logger.info(
                "minio_connected",
                endpoint=settings.minio_endpoint,
                secure=settings.minio_secure,
            )

        except S3Error as e:
            logger.error(
                "minio_connection_failed",
                error=str(e),
                endpoint=settings.minio_endpoint,
            )
            raise
        except Exception as e:
            logger.error(
                "minio_unexpected_error",
                error=str(e),
                endpoint=settings.minio_endpoint,
            )
            raise

    def disconnect(self) -> None:
        """
        Disconnect from MinIO (MinIO client doesn't need explicit disconnect)
        """
        if self._client:
            self._is_connected = False
            self._client = None
            logger.info("minio_disconnected")

    def health_check(self) -> dict:
        """
        Check MinIO service health
        """
        if not self._is_connected or not self._client:
            return {
                "status": "unhealthy",
                "error": "Not connected",
            }

        try:
            # Try to list buckets as a health check
            buckets = self._client.list_buckets()
            return {
                "status": "healthy",
                "endpoint": settings.minio_endpoint,
                "bucket_count": len(buckets),
                "secure": settings.minio_secure,
            }

        except S3Error as e:
            logger.error("minio_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
            }
        except Exception as e:
            logger.error("minio_health_check_error", error=str(e))
            return {
                "status": "unhealthy",
                "error": f"Unexpected error: {str(e)}",
            }

    @property
    def client(self) -> Minio:
        """
        Get the MinIO client
        """
        if not self._is_connected or not self._client:
            raise RuntimeError("MinIO client is not connected")
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._is_connected

    def ensure_bucket(self, bucket_name: str) -> None:
        """
        Ensure a bucket exists, create if it doesn't
        """
        try:
            if not self._client.bucket_exists(bucket_name):
                self._client.make_bucket(bucket_name)
                logger.info("minio_bucket_created", bucket=bucket_name)
            else:
                logger.debug("minio_bucket_exists", bucket=bucket_name)

        except S3Error as e:
            logger.error(
                "minio_ensure_bucket_failed",
                bucket=bucket_name,
                error=str(e),
            )
            raise

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        """
        Upload a file to MinIO
        """
        try:
            self.ensure_bucket(bucket_name)
            self._client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
            )
            logger.info(
                "minio_file_uploaded",
                bucket=bucket_name,
                object=object_name,
            )

        except S3Error as e:
            logger.error(
                "minio_upload_failed",
                bucket=bucket_name,
                object=object_name,
                error=str(e),
            )
            raise


# Global instance
minio_client = MinioClient()


# Convenience function
def get_minio_client() -> Minio:
    """
    Get connected MinIO client
    """
    if not minio_client.is_connected:
        minio_client.connect()
    return minio_client.client
