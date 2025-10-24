"""
Cache Management API Routes

Provides endpoints for managing the multi-tier context cache system.
Includes cache statistics, invalidation, and configuration.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.routes.context import get_context_builder

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CacheInvalidationRequest(BaseModel):
    """Request model for cache invalidation"""
    client_id: str = Field(..., description="Client identifier")
    case_id: str = Field(..., description="Case identifier to invalidate")
    scope: Optional[str] = Field(
        default=None,
        description="Specific scope to invalidate (if None, invalidates all scopes)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client-abc-123",
                "case_id": "case-xyz-456",
                "scope": "comprehensive"
            }
        }


# ============================================================================
# CACHE STATISTICS
# ============================================================================

@router.get("/stats")
async def get_cache_stats():
    """
    Get comprehensive cache statistics across all tiers.

    Returns metrics for:
    - Memory cache (Tier 1): size, utilization, hit rate
    - Redis cache (Tier 2): hits, misses, hit rate (if enabled)
    - Database cache (Tier 3): hits, misses, hit rate (if enabled)
    - Overall cache performance

    **Example Response:**
    ```json
    {
        "memory_hits": 1523,
        "memory_misses": 347,
        "memory_hit_rate": 0.8145,
        "redis_hits": 245,
        "redis_misses": 102,
        "redis_hit_rate": 0.7060,
        "db_hits": 18,
        "db_misses": 84,
        "db_hit_rate": 0.1765,
        "total_sets": 449,
        "total_deletes": 23,
        "overall_hit_rate": 0.7821,
        "memory_cache": {
            "size": 847,
            "max_size": 1000,
            "utilization": 0.847,
            "total_hits": 1523,
            "expired_entries": 12,
            "default_ttl_seconds": 600
        }
    }
    ```
    """
    try:
        logger.info("Fetching cache statistics")

        # Get context builder (which holds cache manager)
        builder = get_context_builder()

        # Get cache stats
        stats = builder.cache_manager.get_stats()

        logger.info(
            f"Cache stats retrieved: overall_hit_rate={stats['overall_hit_rate']:.2%}, "
            f"memory_utilization={stats.get('memory_cache', {}).get('utilization', 0):.2%}"
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.post("/stats/reset")
async def reset_cache_stats():
    """
    Reset cache statistics counters to zero.

    Useful for benchmarking and testing. Does not clear cached data,
    only resets the statistics counters.

    **Example Response:**
    ```json
    {
        "message": "Cache statistics reset successfully",
        "previous_stats": {...},
        "new_stats": {...}
    }
    ```
    """
    try:
        logger.info("Resetting cache statistics")

        builder = get_context_builder()

        # Get stats before reset
        previous_stats = builder.cache_manager.get_stats()

        # Reset stats
        builder.cache_manager.reset_stats()

        # Get stats after reset
        new_stats = builder.cache_manager.get_stats()

        logger.info("Cache statistics reset successfully")

        return {
            "message": "Cache statistics reset successfully",
            "previous_stats": previous_stats,
            "new_stats": new_stats
        }

    except Exception as e:
        logger.error(f"Failed to reset cache stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset cache stats: {str(e)}")


# ============================================================================
# CACHE INVALIDATION
# ============================================================================

@router.delete("/invalidate")
async def invalidate_cache(
    client_id: str = Query(..., description="Client identifier"),
    case_id: str = Query(..., description="Case identifier"),
    scope: Optional[str] = Query(
        default=None,
        description="Specific scope to invalidate (if not specified, invalidates all scopes)"
    )
):
    """
    Invalidate cached context for a specific case.

    Use this endpoint when case data has been updated and cached context
    should be regenerated. Invalidates across all cache tiers (memory, Redis, database).

    **Query Parameters:**
    - `client_id` (required): Client identifier
    - `case_id` (required): Case identifier to invalidate
    - `scope` (optional): Specific scope to invalidate (minimal/standard/comprehensive)
      - If not specified, invalidates all scopes for the case

    **Example:**
    ```
    DELETE /api/v1/cache/invalidate?client_id=client-123&case_id=case-456
    DELETE /api/v1/cache/invalidate?client_id=client-123&case_id=case-456&scope=comprehensive
    ```

    **Example Response:**
    ```json
    {
        "message": "Cache invalidated successfully",
        "client_id": "client-abc-123",
        "case_id": "case-xyz-456",
        "scope": "all",
        "entries_deleted": 3
    }
    ```
    """
    try:
        logger.info(
            f"Cache invalidation request: case={case_id}, scope={scope or 'all'}"
        )

        builder = get_context_builder()

        # Delete from cache
        deleted_count = await builder.cache_manager.delete(
            client_id=client_id,
            case_id=case_id,
            scope=scope
        )

        logger.info(
            f"Cache invalidated: case={case_id}, deleted={deleted_count} entries"
        )

        return {
            "message": "Cache invalidated successfully",
            "client_id": client_id,
            "case_id": case_id,
            "scope": scope or "all",
            "entries_deleted": deleted_count
        }

    except Exception as e:
        logger.error(f"Cache invalidation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")


@router.post("/invalidate/case")
async def invalidate_case_cache(
    client_id: str = Query(..., description="Client identifier"),
    case_id: str = Query(..., description="Case identifier")
):
    """
    Invalidate all cached contexts for a specific case.

    Convenience endpoint that invalidates all scopes and dimensions for a case.
    Equivalent to calling /invalidate without scope parameter.

    **Example:**
    ```
    POST /api/v1/cache/invalidate/case?client_id=client-123&case_id=case-456
    ```

    **Example Response:**
    ```json
    {
        "message": "All cache for case invalidated successfully",
        "case_id": "case-xyz-456",
        "entries_deleted": 15
    }
    ```
    """
    try:
        logger.info(f"Invalidating all cache for case: {case_id}")

        builder = get_context_builder()

        # Invalidate all cache for case
        deleted_count = await builder.cache_manager.invalidate_case(
            client_id=client_id,
            case_id=case_id
        )

        logger.info(f"All cache invalidated for case {case_id}: {deleted_count} entries")

        return {
            "message": "All cache for case invalidated successfully",
            "case_id": case_id,
            "entries_deleted": deleted_count
        }

    except Exception as e:
        logger.error(f"Case cache invalidation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Case cache invalidation failed: {str(e)}")


# ============================================================================
# CACHE WARMUP
# ============================================================================

class CacheWarmupRequest(BaseModel):
    """Request model for cache warmup"""
    client_id: str = Field(..., description="Client identifier")
    case_ids: list[str] = Field(..., description="List of case IDs to warm up")
    scope: str = Field(default="standard", description="Context scope to warm up")

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client-abc-123",
                "case_ids": ["case-1", "case-2", "case-3"],
                "scope": "standard"
            }
        }


@router.post("/warmup")
async def warmup_cache(request: CacheWarmupRequest):
    """
    Pre-warm cache for multiple cases.

    Useful for preparing cache before high-traffic periods or after
    system restart. Builds and caches context for specified cases.

    **Example Request:**
    ```json
    {
        "client_id": "client-abc-123",
        "case_ids": ["case-1", "case-2", "case-3"],
        "scope": "standard"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "Cache warmup completed",
        "total_cases": 3,
        "successful": 3,
        "failed": 0,
        "errors": {}
    }
    ```
    """
    try:
        logger.info(
            f"Cache warmup request: {len(request.case_ids)} cases, scope={request.scope}"
        )

        builder = get_context_builder()

        results = {
            "total_cases": len(request.case_ids),
            "successful": 0,
            "failed": 0,
            "errors": {}
        }

        # Warm up cache for each case
        for case_id in request.case_ids:
            try:
                # Build context (will be cached)
                await builder.build_context(
                    client_id=request.client_id,
                    case_id=case_id,
                    scope=request.scope,
                    use_cache=False  # Force rebuild to ensure fresh cache
                )
                results["successful"] += 1

            except Exception as e:
                logger.error(f"Failed to warm cache for case {case_id}: {str(e)}")
                results["errors"][case_id] = str(e)
                results["failed"] += 1

        logger.info(
            f"Cache warmup complete: {results['successful']}/{results['total_cases']} successful"
        )

        return {
            "message": "Cache warmup completed",
            **results
        }

    except Exception as e:
        logger.error(f"Cache warmup failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cache warmup failed: {str(e)}")


# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

@router.get("/config")
async def get_cache_config():
    """
    Get current cache configuration.

    Returns TTL settings and tier enablement status.

    **Example Response:**
    ```json
    {
        "tiers": {
            "memory": {
                "enabled": true,
                "ttl_seconds": 600,
                "max_size": 1000
            },
            "redis": {
                "enabled": false,
                "active_case_ttl_seconds": 3600,
                "closed_case_ttl_seconds": 86400
            },
            "database": {
                "enabled": false
            }
        },
        "ttl_strategy": {
            "memory": "10 minutes",
            "active_cases": "1 hour (Redis/DB)",
            "closed_cases": "24 hours (Redis/DB)"
        }
    }
    ```
    """
    try:
        logger.info("Fetching cache configuration")

        builder = get_context_builder()
        cache_manager = builder.cache_manager

        config = {
            "tiers": {
                "memory": {
                    "enabled": cache_manager.enable_memory_cache,
                    "ttl_seconds": cache_manager.MEMORY_TTL,
                    "max_size": cache_manager.memory_cache.max_size if cache_manager.memory_cache else 0
                },
                "redis": {
                    "enabled": cache_manager.enable_redis_cache,
                    "active_case_ttl_seconds": cache_manager.ACTIVE_CASE_TTL,
                    "closed_case_ttl_seconds": cache_manager.CLOSED_CASE_TTL
                },
                "database": {
                    "enabled": cache_manager.enable_db_cache
                }
            },
            "ttl_strategy": {
                "memory": f"{cache_manager.MEMORY_TTL // 60} minutes",
                "active_cases": f"{cache_manager.ACTIVE_CASE_TTL // 3600} hour (Redis/DB)",
                "closed_cases": f"{cache_manager.CLOSED_CASE_TTL // 3600} hours (Redis/DB)"
            }
        }

        return config

    except Exception as e:
        logger.error(f"Failed to get cache config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cache config: {str(e)}")


# ============================================================================
# CACHE HEALTH CHECK
# ============================================================================

@router.get("/health")
async def cache_health():
    """
    Check cache system health.

    Returns status of all cache tiers and overall health.

    **Example Response:**
    ```json
    {
        "status": "healthy",
        "tiers": {
            "memory": {
                "status": "healthy",
                "utilization": 0.847,
                "hit_rate": 0.8145
            },
            "redis": {
                "status": "disabled"
            },
            "database": {
                "status": "disabled"
            }
        },
        "overall_hit_rate": 0.8145
    }
    ```
    """
    try:
        logger.info("Checking cache health")

        builder = get_context_builder()
        stats = builder.cache_manager.get_stats()

        # Determine health status
        memory_healthy = stats.get("memory_hit_rate", 0) > 0.5  # >50% hit rate is healthy
        overall_healthy = memory_healthy or stats.get("overall_hit_rate", 0) > 0.5

        health_status = {
            "status": "healthy" if overall_healthy else "degraded",
            "tiers": {
                "memory": {
                    "status": "healthy" if memory_healthy else "degraded",
                    "utilization": stats.get("memory_cache", {}).get("utilization", 0),
                    "hit_rate": stats.get("memory_hit_rate", 0)
                },
                "redis": {
                    "status": "enabled" if builder.cache_manager.enable_redis_cache else "disabled"
                },
                "database": {
                    "status": "enabled" if builder.cache_manager.enable_db_cache else "disabled"
                }
            },
            "overall_hit_rate": stats.get("overall_hit_rate", 0)
        }

        return health_status

    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }
