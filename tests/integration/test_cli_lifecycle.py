from __future__ import annotations

import asyncio
import os
import signal
import socket
import sys
from pathlib import Path

import aiohttp
import imageio_ffmpeg
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.ffmpeg]

ROOT = Path(__file__).parents[2]
GRID = ROOT / "tests" / "assets" / "grid.html"


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def test_cli_sigint_finalizes_readable_recording(tmp_path: Path) -> None:
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
    url = f"http://127.0.0.1:{port}"
    try:
        async with aiohttp.ClientSession() as session:
            for _ in range(100):
                if proc.returncode is not None:
                    stdout, stderr = await proc.communicate()
                    pytest.fail(f"module exited early: {stdout!r} {stderr!r}")
                try:
                    async with session.get(url, timeout=0.2) as response:
                        if response.status == 200:
                            break
                except (aiohttp.ClientError, TimeoutError):
                    await asyncio.sleep(0.1)
            else:
                pytest.fail("module did not start HTTP server")
            snippet = """
import asyncio, json, struct
from aiohttp import ClientSession, WSMsgType
async def main():
    async with ClientSession() as session:
        async with session.ws_connect(URL) as ws:
            async for msg in ws:
                if msg.type is WSMsgType.BINARY:
                    (n,) = struct.unpack_from('>I', msg.data)
                    header = json.loads(msg.data[4:4+n])
                    assert header['seq'] >= 0 and msg.data[4+n].to_bytes(1, 'big')
                    return
asyncio.run(main())
""".replace("URL", repr(f"ws://127.0.0.1:{port}/frames?mode=latest"))
            client = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                snippet,
                cwd=ROOT,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            client_out, client_err = await asyncio.wait_for(client.communicate(), 10)
            assert client.returncode == 0, (client_out, client_err)
            async with session.ws_connect(f"ws://127.0.0.1:{port}/control") as ws:
                await ws.send_json({"id": 1, "cmd": "start_recording"})
                response = await ws.receive_json(timeout=5)
                assert response["ok"] is True
                await asyncio.sleep(2.2)
                proc.send_signal(signal.SIGINT)
                await asyncio.wait_for(proc.wait(), 20)
                stdout, stderr = await proc.communicate()
                await ws.close()
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
            await proc.communicate()
    assert proc.returncode == 0
    videos = list(output.glob("*.mp4"))
    assert len(videos) == 1
    frames, duration = imageio_ffmpeg.count_frames_and_secs(str(videos[0]))
    assert frames >= 15
    assert 1.8 <= duration <= 2.8
