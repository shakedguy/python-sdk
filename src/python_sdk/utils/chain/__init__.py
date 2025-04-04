from typing import Any, Generic, TypeVar, Union

from .all_funcs import AllFuncs

ValueT_co = TypeVar("ValueT_co", covariant=True)
T = TypeVar("T")
T2 = TypeVar("T2")


class InvalidMethod(AttributeError):
    pass


class UnsetValue: ...


UNSET = UnsetValue()


class Chain(AllFuncs, Generic[ValueT_co]):
    """Enables chaining of :attr:`module` functions."""

    invalid_method_exception = InvalidMethod

    def __init__(self, value: Union[ValueT_co, UnsetValue] = UNSET) -> None:
        self._value = value

    def _wrap(self, func) -> "ChainWrapper[Union[ValueT_co, UnsetValue]]":
        """Implement `AllFuncs` interface."""
        return ChainWrapper(self._value, func)

    def value(self) -> ValueT_co:
        """
        Return current value of the chain operations.

        Returns:
            Current value of chain operations.
        """
        return self(self._value)

    def to_string(self) -> str:
        """
        Return current value as string.

        Returns:
            Current value of chain operations casted to ``str``.
        """
        return self.module.to_string(self.value())

    def commit(self) -> "Chain[ValueT_co]":
        """
        Executes the chained sequence and returns the wrapped result.

        Returns:
            New instance of :class:`Chain` with resolved value from
                previous :class:`Class`.
        """
        return Chain(self.value())

    def plant(self, value: Any) -> "Chain[ValueT_co]":
        """
        Return a clone of the chained sequence planting `value` as the wrapped value.

        Args:
            value: Value to plant as the initial chain value.
        """
        # pylint: disable=no-member,maybe-no-member
        wrapper = self._value
        wrappers = []

        if hasattr(wrapper, "_value"):
            wrappers = [wrapper]

            while isinstance(wrapper._value, ChainWrapper):  # noqa
                wrapper = wrapper._value  # noqa
                wrappers.insert(0, wrapper)

        clone: Chain[Any] = Chain(value)

        for wrap in wrappers:
            clone = ChainWrapper(clone._value, wrap.method)(  # type: ignore
                *wrap.args,  # type: ignore
                **wrap.kwargs,  # type: ignore
            )

        return clone

    def __call__(self, value) -> ValueT_co:
        """
        Return result of passing `value` through chained methods.

        Args:
            value: Initial value to pass through chained methods.

        Returns:
            Result of method chain evaluation of `value`.
        """
        if isinstance(self._value, ChainWrapper):
            # pylint: disable=maybe-no-member
            value = self._value.unwrap(value)
        return value


class ChainWrapper(Generic[ValueT_co]):
    """Wrap :class:`Chain` method call within a :class:`ChainWrapper` context."""

    def __init__(self, value: ValueT_co, method) -> None:
        self._value = value
        self.method = method
        self.args = ()
        self.kwargs: dict[Any, Any] = {}

    def _generate(self):
        """Generate a copy of this instance."""
        # pylint: disable=attribute-defined-outside-init
        new = self.__class__.__new__(self.__class__)
        new.__dict__ = self.__dict__.copy()
        return new

    def unwrap(self, value=UNSET):
        """
        Execute :meth:`method` with :attr:`_value`, :attr:`args`, and :attr:`kwargs`.

        If :attr:`_value` is an instance of :class:`ChainWrapper`, then unwrap it before calling
        :attr:`method`.
        """
        # Generate a copy of ourself so that we don't modify the chain wrapper
        # _value directly. This way if we are late passing a value, we don't
        # "freeze" the chain wrapper value when a value is first passed.
        # Otherwise, we'd locked the chain wrapper value permanently and not be
        # able to reuse it.
        wrapper = self._generate()

        if isinstance(wrapper._value, ChainWrapper):
            # pylint: disable=no-member,maybe-no-member
            wrapper._value = wrapper._value.unwrap(value)
        elif not isinstance(value, ChainWrapper) and value is not UNSET:
            # Override wrapper's initial value.
            wrapper._value = value

        if wrapper._value is not UNSET:
            value = wrapper._value

        return wrapper.method(value, *wrapper.args, **wrapper.kwargs)

    def __call__(self, *args, **kwargs):
        """
        Invoke the :attr:`method` with :attr:`value` as the first argument and return a new
        :class:`Chain` object with the return value.

        Returns:
            New instance of :class:`Chain` with the results of :attr:`method` passed in as
                value.
        """
        self.args = args
        self.kwargs = kwargs
        return Chain(self)
