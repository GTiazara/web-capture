from __future__ import annotations

import io

import aiohttp
import pytest
from PIL import Image
from playwright.async_api import async_playwright

from tests.integration.http_support import Server, server

__all__ = ["server"]

pytestmark = pytest.mark.integration


def make_jpeg() -> bytes:
    image_buffer = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 30, 20)).save(image_buffer, "JPEG")
    return image_buffer.getvalue()


async def test_control_correlation_errors_and_connection_kept(server: Server) -> None:
    async with (
        aiohttp.ClientSession() as session,
        session.ws_connect(server.ws_url + "/control") as ws,
    ):
        await ws.send_json({"id": 7, "cmd": "status"})
        resp = await ws.receive_json(timeout=5)
        assert resp["id"] == 7 and resp["ok"] is True and resp["state"] == "running"

        await ws.send_json({"id": 8, "cmd": "explode"})
        resp = await ws.receive_json(timeout=5)
        assert resp["id"] == 8 and resp["ok"] is False

        await ws.send_str("pas du json")
        resp = await ws.receive_json(timeout=5)
        assert resp["ok"] is False and resp["id"] is None

        await ws.send_bytes(b"\x00")
        resp = await ws.receive_json(timeout=5)
        assert resp["ok"] is False

        await ws.send_json({"id": 9, "cmd": "set_fps", "fps": 5})
        resp = await ws.receive_json(timeout=5)
        assert resp == {"id": 9, "ok": True, "fps": 5.0}
        assert server.capture.fps == 5
        assert not ws.closed


@pytest.mark.parametrize("server", [{"jpeg": make_jpeg()}], indirect=True)
async def test_viewer_displays_frames_and_fps_error(server: Server) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(server.url)
        await page.wait_for_function("document.getElementById('seq').textContent !== '-'")
        assert await page.locator("#seq").inner_text() != "-"
        await page.locator("#fps-input").fill("120")
        await page.locator("#fps-apply").click()
        await page.wait_for_function("document.getElementById('error').textContent.length > 0")
        assert "FPS" in await page.locator("#error").inner_text()
        assert not errors
        await browser.close()


@pytest.mark.parametrize("server", [{"jpeg": make_jpeg()}], indirect=True)
async def test_viewer_reconnects_after_server_restart(server: Server) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(server.url)
        await page.wait_for_function("document.getElementById('seq').textContent !== '-'")
        previous_seq = int(await page.locator("#seq").inner_text())
        await server.runner.cleanup()
        await page.wait_for_function(
            "document.getElementById('conn').classList.contains('down')", timeout=5000
        )
        await server.runner.setup()
        from aiohttp import web

        settings_host = "127.0.0.1"
        await web.TCPSite(server.runner, settings_host, int(server.url.rsplit(":", 1)[1])).start()
        await page.wait_for_function(
            "document.getElementById('conn').classList.contains('up')", timeout=10000
        )
        await page.wait_for_function(
            "seq => Number(document.getElementById('seq').textContent) > seq",
            arg=previous_seq,
            timeout=5000,
        )
        await browser.close()
