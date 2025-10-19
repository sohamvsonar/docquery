"""
Test Redis connection for debugging cache issues.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.redis_client import get_redis
from app.services.cache import cache_service

def test_redis_connection():
    """Test Redis connection and basic operations."""
    print("Testing Redis connection...")

    try:
        redis = get_redis()
        print(f"[OK] Redis client obtained: {redis}")

        # Test ping
        result = redis.ping()
        print(f"[OK] Redis PING successful: {result}")

        # Test set/get
        redis.set("test_key", "test_value")
        value = redis.get("test_key")
        print(f"[OK] Redis SET/GET successful: {value}")

        # Delete test key
        redis.delete("test_key")

        # Test cache service
        print("\nTesting CacheService...")

        # Test embedding cache
        test_embedding = [0.1, 0.2, 0.3]
        success = cache_service.set_embedding_cache("test text", test_embedding)
        print(f"[OK] Set embedding cache: {success}")

        cached = cache_service.get_embedding_cache("test text")
        print(f"[OK] Get embedding cache: {cached is not None}")

        # Test query cache
        test_results = [{"chunk_id": 1, "content": "test"}]
        success = cache_service.set_query_cache(
            query="test query",
            k=5,
            search_type="hybrid",
            alpha=0.5,
            user_id=1,
            results=test_results
        )
        print(f"[OK] Set query cache: {success}")

        cached_results = cache_service.get_query_cache(
            query="test query",
            k=5,
            search_type="hybrid",
            alpha=0.5,
            user_id=1
        )
        print(f"[OK] Get query cache: {cached_results is not None}")

        # Test stats
        stats = cache_service.get_cache_stats()
        print(f"[OK] Get cache stats: {stats}")

        print("\n[SUCCESS] All Redis tests passed!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Redis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)
