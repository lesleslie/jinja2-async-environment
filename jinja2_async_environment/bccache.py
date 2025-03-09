import typing as t
from types import MappingProxyType

from jinja2 import Environment
from jinja2.bccache import Bucket
from redis.asyncio import Redis, RedisCluster


class AsyncBytecodeCache:
    """Base class for async bytecode caches."""

    def get_bucket_name(self, key: str) -> str:
        """Return a unique bucket name for this cache."""
        raise NotImplementedError()

    def get_cache_key(self, name: str, filename: str | None) -> str:
        """Return the cache key for the bucket."""
        return filename or name

    def get_source_checksum(self, source: str) -> str:
        """Return a checksum for the source."""
        return str(hash(source))

    async def load_bytecode(self, bucket: Bucket) -> t.Any:
        """Load bytecode from the cache."""
        raise NotImplementedError()

    async def dump_bytecode(self, bucket: Bucket) -> None:
        """Dump bytecode to the cache."""
        raise NotImplementedError()

    async def get_bucket(
        self,
        environment: Environment,
        name: str,
        filename: str | None,
        source: str,
    ) -> Bucket:
        """Return a cache bucket for the given template."""
        raise NotImplementedError()

    async def set_bucket(self, bucket: Bucket) -> None:
        """Set a cache bucket for the given template."""
        raise NotImplementedError()


class AsyncRedisBytecodeCache(AsyncBytecodeCache):
    """A bytecode cache that stores bytecode in Redis."""

    prefix: str | None
    client: Redis | RedisCluster  # type: ignore
    configs: MappingProxyType[str, t.Any]

    def __init__(
        self,
        prefix: str | None = None,
        client: Redis | RedisCluster | None = None,  # type: ignore
        **configs: t.Any,
    ) -> None:
        self.prefix = prefix
        self.client = client or Redis(**configs)
        self.configs = MappingProxyType(configs)

    def get_bucket_name(self, key: str) -> str:
        return ":".join([self.prefix, key]) if self.prefix else key

    async def load_bytecode(self, bucket: Bucket) -> t.Any:
        code = await self.client.get(self.get_bucket_name(bucket.key))  # type: ignore
        if code:
            return bucket.bytecode_from_string(code)
        return None

    async def dump_bytecode(self, bucket: Bucket) -> None:
        await self.client.set(  # type: ignore
            self.get_bucket_name(bucket.key), bucket.bytecode_to_string()
        )

    async def get_bucket(
        self,
        environment: Environment,
        name: str,
        filename: str | None,
        source: str,
    ) -> Bucket:
        key = self.get_cache_key(name, filename or name)
        checksum = self.get_source_checksum(source)
        bucket = Bucket(environment, key, checksum)
        await self.load_bytecode(bucket)
        return bucket

    async def set_bucket(self, bucket: Bucket) -> None:
        await self.dump_bytecode(bucket)
