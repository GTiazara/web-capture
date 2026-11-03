from __future__ import annotations

import math

from web_capture.domain.errors import InvalidFpsError, InvalidQualityError, InvalidZoneError
from web_capture.domain.frame import Size, Zone

FPS_MIN = 0.1
FPS_MAX = 30.0
JPEG_QUALITY_MIN = 1
JPEG_QUALITY_MAX = 100


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def validate_fps(fps: object) -> float:
    if isinstance(fps, bool) or not isinstance(fps, int | float) or not math.isfinite(fps):
        raise InvalidFpsError(f"FPS invalide : {fps!r} (nombre attendu)")
    value = float(fps)
    if not FPS_MIN <= value <= FPS_MAX:
        raise InvalidFpsError(f"FPS hors bornes : {value} (attendu entre {FPS_MIN} et {FPS_MAX})")
    return value


def validate_zone(zone: Zone, viewport: Size) -> Zone:
    values = (zone.x, zone.y, zone.width, zone.height)
    if not all(_is_number(v) and math.isfinite(v) for v in values):
        raise InvalidZoneError(f"zone invalide : {zone} (nombres finis attendus)")
    if zone.width <= 0 or zone.height <= 0:
        raise InvalidZoneError("zone invalide : largeur et hauteur doivent être positives")
    if zone.x < 0 or zone.y < 0:
        raise InvalidZoneError("zone invalide : x et y doivent être positifs ou nuls")
    if zone.x + zone.width > viewport.width or zone.y + zone.height > viewport.height:
        raise InvalidZoneError(
            f"zone invalide : dépasse le viewport {viewport.width}x{viewport.height}"
        )
    return zone


def validate_jpeg_quality(quality: object) -> int:
    if not isinstance(quality, int) or isinstance(quality, bool):
        raise InvalidQualityError(f"qualité JPEG invalide : {quality!r} (entier attendu)")
    if not JPEG_QUALITY_MIN <= quality <= JPEG_QUALITY_MAX:
        raise InvalidQualityError(
            f"qualité JPEG hors bornes : {quality} "
            f"(attendu entre {JPEG_QUALITY_MIN} et {JPEG_QUALITY_MAX})"
        )
    return quality
