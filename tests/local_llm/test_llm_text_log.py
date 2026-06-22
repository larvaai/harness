from __future__ import annotations

import asyncio

from harness.adapters.logging import LLMTextLogWriter
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

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
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


def test_llm_text_log_writer_records_human_readable_sections(tmp_path) -> None:
    async def scenario() -> None:
        log_path = tmp_path / "var" / "demo" / "llm-textlog.txt"
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
                  "summary": "The workflow extracted a grounded fact.",
                  "completed_tasks": ["T1"],
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
            text_logger=LLMTextLogWriter(log_path),
        )

        result = await use_case.execute("Understand example")

        assert result.state == LocalWorkflowState.COMPLETED
        text = log_path.read_text(encoding="utf-8")
        assert "LLM STEP: normalizer" in text
        assert "LLM STEP: decomposer" in text
        assert "LLM STEP: fact_extractor" in text
        assert "LLM STEP: planner" in text
        assert "LLM STEP: final_writer" in text
        assert "Human-Readable Answer:" in text
        assert "Goal: Understand example" in text
        assert "Parsed JSON:" in text
        assert "Raw LLM Response:" in text
        assert "WORKFLOW RESULT" in text

    asyncio.run(scenario())
