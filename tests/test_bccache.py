from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jinja2 import Environment
from jinja2.bccache import Bucket
from redis.asyncio import Redis  # type: ignore
from jinja2_async_environment.bccache import AsyncBytecodeCache, AsyncRedisBytecodeCache


class TestAsyncBytecodeCache:
    """Tests for the AsyncBytecodeCache base class."""

    def test_get_cache_key(self) -> None:
        """Test get_cache_key method."""
        cache = AsyncBytecodeCache()

        # Test with filename
        assert cache.get_cache_key("name", "filename") == "filename"

        # Test without filename
        assert cache.get_cache_key("name", None) == "name"

    def test_get_source_checksum(self) -> None:
        """Test get_source_checksum method."""
        cache = AsyncBytecodeCache()
        source = "template source"

        # Ensure we get a string representation of hash
        checksum = cache.get_source_checksum(source)
        assert isinstance(checksum, str)
        assert checksum == str(hash(source))

        # Different source should produce different checksum
        different_source = "different template source"
        different_checksum = cache.get_source_checksum(different_source)
        assert checksum != different_checksum

    @pytest.mark.asyncio
    async def test_not_implemented_methods(self) -> None:
        """Test that abstract methods raise NotImplementedError."""
        cache = AsyncBytecodeCache()
        bucket = MagicMock(spec=Bucket)
        environment = MagicMock(spec=Environment)

        with pytest.raises(NotImplementedError):
            cache.get_bucket_name("key")

        with pytest.raises(NotImplementedError):
            await cache.load_bytecode(bucket)

        with pytest.raises(NotImplementedError):
            await cache.dump_bytecode(bucket)

        with pytest.raises(NotImplementedError):
            await cache.get_bucket(environment, "name", "filename", "source")

        with pytest.raises(NotImplementedError):
            await cache.set_bucket(bucket)


class TestAsyncRedisBytecodeCache:
    """Tests for the AsyncRedisBytecodeCache class."""

    @pytest.fixture
    def mock_redis(self) -> Redis:  # type: ignore
        """Create a mock Redis client."""
        redis_mock = AsyncMock(spec=Redis)
        return redis_mock

    @pytest.fixture
    def cache(self, mock_redis: Redis) -> AsyncRedisBytecodeCache:  # type: ignore
        """Create a Redis bytecode cache with mock Redis client."""
        return AsyncRedisBytecodeCache(prefix="test_prefix", client=mock_redis)

    @pytest.fixture
    def bucket(self) -> MagicMock:
        """Create a mock Bucket."""
        mock_bucket = MagicMock(spec=Bucket)
        mock_bucket.key = "test_key"
        mock_bucket.bytecode_to_string.return_value = b"bytecode"
        mock_bucket.bytecode_from_string.return_value = "decoded_bytecode"
        return mock_bucket

    def test_init(self, mock_redis: Redis) -> None:  # type: ignore
        """Test initialization of AsyncRedisBytecodeCache."""
        # Test with prefix and client
        cache = AsyncRedisBytecodeCache(prefix="test_prefix", client=mock_redis)
        assert cache.prefix == "test_prefix"
        assert cache.client is mock_redis
        assert isinstance(cache.configs, MappingProxyType)

        # Test with configs
        with patch("jinja2_async_environment.bccache.Redis") as mock_redis_class:
            # Create a mock Redis instance for the Redis constructor to return
            mock_redis_instance = AsyncMock(spec=Redis)
            mock_redis_class.return_value = mock_redis_instance

            # Use type: ignore for configs which would cause type error otherwise
            configs = {"host": "localhost", "port": 6379}
            cache = AsyncRedisBytecodeCache(prefix="test_prefix", **configs)  # type: ignore

            mock_redis_class.assert_called_once_with(**configs)
            assert cache.prefix == "test_prefix"
            assert isinstance(cache.configs, MappingProxyType)

    def test_get_bucket_name(self, cache: AsyncRedisBytecodeCache) -> None:
        """Test get_bucket_name method."""
        # Test with prefix
        assert cache.get_bucket_name("key") == "test_prefix:key"

        # Test without prefix
        cache.prefix = None
        assert cache.get_bucket_name("key") == "key"

    @pytest.mark.asyncio
    async def test_load_bytecode_with_code(
        self, cache: AsyncRedisBytecodeCache, bucket: MagicMock
    ) -> None:
        """Test load_bytecode method when code is found."""
        # Type annotations for get method are problematic, so we use type: ignore
        cache.client.get = AsyncMock(return_value=b"bytecode")  # type: ignore
        result = await cache.load_bytecode(bucket)

        # Use getattr to avoid linter errors with assert_called_once_with
        get_method = getattr(cache.client, "get")
        assert get_method.called
        assert get_method.call_args[0][0] == "test_prefix:test_key"

        assert bucket.bytecode_from_string.called
        assert bucket.bytecode_from_string.call_args[0][0] == b"bytecode"
        assert result == "decoded_bytecode"

    @pytest.mark.asyncio
    async def test_load_bytecode_without_code(
        self, cache: AsyncRedisBytecodeCache, bucket: MagicMock
    ) -> None:
        """Test load_bytecode method when no code is found."""
        # Type annotations for get method are problematic, so we use type: ignore
        cache.client.get = AsyncMock(return_value=None)  # type: ignore
        result = await cache.load_bytecode(bucket)

        # Use getattr to avoid linter errors with assert_called_once_with
        get_method = getattr(cache.client, "get")
        assert get_method.called
        assert get_method.call_args[0][0] == "test_prefix:test_key"

        assert not bucket.bytecode_from_string.called
        assert result is None

    @pytest.mark.asyncio
    async def test_dump_bytecode(
        self, cache: AsyncRedisBytecodeCache, bucket: MagicMock
    ) -> None:
        """Test dump_bytecode method."""
        # Type annotations for set method are problematic, so we use type: ignore
        cache.client.set = AsyncMock()  # type: ignore
        await cache.dump_bytecode(bucket)

        assert bucket.bytecode_to_string.called

        # Use getattr to avoid linter errors with assert_called_once_with
        set_method = getattr(cache.client, "set")
        assert set_method.called
        assert set_method.call_args[0][0] == "test_prefix:test_key"
        assert set_method.call_args[0][1] == b"bytecode"

    @pytest.mark.asyncio
    async def test_get_bucket(self, cache: AsyncRedisBytecodeCache) -> None:
        """Test get_bucket method."""
        environment = MagicMock(spec=Environment)

        # Mock relevant methods
        cache.get_cache_key = MagicMock(return_value="cache_key")
        cache.get_source_checksum = MagicMock(return_value="checksum")
        cache.load_bytecode = AsyncMock()

        # Create patch for Bucket
        with patch("jinja2_async_environment.bccache.Bucket") as mock_bucket_class:
            mock_bucket = MagicMock()
            mock_bucket_class.return_value = mock_bucket

            result = await cache.get_bucket(environment, "name", "filename", "source")

            # Verify interactions
            assert cache.get_cache_key.called
            assert cache.get_cache_key.call_args[0] == ("name", "filename")

            assert cache.get_source_checksum.called
            assert cache.get_source_checksum.call_args[0][0] == "source"

            assert mock_bucket_class.called
            assert mock_bucket_class.call_args[0] == (
                environment,
                "cache_key",
                "checksum",
            )

            assert cache.load_bytecode.called
            assert cache.load_bytecode.call_args[0][0] is mock_bucket

            assert result is mock_bucket

    @pytest.mark.asyncio
    async def test_set_bucket(
        self, cache: AsyncRedisBytecodeCache, bucket: MagicMock
    ) -> None:
        """Test set_bucket method."""
        cache.dump_bytecode = AsyncMock()

        await cache.set_bucket(bucket)

        assert cache.dump_bytecode.called
        assert cache.dump_bytecode.call_args[0][0] is bucket
