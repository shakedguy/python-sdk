import asyncio
import time
from functools import cache as functools_cache
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")
R = TypeVar("R")

class AsyncLRUCache(object):
    def __init__(self, ttl: float | None = None):
        self.cache: dict[Any, tuple[R, float]] = {}
        self.ttl = ttl

    async def get_or_set(self, key: Any, create: Callable[[], Awaitable[R]]) -> R:
        now = time.time()
        hit = self.cache.get(key)
        if hit is not None:
            value, ts = hit
            if self.ttl is None or now - ts < self.ttl:
                return value

        value = await create()
        self.cache[key] = (value, now)
        return value

def mem_cache(*, ttl: float | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(inner_func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(inner_func):
            cache_storage = AsyncLRUCache(ttl=ttl)

            @wraps(inner_func)
            async def async_wrapper(*args, **kwargs):
                key = (args, frozenset(kwargs.items()))
                return await cache_storage.get_or_set(key, lambda: inner_func(*args, **kwargs))
            return async_wrapper

        else:
            @functools_cache
            @wraps(inner_func)
            def sync_wrapper(*args, **kwargs):
                return inner_func(*args, **kwargs)
            return sync_wrapper

    return decorator