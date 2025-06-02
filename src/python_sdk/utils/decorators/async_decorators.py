from __future__ import annotations

import asyncio
import functools
import inspect
import threading
from typing import Any, Awaitable, Callable, TypeVar, Union, cast

from anyio.to_thread import run_sync

T = TypeVar("T")

_loop = None
_thread = None


def to_async(
    func: Union[
        Callable[..., T],
        Callable[..., Awaitable[T]],
    ],
) -> Callable[..., Awaitable[T]]:
    """Converts a synchronous function to an asynchronous function."""

    @functools.wraps(func)
    async def to_async_wrapper(*args: Any, **kwargs: Any) -> T:
        """Wraps a function to make it asynchronous."""
        return await _run_async(func, *args, **kwargs)

    return to_async_wrapper


def to_sync(
    func: Union[
        Callable[..., T],
        Callable[..., Awaitable[T]],
    ],
) -> Callable[..., T]:
    """Converts an asynchronous function to a synchronous function."""

    @functools.wraps(func)
    def to_sync_wrapper(*args: Any, **kwargs: Any) -> T:
        if not _is_coroutine_callable(func):
            return cast(Callable[..., T], func)(*args, **kwargs)

        async def _to_sync_wrapper(
            fut_: asyncio.Future, *args: Any, **kwargs: Any
        ) -> T:
            res = await func(*args, **kwargs)
            fut_.set_result(res)
            return res

        loop = _get_default_event_loop()
        fut = loop.create_future()
        loop.create_task(_to_sync_wrapper(fut, *args, **kwargs))

        print("waiting for result")
        return fut.result()

    return to_sync_wrapper


def _get_default_event_loop():
    global _loop, _thread
    if _thread is None:
        if _loop is None:
            try:
                _loop = asyncio.get_event_loop()
            except RuntimeError:
                _loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_loop)
        if not _loop.is_running():
            _thread = threading.Thread(target=_loop.run_forever, daemon=True)
            _thread.start()
    return _loop


async def _run_async(
    func: Union[
        Callable[..., T],
        Callable[..., Awaitable[T]],
    ],
    *args: Any,
    **kwargs: Any,
) -> T:
    return (
        await cast(Callable[..., Awaitable[T]], func)(*args, **kwargs)
        if _is_coroutine_callable(func)
        else await _run_in_threadpool(cast(Callable[..., T], func), *args, **kwargs)
    )


async def _run_in_threadpool(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    if kwargs:
        func = functools.partial(func, **kwargs)
    return await run_sync(func, *args)


def _is_coroutine_callable(call: Callable[..., Any]) -> bool:
    if inspect.isclass(call):
        return False

    if asyncio.iscoroutinefunction(call):
        return True

    dunder_call = getattr(call, "__call__", None)  # noqa: B004
    return asyncio.iscoroutinefunction(dunder_call)
