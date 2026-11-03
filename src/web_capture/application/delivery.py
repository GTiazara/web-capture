from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from web_capture.domain.frame import Frame

if TYPE_CHECKING:
    from web_capture.application.frame_bus import FrameBus


@dataclass(frozen=True, slots=True)
class Delivery:
    frame: Frame
    dropped: int = 0


class DeliveryPolicy(Protocol):
    name: str

    def select(self, bus: FrameBus, last_sent: int | None) -> Delivery | None:
        """Image à livrer après `last_sent`, ou None s'il faut attendre une publication."""
        ...


class LatestPolicy:
    name = "latest"

    def select(self, bus: FrameBus, last_sent: int | None) -> Delivery | None:
        latest = bus.latest()
        if latest is None or (last_sent is not None and latest.seq <= last_sent):
            return None
        return Delivery(latest)


class AllPolicy:
    name = "all"

    def select(self, bus: FrameBus, last_sent: int | None) -> Delivery | None:
        latest = bus.latest()
        oldest = bus.oldest()
        if latest is None or oldest is None:
            return None
        if last_sent is None:
            return Delivery(latest)
        wanted = last_sent + 1
        if wanted > latest.seq:
            return None
        if wanted < oldest.seq:
            return Delivery(oldest, dropped=oldest.seq - wanted)
        frame = bus.get(wanted)
        return Delivery(frame) if frame is not None else None


POLICIES: dict[str, type[LatestPolicy] | type[AllPolicy]] = {
    LatestPolicy.name: LatestPolicy,
    AllPolicy.name: AllPolicy,
}
