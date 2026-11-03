from __future__ import annotations

import weakref
from collections.abc import Callable
from dataclasses import dataclass

from aiohttp import web

from web_capture.application.control.service import ControlService
from web_capture.application.frame_bus import FrameBus


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int
    send_timeout_s: float = 10.0


class OpenSockets:
    def __init__(self) -> None:
        self._items: weakref.WeakSet[web.WebSocketResponse] = weakref.WeakSet()

    def add(self, ws: web.WebSocketResponse) -> None:
        self._items.add(ws)

    def snapshot(self) -> list[web.WebSocketResponse]:
        return list(self._items)


BUS = web.AppKey("bus", FrameBus)
CONTROL = web.AppKey("control", ControlService)
SETTINGS = web.AppKey("settings", ServerSettings)
SOCKETS = web.AppKey("sockets", OpenSockets)


def abort_transport(request: web.Request) -> Callable[[], None]:
    def _abort() -> None:
        transport = request.transport
        if transport is not None:
            transport.abort()

    return _abort
