from __future__ import annotations

from harness.core.domain import (
    CheckpointReason,
    HookPoint,
    LLMResponse,
    RunResult,
    RuntimeState,
    Task,
    ToolDefinition,
)
from harness.core.ports import LLMPort
from harness.core.services import LifecycleManager
from harness.core.use_cases.execute_tool_call import ExecuteToolCallUseCase


class MaxIterationsExceeded(RuntimeError):
    pass


class EmptyLLMResponseError(RuntimeError):
    pass


class RunTaskUseCase:
    def __init__(
        self,
        *,
        llm: LLMPort,
        lifecycle: LifecycleManager,
        execute_tool_call: ExecuteToolCallUseCase,
        tools: list[ToolDefinition] | None = None,
        max_iterations: int = 20,
    ) -> None:
        self._llm = llm
        self._lifecycle = lifecycle
        self._execute_tool_call = execute_tool_call
        self._tools = tools or []
        self._max_iterations = max_iterations

    async def execute(self, task: Task) -> RunResult:
        state = RuntimeState.new(task)

        try:
            await self._lifecycle.reach(
                point=HookPoint.BEFORE_RUN,
                state=state,
                checkpoint_reason=CheckpointReason.RUN_STARTED,
            )

            for _ in range(self._max_iterations):
                if state.is_finished:
                    break

                response = await self._call_llm(state)

                for tool_call in response.tool_calls:
                    await self._execute_tool_call.execute(
                        state=state,
                        tool_call=tool_call,
                    )

                if response.final_answer:
                    state.finish(response.final_answer)

                if not response.final_answer and not response.tool_calls:
                    raise EmptyLLMResponseError(
                        "LLM response must include a final answer or at least one tool call."
                    )
            else:
                raise MaxIterationsExceeded(
                    f"Run exceeded max_iterations={self._max_iterations}."
                )

            await self._lifecycle.reach(
                point=HookPoint.AFTER_RUN,
                state=state,
                checkpoint_reason=CheckpointReason.RUN_FINISHED,
            )
        except Exception as exc:
            state.mark_error(exc)
            await self._lifecycle.reach(
                point=HookPoint.ON_ERROR,
                state=state,
                payload={"error": exc},
                checkpoint_reason=CheckpointReason.ERROR_OCCURRED,
            )

        return RunResult.from_state(state)

    async def _call_llm(self, state: RuntimeState) -> LLMResponse:
        await self._lifecycle.reach(
            point=HookPoint.BEFORE_LLM_CALL,
            state=state,
            checkpoint_reason=CheckpointReason.BEFORE_LLM_CALL,
        )

        response = await self._llm.complete(messages=state.messages, tools=self._tools)
        state.apply_llm_response(response)

        await self._lifecycle.reach(
            point=HookPoint.AFTER_LLM_CALL,
            state=state,
            payload={"llm_response": response},
            checkpoint_reason=CheckpointReason.AFTER_LLM_RESPONSE,
        )

        return response
