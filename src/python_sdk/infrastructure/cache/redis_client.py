import asyncio
import logging
from threading import Lock
from typing import Any, Optional

from py_cachify import init_cachify
from redis import Connection as SyncConnection
from redis import ConnectionPool as SyncConnectionPool
from redis import Redis
from redis.asyncio import (
    Connection as AsyncConnection,
)
from redis.asyncio import (
    ConnectionPool as AsyncConnectionPool,
)
from redis.asyncio import (
    Redis as AsyncRedis,
)

from ...conf import settings
from ...conf.logger import get_logger
from ...utils.decorators import singleton

logger = get_logger("RedisClient", level=logging.DEBUG)

params: dict[str, Any] = {
    "url": settings.redis.url,
    "decode_responses": True,
    "socket_keepalive": True,
    "health_check_interval": 30,
    "retry_on_timeout": True,
    "max_connections": 10,
}


@singleton
class RedisPools(object):
    __slots__ = ()

    sync_pool: Optional[SyncConnectionPool] = None
    async_pool: Optional[AsyncConnectionPool] = None
    mutex: Lock = Lock()

    @classmethod
    def init_pools(cls) -> None:
        with cls.mutex:
            if not cls.async_pool:
                logger.debug("Initializing Redis Connection Pool")
                cls.sync_pool = SyncConnectionPool.from_url(**params)  # type: ignore
                cls.async_pool = AsyncConnectionPool.from_url(**params)


class RedisClient(object):
    __slots__ = ("sync_client", "async_client")

    def __init__(self):
        self.sync_client: Optional[SyncConnection] = None
        self.async_client: Optional[AsyncConnection] = None

    def __enter__(self):
        self.sync_client = Redis.from_pool(connection_pool=RedisPools.sync_pool)
        if not self.sync_client.ping():
            raise Exception("Cannot connect to Redis")

        return self.sync_client

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sync_client:
            self.pools.sync_pool.release(self.sync_client)  # type: ignore # noqa

    async def __aenter__(self):
        self.async_client = AsyncRedis.from_pool(connection_pool=RedisPools.async_pool)
        if not await self.async_client.ping():
            raise Exception("Cannot connect to Redis")
        return self.async_client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.async_client:
            await self.pools.async_pool.release(self.async_client)  # type: ignore # noqa

    @classmethod
    async def close_async(cls) -> None:
        logger.debug("Closing Redis client")
        if RedisPools.sync_pool:
            RedisPools.sync_pool.disconnect()
        if RedisPools.async_pool:
            await RedisPools.async_pool.disconnect()

    @classmethod
    def close(cls) -> None:
        logger.debug("Closing Redis client")
        if RedisPools.sync_pool:
            RedisPools.sync_pool.close()
        if RedisPools.async_pool:
            loop = asyncio.get_running_loop() or asyncio.new_event_loop()
            loop.run_until_complete(RedisPools.async_pool.disconnect())


async def init_cache() -> None:
    logger.debug("Initializing Redis cache")
    await asyncio.sleep(0)
    RedisPools.init_pools()
    init_cachify(
        sync_client=Redis.from_pool(connection_pool=RedisPools.sync_pool),
        async_client=AsyncRedis.from_pool(connection_pool=RedisPools.async_pool),
    )
