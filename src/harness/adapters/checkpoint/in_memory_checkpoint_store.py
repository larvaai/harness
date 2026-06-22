from __future__ import annotations

from harness.core.domain import Checkpoint


class InMemoryCheckpointStore:
    def __init__(self) -> None:
        self.checkpoints: list[Checkpoint] = []

    async def save(self, checkpoint: Checkpoint) -> None:
        self.checkpoints.append(checkpoint)

    async def load_latest(self, run_id: str) -> Checkpoint | None:
        for checkpoint in reversed(self.checkpoints):
            if checkpoint.run_id == run_id:
                return checkpoint
        return None
