from collections.abc import Callable
from functools import wraps
from typing import Any, Optional

from .registry import DecoratorRegistry


@DecoratorRegistry.register
def task(name: Optional[str] = None) -> Callable:
    def decorator(func: Callable) -> Callable[[Callable], Callable]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal name

            name = name or func.__name__
            return func(*args, **kwargs)

        return wrapper

    return decorator
