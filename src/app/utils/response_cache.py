from __future__ import annotations

import time
from typing import TypeVar

T = TypeVar("T")

_CACHE: dict[str, tuple[float, object]] = {}
# Public list endpoints invalidate their own cache on writes, so a longer TTL
# is safe and dramatically cuts DB round-trips for read-heavy browsing.
DEFAULT_TTL_SECS = 180


def get_cached(key: str, ttl_secs: int = DEFAULT_TTL_SECS) -> T | None:
    hit = _CACHE.get(key)
    if not hit:
        return None
    cached_at, value = hit
    if time.monotonic() - cached_at > ttl_secs:
        _CACHE.pop(key, None)
        return None
    return value  # type: ignore[return-value]


def set_cached(key: str, value: T) -> T:
    _CACHE[key] = (time.monotonic(), value)
    return value


def invalidate_prefix(prefix: str) -> None:
    for key in list(_CACHE.keys()):
        if key.startswith(prefix):
            _CACHE.pop(key, None)


def invalidate_job_listings() -> None:
    invalidate_prefix("jobs:list:")


def invalidate_skill_listings() -> None:
    invalidate_prefix("skills:list:")
