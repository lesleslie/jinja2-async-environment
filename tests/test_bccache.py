from unittest.mock import MagicMock

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
        cache = AsyncBytecodeCache()
        bucket = MagicMock(spec=Bucket)
        MagicMock(spec=Environment)

        # Test methods that should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            cache.load_bytecode(bucket)
        with pytest.raises(NotImplementedError):
            cache.dump_bytecode(bucket)
        with pytest.raises(NotImplementedError):
            cache.clear()
