from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from ._serialization import to_plain_data
from .llm import LLMResponse
from .message import Message, MessageRole
from .task import Task
from .tool import ToolCall, ToolResult


class RuntimeStatus(str, Enum):
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass(slots=True)
class RuntimeState:
    run_id: str
    task: Task
    messages: list[Message] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    status: RuntimeStatus = RuntimeStatus.RUNNING
    final_answer: str | None = None
    error: str | None = None
    revision: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def new(cls, task: Task, run_id: str | None = None) -> RuntimeState:
        state = cls(run_id=run_id or f"run_{uuid4().hex}", task=task)
        state.messages.append(Message(role=MessageRole.USER, content=task.user_input))
        return state

    @property
    def is_finished(self) -> bool:
        return self.status in {RuntimeStatus.FINISHED, RuntimeStatus.FAILED}

    def has_changed_since(self, revision: int) -> bool:
        return self.revision > revision

    def apply_llm_response(self, response: LLMResponse) -> None:
        content = response.content or response.final_answer or ""
        self.messages.append(
            Message(
                role=MessageRole.ASSISTANT,
                content=content,
                metadata={"tool_call_ids": [call.id for call in response.tool_calls]},
            )
        )
        self.tool_calls.extend(response.tool_calls)
        self._touch()

    def apply_tool_result(self, result: ToolResult) -> None:
        self.tool_results.append(result)
        self.messages.append(
            Message(
                role=MessageRole.TOOL,
                content=result.output or result.error or "",
                tool_call_id=result.tool_call_id,
                metadata={"success": result.success},
            )
        )
        self._touch()

    def finish(self, final_answer: str) -> None:
        if self.status == RuntimeStatus.FINISHED and self.final_answer == final_answer:
            return

        self.status = RuntimeStatus.FINISHED
        self.final_answer = final_answer
        self.error = None
        self._touch()

    def mark_error(self, error: BaseException | str) -> None:
        message = str(error)
        if self.status == RuntimeStatus.FAILED and self.error == message:
            return

        self.status = RuntimeStatus.FAILED
        self.error = message
        self._touch()

    def to_snapshot(self) -> dict[str, Any]:
        return to_plain_data(
            {
                "run_id": self.run_id,
                "task": self.task,
                "messages": self.messages,
                "tool_calls": self.tool_calls,
                "tool_results": self.tool_results,
                "status": self.status,
                "final_answer": self.final_answer,
                "error": self.error,
                "revision": self.revision,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
        )

    def _touch(self) -> None:
        self.revision += 1
        self.updated_at = datetime.now(UTC)
