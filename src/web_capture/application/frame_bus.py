from __future__ import annotations

import asyncio
from collections import Counter, deque

from web_capture.application.delivery import Delivery, DeliveryPolicy
from web_capture.domain.frame import Frame


class FrameBus:
    """Buffer circulaire en mémoire diffusant les images à des abonnés indépendants.

    `publish` ne bloque jamais : chaque abonné lit à son rythme selon sa politique.
    """

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._frames: deque[Frame] = deque(maxlen=capacity)
        self._published = asyncio.Event()
        self._closed = False
        self._subscribers: Counter[str] = Counter()

    @property
    def capacity(self) -> int:
        return self._frames.maxlen or 0

    @property
    def closed(self) -> bool:
        return self._closed

    def publish(self, frame: Frame) -> None:
        if self._closed:
            return
        self._frames.append(frame)
        self._notify()

    def latest(self) -> Frame | None:
        return self._frames[-1] if self._frames else None

    def oldest(self) -> Frame | None:
        return self._frames[0] if self._frames else None

    def get(self, seq: int) -> Frame | None:
        oldest = self.oldest()
        if oldest is None:
            return None
        index = seq - oldest.seq
        if 0 <= index < len(self._frames):
            frame = self._frames[index]
            if frame.seq == seq:
                return frame
        return next((f for f in self._frames if f.seq == seq), None)

    def frames(self) -> list[Frame]:
        return list(self._frames)

    def subscribe(self, policy: DeliveryPolicy) -> Subscription:
        self._subscribers[policy.name] += 1
        return Subscription(self, policy)

    def subscriber_counts(self) -> dict[str, int]:
        return {name: n for name, n in self._subscribers.items() if n > 0}

    def close(self) -> None:
        self._closed = True
        self._notify()

    def _unsubscribe(self, policy: DeliveryPolicy) -> None:
        self._subscribers[policy.name] -= 1

    def _notify(self) -> None:
        event, self._published = self._published, asyncio.Event()
        event.set()

    def _publication_event(self) -> asyncio.Event:
        return self._published


class Subscription:
    def __init__(self, bus: FrameBus, policy: DeliveryPolicy) -> None:
        self._bus = bus
        self._policy = policy
        self._last_sent: int | None = None
        self._active = True

    @property
    def policy_name(self) -> str:
        return self._policy.name

    async def next(self) -> Delivery | None:
        """Prochaine image selon la politique ; None quand le bus est fermé."""
        while self._active and not self._bus.closed:
            event = self._bus._publication_event()
            delivery = self._policy.select(self._bus, self._last_sent)
            if delivery is not None:
                self._last_sent = delivery.frame.seq
                return delivery
            await event.wait()
        return None

    def close(self) -> None:
        if self._active:
            self._active = False
            self._bus._unsubscribe(self._policy)
