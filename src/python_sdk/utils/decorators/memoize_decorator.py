from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .registry import DecoratorRegistry

T = TypeVar("T")


@DecoratorRegistry.register
def memoize(func: Callable[..., T]) -> Callable[..., T]:
    memo: dict[str, T] = {}

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        key = str(args)

        for k, v in kwargs.items():
            key += f"{k}={v}"

        if key not in memo:
            memo[key] = func(*args, **kwargs)

        return memo[key]

    return wrapper
