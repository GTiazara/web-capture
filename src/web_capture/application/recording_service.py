from __future__ import annotations

import asyncio
import contextlib
import enum
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from web_capture.application.frame_bus import FrameBus
from web_capture.application.ports import Clock, VideoEncoder
from web_capture.domain.errors import RecordingError

log = logging.getLogger(__name__)

NS_PER_S = 1_000_000_000


class RecordingState(enum.Enum):
    IDLE = "idle"
    RECORDING = "recording"
    FINALIZING = "finalizing"


_TRANSITIONS: dict[RecordingState, frozenset[RecordingState]] = {
    RecordingState.IDLE: frozenset({RecordingState.RECORDING}),
    RecordingState.RECORDING: frozenset({RecordingState.FINALIZING}),
    RecordingState.FINALIZING: frozenset({RecordingState.IDLE}),
}


class RecordingService:
    """Enregistre le flux à cadence constante en rééchantillonnant la dernière image du bus."""

    def __init__(
        self,
        bus: FrameBus,
        encoder: VideoEncoder,
        clock: Clock,
        output_dir: Path,
        fps_provider: Callable[[], float],
        *,
        queue_seconds: float = 2.0,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._bus = bus
        self._encoder = encoder
        self._clock = clock
        self._output_dir = output_dir
        self._fps_provider = fps_provider
        self._queue_seconds = queue_seconds
        self._now = now
        self._state = RecordingState.IDLE
        self._path: Path | None = None
        self._fps = 0.0
        self._written = 0
        self._dropped = 0
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._stop = asyncio.Event()
        self._ticker: asyncio.Task[None] | None = None
        self._writer: asyncio.Task[None] | None = None
        self._writer_error: BaseException | None = None

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def active(self) -> bool:
        return self._state is not RecordingState.IDLE

    def status(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "file": str(self._path) if self._path else None,
            "fps": self._fps if self.active else None,
            "frames_written": self._written,
            "frames_dropped": self._dropped,
        }

    def _transition(self, target: RecordingState) -> None:
        if target not in _TRANSITIONS[self._state]:
            raise RecordingError(f"transition invalide : {self._state.value} -> {target.value}")
        self._state = target

    def _new_path(self) -> Path:
        stamp = self._now().strftime("%Y%m%d-%H%M%S")
        path = self._output_dir / f"capture-{stamp}.mp4"
        index = 1
        while path.exists():
            path = self._output_dir / f"capture-{stamp}-{index}.mp4"
            index += 1
        return path

    async def start(self) -> Path:
        if self._state is not RecordingState.IDLE:
            raise RecordingError("un enregistrement est déjà en cours")
        fps = self._fps_provider()
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._new_path()
        await self._encoder.open(path, fps)
        self._transition(RecordingState.RECORDING)
        self._path, self._fps = path, fps
        self._written = self._dropped = 0
        self._writer_error = None
        self._queue = asyncio.Queue(maxsize=max(1, round(fps * self._queue_seconds)))
        self._stop = asyncio.Event()
        self._writer = asyncio.create_task(self._write_loop())
        self._ticker = asyncio.create_task(self._tick_loop())
        log.info("enregistrement démarré : %s (%.2f FPS)", path, fps)
        return path

    async def stop(self) -> Path:
        if self._state is not RecordingState.RECORDING or self._path is None:
            raise RecordingError("aucun enregistrement en cours")
        self._transition(RecordingState.FINALIZING)
        path = self._path
        try:
            self._stop.set()
            if self._ticker is not None:
                await self._ticker
            await self._queue.put(None)
            if self._writer is not None:
                await self._writer
            await self._encoder.close()
        finally:
            self._transition(RecordingState.IDLE)
        if self._writer_error is not None:
            raise RecordingError(f"échec d'encodage : {self._writer_error}")
        log.info(
            "enregistrement finalisé : %s (%d images, %d perdues)",
            path,
            self._written,
            self._dropped,
        )
        return path

    async def _tick_loop(self) -> None:
        period = NS_PER_S / self._fps
        start = self._clock.monotonic_ns()
        emitted = 0
        while not self._stop.is_set():
            # Une image par pas de temps écoulé : duplication si la capture est plus lente.
            due = int((self._clock.monotonic_ns() - start) / period) + 1
            latest = self._bus.latest()
            if latest is not None:
                for _ in range(due - emitted):
                    self._enqueue(latest.data)
            emitted = due
            await self._clock.sleep_until(start + round(due * period), self._stop)

    def _enqueue(self, data: bytes) -> None:
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:
            self._dropped += 1

    async def _write_loop(self) -> None:
        while (data := await self._queue.get()) is not None:
            if self._writer_error is not None:
                continue
            try:
                await self._encoder.write(data)
                self._written += 1
            except Exception as exc:
                log.error("échec d'écriture vers l'encodeur : %s", exc)
                self._writer_error = exc

    async def aclose(self) -> None:
        """Finalise l'enregistrement en cours, s'il y en a un (arrêt du module)."""
        if self._state is RecordingState.RECORDING:
            with contextlib.suppress(RecordingError):
                await self.stop()
