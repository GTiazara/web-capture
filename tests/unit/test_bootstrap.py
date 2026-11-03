from __future__ import annotations

import asyncio
from pathlib import Path

from tests.fakes import FakeClock, FakeEncoder, FakeFrameSource, S
from web_capture.application.capture_service import CaptureService
from web_capture.application.frame_bus import FrameBus
from web_capture.application.recording_service import RecordingService
from web_capture.entrypoints.bootstrap import _run_until_shutdown


class FakeBrowser:
    def __init__(self) -> None:
        self.closed = asyncio.Event()

    async def wait_closed(self) -> None:
        await self.closed.wait()


async def test_browser_close_stops_capture_and_closes_bus(tmp_path: Path) -> None:
    clock = FakeClock()
    bus = FrameBus(10)
    capture = CaptureService(FakeFrameSource(clock), clock, bus, fps=10)
    encoder = FakeEncoder()
    recording = RecordingService(bus, encoder, clock, tmp_path, lambda: capture.fps)
    browser = FakeBrowser()
    shutdown = asyncio.Event()
    task = asyncio.create_task(
        _run_until_shutdown(capture, browser, recording, bus, shutdown)  # type: ignore[arg-type]
    )
    await clock.advance(S)
    browser.closed.set()
    await asyncio.wait_for(task, 1)
    assert bus.closed
    assert capture.last_seq is not None
    assert not recording.active
