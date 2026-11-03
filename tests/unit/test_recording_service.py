from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from tests.fakes import MS, FakeClock, FakeEncoder, S
from tests.unit.test_frame_bus import frame
from web_capture.application.frame_bus import FrameBus
from web_capture.application.recording_service import RecordingService, RecordingState
from web_capture.domain.errors import EncoderUnavailableError, RecordingError


class Rec:
    def __init__(self, tmp: Path, fps: float = 10, encoder: FakeEncoder | None = None) -> None:
        self.clock = FakeClock()
        self.bus = FrameBus(10)
        self.bus.publish(frame(0))
        self.fps = fps
        self.encoder = encoder or FakeEncoder()
        self.service = RecordingService(
            self.bus,
            self.encoder,
            self.clock,
            tmp / "out",
            lambda: self.fps,
            now=lambda: datetime(2026, 11, 3, 14, 5, 9),
        )


async def publisher(rec: Rec, fps: float, until_ns: int) -> None:
    seq = 1
    while rec.clock.monotonic_ns() < until_ns:
        await rec.clock.sleep_until(rec.clock.monotonic_ns() + round(S / fps))
        rec.bus.publish(frame(seq))
        seq += 1


async def test_about_100_frames_in_10_s_whatever_the_capture_rate(tmp_path: Path) -> None:
    rec = Rec(tmp_path)
    path = await rec.service.start()
    pub = asyncio.create_task(publisher(rec, 3, 10 * S))
    await rec.clock.advance_to(10 * S - 1)
    assert (await rec.service.stop()) == path
    await rec.clock.advance(S)
    await pub
    assert 99 <= len(rec.encoder.frames) <= 101
    assert rec.service.status()["frames_written"] == len(rec.encoder.frames)
    assert rec.encoder.opened == [(path, 10)]
    assert rec.encoder.closed == 1


async def test_fps_change_during_recording_keeps_recording_fps(tmp_path: Path) -> None:
    rec = Rec(tmp_path)
    await rec.service.start()
    await rec.clock.advance_to(5 * S - 1)
    rec.fps = 2
    await rec.clock.advance_to(10 * S - 1)
    await rec.service.stop()
    assert 99 <= len(rec.encoder.frames) <= 101


async def test_generated_file_name_in_output_dir(tmp_path: Path) -> None:
    rec = Rec(tmp_path)
    path = await rec.service.start()
    assert path.parent == tmp_path / "out"
    assert path.name == "capture-20261103-140509.mp4"
    await rec.service.stop()
    second = await rec.service.start()
    assert second.name == "capture-20261103-140509-1.mp4"
    await rec.service.stop()


async def test_double_start_refused(tmp_path: Path) -> None:
    rec = Rec(tmp_path)
    await rec.service.start()
    with pytest.raises(RecordingError):
        await rec.service.start()
    assert rec.service.state is RecordingState.RECORDING
    await rec.service.stop()
    with pytest.raises(RecordingError):
        await rec.service.stop()


async def test_slow_encoder_counts_drops(tmp_path: Path) -> None:
    clock_holder = FakeEncoder()
    rec = Rec(tmp_path, encoder=clock_holder)
    clock_holder.clock = rec.clock
    clock_holder.write_delay_ns = 500 * MS
    await rec.service.start()
    await rec.clock.advance_to(10 * S - 1)
    stopping = asyncio.create_task(rec.service.stop())
    await rec.clock.advance(60 * S)
    await stopping
    status = rec.service.status()
    assert status["frames_dropped"] > 0
    assert 99 <= status["frames_written"] + status["frames_dropped"] <= 101


async def test_encoder_unavailable_keeps_idle(tmp_path: Path) -> None:
    rec = Rec(tmp_path, encoder=FakeEncoder(available=False))
    with pytest.raises(EncoderUnavailableError):
        await rec.service.start()
    assert rec.service.state is RecordingState.IDLE


async def test_aclose_finalizes(tmp_path: Path) -> None:
    rec = Rec(tmp_path)
    await rec.service.start()
    await rec.clock.advance(S)
    await rec.service.aclose()
    assert rec.service.state is RecordingState.IDLE
    assert rec.encoder.closed == 1
    await rec.service.aclose()
    assert rec.encoder.closed == 1
