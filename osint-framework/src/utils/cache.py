"""
Redis Caching Layer for OSINT Framework

Purpose:
- Cache connector results to avoid redundant API calls
- Store graph and entity data for fast retrieval
- Cache expensive computations (matching, analytics)
- Implement TTL-based expiration strategies

Features:
- Connector result caching with configurable TTL
- Graph data caching
- Entity matching result caching
- Analytics result caching
- Cache statistics and monitoring
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib
import structlog

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheKey:
    """Cache key generation utilities."""
    
    @staticmethod
    def connector_result(connector_name: str, query: str, entity_id: str = "") -> str:
        """Generate cache key for connector result."""
        key_parts = [f"connector:{connector_name}"]
        key_parts.append(f"query:{hashlib.md5(query.encode()).hexdigest()[:8]}")
        if entity_id:
            key_parts.append(f"entity:{entity_id}")
        return ":".join(key_parts)
    
    @staticmethod
    def graph(investigation_id: str) -> str:
        """Generate cache key for graph data."""
        return f"graph:{investigation_id}"
    
    @staticmethod
    def entity_match(entity_id_1: str, entity_id_2: str) -> str:
        """Generate cache key for entity matching result."""
        sorted_ids = sorted([entity_id_1, entity_id_2])
        return f"entity_match:{':'.join(sorted_ids)}"
    
    @staticmethod
    def analytics_result(entity_id: str, analysis_type: str) -> str:
        """Generate cache key for analytics result."""
        return f"analytics:{analysis_type}:{entity_id}"
    
    @staticmethod
    def search_result(search_query: str, entity_type: str = "") -> str:
        """Generate cache key for search result."""
        query_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
        if entity_type:
            return f"search:{query_hash}:{entity_type}"
        return f"search:{query_hash}"


class RedisCache:
    """Redis-based caching layer for OSINT Framework."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
        """
        self.logger = structlog.get_logger(__name__)
        self.host = host
        self.port = port
        self.db = db
        self.redis = None
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis not available, using in-memory cache")
            self.local_cache = {}
    
    async def connect(self):
        """Connect to Redis server."""
        if not REDIS_AVAILABLE:
            return
        
        try:
            self.redis = await aioredis.create_redis_pool(
                f"redis://{self.host}:{self.port}",
                db=self.db,
                encoding="utf-8"
            )
            self.logger.info("Connected to Redis", host=self.host, port=self.port)
        except Exception as e:
            self.logger.warning(f"Failed to connect to Redis: {str(e)}, using in-memory cache")
            self.local_cache = {}
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
            self.logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            if self.redis:
                value = await self.redis.get(key)
                if value:
                    self.stats["hits"] += 1
                    try:
                        return json.loads(value)
                    except:
                        return value
                else:
                    self.stats["misses"] += 1
                    return None
            else:
                # Use local cache
                if key in self.local_cache:
                    cached_item = self.local_cache[key]
                    if cached_item["expires_at"] > datetime.utcnow():
                        self.stats["hits"] += 1
                        return cached_item["value"]
                    else:
                        del self.local_cache[key]
                        self.stats["misses"] += 1
                        return None
                else:
                    self.stats["misses"] += 1
                    return None
        except Exception as e:
            self.logger.error(f"Cache get failed", key=key, error=str(e))
            self.stats["errors"] += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 86400
    ) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
            
        Returns:
            Success status
        """
        try:
            if self.redis:
                json_value = json.dumps(value) if not isinstance(value, str) else value
                await self.redis.setex(key, ttl_seconds, json_value)
                self.stats["sets"] += 1
                return True
            else:
                # Use local cache
                self.local_cache[key] = {
                    "value": value,
                    "expires_at": datetime.utcnow() + timedelta(seconds=ttl_seconds)
                }
                self.stats["sets"] += 1
                return True
        except Exception as e:
            self.logger.error(f"Cache set failed", key=key, error=str(e))
            self.stats["errors"] += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Success status
        """
        try:
            if self.redis:
                await self.redis.delete(key)
                self.stats["deletes"] += 1
                return True
            else:
                if key in self.local_cache:
                    del self.local_cache[key]
                    self.stats["deletes"] += 1
                return True
        except Exception as e:
            self.logger.error(f"Cache delete failed", key=key, error=str(e))
            self.stats["errors"] += 1
            return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        try:
            if self.redis:
                await self.redis.flushdb()
                self.logger.info("Cache cleared")
                return True
            else:
                self.local_cache.clear()
                return True
        except Exception as e:
            self.logger.error(f"Cache clear failed", error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            if self.redis:
                return await self.redis.exists(key)
            else:
                if key in self.local_cache:
                    if self.local_cache[key]["expires_at"] > datetime.utcnow():
                        return True
                    else:
                        del self.local_cache[key]
                return False
        except Exception as e:
            self.logger.error(f"Cache exists check failed", error=str(e))
            return False
    
    # Connector-specific methods
    async def get_connector_result(
        self,
        connector_name: str,
        query: str,
        entity_id: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Get cached connector result."""
        key = CacheKey.connector_result(connector_name, query, entity_id)
        return await self.get(key)
    
    async def set_connector_result(
        self,
        connector_name: str,
        query: str,
        result: Dict[str, Any],
        ttl_seconds: int = 86400,
        entity_id: str = ""
    ) -> bool:
        """Cache connector result."""
        key = CacheKey.connector_result(connector_name, query, entity_id)
        return await self.set(key, result, ttl_seconds)
    
    # Graph-specific methods
    async def get_graph(self, investigation_id: str) -> Optional[Dict[str, Any]]:
        """Get cached graph data."""
        key = CacheKey.graph(investigation_id)
        return await self.get(key)
    
    async def set_graph(
        self,
        investigation_id: str,
        graph_data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> bool:
        """Cache graph data."""
        key = CacheKey.graph(investigation_id)
        return await self.set(key, graph_data, ttl_seconds)
    
    # Entity matching methods
    async def get_entity_match_score(
        self,
        entity_id_1: str,
        entity_id_2: str
    ) -> Optional[float]:
        """Get cached entity matching score."""
        key = CacheKey.entity_match(entity_id_1, entity_id_2)
        result = await self.get(key)
        return result.get("score") if result else None
    
    async def set_entity_match_score(
        self,
        entity_id_1: str,
        entity_id_2: str,
        score: float,
        confidence: float,
        ttl_seconds: int = 604800  # 7 days
    ) -> bool:
        """Cache entity matching result."""
        key = CacheKey.entity_match(entity_id_1, entity_id_2)
        return await self.set(
            key,
            {"score": score, "confidence": confidence, "timestamp": datetime.utcnow().isoformat()},
            ttl_seconds
        )
    
    # Analytics methods
    async def get_analytics_result(
        self,
        entity_id: str,
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached analytics result."""
        key = CacheKey.analytics_result(entity_id, analysis_type)
        return await self.get(key)
    
    async def set_analytics_result(
        self,
        entity_id: str,
        analysis_type: str,
        result: Dict[str, Any],
        ttl_seconds: int = 86400
    ) -> bool:
        """Cache analytics result."""
        key = CacheKey.analytics_result(entity_id, analysis_type)
        return await self.set(key, result, ttl_seconds)
    
    # Search methods
    async def get_search_result(
        self,
        search_query: str,
        entity_type: str = ""
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached search result."""
        key = CacheKey.search_result(search_query, entity_type)
        return await self.get(key)
    
    async def set_search_result(
        self,
        search_query: str,
        results: List[Dict[str, Any]],
        entity_type: str = "",
        ttl_seconds: int = 3600
    ) -> bool:
        """Cache search result."""
        key = CacheKey.search_result(search_query, entity_type)
        return await self.set(key, results, ttl_seconds)
    
    # Statistics methods
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total_requests if total_requests > 0 else 0.0
        )
        
        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate
        }
    
    def reset_stats(self):
        """Reset cache statistics."""
        for key in self.stats:
            self.stats[key] = 0
    
    async def cleanup_expired(self) -> int:
        """
        Cleanup expired entries (Redis handles this automatically,
        but useful for local cache).
        
        Returns:
            Number of entries cleaned up
        """
        if not self.redis:
            removed = 0
            expired_keys = []
            
            for key, cached_item in self.local_cache.items():
                if cached_item["expires_at"] < datetime.utcnow():
                    expired_keys.append(key)
                    removed += 1
            
            for key in expired_keys:
                del self.local_cache[key]
            
            return removed
        return 0


# Global cache instance
_cache_instance: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """Get or create global cache instance."""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = RedisCache()
        try:
            await _cache_instance.connect()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Cache initialization failed: {str(e)}")
    
    return _cache_instance


async def shutdown_cache():
    """Shutdown global cache instance."""
    global _cache_instance
    
    if _cache_instance:
        await _cache_instance.disconnect()
        _cache_instance = None
