from __future__ import annotations

from pathlib import Path

from harness.core.domain import HookContext, HookPoint, HookResult, ToolCall, ToolResult

from .tools import (
    CODE_INDEX_LIST_FILES_TOOL,
    CODE_INDEX_READ_FILE_TOOL,
    CODE_INDEX_SEARCH_TEXT_TOOL,
)


class CodeIndexToolHookRunner:
    def __init__(self, *, workspace_root: str | Path) -> None:
        self._workspace_root = Path(workspace_root).resolve()

    async def run(self, point: HookPoint, context: HookContext) -> list[HookResult]:
        if point == HookPoint.BEFORE_TOOL:
            tool_call = context.payload.get("tool_call")
            if isinstance(tool_call, ToolCall) and _is_code_index_tool(tool_call):
                self._validate_tool_call(tool_call)
                return [HookResult(hook_name="code_index.validate_tool", point=point)]

        if point == HookPoint.AFTER_TOOL:
            tool_result = context.payload.get("tool_result")
            tool_call = context.payload.get("tool_call")
            if isinstance(tool_call, ToolCall) and isinstance(tool_result, ToolResult):
                if _is_code_index_tool(tool_call):
                    return [
                        HookResult(
                            hook_name="code_index.inspect_tool_result",
                            point=point,
                            success=tool_result.success,
                            error=tool_result.error,
                            metadata={"feature": "code_index"},
                        )
                    ]

        return [
            HookResult(
                hook_name="code_index.hooks",
                point=point,
                skipped=True,
                metadata={"feature": "code_index"},
            )
        ]

    def _validate_tool_call(self, tool_call: ToolCall) -> None:
        if tool_call.tool_name == CODE_INDEX_LIST_FILES_TOOL:
            _validate_optional_positive_int(tool_call.arguments, "max_results")
            return

        if tool_call.tool_name == CODE_INDEX_SEARCH_TEXT_TOOL:
            query = tool_call.arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                raise PermissionError("code index search query must be a non-empty string")
            _validate_optional_positive_int(tool_call.arguments, "max_results")
            return

        if tool_call.tool_name == CODE_INDEX_READ_FILE_TOOL:
            path = tool_call.arguments.get("path")
            if not isinstance(path, str) or not path.strip():
                raise PermissionError("code index read path must be a non-empty string")
            resolved = (self._workspace_root / path).resolve()
            if not _is_relative_to(resolved, self._workspace_root):
                raise PermissionError(f"code index path escapes workspace root: {path}")
            _validate_optional_positive_int(tool_call.arguments, "start_line")
            _validate_optional_positive_int(tool_call.arguments, "end_line")
            start_line = tool_call.arguments.get("start_line")
            end_line = tool_call.arguments.get("end_line")
            if isinstance(start_line, int) and isinstance(end_line, int):
                if end_line < start_line:
                    raise PermissionError(
                        "code index end_line must be greater than or equal to start_line"
                    )
            return

        raise PermissionError(f"unsupported code index tool: {tool_call.tool_name}")


def _is_code_index_tool(tool_call: ToolCall) -> bool:
    return tool_call.tool_name in {
        CODE_INDEX_LIST_FILES_TOOL,
        CODE_INDEX_SEARCH_TEXT_TOOL,
        CODE_INDEX_READ_FILE_TOOL,
    }


def _validate_optional_positive_int(arguments: dict[str, object], name: str) -> None:
    value = arguments.get(name)
    if value is None:
        return
    if not isinstance(value, int) or value < 1:
        raise PermissionError(f"code index {name} must be a positive integer")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
