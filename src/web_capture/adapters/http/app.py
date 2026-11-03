from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path

from aiohttp import WSCloseCode, web

from web_capture.adapters.http.control_ws import control_handler
from web_capture.adapters.http.frames_ws import frames_handler
from web_capture.adapters.http.keys import (
    BUS,
    CONTROL,
    SETTINGS,
    SOCKETS,
    OpenSockets,
    ServerSettings,
)
from web_capture.application.control.service import ControlService
from web_capture.application.frame_bus import FrameBus

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


async def viewer(_: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "viewer.html")


async def _close_sockets(app: web.Application) -> None:
    for ws in app[SOCKETS].snapshot():
        with contextlib.suppress(Exception):
            await asyncio.wait_for(ws.close(code=WSCloseCode.GOING_AWAY), 2)


def create_app(bus: FrameBus, control: ControlService, settings: ServerSettings) -> web.Application:
    app = web.Application()
    app[BUS] = bus
    app[CONTROL] = control
    app[SETTINGS] = settings
    app[SOCKETS] = OpenSockets()
    app.router.add_get("/", viewer)
    app.router.add_get("/frames", frames_handler)
    app.router.add_get("/control", control_handler)
    app.on_shutdown.append(_close_sockets)
    return app


async def start_server(app: web.Application, host: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(app, handle_signals=False)
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    log.info("serveur à l'écoute sur http://%s:%d/", host, port)
    return runner
