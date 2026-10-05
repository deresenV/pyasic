import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pyasic import settings

T = TypeVar("T")


async def cached_response(
    owner: Any,
    attribute: str,
    setting: str,
    fetch: Callable[[], Awaitable[T]],
) -> T:
    """Reuse an instance response while its cache setting is enabled."""
    if not settings.get(setting, True):
        return await fetch()

    cached = getattr(owner, attribute)
    if cached is not None:
        return cached

    locks = getattr(owner, "_response_cache_locks", None)
    if locks is None:
        locks = {}
        setattr(owner, "_response_cache_locks", locks)
    lock = locks.setdefault(attribute, asyncio.Lock())

    async with lock:
        # The first caller may have populated the cache while we waited.
        cached = getattr(owner, attribute)
        if cached is not None:
            return cached

        result = await fetch()
        if result is not None and not (
            isinstance(result, dict) and result.get("success") is False
        ):
            setattr(owner, attribute, result)
        return result
