"""
Redis Client for Caching and Task Queues
Supports both sync and async operations
"""

from typing import Optional, Any, Dict
import json
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError
import structlog

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)


class RedisClient:
    """
    Async Redis client for caching and pub/sub
    
    Features:
    - Connection pooling
    - Auto-serialization (JSON)
    - Health checks
    - Prefix support for key namespacing
    """
    
    def __init__(self, key_prefix: str = "bibliograph"):
        self.settings = get_settings()
        self.key_prefix = key_prefix
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._client: Optional[Redis] = None
    
    async def connect(self) -> None:
        """Initialize Redis connection pool"""
        if self._pool is None:
            try:
                # ✅ تغییر: استفاده مستقیم از فیلدهای settings
                self._pool = aioredis.ConnectionPool.from_url(
                    self.settings.redis_url,  # ✅ تغییر از settings.database.redis_url
                    max_connections=self.settings.redis_max_connections,  # ✅ تغییر
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )
                
                self._client = Redis(connection_pool=self._pool)
                
                # Test connection
                await self._client.ping()
                
                logger.info(
                    "redis_connected",
                    host=f"{self.settings.redis_host}:{self.settings.redis_port}",  # ✅ تغییر
                    prefix=self.key_prefix
                )
                
            except RedisError as e:
                logger.error("redis_connection_failed", error=str(e))
                raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        
        logger.info("redis_disconnected")
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{self.key_prefix}:{key}"
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        try:
            value = await self._client.get(self._make_key(key))
            if value is None:
                return default
            
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except RedisError as e:
            logger.error("redis_get_failed", key=key, error=str(e))
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to store (auto-serialized to JSON)
            expire: TTL in seconds
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            result = await self._client.set(
                self._make_key(key),
                value,
                ex=expire
            )
            
            return bool(result)
            
        except RedisError as e:
            logger.error("redis_set_failed", key=key, error=str(e))
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            prefixed_keys = [self._make_key(k) for k in keys]
            return await self._client.delete(*prefixed_keys)
        except RedisError as e:
            logger.error("redis_delete_failed", keys=keys, error=str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(await self._client.exists(self._make_key(key)))
        except RedisError as e:
            logger.error("redis_exists_failed", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time on key"""
        try:
            return bool(await self._client.expire(self._make_key(key), seconds))
        except RedisError as e:
            logger.error("redis_expire_failed", key=key, error=str(e))
            return False
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return await self._client.incrby(self._make_key(key), amount)
        except RedisError as e:
            logger.error("redis_incr_failed", key=key, error=str(e))
            return 0
    
    async def keys_pattern(self, pattern: str) -> list[str]:
        """Get keys matching pattern (use sparingly!)"""
        try:
            full_pattern = self._make_key(pattern)
            keys = await self._client.keys(full_pattern)
            # Remove prefix from results
            prefix_len = len(self.key_prefix) + 1
            return [k[prefix_len:] for k in keys]
        except RedisError as e:
            logger.error("redis_keys_failed", pattern=pattern, error=str(e))
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            if self._client is None:
                return {
                    "status": "disconnected",
                    "healthy": False,
                    "error": "Client not initialized"
                }
            
            # Ping test
            latency_start = await self._client.time()
            await self._client.ping()
            latency_end = await self._client.time()
            
            latency_ms = (latency_end[0] - latency_start[0]) * 1000
            
            # Get info
            info = await self._client.info()
            
            return {
                "status": "connected",
                "healthy": True,
                "version": info.get("redis_version"),
                "latency_ms": round(latency_ms, 2),
                "connected_clients": info.get("connected_clients"),
                "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
                "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 1),
            }
            
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    @asynccontextmanager
    async def pipeline(self):
        """Context manager for Redis pipeline"""
        pipe = self._client.pipeline()
        try:
            yield pipe
            await pipe.execute()
        finally:
            await pipe.reset()


# Singleton instances for different use cases
cache_client = RedisClient(key_prefix="bibliograph:cache")
celery_client = RedisClient(key_prefix="bibliograph:celery")
