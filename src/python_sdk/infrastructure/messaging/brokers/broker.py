from __future__ import annotations

import json
import ssl
from asyncio import Future, wait_for
from datetime import datetime, timedelta
from functools import cache
from ssl import SSLContext
from typing import Any, AnyStr, Literal, Optional, Sequence, Union, cast, overload

from faststream.broker.fastapi import StreamRouter
from faststream.confluent import KafkaBroker, KafkaMessage, TopicPartition
from faststream.confluent.subscriber.asyncapi import (
    AsyncAPISubscriber as KafkaSubscriber,
)
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitMessage, RabbitQueue
from faststream.rabbit.subscriber.asyncapi import AsyncAPISubscriber as RabbitSubscriber
from faststream.redis import ListSub, PubSub, RedisBroker, RedisMessage, StreamSub
from faststream.redis.subscriber.asyncapi import AsyncAPISubscriber as RedisSubscriber
from faststream.security import BaseSecurity
from faststream.types import SendableMessage
from loguru import logger
from pydantic import AmqpDsn, Field, KafkaDsn, RedisDsn
from pydantic import BaseModel as PydanticBaseModel

from ....conf.app_settings import settings
from ....domain.base.base_model import BaseModel
from ....utils import Crypto, DateTime, Strings
from ..queues import create_rabbit_queue
from .kafka import KafkaBrokerFactory
from .rabbitmq import RabbitMQBrokerFactory
from .redis import RedisBrokerFactory

Subscriber = Union[RedisSubscriber, RabbitSubscriber, KafkaSubscriber]
BrokerType = Union[RabbitBroker, RedisBroker, KafkaBroker]
BrokerUrl = Union[str, RedisDsn, AmqpDsn, KafkaDsn]


class Broker(object):
    __slots__ = (
        "_broker",
        "_security",
        "broker_type",
        "url",
        "connection_name",
        "responses",
        "_kafka_worker",
    )

    def __init__(
        self,
        url: BrokerUrl = settings.broker.url,
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

        connection_name = connection_name or "buzzerpy"
        self.connection_name: Optional[str] = (
            f"{Strings.slugify(connection_name)}:{Crypto.uuidv7()[:12]}"
        )
        self._broker: Union[RabbitBroker, RedisBroker, KafkaBroker]

        self._security: Optional[BaseSecurity] = (
            BaseSecurity(ssl_context=create_ssl_context(), use_ssl=True)
            if tls
            else None
        )
        self.responses: dict[str, Future[bytes]] = {}
        if self.broker_type == "rabbitmq":
            self._broker = RabbitMQBrokerFactory.create_broker(
                connection_name=self.connection_name,
                max_consumers=max_consumers,
                use_ssl=tls,
            )
        elif self.broker_type == "redis":
            self._broker = RedisBrokerFactory.create_broker(
                connection_name=self.connection_name,
                use_ssl=tls,
            )
        elif self.broker_type == "kafka":
            self._broker = KafkaBrokerFactory.create_broker(
                connection_name=self.connection_name,
                use_ssl=tls,
            )
            self._kafka_worker = KafkaRPCWorker(self._broker)
        else:
            raise ValueError(f"Unsupported broker type: {self.broker_type}")

    def _create_redis_broker(self) -> RedisBroker:
        return RedisBroker(
            self.url.unicode_string(),
            security=self._security,
            log_level=settings.log_level,
            logger=logger,
        )

    async def start(self) -> None:
        try:
            if not self._broker.running:
                await self._broker.start()
        except Exception as e:
            logger.error("Error starting broker: {error}", error=e)

    async def close(self) -> None:
        try:
            await self._broker.close()
        except Exception as e:
            logger.error("Error closing broker: {error}", error=e)

    async def publish(
        self,
        message: SendableMessage,
        to: Union[str, RabbitQueue, PubSub, ListSub, StreamSub],
        *,
        exchange: Union[str, RabbitExchange, None] = None,
        pub_type: Optional[Literal["pubsub", "list", "stream"]] = "pubsub",
        headers: dict[str, Any] | None = None,
        maxlen: Optional[int] = None,
        expiration: Optional[int | datetime | float | timedelta] = None,
        routing_key: Optional[str] = "",
        auto_delete: bool = False,
        **kwargs,
    ) -> None:
        match self.broker_type:
            case "redis":
                await cast(RedisBroker, self._broker).publish(
                    _prepare_message(message),
                    channel=to if pub_type == "pubsub" or pub_type is None else None,
                    list=to if pub_type == "list" else None,
                    stream=to if pub_type == "stream" else None,
                    maxlen=maxlen,
                    **kwargs,
                )
            case "kafka":
                await self._broker.publish(
                    _prepare_message(message),
                    to,
                    headers=headers,
                    **kwargs,
                )
            case "rabbitmq":
                queue = (
                    create_rabbit_queue(to, auto_delete=auto_delete)
                    if isinstance(to, str)
                    else to
                )
                await self.declare_rabbit_queue(queue)
                await cast(RabbitBroker, self._broker).publish(
                    _prepare_message(message),
                    queue=queue,
                    exchange=exchange,
                    expiration=expiration,
                    routing_key=routing_key or "",
                    headers=headers,
                    **kwargs,
                )

    async def request(
        self,
        message: SendableMessage,
        to: Union[str, RabbitQueue, PubSub, ListSub, StreamSub],
        *,
        exchange: Union[str, RabbitExchange, None] = None,
        pub_type: Optional[Literal["pubsub", "list", "stream"]] = "pubsub",
        headers: dict[str, Any] | None = None,
        maxlen: Optional[int] = None,
        timeout: Optional[float] = 30.0,
        expiration: Optional[int | datetime | float | timedelta] = None,
        routing_key: Optional[str] = "",
        auto_delete: bool = False,
        **kwargs,
    ) -> Optional[BrokerMessage]:
        if self.broker_type == "kafka":
            response = await self._kafka_worker.request(
                _prepare_message(message),
                to,
                timeout=timeout,
                headers=headers,
                **kwargs,
            )
            return BrokerMessage(body=response)
        if self.broker_type == "redis":
            response: RedisMessage = await cast(RedisBroker, self._broker).request(
                message=_prepare_message(message),
                channel=to if pub_type == "pubsub" or pub_type is None else None,
                list=to if pub_type == "list" else None,
                stream=to if pub_type == "stream" else None,
                maxlen=maxlen,
                timeout=timeout or 30.0,
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
        queue = (
            create_rabbit_queue(to, auto_delete=auto_delete)
            if isinstance(to, str)
            else to
        )
        await self.declare_rabbit_queue(queue)
        response: RabbitMessage = await cast(RabbitBroker, self._broker).request(
            _prepare_message(message),
            queue=queue,
            exchange=exchange,
            timeout=timeout,
            headers=headers,
            routing_key=routing_key,
            expiration=expiration,
            **kwargs,
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
        no_ack: Optional[bool] = False,
        no_reply: Optional[bool] = False,
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
        no_ack: Optional[bool] = False,
        no_reply: Optional[bool] = False,
        group_id: Optional[str] = None,
    ) -> KafkaSubscriber: ...

    @overload
    def subscribe(
        self,
        *,
        to: Union[str, PubSub, ListSub, StreamSub],
        sub_from: Optional[Literal["pubsub", "list", "stream"]] = "pubsub",
        retry: Union[bool, int] = False,
        no_ack: Optional[bool] = False,
        no_reply: Optional[bool] = False,
    ) -> RedisSubscriber: ...

    def subscribe(
        self,
        *,
        to: Union[str, RabbitQueue, PubSub, ListSub, StreamSub],
        exchange: Union[str, RabbitExchange, None] = None,
        retry: Union[bool, int] = False,
        no_ack: Optional[bool] = False,
        no_reply: Optional[bool] = False,
        partitions: Sequence[TopicPartition] = (),
        group_id: Optional[str] = None,
        sub_from: Optional[Literal["pubsub", "list", "stream"]] = "pubsub",
        auto_delete: Optional[bool] = False,
    ) -> Subscriber:
        match self.broker_type:
            case "rabbitmq":
                return self._rabbit_subscriber(
                    cast(RabbitBroker, self._broker),
                    to=to,
                    exchange=exchange,
                    retry=retry,
                    no_ack=no_ack,
                    no_reply=no_reply,
                    auto_delete=auto_delete,
                )
            case "kafka":
                return self._kafka_subscriber(
                    cast(KafkaBroker, self._broker),
                    to=to,
                    partitions=partitions,
                    retry=retry,
                    no_ack=no_ack,
                    no_reply=no_reply,
                    group_id=group_id,
                )
            case "redis":
                return self._redis_subscriber(
                    cast(RedisBroker, self._broker),
                    to=to,
                    sub_from=sub_from,
                    retry=retry,
                    no_ack=no_ack,
                    no_reply=no_reply,
                )
            case _:
                raise ValueError(f"Unsupported broker type: {self.broker_type}")

    @classmethod
    def _redis_subscriber(
        cls,
        broker: RedisBroker,
        *,
        to: Union[str, PubSub, ListSub, StreamSub],
        sub_from: Optional[Literal["pubsub", "list", "stream"]] = "pubsub",
        retry: Union[bool, int] = False,
        no_ack: Optional[bool] = False,
        no_reply: Optional[bool] = False,
    ) -> RedisSubscriber:
        args = {}
        if isinstance(to, ListSub) or sub_from == "list":
            args["list"] = to
        elif isinstance(to, StreamSub) or sub_from == "stream":
            args["stream"] = to
        else:
            args["channel"] = to
        return broker.subscriber(**args, retry=retry, no_ack=no_ack, no_reply=no_reply)

    @classmethod
    def _rabbit_subscriber(
        cls,
        broker: RabbitBroker,
        *,
        to: Union[str, RabbitQueue],
        exchange: Union[str, RabbitExchange, None] = None,
        retry: Union[bool, int] = False,
        no_ack: Optional[bool] = False,
        no_reply: Optional[bool] = False,
        auto_delete: bool = False,
    ) -> RabbitSubscriber:
        queue = (
            create_rabbit_queue(
                to,
                auto_delete=auto_delete,
            )
            if isinstance(to, str)
            else to
        )

        return broker.subscriber(
            queue=queue,
            exchange=exchange,
            retry=retry,
            no_ack=no_ack,
            no_reply=no_reply,
        )

    @classmethod
    def _kafka_subscriber(
        cls,
        broker: KafkaBroker,
        *,
        to: str,
        partitions: Sequence[TopicPartition] = (),
        retry: Union[bool, int] = False,
        no_ack: Optional[bool] = False,
        no_reply: Optional[bool] = False,
        group_id: Optional[str] = None,
    ) -> KafkaSubscriber:
        return broker.subscriber(
            to,
            partitions=partitions,
            retry=retry,
            group_id=group_id,
            no_ack=no_ack,
            no_reply=no_reply,
        )

    @classmethod
    def create_router(
        cls,
        url: BrokerUrl,
        *,
        connection_name: Optional[str] = None,
        max_consumers: int = 5,
        tls: bool = False,
    ) -> StreamRouter:
        url_str = url if isinstance(url, str) else url.unicode_string()
        if "redis" in url_str:
            return RedisBrokerFactory.create_router(
                connection_name=connection_name, use_ssl=tls
            )
        elif "amqp" in url_str:
            return RabbitMQBrokerFactory.create_router(
                connection_name=connection_name,
                use_ssl=tls,
                max_consumers=max_consumers,
            )
        else:
            return KafkaBrokerFactory.create_router(
                connection_name=connection_name, use_ssl=tls
            )

    async def declare_rabbit_queue(self, queue: Union[str, RabbitQueue]) -> RabbitQueue:
        """
        Declare a RabbitMQ queue if it does not exist.
        """
        if self.broker_type != "rabbitmq":
            raise ValueError("This method is only applicable for RabbitMQ brokers.")
        if isinstance(queue, str):
            queue = create_rabbit_queue(queue)
        await cast(RabbitBroker, self._broker).declare_queue(queue)
        return queue


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
        **kwargs,
    ) -> bytes:
        correlation_id = Crypto.uuidv7()
        future = self.responses[correlation_id] = Future[bytes]()

        await self.broker.publish(
            data,
            topic,
            reply_to=self.reply_topic,
            correlation_id=correlation_id,
            headers=headers,
            **kwargs,
        )

        try:
            response: bytes = await wait_for(future, timeout=timeout)
        except TimeoutError:
            self.responses.pop(correlation_id, None)  # noqa
            raise

        return response


class BrokerMessage(BaseModel):
    message_id: str = Field(
        default_factory=Crypto.uuidv7,
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
