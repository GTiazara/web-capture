from __future__ import annotations

from urllib.parse import urlsplit

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def is_loopback(host: str) -> bool:
    return host.strip("[]") in LOOPBACK_HOSTS


def is_origin_allowed(origin: str | None, server_host: str, server_port: int) -> bool:
    """Accepte les clients sans Origin (non navigateurs) et la seule origine du module.

    La comparaison porte sur l'hôte configuré, pas sur l'en-tête Host, pour résister
    au DNS rebinding.
    """
    if origin is None:
        return True
    try:
        parts = urlsplit(origin)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme != "http" or parts.hostname is None:
        return False
    if (port or 80) != server_port:
        return False
    if is_loopback(server_host):
        return parts.hostname in {h.strip("[]") for h in LOOPBACK_HOSTS}
    return parts.hostname == server_host.strip("[]")
