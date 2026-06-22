from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from ._serialization import to_plain_data


class LocalWorkflowState(str, Enum):
    CREATED = "created"
    NORMALIZED = "normalized"
    DECOMPOSED = "decomposed"
    CONTEXT_COLLECTED = "context_collected"
    FACTS_EXTRACTED = "facts_extracted"
    PLANNED = "planned"
    PLAN_VALIDATED = "plan_validated"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TaskSpec:
    goal: str
    task_type: str
    success_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskSpec:
        return cls(
            goal=str(data.get("goal", "")).strip(),
            task_type=str(data.get("task_type", "")).strip(),
            success_criteria=_string_list(data.get("success_criteria")),
            constraints=_string_list(data.get("constraints")),
            unknowns=_string_list(data.get("unknowns")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class MicroTask:
    id: str
    name: str
    type: str
    expected_output: str
    depends_on: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MicroTask:
        return cls(
            id=str(data.get("id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            type=str(data.get("type", "")).strip(),
            expected_output=str(data.get("expected_output", "")).strip(),
            depends_on=_string_list(data.get("depends_on")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class TaskGraph:
    tasks: list[MicroTask] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskGraph:
        return cls(
            tasks=[
                MicroTask.from_dict(item)
                for item in data.get("tasks", [])
                if isinstance(item, dict)
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class ContextItem:
    type: str
    content: str
    file: str | None = None
    start_line: int | None = None
    end_line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class ContextPack:
    purpose: str
    token_budget: int
    items: list[ContextItem] = field(default_factory=list)
    context_pack_id: str = field(default_factory=lambda: f"ctx_{uuid4().hex}")

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class Fact:
    id: str
    claim: str
    source: str
    confidence: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Fact:
        return cls(
            id=str(data.get("id", "")).strip(),
            claim=str(data.get("claim", "")).strip(),
            source=str(data.get("source", "")).strip(),
            confidence=str(data.get("confidence", "")).strip().lower(),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class FactSet:
    facts: list[Fact] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactSet:
        return cls(
            facts=[
                Fact.from_dict(item)
                for item in data.get("facts", [])
                if isinstance(item, dict)
            ],
            unknowns=_string_list(data.get("unknowns")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class PlanStep:
    step: int
    action: str
    reason_fact_ids: list[str] = field(default_factory=list)
    target_files: list[str] = field(default_factory=list)
    risk: str = "low"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanStep:
        raw_step = data.get("step", 0)
        return cls(
            step=raw_step if isinstance(raw_step, int) else 0,
            action=str(data.get("action", "")).strip(),
            reason_fact_ids=_string_list(
                data.get("reason_fact_ids", data.get("reason", []))
            ),
            target_files=_string_list(data.get("target_files", data.get("files", []))),
            risk=str(data.get("risk", "low")).strip().lower(),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class Plan:
    plan: list[PlanStep] = field(default_factory=list)
    requires_approval: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        return cls(
            plan=[
                PlanStep.from_dict(item)
                for item in data.get("plan", [])
                if isinstance(item, dict)
            ],
            requires_approval=bool(data.get("requires_approval", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class FinalReport:
    summary: str
    completed_tasks: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    commands_run: list[dict[str, Any]] = field(default_factory=list)
    remaining_issues: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinalReport:
        commands = data.get("commands_run", [])
        return cls(
            summary=str(data.get("summary", "")).strip(),
            completed_tasks=_string_list(data.get("completed_tasks")),
            changed_files=_string_list(data.get("changed_files")),
            commands_run=[item for item in commands if isinstance(item, dict)],
            remaining_issues=_string_list(data.get("remaining_issues")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)

    @classmethod
    def ok(cls) -> ValidationResult:
        return cls(valid=True)

    @classmethod
    def invalid(cls, *issues: str) -> ValidationResult:
        return cls(valid=False, issues=list(issues))

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


@dataclass(frozen=True, slots=True)
class LocalWorkflowResult:
    run_id: str
    state: LocalWorkflowState
    task_spec: TaskSpec | None = None
    task_graph: TaskGraph | None = None
    context_pack: ContextPack | None = None
    fact_set: FactSet | None = None
    plan: Plan | None = None
    final_report: FinalReport | None = None
    validations: dict[str, ValidationResult] = field(default_factory=dict)
    raw_outputs: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_plain_data(self)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]
