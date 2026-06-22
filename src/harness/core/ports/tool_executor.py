from __future__ import annotations

from typing import Protocol

from harness.core.domain import ToolCall, ToolResult


class ToolExecutorPort(Protocol):
    async def execute(self, call: ToolCall) -> ToolResult:
        ...
