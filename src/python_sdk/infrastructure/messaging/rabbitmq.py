import asyncio
import logging
import ssl
import time
from asyncio import Semaphore
from contextlib import AbstractContextManager
from functools import cache
from ssl import SSLContext
from threading import Lock, Thread
from typing import Any, AnyStr, Awaitable, Callable, Optional, Self, Union

import pika
from aio_pika import Message, connect_robust
from aio_pika.abc import (
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractRobustChannel,
    AbstractRobustConnection,
)
from aio_pika.abc import (
    DeliveryMode as AioPikaDeliveryMode,
)
from pika import BlockingConnection, SSLOptions
from pika.adapters.blocking_connection import BlockingChannel
from pika.delivery_mode import DeliveryMode
from pika.exchange_type import ExchangeType

from ...conf import settings
from ...conf.logger import get_logger
from ...utils import Crypto
from ...utils.decorators import singleton

logging.getLogger("pika").setLevel(logging.ERROR)
logger = get_logger(name="RabbitMQ", level=logging.DEBUG)


@singleton
class RabbitMQConnectionManager:
    sync_connection: Optional[BlockingConnection] = None
    sync_channel: Optional[BlockingChannel] = None
    async_connection: Optional[AbstractRobustConnection] = None
    async_channel: Optional[AbstractRobustChannel] = None
    connection_mutex: Lock = Lock()
    channel_mutex: Lock = Lock()
    connection_sem: Semaphore = Semaphore(1)
    channel_sem: Semaphore = Semaphore(1)

    def __init__(self):
        self.sync_connection = RabbitMQConnectionManager.create_connection()

    @classmethod
    def create_connection(cls) -> BlockingConnection:
        with RabbitMQConnectionManager.connection_mutex:
            if RabbitMQConnectionManager.sync_connection is None:
                logger.debug("Connecting to RabbitMQ")
                RabbitMQConnectionManager.sync_connection = _create_sync_connection()

        return RabbitMQConnectionManager.sync_connection

    @classmethod
    async def create_async_connection(cls) -> AbstractRobustConnection:
        async with RabbitMQConnectionManager.connection_sem:
            if RabbitMQConnectionManager.async_connection is None:
                logger.debug("Connecting to RabbitMQ")
                RabbitMQConnectionManager.async_connection = (
                    await _create_async_connection()
                )
        return RabbitMQConnectionManager.async_connection

    @classmethod
    def close(cls) -> None:
        try:
            if cls.sync_connection and cls.sync_connection.is_open:
                cls.close_channel()
                logger.debug("Closing RabbitMQ connection")
                cls.sync_connection.close()
                cls.sync_connection = None
        except:  # noqa
            pass

    @classmethod
    async def close_async(cls) -> None:
        if cls.async_connection and not cls.async_connection.is_closed:
            await cls.close_async_channel()
            logger.debug("Closing RabbitMQ async connection")
            await cls.async_connection.close()
            cls.async_connection = None

    @classmethod
    def reconnect(cls) -> None:
        logger.debug("Reconnecting to RabbitMQ")
        cls.sync_connection = _create_sync_connection()

        cls.create_channel()

    @classmethod
    async def reconnect_async(cls) -> None:
        logger.debug("Reconnecting to RabbitMQ")
        await cls.close_async()
        await cls.create_async_connection()
        await cls.create_async_channel()

    @classmethod
    def create_channel(cls) -> BlockingChannel:
        with RabbitMQConnectionManager.channel_mutex:
            if (
                RabbitMQConnectionManager.sync_channel is None
                or RabbitMQConnectionManager.sync_channel.is_closed
            ):
                logger.debug("Creating new channel")
                RabbitMQConnectionManager.create_connection()
                RabbitMQConnectionManager.sync_channel = (
                    RabbitMQConnectionManager.sync_connection.channel()
                )

        return RabbitMQConnectionManager.sync_channel

    @classmethod
    async def create_async_channel(
        cls, publisher_confirms: bool = True
    ) -> AbstractRobustChannel:
        async with RabbitMQConnectionManager.channel_sem:
            if (
                RabbitMQConnectionManager.async_channel is None
                or RabbitMQConnectionManager.async_channel.is_closed
            ):
                logger.debug("Creating new channel")
                await RabbitMQConnectionManager.create_async_connection()
                RabbitMQConnectionManager.async_channel = (
                    await RabbitMQConnectionManager.async_connection.channel(
                        publisher_confirms=publisher_confirms
                    )
                )

        return RabbitMQConnectionManager.async_channel

    @classmethod
    def close_channel(cls) -> None:
        try:
            if cls.sync_channel and cls.sync_channel.is_open:
                logger.debug("Closing RabbitMQ channel")
                cls.sync_channel.close()
                cls.sync_channel = None
        except:  # noqa
            pass

    @classmethod
    async def close_async_channel(cls) -> None:
        logger.debug("Closing RabbitMQ async channel")
        if cls.async_channel and not cls.async_channel.is_closed:
            await cls.async_channel.close()
            cls.async_channel = None


class RabbitMQ(AbstractContextManager):
    declared_exchanges: list[str] = [""]
    declared_queues: list[str] = []

    def __init__(self) -> None:
        self.sync_channel: Optional[BlockingChannel] = None
        self.async_channel: Optional[AbstractRobustChannel] = None

    def __enter__(self) -> Self:
        self.sync_channel = RabbitMQConnectionManager.create_channel()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type:
            try:
                RabbitMQConnectionManager.reconnect()
            except:  # noqa
                logger.exception("Error during RabbitMQ reconnection")

        return None

    async def __aenter__(self) -> Self:
        self.async_channel = await RabbitMQConnectionManager.create_async_channel()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type:
            await RabbitMQConnectionManager.reconnect_async()

        return None

    async def publish_async(
        self,
        queue: str,
        body: AnyStr,
        exchange: Optional[str] = None,
        exchange_type: Optional[ExchangeType] = None,
        expiration: Optional[Union[int, str]] = None,
        delivery_mode: Optional[AioPikaDeliveryMode] = None,
    ) -> None:
        exchange = exchange or ""

        exchange_type = exchange_type or ExchangeType.direct
        delivery_mode = delivery_mode or AioPikaDeliveryMode.PERSISTENT

        publish_exchange: Optional[AbstractExchange] = None
        if exchange not in self.declared_exchanges:
            publish_exchange = await self.async_channel.declare_exchange(
                name=exchange, type=exchange_type
            )
            self.declared_exchanges.append(exchange)
        if queue not in self.declared_queues:
            self.declared_queues.append(queue)
            queue_obj = await self.async_channel.declare_queue(
                name=queue, durable=True, exclusive=False, auto_delete=False
            )
            if exchange != "":
                await queue_obj.bind(exchange=exchange)
        body = body.encode("utf-8") if isinstance(body, str) else body
        expiration = str(expiration) if expiration else None

        if exchange != "":
            publish_exchange = (
                publish_exchange or await self.async_channel.get_exchange(name=exchange)
            )
        else:
            publish_exchange = self.async_channel.default_exchange

        await publish_exchange.publish(
            message=Message(
                body=body,
                content_type="text/plain",
                content_encoding="utf-8",
                expiration=expiration,
                delivery_mode=delivery_mode,
            ),
            routing_key=queue,
            mandatory=True,
        )

    def publish(
        self,
        queue: str,
        body: AnyStr,
        exchange: Optional[str] = None,
        exchange_type: Optional[ExchangeType] = None,
        expiration: Optional[Union[int, str]] = None,
        delivery_mode: Optional[DeliveryMode] = None,
    ) -> None:
        exchange = exchange or ""
        exchange_type = exchange_type or ExchangeType.direct
        delivery_mode = delivery_mode or DeliveryMode.Persistent

        if exchange not in self.declared_exchanges:
            self.sync_channel.exchange_declare(
                exchange=exchange, exchange_type=exchange_type
            )
            self.declared_exchanges.append(exchange)

        if queue not in self.declared_queues:
            self.declared_queues.append(queue)
            self.sync_channel.queue_declare(
                queue=queue, durable=True, exclusive=False, auto_delete=False
            )
            if exchange != "":
                self.sync_channel.queue_bind(
                    queue=queue,
                    exchange=exchange,
                    routing_key="",
                )

        body = body.encode("utf-8") if isinstance(body, str) else body
        expiration = str(expiration) if expiration else None
        self.sync_channel.basic_publish(
            exchange=exchange,
            routing_key=queue,
            body=body,
            mandatory=True,
            properties=pika.BasicProperties(
                content_type="text/plain",
                content_encoding="utf-8",
                expiration=expiration,
                delivery_mode=delivery_mode,
            ),
        )

    def get(self, queue: str, auto_ack: bool = True) -> Optional[bytes]:
        if queue not in self.declared_queues:
            self.sync_channel.queue_declare(
                queue=queue, durable=True, exclusive=False, auto_delete=False
            )
            self.declared_queues.append(queue)

        for _ in range(3):
            try:
                method_frame, header_frame, body = self.sync_channel.basic_get(
                    queue=queue, auto_ack=auto_ack
                )
                if method_frame:
                    return body

            except Exception as e:
                logger.exception("Error during getting message: %s", e)
            time.sleep(0.2)
        return None

    async def get_async(
        self, queue: str, no_ack: bool = False
    ) -> Optional[AbstractIncomingMessage]:
        if queue in self.declared_queues:
            fetcher = self.async_channel.get_queue(name=queue)

        else:
            fetcher = await self.async_channel.declare_queue(
                name=queue, durable=True, exclusive=False, auto_delete=False
            )
            self.declared_queues.append(queue)
        for _ in range(3):
            try:
                message = await fetcher.get(no_ack=no_ack)
                if message:
                    return message
            except Exception as e:
                logger.exception("Error during getting message: %s", e)
            await asyncio.sleep(0.2)
        return None

    async def subscribe_async(
        self,
        queue: str,
        callback: Callable[[AbstractIncomingMessage], Awaitable],
        no_ack: bool = False,
        concurrent: int = 1,
        consumer_tag: Optional[str] = None,
    ) -> None:
        consumer_tag = consumer_tag or Crypto.uuid7()
        await self.async_channel.set_qos(prefetch_count=concurrent)

        if queue not in self.declared_queues:
            consumer = await self.async_channel.declare_queue(
                name=queue, durable=True, exclusive=False, auto_delete=False
            )
        else:
            consumer = await self.async_channel.get_queue(name=queue)

        await consumer.consume(
            callback=callback, no_ack=no_ack, consumer_tag=consumer_tag
        )

    def subscribe(
        self,
        queue: str,
        callback: Callable[[BlockingChannel, Any, Any, bytes], None],
        auto_ack: bool = False,
        concurrent: int = 1,
        timeout: Optional[int] = None,
        consumer_tag: Optional[str] = None,
    ) -> None:
        consumer_tag = consumer_tag or Crypto.uuid7()
        self.sync_channel.basic_qos(prefetch_count=concurrent)
        if queue not in self.declared_queues:
            self.sync_channel.queue_declare(
                queue=queue, durable=True, exclusive=False, auto_delete=False
            )
            self.declared_queues.append(queue)

        self.sync_channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
            auto_ack=auto_ack,
            consumer_tag=consumer_tag,
        )

        def start_consuming():
            try:
                self.sync_channel.start_consuming()
            except Exception as e:
                logger.exception("Error during consuming: %s", e)
            return

        if timeout:
            t = Thread(target=start_consuming, daemon=True)
            t.start()
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(0.2)
            self.sync_channel.connection.add_callback_threadsafe(
                lambda: self.sync_channel.stop_consuming(consumer_tag=consumer_tag)
            )
            t.join()

        else:
            start_consuming()

    @classmethod
    def close(cls) -> None:
        RabbitMQConnectionManager.close()

    @classmethod
    async def close_async(cls) -> None:
        await RabbitMQConnectionManager.close_async()


def _create_sync_connection(
    connection_name: Optional[str] = None,
) -> BlockingConnection:
    base_args = {
        "host": settings.rabbit_mq.dsn.host,
        "port": settings.rabbit_mq.dsn.port,
        "virtual_host": settings.rabbit_mq.virtual_host,
        "connection_attempts": 3,
        "retry_delay": 5,
        "socket_timeout": 5,
        "stack_timeout": 5,
        "heartbeat": 60,
        "channel_max": 20,
        "client_properties": {
            "connection_name": connection_name or "python-sdk",
        },
    }

    conn_params = (
        pika.ConnectionParameters(
            **base_args,
            ssl_options=SSLOptions(create_ssl_context(), settings.rabbit_mq.dsn.host),
            client_properties={
                **base_args["client_properties"],
                "auth": "EXTERNAL",
            },
        )
        if settings.rabbit_mq.use_ssl
        else pika.ConnectionParameters(
            **base_args,
            credentials=pika.PlainCredentials(
                settings.rabbit_mq.dsn.username,
                settings.rabbit_mq.dsn.password,
            ),
        )
    )

    return BlockingConnection(parameters=conn_params)


async def _create_async_connection(
    connection_name: Optional[str] = None,
) -> AbstractRobustConnection:
    basic_params = {
        "virtual_host": settings.rabbit_mq.virtual_host,
        "channel_max": 20,
        "client_properties": {
            "connection_name": connection_name or "python-sdk",
            "auth": "PLAIN",
        },
    }

    if settings.rabbit_mq.use_ssl:
        conn_params = {
            "host": settings.rabbit_mq.dsn.host,
            "port": settings.rabbit_mq.dsn.port,
            "ssl_context": create_ssl_context(),
            **basic_params,
        }
        conn_params["client_properties"]["auth"] = "EXTERNAL"
        return await connect_robust(**conn_params, login="", password="")
    else:
        return await connect_robust(
            str(settings.rabbit_mq.url),
            **basic_params,
        )


@cache
def create_ssl_context() -> SSLContext:
    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=settings.rabbit_mq.cafile,
    )

    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    context.load_cert_chain(
        certfile=settings.rabbit_mq.certfile,
        keyfile=settings.rabbit_mq.keyfile,
        password=settings.rabbit_mq.cert_password,
    )

    return context
