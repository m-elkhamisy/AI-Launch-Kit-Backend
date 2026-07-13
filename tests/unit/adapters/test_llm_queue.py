"""Tests for shared provider request pacing."""

import asyncio

from launchkit.adapters.llm_queue import RequestQueue


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.now += delay


def test_queue_spaces_starts_and_counts_requests() -> None:
    fake = FakeTime()
    queue = RequestQueue(max_concurrent=0, min_gap_seconds=-1, clock=fake.clock, sleep=fake.sleep)

    async def scenario() -> list[int]:
        first = await queue.run(lambda: asyncio.sleep(0, result=1))
        second = await queue.run(lambda: asyncio.sleep(0, result=2))
        return [first, second]

    assert asyncio.run(scenario()) == [1, 2]
    assert queue.max_concurrent == 1
    assert queue.min_gap_seconds == 0
    assert queue.started == 2


def test_queue_honors_start_gap_and_longest_shared_cooldown() -> None:
    fake = FakeTime()
    queue = RequestQueue(max_concurrent=2, min_gap_seconds=0.25, clock=fake.clock, sleep=fake.sleep)

    async def scenario() -> None:
        await queue.run(lambda: asyncio.sleep(0))
        await queue.note_rate_limit(1.0)
        await queue.note_rate_limit(0.5)
        await queue.run(lambda: asyncio.sleep(0))

    asyncio.run(scenario())

    assert fake.sleeps == [1.0]
    assert queue.started == 2
