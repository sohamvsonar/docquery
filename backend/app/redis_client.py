"""
Redis client utilities for caching, rate limiting, and session management.
"""

import redis
from typing import Optional
from app.config import settings

# Global Redis client instance
redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """
    Get or create Redis client connection.

    Returns:
        Redis client instance
    """
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5
        )
    return redis_client


def check_rate_limit(key: str, max_attempts: int, window_seconds: int = 60) -> bool:
    """
    Check if a rate limit has been exceeded using Redis.

    Args:
        key: Unique key for the rate limit (e.g., "login:192.168.1.1")
        max_attempts: Maximum number of attempts allowed
        window_seconds: Time window in seconds

    Returns:
        True if within rate limit, False if exceeded
    """
    try:
        client = get_redis()

        # Get current count
        current = client.get(key)

        if current is None:
            # First attempt, set counter with expiration
            client.setex(key, window_seconds, 1)
            return True

        current_count = int(current)

        if current_count >= max_attempts:
            # Rate limit exceeded
            return False

        # Increment counter
        client.incr(key)
        return True

    except redis.RedisError:
        # If Redis is unavailable, allow the request (fail open)
        # In production, you might want to fail closed or log this
        return True


def reset_rate_limit(key: str) -> None:
    """
    Reset a rate limit counter.

    Args:
        key: Rate limit key to reset
    """
    try:
        client = get_redis()
        client.delete(key)
    except redis.RedisError:
        pass  # Silently fail if Redis is unavailable
