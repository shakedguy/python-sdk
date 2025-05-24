import json
from collections import UserDict
from collections.abc import ItemsView, KeysView, ValuesView
from inspect import ismethod
from typing import Any, Iterator, Self


class DictMixin(UserDict):
    """Mixin for dict operations."""

    def __getitem__(self, item: str) -> Any:
        """Get item from dict.

        Args:
            item (Any): key to get item from dict

        Returns:
            Any: item from dict
        """
        return getattr(self, item)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item in dict.

        Args:
            key (str): key to set item in dict
            value (Any): value to set in dict
        """
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        """Delete item from dict.

        Args:
            key (str): key to delete from dict
        """
        delattr(self, key)

    def __contains__(self, key: object) -> bool:
        """Check if dict has key.

        Args:
            key (str): key to check in dict

        Returns:
            bool: True if key in dict, False otherwise
        """
        return key in vars(self)

    def __iter__(self) -> Iterator[str]:
        """Get iterator for dict.

        Returns:
            Any: iterator for dict
        """
        for key in self.keys():
            yield key

    def __len__(self) -> int:
        """Get length of dict.

        Returns:
            int: length of dict
        """
        return len(vars(self))

    #
    def __eq__(self, other: Any) -> bool:
        """Check if dict is equal to other dict.

        Args:
            other (Any): other dict to check equality with

        Returns:
            bool: True if dict is equal to other dict, False otherwise
        """
        return True if vars(self) == vars(other) else False

    def __dir__(self) -> dict[str, Any]:
        """Get list of keys in dict.

        Returns:
            List[str]: list of keys in dict
        """
        res = {}
        for key, value in vars(self).items():
            if not ismethod(value):
                res[key] = value
        return res

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from dict.

        Args:
            key (str): key to get value from dict
            default (Any, optional): default value if key not found. Defaults to None.

        Returns:
            Any: value from dict or default value
        """
        return self[key] if key in self else default

    def set(self, key: str, value: Any) -> None:
        """Set value in dict.

        Args:
            key (str): key to set value in dict
            value (Any): value to set in dict
        """
        setattr(self, key, value)

    def setdefault(self, key, default=None, /):
        if key in self:
            return self[key]
        self.set(key, default)
        return default

    def has(self, key: str) -> bool:
        """Check if dict has key.

        Args:
            key (str): key to check in dict

        Returns:
            bool: True if key in dict, False otherwise
        """
        return hasattr(self, key)

    def keys(self) -> KeysView:
        """Get list of keys in dict.

        Returns:
            KeysView: list of keys in dict
        """
        res = vars(self)
        res.pop("data", None)
        return res.keys()

    def values(self) -> ValuesView:
        """Get list of values in dict.

        Returns:
            ValuesView: list of values in dict
        """
        res = vars(self)
        res.pop("data", None)
        return res.values()

    def items(self) -> ItemsView:
        """Get list of key-value pairs in dict.

        Returns:
            ItemsView: list of key-value pairs in dict
        """
        res = vars(self)
        res.pop("data", None)
        return res.items()

    # def update(self, **kwargs: Mapping[str, Any]) -> None:  # type: ignore
    #     for key, value in kwargs.items():
    #         setattr(self, key, value)
    #
    #     for key, value in kwargs.items():
    #         setattr(self, key, value)

    def clear(self) -> None:
        """Clear dict."""
        for key in vars(self):
            setattr(self, key, None)

    def copy(self) -> Self:
        """Get copy of dict.

        Returns:
            Dict[str, Any]: copy of dict
        """
        return self.__class__(**vars(self))

    def __repr__(self) -> str:
        """Get string representation"""

        return json.dumps(
            {
                key: value.model_dump() if hasattr(value, "model_dump") else value
                for key, value in vars(self).items()
                if key != "data"
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )
