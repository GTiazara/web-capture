from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pytest
from PIL import Image

from web_capture.adapters.browser.playwright_session import PlaywrightBrowserSession
from web_capture.adapters.capture.cdp_frame_source import CdpFrameSource
from web_capture.adapters.clock import SystemClock
from web_capture.application.capture_service import CaptureService
from web_capture.application.frame_bus import FrameBus
from web_capture.domain.frame import CapturedImage, Size, Zone

pytestmark = pytest.mark.integration

VIEWPORT = Size(1280, 720)
RED = Zone(100, 50, 400, 300)


def source_for(session: PlaywrightBrowserSession) -> CdpFrameSource:
    return CdpFrameSource(session.cdp, session.tab_id, VIEWPORT, jpeg_quality=90)


def center_rgb(image: CapturedImage) -> tuple[int, int, int]:
    img = Image.open(io.BytesIO(image.data)).convert("RGB")
    r, g, b = img.getpixel((img.width // 2, img.height // 2))  # type: ignore[misc]
    return int(r), int(g), int(b)


def dominant(rgb: tuple[int, int, int]) -> str:
    names = ("red", "green", "blue")
    hi = max(range(3), key=lambda i: rgb[i])
    return names[hi] if rgb[hi] > 200 and sorted(rgb)[1] < 60 else "other"


async def scroll_to(session: PlaywrightBrowserSession, y: int) -> None:
    await session.cdp.send("Runtime.evaluate", {"expression": f"window.scrollTo(0, {y})"})
    await asyncio.sleep(0.2)


async def test_full_viewport_capture(session: PlaywrightBrowserSession) -> None:
    image = await source_for(session).grab(None)
    assert image.size == Size(1280, 720)
    assert image.zone == Zone(0, 0, 1280, 720)
    assert image.dpr == 1.0
    assert image.tab_id == session.tab_id


async def test_zone_capture_size_and_content(session: PlaywrightBrowserSession) -> None:
    image = await source_for(session).grab(RED)
    assert image.size == Size(400, 300)
    assert dominant(center_rgb(image)) == "red"
    blue = await source_for(session).grab(Zone(600, 50, 400, 300))
    assert dominant(center_rgb(blue)) == "blue"


async def test_zone_stays_fixed_to_viewport_after_scroll(
    session: PlaywrightBrowserSession,
) -> None:
    await scroll_to(session, 1000)
    image = await source_for(session).grab(RED)
    # Le rectangle (100, 50) du viewport montre maintenant le document en (100, 1050) : vert.
    assert dominant(center_rgb(image)) == "green"
    assert image.scroll.y == 1000
    assert image.scroll.x == 0


async def test_sequence_continues_across_navigation(
    session: PlaywrightBrowserSession, grid_url: str
) -> None:
    bus = FrameBus(500)
    service = CaptureService(source_for(session), SystemClock(), bus, fps=20)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.5)
    await session.cdp.send("Page.navigate", {"url": grid_url + "?second"})
    await asyncio.sleep(1.0)
    service.stop()
    await asyncio.wait_for(task, 5)
    seqs = [f.seq for f in bus.frames()]
    assert len(seqs) > 10
    assert seqs == list(range(seqs[0], seqs[0] + len(seqs)))
    assert session.current_url().endswith("?second")


def test_grid_asset_exists() -> None:
    assert (Path(__file__).parents[1] / "assets" / "grid.html").is_file()
