from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from web_capture.domain.errors import InvalidCommandError
from web_capture.domain.frame import Zone


@dataclass(frozen=True, slots=True)
class SetFps:
    fps: object


@dataclass(frozen=True, slots=True)
class SetZone:
    zone: Zone | None


@dataclass(frozen=True, slots=True)
class Pause:
    pass


@dataclass(frozen=True, slots=True)
class Resume:
    pass


@dataclass(frozen=True, slots=True)
class GetStatus:
    pass


@dataclass(frozen=True, slots=True)
class StartRecording:
    pass


@dataclass(frozen=True, slots=True)
class StopRecording:
    pass


def _require(raw: Mapping[str, Any], key: str) -> Any:
    if key not in raw:
        raise InvalidCommandError(f"champ '{key}' requis")
    return raw[key]


def parse_set_fps(raw: Mapping[str, Any]) -> SetFps:
    return SetFps(_require(raw, "fps"))


def parse_zone(value: Any) -> Zone | None:
    if value is None:
        return None
    keys = ("x", "y", "width", "height")
    if not isinstance(value, Mapping) or any(k not in value for k in keys):
        raise InvalidCommandError("zone attendue : {x, y, width, height} ou null")
    nums = [value[k] for k in keys]
    if any(isinstance(n, bool) or not isinstance(n, int | float) for n in nums):
        raise InvalidCommandError("zone : x, y, width et height doivent être des nombres")
    return Zone(*(float(n) for n in nums))


def parse_set_zone(raw: Mapping[str, Any]) -> SetZone:
    return SetZone(parse_zone(_require(raw, "zone")))


def parse_pause(_: Mapping[str, Any]) -> Pause:
    return Pause()


def parse_resume(_: Mapping[str, Any]) -> Resume:
    return Resume()


def parse_status(_: Mapping[str, Any]) -> GetStatus:
    return GetStatus()


def parse_start_recording(_: Mapping[str, Any]) -> StartRecording:
    return StartRecording()


def parse_stop_recording(_: Mapping[str, Any]) -> StopRecording:
    return StopRecording()
