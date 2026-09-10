import time
import diskcache
from functools import wraps
from typing import Any, Callable

_cache = diskcache.Cache(".cache/india-market-mcp", size_limit=500_000_000)

def cached(ttl: int = 300, prefix: str = ""):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_parts = [prefix or func.__name__] + [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
            cache_key = ":".join(key_parts)
            result = _cache.get(cache_key)
            if result is not None:
                ts, data = result
                if time.time() - ts < ttl:
                    return data
            data = await func(*args, **kwargs)
            # Error responses are transient diagnostics, not cacheable data.
            if data is not None and not (isinstance(data, dict) and data.get("error")):
                _cache.set(cache_key, (time.time(), data), expire=ttl)
            return data
        return wrapper
    return decorator
