from __future__ import annotations

import io
from unittest.mock import patch

import pytest

from web_capture.entrypoints import cli

URL = "browser.url=http://127.0.0.1:8000/"


def test_print_config_displays_merged_yaml_and_exits_zero() -> None:
    stdout = io.StringIO()
    with patch("sys.stdout", stdout):
        code = cli.main(["--print-config", URL, "capture.fps=15"])
    assert code == 0
    assert "fps: 15" in stdout.getvalue()
    assert "port: 8765" in stdout.getvalue()


def test_print_config_does_not_require_url() -> None:
    stdout = io.StringIO()
    with patch("sys.stdout", stdout):
        code = cli.main(["--print-config"])
    assert code == 0 and "url: ???" in stdout.getvalue()


def test_invalid_config_returns_two_without_starting_browser() -> None:
    stderr = io.StringIO()
    with patch("sys.stderr", stderr), patch.object(cli, "run_application") as run:
        code = cli.main(["capture.fps=120"])
    assert code == 2
    assert "browser.url" in stderr.getvalue()
    run.assert_not_called()


def test_unknown_key_returns_two() -> None:
    stderr = io.StringIO()
    with patch("sys.stderr", stderr):
        code = cli.main([URL, "capture.fsp=15"])
    assert code == 2 and "capture.fsp" in stderr.getvalue()


def test_help_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "--config" in capsys.readouterr().out
