from __future__ import annotations

from harness.core.domain import (
    CheckpointReason,
    HookPoint,
    RuntimeState,
    ToolCall,
    ToolResult,
)
from harness.core.ports import ToolExecutorPort
from harness.core.services import LifecycleManager


class ExecuteToolCallUseCase:
    def __init__(
        self,
        *,
        tool_executor: ToolExecutorPort,
        lifecycle: LifecycleManager,
    ) -> None:
        self._tool_executor = tool_executor
        self._lifecycle = lifecycle

    async def execute(self, *, state: RuntimeState, tool_call: ToolCall) -> ToolResult:
        await self._lifecycle.reach(
            point=HookPoint.BEFORE_TOOL,
            state=state,
            payload={"tool_call": tool_call},
            checkpoint_reason=CheckpointReason.BEFORE_TOOL_EXECUTION,
        )

        tool_result = await self._tool_executor.execute(tool_call)
        state.apply_tool_result(tool_result)

        await self._lifecycle.reach(
            point=HookPoint.AFTER_TOOL,
            state=state,
            payload={"tool_call": tool_call, "tool_result": tool_result},
            checkpoint_reason=CheckpointReason.AFTER_TOOL_EXECUTION,
        )

        return tool_result
