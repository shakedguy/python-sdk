from typing import Any, Optional, Type


class ClassProperty:  # noqa
    def __init__(self, get_method: classmethod) -> None:
        self.get_method = get_method

    def __get__(self, obj: Optional[Any], owner: Type[Any]) -> Any:
        return self.get_method(owner)
