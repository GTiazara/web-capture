from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Size:
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Zone:
    """Rectangle en pixels CSS relatifs au viewport."""

    x: float
    y: float
    width: float
    height: float

    @classmethod
    def full(cls, viewport: Size) -> Zone:
        return cls(0, 0, viewport.width, viewport.height)


@dataclass(frozen=True, slots=True)
class CapturedImage:
    """Image brute fournie par une source, avant numérotation et horodatage."""

    data: bytes
    tab_id: str
    zone: Zone
    dpr: float
    scroll: Point
    size: Size
    format: str = "jpeg"


@dataclass(frozen=True, slots=True)
class FrameMetadata:
    seq: int
    ts_mono_ns: int
    ts_wall_ms: int
    capture_ms: float
    tab_id: str
    zone: Zone
    dpr: float
    scroll: Point
    size: Size
    format: str = "jpeg"


@dataclass(frozen=True, slots=True)
class Frame:
    data: bytes
    meta: FrameMetadata

    @property
    def seq(self) -> int:
        return self.meta.seq
