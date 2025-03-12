from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2 import Environment
from jinja2.bccache import Bucket
from jinja2_async_environment.bccache import AsyncBytecodeCache


class TestAsyncBytecodeCache:
    def test_get_cache_key(self) -> None:
        cache = MagicMock(spec=AsyncBytecodeCache)
        cache.get_cache_key.side_effect = lambda name, filename: filename or name
        assert cache.get_cache_key("name", "filename") == "filename"
        assert cache.get_cache_key("name", None) == "name"

    def test_get_source_checksum(self) -> None:
        cache = MagicMock(spec=AsyncBytecodeCache)
        cache.get_source_checksum.side_effect = lambda source: str(hash(source))
        source = "template source"
        checksum = cache.get_source_checksum(source)
        assert isinstance(checksum, str)
        assert checksum == str(hash(source))
        different_source = "different template source"
        different_checksum = cache.get_source_checksum(different_source)
        assert checksum != different_checksum

    @pytest.mark.asyncio
    async def test_not_implemented_methods(self) -> None:
        cache = MagicMock(spec=AsyncBytecodeCache)
        bucket = MagicMock(spec=Bucket)
        environment = MagicMock(spec=Environment)
        cache.get_bucket_name.side_effect = NotImplementedError
        cache.load_bytecode = AsyncMock(side_effect=NotImplementedError)
        cache.dump_bytecode = AsyncMock(side_effect=NotImplementedError)
        cache.get_bucket = AsyncMock(side_effect=NotImplementedError)
        cache.set_bucket = AsyncMock(side_effect=NotImplementedError)
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
