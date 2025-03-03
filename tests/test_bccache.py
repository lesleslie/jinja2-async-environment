import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import Redis
from jinja2_async_environment.bccache import AsyncRedisBytecodeCache
from jinja2_async_environment.environment import AsyncEnvironment


@pytest.mark.asyncio
async def test_async_redis_bytecode_cache_init() -> None:
    """Test the initialization of AsyncRedisBytecodeCache."""
    client = AsyncMock(spec=Redis)
    cache = AsyncRedisBytecodeCache(prefix="test_prefix", client=client)
    assert cache.prefix == "test_prefix"
    assert cache.client == client


@pytest.mark.asyncio
async def test_async_redis_bytecode_cache_get_bucket_name() -> None:
    """Test the get_bucket_name method."""
    client = AsyncMock(spec=Redis)
    cache = AsyncRedisBytecodeCache(prefix="test_prefix", client=client)
    assert cache.get_bucket_name("my_key") == "test_prefix:my_key"

    cache_no_prefix = AsyncRedisBytecodeCache(client=client)
    assert cache_no_prefix.get_bucket_name("my_key") == "my_key"


@pytest.mark.asyncio
async def test_async_redis_bytecode_cache_load_bytecode() -> None:
    """Test the load_bytecode method."""
    client = AsyncMock(spec=Redis)
    cache = AsyncRedisBytecodeCache(prefix="test_prefix", client=client)
    bucket = MagicMock()
    bucket.key = "my_key"
    bucket.bytecode_from_string.return_value = "bytecode"
    client.get.return_value = asyncio.Future()
    client.get.return_value.set_result(b"bytecode_string")

    result = await cache.load_bytecode(bucket)
    assert result == "bytecode"
    client.get.assert_awaited_once_with("test_prefix:my_key")
    bucket.bytecode_from_string.assert_called_once_with(b"bytecode_string")

    client.get.return_value = asyncio.Future()
    client.get.return_value.set_result(None)
    result = await cache.load_bytecode(bucket)
    assert result is None


@pytest.mark.asyncio
async def test_async_redis_bytecode_cache_dump_bytecode() -> None:
    """Test the dump_bytecode method."""
    client = AsyncMock(spec=Redis)
    cache = AsyncRedisBytecodeCache(prefix="test_prefix", client=client)
    bucket = MagicMock()
    bucket.key = "my_key"
    bucket.bytecode_to_string.return_value = b"bytecode_string"

    await cache.dump_bytecode(bucket)
    client.set.assert_awaited_once_with("test_prefix:my_key", b"bytecode_string")


@pytest.mark.asyncio
async def test_async_redis_bytecode_cache_get_bucket() -> None:
    """Test the get_bucket method."""
    client = AsyncMock(spec=Redis)
    cache = AsyncRedisBytecodeCache(prefix="test_prefix", client=client)
    env = AsyncMock(spec=AsyncEnvironment)
    name = "template_name"
    path = "template_path"
    source = "template_source"
    client.get.return_value = asyncio.Future()
    client.get.return_value.set_result(b"bytecode_string")
    bucket = MagicMock()
    bucket.bytecode_from_string.return_value = "bytecode"
    with patch(
        "jinja2_async_environment.bccache.Bucket", return_value=bucket
    ) as MockBucket:
        result = await cache.get_bucket(env, name, path, source)
        assert result == bucket
        bucket.bytecode_from_string.assert_called_once_with(b"bytecode_string")


@pytest.mark.asyncio
async def test_async_redis_bytecode_cache_set_bucket() -> None:
    """Test the set_bucket method."""
    client = AsyncMock(spec=Redis)
    cache = AsyncRedisBytecodeCache(prefix="test_prefix", client=client)
    bucket = MagicMock()
    bucket.key = "my_key"
    bucket.bytecode_to_string.return_value = b"bytecode_string"
    await cache.set_bucket(bucket)
    client.set.assert_awaited_once_with("test_prefix:my_key", b"bytecode_string")
