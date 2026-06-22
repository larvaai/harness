from __future__ import annotations

from harness.core.domain import (
    FactSet,
    FinalReport,
    Plan,
    TaskGraph,
    TaskSpec,
    ValidationResult,
)


class LocalWorkflowValidationError(ValueError):
    pass


class LocalWorkflowValidator:
    def validate_task_spec(self, task_spec: TaskSpec) -> ValidationResult:
        issues: list[str] = []
        if not task_spec.goal:
            issues.append("TaskSpec.goal is required.")
        if not task_spec.task_type:
            issues.append("TaskSpec.task_type is required.")
        if not task_spec.success_criteria:
            issues.append("TaskSpec.success_criteria must not be empty.")
        return _result(issues)

    def validate_task_graph(self, task_graph: TaskGraph) -> ValidationResult:
        issues: list[str] = []
        ids: set[str] = set()

        if not task_graph.tasks:
            issues.append("TaskGraph.tasks must not be empty.")

        for task in task_graph.tasks:
            if not task.id:
                issues.append("Every task must have an id.")
            if task.id in ids:
                issues.append(f"Duplicate task id: {task.id}.")
            ids.add(task.id)
            if not task.name:
                issues.append(f"Task {task.id or '<missing>'} must have a name.")
            if not task.type:
                issues.append(f"Task {task.id or '<missing>'} must have a type.")
            if not task.expected_output:
                issues.append(
                    f"Task {task.id or '<missing>'} must have expected_output."
                )

        for task in task_graph.tasks:
            for dependency in task.depends_on:
                if dependency not in ids:
                    issues.append(
                        f"Task {task.id} depends on unknown task id {dependency}."
                    )

        return _result(issues)

    def validate_fact_set(self, fact_set: FactSet) -> ValidationResult:
        issues: list[str] = []
        allowed_confidence = {"high", "medium", "low"}

        if not fact_set.facts:
            issues.append("FactSet.facts must not be empty.")

        ids: set[str] = set()
        for fact in fact_set.facts:
            if not fact.id:
                issues.append("Every fact must have an id.")
            if fact.id in ids:
                issues.append(f"Duplicate fact id: {fact.id}.")
            ids.add(fact.id)
            if not fact.claim:
                issues.append(f"Fact {fact.id or '<missing>'} must have a claim.")
            if not fact.source:
                issues.append(f"Fact {fact.id or '<missing>'} must have a source.")
            if fact.confidence not in allowed_confidence:
                issues.append(
                    f"Fact {fact.id or '<missing>'} has invalid confidence "
                    f"{fact.confidence!r}."
                )

        return _result(issues)

    def validate_plan(self, plan: Plan, fact_set: FactSet) -> ValidationResult:
        issues: list[str] = []
        fact_ids = {fact.id for fact in fact_set.facts}
        allowed_risk = {"low", "medium", "high"}

        if not plan.plan:
            issues.append("Plan.plan must not be empty.")

        for step in plan.plan:
            if step.step <= 0:
                issues.append("Every plan step must have a positive step number.")
            if not step.action:
                issues.append(f"Plan step {step.step} must have an action.")
            if not step.reason_fact_ids:
                issues.append(
                    f"Plan step {step.step} must cite at least one fact id."
                )
            for fact_id in step.reason_fact_ids:
                if fact_id not in fact_ids:
                    issues.append(
                        f"Plan step {step.step} cites unknown fact id {fact_id}."
                    )
            if step.risk not in allowed_risk:
                issues.append(f"Plan step {step.step} has invalid risk {step.risk!r}.")
            if step.risk == "high" and not plan.requires_approval:
                issues.append("High-risk plan steps require approval.")

        return _result(issues)

    def validate_final_report(self, final_report: FinalReport) -> ValidationResult:
        issues: list[str] = []
        if not final_report.summary:
            issues.append("FinalReport.summary is required.")
        return _result(issues)

    def ensure_valid(self, name: str, validation: ValidationResult) -> None:
        if not validation.valid:
            raise LocalWorkflowValidationError(
                f"{name} validation failed: {'; '.join(validation.issues)}"
            )


def _result(issues: list[str]) -> ValidationResult:
    return ValidationResult.invalid(*issues) if issues else ValidationResult.ok()
