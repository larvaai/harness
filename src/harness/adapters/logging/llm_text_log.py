from __future__ import annotations

import json
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from harness.core.domain import ContextPack, LocalWorkflowResult


class LLMTextLogWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    async def start_run(self, *, run_id: str, user_request: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "\n".join(
                [
                    "# Local LLM Workflow Text Log",
                    "",
                    f"Started At: {datetime.now(UTC).isoformat()}",
                    f"Run ID: {run_id}",
                    "",
                    "User Request:",
                    _indent(user_request),
                    "",
                ]
            ),
            encoding="utf-8",
        )

    async def log_context_pack(self, *, context_pack: ContextPack) -> None:
        lines = [
            _section("CONTEXT PACK"),
            f"Purpose: {context_pack.purpose}",
            f"Token Budget: {context_pack.token_budget}",
            f"Items: {len(context_pack.items)}",
            "",
        ]
        for index, item in enumerate(context_pack.items, start=1):
            source = item.file or item.type
            line_range = ""
            if item.start_line is not None and item.end_line is not None:
                line_range = f":{item.start_line}-{item.end_line}"
            lines.extend(
                [
                    f"Context Item {index}: {source}{line_range}",
                    _indent(_truncate(item.content, 2500)),
                    "",
                ]
            )
        self._append("\n".join(lines))

    async def log_llm_step(
        self,
        *,
        step_name: str,
        system_prompt: str,
        user_payload: str,
        raw_text: str,
        parsed_json: dict[str, Any],
    ) -> None:
        human_text = render_human_readable(step_name, parsed_json)
        pretty_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
        lines = [
            _section(f"LLM STEP: {step_name}"),
            "Human-Readable Answer:",
            _indent(human_text),
            "",
            "Parsed JSON:",
            _indent(pretty_json),
            "",
            "Raw LLM Response:",
            _indent(raw_text),
            "",
            "System Prompt Sent:",
            _indent(system_prompt),
            "",
            "User Payload Sent:",
            _indent(user_payload),
            "",
        ]
        self._append("\n".join(lines))

    async def finish_run(self, *, result: LocalWorkflowResult) -> None:
        lines = [
            _section("WORKFLOW RESULT"),
            f"Finished At: {datetime.now(UTC).isoformat()}",
            f"State: {result.state.value}",
            f"Error: {result.error or '<none>'}",
        ]
        if result.final_report is not None:
            lines.extend(
                [
                    "",
                    "Final Summary:",
                    _indent(result.final_report.summary),
                ]
            )
        self._append("\n".join(lines))

    def _append(self, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(text.rstrip())
            file.write("\n\n")


def render_human_readable(step_name: str, data: dict[str, Any]) -> str:
    if step_name == "normalizer":
        return _render_normalizer(data)
    if step_name == "decomposer":
        return _render_decomposer(data)
    if step_name == "fact_extractor":
        return _render_fact_extractor(data)
    if step_name == "planner":
        return _render_planner(data)
    if step_name == "final_writer":
        return _render_final_writer(data)
    return json.dumps(data, indent=2, ensure_ascii=False)


def _render_normalizer(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Goal: {data.get('goal', '')}",
            f"Task Type: {data.get('task_type', '')}",
            "",
            "Success Criteria:",
            *_bullets(data.get("success_criteria")),
            "",
            "Constraints:",
            *_bullets(data.get("constraints")),
            "",
            "Unknowns:",
            *_bullets(data.get("unknowns")),
        ]
    )


def _render_decomposer(data: dict[str, Any]) -> str:
    lines = ["Micro Tasks:"]
    for task in _list_of_dicts(data.get("tasks")):
        dependencies = task.get("depends_on") or []
        dependency_text = ", ".join(str(item) for item in dependencies) or "none"
        lines.extend(
            [
                f"- {task.get('id', '?')}: {task.get('name', '')}",
                f"  type: {task.get('type', '')}",
                f"  depends_on: {dependency_text}",
                f"  expected_output: {task.get('expected_output', '')}",
            ]
        )
    return "\n".join(lines)


def _render_fact_extractor(data: dict[str, Any]) -> str:
    lines = ["Facts:"]
    for fact in _list_of_dicts(data.get("facts")):
        lines.extend(
            [
                f"- {fact.get('id', '?')}: {fact.get('claim', '')}",
                f"  source: {fact.get('source', '')}",
                f"  confidence: {fact.get('confidence', '')}",
            ]
        )
    lines.extend(["", "Unknowns:", *_bullets(data.get("unknowns"))])
    return "\n".join(lines)


def _render_planner(data: dict[str, Any]) -> str:
    lines = [f"Requires Approval: {bool(data.get('requires_approval', False))}", ""]
    lines.append("Plan:")
    for step in _list_of_dicts(data.get("plan")):
        reason_ids = ", ".join(str(item) for item in step.get("reason_fact_ids", []))
        files = ", ".join(str(item) for item in step.get("target_files", []))
        lines.extend(
            [
                f"- Step {step.get('step', '?')}: {step.get('action', '')}",
                f"  facts: {reason_ids or 'none'}",
                f"  target_files: {files or 'none'}",
                f"  risk: {step.get('risk', '')}",
            ]
        )
    return "\n".join(lines)


def _render_final_writer(data: dict[str, Any]) -> str:
    lines = [
        f"Summary: {data.get('summary', '')}",
        "",
        "Completed Tasks:",
        *_bullets(data.get("completed_tasks")),
        "",
        "Changed Files:",
        *_bullets(data.get("changed_files")),
        "",
        "Commands Run:",
    ]
    commands = _list_of_dicts(data.get("commands_run"))
    if commands:
        for command in commands:
            lines.append(f"- {command.get('cmd', '')} -> {command.get('exit_code', '')}")
    else:
        lines.append("- none")
    lines.extend(["", "Remaining Issues:", *_bullets(data.get("remaining_issues"))])
    return "\n".join(lines)


def _section(title: str) -> str:
    return f"{'=' * 80}\n{title}\n{'=' * 80}"


def _indent(text: str) -> str:
    return textwrap.indent(text.rstrip() or "<empty>", "  ")


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n... <truncated {len(text) - max_chars} chars>"


def _bullets(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["- none"]
    return [f"- {item}" for item in value]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
