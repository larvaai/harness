from __future__ import annotations

from dataclasses import dataclass

from harness.adapters.checkpoint import InMemoryCheckpointStore
from harness.adapters.events import InMemoryEventPublisher
from harness.adapters.hooks import NoopHookRunner
from harness.adapters.llm import LMStudioConfig, LMStudioLLMAdapter
from harness.adapters.tools import RejectingToolExecutor
from harness.core.services import LifecycleManager
from harness.core.use_cases import ExecuteToolCallUseCase, RunTaskUseCase


@dataclass(frozen=True, slots=True)
class LMStudioRuntime:
    llm: LMStudioLLMAdapter
    run_task: RunTaskUseCase
    events: InMemoryEventPublisher
    checkpoints: InMemoryCheckpointStore


def build_lm_studio_runtime(
    *,
    base_url: str = "http://localhost:1234/v1",
    model: str | None = None,
    temperature: float = 0.2,
    timeout_seconds: float = 120.0,
    max_tokens: int | None = None,
    max_iterations: int = 3,
) -> LMStudioRuntime:
    llm = LMStudioLLMAdapter(
        LMStudioConfig(
            base_url=base_url,
            model=model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
    )
    events = InMemoryEventPublisher()
    checkpoints = InMemoryCheckpointStore()
    lifecycle = LifecycleManager(
        hook_runner=NoopHookRunner(),
        event_publisher=events,
        checkpoint_store=checkpoints,
    )
    execute_tool_call = ExecuteToolCallUseCase(
        tool_executor=RejectingToolExecutor(),
        lifecycle=lifecycle,
    )
    run_task = RunTaskUseCase(
        llm=llm,
        lifecycle=lifecycle,
        execute_tool_call=execute_tool_call,
        max_iterations=max_iterations,
    )

    return LMStudioRuntime(
        llm=llm,
        run_task=run_task,
        events=events,
        checkpoints=checkpoints,
    )
