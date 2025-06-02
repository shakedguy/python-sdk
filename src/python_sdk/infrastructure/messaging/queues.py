from typing import Literal, Optional, Union

from faststream.rabbit import ExchangeType, QueueType, RabbitExchange, RabbitQueue
from faststream.rabbit.schemas.queue import ClassicQueueArgs

BACKGROUND_WORKER_QUEUE_NAME = "background-worker"
HEALTH_CHECK_QUEUE_NAME = "health-check"
DEAD_LETTER_QUEUE_NAME = "dead-letter"

queue_args: ClassicQueueArgs = {
    "x-message-ttl": 60000,  # 1 minute
    "x-dead-letter-exchange": DEAD_LETTER_QUEUE_NAME,
    "x-dead-letter-routing-key": DEAD_LETTER_QUEUE_NAME,
}


background_worker_queue = RabbitQueue(
    name=BACKGROUND_WORKER_QUEUE_NAME,
    durable=True,
    exclusive=False,
    auto_delete=False,
    arguments=queue_args,
)


health_check_exchange = RabbitExchange(
    name=HEALTH_CHECK_QUEUE_NAME,
    type=ExchangeType.FANOUT,
    durable=True,
    auto_delete=False,
)

dead_letter_exchange = RabbitExchange(
    name=DEAD_LETTER_QUEUE_NAME,
    type=ExchangeType.FANOUT,
    durable=True,
    auto_delete=False,
)
dead_letter_queue = RabbitQueue(
    name=DEAD_LETTER_QUEUE_NAME,
    durable=True,
    exclusive=False,
    auto_delete=False,
    queue_type=QueueType.QUORUM,
)


def create_rabbit_queue(
    name: str,
    *,
    durable: bool = True,
    exclusive: bool = False,
    auto_delete: bool = False,
    message_ttl_seconds: Optional[Union[int, float]] = None,
    bind_to_dead_letter: bool = False,
    queue_max_length: Optional[int] = None,
    queue_type: Literal["classic", "quorum", "stream"] = "quorum",
) -> RabbitQueue:
    """
    Create a RabbitMQ queue with the specified parameters.
    """
    arguments = ClassicQueueArgs()

    if message_ttl_seconds is not None:
        arguments["x-message-ttl"] = int(
            message_ttl_seconds * 1000
        )  # Convert seconds to milliseconds
    if bind_to_dead_letter:
        arguments["x-dead-letter-exchange"] = DEAD_LETTER_QUEUE_NAME
        arguments["x-dead-letter-routing-key"] = DEAD_LETTER_QUEUE_NAME
    if queue_max_length is not None:
        arguments["x-max-length"] = queue_max_length

    return RabbitQueue(
        name=name,
        durable=durable,
        exclusive=exclusive,
        auto_delete=auto_delete,
        queue_type=QueueType(queue_type),
        arguments=arguments,
    )
