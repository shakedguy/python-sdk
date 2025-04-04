import copy
from abc import ABC
from typing import Any, Callable, Collection, Type, TypeVar, Union

from pydantic import BaseModel

from . import is_iterable_except_str_like
from .strings import Strings

ValidIterables = Union[dict[str, Any], Collection[Any]]

T = TypeVar("T")


def dict_or_pydantic_model_to_dict(
    data: Union[BaseModel, dict[str, Any]],
) -> dict[str, Any]:
    """
    Convert a Pydantic model or dictionary to a dictionary.

    Args:
        data (BaseModel | dict[str, Any]): The Pydantic model or dictionary to convert.

    Returns:
        dict[str, Any]: The resulting dictionary.
    """

    res = dict()
    if isinstance(data, BaseModel):
        for field_name, field in data.model_fields.items():
            key = field.alias or field_name
            value = getattr(data, key, None)
            res[key] = (
                dict_or_pydantic_model_to_dict(value)
                if isinstance(value, (BaseModel, dict))
                else value
            )
    else:
        for key, value in data.items():
            res[key] = (
                dict_or_pydantic_model_to_dict(value)
                if isinstance(value, (BaseModel, dict))
                else value
            )

    return res


def _return_same_iterable(
    origin: ValidIterables, result: ValidIterables
) -> ValidIterables:
    return (
        set(result)
        if isinstance(origin, set)
        else tuple(result)
        if isinstance(origin, tuple)
        else list(result)
        if isinstance(origin, list)
        else result
    )


def recursive_sort_keys(
    input_value: ValidIterables,
) -> ValidIterables:
    """
    Recursively sort the keys of a dictionary or list of dictionaries.

    Args:
        input_value (dict[str, Any] | Collection[Any]): The input dictionary or list of dictionaries to sort.

    Returns:
        dict[str, Any] | Collection[Any]: The sorted dictionary or list of dictionaries.
    """

    if isinstance(input_value, dict):
        return dict(sorted(dict(input_value).items()))

    if isinstance(input_value, Collection):
        return _return_same_iterable(
            input_value, [recursive_sort_keys(item) for item in input_value]
        )

    return input_value


class ChangeKeysCase(ABC):  # noqa
    """
    A utility class for changing the case of keys in dictionaries.
    """

    @staticmethod
    def to_camel_case(input_obj: ValidIterables, deep: bool = True) -> ValidIterables:
        """
        Convert the keys of the input object to camel case.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input object (str, dict, or list) to convert.
            deep (bool): Whether to apply the conversion deeply. Defaults to True.

        Returns:
            dict[str, Any] | Collection[Any]: The object with keys converted to camel case.
        """
        return ChangeKeysCase._change_case(input_obj, Strings.to_camel_case, deep)

    @staticmethod
    def to_snake_case(input_obj: ValidIterables, deep: bool = True) -> ValidIterables:
        """
        Convert the keys of the input object to snake case.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input object (str, dict, or list) to convert.
            deep (bool): Whether to apply the conversion deeply. Defaults to True.

        Returns:
            dict[str, Any] | Collection[Any]: The object with keys converted to snake case.

        """
        return ChangeKeysCase._change_case(input_obj, Strings.to_snake_case, deep)

    @staticmethod
    def to_kebab_case(input_obj: ValidIterables, deep: bool = True) -> ValidIterables:
        """
        Convert the keys of the input object to kebab case.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input object (str, dict, or list) to convert.
            deep (bool): Whether to apply the conversion deeply. Defaults to True.

        Returns:
            dict[str, Any] | Collection[Any]: The object with keys converted to kebab case.
        """
        return ChangeKeysCase._change_case(input_obj, Strings.to_kebab_case, deep)

    @staticmethod
    def to_pascal_case(input_obj: ValidIterables, deep: bool = True) -> ValidIterables:
        """
        Convert the keys of the input object to pascal case.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input object (str, dict, or list) to convert.
            deep (bool): Whether to apply the conversion deeply. Defaults to True.

        Returns:
            dict[str, Any] | Collection[Any]: The object with keys converted to pascal case.
        """
        return ChangeKeysCase._change_case(input_obj, Strings.to_pascale_case, deep)

    @staticmethod
    def to_constant_case(
        input_obj: ValidIterables, deep: bool = True
    ) -> ValidIterables:
        """
        Convert the keys of the input object to constant case.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input object (str, dict, or list) to convert.
            deep (bool): Whether to apply the conversion deeply. Defaults to True.

        Returns:
            dict[str, Any] | Collection[Any]: The object with keys converted to constant case.
        """
        return ChangeKeysCase._change_case(input_obj, Strings.to_constant_case, deep)

    @staticmethod
    def to_dot_case(input_obj: ValidIterables) -> ValidIterables:
        """
        Convert the keys of the input dictionary to dot case and sort them.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input dictionary to convert.

        Returns:
            dict[str, Any] | Collection[Any]: The dictionary with keys converted to dot case and sorted.
        """
        return recursive_sort_keys(
            ChangeKeysCase._change_to_dot_case(ChangeKeysCase.to_snake_case(input_obj))
        )

    @staticmethod
    def _change_case(
        input_obj: ValidIterables, method: Callable[[str], str], deep: bool = True
    ) -> ValidIterables:
        """
        Helper method to change the case of keys in the input object using the specified method.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input object (str, dict, or list) to convert.
            method (Callable[[str], str]): The method to use for changing the case.
            deep (bool): Whether to apply the conversion deeply. Defaults to True.

        Returns:
            ValidIterables: The object with keys converted using the specified method.
        """
        if isinstance(input_obj, (bytes, str, bytearray, memoryview)):
            return method(input_obj)

        if isinstance(input_obj, dict):
            for key in filter(lambda k: k.startswith("_"), input_obj.keys()):
                new_key = str(key).lstrip("_")
                if new_key in input_obj:
                    input_obj[new_key] = input_obj[new_key] or input_obj[key]

            return {
                method(key): ChangeKeysCase._change_case(value, method)
                if deep and is_iterable_except_str_like(value)
                else value
                for key, value in dict(input_obj).items()
            }

        return _return_same_iterable(
            input_obj,
            [
                ChangeKeysCase._change_case(item, method)
                if is_iterable_except_str_like(item)
                else item
                for item in input_obj
            ],
        )

    @staticmethod
    def _change_to_dot_case(
        input_obj: ValidIterables, prefix: str = ""
    ) -> ValidIterables:
        """
        Helper method to convert the keys of the input dictionary to dot case.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input dictionary to convert.
            prefix (str, optional): The prefix to add to the keys. Defaults to "".

        Returns:
            dict[str, Any] | Collection[Any]: The dictionary with keys converted to dot case.
        """
        if not isinstance(input_obj, (ValidIterables, dict)):
            raise ValueError("Invalid input, must be an iterable")

        if not isinstance(input_obj, dict):
            return _return_same_iterable(
                input_obj,
                [
                    ChangeKeysCase._change_to_dot_case(item, prefix)
                    for item in input_obj
                ],
            )

        result = {}
        for key, value in dict(input_obj).items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(ChangeKeysCase._change_to_dot_case(value, new_key))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, dict):
                        result.update(
                            ChangeKeysCase._change_to_dot_case(
                                item, f"{new_key}.[{index}]"
                            )
                        )
                    else:
                        result[f"{new_key}[{index}]"] = item
            else:
                result[new_key] = value
        return result

    @staticmethod
    def flatten_all_cases(input_obj: ValidIterables) -> ValidIterables:
        """
        Flatten the input object by converting its keys to various cases.

        Args:
            input_obj (dict[str, Any] | Collection[Any]): The input object (dictionary or collection) to flatten.

        Returns:
            dict[str, Any] | Collection[Any]: The flattened object with keys converted to various cases.

        Raises:
            ValueError: If the input is not an iterable.
        """
        if not isinstance(input_obj, (dict, list, set, tuple)):
            return input_obj

        obj_copy = copy.deepcopy(input_obj)
        if isinstance(obj_copy, dict):
            if obj_copy.get("__flatten__", False):
                return obj_copy
            result = {}
            for key, value in dict(obj_copy).items():
                new_value = (
                    ChangeKeysCase.flatten_all_cases(value)
                    if isinstance(value, (Collection, dict))
                    and not isinstance(value, str)
                    else value
                )
                result.update(
                    {
                        Strings.to_camel_case(key): new_value,
                        Strings.to_snake_case(key): new_value,
                        Strings.to_kebab_case(key): new_value,
                        Strings.to_pascale_case(key): new_value,
                        Strings.to_constant_case(key): new_value,
                    }
                )

            result.update(ChangeKeysCase.to_dot_case(obj_copy))
            result["__flatten__"] = True
            return result

        return _return_same_iterable(
            obj_copy, [ChangeKeysCase.flatten_all_cases(item) for item in obj_copy]
        )


def find_subclasses(base_class: Type[T]) -> list[Type[T]]:
    """
    Find all classes that inherit from the given base class.

    Args:
        base_class: The class to find subclasses for

    Returns:
        list: A list of all subclasses (direct and indirect)
    """
    direct_subclasses = base_class.__subclasses__()
    all_subclasses = list(direct_subclasses)

    for subclass in direct_subclasses:
        all_subclasses.extend(find_subclasses(subclass))

    return list(dict.fromkeys(all_subclasses))
