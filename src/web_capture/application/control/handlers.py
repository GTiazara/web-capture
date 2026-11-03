from __future__ import annotations

from collections.abc import Callable

from web_capture.application.capture_service import CaptureService
from web_capture.application.control.commands import (
    GetStatus,
    Pause,
    Resume,
    SetFps,
    SetZone,
    StartRecording,
    StopRecording,
    parse_pause,
    parse_resume,
    parse_set_fps,
    parse_set_zone,
    parse_start_recording,
    parse_status,
    parse_stop_recording,
)
from web_capture.application.control.registry import CommandRegistry, Result
from web_capture.application.frame_bus import FrameBus
from web_capture.application.recording_service import RecordingService
from web_capture.domain.errors import InvalidZoneError
from web_capture.domain.frame import Zone


def zone_dict(zone: Zone | None) -> dict[str, float] | None:
    if zone is None:
        return None
    return {"x": zone.x, "y": zone.y, "width": zone.width, "height": zone.height}


class CaptureHandlers:
    def __init__(
        self,
        capture: CaptureService,
        bus: FrameBus,
        url_provider: Callable[[], str],
        recording: RecordingService | None = None,
    ) -> None:
        self._capture = capture
        self._bus = bus
        self._url = url_provider
        self._recording = recording

    async def set_fps(self, cmd: SetFps) -> Result:
        return {"fps": self._capture.set_fps(cmd.fps)}

    async def set_zone(self, cmd: SetZone) -> Result:
        if self._recording is not None and self._recording.active:
            raise InvalidZoneError("zone non modifiable pendant un enregistrement")
        return {"zone": zone_dict(self._capture.set_zone(cmd.zone))}

    async def pause(self, _: Pause) -> Result:
        self._capture.pause()
        return {"state": "paused"}

    async def resume(self, _: Resume) -> Result:
        self._capture.resume()
        return {"state": "running"}

    async def status(self, _: GetStatus) -> Result:
        result: Result = {
            "url": self._url(),
            "state": "paused" if self._capture.paused else "running",
            "fps": self._capture.fps,
            "effective_fps": round(self._capture.effective_fps(), 2),
            "zone": zone_dict(self._capture.zone),
            "last_seq": self._capture.last_seq,
            "subscribers": {"latest": 0, "all": 0, **self._bus.subscriber_counts()},
        }
        if self._recording is not None:
            result["recording"] = self._recording.status()
        return result

    async def start_recording(self, _: StartRecording) -> Result:
        assert self._recording is not None
        path = await self._recording.start()
        return {"file": path.name}

    async def stop_recording(self, _: StopRecording) -> Result:
        assert self._recording is not None
        path = await self._recording.stop()
        status = self._recording.status()
        return {
            "path": str(path.resolve()),
            "frames_written": status["frames_written"],
            "frames_dropped": status["frames_dropped"],
        }

    def register(self, registry: CommandRegistry) -> None:
        registry.register("set_fps", parse_set_fps, self.set_fps)
        registry.register("set_zone", parse_set_zone, self.set_zone)
        registry.register("pause", parse_pause, self.pause)
        registry.register("resume", parse_resume, self.resume)
        registry.register("status", parse_status, self.status)
        if self._recording is not None:
            registry.register("start_recording", parse_start_recording, self.start_recording)
            registry.register("stop_recording", parse_stop_recording, self.stop_recording)
