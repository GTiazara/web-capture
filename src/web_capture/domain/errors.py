from __future__ import annotations


class WebCaptureError(Exception):
    """Erreur métier dont le message est destiné à l'utilisateur ou au client du module."""


class InvalidFpsError(WebCaptureError):
    pass


class InvalidZoneError(WebCaptureError):
    pass


class InvalidQualityError(WebCaptureError):
    pass


class InvalidCommandError(WebCaptureError):
    pass


class RecordingError(WebCaptureError):
    pass


class EncoderUnavailableError(RecordingError):
    pass


class NavigationError(WebCaptureError):
    pass


class ConfigError(WebCaptureError):
    pass
