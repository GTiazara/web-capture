from __future__ import annotations

import json
import struct
from typing import Any

from web_capture.domain.frame import Frame

HEADER_FIELDS = (
    "seq",
    "ts_mono_ns",
    "ts_wall_ms",
    "capture_ms",
    "tab_id",
    "zone",
    "dpr",
    "scroll",
    "size",
    "format",
    "dropped",
)

_LEN = struct.Struct(">I")


def frame_header(frame: Frame, dropped: int = 0) -> dict[str, Any]:
    m = frame.meta
    return {
        "seq": m.seq,
        "ts_mono_ns": m.ts_mono_ns,
        "ts_wall_ms": m.ts_wall_ms,
        "capture_ms": round(m.capture_ms, 3),
        "tab_id": m.tab_id,
        "zone": {"x": m.zone.x, "y": m.zone.y, "width": m.zone.width, "height": m.zone.height},
        "dpr": m.dpr,
        "scroll": {"x": m.scroll.x, "y": m.scroll.y},
        "size": {"width": m.size.width, "height": m.size.height},
        "format": m.format,
        "dropped": dropped,
    }


def encode_frame(frame: Frame, dropped: int = 0) -> bytes:
    header = json.dumps(frame_header(frame, dropped), separators=(",", ":")).encode()
    return _LEN.pack(len(header)) + header + frame.data


def decode_frame(message: bytes) -> tuple[dict[str, Any], bytes]:
    if len(message) < _LEN.size:
        raise ValueError("message trop court")
    (length,) = _LEN.unpack_from(message)
    end = _LEN.size + length
    if end > len(message):
        raise ValueError("longueur d'en-tête incohérente")
    header = json.loads(message[_LEN.size : end].decode("utf-8"))
    if not isinstance(header, dict):
        raise ValueError("en-tête JSON invalide")
    missing = [f for f in HEADER_FIELDS if f not in header]
    if missing:
        raise ValueError(f"champs d'en-tête manquants : {', '.join(missing)}")
    return header, message[end:]
