from __future__ import annotations

from dataclasses import dataclass, field

from omegaconf import MISSING


@dataclass(frozen=True)
class ViewportConfig:
    width: int = 1280
    height: int = 720


@dataclass(frozen=True)
class ZoneConfig:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0


@dataclass(frozen=True)
class BrowserConfig:
    url: str = MISSING
    headless: bool = False
    viewport: ViewportConfig = field(default_factory=ViewportConfig)


@dataclass(frozen=True)
class CaptureConfig:
    fps: float = 10.0
    zone: ZoneConfig | None = None
    jpeg_quality: int = 80


@dataclass(frozen=True)
class StreamingConfig:
    buffer_size: int = 60
    send_timeout_s: float = 10.0


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass(frozen=True)
class RecordingConfig:
    output_dir: str = "./recordings"


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"


@dataclass(frozen=True)
class AppConfig:
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
