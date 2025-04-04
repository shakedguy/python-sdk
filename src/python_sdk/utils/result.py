from typing import Any, Callable, Generic, Iterator, TypeVar, Union

TValue = TypeVar("TValue")
TReturn = TypeVar("TReturn")


class Result(Generic[TValue]):
    def __init__(self, value: Union[TValue, Exception]):
        self._is_error = isinstance(value, Exception)
        self.value = None if self._is_error else value
        self.error = value if self._is_error else None

    @staticmethod
    def ok(value: TValue) -> "Result[TValue]":
        if isinstance(value, Exception):
            raise ValueError("Result.ok called with an error value")
        return Result(value)

    @staticmethod
    def error(error: Union[str, Exception]) -> "Result[TValue]":
        if not isinstance(error, (str, Exception)):
            raise ValueError("Result.error called without an error value")
        error = error if isinstance(error, Exception) else Exception(error)
        return Result(error)

    @property
    def is_error(self) -> bool:
        return self._is_error

    @property
    def is_ok(self) -> bool:
        return not self._is_error

    def __repr__(self) -> str:
        return f"Result({self.value!r}, is_error={self.is_error}, error={self.error!r})"

    def __str__(self) -> str:
        return f"Result({self.value!r}, is_error={self.is_error}, error={self.error!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Result):
            return (
                self.value == other.value
                and self.is_error == other.is_error
                and self.error == other.error
            )

        val = self.unwrap()
        if type(other) is not type(val):
            return False
        try:
            return val == other
        except Exception:  # noqa
            return False

    def unwrap(self) -> Union[TValue, Exception]:
        return self.error if self.is_error else self.value

    def __hash__(self) -> int:
        return hash((self.value, self.is_error, self.error))

    def __bool__(self) -> bool:
        return not self.is_error

    def unwrap_or(self, default: TValue) -> TValue:
        if self.is_error:
            return default
        return self.value

    def unwrap_or_else(self, default: Callable[[], TValue]) -> TValue:
        if self.is_error:
            return default()
        return self.value

    def map(self, func: Callable[[TValue], Any]) -> "Result[Any]":
        if self.is_error:
            return Result(self.error)
        return Result(func(self.value))

    def match(
        self, ok: Callable[[TValue], Any], error: Callable[[Exception], Any]
    ) -> Any:
        return error(self.error) if self._is_error else ok(self.value)

    def map_error(self, func: Callable[[Exception], Exception]) -> "Result[TValue]":
        if not self.is_error:
            return Result(self.value)
        return Result(func(self.error))

    def and_then(self, func: Callable[[TValue], "Result[Any]"]) -> "Result[Any]":
        if self.is_error:
            return Result(self.error)
        return func(self.value)

    def or_else(
        self, func: Callable[[Exception], "Result[TValue]"]
    ) -> "Result[TValue]":
        if not self.is_error:
            return Result(self.value)
        return func(self.error)

    def if_ok(self, func: Callable[[TValue], TReturn]) -> Union[TReturn, None]:
        if self.is_error:
            return None
        return func(self.value)

    def if_error(self, func: Callable[[Exception], TReturn]) -> Union[TReturn, None]:
        if not self.is_error:
            return None
        return func(self.error)

    def __iter__(self) -> Iterator[TValue]:
        if self.is_error:
            raise self.error
        yield self.value
