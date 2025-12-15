import enum
from typing import Any, AnyStr, Optional, Self, Union

from ..utils.strings import to_snake_case, to_str
from ._lazy import Promise


class StrEnum(enum.StrEnum):
    @classmethod
    def _missing_(cls, value: AnyStr) -> Optional[Self]:
        key = to_snake_case(text=to_str(text=value).lower())

        for member in cls:
            if to_snake_case(text=member) == key:
                return member
        return None


class IntEnum(enum.IntEnum):
    @classmethod
    def _missing_(cls, value: Union[AnyStr, int]) -> Optional[Self]:
        if not isinstance(value, (str, int)):
            return None

        if isinstance(value, int):
            return value if value in [member for member in cls] else None

        key = to_snake_case(text=to_str(text=value))

        for member in cls:
            if to_snake_case(text=member.name) == key:
                return member
        return None


class ChoicesType(enum.EnumType):
    """A metaclass for creating a enum choices."""

    def __new__(
        metacls,
        classname: str,
        bases: tuple[Any],
        classdict: enum.EnumDict,
        **kwargs: any,
    ) -> enum.Enum:
        labels = []
        for key in classdict._member_names:  # noqa
            value = classdict[key]
            if (
                isinstance(value, (list, tuple))
                and len(value) > 1
                and isinstance(value[-1], (Promise, str))
            ):
                *value, label = value
                value = tuple(value)
            else:
                label = value
                # label = key.replace("_", " ").title()
            labels.append(label)
            # Use dict.__setitem__() to suppress defenses against double
            # assignment in enum's classdict.
            dict.__setitem__(classdict, key, value)
        cls = super().__new__(
            metacls=metacls, cls=classname, bases=bases, classdict=classdict, **kwargs
        )
        for member, label in zip(cls.__members__.values(), labels, strict=False):
            member._label_ = label
        return enum.unique(cls)  # type: ignore

    @property
    def names(cls) -> list[str]:
        empty = ["__empty__"] if hasattr(cls, "__empty__") else []
        return empty + [member.name for member in cls]

    @property
    def choices(cls) -> list[tuple[Any, str]]:
        empty = [(None, cls.__empty__)] if hasattr(cls, "__empty__") else []
        return empty + [(member.value, member.label) for member in cls]

    @property
    def labels(cls) -> list[str]:
        return [label for _, label in cls.choices]

    @property
    def values(cls) -> list[Any]:
        return [value for value, _ in cls.choices]


class Choices(enum.Enum, metaclass=ChoicesType):
    """Class for creating enumerated choices."""

    do_not_call_in_templates = enum.nonmember(True)

    @enum.property
    def label(self) -> str:
        return self._label_

    # A similar format was proposed for Python 3.10.
    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}.{self._name_}"


class IntegerChoices(Choices, IntEnum):
    """Class for creating enumerated integer choices."""

    @classmethod
    def _missing_(cls, value: Union[AnyStr, int]) -> Optional[Self]:
        if not isinstance(value, (str, int)):
            return None

        if isinstance(value, int):
            return value if value in [member for member in cls] else None

        key = to_snake_case(text=to_str(text=value).lower())

        for member in cls:
            if to_snake_case(text=member.name) == key:
                return member
        return None


class TextChoices(Choices, StrEnum):
    """Class for creating enumerated string choices."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def _missing_(cls, value: AnyStr) -> Optional[Self]:
        key = to_snake_case(text=to_str(text=value).lower())

        for member in cls:
            if to_snake_case(text=member) == key:
                return member
        return None

    def __eq__(self, other) -> bool:
        if isinstance(other, enum.Enum):
            return super().__eq__(other)

        return (
            self.value == str(other)
            or self.label == str(other)
            or self.name == str(other)
        )

    def __str__(self) -> str:
        return str(self.label)

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}.{self._name_}"

    def __hash__(self) -> int:
        return hash(self.value)
