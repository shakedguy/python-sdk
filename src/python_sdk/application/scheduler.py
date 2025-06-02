from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Union

from faststream import FastStream
from faststream.types import SendableMessage
from taskiq import AsyncTaskiqDecoratedTask
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_faststream import AppWrapper, BrokerWrapper, StreamScheduler
from taskiq_faststream.types import ScheduledTask

from ..infrastructure.messaging import (
    Broker,
)


class Scheduler(object):
    def __init__(
        self,
        *,
        app: Optional[FastStream] = None,
        broker: Optional[Broker] = None,
    ) -> None:
        if not any([app, broker]):
            raise ValueError("Either app or broker must be provided.")

        self.wrapper: Union[AppWrapper, BrokerWrapper] = (
            AppWrapper(app) if app else BrokerWrapper(broker)
        )

        self._scheduler = StreamScheduler(
            broker=self.wrapper,
            sources=[LabelScheduleSource(self.wrapper)],
        )

    def task(
        self,
        message: Optional[
            Union[
                SendableMessage,
                Callable[..., SendableMessage],
                Callable[..., Awaitable[SendableMessage]],
            ]
        ] = None,
        *,
        cron: Optional[str] = None,
        time: Optional[datetime] = None,
        **kwargs: Any,
    ) -> AsyncTaskiqDecoratedTask[[], None]:
        if not any([cron, time]):
            raise ValueError("Either cron or time must be provided.")

        return self.wrapper.task(
            message=message,
            schedule=[ScheduledTask(cron=cron, time=time)],
            **kwargs,
        )
