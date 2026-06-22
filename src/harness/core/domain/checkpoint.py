from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from ._serialization import to_plain_data
from .state import RuntimeState


class CheckpointReason(str, Enum):
    RUN_STARTED = "run_started"
    BEFORE_LLM_CALL = "before_llm_call"
    AFTER_LLM_RESPONSE = "after_llm_response"
    BEFORE_TOOL_EXECUTION = "before_tool_execution"
    AFTER_TOOL_EXECUTION = "after_tool_execution"
    ERROR_OCCURRED = "error_occurred"
    RUN_FINISHED = "run_finished"


@dataclass(frozen=True, slots=True)
class Checkpoint:
    run_id: str
    seq: int
    reason: CheckpointReason
    state_snapshot: dict[str, Any]
    id: str = field(default_factory=lambda: f"checkpoint_{uuid4().hex}")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_state(
        cls,
        *,
        reason: CheckpointReason,
        state: RuntimeState,
        seq: int,
    ) -> Checkpoint:
        return cls(
            run_id=state.run_id,
            seq=seq,
            reason=reason,
            state_snapshot=state.to_snapshot(),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(
            {
                "id": self.id,
                "run_id": self.run_id,
                "seq": self.seq,
                "reason": self.reason,
                "state_snapshot": self.state_snapshot,
                "created_at": self.created_at,
            }
        )
