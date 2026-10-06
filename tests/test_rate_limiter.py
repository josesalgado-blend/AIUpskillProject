# tests/test_rate_limiter.py
import asyncio

import pytest

from src.strategies.rate_limit_strategy import SemaphoreStrategy, TokenBucketStrategy
from src.utils.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_caps_concurrency():
    limiter = RateLimiter(max_concurrent=2)
    running = 0
    peak = 0

    async def task():
        nonlocal running, peak
        async with limiter:
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.02)
            running -= 1

    await asyncio.gather(*(task() for _ in range(6)))

    assert peak == 2


@pytest.mark.asyncio
async def test_rate_limiter_execute_returns_result():
    async def work():
        return 42

    assert await RateLimiter(max_concurrent=1).execute(work()) == 42


@pytest.mark.asyncio
async def test_semaphore_strategy_caps_concurrency():
    strategy = SemaphoreStrategy(max_concurrent=3)
    running = 0
    peak = 0

    async def task():
        nonlocal running, peak
        await strategy.acquire()
        try:
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.02)
            running -= 1
        finally:
            strategy.release()

    await asyncio.gather(*(task() for _ in range(9)))

    assert peak == 3


@pytest.mark.asyncio
async def test_token_bucket_allows_burst_then_waits():
    # 2 requests per 0.2 s: the burst of 2 is immediate, the 3rd must wait.
    bucket = TokenBucketStrategy(rate=2, per=0.2)
    loop = asyncio.get_running_loop()

    start = loop.time()
    await bucket.acquire()
    await bucket.acquire()
    burst = loop.time() - start

    await bucket.acquire()
    third = loop.time() - start

    assert burst < 0.05
    assert third >= 0.05
    bucket.release()  # no-op, must not raise
