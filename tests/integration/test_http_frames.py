from __future__ import annotations

import asyncio

import aiohttp
import pytest

from tests.integration.http_support import Server, receive_frames, server

__all__ = ["server"]

pytestmark = pytest.mark.integration


async def test_two_simultaneous_subscribers(server: Server) -> None:
    async with (
        aiohttp.ClientSession() as session,
        session.ws_connect(server.ws_url + "/frames") as a,
        session.ws_connect(server.ws_url + "/frames?mode=all") as b,
    ):
        ha = await receive_frames(a, 3)
        hb = await receive_frames(b, 5)
        assert all(h["dropped"] == 0 for h in ha + hb)
        seqs_b = [h["seq"] for h in hb]
        assert seqs_b == list(range(seqs_b[0], seqs_b[0] + 5))  # type: ignore[call-overload]
        assert server.bus.subscriber_counts() == {"latest": 1, "all": 1}


async def test_unknown_mode_refused(server: Server) -> None:
    async with aiohttp.ClientSession() as session:
        with pytest.raises(aiohttp.WSServerHandshakeError) as err:
            await session.ws_connect(server.ws_url + "/frames?mode=burst")
        assert err.value.status == 400


@pytest.mark.parametrize("path", ["/frames", "/control"])
async def test_foreign_origin_refused(server: Server, path: str) -> None:
    async with aiohttp.ClientSession() as session:
        with pytest.raises(aiohttp.WSServerHandshakeError) as err:
            await session.ws_connect(server.ws_url + path, origin="http://example.com")
        assert err.value.status == 403


async def test_same_origin_and_no_origin_accepted(server: Server) -> None:
    async with aiohttp.ClientSession() as session:
        for origin in (None, server.url, server.url.replace("127.0.0.1", "localhost")):
            async with session.ws_connect(server.ws_url + "/frames", origin=origin) as ws:
                assert len(await receive_frames(ws, 1)) == 1


@pytest.mark.parametrize(
    "server", [{"payload": 1_000_000, "fps": 20, "send_timeout": 1.0}], indirect=True
)
async def test_blocked_subscriber_does_not_slow_others(server: Server) -> None:
    async with (
        aiohttp.ClientSession() as session,
        session.ws_connect(server.ws_url + "/frames?mode=all") as blocked,
        session.ws_connect(server.ws_url + "/frames?mode=all") as healthy,
    ):
        loop = asyncio.get_running_loop()
        start = loop.time()
        received = 0
        while loop.time() - start < 3:
            msg = await asyncio.wait_for(healthy.receive(), 5)
            assert msg.type == aiohttp.WSMsgType.BINARY
            received += 1
        assert received >= 45
        assert server.capture.effective_fps() >= 17
        # L'abonné qui ne lit jamais est déconnecté par le serveur après le délai d'envoi.
        while True:
            msg = await asyncio.wait_for(blocked.receive(), 10)
            if msg.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.ERROR,
            ):
                break
