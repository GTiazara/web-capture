from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from web_capture.adapters.config.schema import AppConfig
from web_capture.domain.errors import ConfigError, WebCaptureError
from web_capture.domain.frame import Size, Zone
from web_capture.domain.rules import validate_fps, validate_jpeg_quality, validate_zone

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _describe(exc: OmegaConfBaseException) -> str:
    key = getattr(exc, "full_key", None)
    msg = getattr(exc, "msg", None) or str(exc)
    first_line = str(msg).splitlines()[0] if msg else type(exc).__name__
    return f"{key} : {first_line}" if key else first_line


def merge_config(config_file: Path | None, overrides: Sequence[str]) -> DictConfig:
    """Fusionne défauts < fichier YAML < surcharges, sans exiger les valeurs obligatoires."""
    try:
        base = OmegaConf.structured(AppConfig)
        OmegaConf.set_readonly(base, False)
        layers: list[Any] = [base]
        if config_file is not None:
            layers.append(OmegaConf.load(config_file))
        layers.append(OmegaConf.from_dotlist(list(overrides)))
        merged = OmegaConf.merge(*layers)
    except OmegaConfBaseException as exc:
        raise ConfigError(_describe(exc)) from exc
    except OSError as exc:
        raise ConfigError(f"fichier de configuration illisible : {exc}") from exc
    if not isinstance(merged, DictConfig):
        raise ConfigError("la configuration doit être un dictionnaire")
    return merged


def load_config(config_file: Path | None = None, overrides: Sequence[str] = ()) -> AppConfig:
    merged = merge_config(config_file, overrides)
    try:
        config = OmegaConf.to_object(merged)
    except OmegaConfBaseException as exc:
        raise ConfigError(_describe(exc)) from exc
    if not isinstance(config, AppConfig):
        raise ConfigError("configuration invalide")
    validate(config)
    return config


def _check(key: str, check: Callable[[], object]) -> None:
    try:
        check()
    except WebCaptureError as exc:
        raise ConfigError(f"{key} : {exc}") from exc


def _fail(key: str, message: str) -> None:
    raise ConfigError(f"{key} : {message}")


def validate(config: AppConfig) -> None:
    if not config.browser.url.strip():
        _fail("browser.url", "URL vide")
    viewport = config.browser.viewport
    if viewport.width <= 0 or viewport.height <= 0:
        _fail("browser.viewport", "largeur et hauteur doivent être positives")
    _check("capture.fps", lambda: validate_fps(config.capture.fps))
    _check("capture.jpeg_quality", lambda: validate_jpeg_quality(config.capture.jpeg_quality))
    zone = to_zone(config)
    if zone is not None:
        _check(
            "capture.zone",
            lambda: validate_zone(zone, Size(viewport.width, viewport.height)),
        )
    if config.streaming.buffer_size < 1:
        _fail("streaming.buffer_size", "doit être supérieur ou égal à 1")
    if config.streaming.send_timeout_s <= 0:
        _fail("streaming.send_timeout_s", "doit être strictement positif")
    if not 1 <= config.server.port <= 65535:
        _fail("server.port", "doit être compris entre 1 et 65535")
    if not config.recording.output_dir.strip():
        _fail("recording.output_dir", "chemin vide")
    if config.logging.level.upper() not in LOG_LEVELS:
        _fail("logging.level", f"valeur attendue parmi {', '.join(LOG_LEVELS)}")


def to_zone(config: AppConfig) -> Zone | None:
    z = config.capture.zone
    return None if z is None else Zone(z.x, z.y, z.width, z.height)


def dump_config(config: DictConfig) -> str:
    return OmegaConf.to_yaml(config)
