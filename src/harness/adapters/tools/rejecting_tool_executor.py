from __future__ import annotations

from harness.core.domain import ToolCall, ToolResult


class RejectingToolExecutor:
    async def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(
            tool_call_id=call.id,
            success=False,
            error=f"No tool executor is configured for tool '{call.tool_name}'.",
        )
