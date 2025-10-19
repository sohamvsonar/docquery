"""
Caching service for performance optimization.
Handles query caching, embedding caching, and token blacklisting.
"""

import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta

from app.redis_client import get_redis

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis-based caching service for DocQuery.

    Features:
    - Query result caching with TTL
    - Embedding caching for frequent queries
    - Token blacklisting for logout
    - Cache statistics and management
    """

    def __init__(self):
        """Initialize cache service."""
        self.redis = get_redis()

        # Cache key prefixes
        self.QUERY_CACHE_PREFIX = "query_cache:"
        self.EMBEDDING_CACHE_PREFIX = "embedding_cache:"
        self.TOKEN_BLACKLIST_PREFIX = "token_blacklist:"
        self.CACHE_STATS_KEY = "cache_stats"

        # Default TTLs (in seconds)
        self.QUERY_CACHE_TTL = 3600  # 1 hour
        self.EMBEDDING_CACHE_TTL = 86400  # 24 hours
        self.TOKEN_BLACKLIST_TTL = 86400  # 24 hours (match token expiry)

    def _make_cache_key(self, prefix: str, identifier: str) -> str:
        """
        Create a cache key with prefix.

        Args:
            prefix: Cache key prefix
            identifier: Unique identifier

        Returns:
            Full cache key
        """
        return f"{prefix}{identifier}"

    def _hash_query(
        self,
        query: str,
        k: int,
        search_type: str,
        alpha: float,
        user_id: int
    ) -> str:
        """
        Create a hash for query caching.

        Args:
            query: Query text
            k: Number of results
            search_type: Search type
            alpha: Alpha parameter
            user_id: User ID (for access control)

        Returns:
            Query hash (hex string)
        """
        query_data = f"{query}|{k}|{search_type}|{alpha}|{user_id}"
        return hashlib.sha256(query_data.encode()).hexdigest()

    # ========================================================================
    # Query Result Caching
    # ========================================================================

    def get_query_cache(
        self,
        query: str,
        k: int,
        search_type: str,
        alpha: float,
        user_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached query results.

        Args:
            query: Query text
            k: Number of results
            search_type: Search type
            alpha: Alpha parameter
            user_id: User ID

        Returns:
            Cached search results or None if not cached
        """
        try:
            query_hash = self._hash_query(query, k, search_type, alpha, user_id)
            cache_key = self._make_cache_key(self.QUERY_CACHE_PREFIX, query_hash)

            cached_data = self.redis.get(cache_key)

            if cached_data:
                logger.info(f"Query cache HIT for query: {query[:50]}...")
                self._increment_cache_stat("query_hits")
                return json.loads(cached_data)
            else:
                logger.debug(f"Query cache MISS for query: {query[:50]}...")
                self._increment_cache_stat("query_misses")
                return None

        except Exception as e:
            logger.warning(f"Failed to get query cache: {e}")
            return None

    def set_query_cache(
        self,
        query: str,
        k: int,
        search_type: str,
        alpha: float,
        user_id: int,
        results: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache query results.

        Args:
            query: Query text
            k: Number of results
            search_type: Search type
            alpha: Alpha parameter
            user_id: User ID
            results: Search results to cache
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if cached successfully
        """
        try:
            query_hash = self._hash_query(query, k, search_type, alpha, user_id)
            cache_key = self._make_cache_key(self.QUERY_CACHE_PREFIX, query_hash)

            # Serialize results
            cached_data = json.dumps(results)

            # Set with TTL
            ttl = ttl or self.QUERY_CACHE_TTL
            self.redis.setex(cache_key, ttl, cached_data)

            logger.debug(f"Cached query results: {query[:50]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Failed to set query cache: {e}")
            return False

    def invalidate_query_cache(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate query cache.

        Args:
            pattern: Optional pattern to match keys (e.g., "*user_123*")
                    If None, invalidates all query cache

        Returns:
            Number of keys deleted
        """
        try:
            if pattern:
                search_pattern = self._make_cache_key(self.QUERY_CACHE_PREFIX, pattern)
            else:
                search_pattern = self._make_cache_key(self.QUERY_CACHE_PREFIX, "*")

            keys = list(self.redis.scan_iter(match=search_pattern))

            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} query cache entries")
                return deleted

            return 0

        except Exception as e:
            logger.warning(f"Failed to invalidate query cache: {e}")
            return 0

    # ========================================================================
    # Embedding Caching
    # ========================================================================

    def get_embedding_cache(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text.

        Args:
            text: Text to get embedding for

        Returns:
            Cached embedding vector or None
        """
        try:
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            cache_key = self._make_cache_key(self.EMBEDDING_CACHE_PREFIX, text_hash)

            cached_data = self.redis.get(cache_key)

            if cached_data:
                logger.debug(f"Embedding cache HIT for text: {text[:30]}...")
                self._increment_cache_stat("embedding_hits")
                return json.loads(cached_data)
            else:
                logger.debug(f"Embedding cache MISS for text: {text[:30]}...")
                self._increment_cache_stat("embedding_misses")
                return None

        except Exception as e:
            logger.warning(f"Failed to get embedding cache: {e}")
            return None

    def set_embedding_cache(
        self,
        text: str,
        embedding: List[float],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache embedding for text.

        Args:
            text: Text
            embedding: Embedding vector
            ttl: Time to live in seconds (default: 24 hours)

        Returns:
            True if cached successfully
        """
        try:
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            cache_key = self._make_cache_key(self.EMBEDDING_CACHE_PREFIX, text_hash)

            # Serialize embedding
            cached_data = json.dumps(embedding)

            # Set with TTL
            ttl = ttl or self.EMBEDDING_CACHE_TTL
            self.redis.setex(cache_key, ttl, cached_data)

            logger.debug(f"Cached embedding for text: {text[:30]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Failed to set embedding cache: {e}")
            return False

    # ========================================================================
    # Token Blacklisting (for Logout)
    # ========================================================================

    def blacklist_token(self, token: str, ttl: Optional[int] = None) -> bool:
        """
        Add token to blacklist (for logout).

        Args:
            token: JWT token to blacklist
            ttl: Time to live in seconds (default: 24 hours)

        Returns:
            True if blacklisted successfully
        """
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            cache_key = self._make_cache_key(self.TOKEN_BLACKLIST_PREFIX, token_hash)

            # Set with TTL (token will auto-expire)
            ttl = ttl or self.TOKEN_BLACKLIST_TTL
            self.redis.setex(cache_key, ttl, "blacklisted")

            logger.info(f"Blacklisted token: {token_hash[:16]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Failed to blacklist token: {e}")
            return False

    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted
        """
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            cache_key = self._make_cache_key(self.TOKEN_BLACKLIST_PREFIX, token_hash)

            exists = self.redis.exists(cache_key)
            return bool(exists)

        except Exception as e:
            logger.warning(f"Failed to check token blacklist: {e}")
            # Fail open - allow access if Redis is down
            return False

    # ========================================================================
    # Cache Statistics
    # ========================================================================

    def _increment_cache_stat(self, stat_name: str) -> None:
        """
        Increment cache statistic counter.

        Args:
            stat_name: Statistic name (e.g., "query_hits", "query_misses")
        """
        try:
            self.redis.hincrby(self.CACHE_STATS_KEY, stat_name, 1)
        except Exception as e:
            logger.debug(f"Failed to increment cache stat {stat_name}: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            stats = self.redis.hgetall(self.CACHE_STATS_KEY)

            # Handle both bytes and string returns from Redis
            if not stats:
                # No stats yet, return empty stats
                stats_dict = {}
            else:
                stats_dict = {}
                for k, v in stats.items():
                    # Decode if bytes, otherwise use as-is
                    key = k.decode() if isinstance(k, bytes) else k
                    value_str = v.decode() if isinstance(v, bytes) else v
                    stats_dict[key] = int(value_str)

            # Calculate hit rates
            query_hits = stats_dict.get("query_hits", 0)
            query_misses = stats_dict.get("query_misses", 0)
            query_total = query_hits + query_misses

            embedding_hits = stats_dict.get("embedding_hits", 0)
            embedding_misses = stats_dict.get("embedding_misses", 0)
            embedding_total = embedding_hits + embedding_misses

            return {
                "query_cache": {
                    "hits": query_hits,
                    "misses": query_misses,
                    "total": query_total,
                    "hit_rate": round(query_hits / query_total * 100, 2) if query_total > 0 else 0
                },
                "embedding_cache": {
                    "hits": embedding_hits,
                    "misses": embedding_misses,
                    "total": embedding_total,
                    "hit_rate": round(embedding_hits / embedding_total * 100, 2) if embedding_total > 0 else 0
                }
            }

        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {}

    def reset_cache_stats(self) -> bool:
        """
        Reset cache statistics.

        Returns:
            True if reset successfully
        """
        try:
            self.redis.delete(self.CACHE_STATS_KEY)
            logger.info("Reset cache statistics")
            return True
        except Exception as e:
            logger.warning(f"Failed to reset cache stats: {e}")
            return False

    def clear_all_caches(self) -> Dict[str, int]:
        """
        Clear all caches (query, embedding, token blacklist).

        Returns:
            Dictionary with counts of deleted keys per cache type
        """
        try:
            results = {
                "query_cache": self.invalidate_query_cache(),
                "embedding_cache": self._clear_cache(self.EMBEDDING_CACHE_PREFIX),
                "token_blacklist": self._clear_cache(self.TOKEN_BLACKLIST_PREFIX)
            }

            total = sum(results.values())
            logger.info(f"Cleared all caches: {total} keys deleted")

            return results

        except Exception as e:
            logger.warning(f"Failed to clear all caches: {e}")
            return {}

    def _clear_cache(self, prefix: str) -> int:
        """
        Clear cache by prefix.

        Args:
            prefix: Cache key prefix

        Returns:
            Number of keys deleted
        """
        try:
            search_pattern = f"{prefix}*"
            keys = list(self.redis.scan_iter(match=search_pattern))

            if keys:
                return self.redis.delete(*keys)

            return 0

        except Exception as e:
            logger.warning(f"Failed to clear cache with prefix {prefix}: {e}")
            return 0


# Global instance
cache_service = CacheService()
