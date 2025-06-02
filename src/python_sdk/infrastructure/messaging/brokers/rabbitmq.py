from collections.abc import Collection
from threading import Lock
from typing import Optional

from faststream.rabbit import RabbitBroker
from faststream.rabbit.fastapi import RabbitRouter

from ....domain.configs.rabbitmq import RabbitMQConfigs
from ....utils.decorators.singleton_decorator import singleton


@singleton
class RabbitMQBrokerFactory:
    """
    RabbitMQ Broker for handling messaging.
    """

    __slots__ = ()

    router: Optional[RabbitRouter] = None
    broker: Optional[RabbitBroker] = None
    mutex: Lock = Lock()

    @classmethod
    def create_broker(
        cls,
        *,
        connection_name: Optional[str] = None,
        max_consumers: int = 5,
        heartbeat: int = 60,
        connection_timeout: int = 10,
        use_ssl: bool = False,
    ) -> RabbitBroker:
        """
        Create a Faststream RabbitMQ broker instance.
        """
        with cls.mutex:
            if cls.broker is None:
                configs = RabbitMQConfigs(
                    use_ssl=use_ssl,
                    client_properties={
                        "connection_name": connection_name,
                        "max_consumers": max_consumers,
                        "heartbeat": heartbeat,
                        "connection_timeout": connection_timeout,
                    },
                )
                cls.broker = RabbitBroker(
                    **configs.connection_args,
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
        max_consumers: int = 5,
        heartbeat: int = 60,
        connection_timeout: int = 10,
    ) -> RabbitRouter:
        with cls.mutex:
            if cls.router is None:
                configs = RabbitMQConfigs(
                    use_ssl=use_ssl,
                    client_properties={
                        "connection_name": connection_name,
                        "max_consumers": max_consumers,
                        "heartbeat": heartbeat,
                        "connection_timeout": connection_timeout,
                    },
                )

                cls.router = RabbitRouter(
                    **configs.connection_args,
                    schema_url=schema_url,
                    include_in_schema=include_in_schema,
                    prefix=prefix,
                    tags=tags,
                    description=description,
                )
            if cls.broker is None:
                cls.broker = cls.router.broker

        return cls.router
