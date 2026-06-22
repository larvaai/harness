from __future__ import annotations

import asyncio

from harness.core.domain import (
    Checkpoint,
    CheckpointReason,
    HookContext,
    HookPoint,
    HookResult,
    LLMResponse,
    LifecycleEvent,
    Message,
    RuntimeStatus,
    Task,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from harness.core.services import LifecycleManager
from harness.core.use_cases import ExecuteToolCallUseCase, RunTaskUseCase


class ScriptedLLM:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[list[Message], list[ToolDefinition] | None]] = []

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        self.calls.append((list(messages), tools))
        return self.responses.pop(0)


class RecordingToolExecutor:
    def __init__(self) -> None:
        self.calls: list[ToolCall] = []

    async def execute(self, call: ToolCall) -> ToolResult:
        self.calls.append(call)
        return ToolResult(
            tool_call_id=call.id,
            success=True,
            output=f"result for {call.tool_name}",
        )


class RecordingHookRunner:
    def __init__(self, fail_at: HookPoint | None = None) -> None:
        self.fail_at = fail_at
        self.calls: list[tuple[HookPoint, HookContext]] = []

    async def run(self, point: HookPoint, context: HookContext) -> list[HookResult]:
        self.calls.append((point, context))
        if point == self.fail_at:
            raise PermissionError(f"blocked at {point.value}")
        return [HookResult(hook_name=f"record_{point.value}", point=point)]


class RecordingEventPublisher:
    def __init__(self) -> None:
        self.events: list[LifecycleEvent] = []

    async def publish(self, event: LifecycleEvent) -> None:
        self.events.append(event)


class RecordingCheckpointStore:
    def __init__(self) -> None:
        self.saved: list[Checkpoint] = []

    async def save(self, checkpoint: Checkpoint) -> None:
        self.saved.append(checkpoint)

    async def load_latest(self, run_id: str) -> Checkpoint | None:
        matching = [checkpoint for checkpoint in self.saved if checkpoint.run_id == run_id]
        return matching[-1] if matching else None


def build_use_case(
    *,
    llm: ScriptedLLM,
    tool_executor: RecordingToolExecutor | None = None,
    hook_runner: RecordingHookRunner | None = None,
) -> tuple[
    RunTaskUseCase,
    RecordingHookRunner,
    RecordingEventPublisher,
    RecordingCheckpointStore,
    RecordingToolExecutor,
]:
    hooks = hook_runner or RecordingHookRunner()
    events = RecordingEventPublisher()
    checkpoints = RecordingCheckpointStore()
    lifecycle = LifecycleManager(
        hook_runner=hooks,
        event_publisher=events,
        checkpoint_store=checkpoints,
    )
    tools = tool_executor or RecordingToolExecutor()
    execute_tool_call = ExecuteToolCallUseCase(
        tool_executor=tools,
        lifecycle=lifecycle,
    )
    use_case = RunTaskUseCase(
        llm=llm,
        lifecycle=lifecycle,
        execute_tool_call=execute_tool_call,
    )
    return use_case, hooks, events, checkpoints, tools


def test_run_task_final_answer_goes_through_core_lifecycle() -> None:
    async def scenario() -> None:
        llm = ScriptedLLM([LLMResponse(final_answer="done")])
        use_case, hooks, events, checkpoints, _ = build_use_case(llm=llm)

        result = await use_case.execute(Task("say done"))

        assert result.status == RuntimeStatus.FINISHED
        assert result.final_answer == "done"
        assert [checkpoint.reason for checkpoint in checkpoints.saved] == [
            CheckpointReason.RUN_STARTED,
            CheckpointReason.BEFORE_LLM_CALL,
            CheckpointReason.AFTER_LLM_RESPONSE,
            CheckpointReason.RUN_FINISHED,
        ]
        assert [point for point, _ in hooks.calls] == [
            HookPoint.BEFORE_RUN,
            HookPoint.ON_STATE_SAVED,
            HookPoint.BEFORE_LLM_CALL,
            HookPoint.ON_STATE_SAVED,
            HookPoint.AFTER_LLM_CALL,
            HookPoint.ON_STATE_SAVED,
            HookPoint.AFTER_RUN,
            HookPoint.ON_STATE_SAVED,
        ]
        assert [event.point for event in events.events] == [
            HookPoint.BEFORE_RUN,
            HookPoint.ON_STATE_SAVED,
            HookPoint.BEFORE_LLM_CALL,
            HookPoint.ON_STATE_SAVED,
            HookPoint.AFTER_LLM_CALL,
            HookPoint.ON_STATE_SAVED,
            HookPoint.AFTER_RUN,
            HookPoint.ON_STATE_SAVED,
        ]
        assert result.state_snapshot["revision"] == 2

    asyncio.run(scenario())


def test_run_task_tool_call_goes_through_before_and_after_tool_hooks() -> None:
    async def scenario() -> None:
        tool_call = ToolCall(tool_name="read_file", arguments={"path": "README.md"})
        llm = ScriptedLLM(
            [
                LLMResponse(content="I need a file", tool_calls=[tool_call]),
                LLMResponse(final_answer="file inspected"),
            ]
        )
        use_case, hooks, _, checkpoints, tool_executor = build_use_case(llm=llm)

        result = await use_case.execute(Task("inspect README"))

        assert result.status == RuntimeStatus.FINISHED
        assert result.final_answer == "file inspected"
        assert tool_executor.calls == [tool_call]
        assert [checkpoint.reason for checkpoint in checkpoints.saved] == [
            CheckpointReason.RUN_STARTED,
            CheckpointReason.BEFORE_LLM_CALL,
            CheckpointReason.AFTER_LLM_RESPONSE,
            CheckpointReason.BEFORE_TOOL_EXECUTION,
            CheckpointReason.AFTER_TOOL_EXECUTION,
            CheckpointReason.BEFORE_LLM_CALL,
            CheckpointReason.AFTER_LLM_RESPONSE,
            CheckpointReason.RUN_FINISHED,
        ]
        hook_points = [point for point, _ in hooks.calls]
        assert HookPoint.BEFORE_TOOL in hook_points
        assert HookPoint.AFTER_TOOL in hook_points
        assert hook_points.index(HookPoint.BEFORE_TOOL) < hook_points.index(
            HookPoint.AFTER_TOOL
        )
        assert result.tool_results[0].output == "result for read_file"
        assert result.state_snapshot["revision"] == 4

    asyncio.run(scenario())


def test_hook_failure_marks_run_failed_and_reaches_on_error_without_executing_tool() -> None:
    async def scenario() -> None:
        tool_call = ToolCall(tool_name="run_shell_command", arguments={"cmd": "boom"})
        llm = ScriptedLLM([LLMResponse(content="Need shell", tool_calls=[tool_call])])
        hook_runner = RecordingHookRunner(fail_at=HookPoint.BEFORE_TOOL)
        use_case, hooks, events, checkpoints, tool_executor = build_use_case(
            llm=llm,
            hook_runner=hook_runner,
        )

        result = await use_case.execute(Task("run a command"))

        assert result.status == RuntimeStatus.FAILED
        assert "blocked at before_tool" in (result.error or "")
        assert tool_executor.calls == []
        assert checkpoints.saved[-1].reason == CheckpointReason.ERROR_OCCURRED
        assert checkpoints.saved[-1].state_snapshot["status"] == "failed"
        assert HookPoint.ON_ERROR in [point for point, _ in hooks.calls]
        assert HookPoint.ON_ERROR in [event.point for event in events.events]

    asyncio.run(scenario())
