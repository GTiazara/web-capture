from __future__ import annotations

import asyncio
import contextlib
import time


class SystemClock:
    def monotonic_ns(self) -> int:
        return time.monotonic_ns()

    def wall_ms(self) -> int:
        return time.time_ns() // 1_000_000

    async def sleep_until(self, deadline_ns: int, wake: asyncio.Event | None = None) -> None:
        delay = max(0.0, (deadline_ns - time.monotonic_ns()) / 1e9)
        if wake is None:
            await asyncio.sleep(delay)
            return
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(wake.wait(), delay)
