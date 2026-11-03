from __future__ import annotations

from web_capture.domain.frame import Size

_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def jpeg_size(data: bytes) -> Size:
    """Lit largeur et hauteur dans le segment SOF d'un JPEG, sans le décoder."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("données JPEG invalides")
    i = 2
    n = len(data)
    while i + 4 <= n:
        if data[i] != 0xFF:
            raise ValueError("marqueur JPEG attendu")
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        length = int.from_bytes(data[i + 2 : i + 4], "big")
        if marker in _SOF_MARKERS and i + 9 <= n:
            height = int.from_bytes(data[i + 5 : i + 7], "big")
            width = int.from_bytes(data[i + 7 : i + 9], "big")
            return Size(width, height)
        i += 2 + length
    raise ValueError("segment SOF introuvable")
