from typing import Any, Callable, Optional, Self

from faststream import FastStream
from loguru import logger
from taskiq.abc.result_backend import AsyncResultBackend
from taskiq.cli.scheduler.args import SchedulerArgs
from taskiq.cli.scheduler.run import run_scheduler

from ..conf import settings
from ..domain.api import APIHealthResponse
from ..infrastructure import cleanup_async, init_async
from ..infrastructure.messaging import (
    HEALTH_CHECK_QUEUE_NAME,
    Broker,
    BrokerUrl,
    health_check_exchange,
)
from ..utils import Crypto, Strings
from .scheduler import Scheduler


class Microservice(object):
    def __init__(
        self,
        broker_url: BrokerUrl,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        on_start: Optional[Callable[[Self], Any]] = None,
        after_start: Optional[Callable[[Self], Any]] = None,
        on_shutdown: Optional[Callable[[Self], Any]] = None,
        after_shutdown: Optional[Callable[[Self], Any]] = None,
        init_postgres: bool = False,
        init_cache: bool = False,
        init_mongo: bool = False,
        max_consumers: int = 5,
        tls: bool = False,
    ):
        pod_name = settings.kube.pod_name or Crypto.generate_random_id(
            8, encoding="hex", case="upper"
        )
        self.name: str = f"{Strings.slugify(name or 'python-microservice')}:{pod_name}"
        self.description: str = description or self.name
        self.version: str = version or "0.1.0"
        self.broker = Broker(
            broker_url, connection_name=self.name, max_consumers=max_consumers, tls=tls
        )
        self.results_backend: Optional[AsyncResultBackend] = None
        self.init_postgres: bool = init_postgres
        self.init_cache: bool = init_cache
        self.init_mongo: bool = init_mongo

        async def _on_startup() -> None:
            """
            Called when the application starts.
            """
            logger.debug("starting microservice")
            try:
                await init_async(
                    init_postgres=init_postgres,
                    init_cache=init_cache,
                    init_mongo=init_mongo,
                )
                logger.debug("microservice started successfully")
            except Exception as e:
                logger.error(f"Failed to initialize: {e}")
                raise e

        async def _on_shutdown() -> None:
            """
            Called when the application shuts down.
            """

            logger.debug("shutting down microservice")
            try:
                await cleanup_async()
            except Exception as e:
                logger.error(f"Failed to cleanup: {e}")
                raise e
            finally:
                logger.info("microservice shutdown")

        @self.broker.subscribe(
            to=HEALTH_CHECK_QUEUE_NAME,
            exchange=health_check_exchange,
        )
        def _on_health_check(*args, **kwargs) -> APIHealthResponse:
            logger.debug("Received health check message")
            return APIHealthResponse()

        self._app = FastStream(
            self.broker._broker,  # noqa
            title=self.name,
            description=self.description,
            version=self.version,
            identifier=self.name,
            on_startup=[_on_startup, on_start] if on_start else [_on_startup],
            after_startup=[after_start] if after_start else [],
            on_shutdown=[_on_shutdown, on_shutdown] if on_shutdown else [_on_shutdown],
            after_shutdown=[after_shutdown] if after_shutdown else [],
        )  # noqa
        self.scheduler = Scheduler(app=self._app)

    async def run(self) -> None:
        try:
            await run_scheduler(
                args=SchedulerArgs(
                    scheduler=self.scheduler._scheduler,  # noqa
                    skip_first_run=False,
                    modules=["src"],
                )
            )
        except Exception as e:
            logger.error(f"Failed to run scheduler: {e}")
            raise e
