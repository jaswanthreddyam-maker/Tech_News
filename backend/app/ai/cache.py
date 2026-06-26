import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    payload: dict[str, Any]
    expires_at: float


class MemoryAICache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}

    def build_key(
        self,
        *,
        provider: str,
        model: str,
        task_type: str,
        prompt_version: str,
        title: str,
        content: str,
    ) -> str:
        raw = json.dumps(
            {
                "provider": provider,
                "model": model,
                "task_type": task_type,
                "prompt_version": prompt_version,
                "title": title,
                "content": content,
            },
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            self._entries.pop(key, None)
            return None
        return entry.payload

    def set(self, key: str, payload: dict[str, Any]) -> None:
        self._entries[key] = CacheEntry(payload=payload, expires_at=time.time() + self.ttl_seconds)
