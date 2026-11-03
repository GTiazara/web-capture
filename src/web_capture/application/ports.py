from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from web_capture.domain.frame import CapturedImage, Size, Zone


class CdpChannel(Protocol):
    """Transport de commandes Chrome DevTools Protocol vers l'onglet cible."""

    async def send(
        self, method: str, params: Mapping[str, Any] | None = None
    ) -> dict[str, Any]: ...


class FrameSource(Protocol):
    @property
    def viewport(self) -> Size: ...

    async def grab(self, zone: Zone | None) -> CapturedImage: ...


class Clock(Protocol):
    def monotonic_ns(self) -> int: ...

    def wall_ms(self) -> int: ...

    async def sleep_until(self, deadline_ns: int, wake: asyncio.Event | None = None) -> None:
        """Attend l'échéance, ou retourne plus tôt si `wake` est positionné."""
        ...


class VideoEncoder(Protocol):
    async def open(self, path: Path, fps: float) -> None:
        """Lève EncoderUnavailableError si aucun encodeur n'est disponible."""
        ...

    async def write(self, jpeg: bytes) -> None: ...

    async def close(self) -> None: ...


class BrowserSession(Protocol):
    @property
    def tab_id(self) -> str: ...

    @property
    def cdp(self) -> CdpChannel: ...

    def current_url(self) -> str: ...

    async def wait_closed(self) -> None: ...

    async def close(self) -> None: ...
