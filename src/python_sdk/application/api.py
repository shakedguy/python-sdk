from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Optional, Union, cast

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from faststream.broker.fastapi import StreamRouter
from loguru import logger
from socketio import ASGIApp as SocketIOASGIApp
from socketio import AsyncServer as SocketIOAsyncServer
from starlette.types import Lifespan

from .. import settings
from ..conf.logger import configure_logger
from ..infrastructure import cleanup_async, init_async
from ..infrastructure.messaging import Broker
from ..utils.decorators.async_decorators import to_async
from .socketio import create_socketio_app
from .websocket import ConnectionManager, create_connection_manager

LifeCycleFunction = Callable[[FastAPI], Union[Any, Awaitable[Any]]]


class API(FastAPI):
    def __init__(
            self,
            *,
            name: str,
            description: Optional[str] = None,
            version: Optional[str] = None,
            lifespan: Optional[Lifespan] = None,
            before_start: Optional[
                Union[LifeCycleFunction, list[LifeCycleFunction]]
            ] = None,
            before_finish: Optional[
                Union[LifeCycleFunction, list[LifeCycleFunction]]
            ] = None,
            debug: bool = False,
            openapi_url: Optional[str] = "/openapi.json",
            docs_url: Optional[str] = "/docs",
            init_postgres: bool = False,
            init_cache: bool = False,
            init_mongo: bool = False,
            init_messaging: bool = False,
            init_qdrant: bool = False,
            add_websocket: bool = False,
    ) -> None:
        self.debug = debug
        self.sio: Optional[SocketIOAsyncServer] = None
        self.sio_app: Optional[SocketIOASGIApp] = None
        self.websocket_manager: Optional[ConnectionManager] = (
            create_connection_manager() if add_websocket else None
        )
        self._broker_router: Optional[StreamRouter] = None
        self.broker: Optional[Broker] = None
        self._init_postgres = init_postgres
        self._init_cache = init_cache
        self._init_mongo = init_mongo
        self._init_messaging = init_messaging
        self._init_qdrant = init_qdrant
        if init_messaging:
            self._broker_router = Broker.create_router(
                settings.broker.url, tls=settings.broker.use_ssl
            )
            self.broker = Broker(settings.broker.url, tls=settings.broker.use_ssl)
        self._lifespan = lifespan
        self._before_start = before_start
        self._before_finish = before_finish


    @asynccontextmanager
    async def lifespan(self):
        nonlocal before_start, before_finish
        try:
            await init_async(
                init_postgres=self._init_postgres,
                init_cache=self._init_cache,
                init_mongo=self._init_mongo,
                init_messaging=self._init_messaging,
                init_qdrant=self._init_qdrant,
            )
            if self._before_start:
                self._before_start = (
                    [to_async(f)(self) for f in self._before_start]
                    if isinstance(self._before_start, list)
                    else [to_async(self._before_start)(self)]
                )
                await asyncio.gather(*before_start)

            yield {"ws": self.websocket_manager, "sio": self.sio_app}
        finally:
            logger.info("Application shutdown")
            if self.websocket_manager is not None:
                await self.websocket_manager.close()
            if self.sio is not None:
                await self.sio.shutdown()
            await cleanup_async()
            if self._before_finish:
                self._before_finish = (
                    [to_async(f)(self) for f in self._before_finish]
                    if isinstance(self._before_finish, list)
                    else [to_async(self._before_finish)(self)]
                )
                await asyncio.gather(*self._before_finish)

        super().__init__(
            title=name,
            description=description,
            version=version,
            debug=debug,
            openapi_url=openapi_url,
            docs_url=docs_url,
            lifespan=lifespan or self.lifespan,
        )
        self.add_exception_handler(HTTPException, http_exception_handler)
        self.add_middleware(
            CORSMiddleware,  # type: ignore
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        if self._broker_router is not None:
            self.include_router(self._broker_router)

    @classmethod
    def run(
            cls,
            app_path: str,
            *,
            host: str = "0.0.0.0",
            port: int = 8000,
            reload: bool = False,
            workers: int = 1,
            log_level: Union[str, int] = "INFO",
    ) -> None:
        configure_logger()

        logger.info(
            f"starting API at {host}:{port} with reload={reload} and workers={workers}"
        )

        uvicorn.run(
            app_path,
            host=host,
            port=port,
            reload=reload,
            log_level=log_level.upper() if isinstance(log_level, str) else log_level,
            workers=workers,
            use_colors=True,
        )

    def add_socketio(
            self,
            *,
            socketio_path: str = "/socket.io",
            socketio_on_connect: Optional[
                Callable[[str, dict, dict], Union[Any, Awaitable[Any]]]
            ] = None,  # noqa
            socketio_on_disconnect: Optional[
                Callable[[str], Union[Any, Awaitable[Any]]]
            ] = None,
    ) -> None:
        self.sio, self.sio_app = create_socketio_app(
            enable_logging=self.debug,
            socketio_path=socketio_path,
            on_connect=socketio_on_connect,
            on_disconnect=socketio_on_disconnect,
        )
        self.mount("/", self.sio_app)


def http_exception_handler(request: Request, exc: Exception) -> Response:
    """
    Custom exception handler for HTTP exceptions.
    """

    exc = cast(HTTPException, exc)

    logger.error(
        f"HTTPException: {exc.detail}, status_code: {exc.status_code}, headers: {exc.headers}, request details: {request}"
    )
    return Response(
        content=exc.detail,
        status_code=exc.status_code,
        headers=exc.headers,
        media_type="application/json",
    )
