from __future__ import annotations

import json

from aiohttp import WSMsgType, web

from web_capture.adapters.http.keys import CONTROL, SETTINGS, SOCKETS
from web_capture.adapters.http.origin import is_origin_allowed


async def control_handler(request: web.Request) -> web.StreamResponse:
    settings = request.app[SETTINGS]
    if not is_origin_allowed(request.headers.get("Origin"), settings.host, settings.port):
        raise web.HTTPForbidden(text="origine refusée")

    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=64 * 1024)
    await ws.prepare(request)
    request.app[SOCKETS].add(ws)
    control = request.app[CONTROL]
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                raw = json.loads(msg.data)
            except ValueError:
                response = {"id": None, "ok": False, "error": "JSON invalide"}
            else:
                response = await control.execute(raw)
            await ws.send_json(response)
        elif msg.type == WSMsgType.BINARY:
            await ws.send_json({"id": None, "ok": False, "error": "message texte JSON attendu"})
    return ws
