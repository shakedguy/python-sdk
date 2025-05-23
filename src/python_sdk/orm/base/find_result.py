from collections.abc import AsyncIterator, Iterator
from typing import (
    Callable,
    Generic,
    Type,
    TypeVar,
)

from ...domain.base.base_model import BaseModel

T = TypeVar("T", bound=BaseModel)


class FindAsyncResult(Generic[T]):
    def __init__(self, generator_func: Callable[[], AsyncIterator[Type[T]]]):
        self._generator_func = generator_func

    def __aiter__(self) -> AsyncIterator[Type[T]]:
        return self._generator_func()

    async def to_list(self) -> list[Type[T]]:
        return [item async for item in self._generator_func()]


class FindResult(Generic[T]):
    def __init__(self, generator_func: Callable[[], Iterator[Type[T]]]):
        self._generator_func = generator_func

    def __iter__(self) -> Iterator[Type[T]]:
        return self._generator_func()

    def to_list(self) -> list[Type[T]]:
        return [item for item in self._generator_func()]
