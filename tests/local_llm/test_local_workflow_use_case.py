from __future__ import annotations

import asyncio

from harness.core.domain import (
    ContextItem,
    ContextPack,
    LLMResponse,
    LocalWorkflowState,
    Message,
    TaskGraph,
    TaskSpec,
    ToolDefinition,
)
from harness.core.ports import ContextRetrieverPort
from harness.core.services import LocalLLMJsonWorker, LocalWorkflowValidator
from harness.core.use_cases import LocalWorkflowPromptSet, RunLocalLLMWorkflowUseCase


class ScriptedLLM:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.calls: list[list[Message]] = []

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        self.calls.append(messages)
        return LLMResponse(content=self.outputs.pop(0), final_answer=None)


class FakeContextRetriever(ContextRetrieverPort):
    async def retrieve(self, task_spec: TaskSpec, task_graph: TaskGraph) -> ContextPack:
        return ContextPack(
            purpose=f"Context for {task_spec.goal}",
            token_budget=1000,
            items=[
                ContextItem(
                    type="code_chunk",
                    file="src/example.py",
                    start_line=1,
                    end_line=3,
                    content="1: class Example:\n2:     pass",
                )
            ],
        )


PROMPTS = LocalWorkflowPromptSet(
    normalizer="normalize",
    decomposer="decompose",
    fact_extractor="facts",
    planner="plan",
    final_writer="final",
)


def test_run_local_llm_workflow_success() -> None:
    async def scenario() -> None:
        llm = ScriptedLLM(
            [
                """
                {
                  "goal": "Understand example",
                  "task_type": "read_only_analysis",
                  "success_criteria": ["Facts are extracted"],
                  "constraints": ["Do not edit files"],
                  "unknowns": ["Need context"]
                }
                """,
                """
                {
                  "tasks": [
                    {
                      "id": "T1",
                      "name": "Read context",
                      "type": "read_only",
                      "expected_output": "Context facts"
                    },
                    {
                      "id": "T2",
                      "name": "Plan report",
                      "type": "planning",
                      "depends_on": ["T1"],
                      "expected_output": "Plan"
                    }
                  ]
                }
                """,
                """
                {
                  "facts": [
                    {
                      "id": "F1",
                      "claim": "The context contains class Example.",
                      "source": "src/example.py",
                      "confidence": "high"
                    }
                  ],
                  "unknowns": []
                }
                """,
                """
                {
                  "plan": [
                    {
                      "step": 1,
                      "action": "Report the extracted class fact.",
                      "reason_fact_ids": ["F1"],
                      "target_files": ["src/example.py"],
                      "risk": "low"
                    }
                  ],
                  "requires_approval": false
                }
                """,
                """
                {
                  "summary": "The workflow extracted a grounded fact and produced a read-only plan.",
                  "completed_tasks": ["T1", "T2"],
                  "changed_files": [],
                  "commands_run": [],
                  "remaining_issues": []
                }
                """,
            ]
        )
        use_case = RunLocalLLMWorkflowUseCase(
            json_worker=LocalLLMJsonWorker(llm),
            context_retriever=FakeContextRetriever(),
            validator=LocalWorkflowValidator(),
            prompts=PROMPTS,
        )

        result = await use_case.execute("Understand example")

        assert result.state == LocalWorkflowState.COMPLETED
        assert result.task_spec is not None
        assert result.fact_set is not None
        assert result.plan is not None
        assert result.final_report is not None
        assert result.final_report.changed_files == []
        assert len(llm.calls) == 5

    asyncio.run(scenario())


def test_run_local_llm_workflow_fails_on_ungrounded_plan() -> None:
    async def scenario() -> None:
        llm = ScriptedLLM(
            [
                """
                {
                  "goal": "Understand example",
                  "task_type": "read_only_analysis",
                  "success_criteria": ["Facts are extracted"],
                  "constraints": ["Do not edit files"],
                  "unknowns": []
                }
                """,
                """
                {
                  "tasks": [
                    {
                      "id": "T1",
                      "name": "Read context",
                      "type": "read_only",
                      "expected_output": "Context facts"
                    }
                  ]
                }
                """,
                """
                {
                  "facts": [
                    {
                      "id": "F1",
                      "claim": "The context contains class Example.",
                      "source": "src/example.py",
                      "confidence": "high"
                    }
                  ],
                  "unknowns": []
                }
                """,
                """
                {
                  "plan": [
                    {
                      "step": 1,
                      "action": "Report an unsupported claim.",
                      "reason_fact_ids": ["F404"],
                      "target_files": ["src/example.py"],
                      "risk": "low"
                    }
                  ],
                  "requires_approval": false
                }
                """,
            ]
        )
        use_case = RunLocalLLMWorkflowUseCase(
            json_worker=LocalLLMJsonWorker(llm),
            context_retriever=FakeContextRetriever(),
            validator=LocalWorkflowValidator(),
            prompts=PROMPTS,
        )

        result = await use_case.execute("Understand example")

        assert result.state == LocalWorkflowState.FAILED
        assert result.error is not None
        assert "unknown fact id F404" in result.error

    asyncio.run(scenario())
