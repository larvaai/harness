from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ._serialization import to_plain_data
from .message import Message
from .state import RuntimeState, RuntimeStatus
from .tool import ToolResult


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    task_id: str
    status: RuntimeStatus
    final_answer: str | None = None
    error: str | None = None
    messages: list[Message] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    state_snapshot: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_state(cls, state: RuntimeState) -> RunResult:
        return cls(
            run_id=state.run_id,
            task_id=state.task.id,
            status=state.status,
            final_answer=state.final_answer,
            error=state.error,
            messages=list(state.messages),
            tool_results=list(state.tool_results),
            state_snapshot=state.to_snapshot(),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(
            {
                "run_id": self.run_id,
                "task_id": self.task_id,
                "status": self.status,
                "final_answer": self.final_answer,
                "error": self.error,
                "messages": self.messages,
                "tool_results": self.tool_results,
                "state_snapshot": self.state_snapshot,
            }
        )
