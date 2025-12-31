"""
Application Settings Configuration
Manages environment variables and configuration using Pydantic Settings
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # ─────────────────────────────────────────────
    # Application Settings
    # ─────────────────────────────────────────────
    environment: str = Field(default="development")
    service_name: str = Field(default="scraper-service")
    
    # ─────────────────────────────────────────────
    # PostgreSQL Database Settings
    # ─────────────────────────────────────────────
    database_url: str = Field(alias="DATABASE_URL")
    db_user: str = Field(alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")
    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(alias="DB_PORT")
    db_name: str = Field(alias="DB_NAME")
    
    @computed_field
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL for asyncpg"""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    # ─────────────────────────────────────────────
    # MongoDB Settings
    # ─────────────────────────────────────────────
    mongo_url: str = Field(alias="MONGO_URL")
    mongo_db_name: str = Field(alias="MONGO_DB_NAME")
    mongo_user: str = Field(alias="MONGO_USER")
    mongo_password: str = Field(alias="MONGO_PASSWORD")
    mongo_host: str = Field(alias="MONGO_HOST")
    mongo_port: int = Field(alias="MONGO_PORT")
    
    # ─────────────────────────────────────────────
    # Redis Settings
    # ─────────────────────────────────────────────
    redis_url: str = Field(alias="REDIS_URL")
    redis_password: str = Field(alias="REDIS_PASSWORD")
    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(alias="REDIS_PORT")
    redis_db: int = Field(alias="REDIS_DB")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")  # ✅ اضافه شد

    # ─────────────────────────────────────────────
    # Elasticsearch Settings
    # ─────────────────────────────────────────────
    es_hosts: str = Field(alias="ES_HOSTS")
    es_user: Optional[str] = Field(default=None, alias="ES_USER")
    es_password: Optional[str] = Field(default=None, alias="ES_PASSWORD")
    elasticsearch_index_prefix: str = Field(default="bibliograph")
    # ─────────────────────────────────────────────
    # Elasticsearch Settings
    # ─────────────────────────────────────────────
    es_hosts: str = Field(alias="ES_HOSTS")
    es_user: Optional[str] = Field(default=None, alias="ES_USER")
    es_password: Optional[str] = Field(default=None, alias="ES_PASSWORD")
    elasticsearch_index_prefix: str = Field(default="bibliograph")

    @computed_field  # ✅ اضافه کردن
    @property
    def elasticsearch_url(self) -> str:
        """Construct Elasticsearch URL"""
        if self.es_hosts.startswith(("http://", "https://")):
            return self.es_hosts
        return f"http://{self.es_hosts}"
    # ─────────────────────────────────────────────
    # RabbitMQ Settings
    # ─────────────────────────────────────────────
    rabbitmq_url: str = Field(alias="RABBITMQ_URL")
    rabbitmq_user: str = Field(alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(alias="RABBITMQ_PASSWORD")
    rabbitmq_host: str = Field(alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(alias="RABBITMQ_PORT")
    rabbitmq_vhost: str = Field(default="/", alias="RABBITMQ_VHOST")
    
    # ─────────────────────────────────────────────
    # MinIO Settings
    # ─────────────────────────────────────────────
    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    minio_bucket_name: str = Field(default="bibliograph", alias="MINIO_BUCKET_NAME")
    
    # ─────────────────────────────────────────────
    # Celery Settings
    # ─────────────────────────────────────────────
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")
    
    # ─────────────────────────────────────────────
    # Logging Settings
    # ─────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # ─────────────────────────────────────────────
    # Scraper Settings
    # ─────────────────────────────────────────────
    max_concurrent_scrapers: int = Field(default=5, alias="MAX_CONCURRENT_SCRAPERS")
    scraper_timeout: int = Field(default=300, alias="SCRAPER_TIMEOUT")
    scraper_retry_limit: int = Field(default=3, alias="SCRAPER_RETRY_LIMIT")
    
    # ─────────────────────────────────────────────
    # Monitoring Settings
    # ─────────────────────────────────────────────
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    
    # ─────────────────────────────────────────────
    # Flower Settings (Celery UI)
    # ─────────────────────────────────────────────
    flower_user: str = Field(default="admin", alias="FLOWER_USER")
    flower_password: str = Field(default="bibliograph_flower_2024", alias="FLOWER_PASSWORD")
    flower_port: int = Field(default=5555, alias="FLOWER_PORT")
    
    # ─────────────────────────────────────────────
    # Python Settings
    # ─────────────────────────────────────────────
    pythonunbuffered: str = Field(default="1", alias="PYTHONUNBUFFERED")
    
    # ─────────────────────────────────────────────
    # API Settings
    # ─────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")
    cors_origins: List[str] = Field(default=["*"])
    
    # ─────────────────────────────────────────────
    # Pydantic Settings Configuration
    # ─────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,  # 🔑 اضافه شد
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Uses LRU cache to ensure settings are loaded only once
    """
    return Settings()


# Convenience function to get specific config sections
def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    settings = get_settings()
    return {
        "postgres": {
            "url": settings.postgres_url,
            "host": settings.db_host,
            "port": settings.db_port,
            "database": settings.db_name,
        },
        "mongodb": {
            "url": settings.mongo_url,
            "database": settings.mongo_db_name,
        },
        "redis": {
            "url": settings.redis_url,
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
        },
        "elasticsearch": {
            "url": settings.es_hosts,
            "index_prefix": settings.elasticsearch_index_prefix,
        },
    }


def get_celery_config() -> Dict[str, Any]:
    """Get Celery configuration"""
    settings = get_settings()
    return {
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,
    }
