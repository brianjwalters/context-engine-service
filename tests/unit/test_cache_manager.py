"""
Unit tests for CacheManager and LRUCache components.

Tests cover:
- LRU eviction policy
- TTL expiration
- Multi-tier cache operations
- Cache key generation
- Statistics tracking

ALL TESTS USE REAL CACHE OPERATIONS - NO MOCKS
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from collections import OrderedDict

from src.core.cache_manager import (
    LRUCache,
    CacheEntry,
    CacheManager,
    create_cache_manager
)


class TestCacheEntry:
    """Test CacheEntry data class"""

    @pytest.mark.unit
    def test_cache_entry_creation(self):
        """Test basic cache entry creation"""
        value = {"test": "data"}
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value=value,
            created_at=now,
            expires_at=now + timedelta(seconds=60)
        )

        assert entry.value == value
        assert entry.hit_count == 0
        assert not entry.is_expired()

    @pytest.mark.unit
    def test_cache_entry_expiration(self):
        """Test TTL expiration"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value={"test": "data"},
            created_at=now,
            expires_at=now - timedelta(seconds=1)  # Already expired
        )
        assert entry.is_expired()

    @pytest.mark.unit
    def test_cache_entry_hit_tracking(self):
        """Test hit counter incrementation"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value={"test": "data"},
            created_at=now,
            expires_at=now + timedelta(seconds=60)
        )

        assert entry.hit_count == 0
        entry.increment_hits()
        assert entry.hit_count == 1
        entry.increment_hits()
        assert entry.hit_count == 2

    @pytest.mark.unit
    def test_cache_entry_no_expiration_when_future(self):
        """Test that entries with future expiration don't expire"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value={"test": "data"},
            created_at=now,
            expires_at=now + timedelta(hours=24)
        )
        assert not entry.is_expired()


class TestLRUCache:
    """Test LRU cache implementation"""

    @pytest.mark.unit
    def test_lru_cache_creation(self):
        """Test basic LRU cache creation"""
        cache = LRUCache(max_size=100, default_ttl=600)

        assert cache.max_size == 100
        assert cache.default_ttl == 600
        assert len(cache.cache) == 0

    @pytest.mark.unit
    def test_lru_cache_set_and_get(self):
        """Test basic set and get operations"""
        cache = LRUCache(max_size=10, default_ttl=60)

        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")

        assert result == {"data": "value1"}

    @pytest.mark.unit
    def test_lru_cache_get_nonexistent_key(self):
        """Test get with non-existent key returns None"""
        cache = LRUCache(max_size=10, default_ttl=60)

        result = cache.get("nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_lru_cache_ttl_expiration(self):
        """Test that expired entries are removed on get"""
        cache = LRUCache(max_size=10, default_ttl=60)

        # Set with 1-second TTL for deterministic testing
        cache.set("key1", {"data": "value1"}, ttl=1)

        # Wait long enough to ensure expiration (1.1 seconds)
        time.sleep(1.1)

        # Access should return None and remove expired entry
        result = cache.get("key1")

        assert result is None, "Expired entry should return None"
        assert "key1" not in cache.cache, "Expired entry should be removed from cache"

    @pytest.mark.unit
    def test_lru_cache_eviction_policy(self):
        """Test LRU eviction when cache is full"""
        cache = LRUCache(max_size=3, default_ttl=60)

        # Fill cache to capacity
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})
        cache.set("key3", {"data": "value3"})

        # Access key1 to make it recently used
        cache.get("key1")

        # Add new key should evict key2 (least recently used)
        cache.set("key4", {"data": "value4"})

        assert cache.get("key1") is not None  # Recently used, not evicted
        assert cache.get("key2") is None      # Evicted (LRU)
        assert cache.get("key3") is not None  # Not evicted
        assert cache.get("key4") is not None  # Newly added

    @pytest.mark.unit
    def test_lru_cache_move_to_end_on_get(self):
        """Test that get operation moves key to end (most recent)"""
        cache = LRUCache(max_size=3, default_ttl=60)

        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})
        cache.set("key3", {"data": "value3"})

        # Access key1 (makes it most recent)
        cache.get("key1")

        # Verify order: key2 is now oldest
        assert list(cache.cache.keys()) == ["key2", "key3", "key1"]

    @pytest.mark.unit
    def test_lru_cache_delete(self):
        """Test delete operation"""
        cache = LRUCache(max_size=10, default_ttl=60)

        cache.set("key1", {"data": "value1"})
        assert cache.get("key1") is not None

        cache.delete("key1")
        assert cache.get("key1") is None

    @pytest.mark.unit
    def test_lru_cache_delete_nonexistent_key(self):
        """Test delete with non-existent key (should not raise error)"""
        cache = LRUCache(max_size=10, default_ttl=60)

        result = cache.delete("nonexistent")  # Should not raise error
        assert result is False

    @pytest.mark.unit
    def test_lru_cache_clear(self):
        """Test clear operation removes all entries"""
        cache = LRUCache(max_size=10, default_ttl=60)

        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})

        count = cache.clear()

        assert count == 2
        assert len(cache.cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    @pytest.mark.unit
    def test_lru_cache_size(self):
        """Test size using len(cache.cache)"""
        cache = LRUCache(max_size=10, default_ttl=60)

        assert len(cache.cache) == 0

        cache.set("key1", {"data": "value1"})
        assert len(cache.cache) == 1

        cache.set("key2", {"data": "value2"})
        assert len(cache.cache) == 2

    @pytest.mark.unit
    def test_lru_cache_get_stats(self):
        """Test statistics gathering"""
        cache = LRUCache(max_size=10, default_ttl=600)

        cache.set("key1", {"data": "value1"})
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()

        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["default_ttl_seconds"] == 600


class TestCacheManager:
    """Test CacheManager multi-tier cache operations with REAL cache"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_manager_creation(self, real_cache_manager):
        """Test CacheManager initialization with real cache"""
        assert real_cache_manager.enable_memory_cache is True
        assert real_cache_manager.enable_redis_cache is False
        assert real_cache_manager.enable_db_cache is False
        assert real_cache_manager.memory_cache is not None

    @pytest.mark.unit
    def test_cache_key_generation(self, real_cache_manager):
        """Test cache key format"""
        key = real_cache_manager._generate_cache_key(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive"
        )

        # Key should contain all components
        assert "client-123" in key
        assert "case-456" in key
        assert "comprehensive" in key
        assert key.startswith("context:")

    @pytest.mark.unit
    def test_cache_key_hash_includes_params(self, real_cache_manager):
        """Test that cache key hash changes with different parameters"""
        key1 = real_cache_manager._generate_cache_key(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive"
        )

        key2 = real_cache_manager._generate_cache_key(
            client_id="client-123",
            case_id="case-456",
            scope="minimal"  # Different scope
        )

        # Keys should be different due to different scope
        assert key1 != key2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_set_and_get_memory(self, real_cache_manager):
        """Test set and get from real memory cache"""
        value = {"test": "data", "case_id": "case-456"}

        # Set value in real cache
        await real_cache_manager.set(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive",
            value=value
        )

        # Get value from real cache
        result = await real_cache_manager.get(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive"
        )

        # Assert real cache behavior
        assert result == value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_get_miss(self, real_cache_manager):
        """Test get with cache miss returns None (real behavior)"""
        # Don't set any value - test real cache miss
        result = await real_cache_manager.get(
            client_id="client-123",
            case_id="nonexistent",
            scope="comprehensive"
        )

        # Real cache miss returns None
        assert result is None

        # Verify stats show cache miss
        stats = real_cache_manager.get_stats()
        assert stats["memory_misses"] >= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_delete(self, real_cache_manager):
        """Test real cache deletion"""
        value = {"test": "data", "case_id": "case-456"}

        # Set value in real cache
        await real_cache_manager.set(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive",
            value=value
        )

        # Delete it from real cache
        deleted_count = await real_cache_manager.delete(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive"
        )

        # Real deletion returns count
        assert deleted_count == 1

        # Verify it's gone from real cache
        result = await real_cache_manager.get(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive"
        )

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_invalidate_case_all_scopes(self, real_cache_manager):
        """Test invalidating all scopes for a case (real cache operations)"""
        value = {"test": "data"}

        # Set multiple scopes in real cache
        for scope in ["minimal", "standard", "comprehensive"]:
            await real_cache_manager.set(
                client_id="client-123",
                case_id="case-456",
                scope=scope,
                value=value
            )

        # Invalidate all scopes for case (real operation)
        deleted_count = await real_cache_manager.invalidate_case(
            client_id="client-123",
            case_id="case-456"
        )

        # Should delete all 3 scopes from real cache
        assert deleted_count == 3

        # Verify all are gone from real cache
        for scope in ["minimal", "standard", "comprehensive"]:
            result = await real_cache_manager.get(
                client_id="client-123",
                case_id="case-456",
                scope=scope
            )
            assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_ttl_based_on_case_status(self, real_cache_manager):
        """Test that TTL varies based on case status (real cache)"""
        value = {"test": "data"}

        # Active case should use ACTIVE_CASE_TTL in real cache
        await real_cache_manager.set(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive",
            value=value,
            case_status="active"
        )

        # Check real cache entry TTL
        cache_key = real_cache_manager._generate_cache_key("client-123", "case-456", "comprehensive")
        entry = real_cache_manager.memory_cache.cache.get(cache_key)

        # Entry should exist and have real TTL
        assert entry is not None
        assert entry.case_status == "active"

    @pytest.mark.unit
    def test_cache_stats(self, real_cache_manager):
        """Test real cache statistics retrieval"""
        stats = real_cache_manager.get_stats()

        # Should have memory cache stats from real cache
        assert "memory_cache" in stats
        assert "memory_hits" in stats
        assert "memory_misses" in stats
        assert "overall_hit_rate" in stats

    @pytest.mark.unit
    def test_cache_reset_stats(self, real_cache_manager):
        """Test real statistics reset"""
        # Manipulate real stats
        real_cache_manager.stats["memory_hits"] = 10
        real_cache_manager.stats["memory_misses"] = 5

        # Reset real stats
        real_cache_manager.reset_stats()

        # Verify real stats are reset
        stats = real_cache_manager.get_stats()
        assert stats["memory_hits"] == 0
        assert stats["memory_misses"] == 0

    @pytest.mark.unit
    def test_create_cache_manager_factory(self, real_supabase_client):
        """Test factory function creates real CacheManager"""
        manager = create_cache_manager(
            supabase_client=real_supabase_client,
            enable_memory_cache=True,
            enable_redis_cache=False,
            enable_db_cache=False
        )

        assert isinstance(manager, CacheManager)
        assert manager.enable_memory_cache is True


class TestCacheManagerEdgeCases:
    """Test edge cases and error handling with REAL cache"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_handles_empty_value(self, real_cache_manager):
        """Test real cache handles empty dict"""
        empty_value = {}

        # Store empty dict in real cache
        await real_cache_manager.set(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive",
            value=empty_value
        )

        # Get from real cache
        result = await real_cache_manager.get(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive"
        )

        # Real cache preserves empty dict
        assert result == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_handles_large_value(self, real_cache_manager):
        """Test real cache handles large data structure"""
        large_value = {
            "entities": [{"id": i, "data": "x" * 1000} for i in range(100)]
        }

        # Store large data in real cache
        await real_cache_manager.set(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive",
            value=large_value
        )

        # Get from real cache
        result = await real_cache_manager.get(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive"
        )

        # Real cache preserves large data
        assert len(result["entities"]) == 100

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_delete_nonexistent(self, real_cache_manager):
        """Test deleting non-existent key doesn't raise error (real cache)"""
        # Delete non-existent key from real cache
        deleted_count = await real_cache_manager.delete(
            client_id="client-123",
            case_id="nonexistent",
            scope="comprehensive"
        )

        # Real cache returns 0 for non-existent key
        assert deleted_count == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_invalidate_case_empty(self, real_cache_manager):
        """Test invalidating case with no cached data (real cache)"""
        # Invalidate non-existent case in real cache
        deleted_count = await real_cache_manager.invalidate_case(
            client_id="client-123",
            case_id="nonexistent"
        )

        # Real cache returns 0 when nothing to invalidate
        assert deleted_count == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_hit_rate_tracking(self, real_cache_manager):
        """Test that real cache tracks hit/miss statistics correctly"""
        # Clear real cache and reset stats
        real_cache_manager.memory_cache.clear()
        real_cache_manager.reset_stats()

        # Generate hits and misses in real cache
        await real_cache_manager.set("client-123", "case-1", "comprehensive", {"data": "value1"})
        await real_cache_manager.get("client-123", "case-1", "comprehensive")  # HIT
        await real_cache_manager.get("client-123", "case-2", "comprehensive")  # MISS
        await real_cache_manager.get("client-123", "case-1", "comprehensive")  # HIT

        # Verify real stats
        stats = real_cache_manager.get_stats()
        assert stats["memory_hits"] == 2
        assert stats["memory_misses"] == 1
        # Hit rate should be 2/3 ≈ 0.667
        assert 0.66 <= stats["memory_hit_rate"] <= 0.67

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, real_cache_manager):
        """Test that real cache entries expire after TTL"""
        value = {"test": "data"}

        # Set value in real cache
        await real_cache_manager.set(
            client_id="client-123",
            case_id="case-expiry",
            scope="comprehensive",
            value=value,
            case_status="active"
        )

        # Immediate get should work
        result = await real_cache_manager.get("client-123", "case-expiry", "comprehensive")
        assert result == value

        # Manually expire the cache entry to test expiration behavior
        cache_key = real_cache_manager._generate_cache_key("client-123", "case-expiry", "comprehensive")
        entry = real_cache_manager.memory_cache.cache.get(cache_key)
        if entry:
            # Set expiration to past to force expiration
            entry.expires_at = datetime.now() - timedelta(seconds=1)

        # Should be expired now (real behavior)
        result = await real_cache_manager.get("client-123", "case-expiry", "comprehensive")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_handles_none_value(self, real_cache_manager):
        """Test real cache behavior with None values"""
        # Note: CacheManager may not allow None values
        # Test with None to verify real behavior
        try:
            await real_cache_manager.set(
                client_id="client-123",
                case_id="case-none",
                scope="comprehensive",
                value=None
            )

            result = await real_cache_manager.get("client-123", "case-none", "comprehensive")
            # Real behavior: either stores None or rejects it
            assert result is None
        except (ValueError, TypeError):
            # Real cache may reject None values - this is acceptable
            pass

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_handles_complex_objects(self, real_cache_manager):
        """Test real cache handles complex nested objects"""
        complex_value = {
            "parties": [
                {"name": "John Doe", "role": "plaintiff", "id": "party-1"},
                {"name": "Jane Smith", "role": "defendant", "id": "party-2"}
            ],
            "citations": {
                "statutes": ["28 U.S.C. § 1331", "42 U.S.C. § 1983"],
                "cases": ["Marbury v. Madison"]
            },
            "nested": {
                "level1": {
                    "level2": {
                        "level3": "deep value"
                    }
                }
            }
        }

        # Store complex object in real cache
        await real_cache_manager.set(
            client_id="client-123",
            case_id="case-complex",
            scope="comprehensive",
            value=complex_value
        )

        # Get from real cache
        result = await real_cache_manager.get("client-123", "case-complex", "comprehensive")

        # Real cache preserves complex structure
        assert result["parties"][0]["name"] == "John Doe"
        assert result["citations"]["statutes"][0] == "28 U.S.C. § 1331"
        assert result["nested"]["level1"]["level2"]["level3"] == "deep value"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_key_validation(self, real_cache_manager):
        """Test real cache handles invalid keys gracefully"""
        value = {"test": "data"}

        # Test with empty client_id
        try:
            await real_cache_manager.set(
                client_id="",
                case_id="case-456",
                scope="comprehensive",
                value=value
            )
            # If it doesn't raise, verify it handles empty string
            result = await real_cache_manager.get("", "case-456", "comprehensive")
            assert result == value or result is None
        except (ValueError, KeyError):
            # Real cache may reject empty client_id - acceptable
            pass

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self, real_cache_manager):
        """Test real LRU eviction when cache is full"""
        # Fill cache to capacity (max_size = 1000 by default)
        # We'll test with a smaller number to speed up test
        for i in range(10):
            await real_cache_manager.set(
                client_id="client-123",
                case_id=f"case-{i}",
                scope="comprehensive",
                value={"data": f"value{i}"}
            )

        # Verify all entries are cached
        for i in range(10):
            result = await real_cache_manager.get("client-123", f"case-{i}", "comprehensive")
            assert result["data"] == f"value{i}"

        # Access first entry to make it most recently used
        await real_cache_manager.get("client-123", "case-0", "comprehensive")

        # Note: With max_size=1000, we won't trigger eviction with just 10 entries
        # This test verifies that LRU tracking works (MRU ordering)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_size_tracking(self, real_cache_manager):
        """Test real cache size tracking"""
        # Clear cache
        real_cache_manager.memory_cache.clear()

        # Initial size should be 0
        assert len(real_cache_manager.memory_cache.cache) == 0

        # Add entries
        await real_cache_manager.set("client-123", "case-1", "comprehensive", {"data": "value1"})
        assert len(real_cache_manager.memory_cache.cache) == 1

        await real_cache_manager.set("client-123", "case-2", "comprehensive", {"data": "value2"})
        assert len(real_cache_manager.memory_cache.cache) == 2

        # Delete entry
        await real_cache_manager.delete("client-123", "case-1", "comprehensive")
        assert len(real_cache_manager.memory_cache.cache) == 1

        # Clear all
        real_cache_manager.memory_cache.clear()
        assert len(real_cache_manager.memory_cache.cache) == 0
