from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from playwright.async_api import CDPSession


class PlaywrightCdpChannel:
    def __init__(self, session: CDPSession) -> None:
        self._session = session

    async def send(self, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        result = await self._session.send(method, dict(params) if params else None)
        return dict(result)
