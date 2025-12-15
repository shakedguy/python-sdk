import asyncio
import sys
from typing import Any, Awaitable

from loguru import logger

from ..conf.constants import PSYCOPG_EXISTS, PYMONGO_EXISTS


def init(
        *,
        init_postgres: bool = True,
        init_cache: bool = True,
        init_mongo: bool = True,
        init_messaging: bool = True,
        init_qdrant: bool = True,
) -> int:  # noqa:
    logger.debug("Initializing resources")

    if PSYCOPG_EXISTS and init_postgres:
        init_postgres_client()

    if init_cache:
        from .cache import init_cache

        init_cache()

    if PYMONGO_EXISTS and init_mongo:
        init_mongo_clients()

    if init_qdrant:
        init_qdrant_clients()
    logger.debug("Initialization completed successfully")

    return 0


def cleanup(*args: Any) -> int:  # noqa:

    logger.debug("Cleaning up resources")
    try:
        from .cache import RedisClient
        RedisClient.close()
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")

    try:
        from .db import Mongo
        Mongo.close()
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error closing MongoDB: {e}")
    try:
        from .db import Postgres
        Postgres.close()
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error closing Postgres: {e}")

    logger.debug("Cleanup completed successfully")
    return 0


async def cleanup_async(*args: Any) -> int:  # noqa:

    logger.debug("Cleaning up resources")
    try:
        from .db import Mongo
        Mongo.close()
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error closing MongoDB: {e}")
    try:
        from .db import Postgres
        await Postgres.close_async();
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error closing Postgres or Redis: {e}")

    try:
        from .cache import RedisClient
        RedisClient.close_async()
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")

    logger.debug("Cleanup completed")
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
    if PSYCOPG_EXISTS and init_postgres:
        from .db import PostgresConnectionPool

        tasks.append(PostgresConnectionPool.init_pools_async())
    if init_cache:
        from .cache import init_cache_async

        tasks.append(init_cache_async())
    if PYMONGO_EXISTS and init_mongo:
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
    try:
        from .db import PostgresConnectionPool

        PostgresConnectionPool.init_pools()
    except ImportError:
        pass
    except:
        logger.exception("Failed to initialize Postgres clients")


async def init_postgres_client_async() -> None:

    try:
        from .db import PostgresConnectionPool

        await PostgresConnectionPool.init_pools_async()
    except ImportError:
        pass
    except:
        logger.exception("Failed to initialize Postgres clients")


def init_mongo_clients() -> None:
    try:
        from ..domain.documents import MongoDocument, MongoView
        from .db import Mongo

        Mongo.init_clients()
        for d in MongoDocument.get_all_documents():
            d.create_indexes()

        for v in MongoView.get_all_views():
            v.create()
    except ImportError:
        pass
    except:
        logger.exception("Failed to initialize MongoDB clients")


def init_mongo_clients_async() -> Awaitable:

    try:
        from ..domain.documents import MongoDocument, MongoView
        from .db import Mongo

        Mongo.init_clients()

        return asyncio.gather(
            *(
                    [d.create_indexes_async() for d in MongoDocument.get_all_documents()]
                    + [v.create_async() for v in MongoView.get_all_views()]
            )
        )
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB clients async: {e}")
        return asyncio.sleep(0)


def init_qdrant_clients() -> None:

    try:
        from ..domain.documents.qdrant import QdrantDocument

        for d in QdrantDocument.get_all_documents():
            d.create_collection()
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant clients: {e}")


def init_qdrant_async() -> Awaitable:

    try:
        from ..domain.documents.qdrant import QdrantDocument

        return asyncio.gather(
            *[d.create_indexes_async() for d in QdrantDocument.get_all_documents()]
        )
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant clients async: {e}")
        return asyncio.sleep(0)
