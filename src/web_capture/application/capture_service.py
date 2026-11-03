from __future__ import annotations

import asyncio
import logging
from collections import deque

from web_capture.application.frame_bus import FrameBus
from web_capture.application.ports import Clock, FrameSource
from web_capture.domain.frame import Frame, FrameMetadata, Zone
from web_capture.domain.rules import validate_fps, validate_zone

log = logging.getLogger(__name__)

NS_PER_S = 1_000_000_000


class CaptureService:
    """Produit des images à intervalle 1/FPS, sans rattrapage en rafale des échéances manquées."""

    def __init__(
        self,
        source: FrameSource,
        clock: Clock,
        bus: FrameBus,
        *,
        fps: float,
        zone: Zone | None = None,
    ) -> None:
        self._source = source
        self._clock = clock
        self._bus = bus
        self._fps = validate_fps(fps)
        self._zone = validate_zone(zone, source.viewport) if zone is not None else None
        self._seq = 0
        self._resumed = asyncio.Event()
        self._resumed.set()
        self._wake = asyncio.Event()
        self._stopped = False
        self._capture_starts: deque[int] = deque()
        self._consecutive_errors = 0

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def zone(self) -> Zone | None:
        return self._zone

    @property
    def paused(self) -> bool:
        return not self._resumed.is_set()

    @property
    def last_seq(self) -> int | None:
        return self._seq - 1 if self._seq > 0 else None

    def set_fps(self, fps: object) -> float:
        self._fps = validate_fps(fps)
        self._wake.set()
        return self._fps

    def set_zone(self, zone: Zone | None) -> Zone | None:
        self._zone = validate_zone(zone, self._source.viewport) if zone is not None else None
        return self._zone

    def pause(self) -> None:
        self._resumed.clear()
        self._wake.set()

    def resume(self) -> None:
        self._resumed.set()

    def stop(self) -> None:
        self._stopped = True
        self._resumed.set()
        self._wake.set()

    def effective_fps(self) -> float:
        self._trim_window(self._clock.monotonic_ns())
        starts = self._capture_starts
        if len(starts) < 2:
            return 0.0
        return (len(starts) - 1) * NS_PER_S / (starts[-1] - starts[0])

    async def run(self) -> None:
        last_start: int | None = None
        while not self._stopped:
            await self._resumed.wait()
            if self._stopped:
                break
            now = self._clock.monotonic_ns()
            period = round(NS_PER_S / self._fps)
            deadline = now if last_start is None else last_start + period
            if deadline > now:
                self._wake.clear()
                await self._clock.sleep_until(deadline, self._wake)
                if self._wake.is_set() or self._stopped or self.paused:
                    # Réglages modifiés ou pause : on recalcule l'échéance.
                    continue
            last_start = self._clock.monotonic_ns()
            await self._capture_once(last_start)

    async def _capture_once(self, start_ns: int) -> None:
        wall_ms = self._clock.wall_ms()
        try:
            image = await self._source.grab(self._zone)
        except Exception as exc:
            self._consecutive_errors += 1
            if self._consecutive_errors == 1:
                log.warning("échec de capture : %s", exc)
            return
        if self._consecutive_errors:
            log.info("capture rétablie après %d échec(s)", self._consecutive_errors)
            self._consecutive_errors = 0
        end_ns = self._clock.monotonic_ns()
        meta = FrameMetadata(
            seq=self._seq,
            ts_mono_ns=start_ns,
            ts_wall_ms=wall_ms,
            capture_ms=(end_ns - start_ns) / 1e6,
            tab_id=image.tab_id,
            zone=image.zone,
            dpr=image.dpr,
            scroll=image.scroll,
            size=image.size,
            format=image.format,
        )
        self._seq += 1
        self._capture_starts.append(start_ns)
        self._trim_window(end_ns)
        self._bus.publish(Frame(image.data, meta))

    def _trim_window(self, now_ns: int) -> None:
        while self._capture_starts and self._capture_starts[0] < now_ns - NS_PER_S:
            self._capture_starts.popleft()
