from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from ._serialization import to_plain_data

if TYPE_CHECKING:
    from .hook import HookContext


class HookPoint(str, Enum):
    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"
    BEFORE_LLM_CALL = "before_llm_call"
    AFTER_LLM_CALL = "after_llm_call"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_APPROVAL_REQUIRED = "on_approval_required"
    ON_ERROR = "on_error"
    ON_STATE_SAVED = "on_state_saved"


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    run_id: str
    point: HookPoint
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"event_{uuid4().hex}")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_context(cls, context: HookContext) -> LifecycleEvent:
        return cls(
            run_id=context.run_id,
            point=context.point,
            payload=to_plain_data(context.payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(
            {
                "id": self.id,
                "run_id": self.run_id,
                "point": self.point,
                "payload": self.payload,
                "created_at": self.created_at,
            }
        )
