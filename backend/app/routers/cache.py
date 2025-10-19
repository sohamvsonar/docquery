"""
Cache management routes.
Provides endpoints for viewing cache statistics and managing caches.
"""

import logging
from fastapi import APIRouter, Depends, status
from typing import Dict, Any

from app.auth import get_current_user, admin_required
from app.models import User
from app.services.cache import cache_service

router = APIRouter(prefix="/cache", tags=["Cache"])
logger = logging.getLogger(__name__)


@router.get("/stats", status_code=status.HTTP_200_OK)
def get_cache_statistics(current_user: User = Depends(admin_required)) -> Dict[str, Any]:
    """
    Get cache statistics (admin only).

    Shows hit/miss rates for query and embedding caches.

    Args:
        current_user: Authenticated admin user

    Returns:
        Cache statistics
    """
    stats = cache_service.get_cache_stats()

    return {
        "cache_stats": stats,
        "message": "Cache statistics retrieved successfully"
    }


@router.post("/clear", status_code=status.HTTP_200_OK)
def clear_all_caches(current_user: User = Depends(admin_required)) -> Dict[str, Any]:
    """
    Clear all caches (admin only).

    Clears query cache, embedding cache, and token blacklist.

    Warning: This will force all queries to regenerate results and embeddings.

    Args:
        current_user: Authenticated admin user

    Returns:
        Number of keys cleared per cache type
    """
    results = cache_service.clear_all_caches()

    total_cleared = sum(results.values())

    logger.info(f"Admin {current_user.username} cleared all caches: {total_cleared} keys")

    return {
        "cleared": results,
        "total": total_cleared,
        "message": f"Successfully cleared {total_cleared} cache entries"
    }


@router.post("/clear/query", status_code=status.HTTP_200_OK)
def clear_query_cache(current_user: User = Depends(admin_required)) -> Dict[str, int]:
    """
    Clear query cache only (admin only).

    Args:
        current_user: Authenticated admin user

    Returns:
        Number of query cache keys cleared
    """
    cleared = cache_service.invalidate_query_cache()

    logger.info(f"Admin {current_user.username} cleared query cache: {cleared} keys")

    return {
        "cleared": cleared,
        "message": f"Successfully cleared {cleared} query cache entries"
    }


@router.post("/clear/embeddings", status_code=status.HTTP_200_OK)
def clear_embedding_cache(current_user: User = Depends(admin_required)) -> Dict[str, int]:
    """
    Clear embedding cache only (admin only).

    Args:
        current_user: Authenticated admin user

    Returns:
        Number of embedding cache keys cleared
    """
    cleared = cache_service._clear_cache(cache_service.EMBEDDING_CACHE_PREFIX)

    logger.info(f"Admin {current_user.username} cleared embedding cache: {cleared} keys")

    return {
        "cleared": cleared,
        "message": f"Successfully cleared {cleared} embedding cache entries"
    }


@router.post("/stats/reset", status_code=status.HTTP_200_OK)
def reset_cache_statistics(current_user: User = Depends(admin_required)) -> Dict[str, str]:
    """
    Reset cache statistics counters (admin only).

    Does not clear actual cached data, only resets hit/miss counters.

    Args:
        current_user: Authenticated admin user

    Returns:
        Success message
    """
    cache_service.reset_cache_stats()

    logger.info(f"Admin {current_user.username} reset cache statistics")

    return {
        "message": "Cache statistics reset successfully"
    }
