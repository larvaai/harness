from __future__ import annotations

import json
from typing import Any

from harness.core.domain import DangerLevel, ToolCall, ToolDefinition, ToolResult
from .filesystem_indexer import CodeIndexError
from .ports import CodeIndexPort


CODE_INDEX_LIST_FILES_TOOL = "code_index.list_files"
CODE_INDEX_SEARCH_TEXT_TOOL = "code_index.search_text"
CODE_INDEX_READ_FILE_TOOL = "code_index.read_file"


class CodeIndexToolExecutor:
    def __init__(self, *, code_index: CodeIndexPort) -> None:
        self._code_index = code_index

    async def execute(self, call: ToolCall) -> ToolResult:
        try:
            if call.tool_name == CODE_INDEX_LIST_FILES_TOOL:
                return _success(call, self._list_files(call.arguments))
            if call.tool_name == CODE_INDEX_SEARCH_TEXT_TOOL:
                return _success(call, self._search_text(call.arguments))
            if call.tool_name == CODE_INDEX_READ_FILE_TOOL:
                return _success(call, self._read_file(call.arguments))
        except (CodeIndexError, ValueError) as exc:
            return ToolResult(tool_call_id=call.id, success=False, error=str(exc))

        return ToolResult(
            tool_call_id=call.id,
            success=False,
            error=f"Unsupported code index tool: {call.tool_name}",
        )

    def _list_files(self, arguments: dict[str, Any]) -> dict[str, Any]:
        max_results = _positive_int(arguments.get("max_results"), default=200)
        files = self._code_index.list_files()[:max_results]
        return {"files": [file.to_dict() for file in files], "count": len(files)}

    def _search_text(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = _required_string(arguments, "query")
        max_results = _positive_int(arguments.get("max_results"), default=50)
        references = self._code_index.search_text(query, max_results=max_results)
        return {
            "query": query,
            "matches": [reference.to_dict() for reference in references],
            "count": len(references),
        }

    def _read_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = _required_string(arguments, "path")
        start_line = _optional_positive_int(arguments.get("start_line"), "start_line")
        end_line = _optional_positive_int(arguments.get("end_line"), "end_line")
        content = self._code_index.read_file(
            path,
            start_line=start_line,
            end_line=end_line,
        )
        return {
            "path": path,
            "start_line": start_line,
            "end_line": end_line,
            "content": content,
        }


def code_index_tool_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name=CODE_INDEX_LIST_FILES_TOOL,
            description="List text files in the workspace code index.",
            input_schema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 200,
                    }
                },
                "additionalProperties": False,
            },
            danger_level=DangerLevel.SAFE,
        ),
        ToolDefinition(
            name=CODE_INDEX_SEARCH_TEXT_TOOL,
            description="Search indexed text files with a case-insensitive query.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 50,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            danger_level=DangerLevel.SAFE,
        ),
        ToolDefinition(
            name=CODE_INDEX_READ_FILE_TOOL,
            description="Read a UTF-8 text file by workspace-relative path.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "start_line": {"type": "integer", "minimum": 1},
                    "end_line": {"type": "integer", "minimum": 1},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            danger_level=DangerLevel.SAFE,
        ),
    ]


def _success(call: ToolCall, structured_content: dict[str, Any]) -> ToolResult:
    return ToolResult(
        tool_call_id=call.id,
        success=True,
        output=json.dumps(structured_content, indent=2, ensure_ascii=False),
        metadata={
            "feature": "code_index",
            "structured_content": structured_content,
        },
    )


def _required_string(arguments: dict[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _positive_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or value < 1:
        raise ValueError("expected a positive integer")
    return value


def _optional_positive_int(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value
