from __future__ import annotations

from pathlib import Path

import pytest

from tests.fakes import FakeClock, FakeEncoder, FakeFrameSource, S
from web_capture.application.capture_service import CaptureService
from web_capture.application.control.handlers import CaptureHandlers
from web_capture.application.control.registry import CommandRegistry
from web_capture.application.control.service import ControlService
from web_capture.application.frame_bus import FrameBus
from web_capture.application.recording_service import RecordingService


class Ctx:
    def __init__(self, tmp: Path, encoder: FakeEncoder | None = None) -> None:
        self.clock = FakeClock()
        self.bus = FrameBus(10)
        self.capture = CaptureService(FakeFrameSource(self.clock), self.clock, self.bus, fps=10)
        self.encoder = encoder or FakeEncoder()
        self.recording = RecordingService(
            self.bus, self.encoder, self.clock, tmp / "rec", lambda: self.capture.fps
        )
        registry = CommandRegistry()
        CaptureHandlers(self.capture, self.bus, lambda: "u", self.recording).register(registry)
        self.control = ControlService(registry)


@pytest.fixture
def ctx(tmp_path: Path) -> Ctx:
    return Ctx(tmp_path)


async def test_recording_cycle_produces_existing_file(ctx: Ctx) -> None:
    resp = await ctx.control.execute({"id": 1, "cmd": "start_recording"})
    assert resp["ok"] is True and resp["file"].endswith(".mp4")
    await ctx.clock.advance(3 * S)
    resp = await ctx.control.execute({"id": 2, "cmd": "stop_recording"})
    assert resp["ok"] is True
    path = Path(resp["path"])
    assert path.is_file() and path.name.endswith(".mp4")
    assert path.parent == (ctx.recording._output_dir).resolve()


async def test_double_start_refused_and_recording_continues(ctx: Ctx) -> None:
    await ctx.control.execute({"id": 1, "cmd": "start_recording"})
    resp = await ctx.control.execute({"id": 2, "cmd": "start_recording"})
    assert resp["ok"] is False
    assert ctx.recording.active
    await ctx.control.execute({"id": 3, "cmd": "stop_recording"})


async def test_stop_without_recording_refused(ctx: Ctx) -> None:
    resp = await ctx.control.execute({"id": 1, "cmd": "stop_recording"})
    assert resp["ok"] is False


async def test_set_zone_refused_while_recording(ctx: Ctx) -> None:
    await ctx.control.execute({"id": 1, "cmd": "start_recording"})
    zone = {"x": 0, "y": 0, "width": 10, "height": 10}
    resp = await ctx.control.execute({"id": 2, "cmd": "set_zone", "zone": zone})
    assert resp["ok"] is False and "enregistrement" in resp["error"]
    assert ctx.capture.zone is None
    await ctx.control.execute({"id": 3, "cmd": "stop_recording"})
    resp = await ctx.control.execute({"id": 4, "cmd": "set_zone", "zone": zone})
    assert resp["ok"] is True


async def test_status_reflects_recording(ctx: Ctx) -> None:
    status = await ctx.control.execute({"id": 1, "cmd": "status"})
    assert status["recording"]["state"] == "idle"
    await ctx.control.execute({"id": 2, "cmd": "start_recording"})
    status = await ctx.control.execute({"id": 3, "cmd": "status"})
    assert status["recording"]["state"] == "recording"
    assert status["recording"]["file"].endswith(".mp4")
    assert {"frames_written", "frames_dropped"} <= status["recording"].keys()
    await ctx.control.execute({"id": 4, "cmd": "stop_recording"})


async def test_unavailable_encoder_reported(tmp_path: Path) -> None:
    ctx = Ctx(tmp_path, FakeEncoder(available=False))
    resp = await ctx.control.execute({"id": 1, "cmd": "start_recording"})
    assert resp["ok"] is False and "introuvable" in resp["error"]
    assert not ctx.recording.active
