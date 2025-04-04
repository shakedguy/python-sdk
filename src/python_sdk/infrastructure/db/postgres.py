import asyncio
import logging
from asyncio import Semaphore
from datetime import datetime
from typing import Optional, Union

from asyncpg import Pool as AsyncPool
from asyncpg import Record, create_pool
from asyncpg.connection import Connection
from psycopg import (
    Connection as SyncConnection,
)
from psycopg import (
    Cursor as SyncCursor,
)
from psycopg import (
    ServerCursor as SyncServerCursor,
)
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool as SyncPool
from pydantic_core import from_json, to_json

from ...conf.app_settings import settings
from ...conf.logger import get_logger
from ...utils.decorators import singleton

logger = get_logger(name="Postgres", level=logging.DEBUG)


@singleton
class PostgresConnectionPool(object):
    """
    Singleton class to manage Postgres connection pool.
    """

    __slots__ = ()

    sem: Semaphore = Semaphore(1)
    async_pool: Optional[AsyncPool] = None
    sync_pool: Optional[SyncPool] = None

    @classmethod
    async def init_pools(cls) -> None:
        """
        Initialize the connection pools.
        """
        async with cls.sem:
            if not cls.async_pool:
                logger.debug("Initializing Postgres Connection Pools")
                cls.async_pool = await create_pool(
                    settings.postgres.url,
                    min_size=2,
                    max_size=20,
                    record_class=Record,
                )
                cls.sync_pool: SyncPool = SyncPool(
                    settings.postgres.url,
                    min_size=2,
                    max_size=20,
                )


class Postgres(object):
    __slots__ = ("async_connection", "sync_connection", "sync_cursor")

    def __init__(self) -> None:
        self.async_connection: Optional[Connection] = None
        self.sync_connection: Optional[SyncConnection] = None
        self.sync_cursor: Optional[Union[SyncCursor, SyncServerCursor]] = None

    def __enter__(self) -> Union[SyncCursor, SyncServerCursor]:
        self.sync_connection = PostgresConnectionPool.sync_pool.getconn()
        self.sync_cursor = self.sync_connection.cursor(row_factory=dict_row)
        return self.sync_cursor

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.sync_cursor:
            self.sync_cursor.close()
        if self.sync_connection:
            try:
                self.sync_connection.commit()
            except Exception as e:
                print(f"Failed to commit transaction: {e}")
                self.sync_connection.rollback()
        PostgresConnectionPool.sync_pool.putconn(self.sync_connection)

    async def __aenter__(self) -> Connection:
        # await PostgresConnectionPool.init_pools()
        self.async_connection = await PostgresConnectionPool.async_pool.acquire(
            timeout=5
        )
        await self.async_connection.set_type_codec(
            "json",
            encoder=lambda x: to_json(x).decode(),
            decoder=from_json,
            schema="pg_catalog",
        )
        await self.async_connection.set_type_codec(
            "jsonb",
            encoder=lambda x: to_json(x).decode(),
            decoder=from_json,
            schema="pg_catalog",
        )
        await self.async_connection.set_type_codec(
            "timestamp",  # ✅ Correct type name
            encoder=lambda x: x.replace(tzinfo=None).isoformat() if x else None,
            decoder=lambda x: datetime.fromisoformat(x) if x else None,
            format="text",
            schema="pg_catalog",
        )

        return self.async_connection

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.async_connection:
            await PostgresConnectionPool.async_pool.release(self.async_connection)

    @classmethod
    async def close_async(cls) -> None:
        logger.debug("Closing Postgres client")
        if PostgresConnectionPool.async_pool:
            await PostgresConnectionPool.async_pool.close()
        if PostgresConnectionPool.sync_pool:
            PostgresConnectionPool.sync_pool.close()

    @classmethod
    def close(cls) -> None:
        logger.debug("Closing Postgres client")
        if PostgresConnectionPool.sync_pool:
            PostgresConnectionPool.sync_pool.close()
        if PostgresConnectionPool.async_pool:
            loop = asyncio.get_running_loop() or asyncio.new_event_loop()
            loop.run_until_complete(cls.close_async())
