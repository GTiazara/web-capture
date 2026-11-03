from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Browser, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError

from web_capture.adapters.browser.playwright_cdp import PlaywrightCdpChannel
from web_capture.domain.errors import NavigationError
from web_capture.domain.frame import Size

log = logging.getLogger(__name__)


class PlaywrightBrowserSession:
    """Lance un Chromium dédié et ouvre l'onglet cible ; signale la fin de session."""

    def __init__(
        self,
        url: str,
        *,
        headless: bool,
        viewport: Size,
        navigation_timeout_ms: float = 30_000,
    ) -> None:
        self._url = url
        self._headless = headless
        self._viewport = viewport
        self._navigation_timeout_ms = navigation_timeout_ms
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None
        self._cdp: PlaywrightCdpChannel | None = None
        self._tab_id = ""
        self._closed = asyncio.Event()

    @property
    def tab_id(self) -> str:
        return self._tab_id

    @property
    def cdp(self) -> PlaywrightCdpChannel:
        if self._cdp is None:
            raise RuntimeError("session navigateur non démarrée")
        return self._cdp

    def current_url(self) -> str:
        return self._page.url if self._page is not None else ""

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.launch(headless=self._headless)
            self._browser.on("disconnected", lambda _: self._mark_closed("navigateur terminé"))
            context = await self._browser.new_context(
                viewport={"width": self._viewport.width, "height": self._viewport.height}
            )
            page = await context.new_page()
            self._page = page
            page.on("close", lambda _: self._mark_closed("onglet fermé"))
            try:
                await page.goto(self._url, timeout=self._navigation_timeout_ms)
            except PlaywrightError as exc:
                first_line = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
                raise NavigationError(
                    f"navigation impossible vers {self._url} : {first_line}"
                ) from exc
            session = await context.new_cdp_session(page)
            self._cdp = PlaywrightCdpChannel(session)
            info = await self._cdp.send("Target.getTargetInfo")
            self._tab_id = str(info["targetInfo"]["targetId"])
        except BaseException:
            await self.close()
            raise

    def _mark_closed(self, reason: str) -> None:
        if not self._closed.is_set():
            log.info("fin de session navigateur : %s", reason)
            self._closed.set()

    async def wait_closed(self) -> None:
        await self._closed.wait()

    async def close(self) -> None:
        browser, playwright = self._browser, self._playwright
        self._browser = None
        self._playwright = None
        if browser is not None:
            try:
                await browser.close()
            except PlaywrightError:
                log.debug("navigateur déjà fermé")
        if playwright is not None:
            await playwright.stop()
        self._closed.set()
