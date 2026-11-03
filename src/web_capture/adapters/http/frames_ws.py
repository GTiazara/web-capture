from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable

from aiohttp import web

from web_capture.adapters.http.codec import encode_frame
from web_capture.adapters.http.keys import BUS, SETTINGS, SOCKETS, abort_transport
from web_capture.adapters.http.origin import is_origin_allowed
from web_capture.application.delivery import POLICIES
from web_capture.application.frame_bus import Subscription

log = logging.getLogger(__name__)


async def _pump(
    ws: web.WebSocketResponse,
    sub: Subscription,
    send_timeout_s: float,
    abort: Callable[[], None],
) -> None:
    while (delivery := await sub.next()) is not None:
        message = encode_frame(delivery.frame, delivery.dropped)
        try:
            await asyncio.wait_for(ws.send_bytes(message), send_timeout_s)
        except TimeoutError:
            log.warning("abonné /frames trop lent depuis %.1f s : déconnexion", send_timeout_s)
            abort()
            return
        except ConnectionError:
            return
    with contextlib.suppress(Exception):
        await asyncio.wait_for(ws.close(), 2)


async def frames_handler(request: web.Request) -> web.StreamResponse:
    settings = request.app[SETTINGS]
    if not is_origin_allowed(request.headers.get("Origin"), settings.host, settings.port):
        raise web.HTTPForbidden(text="origine refusée")
    mode = request.query.get("mode", "latest")
    policy_cls = POLICIES.get(mode)
    if policy_cls is None:
        raise web.HTTPBadRequest(text=f"mode inconnu : {mode} (attendu : latest ou all)")

    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=4096)
    await ws.prepare(request)
    request.app[SOCKETS].add(ws)
    sub = request.app[BUS].subscribe(policy_cls())
    sender = asyncio.create_task(_pump(ws, sub, settings.send_timeout_s, abort_transport(request)))
    try:
        async for _ in ws:
            pass
    finally:
        sender.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sender
        sub.close()
    return ws
