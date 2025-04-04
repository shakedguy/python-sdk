import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, Awaitable, TypeVar, Union

from ..result import Result
from .registry import DecoratorRegistry

T = TypeVar("T")


@DecoratorRegistry.register
def safe(
    func: Callable[..., Union[T, Awaitable[T]]],
) -> Callable[..., Union[Result[T], Awaitable[Result[T]]]]:
    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Result[T]:
        try:
            res = func(*args, **kwargs)
            return res if isinstance(res, Result) else Result(res)
        except Exception as e:
            return Result.error(e)

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Result[T]:
        try:
            res = await func(*args, **kwargs)
            return res if isinstance(res, Result) else Result(res)
        except Exception as e:
            return Result.error(e)

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
