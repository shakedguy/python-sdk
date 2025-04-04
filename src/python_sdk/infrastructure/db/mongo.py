import logging
from threading import Lock
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient as SyncMongoClient
from pymongo.database import Database

from ...conf.app_settings import settings
from ...conf.logger import get_logger
from ...utils.decorators import singleton

logger = get_logger("Mongo", level=logging.DEBUG)


@singleton
class MongoClients(object):
    __slots__ = ()
    sync_client: Optional[SyncMongoClient] = None
    async_client: Optional[AsyncIOMotorClient] = None
    mutex: Lock = Lock()

    @classmethod
    def init_clients(cls) -> None:
        """
        Initialize the async MongoDB client.
        """
        with cls.mutex:
            if not cls.async_client:
                logger.debug("Initializing MongoDB clients")
                cls.async_client = AsyncIOMotorClient(settings.mongo.url)
                cls.sync_client = SyncMongoClient(settings.mongo.url)


class Mongo(object):
    __slots__ = ()

    def __enter__(self) -> Database:
        return MongoClients.sync_client.get_database(name=settings.mongo.db_name)

    async def __aenter__(self) -> AsyncIOMotorDatabase:
        return MongoClients.async_client.get_database(name=settings.mongo.db_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    def close(cls) -> None:
        logger.debug("Closing MongoDB")
        if MongoClients.async_client:
            MongoClients.async_client.close()
        if MongoClients.sync_client:
            MongoClients.sync_client.close()
