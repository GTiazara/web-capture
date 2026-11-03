import asyncio
import itertools
from collections.abc import AsyncIterator

import pytest

from tests.fakes import MS, FakeClock, FakeFrameSource, S
from web_capture.application.capture_service import CaptureService
from web_capture.application.frame_bus import FrameBus
from web_capture.domain.errors import InvalidFpsError, InvalidZoneError
from web_capture.domain.frame import CapturedImage, Zone


class Harness:
    def __init__(self, fps: float = 10, delay_ns: int = 0) -> None:
        self.clock = FakeClock()
        self.source = FakeFrameSource(self.clock, delay_ns=delay_ns)
        self.bus = FrameBus(1000)
        self.service = CaptureService(self.source, self.clock, self.bus, fps=fps)
        self.task: asyncio.Task[None] | None = None

    def intervals_ms(self) -> list[float]:
        t = self.source.grab_times
        return [(b - a) / MS for a, b in itertools.pairwise(t)]


@pytest.fixture
async def h() -> AsyncIterator[Harness]:
    harness = Harness()
    yield harness
    harness.service.stop()
    if harness.task is not None:
        await harness.clock.advance(S)
        await asyncio.wait_for(harness.task, 1)


def start(h: Harness) -> None:
    h.task = asyncio.create_task(h.service.run())


async def test_about_50_frames_in_5_seconds_at_10_fps(h: Harness) -> None:
    start(h)
    await h.clock.advance_to(5 * S - 1)
    assert 45 <= len(h.bus.frames()) <= 55
    assert all(abs(i - 100) < 1 for i in h.intervals_ms())


async def test_slow_capture_skips_deadlines_without_burst() -> None:
    h = Harness(fps=30, delay_ns=100 * MS)
    h.task = asyncio.create_task(h.service.run())
    await h.clock.advance_to(5 * S)
    assert all(i >= 100 for i in h.intervals_ms())
    assert 9 <= h.service.effective_fps() <= 11
    h.service.stop()
    await h.clock.advance(S)
    await asyncio.wait_for(h.task, 1)


async def test_fps_change_applies_from_next_frame(h: Harness) -> None:
    start(h)
    await h.clock.advance_to(1 * S)
    h.service.set_fps(2)
    await h.clock.advance_to(4 * S)
    after = [t for t in h.source.grab_times if t > 1 * S]
    gaps = [(b - a) / MS for a, b in itertools.pairwise(after)]
    assert gaps and all(abs(g - 500) < 1 for g in gaps)


async def test_fps_increase_interrupts_long_sleep() -> None:
    h = Harness(fps=0.1)
    h.task = asyncio.create_task(h.service.run())
    await h.clock.advance_to(1 * S)
    assert len(h.source.grab_times) == 1
    h.service.set_fps(10)
    await h.clock.advance_to(1 * S + 1)
    assert len(h.source.grab_times) == 2
    h.service.stop()
    await h.clock.advance(S)
    await asyncio.wait_for(h.task, 1)


async def test_out_of_bounds_fps_rejected_and_unchanged(h: Harness) -> None:
    with pytest.raises(InvalidFpsError):
        h.service.set_fps(120)
    assert h.service.fps == 10


async def test_pause_and_resume_keep_sequence(h: Harness) -> None:
    start(h)
    await h.clock.advance_to(1 * S - 1)
    last = h.service.last_seq
    assert last == 9
    h.service.pause()
    await h.clock.advance_to(3 * S)
    assert h.service.last_seq == last
    assert h.service.effective_fps() == 0
    h.service.resume()
    await h.clock.advance(1)
    first_after = h.bus.frames()[-1]
    assert first_after.seq == last + 1
    assert first_after.meta.ts_mono_ns >= 3 * S


async def test_zone_applied_and_invalid_zone_rejected(h: Harness) -> None:
    start(h)
    zone = Zone(100, 50, 400, 300)
    h.service.set_zone(zone)
    await h.clock.advance_to(1 * S)
    assert h.source.zones[-1] == zone
    assert h.bus.frames()[-1].meta.zone == zone
    with pytest.raises(InvalidZoneError):
        h.service.set_zone(Zone(1000, 0, 400, 10))
    assert h.service.zone == zone
    h.service.set_zone(None)
    await h.clock.advance(200 * MS)
    assert h.source.zones[-1] is None


async def test_metadata_and_timestamps(h: Harness) -> None:
    start(h)
    await h.clock.advance_to(150 * MS)
    a, b = h.bus.frames()[:2]
    assert (a.seq, b.seq) == (0, 1)
    assert b.meta.ts_mono_ns > a.meta.ts_mono_ns
    assert b.meta.ts_wall_ms - a.meta.ts_wall_ms == 100


async def test_source_error_does_not_stop_capture(h: Harness) -> None:
    original = h.source.grab
    calls = {"n": 0}

    async def flaky(zone: Zone | None) -> CapturedImage:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("navigation en cours")
        return await original(zone)

    h.source.grab = flaky  # type: ignore[method-assign]
    start(h)
    await h.clock.advance_to(500 * MS)
    seqs = [f.seq for f in h.bus.frames()]
    assert seqs == list(range(len(seqs))) and len(seqs) >= 4
