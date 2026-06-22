from __future__ import annotations

from harness.core.domain import LifecycleEvent


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[LifecycleEvent] = []

    async def publish(self, event: LifecycleEvent) -> None:
        self.events.append(event)
