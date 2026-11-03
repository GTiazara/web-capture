from __future__ import annotations

import asyncio
import io
import itertools
import os
import signal
import socket
import sys
from pathlib import Path

import aiohttp
import imageio_ffmpeg
import pytest
from PIL import Image
from playwright.async_api import async_playwright

from web_capture.adapters.http.codec import decode_frame

pytestmark = [pytest.mark.integration, pytest.mark.ffmpeg]

ROOT = Path(__file__).parents[2]
GRID = ROOT / "tests" / "assets" / "grid.html"


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def command(
    ws: aiohttp.ClientWebSocketResponse,
    msg_id: int,
    cmd: str,
    **kwargs: object,
) -> dict:
    await ws.send_json({"id": msg_id, "cmd": cmd, **kwargs})
    return await ws.receive_json(timeout=5)


async def drain_frames(ws: aiohttp.ClientWebSocketResponse, stop: asyncio.Event) -> list[dict]:
    frames: list[dict] = []
    while not stop.is_set():
        try:
            msg = await asyncio.wait_for(ws.receive(), timeout=0.25)
        except TimeoutError:
            continue
        if msg.type is aiohttp.WSMsgType.BINARY:
            header, jpeg = decode_frame(msg.data)
            if header["zone"]["width"] == 400:
                image = Image.open(io.BytesIO(jpeg))
                assert image.size == (400, 300)
                frames.append(header)
        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
            break
    return frames


async def test_full_live_capture_viewer_subscribers_and_mp4(tmp_path: Path) -> None:
    port = unused_port()
    output = tmp_path / "recordings"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "web_capture",
        f"browser.url={GRID.as_uri()}",
        "browser.headless=true",
        f"server.port={port}",
        f"recording.output_dir={output}",
        "capture.fps=10",
        cwd=ROOT,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    ws_base = f"ws://127.0.0.1:{port}"
    try:
        async with aiohttp.ClientSession() as session:
            for _ in range(100):
                if proc.returncode is not None:
                    stdout, stderr = await proc.communicate()
                    pytest.fail(f"module exited early: {stdout!r} {stderr!r}")
                try:
                    async with session.get(base, timeout=0.2) as response:
                        if response.status == 200:
                            break
                except (aiohttp.ClientError, TimeoutError):
                    await asyncio.sleep(0.1)
            else:
                pytest.fail("module did not start HTTP server")

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(base)
                await page.wait_for_function(
                    "document.getElementById('seq').textContent !== '-'", timeout=10_000
                )
                assert await page.locator("#conn").inner_text() == "connecté"

                async with (
                    session.ws_connect(f"{ws_base}/control") as control,
                    session.ws_connect(f"{ws_base}/frames?mode=latest") as latest,
                    session.ws_connect(f"{ws_base}/frames?mode=all") as all_frames,
                ):
                    assert (await command(control, 1, "set_fps", fps=5))["ok"] is True
                    await asyncio.sleep(0.5)
                    assert (await command(control, 2, "set_fps", fps=10))["ok"] is True
                    zone = {"x": 100, "y": 50, "width": 400, "height": 300}
                    assert (await command(control, 3, "set_zone", zone=zone))["ok"] is True

                    stop_readers = asyncio.Event()
                    latest_task = asyncio.create_task(drain_frames(latest, stop_readers))
                    all_task = asyncio.create_task(drain_frames(all_frames, stop_readers))
                    start = await command(control, 4, "start_recording")
                    assert start["ok"] is True
                    await asyncio.sleep(10)
                    stop = await command(control, 5, "stop_recording")
                    assert stop["ok"] is True
                    stop_readers.set()
                    latest_frames, all_received = await asyncio.gather(latest_task, all_task)
                    assert len(latest_frames) >= 70
                    assert len(all_received) >= 70
                    assert all(h["zone"] == zone for h in latest_frames + all_received)
                    assert all(h["dropped"] == 0 for h in latest_frames)
                    assert all(a["seq"] < b["seq"] for a, b in itertools.pairwise(all_received))
                    assert await page.locator("#seq").inner_text() != "-"
                    path = Path(stop["path"])
                    assert path.is_file()

                await browser.close()
        proc.send_signal(signal.SIGINT)
        await asyncio.wait_for(proc.wait(), 20)
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        await proc.communicate()

    assert proc.returncode == 0
    videos = list(output.glob("*.mp4"))
    assert len(videos) == 1
    frames, duration = imageio_ffmpeg.count_frames_and_secs(str(videos[0]))
    assert 9.5 <= duration <= 10.5
    assert 95 <= frames <= 105
