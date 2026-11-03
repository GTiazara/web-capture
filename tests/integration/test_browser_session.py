from __future__ import annotations

import asyncio

import pytest

from web_capture.adapters.browser.playwright_session import PlaywrightBrowserSession
from web_capture.adapters.clock import SystemClock
from web_capture.domain.errors import NavigationError
from web_capture.domain.frame import Size

pytestmark = pytest.mark.integration


async def test_cdp_channel_get_layout_metrics(session: PlaywrightBrowserSession) -> None:
    metrics = await session.cdp.send("Page.getLayoutMetrics")
    assert metrics["cssLayoutViewport"]["clientHeight"] == 720
    assert session.tab_id


async def test_session_opens_url(session: PlaywrightBrowserSession, grid_url: str) -> None:
    assert session.current_url() == grid_url


async def test_unreachable_url_raises_navigation_error() -> None:
    s = PlaywrightBrowserSession(
        "http://127.0.0.1:9/", headless=True, viewport=Size(800, 600), navigation_timeout_ms=5000
    )
    with pytest.raises(NavigationError, match="127.0.0.1:9"):
        await s.start()


async def test_tab_close_is_detected(session: PlaywrightBrowserSession) -> None:
    await session.cdp.send("Page.close")
    await asyncio.wait_for(session.wait_closed(), 5)


async def test_system_clock_sleep_until_can_be_woken() -> None:
    clock = SystemClock()
    wake = asyncio.Event()
    asyncio.get_running_loop().call_later(0.05, wake.set)
    start = clock.monotonic_ns()
    await clock.sleep_until(start + 5_000_000_000, wake)
    assert clock.monotonic_ns() - start < 1_000_000_000
