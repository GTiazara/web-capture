from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from web_capture.adapters.config.omegaconf_loader import dump_config, load_config, merge_config
from web_capture.domain.errors import ConfigError, WebCaptureError
from web_capture.entrypoints.bootstrap import run_application


def _arguments(argv: Sequence[str] | None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        prog="web-capture",
        description="Capture périodique, visualisation en direct et enregistrement MP4.",
    )
    parser.add_argument("--config", type=Path, help="fichier de configuration YAML")
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="afficher la configuration fusionnée puis quitter (browser.url peut manquer)",
    )
    args, overrides = parser.parse_known_args(argv)
    invalid = [item for item in overrides if "=" not in item or item.startswith("-")]
    if invalid:
        parser.error(f"argument(s) inattendu(s) : {' '.join(invalid)}")
    return args, overrides


def main(argv: Sequence[str] | None = None) -> int:
    args, overrides = _arguments(argv)
    if args.print_config:
        try:
            effective_config = merge_config(args.config, overrides)
            print(dump_config(effective_config), end="")
            return 0
        except ConfigError as exc:
            print(f"Configuration invalide : {exc}", file=sys.stderr)
            return 2
    try:
        app_config = load_config(args.config, overrides)
    except ConfigError as exc:
        print(f"Configuration invalide : {exc}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=getattr(logging, app_config.logging.level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run_application(app_config))
    except WebCaptureError as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0
