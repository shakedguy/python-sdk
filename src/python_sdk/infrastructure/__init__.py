import asyncio
import logging
from typing import Any

from .cache import init_cache
from .db import MongoClients, PostgresConnectionPool


def cleanup(*args: Any) -> int:  # noqa:
    from ..conf.logger import get_logger
    from .cache import RedisClient
    from .db import Mongo, Postgres
    from .messaging import RabbitMQ

    logger = get_logger("PythoSDK.Infrastructure", level=logging.DEBUG)
    logger.debug("Cleaning up resources")
    RabbitMQ.close()
    Postgres.close()
    Mongo.close()
    RedisClient.close()

    logger.debug("Cleanup completed successfully")
    return 0


async def cleanup_async(*args: Any) -> int:  # noqa:
    from ..conf.logger import get_logger
    from .cache import RedisClient
    from .db import Mongo, Postgres
    from .messaging import RabbitMQ

    logger = get_logger("PythoSDK.Infrastructure", level=logging.DEBUG)
    logger.debug("Cleaning up resources")
    Mongo.close()
    await asyncio.gather(
        RabbitMQ.close_async(), Postgres.close_async(), RedisClient.close_async()
    )

    logger.debug("Cleanup completed successfully")
    return 0


async def init_async(*args: Any) -> int:  # noqa:
    from ..conf.logger import get_logger
    from .cache import RedisClient
    from .db import Mongo, Postgres
    from .messaging import RabbitMQ

    logger = get_logger("PythoSDK.Infrastructure", level=logging.DEBUG)
    logger.debug("Initializing resources")
    MongoClients.init_clients()
    await asyncio.gather(
        init_cache(),
    )

    logger.debug("Initialization completed successfully")
    return 0
