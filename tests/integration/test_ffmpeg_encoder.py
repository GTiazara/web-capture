from __future__ import annotations

import asyncio
import io
from pathlib import Path

import imageio_ffmpeg
import pytest
from PIL import Image

from web_capture.adapters.clock import SystemClock
from web_capture.adapters.recording import ffmpeg_encoder
from web_capture.adapters.recording.ffmpeg_encoder import FfmpegEncoder, resolve_ffmpeg
from web_capture.application.frame_bus import FrameBus
from web_capture.application.recording_service import RecordingService
from web_capture.domain.errors import EncoderUnavailableError
from web_capture.domain.frame import Frame, FrameMetadata, Point, Size, Zone

pytestmark = pytest.mark.ffmpeg


def jpeg(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, "JPEG")
    return buf.getvalue()


def probe(path: Path) -> tuple[int, float]:
    frames, secs = imageio_ffmpeg.count_frames_and_secs(str(path))
    return int(frames), float(secs)


async def test_100_frames_at_10_fps_last_10_seconds(tmp_path: Path) -> None:
    out = tmp_path / "a.mp4"
    enc = FfmpegEncoder()
    await enc.open(out, 10)
    for i in range(100):
        await enc.write(jpeg(320, 240, (i * 2, 0, 255 - i * 2)))
    await enc.close()
    frames, secs = probe(out)
    assert frames == 100
    assert 9.5 <= secs <= 10.5


async def test_odd_dimensions_accepted(tmp_path: Path) -> None:
    out = tmp_path / "odd.mp4"
    enc = FfmpegEncoder()
    await enc.open(out, 5)
    for _ in range(10):
        await enc.write(jpeg(401, 301, (0, 255, 0)))
    await enc.close()
    assert probe(out)[0] == 10


def test_missing_ffmpeg_raises_encoder_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_binary() -> str:
        raise RuntimeError("absent")

    monkeypatch.setattr(ffmpeg_encoder.shutil, "which", lambda _: None)
    monkeypatch.setattr(imageio_ffmpeg, "get_ffmpeg_exe", no_binary)
    with pytest.raises(EncoderUnavailableError, match="introuvable"):
        resolve_ffmpeg()


async def test_unavailable_encoder_open_fails(tmp_path: Path) -> None:
    def unavailable() -> str:
        raise EncoderUnavailableError("encodeur vidéo introuvable")

    with pytest.raises(EncoderUnavailableError):
        await FfmpegEncoder(unavailable).open(tmp_path / "x.mp4", 10)


async def test_real_time_recording_duration_is_faithful(tmp_path: Path) -> None:
    bus = FrameBus(10)
    data = jpeg(320, 240, (255, 0, 0))
    meta = FrameMetadata(0, 0, 0, 1.0, "T", Zone(0, 0, 320, 240), 1.0, Point(0, 0), Size(320, 240))
    bus.publish(Frame(data, meta))
    service = RecordingService(bus, FfmpegEncoder(), SystemClock(), tmp_path, lambda: 10.0)
    path = await service.start()
    await asyncio.sleep(3)
    await service.stop()
    frames, secs = probe(path)
    assert 2.85 <= secs <= 3.3
    assert 29 <= frames <= 32
