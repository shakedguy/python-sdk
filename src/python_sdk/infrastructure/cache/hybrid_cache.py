from datetime import timedelta
from typing import Any, Hashable, Optional, TypeVar, Union

import orjson
from cachetools import TTLCache
from pydantic import BaseModel

from ...conf.constants import CACHE_PREFIX
from ...utils.strings import AnyStr, Strings
from .redis_client import RedisClient

T = TypeVar("T")
KeyValueType = Union[AnyStr, int, float, Hashable, list, set, tuple, dict, BaseModel]


def to_str_key(key: KeyValueType) -> bytes:
    if isinstance(key, BaseModel):
        return key.model_dump_json(indent=0).encode()
    elif isinstance(key, AnyStr):
        return Strings.to_str(key).encode()
    elif isinstance(key, (int, float)):
        return str(key).encode()
    else:
        return orjson.dumps(key)


class HybridCache:
    def __init__(self, prefix: str = CACHE_PREFIX, max_size: float = 1024, default_ttl: float = 300) -> None:
        self.prefix: bytes = prefix.encode() if prefix else b""
        self.memory_cache: TTLCache = TTLCache(maxsize=max_size, ttl=default_ttl)

    def get(self, key: KeyValueType) -> Optional[Any]:
        str_key = self.prefix + to_str_key(key)

        result = self.memory_cache.get(str_key)
        if result is not None:
            return result

        with RedisClient() as client:
            result = client.get(str_key)
        if result is None:
            return None

        cache_obj = orjson.loads(result)  # type: ignore

        type_name = cache_obj["type"]
        result = cache_obj["value"]
        self.memory_cache[str_key] = result

        if type_name in ["dict", "list", "set", "tuple"]:
            result = orjson.loads(result)  # type: ignore
            result = list(result) if type_name == "list" else set(result) if type_name == "set" else tuple(
                result) if type_name == "tuple" else result  # type: ignore

        elif type_name in ["int", "float", "bool", "str"]:
            result = eval(f"{type_name}({repr(result)})")  # type: ignore

        else:
            model_class = globals().get(type_name)
            if model_class and issubclass(model_class, BaseModel):
                result = model_class.model_validate_json(result)  # type: ignore

        return result

    def set(self, key: KeyValueType, value: KeyValueType, ttl: Optional[Union[timedelta, float, int]] = None) -> None:

        if isinstance(ttl, (int, float)) and ttl <= 0:
            raise ValueError("TTL must be a positive number")

        key_str = self.prefix + to_str_key(key)
        value_type = type(value).__name__

        value_serialized = value.model_dump(mode="json") if isinstance(value, BaseModel) else value

        cache_obj = {
            "type": value_type,
            "value": value_serialized
        }
        cache_serialized = orjson.dumps(cache_obj)
        self.memory_cache[key_str] = value

        timedelta_ttl = timedelta(seconds=ttl) if isinstance(ttl, (int, float)) else ttl

        with RedisClient() as client:
            client.set(key_str, cache_serialized, ex=timedelta_ttl)

    def delete(self, key) -> None:

        key_str = self.prefix + to_str_key(key)
        self.memory_cache.pop(key_str, None)
        with RedisClient() as client:
            client.delete(key_str)

    def clear(self):
        self.memory_cache.clear()

        with RedisClient() as client:
            client.delete(self.prefix + b"*")
