from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass
class _CacheItem:
    expires_at: float
    value: object


class CacheService:
    def __init__(self):
        self._items: dict[str, _CacheItem] = {}
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None

            if item.expires_at < monotonic():
                self._items.pop(key, None)
                return None

            return item.value

    def set(self, key: str, value, ttl_seconds: int):
        with self._lock:
            self._items[key] = _CacheItem(
                expires_at=monotonic() + max(ttl_seconds, 1),
                value=value,
            )

    def get_or_set(self, key: str, factory, ttl_seconds: int):
        cached = self.get(key)
        if cached is not None:
            return cached

        value = factory()
        self.set(key, value, ttl_seconds)
        return value

    def clear(self):
        with self._lock:
            self._items.clear()

    def delete(self, key: str):
        with self._lock:
            self._items.pop(key, None)

    def clear_prefix(self, prefix: str):
        with self._lock:
            keys = [key for key in self._items if key.startswith(prefix)]
            for key in keys:
                self._items.pop(key, None)


cache_service = CacheService()