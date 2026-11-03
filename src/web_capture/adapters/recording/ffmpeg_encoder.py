from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
from collections.abc import Callable
from pathlib import Path

from web_capture.domain.errors import EncoderUnavailableError, RecordingError

log = logging.getLogger(__name__)


def resolve_ffmpeg() -> str:
    """ffmpeg du PATH en priorité, sinon le binaire fourni par imageio-ffmpeg."""
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg

        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except (ImportError, RuntimeError) as exc:
        raise EncoderUnavailableError(
            "encodeur vidéo introuvable : installez ffmpeg ou imageio-ffmpeg"
        ) from exc


def ffmpeg_command(exe: str, path: Path, fps: float) -> list[str]:
    return [
        exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-f",
        "image2pipe",
        "-c:v",
        "mjpeg",
        "-framerate",
        f"{fps:g}",
        "-i",
        "-",
        # H.264 en yuv420p exige des dimensions paires.
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(path),
    ]


class FfmpegEncoder:
    def __init__(self, resolver: Callable[[], str] = resolve_ffmpeg) -> None:
        self._resolver = resolver
        self._proc: asyncio.subprocess.Process | None = None
        self._stderr: asyncio.Task[bytes] | None = None

    async def open(self, path: Path, fps: float) -> None:
        if self._proc is not None:
            raise RecordingError("encodeur déjà ouvert")
        exe = self._resolver()
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *ffmpeg_command(exe, path, fps),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise EncoderUnavailableError(f"impossible de lancer ffmpeg : {exc}") from exc
        if self._proc.stderr is not None:
            self._stderr = asyncio.create_task(self._proc.stderr.read())

    async def write(self, jpeg: bytes) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            raise RecordingError("encodeur non ouvert")
        try:
            proc.stdin.write(jpeg)
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise RecordingError(f"ffmpeg s'est arrêté : {await self._error_text()}") from exc

    async def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        if proc.stdin is not None:
            proc.stdin.close()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                await proc.stdin.wait_closed()
        code = await proc.wait()
        errors = await self._error_text()
        if code != 0:
            raise RecordingError(f"ffmpeg a échoué (code {code}) : {errors}")

    async def _error_text(self) -> str:
        if self._stderr is None:
            return ""
        with contextlib.suppress(Exception):
            text = (await asyncio.wait_for(self._stderr, 5)).decode(errors="replace").strip()
            return text.splitlines()[-1] if text else ""
        return ""
