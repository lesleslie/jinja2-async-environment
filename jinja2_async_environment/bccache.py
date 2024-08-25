import typing as t

from jinja2 import BytecodeCache
from jinja2.bccache import Bucket
from redis.asyncio import Redis, RedisCluster
from .environment import AsyncEnvironment


class AsyncRedisBytecodeCache(BytecodeCache):  # type: ignore
    def __init__(
        self,
        prefix: t.Optional[str] = None,
        client: t.Optional[Redis | RedisCluster] = None,
        **configs: t.Any,
    ) -> None:
        super().__init__(**configs)
        self.prefix = prefix
        self.client = client
        if not client:
            self.client = Redis(**configs)

    def get_bucket_name(self, key: str) -> str:
        return ":".join([self.prefix, key]) if self.prefix else key

    async def load_bytecode(self, bucket: Bucket) -> t.Any:  # type: ignore
        code = await self.client.get(self.get_bucket_name(bucket.key))
        if code:
            return bucket.bytecode_from_string(code)

    async def dump_bytecode(self, bucket: Bucket) -> None:  # type: ignore
        await self.client.set(
            self.get_bucket_name(bucket.key), bucket.bytecode_to_string()
        )

    async def get_bucket(  # type: ignore
        self,
        environment: "AsyncEnvironment",
        name: str,
        path: str,
        source: str,
    ) -> Bucket:
        key = self.get_cache_key(name, path)
        checksum = self.get_source_checksum(source)
        bucket = Bucket(environment, key, checksum)
        await self.load_bytecode(bucket)
        return bucket

    async def set_bucket(self, bucket: Bucket) -> None:  # type: ignore
        await self.dump_bytecode(bucket)
