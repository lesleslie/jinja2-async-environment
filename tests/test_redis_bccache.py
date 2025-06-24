from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jinja2 import Environment
from jinja2.bccache import Bucket
from jinja2_async_environment.bccache import AsyncRedisBytecodeCache


class TestAsyncRedisBytecodeCache:
    @pytest.fixture
    def mock_redis_client(self) -> AsyncMock:
        client = AsyncMock()
        client.get = AsyncMock()
        client.set = AsyncMock()
        return client

    @pytest.fixture
    def cache(self, mock_redis_client: MagicMock) -> AsyncRedisBytecodeCache:
        return AsyncRedisBytecodeCache(prefix="test_prefix", client=mock_redis_client)

    @pytest.fixture
    def environment(self) -> Environment:
        return Environment(autoescape=True)

    @pytest.fixture
    def bucket(self, environment: Environment) -> Bucket:
        bucket = Bucket(environment, "test_key", "test_checksum")
        bucket.code = compile("x = 1", "<string>", "exec")
        return bucket

    def test_init_with_client(self, mock_redis_client: MagicMock) -> None:
        cache = AsyncRedisBytecodeCache(prefix="test:", client=mock_redis_client)
        assert cache.prefix == "test:"
        assert cache.client is mock_redis_client
        assert not cache.configs

    def test_init_with_configs(self) -> None:
        with patch("jinja2_async_environment.bccache.Redis") as mock_redis:
            cache = AsyncRedisBytecodeCache(
                prefix="test:", host="localhost", port=6379, db=0
            )
            assert cache.prefix == "test:"
            assert mock_redis.called
            assert cache.configs["host"] == "localhost"
            assert cache.configs["port"] == 6379
            assert cache.configs["db"] == 0

    def test_get_cache_key(self, cache: AsyncRedisBytecodeCache) -> None:
        assert cache.get_cache_key("name", "filename") == "filename"
        assert cache.get_cache_key("name") == "name"

    def test_get_source_checksum(self, cache: AsyncRedisBytecodeCache) -> None:
        source = "template source"
        checksum = cache.get_source_checksum(source)
        assert isinstance(checksum, str)
        assert checksum == str(hash(source))

        different_source = "different template source"
        different_checksum = cache.get_source_checksum(different_source)
        assert checksum != different_checksum

    def test_get_bucket_name(self, cache: AsyncRedisBytecodeCache) -> None:
        assert cache.get_bucket_name("key") == "test_prefix:key"

        cache_no_prefix = AsyncRedisBytecodeCache(client=MagicMock())
        assert cache_no_prefix.get_bucket_name("key") == "key"

    @pytest.mark.asyncio
    async def test_load_bytecode_hit(
        self,
        cache: AsyncRedisBytecodeCache,
        bucket: Bucket,
        mock_redis_client: MagicMock,
    ) -> None:
        mock_redis_client.get.return_value = b"bytecode_data"
        with patch.object(bucket, "bytecode_from_string") as mock_from_string:
            result = await cache.load_bytecode(bucket)
            mock_redis_client.get.assert_awaited_once_with("test_prefix:test_key")
            mock_from_string.assert_called_once_with(b"bytecode_data")
            assert result == b"bytecode_data"

    @pytest.mark.asyncio
    async def test_load_bytecode_miss(
        self,
        cache: AsyncRedisBytecodeCache,
        bucket: Bucket,
        mock_redis_client: MagicMock,
    ) -> None:
        mock_redis_client.get.return_value = None
        with patch.object(bucket, "bytecode_from_string") as mock_from_string:
            result = await cache.load_bytecode(bucket)
            mock_redis_client.get.assert_awaited_once_with("test_prefix:test_key")
            mock_from_string.assert_not_called()
            assert result is None

    @pytest.mark.asyncio
    async def test_dump_bytecode(
        self,
        cache: AsyncRedisBytecodeCache,
        bucket: Bucket,
        mock_redis_client: MagicMock,
    ) -> None:
        bucket.bytecode_to_string = MagicMock(return_value=b"serialized_bytecode")
        await cache.dump_bytecode(bucket)
        mock_redis_client.set.assert_awaited_once_with(
            "test_prefix:test_key", b"serialized_bytecode"
        )

    @pytest.mark.asyncio
    async def test_get_bucket(
        self,
        cache: AsyncRedisBytecodeCache,
        environment: Environment,
        mock_redis_client: MagicMock,
    ) -> None:
        mock_redis_client.get.return_value = b"bytecode_data"

        with patch("jinja2_async_environment.bccache.Bucket") as mock_bucket_class:
            mock_bucket = MagicMock()
            mock_bucket_class.return_value = mock_bucket

            result = await cache.get_bucket(
                environment, "template_name", "filename", "source"
            )

            mock_bucket_class.assert_called_once_with(
                environment, "filename", str(hash("source"))
            )
            mock_redis_client.get.assert_awaited_once()
            assert result is mock_bucket

    @pytest.mark.asyncio
    async def test_set_bucket(
        self, cache: AsyncRedisBytecodeCache, bucket: Bucket
    ) -> None:
        with patch.object(cache, "dump_bytecode") as mock_dump:
            await cache.set_bucket(bucket)
            mock_dump.assert_awaited_once_with(bucket)

    @pytest.mark.asyncio
    async def test_get_bucket_async(
        self, cache: AsyncRedisBytecodeCache, environment: Environment
    ) -> None:
        with patch.object(cache, "get_bucket") as mock_get_bucket:
            mock_get_bucket.return_value = "bucket_result"
            result = await cache.get_bucket_async(
                environment, "name", "filename", "source"
            )
            mock_get_bucket.assert_awaited_once_with(
                environment, "name", "filename", "source"
            )
            assert result == "bucket_result"

    @pytest.mark.asyncio
    async def test_set_bucket_async(
        self, cache: AsyncRedisBytecodeCache, bucket: Bucket
    ) -> None:
        with patch.object(cache, "set_bucket") as mock_set_bucket:
            await cache.set_bucket_async(bucket)
            mock_set_bucket.assert_awaited_once_with(bucket)
