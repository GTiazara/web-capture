from __future__ import annotations

import base64
from typing import Any

from web_capture.adapters.capture.jpeg import jpeg_size
from web_capture.application.ports import CdpChannel
from web_capture.domain.frame import CapturedImage, Point, Size, Zone


class CdpFrameSource:
    """Capture l'onglet via `Page.captureScreenshot` ; la zone reste fixe dans le viewport."""

    def __init__(self, cdp: CdpChannel, tab_id: str, viewport: Size, jpeg_quality: int) -> None:
        self._cdp = cdp
        self._tab_id = tab_id
        self._viewport = viewport
        self._quality = jpeg_quality

    @property
    def viewport(self) -> Size:
        return self._viewport

    async def grab(self, zone: Zone | None) -> CapturedImage:
        metrics = await self._cdp.send("Page.getLayoutMetrics")
        css_vv = metrics["cssVisualViewport"]
        scroll = Point(float(css_vv["pageX"]), float(css_vv["pageY"]))
        params: dict[str, Any] = {
            "format": "jpeg",
            "quality": self._quality,
            "captureBeyondViewport": False,
        }
        if zone is not None:
            # `clip` est exprimé en coordonnées document : on ajoute le scroll courant.
            params["clip"] = {
                "x": zone.x + scroll.x,
                "y": zone.y + scroll.y,
                "width": zone.width,
                "height": zone.height,
                "scale": 1,
            }
        result = await self._cdp.send("Page.captureScreenshot", params)
        data = base64.b64decode(result["data"])
        size = jpeg_size(data)
        effective = zone or Zone.full(self._viewport)
        return CapturedImage(
            data=data,
            tab_id=self._tab_id,
            zone=effective,
            dpr=size.width / effective.width,
            scroll=scroll,
            size=size,
        )
