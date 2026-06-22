from __future__ import annotations

from typing import Protocol

from harness.core.domain import Checkpoint


class CheckpointStorePort(Protocol):
    async def save(self, checkpoint: Checkpoint) -> None:
        ...

    async def load_latest(self, run_id: str) -> Checkpoint | None:
        ...
