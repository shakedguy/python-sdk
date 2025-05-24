from __future__ import annotations

import ssl
from asyncio import Future, wait_for
from datetime import datetime, timedelta
from functools import cache
from ssl import SSLContext
from typing import Any, AnyStr, Literal, Optional, Sequence, Union, cast, overload

import orjson
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

from ...conf import settings
from ...domain import BaseModel
from ...utils import Crypto, DateTime, Strings

Subscriber = Union[RedisSubscriber, RabbitSubscriber, KafkaSubscriber]
BrokerType = Union[RabbitBroker, RedisBroker, KafkaBroker]
BrokerUrl = Union[str, RedisDsn, AmqpDsn, KafkaDsn]


class Broker(object):
    __slots__ = (
        "_broker",
        "_virtualhost",
        "_security",
        "broker_type",
        "url",
        "max_consumers",
        "connection_name",
        "responses",
        "_kafka_worker",
    )

    def __init__(
        self,
        url: BrokerUrl,
        *,
        connection_name: Optional[str] = None,
        max_consumers: int = 5,
        virtualhost: Optional[str] = None,
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
        self._virtualhost: Optional[str] = virtualhost
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
        self._kafka_worker: Optional[KafkaRPCWorker] = (
            KafkaRPCWorker(broker=self._broker) if self.broker_type == "kafka" else None
        )

    def _create_rabbit_broker(self) -> RabbitBroker:
        args: dict[str, Any] = {
            "log_level": settings.log_level,
            "reconnect_interval": 5.0,
            "publisher_confirms": False,
            "max_consumers": self.max_consumers,
            "logger": logger,
            "client_properties": {
                "connection_name": self.connection_name,
            },
        }

        if self._security is None:
            print(self.url.unicode_string(), self._virtualhost)
            return RabbitBroker(
                "amqp://appoint:8175f0bb084d58ed@194.32.77.169:5672/esbot",
                virtualhost="esbot",
                # **args,
            )

        else:
            args["client_properties"]["auth"] = "EXTERNAL"
            args["security"] = self._security
            return RabbitBroker(
                host=self.url.host,
                port=self.url.port,
                virtualhost=self._virtualhost,
                **args,
            )

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
        message: SendableMessage,
        to: str,
        *,
        exchange: Union[str, RabbitExchange, None] = None,
        pub_type: Optional[Literal["pubsub", "list", "stream"]] = "pubsub",
        headers: dict[str, Any] | None = None,
        maxlen: Optional[int] = None,
        expiration: Optional[int | datetime | float | timedelta] = None,
        routing_key: Optional[str] = "",
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
                await cast(RabbitBroker, self._broker).publish(
                    _prepare_message(message),
                    queue=to
                    if isinstance(to, RabbitQueue)
                    else RabbitQueue(
                        name=to, durable=True, exclusive=False, auto_delete=False
                    ),
                    exchange=exchange,
                    expiration=expiration,
                    routing_key=routing_key or "",
                    headers=headers,
                    **kwargs,
                )

    async def request(
        self,
        message: SendableMessage,
        to: str,
        *,
        exchange: Union[str, RabbitExchange, None] = None,
        pub_type: Optional[Literal["pubsub", "list", "stream"]] = "pubsub",
        headers: dict[str, Any] | None = None,
        maxlen: Optional[int] = None,
        timeout: Optional[float] = 30.0,
        expiration: Optional[int | datetime | float | timedelta] = None,
        routing_key: Optional[str] = "",
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
                message=message,
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

        response: RabbitMessage = await cast(RabbitBroker, self._broker).request(
            _prepare_message(message),
            queue=to,
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
            RabbitQueue(
                name=to,
                durable=True,
                exclusive=False,
                auto_delete=auto_delete or False,
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
        correlation_id = Crypto.uuid7()
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
    body: AnyStr = (
        orjson.dumps(message) if isinstance(message, (dict, list)) else message
    )
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
