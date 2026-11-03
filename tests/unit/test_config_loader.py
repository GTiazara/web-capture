from pathlib import Path

import pytest
from omegaconf import OmegaConf

from web_capture.adapters.config.omegaconf_loader import (
    dump_config,
    load_config,
    merge_config,
    to_zone,
)
from web_capture.adapters.config.schema import AppConfig
from web_capture.domain.errors import ConfigError
from web_capture.domain.frame import Zone

URL = "browser.url=http://127.0.0.1:8000/"
DEFAULT_YAML = Path(__file__).parents[2] / "configs" / "default.yaml"


def test_defaults_only_url_given() -> None:
    cfg = load_config(None, [URL])
    assert cfg.browser.url == "http://127.0.0.1:8000/"
    assert cfg.capture.fps == 10
    assert (cfg.browser.viewport.width, cfg.browser.viewport.height) == (1280, 720)
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.port == 8765
    assert cfg.capture.zone is None


def test_cli_overrides_yaml_file(tmp_path: Path) -> None:
    f = tmp_path / "c.yaml"
    f.write_text("capture:\n  fps: 5\nserver:\n  port: 9000\n")
    cfg = load_config(f, [URL, "capture.fps=15"])
    assert cfg.capture.fps == 15
    assert cfg.server.port == 9000


def test_yaml_overrides_defaults(tmp_path: Path) -> None:
    f = tmp_path / "c.yaml"
    f.write_text("capture:\n  fps: 5\n")
    assert load_config(f, [URL]).capture.fps == 5


def test_zone_from_dotlist() -> None:
    cfg = load_config(None, [URL, "capture.zone={x: 100, y: 50, width: 400, height: 300}"])
    assert to_zone(cfg) == Zone(100, 50, 400, 300)


def test_unknown_key_mentions_key() -> None:
    with pytest.raises(ConfigError, match=r"capture\.fsp"):
        load_config(None, [URL, "capture.fsp=15"])


def test_out_of_bounds_fps_mentions_key() -> None:
    with pytest.raises(ConfigError, match=r"capture\.fps"):
        load_config(None, [URL, "capture.fps=120"])


def test_wrong_type_mentions_key() -> None:
    with pytest.raises(ConfigError, match=r"server\.port"):
        load_config(None, [URL, "server.port=abc"])


def test_missing_url_mentions_key() -> None:
    with pytest.raises(ConfigError, match=r"browser\.url"):
        load_config(None, [])


def test_zone_outside_viewport_rejected() -> None:
    with pytest.raises(ConfigError, match=r"capture\.zone"):
        load_config(None, [URL, "capture.zone={x: 1000, y: 0, width: 400, height: 10}"])


def test_unreadable_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "absent.yaml", [URL])


def test_print_config_does_not_require_url() -> None:
    text = dump_config(merge_config(None, ["capture.fps=15"]))
    assert "fps: 15" in text
    assert "url: ???" in text


def test_default_yaml_loads_and_only_has_schema_keys() -> None:
    cfg = load_config(DEFAULT_YAML, [URL])
    assert cfg == load_config(None, [URL])
    file_keys = set(OmegaConf.to_container(OmegaConf.load(DEFAULT_YAML)).keys())  # type: ignore[union-attr]
    schema_keys = set(OmegaConf.to_container(OmegaConf.structured(AppConfig)).keys())  # type: ignore[union-attr]
    assert file_keys == schema_keys
