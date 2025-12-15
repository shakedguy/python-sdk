from typing import Any, Awaitable, Callable, Optional, Union

from loguru import logger
from socketio import ASGIApp, AsyncServer

from ..conf import settings
from ..utils.decorators import memoize, to_async


@memoize
def create_socketio_app(
    *,
    enable_logging: Optional[bool] = False,
    socketio_path: str = "/socket.io",
    on_connect: Optional[
        Callable[[str, dict, dict], Union[Any, Awaitable[Any]]]
    ] = None,  # noqa
    on_disconnect: Optional[Callable[[str], Union[Any, Awaitable[Any]]]] = None,  # noqa
) -> tuple[AsyncServer, ASGIApp]:
    """
    Create a SocketIO ASGI application.
    """

    enable_logging = enable_logging if enable_logging is not None else settings.debug
    server = AsyncServer(
        cors_allowed_origins="*",
        async_mode="asgi",
        logger=enable_logging,
        engineio_logger=enable_logging,
    )

    async def connect(
        sid: str,
        environ: Any,
        auth: Optional[Any] = None,
        *args,  # noqa
        **kwargs,  # noqa
    ) -> bool:
        nonlocal on_connect

        logger.debug(f"Client Connected: {sid}")
        if on_connect is not None:
            await to_async(on_connect)(sid, environ, auth)
        return True

    async def disconnect(sid: str, *args, **kwargs):  # noqa
        nonlocal on_disconnect

        logger.debug(f"Client Disconnected: {sid}")

        if on_disconnect is not None:
            await to_async(on_disconnect)(sid)

        return True

    app = ASGIApp(
        socketio_server=server,
        socketio_path=socketio_path,
    )

    server.on("connect", connect)
    server.on("disconnect", disconnect)

    return server, app
