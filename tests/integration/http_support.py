from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from dataclasses import dataclass

import aiohttp
import pytest
from aiohttp import web

from web_capture.adapters.clock import SystemClock
from web_capture.adapters.http.app import create_app, start_server
from web_capture.adapters.http.codec import decode_frame
from web_capture.adapters.http.keys import ServerSettings
from web_capture.application.capture_service import CaptureService
from web_capture.application.control.handlers import CaptureHandlers
from web_capture.application.control.registry import CommandRegistry
from web_capture.application.control.service import ControlService
from web_capture.application.frame_bus import FrameBus
from web_capture.domain.frame import CapturedImage, Point, Size, Zone

pytestmark = pytest.mark.integration

HOST = "127.0.0.1"


def free_port() -> int:
    with socket.socket() as s:
        s.bind((HOST, 0))
        return int(s.getsockname()[1])


class BlobSource:
    def __init__(self, payload_size: int, payload: bytes | None = None) -> None:
        self.payload = payload or b"\xff\xd8" + b"\0" * payload_size

    @property
    def viewport(self) -> Size:
        return Size(1280, 720)

    async def grab(self, zone: Zone | None) -> CapturedImage:
        z = zone or Zone.full(self.viewport)
        return CapturedImage(
            self.payload, "T", z, 1.0, Point(0, 0), Size(int(z.width), int(z.height))
        )


@dataclass
class Server:
    url: str
    ws_url: str
    capture: CaptureService
    bus: FrameBus
    runner: web.AppRunner


@pytest.fixture
async def server(request: pytest.FixtureRequest) -> AsyncIterator[Server]:
    params = getattr(request, "param", {})
    port = params.get("port") or free_port()
    bus = FrameBus(60)
    capture = CaptureService(
        BlobSource(params.get("payload", 1000), params.get("jpeg")),
        SystemClock(),
        bus,
        fps=params.get("fps", 20),
    )
    registry = CommandRegistry()
    CaptureHandlers(capture, bus, lambda: "about:blank").register(registry)
    settings = ServerSettings(HOST, port, send_timeout_s=params.get("send_timeout", 10.0))
    runner = await start_server(create_app(bus, ControlService(registry), settings), HOST, port)
    task = asyncio.create_task(capture.run())
    try:
        yield Server(f"http://{HOST}:{port}", f"ws://{HOST}:{port}", capture, bus, runner)
    finally:
        capture.stop()
        bus.close()
        await task
        await runner.cleanup()


async def receive_frames(ws: aiohttp.ClientWebSocketResponse, n: int) -> list[dict[str, object]]:
    headers = []
    for _ in range(n):
        msg = await asyncio.wait_for(ws.receive(), 5)
        assert msg.type == aiohttp.WSMsgType.BINARY
        header, _jpeg = decode_frame(msg.data)
        headers.append(header)
    return headers
