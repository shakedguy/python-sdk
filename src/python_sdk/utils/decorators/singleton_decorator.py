from threading import Lock
from typing import Any, Optional, Type, TypeVar

from .registry import DecoratorRegistry

T = TypeVar("T")


@DecoratorRegistry.register
def singleton(cls: Type[T]) -> Type[T]:
    instances: dict[Type, T] = {}
    lock = Lock()

    class SingletonWrapper(cls):  # type: ignore
        def __new__(cls, *args: Optional[tuple[Any]], **kwargs: Optional[Any]) -> T:  # type: ignore
            nonlocal instances
            with lock:
                if cls not in instances:
                    instances[cls] = super(SingletonWrapper, cls).__new__(
                        cls, *args, **kwargs
                    )

            return instances[cls]

    return SingletonWrapper
