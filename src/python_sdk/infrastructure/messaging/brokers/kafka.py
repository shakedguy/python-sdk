from collections.abc import Collection
from threading import Lock
from typing import Optional

from faststream.confluent import KafkaBroker
from faststream.confluent.fastapi import KafkaRouter

from ....domain.configs import KafkaConfigs
from ....utils.decorators.singleton_decorator import singleton


@singleton
class KafkaBrokerFactory:
    """
    Kafka Broker for handling messaging.
    """

    __slots__ = ()

    router: Optional[KafkaRouter] = None
    broker: Optional[KafkaBroker] = None
    mutex: Lock = Lock()

    @classmethod
    def create_broker(
        cls,
        *,
        connection_name: Optional[str] = None,
        use_ssl: bool = False,
    ) -> KafkaBroker:
        """
        Create a Faststream RabbitMQ broker instance.
        """
        with cls.mutex:
            if cls.broker is None:
                configs = KafkaConfigs(
                    client_id=connection_name,
                    use_ssl=use_ssl,
                )
                cls.broker = KafkaBroker(**configs.model_dump(exclude={"use_ssl"}))

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
    ) -> KafkaRouter:
        with cls.mutex:
            if cls.router is None:
                configs = KafkaConfigs(
                    client_id=connection_name,
                    use_ssl=use_ssl,
                )
                cls.router = KafkaRouter(
                    **configs.model_dump(exclude={"use_ssl"}),
                    schema_url=schema_url,
                    include_in_schema=include_in_schema,
                    prefix=prefix,
                    tags=tags,
                    description=description,
                )
            if cls.broker is None:
                cls.broker = cls.router.broker

        return cls.router
