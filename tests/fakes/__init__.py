from __future__ import annotations

import asyncio
import heapq
import itertools
from pathlib import Path
from typing import Any

from web_capture.application.ports import Clock, FrameSource, VideoEncoder
from web_capture.domain.errors import EncoderUnavailableError
from web_capture.domain.frame import CapturedImage, Point, Size, Zone

MS = 1_000_000
S = 1_000_000_000


async def settle(rounds: int = 50) -> None:
    for _ in range(rounds):
        await asyncio.sleep(0)


class FakeClock:
    """Horloge virtuelle : le temps n'avance que via `advance_to` / `advance`."""

    def __init__(self, start_ns: int = 0, wall_origin_ms: int = 1_700_000_000_000) -> None:
        self.now_ns = start_ns
        self._wall_origin_ms = wall_origin_ms
        self._sleepers: list[tuple[int, int, asyncio.Future[None]]] = []
        self._ids = itertools.count()

    def monotonic_ns(self) -> int:
        return self.now_ns

    def wall_ms(self) -> int:
        return self._wall_origin_ms + self.now_ns // MS

    async def sleep_until(self, deadline_ns: int, wake: asyncio.Event | None = None) -> None:
        if deadline_ns <= self.now_ns:
            await asyncio.sleep(0)
            return
        fut: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        heapq.heappush(self._sleepers, (deadline_ns, next(self._ids), fut))
        if wake is None:
            await fut
            return
        waiter = asyncio.ensure_future(wake.wait())
        both: set[asyncio.Future[Any]] = {fut, waiter}
        try:
            await asyncio.wait(both, return_when=asyncio.FIRST_COMPLETED)
        finally:
            waiter.cancel()
            if not fut.done():
                fut.cancel()

    async def advance_to(self, target_ns: int) -> None:
        await settle()
        while self._sleepers and self._sleepers[0][0] <= target_ns:
            deadline, _, fut = heapq.heappop(self._sleepers)
            if fut.done():
                continue
            self.now_ns = max(self.now_ns, deadline)
            fut.set_result(None)
            await settle()
        self.now_ns = max(self.now_ns, target_ns)
        await settle()

    async def advance(self, delta_ns: int) -> None:
        await self.advance_to(self.now_ns + delta_ns)


DEFAULT_VIEWPORT = Size(1280, 720)


class FakeFrameSource:
    def __init__(
        self,
        clock: FakeClock,
        viewport: Size = DEFAULT_VIEWPORT,
        delay_ns: int = 0,
        payload: bytes = b"\xff\xd8fake\xff\xd9",
    ) -> None:
        self.clock = clock
        self._viewport = viewport
        self.delay_ns = delay_ns
        self.payload = payload
        self.grab_times: list[int] = []
        self.zones: list[Zone | None] = []

    @property
    def viewport(self) -> Size:
        return self._viewport

    async def grab(self, zone: Zone | None) -> CapturedImage:
        self.grab_times.append(self.clock.monotonic_ns())
        self.zones.append(zone)
        if self.delay_ns:
            await self.clock.sleep_until(self.clock.monotonic_ns() + self.delay_ns)
        effective = zone or Zone.full(self._viewport)
        return CapturedImage(
            data=self.payload,
            tab_id="FAKE",
            zone=effective,
            dpr=1.0,
            scroll=Point(0, 0),
            size=Size(int(effective.width), int(effective.height)),
        )


class FakeEncoder:
    def __init__(
        self,
        clock: FakeClock | None = None,
        write_delay_ns: int = 0,
        available: bool = True,
    ) -> None:
        self.clock = clock
        self.write_delay_ns = write_delay_ns
        self.available = available
        self.opened: list[tuple[Path, float]] = []
        self.frames: list[bytes] = []
        self.closed = 0

    async def open(self, path: Path, fps: float) -> None:
        if not self.available:
            raise EncoderUnavailableError("encodeur vidéo introuvable")
        path.write_bytes(b"")
        self.opened.append((path, fps))

    async def write(self, jpeg: bytes) -> None:
        if self.clock is not None and self.write_delay_ns:
            await self.clock.sleep_until(self.clock.monotonic_ns() + self.write_delay_ns)
        self.frames.append(jpeg)

    async def close(self) -> None:
        self.closed += 1


def _conforms() -> None:
    clock: Clock = FakeClock()
    _source: FrameSource = FakeFrameSource(FakeClock())
    _encoder: VideoEncoder = FakeEncoder()
    del clock
