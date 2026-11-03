from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from web_capture.application.control.registry import CommandRegistry
from web_capture.domain.errors import WebCaptureError

log = logging.getLogger(__name__)


class ControlService:
    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry

    async def execute(self, raw: object) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            return {"id": None, "ok": False, "error": "message JSON objet attendu"}
        msg_id = raw.get("id")
        name = raw.get("cmd")
        if not isinstance(name, str):
            return {"id": msg_id, "ok": False, "error": "champ 'cmd' (chaîne) requis"}
        entry = self._registry.get(name)
        if entry is None:
            known = ", ".join(self._registry.names())
            return {"id": msg_id, "ok": False, "error": f"commande inconnue : {name} ({known})"}
        try:
            result = await entry.handle(entry.parse(raw))
        except WebCaptureError as exc:
            return {"id": msg_id, "ok": False, "error": str(exc)}
        except Exception:
            log.exception("erreur inattendue pendant la commande %s", name)
            return {"id": msg_id, "ok": False, "error": "erreur interne"}
        return {"id": msg_id, "ok": True, **result}
