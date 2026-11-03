from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from web_capture.adapters.browser.playwright_session import PlaywrightBrowserSession
from web_capture.domain.frame import Size

ASSETS = Path(__file__).parents[1] / "assets"
VIEWPORT = Size(1280, 720)


@pytest.fixture
def grid_url() -> str:
    return (ASSETS / "grid.html").resolve().as_uri()


@pytest.fixture
async def session(grid_url: str) -> AsyncIterator[PlaywrightBrowserSession]:
    s = PlaywrightBrowserSession(grid_url, headless=True, viewport=VIEWPORT)
    await s.start()
    try:
        yield s
    finally:
        await s.close()
