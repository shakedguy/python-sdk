import asyncio
from typing import Awaitable, Callable, TypeVar, Union

from typing_extensions import ParamSpec, TypeIs

_R = TypeVar('_R', covariant=True)
_P = ParamSpec('_P')
_S = TypeVar('_S')


def is_coroutine(
        func: Union[Callable[_P, Awaitable[_R]], Callable[_P, _R]],
) -> TypeIs[Callable[_P, Awaitable[_R]]]:
    return asyncio.iscoroutinefunction(func)
