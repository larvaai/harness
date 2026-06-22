from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tool import ToolCall


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str | None = None
    final_answer: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
