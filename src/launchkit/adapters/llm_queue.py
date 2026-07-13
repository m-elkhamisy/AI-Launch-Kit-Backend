"""Shared async pacing for calls that consume one provider rate limit."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
Clock = Callable[[], float]
Sleeper = Callable[[float], Awaitable[None]]


class RequestQueue:
    """Limit concurrency, request-start bursts, and shared cooldowns."""

    def __init__(
        self,
        *,
        max_concurrent: int = 2,
        min_gap_seconds: float = 0.25,
        clock: Clock = time.monotonic,
        sleep: Sleeper = asyncio.sleep,
    ) -> None:
        self.max_concurrent = max(1, max_concurrent)
        self.min_gap_seconds = max(0.0, min_gap_seconds)
        self.started = 0
        self._clock = clock
        self._sleep = sleep
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._start_lock = asyncio.Lock()
        self._last_start = -self.min_gap_seconds
        self._paused_until = 0.0

    async def note_rate_limit(self, cooldown_seconds: float) -> None:
        """Pause future starts for the longest reported cooldown."""

        async with self._start_lock:
            self._paused_until = max(
                self._paused_until,
                self._clock() + max(0.0, cooldown_seconds),
            )

    async def run(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Run one operation while holding a slot only for its request."""

        async with self._semaphore:
            await self._pace_start()
            return await operation()

    async def _pace_start(self) -> None:
        async with self._start_lock:
            while True:
                now = self._clock()
                deadline = max(self._last_start + self.min_gap_seconds, self._paused_until)
                delay = deadline - now
                if delay <= 0:
                    break
                await self._sleep(delay)
            self._last_start = self._clock()
            self.started += 1
