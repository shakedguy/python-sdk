from __future__ import annotations

import json
import ssl
from asyncio import Future, wait_for
from datetime import datetime, timedelta
from functools import cache
from ssl import SSLContext
from typing import Any, AnyStr, Literal, Optional, Sequence, Union, cast, overload

from faststream.confluent import KafkaBroker, KafkaMessage, TopicPartition
from faststream.confluent.subscriber.asyncapi import (
    AsyncAPISubscriber as KafkaSubscriber,
)
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitMessage, RabbitQueue
from faststream.rabbit.subscriber.asyncapi import AsyncAPISubscriber as RabbitSubscriber
from faststream.redis import RedisBroker, RedisMessage
from faststream.redis.subscriber.asyncapi import AsyncAPISubscriber as RedisSubscriber
from faststream.security import BaseSecurity
from faststream.types import SendableMessage
from loguru import logger
from pydantic import AmqpDsn, Field, KafkaDsn, RedisDsn
from pydantic import BaseModel as PydanticBaseModel

from ...conf import settings
from ...domain import BaseModel
from ...utils import Crypto, DateTime, Strings

Subscriber = Union[RedisSubscriber, RabbitSubscriber, KafkaSubscriber]
BrokerType = Union[RabbitBroker, RedisBroker, KafkaBroker]
BrokerUrl = Union[str, RedisDsn, AmqpDsn, KafkaDsn]


class Broker(object):
    def __init__(
        self,
        url: BrokerUrl,
        *,
        connection_name: Optional[str] = None,
        max_consumers: int = 5,
        tls: bool = False,
    ) -> None:
        url = url.lower() if isinstance(url, str) else url.unicode_string()
        self.broker_type: Literal["rabbitmq", "redis", "kafka"] = (
            "redis" if "redis" in url else "rabbitmq" if "amqp" in url else "kafka"
        )
        self.url: BrokerUrl = (
            RedisDsn(url=url)
            if self.broker_type == "redis"
            else AmqpDsn(url=url)
            if self.broker_type == "rabbitmq"
            else KafkaDsn(url=url)
        )
        self.max_consumers: int = max_consumers
        connection_name = connection_name or "buzzerpy"
        self.connection_name: Optional[str] = (
            f"{Strings.slugify(connection_name)}:{Crypto.uuid7()[:12]}"
        )
        self._broker: Union[RabbitBroker, RedisBroker, KafkaBroker]

        self._security: Optional[BaseSecurity] = (
            BaseSecurity(ssl_context=create_ssl_context(), use_ssl=True)
            if tls
            else None
        )
        self.responses: dict[str, Future[bytes]] = {}
        if self.broker_type == "rabbitmq":
            self._broker = self._create_rabbit_broker()
        elif self.broker_type == "redis":
            self._broker = self._create_redis_broker()
        elif self.broker_type == "kafka":
            self._broker = self._create_kafka_broker()
        else:
            raise ValueError(f"Unsupported broker type: {self.broker_type}")

    def _create_rabbit_broker(self) -> RabbitBroker:
        args = {
            "log_level": settings.log_level,
            "reconnect_interval": 5.0,
            "publisher_confirms": False,
            "max_consumers": self.max_consumers,
            "security": self._security,
            "logger": logger,
            "client_properties": {
                "connection_name": self.connection_name,
                "auth": "PLAIN",
            },
        }
        if self._security is None:
            args["url"] = self.url.unicode_string()  # type: ignore
        else:
            args["client_properties"]["auth"] = "EXTERNAL"
            args["host"] = self.url.host  # type: ignore
            args["port"] = self.url.port
        return RabbitBroker(**args)

    def _create_kafka_broker(self) -> KafkaBroker:
        return KafkaBroker(
            self.url.unicode_string(),
            security=self._security,
            log_level=settings.log_level,
            logger=logger,
        )

    def _create_redis_broker(self) -> RedisBroker:
        return RedisBroker(
            self.url.unicode_string(),
            security=self._security,
            log_level=settings.log_level,
            logger=logger,
        )

    async def start(self) -> None:
        try:
            await self._broker.start()
        except Exception as e:
            logger.error(f"Error starting broker: {repr(e)}")

    async def close(self) -> None:
        try:
            await self._broker.close()
        except Exception as e:
            logger.error(f"Error closing broker: {repr(e)}")

    async def publish(
        self,
        *,
        to: str,
        message: SendableMessage,
        headers: dict[str, Any] | None = None,
    ) -> None:
        await self._broker.publish(_prepare_message(message), to, headers=headers)

    async def request(
        self,
        *,
        message: SendableMessage,
        to: Union[str, RabbitQueue],
        exchange: Union[str, RabbitExchange, None] = None,
        headers: dict[str, Any] | None = None,
        timeout: Optional[float] = 10.0,
        routing_key: Optional[str] = None,
        expiration: Optional[float] = None,
    ) -> Optional[BrokerMessage]:
        if self.broker_type == "kafka":
            worker = KafkaRPCWorker(broker=self._broker)
            response = await worker.request(
                _prepare_message(message), to, timeout=timeout, headers=headers
            )
            return BrokerMessage(body=response)
        if self.broker_type == "redis":
            self._broker = cast(RedisBroker, self._broker)
            response: RedisMessage = await self._broker.request(
                _prepare_message(message),
                list=to,
                timeout=timeout,
                headers=headers,
            )
            return (
                BrokerMessage(
                    body=response.body,
                    correlation_id=response.correlation_id,
                    message_id=response.message_id,
                    content_type=response.content_type,
                )
                if response
                else None
            )

        self._broker = cast(RabbitBroker, self._broker)
        response: RabbitMessage = await self._broker.request(
            _prepare_message(message),
            queue=to,
            exchange=exchange,
            timeout=timeout,
            headers=headers,
            routing_key=routing_key,
            expiration=expiration,
        )
        return (
            BrokerMessage(
                body=response.raw_message.body,
                message_id=response.message_id,
                content_type=response.content_type,
                headers=response.headers,
                correlation_id=response.correlation_id,
            )
            if response
            else None
        )

    async def stream(self, *, to: str, message: SendableMessage):
        if self.broker_type == "redis":
            self._broker = cast(RedisBroker, self._broker)
            await self._broker.publish(_prepare_message(message), stream=to)

        else:
            await self._broker.publish(_prepare_message(message), to)

    @overload
    def subscribe(
        self,
        *,
        to: Union[str, RabbitQueue],
        exchange: Union[str, RabbitExchange, None] = None,
        retry: Union[bool, int] = False,
        expiration: Optional[Union[int, float]] = None,
        auto_delete: bool = False,
    ) -> RabbitSubscriber: ...

    @overload
    def subscribe(
        self,
        *,
        to: str,
        partitions: Sequence[TopicPartition] = (),
        retry: Union[bool, int] = False,
        group_id: Optional[str] = None,
    ) -> KafkaSubscriber: ...

    @overload
    def subscribe(
        self,
        *,
        to: str,
        sub_from: Literal["pubsub", "list", "stream"] = "pubsub",
    ) -> RedisSubscriber: ...

    def subscribe(
        self,
        *,
        to: Union[str, RabbitQueue],
        exchange: Union[str, RabbitExchange, None] = None,
        retry: Union[bool, int] = False,
        partitions: Sequence[TopicPartition] = (),
        group_id: Optional[str] = None,
        sub_from: Literal["pubsub", "list", "stream"] = "pubsub",
        auto_delete: Optional[bool] = False,
    ) -> Subscriber:
        if self.broker_type == "rabbitmq":
            self._broker = cast(RabbitBroker, self._broker)
            return self._broker.subscriber(
                queue=RabbitQueue(
                    name=to,
                    durable=True,
                    exclusive=False,
                    auto_delete=auto_delete or False,
                )
                if isinstance(to, str)
                else to,
                exchange=exchange,
                retry=retry,
            )
        elif self.broker_type == "kafka":
            self._broker = cast(KafkaBroker, self._broker)
            return self._broker.subscriber(
                to, partitions=partitions, retry=retry, group_id=group_id
            )
        elif self.broker_type == "redis":
            self._broker = cast(RedisBroker, self._broker)
            args = {}
            if sub_from == "list":
                args["list"] = to
            elif sub_from == "stream":
                args["stream"] = to
            else:
                args["channel"] = to
            return self._broker.subscriber(**args, retry=retry)
        else:
            raise ValueError(f"Unsupported broker type: {self.broker_type}")


class KafkaRPCWorker:
    def __init__(self, broker: KafkaBroker, reply_topic: str = "responses") -> None:
        self.responses: dict[str, Future[bytes]] = {}
        self.broker = broker
        self.reply_topic = reply_topic

        self.subscriber = broker.subscriber(reply_topic)
        self.subscriber(self._handle_responses)

    def _handle_responses(self, msg: KafkaMessage) -> None:
        """Our replies subscriber."""
        if future := self.responses.pop(msg.correlation_id, None):
            future.set_result(msg.body)

    async def request(
        self,
        data: SendableMessage,
        topic: str,
        timeout: float = 10.0,
        headers: Optional[dict[str, str]] = None,
    ) -> bytes:
        correlation_id = Crypto.uuid7()
        future = self.responses[correlation_id] = Future[bytes]()

        await self.broker.publish(
            data,
            topic,
            reply_to=self.reply_topic,
            correlation_id=correlation_id,
            headers=headers,
        )

        try:
            response: bytes = await wait_for(future, timeout=timeout)
        except TimeoutError:
            self.responses.pop(correlation_id, None)  # noqa
            raise

        return response


class BrokerMessage(BaseModel):
    message_id: str = Field(
        default_factory=Crypto.uuid7,
        title="Message ID",
        description="Unique identifier for the message",
    )
    body: bytes = Field(default_factory=dict, title="Data", description="Message data")
    content_type: Optional[str] = Field(
        default=None,
        title="Content Type",
        description="Content type of the message",
    )
    headers: Optional[dict[str, str]] = Field(
        default_factory=dict, title="Headers", description="Message headers"
    )
    correlation_id: Optional[str] = Field(
        default=None,
        title="Correlation ID",
        description="Correlation ID for the message",
    )
    timestamp: Optional[Union[int, datetime, float, timedelta]] = Field(
        default_factory=DateTime.epoch_now,
        title="Timestamp",
        description="Timestamp of the message",
    )


def _prepare_message(
    message: AnyStr | dict | PydanticBaseModel,
) -> Union[PydanticBaseModel, BrokerMessage]:
    if isinstance(message, PydanticBaseModel):
        return message
    content_type = (
        "application/json" if isinstance(message, (dict, list)) else "text/plain"
    )
    body: AnyStr = json.dumps(message) if isinstance(message, (dict, list)) else message
    body = body.encode("utf-8") if isinstance(body, str) else body
    return BrokerMessage(body=body, content_type=content_type)


@cache
def create_ssl_context() -> SSLContext:
    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=settings.broker.cafile,
    )

    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    context.load_cert_chain(
        certfile=settings.broker.certfile,
        keyfile=settings.broker.keyfile,
        password=settings.broker.cert_password,
    )

    return context
