import math

import pytest

from web_capture.domain.errors import InvalidFpsError, InvalidQualityError, InvalidZoneError
from web_capture.domain.frame import Size, Zone
from web_capture.domain.rules import validate_fps, validate_jpeg_quality, validate_zone

VIEWPORT = Size(1280, 720)


@pytest.mark.parametrize("fps", [0.1, 1, 10, 30, 30.0])
def test_fps_within_bounds(fps: float) -> None:
    assert validate_fps(fps) == float(fps)


@pytest.mark.parametrize("fps", [0.09, 0, -1, 30.01, 120, math.nan, math.inf, "10", True, None])
def test_fps_rejected(fps: object) -> None:
    with pytest.raises(InvalidFpsError):
        validate_fps(fps)


@pytest.mark.parametrize(
    "zone",
    [Zone(100, 50, 400, 300), Zone(0, 0, 1280, 720), Zone(1279, 719, 1, 1)],
)
def test_zone_within_viewport(zone: Zone) -> None:
    assert validate_zone(zone, VIEWPORT) is zone


@pytest.mark.parametrize(
    "zone",
    [
        Zone(0, 0, 0, 10),
        Zone(0, 0, 10, 0),
        Zone(-1, 0, 10, 10),
        Zone(0, -1, 10, 10),
        Zone(1000, 0, 281, 10),
        Zone(0, 700, 10, 21),
        Zone(math.nan, 0, 10, 10),
    ],
)
def test_zone_rejected(zone: Zone) -> None:
    with pytest.raises(InvalidZoneError):
        validate_zone(zone, VIEWPORT)


@pytest.mark.parametrize("quality", [1, 80, 100])
def test_quality_within_bounds(quality: int) -> None:
    assert validate_jpeg_quality(quality) == quality


@pytest.mark.parametrize("quality", [0, 101, 80.0, True])
def test_quality_rejected(quality: object) -> None:
    with pytest.raises(InvalidQualityError):
        validate_jpeg_quality(quality)
