from contextlib import AbstractContextManager
from threading import Lock
from typing import Optional

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient as SyncMongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from ...conf.app_settings import settings
from ...utils.decorators import singleton


@singleton
class MongoClients:
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


class Mongo(AbstractContextManager):
    __slots__ = ()

    def __enter__(self) -> Database:
        if not MongoClients.sync_client:
            MongoClients.init_clients()
        return MongoClients.sync_client.get_database(name=settings.mongo.db_name)

    async def __aenter__(self):
        if not MongoClients.async_client:
            MongoClients.init_clients()
        return MongoClients.async_client.get_database(name=settings.mongo.db_name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    def init_clients(cls) -> None:
        MongoClients.init_clients()

    @classmethod
    def close(cls) -> None:
        logger.debug("Closing MongoDB")
        if MongoClients.async_client:
            MongoClients.async_client.close()
        if MongoClients.sync_client:
            MongoClients.sync_client.close()


class MongoCollection(AbstractContextManager):
    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __enter__(self) -> Collection:
        with Mongo() as db:
            return db.get_collection(name=self.name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        async with Mongo() as db:
            return db.get_collection(name=self.name)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
