"""
Case-Aware Query Cache Manager

This module implements a multi-tier caching system for context queries:

Tier 1: In-Memory Cache (fastest, 10-minute TTL)
- LRU cache with configurable size limit
- Per-process cache (not shared across instances)
- Best for frequently accessed active cases

Tier 2: Redis Cache (fast, 1-24 hour TTL)
- Shared across all service instances
- Active cases: 1 hour TTL
- Closed cases: 24 hour TTL
- Production-ready distributed caching

Tier 3: Database Cache (persistent)
- Permanent storage in context.cached_contexts table
- Fallback when Redis unavailable
- Historical context preservation

All cache keys include case_id for multi-tenant isolation.
"""

import logging
import asyncio
import json
import hashlib
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import OrderedDict
from dataclasses import dataclass

from src.models.dimensions import ContextResponse

logger = logging.getLogger(__name__)


# ============================================================================
# CACHE ENTRY MODEL
# ============================================================================

@dataclass
class CacheEntry:
    """
    Represents a cached context entry with metadata.

    Attributes:
        key: Cache key (hash of client_id, case_id, scope)
        value: Cached ContextResponse data
        created_at: When entry was cached
        expires_at: When entry expires
        hit_count: Number of times entry was accessed
        last_accessed: Last access timestamp
        case_status: Case status (active|closed) for TTL determination
    """
    key: str
    value: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: Optional[datetime] = None
    case_status: str = "active"

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() >= self.expires_at

    def increment_hits(self):
        """Increment hit count and update last accessed time"""
        self.hit_count += 1
        self.last_accessed = datetime.now()


# ============================================================================
# IN-MEMORY LRU CACHE (TIER 1)
# ============================================================================

class LRUCache:
    """
    In-memory LRU (Least Recently Used) cache with TTL support.

    This is the fastest cache tier but only available within a single process.
    Automatically evicts least recently used entries when size limit is reached.

    Attributes:
        max_size: Maximum number of entries to cache
        default_ttl: Default TTL in seconds (10 minutes)
        cache: Ordered dictionary for LRU eviction
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 600):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum cache size (default: 1000 entries)
            default_ttl: Default TTL in seconds (default: 600 = 10 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.logger = logging.getLogger(f"{__name__}.LRUCache")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get value from cache by key.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self.cache:
            return None

        entry = self.cache[key]

        # Check if expired
        if entry.is_expired():
            self.logger.debug(f"Cache entry expired: {key}")
            del self.cache[key]
            return None

        # Move to end (mark as recently used)
        self.cache.move_to_end(key)
        entry.increment_hits()

        self.logger.debug(
            f"Cache HIT: {key} (hits: {entry.hit_count}, "
            f"expires in: {(entry.expires_at - datetime.now()).seconds}s)"
        )

        return entry.value

    def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
        case_status: str = "active"
    ) -> None:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if not specified)
            case_status: Case status (active|closed) for metadata
        """
        # Use default TTL if not specified
        ttl = ttl or self.default_ttl

        # Create cache entry
        now = datetime.now()
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            case_status=case_status
        )

        # Add to cache
        self.cache[key] = entry
        self.cache.move_to_end(key)

        # Evict oldest if over limit
        if len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            self.logger.debug(f"Evicting oldest entry: {oldest_key}")
            del self.cache[oldest_key]

        self.logger.debug(
            f"Cache SET: {key} (ttl: {ttl}s, status: {case_status}, "
            f"size: {len(self.cache)}/{self.max_size})"
        )

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            self.logger.debug(f"Cache DELETE: {key}")
            return True
        return False

    def clear(self) -> int:
        """
        Clear all entries from cache.

        Returns:
            Number of entries cleared
        """
        count = len(self.cache)
        self.cache.clear()
        self.logger.info(f"Cache CLEARED: {count} entries removed")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_hits = sum(entry.hit_count for entry in self.cache.values())
        expired_count = sum(1 for entry in self.cache.values() if entry.is_expired())

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "utilization": len(self.cache) / self.max_size if self.max_size > 0 else 0.0,
            "total_hits": total_hits,
            "expired_entries": expired_count,
            "default_ttl_seconds": self.default_ttl
        }


# ============================================================================
# CACHE MANAGER (MULTI-TIER ORCHESTRATOR)
# ============================================================================

class CacheManager:
    """
    Multi-tier cache manager for context queries.

    Orchestrates caching across three tiers:
    1. In-memory LRU cache (fastest, 10-minute TTL)
    2. Redis cache (fast, 1-24 hour TTL) - TODO: implement
    3. Database cache (persistent) - TODO: implement

    The manager checks tiers in order (fastest to slowest) and populates
    faster tiers with data from slower tiers on cache misses.

    Case Status TTL Strategy:
    - Active cases: 1 hour TTL (frequent updates expected)
    - Closed cases: 24 hour TTL (stable, rarely change)

    All cache keys include case_id for multi-tenant isolation.
    """

    # TTL configurations (in seconds)
    MEMORY_TTL = 600  # 10 minutes (in-memory)
    ACTIVE_CASE_TTL = 3600  # 1 hour (Redis/DB for active cases)
    CLOSED_CASE_TTL = 86400  # 24 hours (Redis/DB for closed cases)

    def __init__(
        self,
        supabase_client: Any = None,
        redis_client: Any = None,
        enable_memory_cache: bool = True,
        enable_redis_cache: bool = False,  # Disabled by default until Redis configured
        enable_db_cache: bool = False  # Disabled by default until DB table created
    ):
        """
        Initialize cache manager with optional tier enablement.

        Args:
            supabase_client: Supabase client for database cache
            redis_client: Redis client for distributed cache
            enable_memory_cache: Enable in-memory LRU cache (Tier 1)
            enable_redis_cache: Enable Redis cache (Tier 2)
            enable_db_cache: Enable database cache (Tier 3)
        """
        self.supabase_client = supabase_client
        self.redis_client = redis_client

        # Tier enablement flags
        self.enable_memory_cache = enable_memory_cache
        self.enable_redis_cache = enable_redis_cache and redis_client is not None
        self.enable_db_cache = enable_db_cache and supabase_client is not None

        # Initialize in-memory cache (Tier 1)
        self.memory_cache = LRUCache(max_size=1000, default_ttl=self.MEMORY_TTL) if enable_memory_cache else None

        # Statistics
        self.stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "redis_hits": 0,
            "redis_misses": 0,
            "db_hits": 0,
            "db_misses": 0,
            "total_sets": 0,
            "total_deletes": 0
        }

        self.logger = logging.getLogger(__name__)

        self.logger.info(
            f"CacheManager initialized: "
            f"memory={enable_memory_cache}, "
            f"redis={self.enable_redis_cache}, "
            f"db={self.enable_db_cache}"
        )

    def _generate_cache_key(
        self,
        client_id: str,
        case_id: str,
        scope: str,
        dimension: Optional[str] = None
    ) -> str:
        """
        Generate cache key with case_id isolation.

        Args:
            client_id: Client identifier
            case_id: Case identifier
            scope: Context scope (minimal|standard|comprehensive)
            dimension: Optional specific dimension (WHO|WHAT|WHERE|WHEN|WHY)

        Returns:
            Cache key (MD5 hash for consistency)
        """
        # Build key components
        key_parts = [client_id, case_id, scope]
        if dimension:
            key_parts.append(dimension)

        # Create hash for consistency and length control
        key_string = ":".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        # Use readable format: context:{client_id}:{case_id}:{scope}:{hash}
        cache_key = f"context:{client_id}:{case_id}:{scope}:{key_hash[:8]}"

        return cache_key

    async def get(
        self,
        client_id: str,
        case_id: str,
        scope: str,
        dimension: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached context (check all tiers).

        Checks tiers in order (memory → Redis → database) and populates
        faster tiers when data found in slower tiers.

        Args:
            client_id: Client identifier
            case_id: Case identifier
            scope: Context scope
            dimension: Optional specific dimension

        Returns:
            Cached context data if found, None otherwise
        """
        cache_key = self._generate_cache_key(client_id, case_id, scope, dimension)

        # Tier 1: Check in-memory cache
        if self.enable_memory_cache and self.memory_cache:
            value = self.memory_cache.get(cache_key)
            if value is not None:
                self.stats["memory_hits"] += 1
                self.logger.debug(f"Memory cache HIT: {cache_key}")
                return value
            self.stats["memory_misses"] += 1

        # Tier 2: Check Redis cache (TODO: implement)
        if self.enable_redis_cache:
            value = await self._get_from_redis(cache_key)
            if value is not None:
                self.stats["redis_hits"] += 1
                self.logger.debug(f"Redis cache HIT: {cache_key}")
                # Populate memory cache
                if self.enable_memory_cache and self.memory_cache:
                    self.memory_cache.set(cache_key, value, ttl=self.MEMORY_TTL)
                return value
            self.stats["redis_misses"] += 1

        # Tier 3: Check database cache (TODO: implement)
        if self.enable_db_cache:
            value = await self._get_from_database(cache_key)
            if value is not None:
                self.stats["db_hits"] += 1
                self.logger.debug(f"Database cache HIT: {cache_key}")
                # Populate faster tiers
                if self.enable_redis_cache:
                    await self._set_in_redis(cache_key, value, ttl=self.ACTIVE_CASE_TTL)
                if self.enable_memory_cache and self.memory_cache:
                    self.memory_cache.set(cache_key, value, ttl=self.MEMORY_TTL)
                return value
            self.stats["db_misses"] += 1

        # Cache miss across all tiers
        self.logger.debug(f"Cache MISS (all tiers): {cache_key}")
        return None

    async def set(
        self,
        client_id: str,
        case_id: str,
        scope: str,
        value: Dict[str, Any],
        case_status: str = "active",
        dimension: Optional[str] = None
    ) -> None:
        """
        Set context in cache (all enabled tiers).

        Determines TTL based on case status:
        - Active cases: 1 hour (likely to change)
        - Closed cases: 24 hours (stable)

        Args:
            client_id: Client identifier
            case_id: Case identifier
            scope: Context scope
            value: Context data to cache
            case_status: Case status (active|closed) - determines TTL
            dimension: Optional specific dimension
        """
        cache_key = self._generate_cache_key(client_id, case_id, scope, dimension)

        # Determine TTL based on case status
        redis_db_ttl = self.ACTIVE_CASE_TTL if case_status == "active" else self.CLOSED_CASE_TTL

        # Set in all enabled tiers
        if self.enable_memory_cache and self.memory_cache:
            self.memory_cache.set(cache_key, value, ttl=self.MEMORY_TTL, case_status=case_status)

        if self.enable_redis_cache:
            await self._set_in_redis(cache_key, value, ttl=redis_db_ttl)

        if self.enable_db_cache:
            await self._set_in_database(cache_key, value, case_id=case_id, case_status=case_status)

        self.stats["total_sets"] += 1
        self.logger.debug(
            f"Cache SET: {cache_key} (status: {case_status}, "
            f"redis_ttl: {redis_db_ttl}s)"
        )

    async def delete(
        self,
        client_id: str,
        case_id: str,
        scope: Optional[str] = None,
        dimension: Optional[str] = None
    ) -> int:
        """
        Delete cached context (all tiers).

        If scope not specified, deletes all scopes for the case.

        Args:
            client_id: Client identifier
            case_id: Case identifier
            scope: Optional context scope (if None, deletes all scopes)
            dimension: Optional specific dimension

        Returns:
            Number of entries deleted
        """
        deleted_count = 0

        if scope:
            # Delete specific scope
            cache_key = self._generate_cache_key(client_id, case_id, scope, dimension)

            if self.enable_memory_cache and self.memory_cache:
                if self.memory_cache.delete(cache_key):
                    deleted_count += 1

            if self.enable_redis_cache:
                if await self._delete_from_redis(cache_key):
                    deleted_count += 1

            if self.enable_db_cache:
                if await self._delete_from_database(cache_key):
                    deleted_count += 1
        else:
            # Delete all scopes for case
            for scope_name in ["minimal", "standard", "comprehensive"]:
                cache_key = self._generate_cache_key(client_id, case_id, scope_name, dimension)

                if self.enable_memory_cache and self.memory_cache:
                    if self.memory_cache.delete(cache_key):
                        deleted_count += 1

                if self.enable_redis_cache:
                    if await self._delete_from_redis(cache_key):
                        deleted_count += 1

                if self.enable_db_cache:
                    if await self._delete_from_database(cache_key):
                        deleted_count += 1

        self.stats["total_deletes"] += deleted_count
        self.logger.info(
            f"Cache DELETE: case={case_id}, scope={scope or 'all'}, "
            f"deleted={deleted_count} entries"
        )

        return deleted_count

    async def invalidate_case(self, client_id: str, case_id: str) -> int:
        """
        Invalidate all cached contexts for a specific case.

        Use this when case data is updated and all cached contexts
        should be regenerated.

        Args:
            client_id: Client identifier
            case_id: Case identifier

        Returns:
            Number of entries invalidated
        """
        self.logger.info(f"Invalidating all cache for case: {case_id}")
        return await self.delete(client_id, case_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics across all tiers.

        Returns:
            Dictionary with cache statistics
        """
        stats = self.stats.copy()

        # Add memory cache stats if enabled
        if self.enable_memory_cache and self.memory_cache:
            stats["memory_cache"] = self.memory_cache.get_stats()

        # Calculate hit rates
        total_memory_ops = stats["memory_hits"] + stats["memory_misses"]
        total_redis_ops = stats["redis_hits"] + stats["redis_misses"]
        total_db_ops = stats["db_hits"] + stats["db_misses"]

        stats["memory_hit_rate"] = (
            stats["memory_hits"] / total_memory_ops if total_memory_ops > 0 else 0.0
        )
        stats["redis_hit_rate"] = (
            stats["redis_hits"] / total_redis_ops if total_redis_ops > 0 else 0.0
        )
        stats["db_hit_rate"] = (
            stats["db_hits"] / total_db_ops if total_db_ops > 0 else 0.0
        )

        # Overall hit rate (across all tiers)
        total_hits = stats["memory_hits"] + stats["redis_hits"] + stats["db_hits"]
        total_ops = total_memory_ops + total_redis_ops + total_db_ops
        stats["overall_hit_rate"] = total_hits / total_ops if total_ops > 0 else 0.0

        return stats

    def reset_stats(self) -> None:
        """Reset all statistics counters"""
        self.stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "redis_hits": 0,
            "redis_misses": 0,
            "db_hits": 0,
            "db_misses": 0,
            "total_sets": 0,
            "total_deletes": 0
        }
        self.logger.info("Cache statistics reset")

    # ========================================================================
    # REDIS CACHE OPERATIONS (TIER 2 - TODO)
    # ========================================================================

    async def _get_from_redis(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from Redis cache (placeholder)"""
        # TODO: Implement Redis integration
        return None

    async def _set_in_redis(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        """Set value in Redis cache (placeholder)"""
        # TODO: Implement Redis integration
        pass

    async def _delete_from_redis(self, key: str) -> bool:
        """Delete value from Redis cache (placeholder)"""
        # TODO: Implement Redis integration
        return False

    # ========================================================================
    # DATABASE CACHE OPERATIONS (TIER 3 - TODO)
    # ========================================================================

    async def _get_from_database(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from database cache (placeholder)"""
        # TODO: Implement database cache using context.cached_contexts table
        return None

    async def _set_in_database(
        self,
        key: str,
        value: Dict[str, Any],
        case_id: str,
        case_status: str
    ) -> None:
        """Set value in database cache (placeholder)"""
        # TODO: Implement database cache using context.cached_contexts table
        pass

    async def _delete_from_database(self, key: str) -> bool:
        """Delete value from database cache (placeholder)"""
        # TODO: Implement database cache deletion
        return False


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_cache_manager(
    supabase_client: Any = None,
    redis_client: Any = None,
    enable_memory_cache: bool = True,
    enable_redis_cache: bool = False,
    enable_db_cache: bool = False
) -> CacheManager:
    """
    Factory function to create CacheManager instance.

    Args:
        supabase_client: Supabase client for database cache
        redis_client: Redis client for distributed cache
        enable_memory_cache: Enable in-memory LRU cache (default: True)
        enable_redis_cache: Enable Redis cache (default: False)
        enable_db_cache: Enable database cache (default: False)

    Returns:
        Configured CacheManager instance

    Example:
        # Memory-only cache (fastest, single instance)
        cache = create_cache_manager()

        # Multi-tier cache with Redis
        cache = create_cache_manager(
            redis_client=redis_client,
            enable_memory_cache=True,
            enable_redis_cache=True
        )

        # Full multi-tier cache
        cache = create_cache_manager(
            supabase_client=supabase_client,
            redis_client=redis_client,
            enable_memory_cache=True,
            enable_redis_cache=True,
            enable_db_cache=True
        )
    """
    return CacheManager(
        supabase_client=supabase_client,
        redis_client=redis_client,
        enable_memory_cache=enable_memory_cache,
        enable_redis_cache=enable_redis_cache,
        enable_db_cache=enable_db_cache
    )
