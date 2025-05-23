import asyncio
import logging
import sys
from typing import Any

from loguru import logger


def init(
    *,
    init_postgres: bool = True,
    init_cache: bool = True,
    init_mongo: bool = True,
    init_messaging: bool = True,
) -> int:  # noqa:
    logger.debug("Initializing resources")

    if init_postgres:
        from .db import PostgresConnectionPool

        PostgresConnectionPool.init_pools()

    if init_cache:
        from .cache import init_cache

        init_cache()

    if init_mongo:
        init_mongo_clients()
    logger.debug("Initialization completed successfully")

    return 0


def cleanup(*args: Any) -> int:  # noqa:
    from .cache import RedisClient
    from .db import Mongo, Postgres
    from .messaging import RabbitMQ

    logger.debug("Cleaning up resources")
    Mongo.close()
    RabbitMQ.close()
    Postgres.close()
    RedisClient.close()

    logger.debug("Cleanup completed successfully")
    return 0


async def cleanup_async(*args: Any) -> int:  # noqa:
    from .cache import RedisClient
    from .db import Mongo, Postgres
    from .messaging import RabbitMQ

    logger.debug("Cleaning up resources")
    Mongo.close()
    await asyncio.gather(
        RabbitMQ.close_async(), Postgres.close_async(), RedisClient.close_async()
    )

    logger.debug("Cleanup completed successfully")
    return 0


async def init_async(
    *,
    init_postgres: bool = True,
    init_cache: bool = True,
    init_mongo: bool = True,
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

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Failed to initialize resources: {e}")
        sys.exit(1)

    logger.debug("Initialization completed successfully")
    return 0


def init_mongo_clients() -> None:
    from ..orm import Document, View
    from .db import Mongo

    Mongo.init_clients()
    for d in Document.get_all_documents():
        d.create_indexes()

    for v in View.get_all_views():
        v.create()


async def init_mongo_clients_async():
    from ..orm import Document, View
    from .db import Mongo

    Mongo.init_clients()

    await asyncio.gather(
        *(
            [d.create_indexes_async() for d in Document.get_all_documents()]
            + [v.create_async() for v in View.get_all_views()]
        )
    )
