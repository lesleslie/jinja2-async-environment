from unittest.mock import MagicMock

import pytest
from jinja2.bccache import Bucket
from jinja2_async_environment.bccache import AsyncBytecodeCache
from jinja2_async_environment.environment import AsyncEnvironment


class TestAsyncBytecodeCache:
    @pytest.fixture
    def async_bccache(self) -> AsyncBytecodeCache:
        """Create an AsyncBytecodeCache instance for testing."""
        return AsyncBytecodeCache()

    @pytest.fixture
    def async_env(self) -> AsyncEnvironment:
        """Create an AsyncEnvironment instance for testing."""
        return AsyncEnvironment()

    def test_init(self, async_bccache: AsyncBytecodeCache) -> None:
        """Test initialization of AsyncBytecodeCache."""
        assert isinstance(async_bccache, AsyncBytecodeCache)

    def test_get_cache_key(self, async_bccache: AsyncBytecodeCache) -> None:
        """Test the get_cache_key method."""
        # Create a mock environment
        env = MagicMock()
        env.loader = MagicMock()

        # Call get_cache_key
        key = async_bccache.get_cache_key("template.html", "filename.py", env)

        # Verify the key is a string
        assert isinstance(key, str)
        assert "template.html" in key
        assert "filename.py" in key

    def test_get_source_checksum(self, async_bccache: AsyncBytecodeCache) -> None:
        """Test the get_source_checksum method."""
        # Call get_source_checksum
        checksum = async_bccache.get_source_checksum("template source")

        # Verify the checksum is a string
        assert isinstance(checksum, str)
        assert checksum

    @pytest.mark.asyncio
    async def test_get_bucket_async(
        self, async_bccache: AsyncBytecodeCache, async_env: AsyncEnvironment
    ) -> None:
        """Test the get_bucket_async method."""
        # Mock the get_cache_key and get_source_checksum methods
        async_bccache.get_cache_key = MagicMock(return_value="cache_key")
        async_bccache.get_source_checksum = MagicMock(return_value="checksum")

        # Mock the load_bytecode method
        async_bccache.load_bytecode = MagicMock()

        # Call get_bucket_async
        bucket = await async_bccache.get_bucket_async(
            async_env, "template.html", "filename.py", "source"
        )

        # Verify the bucket
        assert isinstance(bucket, Bucket)
        assert bucket.key == "cache_key"
        assert bucket.checksum == "checksum"
        async_bccache.load_bytecode.assert_called_once_with(bucket)

    @pytest.mark.asyncio
    async def test_set_bucket_async(self, async_bccache: AsyncBytecodeCache) -> None:
        """Test the set_bucket_async method."""
        # Create a mock bucket
        bucket = MagicMock(spec=Bucket)
        bucket.code = "compiled_code"

        # Mock the dump_bytecode method
        async_bccache.dump_bytecode = MagicMock()

        # Call set_bucket_async
        await async_bccache.set_bucket_async(bucket)

        # Verify dump_bytecode was called
        async_bccache.dump_bytecode.assert_called_once_with(bucket)

    def test_load_bytecode_not_implemented(
        self, async_bccache: AsyncBytecodeCache
    ) -> None:
        """Test that load_bytecode raises NotImplementedError."""
        # Create a mock bucket
        bucket = MagicMock(spec=Bucket)

        # Call load_bytecode and verify it raises NotImplementedError
        with pytest.raises(NotImplementedError):
            async_bccache.load_bytecode(bucket)

    def test_dump_bytecode_not_implemented(
        self, async_bccache: AsyncBytecodeCache
    ) -> None:
        """Test that dump_bytecode raises NotImplementedError."""
        # Create a mock bucket
        bucket = MagicMock(spec=Bucket)

        # Call dump_bytecode and verify it raises NotImplementedError
        with pytest.raises(NotImplementedError):
            async_bccache.dump_bytecode(bucket)

    def test_clear_not_implemented(self, async_bccache: AsyncBytecodeCache) -> None:
        """Test that clear raises NotImplementedError."""
        # Call clear and verify it raises NotImplementedError
        with pytest.raises(NotImplementedError):
            async_bccache.clear()


class TestAsyncBytecodeCache_Subclass:
    class CustomAsyncBytecodeCache(AsyncBytecodeCache):
        """A custom subclass of AsyncBytecodeCache for testing."""

        def __init__(self) -> None:
            super().__init__()
            self.cache: dict[str, bytes] = {}

        def load_bytecode(self, bucket: Bucket) -> None:
            """Load bytecode from the cache."""
            if bucket.key in self.cache:
                from io import BytesIO

                stream = BytesIO(self.cache[bucket.key])
                bucket.load_bytecode(stream)

        def dump_bytecode(self, bucket: Bucket) -> None:
            """Dump bytecode to the cache."""
            from io import BytesIO

            stream = BytesIO()
            bucket.write_bytecode(stream)
            self.cache[bucket.key] = stream.getvalue()

        def clear(self) -> None:
            """Clear the cache."""
            self.cache.clear()

    @pytest.fixture
    def custom_bccache(self) -> CustomAsyncBytecodeCache:
        """Create a CustomAsyncBytecodeCache instance for testing."""
        return TestAsyncBytecodeCache_Subclass.CustomAsyncBytecodeCache()

    @pytest.fixture
    def async_env(self) -> AsyncEnvironment:
        """Create an AsyncEnvironment instance for testing."""
        return AsyncEnvironment()

    @pytest.mark.asyncio
    async def test_get_bucket_async_with_custom_cache(
        self, custom_bccache: CustomAsyncBytecodeCache, async_env: AsyncEnvironment
    ) -> None:
        """Test the get_bucket_async method with a custom cache implementation."""
        # Call get_bucket_async
        bucket = await custom_bccache.get_bucket_async(
            async_env, "template.html", "filename.py", "source"
        )

        # Verify the bucket
        assert isinstance(bucket, Bucket)
        assert bucket.key is not None
        assert bucket.checksum is not None

    @pytest.mark.asyncio
    async def test_set_bucket_async_with_custom_cache(
        self, custom_bccache: CustomAsyncBytecodeCache, async_env: AsyncEnvironment
    ) -> None:
        """Test the set_bucket_async method with a custom cache implementation."""
        # Get a bucket
        bucket = await custom_bccache.get_bucket_async(
            async_env, "template.html", "filename.py", "source"
        )

        # Compile some code
        bucket.code = compile("a = 1", "filename.py", "exec")

        # Set the bucket
        await custom_bccache.set_bucket_async(bucket)

        # Verify the bucket was stored in the cache
        assert bucket.key in custom_bccache.cache
        assert custom_bccache.cache[bucket.key] is not None

    @pytest.mark.asyncio
    async def test_get_bucket_async_with_existing_bucket(
        self, custom_bccache: CustomAsyncBytecodeCache, async_env: AsyncEnvironment
    ) -> None:
        """Test the get_bucket_async method with an existing bucket in the cache."""
        # Get a bucket and set it with some code
        bucket1 = await custom_bccache.get_bucket_async(
            async_env, "template.html", "filename.py", "source"
        )
        bucket1.code = compile("a = 1", "filename.py", "exec")
        await custom_bccache.set_bucket_async(bucket1)

        # Get the bucket again
        bucket2 = await custom_bccache.get_bucket_async(
            async_env, "template.html", "filename.py", "source"
        )

        # Verify the bucket has the code
        assert bucket2.code is not None

    def test_clear_with_custom_cache(
        self, custom_bccache: CustomAsyncBytecodeCache
    ) -> None:
        """Test the clear method with a custom cache implementation."""
        # Add some items to the cache
        custom_bccache.cache["key1"] = b"value1"
        custom_bccache.cache["key2"] = b"value2"

        # Clear the cache
        custom_bccache.clear()

        # Verify the cache is empty
        assert not custom_bccache.cache
