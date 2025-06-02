from collections.abc import Collection
from threading import Lock
from typing import Optional

from faststream.redis import RedisBroker
from faststream.redis.fastapi import RedisRouter

from ....domain.configs import RedisConfigs
from ....utils.decorators.singleton_decorator import singleton


@singleton
class RedisBrokerFactory:
    """
    Redis Broker for handling messaging.
    """

    __slots__ = ()

    router: Optional[RedisRouter] = None
    broker: Optional[RedisBroker] = None
    mutex: Lock = Lock()

    @classmethod
    def create_broker(
        cls,
        *,
        connection_name: Optional[str] = None,
        use_ssl: bool = False,
    ) -> RedisBroker:
        """
        Create a Faststream RabbitMQ broker instance.
        """
        with cls.mutex:
            if cls.broker is None:
                configs = RedisConfigs(client_name=connection_name, use_ssl=use_ssl)
                cls.broker = RedisBroker(
                    **configs.model_dump(exclude={"username", "password", "use_ssl"})
                )

            return cls.broker

    @classmethod
    def create_router(
        cls,
        *,
        connection_name: Optional[str] = None,
        use_ssl: bool = False,
        schema_url: str = "/",
        include_in_schema: bool = True,
        prefix: str = "/messaging",
        tags: Optional[Collection[str]] = None,
        description: Optional[str] = None,
    ) -> RedisRouter:
        with cls.mutex:
            if cls.router is None:
                configs = RedisConfigs(client_name=connection_name, use_ssl=use_ssl)
                cls.router = RedisRouter(
                    **configs.model_dump(exclude={"username", "password", "use_ssl"}),
                    schema_url=schema_url,
                    include_in_schema=include_in_schema,
                    prefix=prefix,
                    tags=tags,
                    description=description,
                )
            if cls.broker is None:
                cls.broker = cls.router.broker

        return cls.router
