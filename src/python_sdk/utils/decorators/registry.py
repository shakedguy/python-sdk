from functools import wraps
from typing import Any, Callable


class DecoratorRegistry:
    """Registry to keep track of decorated functions"""

    __slots__ = ("_func", "_args", "_kwargs")

    _decorated_functions: dict[str, set[Callable]] = {}

    @classmethod
    def register(cls, decorator: Callable) -> Callable:
        """
        Creates a registering decorator that tracks decorated functions.

        Args:
            decorator: The original decorator function

        Returns:
            Callable: A wrapped decorator that registers functions
        """

        decorator_name = decorator.__name__
        if decorator_name not in cls._decorated_functions:
            cls._decorated_functions[decorator_name] = set()

        @wraps(decorator)
        def wrapper(*args: Any, **kwargs: Any) -> Callable:
            if len(args) == 1 and not kwargs and callable(args[0]):
                func = args[0]
                cls._decorated_functions[decorator_name].add(func)
                return decorator(func)

            def inner_wrapper(inner_func: Callable) -> Callable:
                cls._decorated_functions[decorator_name].add(inner_func)
                return decorator(*args, **kwargs)(inner_func)

            return inner_wrapper

        return wrapper

    @classmethod
    def get_decorated_functions(cls, decorator: Callable) -> list[Callable]:
        """
        Get all functions decorated by a specific decorator.

        Args:
            decorator: The decorator to look up

        Returns:
            List[Callable]: List of functions decorated by the specified decorator
        """
        return list(cls._decorated_functions.get(decorator.__name__, set()))
