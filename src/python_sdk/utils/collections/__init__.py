from collections.abc import Collection
from typing import Iterable, TypeVar, Union, overload

T = TypeVar("T")


@overload
def flatten(array: Iterable[Iterable[T]]) -> list[T]: ...


@overload
def flatten(array: Iterable[T]) -> list[T]: ...


def flatten(array: Union[Iterable[T], Iterable[Iterable[T]]]) -> list[T]:
    """
    Flattens array a single level deep.

    Args:
        array: List to flatten.

    Returns:
        Flattened list.

    Example:

        >>> flatten([[1], [2, [3]], [[4]]])
        [1, 2, [3], [4]]

    """
    return flatten_depth(array, depth=1)


def flatten_deep(array: Iterable[Iterable[T]]) -> list[T]:
    """
    Flattens an array recursively.

    Args:
        array: List to flatten.

    Returns:
        Flattened list.

    Example:

        >>> flatten_deep([[1], [2, [3]], [[4]]])
        [1, 2, 3, 4]

    """
    return flatten_depth(array, depth=-1)


def flatten_depth(array: Iterable[Iterable[T]], depth: int = 1) -> list[T]:
    """
    Recursively flatten `array` up to `depth` times.

    Args:
        array: List to flatten.
        depth: Depth to flatten to. Defaults to ``1``.

    Returns:
        Flattened list.

    Example:

        >>> flatten_depth([[[1], [2, [3]], [[4]]]], 1)
        [[1], [2, [3]], [[4]]]
        >>> flatten_depth([[[1], [2, [3]], [[4]]]], 2)
        [1, 2, [3], [4]]
        >>> flatten_depth([[[1], [2, [3]], [[4]]]], 3)
        [1, 2, 3, 4]
        >>> flatten_depth([[[1], [2, [3]], [[4]]]], 4)
        [1, 2, 3, 4]

    """
    return list(iterflatten(array, depth=depth))


def iterflatten(array: Iterable[Iterable[T]], depth: int = -1) -> Iterable[T]:
    """Iteratively flatten a list shallowly or deeply."""
    for item in array:
        if isinstance(item, (list, tuple)) and depth != 0:
            for subitem in iterflatten(item, depth - 1):
                yield subitem
        else:
            yield item


def is_iterable_except_str_like(obj: object) -> bool:
    """
    Check if an object is iterable, excluding string-like objects.

    Args:
        obj: Object to check.

    Returns:
        True if the object is iterable, False otherwise.
    """
    return isinstance(
        obj, (Iterable, Collection, dict, set, frozenset, tuple, list)
    ) and not isinstance(obj, (str, bytes, bytearray, memoryview))
