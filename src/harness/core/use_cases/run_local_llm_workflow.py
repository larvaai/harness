from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from harness.core.domain import (
    FactSet,
    FinalReport,
    LocalWorkflowResult,
    LocalWorkflowState,
    Plan,
    TaskGraph,
    TaskSpec,
    ValidationResult,
)
from harness.core.ports import ContextRetrieverPort, LocalWorkflowTextLogPort
from harness.core.services import LocalLLMJsonWorker, LocalWorkflowValidator


@dataclass(frozen=True, slots=True)
class LocalWorkflowPromptSet:
    normalizer: str
    decomposer: str
    fact_extractor: str
    planner: str
    final_writer: str


class RunLocalLLMWorkflowUseCase:
    def __init__(
        self,
        *,
        json_worker: LocalLLMJsonWorker,
        context_retriever: ContextRetrieverPort,
        validator: LocalWorkflowValidator,
        prompts: LocalWorkflowPromptSet,
        text_logger: LocalWorkflowTextLogPort | None = None,
    ) -> None:
        self._json_worker = json_worker
        self._context_retriever = context_retriever
        self._validator = validator
        self._prompts = prompts
        self._text_logger = text_logger

    async def execute(self, user_request: str) -> LocalWorkflowResult:
        run_id = f"local_run_{uuid4().hex}"
        raw_outputs: dict[str, str] = {}
        validations: dict[str, ValidationResult] = {}
        state = LocalWorkflowState.CREATED

        task_spec: TaskSpec | None = None
        task_graph: TaskGraph | None = None
        fact_set: FactSet | None = None
        plan: Plan | None = None
        final_report: FinalReport | None = None
        context_pack = None

        try:
            await self._start_text_log(run_id=run_id, user_request=user_request)

            task_spec_response = await self._json_worker.run_json(
                system_prompt=self._prompts.normalizer,
                user_payload=user_request,
            )
            raw_outputs["normalizer"] = task_spec_response.raw_text
            await self._log_llm_step(
                step_name="normalizer",
                system_prompt=self._prompts.normalizer,
                user_payload=user_request,
                raw_text=task_spec_response.raw_text,
                parsed_json=task_spec_response.data,
            )
            task_spec = TaskSpec.from_dict(task_spec_response.data)
            validations["task_spec"] = self._validator.validate_task_spec(task_spec)
            self._validator.ensure_valid("task_spec", validations["task_spec"])
            state = LocalWorkflowState.NORMALIZED

            task_graph_response = await self._json_worker.run_json(
                system_prompt=self._prompts.decomposer,
                user_payload=_json_payload({"task_spec": task_spec.to_dict()}),
            )
            raw_outputs["decomposer"] = task_graph_response.raw_text
            await self._log_llm_step(
                step_name="decomposer",
                system_prompt=self._prompts.decomposer,
                user_payload=_json_payload({"task_spec": task_spec.to_dict()}),
                raw_text=task_graph_response.raw_text,
                parsed_json=task_graph_response.data,
            )
            task_graph = TaskGraph.from_dict(task_graph_response.data)
            validations["task_graph"] = self._validator.validate_task_graph(task_graph)
            self._validator.ensure_valid("task_graph", validations["task_graph"])
            state = LocalWorkflowState.DECOMPOSED

            context_pack = await self._context_retriever.retrieve(task_spec, task_graph)
            await self._log_context_pack(context_pack)
            state = LocalWorkflowState.CONTEXT_COLLECTED

            fact_payload = _json_payload(
                {
                    "task_spec": task_spec.to_dict(),
                    "context_pack": context_pack.to_dict(),
                }
            )
            fact_response = await self._json_worker.run_json(
                system_prompt=self._prompts.fact_extractor,
                user_payload=fact_payload,
            )
            raw_outputs["fact_extractor"] = fact_response.raw_text
            await self._log_llm_step(
                step_name="fact_extractor",
                system_prompt=self._prompts.fact_extractor,
                user_payload=fact_payload,
                raw_text=fact_response.raw_text,
                parsed_json=fact_response.data,
            )
            fact_set = FactSet.from_dict(fact_response.data)
            validations["fact_set"] = self._validator.validate_fact_set(fact_set)
            self._validator.ensure_valid("fact_set", validations["fact_set"])
            state = LocalWorkflowState.FACTS_EXTRACTED

            plan_payload = _json_payload(
                {
                    "task_spec": task_spec.to_dict(),
                    "task_graph": task_graph.to_dict(),
                    "facts": fact_set.to_dict(),
                }
            )
            plan_response = await self._json_worker.run_json(
                system_prompt=self._prompts.planner,
                user_payload=plan_payload,
            )
            raw_outputs["planner"] = plan_response.raw_text
            await self._log_llm_step(
                step_name="planner",
                system_prompt=self._prompts.planner,
                user_payload=plan_payload,
                raw_text=plan_response.raw_text,
                parsed_json=plan_response.data,
            )
            plan = Plan.from_dict(plan_response.data)
            validations["plan"] = self._validator.validate_plan(plan, fact_set)
            self._validator.ensure_valid("plan", validations["plan"])
            state = LocalWorkflowState.PLAN_VALIDATED

            final_payload = _json_payload(
                {
                    "task_spec": task_spec.to_dict(),
                    "task_graph": task_graph.to_dict(),
                    "context_pack": _compact_context_pack(context_pack.to_dict()),
                    "facts": fact_set.to_dict(),
                    "plan": plan.to_dict(),
                    "validations": {
                        key: value.to_dict() for key, value in validations.items()
                    },
                }
            )
            final_response = await self._json_worker.run_json(
                system_prompt=self._prompts.final_writer,
                user_payload=final_payload,
            )
            raw_outputs["final_writer"] = final_response.raw_text
            await self._log_llm_step(
                step_name="final_writer",
                system_prompt=self._prompts.final_writer,
                user_payload=final_payload,
                raw_text=final_response.raw_text,
                parsed_json=final_response.data,
            )
            final_report = FinalReport.from_dict(final_response.data)
            validations["final_report"] = self._validator.validate_final_report(
                final_report
            )
            self._validator.ensure_valid(
                "final_report", validations["final_report"]
            )
            state = LocalWorkflowState.COMPLETED

            result = LocalWorkflowResult(
                run_id=run_id,
                state=state,
                task_spec=task_spec,
                task_graph=task_graph,
                context_pack=context_pack,
                fact_set=fact_set,
                plan=plan,
                final_report=final_report,
                validations=validations,
                raw_outputs=raw_outputs,
            )
            await self._finish_text_log(result)
            return result
        except Exception as exc:
            result = LocalWorkflowResult(
                run_id=run_id,
                state=LocalWorkflowState.FAILED,
                task_spec=task_spec,
                task_graph=task_graph,
                context_pack=context_pack,
                fact_set=fact_set,
                plan=plan,
                final_report=final_report,
                validations=validations,
                raw_outputs=raw_outputs,
                error=str(exc),
            )
            await self._finish_text_log(result)
            return result

    async def _start_text_log(self, *, run_id: str, user_request: str) -> None:
        if self._text_logger is not None:
            await self._text_logger.start_run(run_id=run_id, user_request=user_request)

    async def _log_context_pack(self, context_pack) -> None:
        if self._text_logger is not None:
            await self._text_logger.log_context_pack(context_pack=context_pack)

    async def _log_llm_step(
        self,
        *,
        step_name: str,
        system_prompt: str,
        user_payload: str,
        raw_text: str,
        parsed_json: dict[str, Any],
    ) -> None:
        if self._text_logger is not None:
            await self._text_logger.log_llm_step(
                step_name=step_name,
                system_prompt=system_prompt,
                user_payload=user_payload,
                raw_text=raw_text,
                parsed_json=parsed_json,
            )

    async def _finish_text_log(self, result: LocalWorkflowResult) -> None:
        if self._text_logger is not None:
            await self._text_logger.finish_run(result=result)


def _json_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _compact_context_pack(context_pack: dict[str, Any]) -> dict[str, Any]:
    compact_items: list[dict[str, Any]] = []
    for item in context_pack.get("items", []):
        if not isinstance(item, dict):
            continue
        compact_items.append(
            {
                "type": item.get("type"),
                "file": item.get("file"),
                "start_line": item.get("start_line"),
                "end_line": item.get("end_line"),
            }
        )
    return {
        "context_pack_id": context_pack.get("context_pack_id"),
        "purpose": context_pack.get("purpose"),
        "token_budget": context_pack.get("token_budget"),
        "items": compact_items,
    }
