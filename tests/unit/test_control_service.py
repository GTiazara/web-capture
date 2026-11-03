from __future__ import annotations

import pytest

from tests.fakes import FakeClock, FakeFrameSource
from web_capture.application.capture_service import CaptureService
from web_capture.application.control.handlers import CaptureHandlers
from web_capture.application.control.registry import CommandRegistry
from web_capture.application.control.service import ControlService
from web_capture.application.delivery import LatestPolicy
from web_capture.application.frame_bus import FrameBus
from web_capture.domain.frame import Zone


class Ctx:
    def __init__(self) -> None:
        clock = FakeClock()
        self.bus = FrameBus(10)
        self.capture = CaptureService(FakeFrameSource(clock), clock, self.bus, fps=10)
        self.handlers = CaptureHandlers(self.capture, self.bus, lambda: "http://x/")
        registry = CommandRegistry()
        self.handlers.register(registry)
        self.registry = registry
        self.control = ControlService(registry)


@pytest.fixture
def ctx() -> Ctx:
    return Ctx()


async def test_correlated_response(ctx: Ctx) -> None:
    resp = await ctx.control.execute({"id": 7, "cmd": "status"})
    assert resp["id"] == 7 and resp["ok"] is True


async def test_unknown_command(ctx: Ctx) -> None:
    resp = await ctx.control.execute({"id": 8, "cmd": "explode"})
    assert resp == {"id": 8, "ok": False, "error": resp["error"]}
    assert "explode" in resp["error"]


@pytest.mark.parametrize("raw", [[1, 2], "texte", None, {"id": 1}])
async def test_malformed_messages(ctx: Ctx, raw: object) -> None:
    resp = await ctx.control.execute(raw)
    assert resp["ok"] is False and resp["error"]


async def test_set_fps(ctx: Ctx) -> None:
    resp = await ctx.control.execute({"id": 1, "cmd": "set_fps", "fps": 5})
    assert resp["ok"] is True and resp["fps"] == 5
    assert ctx.capture.fps == 5


async def test_set_fps_rejected(ctx: Ctx) -> None:
    resp = await ctx.control.execute({"id": 1, "cmd": "set_fps", "fps": 120})
    assert resp["ok"] is False and "120" in resp["error"]
    assert ctx.capture.fps == 10
    resp = await ctx.control.execute({"id": 2, "cmd": "set_fps"})
    assert resp["ok"] is False


async def test_set_zone_and_reset(ctx: Ctx) -> None:
    zone = {"x": 0, "y": 0, "width": 640, "height": 360}
    resp = await ctx.control.execute({"id": 1, "cmd": "set_zone", "zone": zone})
    assert resp["ok"] is True and resp["zone"] == zone
    assert ctx.capture.zone == Zone(0, 0, 640, 360)
    resp = await ctx.control.execute({"id": 2, "cmd": "set_zone", "zone": None})
    assert resp["ok"] is True and ctx.capture.zone is None


@pytest.mark.parametrize(
    "zone",
    [
        {"x": 1000, "y": 0, "width": 400, "height": 10},
        {"x": 0},
        "abc",
        {"x": "a", "y": 0, "width": 1, "height": 1},
    ],
)
async def test_set_zone_rejected(ctx: Ctx, zone: object) -> None:
    resp = await ctx.control.execute({"id": 1, "cmd": "set_zone", "zone": zone})
    assert resp["ok"] is False
    assert ctx.capture.zone is None


async def test_pause_resume(ctx: Ctx) -> None:
    assert (await ctx.control.execute({"id": 2, "cmd": "pause"}))["ok"] is True
    assert ctx.capture.paused
    status = await ctx.control.execute({"id": 3, "cmd": "status"})
    assert status["state"] == "paused"
    assert (await ctx.control.execute({"id": 4, "cmd": "resume"}))["ok"] is True
    assert not ctx.capture.paused


async def test_status_content(ctx: Ctx) -> None:
    ctx.bus.subscribe(LatestPolicy())
    status = await ctx.control.execute({"id": 3, "cmd": "status"})
    assert status["state"] == "running"
    assert status["fps"] == 10
    assert status["zone"] is None
    assert status["url"] == "http://x/"
    assert "effective_fps" in status and "last_seq" in status
    assert status["subscribers"] == {"latest": 1, "all": 0}


def test_duplicate_registration_rejected(ctx: Ctx) -> None:
    with pytest.raises(ValueError):
        ctx.handlers.register(ctx.registry)
