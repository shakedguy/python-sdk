import asyncio
import sys
from typing import Any, Awaitable

from loguru import logger


def init(
        *,
        init_postgres: bool = True,
        init_cache: bool = True,
        init_mongo: bool = True,
        init_messaging: bool = True,
        init_qdrant: bool = True,
) -> int:  # noqa:
    logger.debug("Initializing resources")

    if init_postgres:
        init_postgres_client()

    if init_cache:
        from .cache import init_cache

        init_cache()

    if init_mongo:
        init_mongo_clients()

    if init_qdrant:
        init_qdrant_clients()
    logger.debug("Initialization completed successfully")

    return 0


def cleanup(*args: Any) -> int:  # noqa:
    from .cache import RedisClient
    from .db import Mongo, Postgres

    logger.debug("Cleaning up resources")
    Mongo.close()
    Postgres.close()
    RedisClient.close()

    logger.debug("Cleanup completed successfully")
    return 0


async def cleanup_async(*args: Any) -> int:  # noqa:
    from .cache import RedisClient
    from .db import Mongo, Postgres

    logger.debug("Cleaning up resources")
    Mongo.close()
    await asyncio.gather(Postgres.close_async(), RedisClient.close_async())

    logger.debug("Cleanup completed successfully")
    return 0


async def init_async(
        *,
        init_postgres: bool = True,
        init_cache: bool = True,
        init_mongo: bool = True,
        init_qdrant: bool = True,
        init_messaging: bool = True,
) -> int:  # noqa:
    logger.debug("Initializing resources")

    tasks = []
    if init_postgres:
        from .db import PostgresConnectionPool

        tasks.append(PostgresConnectionPool.init_pools_async())
    if init_cache:
        from .cache import init_cache_async

        tasks.append(init_cache_async())
    if init_mongo:
        tasks.append(init_mongo_clients_async())

    if init_qdrant:
        tasks.append(init_qdrant_async())

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Failed to initialize resources: {e}")
        sys.exit(1)

    logger.debug("Initialization completed successfully")
    return 0


def init_postgres_client() -> None:
    from .db import PostgresConnectionPool

    PostgresConnectionPool.init_pools()


async def init_postgres_client_async() -> None:
    from .db import PostgresConnectionPool

    await PostgresConnectionPool.init_pools_async()


def init_mongo_clients() -> None:
    from ..domain.documents import MongoDocument, MongoView
    from .db import Mongo

    Mongo.init_clients()
    for d in MongoDocument.get_all_documents():
        d.create_indexes()

    for v in MongoView.get_all_views():
        v.create()


def init_mongo_clients_async() -> Awaitable:
    from ..domain.documents import MongoDocument, MongoView
    from .db import Mongo

    Mongo.init_clients()

    return asyncio.gather(
        *(
                [d.create_indexes_async() for d in MongoDocument.get_all_documents()]
                + [v.create_async() for v in MongoView.get_all_views()]
        )
    )


def init_qdrant_clients() -> None:
    from ..domain.documents.qdrant import QdrantDocument

    for d in QdrantDocument.get_all_documents():
        d.create_collection()


def init_qdrant_async() -> Awaitable:
    from ..domain.documents.qdrant import QdrantDocument

    return asyncio.gather(
        *[d.create_indexes_async() for d in QdrantDocument.get_all_documents()]
    )
