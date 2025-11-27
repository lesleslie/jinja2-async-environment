"""Tests for the CompilationCache class to improve test coverage."""

from jinja2_async_environment.compiler_modules.cache import CompilationCache


class TestCompilationCache:
    """Test the CompilationCache class."""

    def test_initialization(self):
        """Test initialization with custom max_size."""
        cache = CompilationCache(max_size=50)
        assert cache.max_size == 50
        assert cache._cache == {}

    def test_get_cache_key(self):
        """Test cache key generation."""
        cache = CompilationCache()

        key1 = cache.get_cache_key("source1", "env1")
        key2 = cache.get_cache_key("source1", "env1")  # Should be same
        key3 = cache.get_cache_key("source2", "env1")  # Should be different
        key4 = cache.get_cache_key("source1", "env2")  # Should be different

        assert isinstance(key1, str)
        assert len(key1) == 16  # First 16 chars of SHA256
        assert key1 == key2  # Same inputs produce same key
        assert key1 != key3  # Different source produces different key
        assert key1 != key4  # Different env produces different key

    def test_set_and_get(self):
        """Test setting and getting values."""
        cache = CompilationCache()

        key = cache.get_cache_key("test_source", "test_env")
        cache.set(key, "compiled_code")

        result = cache.get(key)
        assert result == "compiled_code"

        # Test getting non-existent key
        non_existent = cache.get("non_existent_key")
        assert non_existent is None

    def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
        cache = CompilationCache(max_size=4)

        # Add 5 items to a cache with max size 4
        # When max_size is 4, max_size // 4 = 1, so 1 key will be removed when limit is exceeded
        for i in range(5):
            key = f"key{i}"
            cache.set(key, f"value{i}")

        # After adding 5 items, 1 will be removed (1/4 of 4 = 1), leaving 4 items
        assert len(cache._cache) == 4

        # The first key (key0) should be removed
        assert cache.get("key0") is None
        # Other keys should still be present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_size_limit_large_removal(self):
        """Test cache size limit with larger removal to ensure it works correctly."""
        cache = CompilationCache(max_size=12)

        # Add 13 items to a cache with max size 12
        # When max_size is 12, max_size // 4 = 3
        # So when we exceed max_size (after adding 13th item), 3 oldest keys will be removed
        for i in range(13):
            key = f"key{i}"
            cache.set(key, f"value{i}")

        # After adding 13 items and removing 3, we have 10 items (13 - 3 = 10)
        assert len(cache._cache) == 10

        # The first 3 keys (key0, key1, key2) should be removed
        for i in range(3):
            assert cache.get(f"key{i}") is None
        # The next 10 keys (key3 through key12) should be present
        for i in range(3, 13):
            assert cache.get(f"key{i}") == f"value{i}"

    def test_clear(self):
        """Test clearing the cache."""
        cache = CompilationCache()

        cache.set("test_key", "test_value")
        assert len(cache._cache) == 1

        cache.clear()
        assert len(cache._cache) == 0
        assert cache.get("test_key") is None
