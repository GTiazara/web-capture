import struct

import pytest

from tests.unit.test_frame_bus import frame
from web_capture.adapters.capture.jpeg import jpeg_size
from web_capture.adapters.http.codec import HEADER_FIELDS, decode_frame, encode_frame
from web_capture.adapters.http.origin import is_origin_allowed
from web_capture.domain.frame import Size


def test_codec_round_trip() -> None:
    f = frame(42)
    header, payload = decode_frame(encode_frame(f, dropped=3))
    assert set(HEADER_FIELDS) <= header.keys()
    assert header["seq"] == 42
    assert header["dropped"] == 3
    assert header["zone"] == {"x": 0, "y": 0, "width": 10, "height": 10}
    assert header["size"] == {"width": 10, "height": 10}
    assert payload == f.data


def test_codec_layout_is_length_prefixed_json() -> None:
    msg = encode_frame(frame(1))
    (length,) = struct.unpack(">I", msg[:4])
    assert msg[4 : 4 + length].startswith(b"{")


def test_decode_rejects_missing_field() -> None:
    header = b'{"seq": 1}'
    with pytest.raises(ValueError, match="manquants"):
        decode_frame(struct.pack(">I", len(header)) + header + b"jpeg")


def test_decode_rejects_bad_length() -> None:
    with pytest.raises(ValueError):
        decode_frame(struct.pack(">I", 999) + b"{}")


@pytest.mark.parametrize(
    ("origin", "host", "port", "allowed"),
    [
        (None, "127.0.0.1", 8765, True),
        ("http://127.0.0.1:8765", "127.0.0.1", 8765, True),
        ("http://localhost:8765", "127.0.0.1", 8765, True),
        ("http://[::1]:8765", "localhost", 8765, True),
        ("http://example.com", "127.0.0.1", 8765, False),
        ("http://example.com:8765", "127.0.0.1", 8765, False),
        ("http://127.0.0.1:9999", "127.0.0.1", 8765, False),
        ("https://127.0.0.1:8765", "127.0.0.1", 8765, False),
        ("null", "127.0.0.1", 8765, False),
        ("http://10.0.0.5:8765", "10.0.0.5", 8765, True),
        ("http://localhost:8765", "10.0.0.5", 8765, False),
    ],
)
def test_origin_check(origin: str | None, host: str, port: int, allowed: bool) -> None:
    assert is_origin_allowed(origin, host, port) is allowed


def test_jpeg_size_reads_sof() -> None:
    sof = b"\xff\xc0\x00\x11\x08" + (300).to_bytes(2, "big") + (400).to_bytes(2, "big")
    data = b"\xff\xd8" + b"\xff\xe0\x00\x04ab" + sof + b"\x00" * 10
    assert jpeg_size(data) == Size(400, 300)
    with pytest.raises(ValueError):
        jpeg_size(b"notjpeg")
