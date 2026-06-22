from __future__ import annotations

from typing import Protocol

from harness.core.domain import LifecycleEvent


class EventPublisherPort(Protocol):
    async def publish(self, event: LifecycleEvent) -> None:
        ...
