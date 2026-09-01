"""Client-side rate limiter for Telegram Bot API limits."""

from __future__ import annotations

import time
from collections import deque

from telegram_demo_outbound.constants import (
    GLOBAL_MAX_PER_SEC,
    PER_CHAT_MIN_INTERVAL_SEC,
)


class Clock:
    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


class RateLimiter:
    """Enforce per-chat spacing and a global messages-per-second cap."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        per_chat_interval: float = PER_CHAT_MIN_INTERVAL_SEC,
        global_max_per_sec: int = GLOBAL_MAX_PER_SEC,
    ) -> None:
        self._clock = clock or Clock()
        self._per_chat_interval = per_chat_interval
        self._global_max_per_sec = global_max_per_sec
        self._last_per_chat: dict[str, float] = {}
        self._global_times: deque[float] = deque()

    def wait(self, chat_id: str) -> None:
        while True:
            now = self._clock.monotonic()
            wait_chat = 0.0
            last = self._last_per_chat.get(chat_id)
            if last is not None:
                wait_chat = self._per_chat_interval - (now - last)

            while self._global_times and now - self._global_times[0] >= 1.0:
                self._global_times.popleft()
            wait_global = 0.0
            if len(self._global_times) >= self._global_max_per_sec:
                wait_global = 1.0 - (now - self._global_times[0])

            delay = max(wait_chat, wait_global, 0.0)
            if delay <= 0:
                stamp = self._clock.monotonic()
                self._last_per_chat[chat_id] = stamp
                self._global_times.append(stamp)
                return
            self._clock.sleep(delay)
