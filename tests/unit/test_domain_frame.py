import dataclasses

import pytest

from web_capture.domain.errors import (
    EncoderUnavailableError,
    InvalidFpsError,
    RecordingError,
    WebCaptureError,
)
from web_capture.domain.frame import Frame, FrameMetadata, Point, Size, Zone


def _meta(seq: int = 3) -> FrameMetadata:
    return FrameMetadata(
        seq=seq,
        ts_mono_ns=10,
        ts_wall_ms=20,
        capture_ms=1.5,
        tab_id="T1",
        zone=Zone(1, 2, 3, 4),
        dpr=2.0,
        scroll=Point(0, 200),
        size=Size(6, 8),
    )


def test_frame_exposes_seq_and_default_format() -> None:
    frame = Frame(b"jpeg", _meta(seq=7))
    assert frame.seq == 7
    assert frame.meta.format == "jpeg"


def test_value_objects_are_immutable() -> None:
    frame = Frame(b"jpeg", _meta())
    with pytest.raises(dataclasses.FrozenInstanceError):
        frame.meta.seq = 9  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        Zone(0, 0, 1, 1).x = 5  # type: ignore[misc]


def test_full_zone_covers_viewport() -> None:
    assert Zone.full(Size(1280, 720)) == Zone(0, 0, 1280, 720)


def test_error_hierarchy() -> None:
    assert issubclass(InvalidFpsError, WebCaptureError)
    assert issubclass(EncoderUnavailableError, RecordingError)
