from abc import ABC, abstractmethod
from typing import Any, Callable, Type


class AllFuncs(ABC):
    """Exposing all of the exposed functions of a module through an class."""

    module: Any
    invalid_method_exception: Type[Exception]

    @abstractmethod
    def _wrap(self, func) -> Callable:
        """Proxy attribute access to :attr:`module`."""
        raise NotImplementedError()  # pragma: no cover

    @classmethod
    def get_method(cls, name: str) -> Callable:
        """
        Return valid :attr:`module` method.

        Args:
            name: Name of pydash method to get.

        Returns:
            :attr:`module` callable.

        Raises:
            InvalidMethod: Raised if `name` is not a valid :attr:`module` method.
        """
        method = getattr(cls.module, name, None)

        if not callable(method) and not name.endswith("_"):
            # Alias method names not ending in underscore to their underscore
            # counterpart. This allows chaining of functions like "map_()"
            # using "map()" instead.
            method = getattr(cls.module, name + "_", None)

        if not callable(method):
            raise cls.invalid_method_exception(
                f"Invalid {cls.module.__name__} method: {name}"
            )

        return method

    def __getattr__(self, name: str) -> Callable:
        return self._wrap(self.get_method(name))
