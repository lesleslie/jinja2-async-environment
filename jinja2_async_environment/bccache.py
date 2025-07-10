import typing as t
from types import MappingProxyType

from jinja2 import Environment
from jinja2.bccache import Bucket, BytecodeCache
from redis.asyncio import Redis, RedisCluster  # type: ignore


class AsyncBytecodeCache(BytecodeCache):
    def load_bytecode(self, bucket: Bucket) -> None:
        raise NotImplementedError(
            "AsyncBytecodeCache.load_bytecode must be implemented."
        )

    def dump_bytecode(self, bucket: Bucket) -> None:
        raise NotImplementedError(
            "AsyncBytecodeCache.dump_bytecode must be implemented."
        )

    def clear(self) -> None:
        raise NotImplementedError("AsyncBytecodeCache.clear must be implemented.")

    def get_cache_key(
        self, name: str, filename: str | None = None, env: Environment | None = None
    ) -> str:
        return f"{name}:{filename or name}"

    def get_source_checksum(self, source: str) -> str:
        import hashlib

        return hashlib.md5(source.encode(), usedforsecurity=False).hexdigest()

    async def get_bucket_async(
        self, environment: Environment, name: str, filename: str | None, source: str
    ) -> Bucket:
        key = self.get_cache_key(name, filename, environment)
        checksum = self.get_source_checksum(source)
        bucket = Bucket(environment, key, checksum)
        self.load_bytecode(bucket)
        return bucket

    async def set_bucket_async(self, bucket: Bucket) -> None:
        self.dump_bytecode(bucket)


class AsyncRedisBytecodeCache(AsyncBytecodeCache):
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

    def get_cache_key(
        self, name: str, filename: str | None = None, env: Environment | None = None
    ) -> str:
        return filename or name

    def get_source_checksum(self, source: str) -> str:
        return str(hash(source))

    def get_bucket_name(self, key: str) -> str:
        return f"{self.prefix}:{key}" if self.prefix else key

    async def load_bytecode(self, bucket: Bucket) -> bytes | None:  # type: ignore[override]
        code = await self.client.get(self.get_bucket_name(bucket.key))  # type: ignore
        if code:
            code_bytes = code.encode("utf-8") if isinstance(code, str) else code
            bucket.bytecode_from_string(code_bytes)
            return code_bytes
        return None

    async def dump_bytecode(self, bucket: Bucket) -> None:  # type: ignore[override]
        await self.client.set(  # type: ignore
            self.get_bucket_name(bucket.key), bucket.bytecode_to_string()
        )

    async def get_bucket(  # type: ignore[override]
        self, environment: Environment, name: str, filename: str | None, source: str
    ) -> Bucket:
        key = self.get_cache_key(name, filename or name)
        checksum = self.get_source_checksum(source)
        bucket = Bucket(environment, key, checksum)
        await self.load_bytecode(bucket)
        return bucket

    async def set_bucket(self, bucket: Bucket) -> None:  # type: ignore[override]
        await self.dump_bytecode(bucket)

    async def get_bucket_async(
        self, environment: Environment, name: str, filename: str | None, source: str
    ) -> Bucket:
        return await self.get_bucket(environment, name, filename, source)

    async def set_bucket_async(self, bucket: Bucket) -> None:
        return await self.set_bucket(bucket)
