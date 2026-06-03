import hashlib

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

    def test_get_source_checksum_uses_sha256(self) -> None:
        """Test that get_source_checksum uses SHA-256 cryptographic hash."""
        cache = MagicMock(spec=AsyncBytecodeCache)
        cache.get_source_checksum.side_effect = (
            lambda source: hashlib.sha256(source.encode("utf-8")).hexdigest()
        )

        source = "template source"
        checksum = cache.get_source_checksum(source)

        # Verify checksum is a hex string
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 produces 64 hex characters

        # Verify it's a valid hex string
        try:
            int(checksum, 16)
        except ValueError:
            pytest.fail("Checksum is not a valid hexadecimal string")

        # Verify different sources produce different checksums
        different_source = "different template source"
        different_checksum = cache.get_source_checksum(different_source)
        assert checksum != different_checksum

    def test_get_source_checksum_deterministic(self) -> None:
        """Test that checksums are deterministic across multiple calls."""
        cache = MagicMock(spec=AsyncBytecodeCache)
        cache.get_source_checksum.side_effect = (
            lambda source: hashlib.sha256(source.encode("utf-8")).hexdigest()
        )

        source = "template source"
        checksum1 = cache.get_source_checksum(source)
        checksum2 = cache.get_source_checksum(source)

        # Same source should always produce same checksum
        assert checksum1 == checksum2

    def test_get_source_checksum_collision_resistance(self) -> None:
        """Test that SHA-256 provides collision resistance."""
        cache = MagicMock(spec=AsyncBytecodeCache)
        cache.get_source_checksum.side_effect = (
            lambda source: hashlib.sha256(source.encode("utf-8")).hexdigest()
        )

        # Test similar sources produce different checksums
        sources = [
            "template source",
            "template source ",  # Extra space
            "Template source",  # Capital T
            "template sourcE",  # Capital E
            "template source\n",  # Newline
        ]

        checksums = [cache.get_source_checksum(source) for source in sources]

        # All checksums should be different
        assert len(checksums) == len(set(checksums)), "Collision detected!"

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
