from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from web_capture.adapters.browser.playwright_session import PlaywrightBrowserSession
from web_capture.adapters.capture.cdp_frame_source import CdpFrameSource
from web_capture.adapters.clock import SystemClock
from web_capture.adapters.config.omegaconf_loader import to_zone
from web_capture.adapters.config.schema import AppConfig
from web_capture.adapters.http.app import create_app, start_server
from web_capture.adapters.http.keys import ServerSettings
from web_capture.adapters.http.origin import is_loopback
from web_capture.adapters.recording.ffmpeg_encoder import FfmpegEncoder
from web_capture.application.capture_service import CaptureService
from web_capture.application.control.handlers import CaptureHandlers
from web_capture.application.control.registry import CommandRegistry
from web_capture.application.control.service import ControlService
from web_capture.application.frame_bus import FrameBus
from web_capture.application.recording_service import RecordingService
from web_capture.domain.frame import Size

log = logging.getLogger(__name__)


async def _run_until_shutdown(
    capture: CaptureService,
    browser: PlaywrightBrowserSession,
    recording: RecordingService,
    bus: FrameBus,
    shutdown: asyncio.Event,
) -> None:
    async with asyncio.TaskGroup() as group:
        capture_task = group.create_task(capture.run(), name="capture")
        browser_task = group.create_task(browser.wait_closed(), name="browser-closed")
        shutdown_task = group.create_task(shutdown.wait(), name="shutdown-signal")
        await asyncio.wait(
            {capture_task, browser_task, shutdown_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        capture.stop()
        bus.close()
        await recording.aclose()
        for task in (capture_task, browser_task, shutdown_task):
            if not task.done():
                task.cancel()


async def run_application(config: AppConfig) -> None:
    browser = PlaywrightBrowserSession(
        config.browser.url,
        headless=config.browser.headless,
        viewport=Size(config.browser.viewport.width, config.browser.viewport.height),
    )
    await browser.start()
    shutdown = asyncio.Event()
    loop = asyncio.get_running_loop()
    installed: list[signal.Signals] = []
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown.set)
            installed.append(sig)
        except (NotImplementedError, RuntimeError):
            pass

    bus = FrameBus(config.streaming.buffer_size)
    source = CdpFrameSource(
        browser.cdp,
        browser.tab_id,
        Size(config.browser.viewport.width, config.browser.viewport.height),
        config.capture.jpeg_quality,
    )
    capture = CaptureService(
        source,
        SystemClock(),
        bus,
        fps=config.capture.fps,
        zone=to_zone(config),
    )
    recording = RecordingService(
        bus,
        FfmpegEncoder(),
        SystemClock(),
        Path(config.recording.output_dir),
        lambda: capture.fps,
    )
    handlers = CaptureHandlers(capture, bus, browser.current_url, recording)
    registry = CommandRegistry()
    handlers.register(registry)
    app = create_app(
        bus,
        ControlService(registry),
        ServerSettings(config.server.host, config.server.port, config.streaming.send_timeout_s),
    )
    runner = None
    try:
        if not is_loopback(config.server.host):
            log.warning(
                "le serveur écoute sur %s ; flux et contrôle sont accessibles sur le réseau",
                config.server.host,
            )
        runner = await start_server(app, config.server.host, config.server.port)
        await _run_until_shutdown(capture, browser, recording, bus, shutdown)
    finally:
        capture.stop()
        bus.close()
        await recording.aclose()
        if runner is not None:
            await runner.cleanup()
        await browser.close()
        for sig in installed:
            loop.remove_signal_handler(sig)
